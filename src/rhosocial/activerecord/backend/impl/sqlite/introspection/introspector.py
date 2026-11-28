# src/rhosocial/activerecord/backend/impl/sqlite/introspection/introspector.py
"""
SQLite concrete introspectors.

Implements AbstractIntrospector and AsyncAbstractIntrospector for SQLite
databases using PRAGMA commands and the sqlite_master / sqlite_schema system
table for metadata queries.

The introspectors are exposed via ``backend.introspector`` and also provide
SQLite-specific access through ``backend.introspector.pragma``.

Key behaviours:
  - Version-aware: uses ``PRAGMA table_list`` (3.37+) or ``sqlite_master``
  - Extended column info: uses ``PRAGMA table_xinfo`` (3.26+)
  - ``parse_*`` methods are pure Python — shared by sync and async introspectors

Design principle: Sync and Async are separate and cannot coexist.
- SQLiteIntrospector: for synchronous backends
- AsyncSQLiteIntrospector: for asynchronous backends
"""

import copy
import sqlite3
from typing import Any, Dict, List, Optional, Tuple, cast

from rhosocial.activerecord.backend.introspection.base import (
    IntrospectorMixin,
    AbstractIntrospector,
    AsyncAbstractIntrospector,
)
from rhosocial.activerecord.backend.introspection.cache import IntrospectionCache
from rhosocial.activerecord.backend.introspection.errors import ObjectNotFoundError
from rhosocial.activerecord.backend.introspection.executor import (
    IntrospectorExecutor,
    AsyncIntrospectorExecutor,
)
from rhosocial.activerecord.backend.introspection.types import (
    ConstraintState,
    DerivedObjectState,
    IndexState,
    ItemKind,
    PartitionState,
    SequenceState,
    StorageOptionsState,
    TableState,
    IntrospectionDatabaseInfo,
    IntrospectionTableInfo,
    TableType,
    IntrospectionColumnInfo,
    ColumnNullable,
    IndexInfo,
    IndexColumnInfo,
    IndexType,
    IntrospectionForeignKeyInfo,
    ReferentialAction,
    IntrospectionViewInfo,
    IntrospectionTriggerInfo,
    IntrospectionScope,
)
from rhosocial.activerecord.backend.textscan import (
    find_word,
    has_word,
    leading_word,
    parenthesised,
    split_top_level,
)
from .pragma_introspector import (
    PragmaIntrospector,
    AsyncPragmaIntrospector,
)
from .status_introspector import (
    SQLiteStatusIntrospector,
    AsyncSQLiteStatusIntrospector,
)
from ..expression.introspection.introspection import (
    SQLiteIndexDdlStatement,
    SQLiteIndexOwnerStatement,
    SQLiteTableCountStatement,
    SQLiteTableDdlStatement,
    SQLiteTableStorageStatement,
)


def _precision_pair(inner: str) -> Optional[Tuple[int, int]]:
    """The two numbers of a ``(10, 2)`` group, when that is its whole shape.

    The original spelling admitted ``(10, 2)`` and ``(10,2)`` but not
    whitespace against either parenthesis, nor anything but the two numbers
    around the comma inside. Returning ``None`` leaves the single-number
    reading and the all-``None`` answer to the caller.
    """
    if not inner or not inner[0].isdecimal() or not inner[-1].isdecimal():
        return None
    pieces = split_top_level(inner, ",")
    if len(pieces) != 2:
        return None
    first, second = pieces
    if not first.rstrip().isdecimal() or not second.lstrip().isdecimal():
        return None
    return int(first.strip()), int(second.strip())


def _keyword_before_parenthesis(text: str, keywords: Tuple[str, ...]) -> bool:
    """Whether *text* starts with one of *keywords*, then ``(``.

    Whitespace is allowed on both sides of the keyword. The keyword is read as
    a whole word, so ``TIME`` does not claim ``TIMESTAMP`` and ``DEC`` does not
    claim ``DECIMAL``.
    """
    index = 0
    while index < len(text) and text[index].isspace():
        index += 1
    word = leading_word(text, index)
    if not word or word.upper() not in keywords:
        return False
    index += len(word)
    while index < len(text) and text[index].isspace():
        index += 1
    return index < len(text) and text[index] == "("


class SQLiteIntrospectorMixin(IntrospectorMixin):
    """Mixin providing shared SQLite-specific introspection logic.

    Both SQLiteIntrospector and AsyncSQLiteIntrospector inherit
    from this mixin to share:
    - Default schema handling
    - SQLite version detection
    - SQL generation overrides
    - parse_* implementations
    """

    @property
    def default_schema(self) -> str:
        """The SQLite schema name for the primary database."""
        return "main"

    def _get_sqlite_version(self) -> tuple:
        """Return SQLite library version as an integer tuple."""
        parts = sqlite3.sqlite_version.split(".")
        return tuple(int(p) if p.isdigit() else 0 for p in (parts + ["0", "0"])[:3])

    # ------------------------------------------------------------------ #
    # SQL generation — uses base class implementation via Expression/Dialect
    # SQLite's format_*_query() methods in the Dialect layer handle PRAGMA
    # commands and sqlite_master queries.
    # ------------------------------------------------------------------ #

    # Note: SQLite does NOT override the *_statement() factories because:
    # 1. The base factory returns the family's statement object
    # 2. Expression.to_sql() calls Dialect.format_*_query()
    # 3. SQLiteDialect.format_*_query() generates correct PRAGMA/sqlite_master SQL
    #
    # This follows the same pattern as MySQL and PostgreSQL backends.

    # ------------------------------------------------------------------ #
    # Parse methods — pure Python, no I/O
    # ------------------------------------------------------------------ #

    def parse_database_info(self, rows: List[Dict[str, Any]],
                             pragma_values: Optional[Dict[str, Any]] = None) -> IntrospectionDatabaseInfo:
        """Turn the version row into a database record.

        *pragma_values* carries what the pragmas answered -- encoding, page
        counts -- because those are not columns of any row. They arrive as a
        dict rather than being read here so that this method stays pure:
        ``get_database_info`` does the I/O, and the sync and async paths hand
        the same dict to the same parser.
        """
        row = rows[0] if rows else {}
        version_str = row.get("version") or sqlite3.sqlite_version
        parts = version_str.split(".")
        version_tuple = tuple(int(p) if p.isdigit() else 0 for p in (parts + ["0", "0"])[:3])
        # SQLite's database name is the schema name (e.g., "main")
        # For file-based databases, we can also show the filename
        db_path = self._backend.config.database or ":memory:"
        values = pragma_values or {}

        # size_bytes is page_count * page_size, which is the file's size on
        # disk rather than the sum of its rows. Either pragma missing makes the
        # answer None rather than a wrong number.
        page_count = values.get("page_count")
        page_size = values.get("page_size")
        size_bytes = None
        if page_count is not None and page_size is not None:
            try:
                size_bytes = int(page_count) * int(page_size)
            except (TypeError, ValueError):
                size_bytes = None

        return IntrospectionDatabaseInfo(
            name="main",  # SQLite's default schema name
            version=version_str,
            version_tuple=version_tuple,
            vendor="SQLite",
            encoding=values.get("encoding"),
            # No database-level collation: SQLite attaches a collation to a
            # column or an expression, not to the file, so this stays None
            # rather than repeating the encoding under a second name.
            size_bytes=size_bytes,
            table_count=values.get("table_count"),
            extra={"path": db_path},
        )

    #: The pragmas a database record reads, and why each is here.
    _DATABASE_PRAGMAS = ("encoding", "page_count", "page_size")

    @staticmethod
    def _pragma_value(row: Any, name: str) -> Any:
        """The scalar a PRAGMA answered with, or ``None``.

        ``PRAGMA encoding`` returns one row with one column named after the
        pragma; ``pragma.get`` hands back that whole row, so the value has to be
        picked out of it. An engine that names the column differently yields a
        single-key row, and that key's value is used; a row with several columns
        is not a scalar answer and is returned as-is rather than guessed at.
        """
        if row is None:
            return None
        if not isinstance(row, dict):
            return row
        if name in row:
            return row[name]
        if len(row) == 1:
            return next(iter(row.values()))
        return row

    def _collect_database_pragmas(self) -> Dict[str, Any]:
        """Read the pragmas that answer what the version row cannot.

        ``encoding`` is the database's text encoding (``PRAGMA encoding``),
        ``page_count`` and ``page_size`` the file's extent. ``table_count`` is
        not a pragma -- it is a count over ``sqlite_master`` -- and is read by
        the caller because it needs the schema.
        """
        values: Dict[str, Any] = {}
        for name in self._DATABASE_PRAGMAS:
            values[name] = self._pragma_value(self.pragma.get(name), name)
        return values

    def parse_tables(self, rows: List[Dict[str, Any]], schema: Optional[str]) -> List[IntrospectionTableInfo]:
        # PRAGMA table_list reports four kinds, and the two beyond table/view
        # are the ones a caller cannot otherwise tell apart:
        #
        #   table    an ordinary storage table
        #   view     a stored SELECT
        #   shadow   the storage tables a virtual-table module creates and
        #            maintains (fts_data, fts_idx, ...); nobody outside the
        #            module may write them, which is what SYSTEM_TABLE says
        #   virtual  the module-backed table the user created (an FTS5 or
        #            R-Tree index); its contents are maintained by the module,
        #            not by the table itself, which is what EXTERNAL says
        #
        # The sqlite_master fallback only ever produces the first two, so the
        # extra branches cost nothing on older SQLite versions.
        table_type_by_kind = {
            "table": TableType.BASE_TABLE,
            "view": TableType.VIEW,
            "shadow": TableType.SYSTEM_TABLE,
            "virtual": TableType.EXTERNAL,
        }
        tables = []
        for row in rows:
            type_str = row.get("type", "table").lower()
            table_type = table_type_by_kind.get(type_str, TableType.EXTERNAL)

            tables.append(
                IntrospectionTableInfo(
                    name=row["name"],
                    schema=schema or self.default_schema,
                    table_type=table_type,
                    row_count=None,
                    create_time=None,
                )
            )
        return tables

    def parse_table_storage(
        self,
        tables: List[IntrospectionTableInfo],
        storage_rows: List[Dict[str, Any]],
        index_rows: List[Dict[str, Any]],
    ) -> List[IntrospectionTableInfo]:
        """Attribute page bytes to the tables they belong to.

        The two row sets answer two catalogue questions: ``dbstat`` names
        every btree and its size, and ``sqlite_master`` names the table each
        index belongs to. Reducing them here -- rather than asking the engine
        to aggregate -- keeps the statements simple and the mapping explicit:
        a table's own btree carries its rows (``data_size_bytes``), the
        btrees of its indexes carry the rest (``index_size_bytes``), and
        ``size_bytes`` is their sum.

        A table with no pages keeps every slot ``None``: a view has no btree,
        and "this object's storage is not a question this engine answers for
        it" is a different answer from zero. Both directions hand the same
        rows to this method, so the two cannot disagree about one table's
        size.
        """
        bytes_by_btree: Dict[str, int] = {}
        for row in storage_rows:
            name = row.get("name")
            if not name:
                continue
            try:
                bytes_by_btree[name] = bytes_by_btree.get(name, 0) + int(row.get("pgsize") or 0)
            except (TypeError, ValueError):
                continue

        index_bytes: Dict[str, int] = {}
        for row in index_rows:
            index_name = row.get("name")
            owner = row.get("tbl_name")
            if index_name and owner:
                index_bytes[owner] = index_bytes.get(owner, 0) + bytes_by_btree.get(index_name, 0)

        for table in tables:
            data_bytes = bytes_by_btree.get(table.name)
            this_index_bytes = index_bytes.get(table.name) or None
            table.data_size_bytes = data_bytes
            table.index_size_bytes = this_index_bytes
            if data_bytes is not None:
                table.size_bytes = data_bytes + (this_index_bytes or 0)
        return tables

    @staticmethod
    def _extract_type_params(raw_type: str) -> dict:
        """Extract length/precision/scale from a raw SQL type string.

        Returns a dict with keys: character_maximum_length, numeric_precision,
        numeric_scale, datetime_precision (all None if not found).
        """
        result = dict.fromkeys(
            ["character_maximum_length", "numeric_precision", "numeric_scale",
             "datetime_precision"]
        )
        inner = parenthesised(raw_type)
        if inner is None:
            return result
        pair = _precision_pair(inner)
        if pair is not None:
            result["numeric_precision"], result["numeric_scale"] = pair
            return result
        if inner.isdecimal():
            value = int(inner)
            if _keyword_before_parenthesis(raw_type, ("TIMESTAMP", "TIME", "DATETIME")):
                result["datetime_precision"] = value
            elif _keyword_before_parenthesis(
                    raw_type, ("DECIMAL", "NUMERIC", "FLOAT", "DOUBLE", "REAL")):
                result["numeric_precision"] = value
            else:
                result["character_maximum_length"] = value
        return result

    def parse_columns(self, rows: List[Dict[str, Any]], table_name: str, schema: str,
                       ddl: Optional[str] = None,
                       unique_columns: Optional[set] = None) -> List[IntrospectionColumnInfo]:
        """Turn ``PRAGMA table_xinfo`` rows into column records.

        *ddl* carries the table's own text because ``AUTOINCREMENT`` appears
        only there. *unique_columns* carries the names a unique index covers,
        because SQLite records uniqueness on the index and not on the column:
        ``PRAGMA table_info`` says a column is unique no more than it says a
        table has a foreign key. Reporting ``False`` for a column the engine
        has a unique index on is the wrong answer, not a conservative one --
        a caller building a model from it would drop a constraint that exists.
        """
        columns = []
        has_auto_increment = ddl is not None and "AUTOINCREMENT" in ddl.upper()
        for row in rows:
            hidden = row.get("hidden", 0)
            if hidden == 1:
                # A hidden column of a virtual table (FTS shadow columns and
                # the like): part of the module's storage, not of the table a
                # caller reads. Generated columns are hidden==2/3 and are kept.
                continue
            nullable = ColumnNullable.NULLABLE if row["notnull"] == 0 else ColumnNullable.NOT_NULL
            raw_type = row.get("type") or "TEXT"
            # Extract base type (e.g., "VARCHAR" from "VARCHAR(255)")
            base_type = leading_word(raw_type, digits=False) or raw_type
            # SQLite pk field: 0 = not primary key, >0 = primary key (or part of composite PK)
            is_pk = row.get("pk", 0) > 0
            # Parse raw type string into a DataType expression
            from .type_parser import SQLiteTypeParser
            parsed = SQLiteTypeParser(self._backend.dialect).parse(raw_type)
            # Auto-increment: only applies to INTEGER PRIMARY KEY with AUTOINCREMENT keyword
            is_auto_inc = is_pk and has_auto_increment
            # Generated columns (hidden=2 => virtual, hidden=3 => stored).
            # SQLite reports *that* a column is generated, not what it is made
            # of: the expression lives in the table's DDL, which `table_xinfo`
            # does not return. Reading it would mean parsing that DDL, so the
            # field stays None here rather than carrying a guess.
            is_generated = hidden in (2, 3)
            gen_expr = None
            # Extract precision/length from raw type
            params = self._extract_type_params(raw_type)
            columns.append(
                IntrospectionColumnInfo(
                    name=row["name"],
                    table_name=table_name,
                    schema=schema,
                    ordinal_position=row["cid"] + 1,
                    data_type=base_type.lower(),
                    data_type_full=raw_type,
                    parsed_data_type=parsed,
                    nullable=nullable,
                    default_value=row.get("dflt_value"),
                    is_primary_key=is_pk,
                    # SQLite records uniqueness on the index, not on the column:
                    # PRAGMA table_info says a column is unique no more than it
                    # says a table has a foreign key. Reporting False for a
                    # column the engine has a unique index on is the wrong
                    # answer rather than a conservative one -- a caller building
                    # a model from it would drop a constraint that exists.
                    is_unique=(
                        is_pk
                        or (unique_columns is not None
                            and row["name"] in unique_columns)
                    ),
                    is_auto_increment=is_auto_inc,
                    is_generated=is_generated,
                    generated_expression=gen_expr,
                    character_maximum_length=params["character_maximum_length"],
                    numeric_precision=params["numeric_precision"],
                    numeric_scale=params["numeric_scale"],
                    datetime_precision=params["datetime_precision"],
                    extra={},
                )
            )
        return columns

    def _collect_unique_columns(self, table_name: str, schema: Optional[str]) -> set:
        """Read the index pragmas and return the unique column names.

        The I/O half of ``is_unique``: ``PRAGMA index_list`` says which indexes
        are unique and whether one is partial, ``PRAGMA index_xinfo`` says what
        each covers. Both are cheap and both are cached with the column list, so
        the cost is paid once per table rather than once per column.
        """
        index_rows = self.pragma.index_list(table_name, schema)
        columns_by_index: Dict[str, List[str]] = {}
        for idx in index_rows:
            name = idx.get("name")
            if not name:
                continue
            columns_by_index[name] = [
                str(c.get("name"))
                for c in self.pragma.index_xinfo(name, schema)
                if c.get("name") and not c.get("hidden")
            ]
        return self._unique_columns(index_rows, columns_by_index)

    async def _collect_unique_columns_async(self, table_name: str,
                                            schema: Optional[str]) -> set:
        """The async twin of :meth:`_collect_unique_columns`.

        Same two pragmas, awaited; the reduction is the shared
        :meth:`_unique_columns`, so the two directions cannot disagree about
        which columns count.
        """
        index_rows = await self.pragma.index_list(table_name, schema)
        columns_by_index: Dict[str, List[str]] = {}
        for idx in index_rows:
            name = idx.get("name")
            if not name:
                continue
            xinfo = await self.pragma.index_xinfo(name, schema)
            columns_by_index[name] = [
                str(c.get("name"))
                for c in xinfo
                if c.get("name") and not c.get("hidden")
            ]
        return self._unique_columns(index_rows, columns_by_index)

    @staticmethod
    def _unique_columns(index_rows: List[Dict[str, Any]],
                        columns_by_index: Dict[str, List[str]]) -> set:
        """Column names a unique index covers, for ``is_unique``.

        Takes the PRAGMA answers rather than the parsed ``IndexInfo`` list,
        because the index's *partial* flag and its *origin* are what decide
        whether the uniqueness is a promise about every row, and ``IndexInfo``
        carries neither. A partial unique index is skipped: it constrains only
        the rows that pass its ``WHERE``, which is not what ``is_unique``
        claims.
        """
        unique: set = set()
        for idx in index_rows:
            if not idx.get("unique") or idx.get("partial"):
                continue
            unique.update(columns_by_index.get(idx.get("name") or "", []))
        return unique

    def parse_indexes(self, rows: List[Dict[str, Any]], table_name: str, schema: str) -> List[IndexInfo]:
        if not rows:
            return []
        idx_map: Dict[str, IndexInfo] = {}
        for row in rows:
            idx_name = row.get("name")
            if idx_name not in idx_map:
                idx_type = IndexType.BTREE
                is_unique = bool(row.get("unique", 0))
                is_primary = idx_name.startswith("sqlite_autoindex_")
                idx_map[idx_name] = IndexInfo(
                    name=idx_name,
                    table_name=table_name,
                    schema=schema,
                    is_unique=is_unique,
                    is_primary=is_primary,
                    index_type=idx_type,
                    columns=[],
                    extra={},
                )
            col_name = row.get("column_name")
            if col_name:
                idx_map[idx_name].columns.append(
                    IndexColumnInfo(
                        name=col_name,
                        ordinal_position=row.get("seq", 0) + 1,
                    )
                )
        return list(idx_map.values())

    def parse_foreign_keys(
        self, rows: List[Dict[str, Any]], table_name: str, schema: str
    ) -> List[IntrospectionForeignKeyInfo]:
        if not rows:
            return []
        fk_map: Dict[int, IntrospectionForeignKeyInfo] = {}
        action_map = {
            "NO ACTION": ReferentialAction.NO_ACTION,
            "RESTRICT": ReferentialAction.RESTRICT,
            "CASCADE": ReferentialAction.CASCADE,
            "SET NULL": ReferentialAction.SET_NULL,
            "SET DEFAULT": ReferentialAction.SET_DEFAULT,
        }
        for row in rows:
            fk_id = row["id"]
            if fk_id not in fk_map:
                on_update = action_map.get(
                    row.get("on_update", "NO ACTION").upper(),
                    ReferentialAction.NO_ACTION,
                )
                on_delete = action_map.get(
                    row.get("on_delete", "NO ACTION").upper(),
                    ReferentialAction.NO_ACTION,
                )
                fk_map[fk_id] = IntrospectionForeignKeyInfo(
                    name=f"fk_{table_name}_{fk_id}",
                    table_name=table_name,
                    schema=schema,
                    referenced_table=row["table"],
                    on_update=on_update,
                    on_delete=on_delete,
                    columns=[],
                    referenced_columns=[],
                )
            fk_map[fk_id].columns.append(row["from"])
            fk_map[fk_id].referenced_columns.append(row["to"])
        return list(fk_map.values())

    def parse_views(self, rows: List[Dict[str, Any]], schema: str) -> List[IntrospectionViewInfo]:
        return [IntrospectionViewInfo(name=row["name"], schema=schema, definition=row.get("sql")) for row in rows]

    def parse_view_info(
        self, rows: List[Dict[str, Any]], view_name: str, schema: str
    ) -> Optional[IntrospectionViewInfo]:
        if not rows:
            return None
        row = rows[0]
        return IntrospectionViewInfo(name=row["name"], schema=schema, definition=row.get("sql"))

    #: The words that say *when* a trigger fires. ``INSTEAD OF`` is a timing
    #: too, and the only one that makes a view writable, so it is not folded
    #: into the event list.
    _TRIGGER_TIMING = ("BEFORE", "AFTER", "INSTEAD OF")
    #: The events a trigger can fire on. ``UPDATE OF col`` names columns, which
    #: are not part of the event.
    _TRIGGER_EVENTS = ("DELETE", "INSERT", "UPDATE")

    @classmethod
    def parse_trigger_header(cls, ddl: Optional[str]):
        """(timing, events) from a trigger's ``CREATE TRIGGER`` text.

        SQLite keeps a trigger's header only in its DDL -- there is no pragma
        and no column for *when* it fires or *what* it fires on -- so leaving
        these fields empty discards information the caller can already see in
        the definition and cannot be expected to re-parse.

        Returns ``("", [])`` when the text is missing or unparseable rather
        than guessing: an empty timing reads as "not stated", a wrong one
        reads as a fact about the schema.
        """
        if not ddl:
            return "", []
        header = ddl.split("ON", 1)[0].upper()
        timing = ""
        for candidate in cls._TRIGGER_TIMING:
            if candidate in header:
                timing = candidate
                break
        events = [e for e in cls._TRIGGER_EVENTS if e in header]
        return timing, events

    def parse_triggers(self, rows: List[Dict[str, Any]], schema: str) -> List[IntrospectionTriggerInfo]:
        triggers = []
        for row in rows:
            timing, events = self.parse_trigger_header(row.get("sql"))
            triggers.append(
                IntrospectionTriggerInfo(
                    name=row["name"],
                    table_name=row["tbl_name"],
                    schema=schema,
                    timing=timing,
                    events=events,
                    definition=row.get("sql"),
                )
            )
        return triggers

    # ------------------------------------------------------------------ #
    # Neutral object state — the pure parsers behind every state method.
    #
    # The I/O differs between sync and async; the reduction must not, so
    # every fact gathered from a pragma or a DDL is reduced here once and
    # handed the same inputs by both directions.
    # ------------------------------------------------------------------ #

    def _use_table_list(self) -> bool:
        """Whether ``PRAGMA table_list`` can answer this build.

        It carries ``wr`` and ``strict`` directly, so a build that has it need
        not parse the table DDL for those traits. The probe is the dialect's
        because the version belongs to the connected server, not to the
        ``sqlite3`` module the process happens to import.
        """
        probe = getattr(self.dialect, "supports_table_list_pragma", None)
        if probe is None:
            return False
        return bool(probe())

    @staticmethod
    def ordered_schema_names(
        names: List[str], schema: Optional[str] = None
    ) -> List[str]:
        """The schemas an unqualified name may live in, in resolution order.

        SQLite searches ``temp`` before ``main`` and the ``ATTACH``-ed
        databases after them, so a later candidate must not shadow an earlier
        one. An explicit schema is the whole list.
        """
        if schema is not None:
            return [schema]
        ordered: List[str] = [name for name in ("temp", "main") if name in names]
        ordered.extend(name for name in names if name not in ("temp", "main"))
        return ordered

    @staticmethod
    def select_table_row(
        rows: List[Dict[str, Any]],
        table_name: str,
        schema: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Pick the row ``PRAGMA table_list`` reported for one table.

        With no schema the row for ``temp`` wins over ``main``, because that
        is the table an unqualified reference would reach. A row from an
        ``ATTACH``-ed database is only chosen when neither of the two exists.
        """
        matches = [row for row in rows if row.get("name") == table_name]
        if schema is not None:
            matches = [row for row in matches if row.get("schema") == schema]
            return matches[0] if matches else None
        for preferred in ("temp", "main"):
            for row in matches:
                if row.get("schema") == preferred:
                    return row
        return matches[0] if matches else None

    @staticmethod
    def table_kind(schema: str, table_type: Optional[str] = None) -> str:
        """The neutral kind for a table in *schema*.

        ``temporary`` is a property of the schema the table lives in, not a
        separate object type: a temp table is an ordinary table in ``temp``.
        The module-backed and shadow kinds keep SQLite's own spelling rather
        than pretending to be regular tables.
        """
        if schema == "temp":
            return "temporary"
        if table_type in ("view", "shadow", "virtual"):
            return table_type
        return "regular"

    @staticmethod
    def parse_table_traits(
        ddl: Optional[str],
        without_rowid: Optional[bool] = None,
        strict: Optional[bool] = None,
    ) -> Tuple[str, ...]:
        """The table's storage traits, read from flags or from its DDL.

        ``PRAGMA table_list`` reports ``wr`` and ``strict`` as flags; a
        build without that pragma has only the statement text, where they
        follow the closing parenthesis. Reading the tail rather than the
        whole statement keeps a column named ``strict`` from being mistaken
        for the table option.
        """
        if without_rowid is None or strict is None:
            tail = ""
            if ddl:
                close = ddl.rfind(")")
                tail = ddl[close + 1:] if close != -1 else ddl
            if without_rowid is None:
                without_rowid = find_word(
                    tail, "WITHOUT ROWID", ignore_case=True
                ) != -1
            if strict is None:
                strict = has_word(tail, "STRICT", ignore_case=True)
        traits: List[str] = []
        if strict:
            traits.append("strict")
        if without_rowid:
            traits.append("without_rowid")
        return tuple(traits)

    def parse_table_state(
        self,
        table_name: str,
        schema: str,
        kind: str,
        traits: Tuple[str, ...],
        raw: Optional[Dict[str, Any]] = None,
    ) -> TableState:
        """Assemble the neutral table state.

        SQLite stores no table comments and has no partitioning, so the
        comment stays empty and the partition state is an empty
        :class:`PartitionState` whose ``scheme`` is ``None`` -- never ``None``
        itself, which is not an answer.
        """
        return TableState(
            name=table_name,
            schema=schema,
            kind=kind,
            traits=traits,
            storage=StorageOptionsState(),
            comment=None,
            partitioning=PartitionState(),
            raw=raw or {},
        )

    def parse_index_states(
        self,
        index_rows: List[Dict[str, Any]],
        table_name: str,
        schema: str,
        predicates: Optional[Dict[str, str]] = None,
    ) -> List[IndexState]:
        """Turn ``PRAGMA index_list`` rows into neutral index states.

        SQLite has one index method (btree) and no unusable or invisible
        index state, so ``usable`` and ``visible`` are true by fact rather
        than by assumption. A partial index's predicate is read from its
        DDL, which is the only place the engine keeps the ``WHERE``.
        """
        predicates = predicates or {}
        states: List[IndexState] = []
        for row in index_rows:
            name = row.get("name")
            if not name:
                continue
            states.append(
                IndexState(
                    name=name,
                    table=table_name,
                    schema=schema,
                    unique=bool(row.get("unique", 0)),
                    method="btree",
                    predicate=predicates.get(name),
                    visible=True,
                    usable=True,
                    backs_constraint=None,
                    raw={
                        "origin": row.get("origin", "c"),
                        "autoindex": name.startswith("sqlite_autoindex_"),
                        "partial": bool(row.get("partial", 0)),
                    },
                )
            )
        return states

    def sequence_rows_statement(self, schema: str) -> Tuple[str, tuple]:
        """The SELECT that reads one database's ``sqlite_sequence`` rows.

        There is no pragma for it: ``sqlite_sequence`` is an ordinary table
        the engine creates, so the question is a SELECT over it. The schema
        is placed as the existing statement factories place it, because
        ``main`` and ``temp`` each have their own sequence table.
        """
        from rhosocial.activerecord.backend.expression import Column, QueryStatement
        from rhosocial.activerecord.backend.expression.sources import (
            NamedRelationRef,
        )
        from ..expression import SQLiteTable

        return cast(
            Tuple[str, tuple],
            QueryStatement(
                self.dialect,
                select=[Column(self.dialect, "name"), Column(self.dialect, "seq")],
                from_=NamedRelationRef(
                    self.dialect,
                    SQLiteTable(
                        self.dialect,
                        "sqlite_sequence",
                        schema_name=schema,
                        schema_need_quote=False,
                        name_need_quote=False,
                    ),
                ),
            ).to_sql(),
        )

    def parse_sequence_states(
        self,
        rows: List[Dict[str, Any]],
        schema: str,
    ) -> List[SequenceState]:
        """Turn ``sqlite_sequence`` rows into neutral sequence states.

        Each row is the AUTOINCREMENT counter of one table, so the table's
        name is the only identifier the engine gives it. The counter's last
        value is carried in ``raw``; ``start`` and ``increment`` stay unset
        because SQLite stores neither.
        """
        states: List[SequenceState] = []
        for row in rows:
            name = row.get("name")
            if not name:
                continue
            last_value: Optional[int] = None
            raw_value = row.get("seq")
            if raw_value is not None:
                try:
                    last_value = int(raw_value)
                except (TypeError, ValueError):
                    last_value = None
            states.append(
                SequenceState(
                    name=name,
                    schema=schema,
                    owned_by=name,
                    start=None,
                    increment=None,
                    raw={
                        "source": "sqlite_sequence",
                        "last_value": last_value,
                    },
                )
            )
        return states

    @staticmethod
    def _group_at(text: str, open_index: int) -> Optional[Tuple[str, int]]:
        """The balanced ``(...)`` group opening at *open_index*.

        Returns the contents and the index of the closing parenthesis, or
        ``None`` when no group opens there or it never closes.
        """
        if open_index < 0 or open_index >= len(text) or text[open_index] != "(":
            return None
        depth = 0
        for index in range(open_index, len(text)):
            char = text[index]
            if char == "(":
                depth += 1
            elif char == ")":
                depth -= 1
                if depth == 0:
                    return text[open_index + 1:index], index
        return None

    @staticmethod
    def declared_constraint_name(
        prefix: str, masked_prefix: Optional[str] = None
    ) -> Optional[str]:
        """The name a ``CONSTRAINT name`` clause gives, read from *prefix*.

        The prefix is everything before the constraint keyword, so this
        cannot accidentally name a later clause. Quoted spellings are
        unwrapped; an unquoted name is read as one word. The keyword itself
        is located in *masked_prefix* when one is given, because a quoted
        default before the clause must not be read as the keyword.
        """
        search_text = masked_prefix if masked_prefix is not None else prefix
        at = find_word(search_text, "CONSTRAINT", ignore_case=True)
        if at == -1:
            return None
        rest = prefix[at + len("CONSTRAINT"):].strip()
        if not rest:
            return None
        opener = rest[0]
        if opener in "\"'`":
            close = rest.find(opener, 1)
            return rest[1:close] if close != -1 else None
        if opener == "[":
            close = rest.find("]", 1)
            return rest[1:close] if close != -1 else None
        return leading_word(rest) or None

    @staticmethod
    def _split_definitions(text: str) -> List[str]:
        """Split a table body at top-level commas, respecting quotes.

        ``split_top_level`` counts brackets but not quotes, which is enough
        for type grammars and not for a declaration where a default is a
        string containing a comma. The quoted run is skipped here, so a
        comma inside ``'a,b'`` does not divide two definitions.
        """
        parts: List[str] = []
        depth = 0
        start = 0
        quote: Optional[str] = None
        index = 0
        while index < len(text):
            char = text[index]
            if quote is not None:
                if char == quote:
                    if (
                        index + 1 < len(text)
                        and text[index + 1] == quote
                        and quote in ("'", '"', "`")
                    ):
                        index += 2
                        continue
                    quote = None
            elif char in "'\"`":
                quote = char
            elif char == "[":
                quote = "]"
            elif char in "([{":
                depth += 1
            elif char in ")]}":
                if depth:
                    depth -= 1
            elif char == "," and depth == 0:
                parts.append(text[start:index])
                start = index + 1
            index += 1
        parts.append(text[start:])
        return parts

    @staticmethod
    def _mask_quoted(text: str) -> str:
        """A copy of *text* with every quoted run replaced by spaces.

        The length is preserved, so an index found in the masked copy still
        points at the same character of the original. This is how the CHECK
        keyword and its parenthesis are found without a quoted default such
        as ``DEFAULT 'CHECK(1)'`` being read as a constraint.
        """
        masked: List[str] = []
        quote: Optional[str] = None
        index = 0
        while index < len(text):
            char = text[index]
            if quote is not None:
                masked.append(" ")
                if char == quote:
                    if (
                        index + 1 < len(text)
                        and text[index + 1] == quote
                        and quote in ("'", '"', "`")
                    ):
                        masked.append(" ")
                        index += 2
                        continue
                    quote = None
            elif char in "'\"`":
                quote = char
                masked.append(" ")
            elif char == "[":
                quote = "]"
                masked.append(" ")
            else:
                masked.append(char)
            index += 1
        return "".join(masked)

    def parse_check_constraints(
        self,
        ddl: Optional[str],
        table_name: str,
    ) -> List[Dict[str, Any]]:
        """Every ``CHECK`` expression in the table's declaration.

        No pragma returns a check constraint: its expression exists only in
        the stored ``CREATE TABLE`` text. The definition list is split at
        top level so a comma inside an expression does not divide it, and
        each ``CHECK`` is read with its own balanced parentheses; quoted
        text is masked first so a default mentioning ``CHECK`` is not read
        as a constraint.

        An unnamed check gets a deterministic label because the engine has
        no name for it; ``named`` records whether the DDL supplied one, so
        a caller can tell the two apart.
        """
        results: List[Dict[str, Any]] = []
        body = parenthesised(ddl) if ddl else None
        if body is None:
            return results
        ordinal = 0
        for part in self._split_definitions(body):
            masked = self._mask_quoted(part)
            search = 0
            while True:
                at = find_word(masked, "CHECK", ignore_case=True, start=search)
                if at == -1:
                    break
                open_index = at + len("CHECK")
                while open_index < len(masked) and masked[open_index].isspace():
                    open_index += 1
                group = self._group_at(masked, open_index)
                if group is None:
                    # ``CHECK`` without a group is not a check constraint;
                    # do not invent an expression for it.
                    break
                _, close = group
                expression = part[open_index + 1:close].strip()
                ordinal += 1
                declared = self.declared_constraint_name(
                    part[:at], masked[:at]
                )
                results.append(
                    {
                        "name": declared or f"check_{table_name}_{ordinal}",
                        "expression": expression,
                        "named": declared is not None,
                        "table_constraint": masked.lstrip()
                        .upper()
                        .startswith(("CHECK", "CONSTRAINT")),
                    }
                )
                search = close + 1
        return results

    def parse_constraint_states(
        self,
        table_name: str,
        schema: str,
        column_rows: List[Dict[str, Any]],
        index_rows: List[Dict[str, Any]],
        index_columns: Dict[str, List[str]],
        fk_rows: List[Dict[str, Any]],
        ddl: Optional[str],
        foreign_keys_enabled: bool,
    ) -> List[ConstraintState]:
        """Reduce pragma rows and the DDL into neutral constraint states.

        Primary keys come from ``PRAGMA table_xinfo``; unique constraints
        from the ``u`` origin of ``PRAGMA index_list``; foreign keys from
        ``PRAGMA foreign_key_list``; checks from the declaration because no
        pragma reports them. SQLite names only the autoindex a unique
        constraint creates, so the other three get deterministic labels and
        their ``raw`` entry says the engine gave no name.

        A foreign key's effective enforcement is the connection's
        ``PRAGMA foreign_keys`` switch, not a per-constraint attribute,
        which is why every foreign key reports the same answer.
        """
        states: List[ConstraintState] = []

        pk_rows = sorted(
            (row for row in column_rows if row.get("pk", 0) > 0),
            key=lambda row: row.get("pk", 0),
        )
        if pk_rows:
            pk_columns = [row.get("name") for row in pk_rows if row.get("name")]
            pk_index = next(
                (row.get("name") for row in index_rows if row.get("origin") == "pk"),
                None,
            )
            states.append(
                ConstraintState(
                    name=f"pk_{table_name}",
                    table=table_name,
                    kind="primary_key",
                    schema=schema,
                    backing_index=pk_index,
                    raw={
                        "columns": pk_columns,
                        "source": "table_xinfo",
                    },
                )
            )

        for row in index_rows:
            if row.get("origin") != "u":
                continue
            name = row.get("name")
            if not name:
                continue
            states.append(
                ConstraintState(
                    name=name,
                    table=table_name,
                    kind="unique",
                    schema=schema,
                    backing_index=name,
                    raw={
                        "columns": index_columns.get(name, []),
                        "origin": "u",
                        "autoindex": name.startswith("sqlite_autoindex_"),
                    },
                )
            )

        for check in self.parse_check_constraints(ddl, table_name):
            states.append(
                ConstraintState(
                    name=check["name"],
                    table=table_name,
                    kind="check",
                    schema=schema,
                    raw={
                        "expression": check["expression"],
                        "named": check["named"],
                        "table_constraint": check["table_constraint"],
                    },
                )
            )

        for fk in self.parse_foreign_keys(fk_rows, table_name, schema):
            states.append(
                ConstraintState(
                    name=fk.name,
                    table=table_name,
                    kind="foreign_key",
                    schema=schema,
                    enforced=foreign_keys_enabled,
                    raw={
                        "referenced_table": fk.referenced_table,
                        "columns": list(fk.columns),
                        "referenced_columns": list(fk.referenced_columns),
                        "on_update": fk.on_update.value,
                        "on_delete": fk.on_delete.value,
                        "foreign_keys_pragma": foreign_keys_enabled,
                    },
                )
            )
        return states

    def parse_derived_objects(
        self,
        table_name: str,
        ddl: Optional[str],
        index_rows: List[Dict[str, Any]],
    ) -> List[DerivedObjectState]:
        """The objects SQLite created for this table's declaration.

        ``sqlite_autoindex_*`` rows are the indexes a PRIMARY KEY or UNIQUE
        clause made without being asked; ``sqlite_sequence`` appears once
        the declaration says AUTOINCREMENT, even before it holds a row.
        """
        derived: List[DerivedObjectState] = []
        if ddl and has_word(
            self._mask_quoted(ddl), "AUTOINCREMENT", ignore_case=True
        ):
            derived.append(
                DerivedObjectState(
                    kind="identity_sequence",
                    name="sqlite_sequence",
                    owned_by=table_name,
                    raw={"shared_table": True},
                )
            )
        for row in index_rows:
            name = row.get("name")
            if not name or not name.startswith("sqlite_autoindex_"):
                continue
            derived.append(
                DerivedObjectState(
                    kind="autoindex",
                    name=name,
                    owned_by=table_name,
                    raw={"origin": row.get("origin", "")},
                )
            )
        return derived


    def get_database_info(self) -> IntrospectionDatabaseInfo:
        """Answer the version, the encoding, the file extent and the table count.

        Core's version asks one question and parses its row. SQLite's answer
        also lives in three pragmas and a count, so this gathers them and hands
        the same dict to the same parser the async twin uses -- which is what
        keeps the two directions from disagreeing about the values.
        """
        key = self._cache.key(IntrospectionScope.DATABASE)
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        sql, params = self.database_info_statement().to_sql()
        rows = self._executor.execute(sql, params)
        values = self._collect_database_pragmas()
        values["table_count"] = self._count_tables()
        result = self.parse_database_info(rows, values)
        self._cache.set(key, result)
        return result

    def _count_tables(self) -> Optional[int]:
        """How many tables this database declares, system ones excluded."""
        sql, params = SQLiteTableCountStatement(
            self.dialect, self.default_schema
        ).to_sql()
        return self.parse_table_count(self._executor.execute(sql, params))

    def parse_table_count(self, rows: List[Dict[str, Any]]) -> Optional[int]:
        """Read the count from the single row ``COUNT(*)`` returns."""
        if not rows:
            return None
        try:
            return int(rows[0]["table_count"])
        except (KeyError, TypeError, ValueError):
            return None


class SQLiteIntrospector(SQLiteIntrospectorMixin, AbstractIntrospector):
    """Synchronous introspector for SQLite backends.

    In addition to the standard AbstractIntrospector interface, exposes the
    `.pragma` sub-introspector for direct PRAGMA access::

        # Standard API
        tables = backend.introspector.list_tables()

        # SQLite-specific
        mode = backend.introspector.pragma.get("journal_mode")
        backend.introspector.pragma.set("journal_mode", "WAL")
        errors = backend.introspector.pragma.integrity_check()
    """

    def __init__(
        self,
        backend: Any,
        executor: IntrospectorExecutor,
        cache: Optional[IntrospectionCache] = None,
    ) -> None:
        super().__init__(backend, executor, cache)
        self._pragma_instance: Optional[PragmaIntrospector] = None
        self._status_instance: Optional[SQLiteStatusIntrospector] = None

    @property
    def pragma(self) -> PragmaIntrospector:
        """SQLite-specific PRAGMA sub-introspector (lazily created)."""
        if self._pragma_instance is None:
            self._pragma_instance = PragmaIntrospector(self._backend, self._executor)
        return self._pragma_instance

    @property
    def status(self) -> SQLiteStatusIntrospector:
        """SQLite status introspector (lazily created)."""
        if self._status_instance is None:
            self._status_instance = SQLiteStatusIntrospector(self._backend)
        return self._status_instance



    # ------------------------------------------------------------------ #
    # Per-table storage: one dbstat read, one index-ownership read, and the
    # shared reducer that attributes the bytes.
    # ------------------------------------------------------------------ #

    def collect_table_storage(
        self, schema: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """The two row sets the storage reducer needs, or two empty ones.

        Empty rather than an error when the build has no ``dbstat``: the
        family is not answerable here, and the reducer keeps every slot
        ``None`` -- the same answer a caller sees for an unsupported family
        on any other backend, arrived at without raising.
        """
        if not self.dialect.supports_table_storage_introspection():
            return [], []
        storage_sql, storage_params = SQLiteTableStorageStatement(self.dialect, schema).to_sql()
        owner_sql, owner_params = SQLiteIndexOwnerStatement(self.dialect, schema).to_sql()
        return (
            self._executor.execute(storage_sql, storage_params),
            self._executor.execute(owner_sql, owner_params),
        )

    def list_tables(
        self,
        schema: Optional[str] = None,
        include_system: bool = False,
        table_type: Optional[str] = None,
    ) -> List[IntrospectionTableInfo]:
        """List tables, with the storage slots filled where this build can.

        The base flow asks one question and parses its rows; this override
        adds the two storage questions beside it, gated by the dialect's
        ``supports_table_storage_introspection``. A build without ``dbstat``
        answers the same list with the slots left ``None`` -- one code path,
        one cache key, no second shape.
        """
        key = self._cache.key(
            IntrospectionScope.TABLE,
            schema=schema,
            extra=f"{include_system}:{table_type}",
        )
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        sql, params = self.table_list_statement(
            schema=schema,
            include_system=include_system,
            include_views=True,
            table_type=table_type,
        ).to_sql()
        tables = self.parse_tables(self._executor.execute(sql, params), schema)
        storage_rows, index_rows = self.collect_table_storage(schema)
        tables = self.parse_table_storage(tables, storage_rows, index_rows)
        self._cache.set(key, tables)
        return tables

    # ------------------------------------------------------------------ #
    # Override list_columns for auto-increment detection
    # ------------------------------------------------------------------ #

    def list_columns(self, table_name: str, schema: Optional[str] = None) -> List[IntrospectionColumnInfo]:
        """List columns, with auto-increment detection from DDL."""
        target_db = schema or self.default_schema
        key = self._cache.key(IntrospectionScope.COLUMN, table_name, schema=schema)
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        sql, params = self.column_info_statement(
            table_name=table_name, schema=schema, include_hidden=True
        ).to_sql()
        rows = self._executor.execute(sql, params)

        # Query the DDL for AUTOINCREMENT detection, and the index pragmas for
        # uniqueness: neither fact is on the column row.
        ddl = None
        ddl_sql, ddl_params = SQLiteTableDdlStatement(self.dialect, table_name).to_sql()
        ddl_result = self._executor.execute(ddl_sql, ddl_params)
        if ddl_result and ddl_result[0].get("sql"):
            ddl = ddl_result[0]["sql"]

        unique_columns = self._collect_unique_columns(table_name, target_db)

        result = self.parse_columns(
            rows, table_name, target_db, ddl=ddl, unique_columns=unique_columns
        )
        self._cache.set(key, result)
        return result

    # ------------------------------------------------------------------ #
    # Override list_indexes for SQLite's two-step index query
    # ------------------------------------------------------------------ #

    def list_indexes(self, table_name: str, schema: Optional[str] = None) -> List[IndexInfo]:
        """List all indexes of the given table.

        SQLite requires two queries:
        1. PRAGMA index_list(table) - get index list
        2. PRAGMA index_xinfo(index) - get column info for each index
        """
        target_db = schema or self.default_schema
        key = self._cache.key(IntrospectionScope.INDEX, table_name, schema=schema)
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        # Step 1: Get index list
        index_rows = self.pragma.index_list(table_name, target_db)
        if not index_rows:
            return []

        indexes: List[IndexInfo] = []
        for idx_row in index_rows:
            idx_name = idx_row.get("name", "")
            is_unique = bool(idx_row.get("unique", 0))
            is_primary = False  # Will be set based on origin below
            origin = idx_row.get("origin", "c")

            # Map origin to index type
            if origin == "pk":
                is_primary = True
                idx_type = IndexType.BTREE
            elif origin == "u":
                is_unique = True
                idx_type = IndexType.BTREE
            else:
                idx_type = IndexType.BTREE

            # Step 2: Get column info for this index
            col_rows = self.pragma.index_xinfo(idx_name, target_db)
            columns: List[IndexColumnInfo] = []
            is_partial = False
            for col_row in col_rows:
                col_name = col_row.get("name")
                if col_name:
                    columns.append(
                        IndexColumnInfo(
                            name=col_name,
                            ordinal_position=col_row.get("seqno", 0) + 1,
                            is_descending=bool(col_row.get("desc", 0)),
                        )
                    )
                else:
                    is_partial = True

            # For partial indexes, extract filter_condition from DDL
            filter_condition: Optional[str] = None
            if is_partial:
                index_ddl, index_params = SQLiteIndexDdlStatement(self.dialect, idx_name).to_sql()
                ddl_result = self._executor.execute(index_ddl, index_params)
                if ddl_result and ddl_result[0].get("sql"):
                    ddl_sql = ddl_result[0]["sql"]
                    where_at = find_word(ddl_sql, "WHERE", ignore_case=True)
                    if where_at != -1:
                        filter_condition = ddl_sql[where_at + len("WHERE"):].strip().rstrip(';')

            indexes.append(
                IndexInfo(
                    name=idx_name,
                    table_name=table_name,
                    schema=target_db,
                    is_unique=is_unique,
                    is_primary=is_primary,
                    index_type=idx_type,
                    columns=columns,
                    filter_condition=filter_condition,
                    extra={"origin": origin},
                )
            )

        self._cache.set(key, indexes)
        return indexes

    # ------------------------------------------------------------------ #
    # Neutral object state — sync I/O. The reductions live in the mixin so
    # the async twin cannot answer a different fact from the same rows.
    # ------------------------------------------------------------------ #

    def _table_ddl_row(
        self, table_name: str, schema: str
    ) -> Optional[Dict[str, Any]]:
        """The ``sqlite_master`` row a table's declaration was read from."""
        sql, params = SQLiteTableDdlStatement(
            self.dialect, table_name, schema
        ).to_sql()
        rows = self._executor.execute(sql, params)
        return rows[0] if rows else None

    def _table_exists(self, table_name: str, schema: str) -> bool:
        """Whether a table exists, preferring the pragma that needs no DDL."""
        if self._use_table_list():
            return any(
                row.get("name") == table_name
                for row in self.pragma.table_list(schema)
            )
        return self._table_ddl_row(table_name, schema) is not None

    def _sequence_rows(self, schema: str) -> List[Dict[str, Any]]:
        """Read one database's ``sqlite_sequence`` rows."""
        sql, params = self.sequence_rows_statement(schema)
        rows: List[Dict[str, Any]] = self._executor.execute(sql, params)
        return rows

    def _schema_candidates(self, schema: Optional[str]) -> List[str]:
        """Resolution order for an unqualified name, from the live schemas."""
        return self.ordered_schema_names(self.list_schemas(), schema)

    def _state_schema(
        self, table_name: str, schema: Optional[str] = None
    ) -> Optional[str]:
        """The schema the table actually lives in, or ``None``."""
        if schema is not None:
            return schema
        if self._use_table_list():
            rows = self.pragma.table_list()
            row = self.select_table_row(rows, table_name)
            return row.get("schema") if row else None
        for candidate in self._schema_candidates(None):
            if self._table_ddl_row(table_name, candidate) is not None:
                return candidate
        return None

    def get_table_state(
        self,
        table_name: str,
        schema: Optional[str] = None,
    ) -> TableState:
        """Read the table's kind and storage traits.

        SQLite has no table comments and no partitioning, so both answer
        empty; a table's ``STRICT`` and ``WITHOUT ROWID`` options are the
        only storage traits it has.
        """
        target = self._state_schema(table_name, schema)
        if target is None:
            raise ObjectNotFoundError("Table", table_name, schema)

        row: Optional[Dict[str, Any]] = None
        ddl_row: Optional[Dict[str, Any]] = None
        if self._use_table_list():
            row = self.select_table_row(
                self.pragma.table_list(target), table_name, target
            )
        if row is None:
            ddl_row = self._table_ddl_row(table_name, target)
            if ddl_row is None:
                raise ObjectNotFoundError("Table", table_name, schema)

        table_type = row.get("type") if row else None
        traits = self.parse_table_traits(
            ddl_row.get("sql") if ddl_row else None,
            bool(row.get("wr", 0)) if row else None,
            bool(row.get("strict", 0)) if row else None,
        )
        raw: Dict[str, Any] = {}
        if row:
            raw["table_type"] = row.get("type")
            raw["ncol"] = row.get("ncol")
        return self.parse_table_state(
            table_name,
            target,
            self.table_kind(target, table_type),
            traits,
            raw,
        )

    def get_partition_state(
        self,
        table_name: str,
        schema: Optional[str] = None,
        include_stats: bool = False,
    ) -> PartitionState:
        """``scheme=None``: SQLite has no partitioning.

        The table is still resolved and its existence checked, so a missing
        table is reported rather than read as an unpartitioned one.
        """
        self.get_table_state(table_name, schema)
        return PartitionState(scheme=None)

    def list_index_states(
        self,
        table_name: str,
        schema: Optional[str] = None,
    ) -> List[IndexState]:
        """Read every index, including autoindexes and partial predicates."""
        target = self._state_schema(table_name, schema)
        if target is None:
            return []
        index_rows = self.pragma.index_list(table_name, target)
        predicates: Dict[str, str] = {}
        for row in index_rows:
            if not row.get("partial"):
                continue
            name = row.get("name")
            if not name:
                continue
            sql, params = SQLiteIndexDdlStatement(self.dialect, name, target).to_sql()
            rows = self._executor.execute(sql, params)
            if not rows or not rows[0].get("sql"):
                continue
            where_at = find_word(rows[0]["sql"], "WHERE", ignore_case=True)
            if where_at != -1:
                predicates[name] = (
                    rows[0]["sql"][where_at + len("WHERE"):].strip().rstrip(";")
                )
        return self.parse_index_states(index_rows, table_name, target, predicates)

    def list_constraint_states(
        self,
        table_name: str,
        schema: Optional[str] = None,
    ) -> List[ConstraintState]:
        """Read PK, unique, check and foreign-key constraints."""
        target = self._state_schema(table_name, schema)
        if target is None:
            return []
        if getattr(self.dialect, "supports_table_xinfo_pragma", lambda: False)():
            column_rows = self.pragma.table_xinfo(table_name, target)
        else:
            column_rows = self.pragma.table_info(table_name, target)
        index_rows = self.pragma.index_list(table_name, target)
        index_columns: Dict[str, List[str]] = {}
        for row in index_rows:
            name = row.get("name")
            if not name:
                continue
            if getattr(
                self.dialect, "supports_index_xinfo_pragma", lambda: False
            )():
                xinfo = self.pragma.index_xinfo(name, target)
            else:
                xinfo = self.pragma.index_info(name, target)
            index_columns[name] = [
                str(col["name"]) for col in xinfo if col.get("name")
            ]
        fk_rows = self.pragma.foreign_key_list(table_name, target)
        ddl_row = self._table_ddl_row(table_name, target)
        fk_enabled = bool(
            self._pragma_value(self.pragma.get("foreign_keys"), "foreign_keys")
        )
        return self.parse_constraint_states(
            table_name,
            target,
            column_rows,
            index_rows,
            index_columns,
            fk_rows,
            ddl_row.get("sql") if ddl_row else None,
            fk_enabled,
        )

    def list_sequence_states(
        self,
        schema: Optional[str] = None,
    ) -> List[SequenceState]:
        """Read the AUTOINCREMENT counters the schema holds."""
        target = schema or self.default_schema
        if not self._table_exists("sqlite_sequence", target):
            return []
        return self.parse_sequence_states(self._sequence_rows(target), target)

    def list_schemas(self) -> List[str]:
        """The database names SQLite exposes: main, temp and attached.

        ``PRAGMA database_list`` omits ``temp`` until it holds an object,
        although a temp table can be created at any time; the namespace is
        therefore reported even when the pragma does not name it.
        """
        rows = sorted(
            self.pragma.execute("database_list"),
            key=lambda row: row.get("seq", 0),
        )
        names = [row["name"] for row in rows if row.get("name")]
        ordered = ["main"]
        if "temp" in names:
            ordered.append("temp")
        ordered.extend(name for name in names if name not in ("main", "temp"))
        if "temp" not in ordered:
            ordered.insert(1, "temp")
        return ordered

    def list_derived_objects(
        self,
        table_name: str,
        schema: Optional[str] = None,
    ) -> List[DerivedObjectState]:
        """Read the autoindexes and sequence row the declaration produced."""
        target = self._state_schema(table_name, schema)
        if target is None:
            return []
        ddl_row = self._table_ddl_row(table_name, target)
        if ddl_row is None:
            return []
        index_rows = self.pragma.index_list(table_name, target)
        return self.parse_derived_objects(
            table_name, ddl_row.get("sql"), index_rows
        )

    def item_exists(
        self,
        kind: ItemKind,
        name: str,
        schema: Optional[str] = None,
    ) -> bool:
        """Whether a table, index or sequence of this name exists.

        Types, functions, extensions, tablespaces and the like are not
        named objects in SQLite, so they answer False. A sequence is either
        the ``sqlite_sequence`` table itself or one of its per-table rows.
        """
        if kind == ItemKind.SCHEMA:
            return name in self.list_schemas()
        candidates = self._schema_candidates(schema)
        if kind == ItemKind.TABLE:
            return any(
                self._table_exists(name, candidate)
                for candidate in candidates
            )
        if kind == ItemKind.INDEX:
            for candidate in candidates:
                sql, params = SQLiteIndexDdlStatement(
                    self.dialect, name, candidate
                ).to_sql()
                if self._executor.execute(sql, params):
                    return True
            return False
        if kind == ItemKind.SEQUENCE:
            for candidate in candidates:
                if not self._table_exists("sqlite_sequence", candidate):
                    continue
                if name == "sqlite_sequence":
                    return True
                if any(
                    row.get("name") == name
                    for row in self._sequence_rows(candidate)
                ):
                    return True
            return False
        return False

    # ------------------------------------------------------------------ #
    # get_table_info override — parses rows directly instead of calling
    # list_tables() again, and populates columns/indexes/FKs in one sweep.
    # ------------------------------------------------------------------ #

    def get_table_info(self, table_name: str, schema: Optional[str] = None) -> Optional[IntrospectionTableInfo]:
        key = self._cache.key(IntrospectionScope.TABLE, table_name, schema=schema)
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        tables = self.list_tables(schema)
        table = next((t for t in tables if t.name == table_name), None)
        if table is None:
            return None

        # Copy to avoid mutating the object stored in the list_tables() cache
        table = copy.copy(table)
        table.columns = self.list_columns(table_name, schema)
        table.indexes = self.list_indexes(table_name, schema)
        table.foreign_keys = self.list_foreign_keys(table_name, schema)
        self._cache.set(key, table)
        return table



class AsyncSQLiteIntrospector(SQLiteIntrospectorMixin, AsyncAbstractIntrospector):
    """Asynchronous introspector for SQLite backends.

    In addition to the standard AsyncAbstractIntrospector interface, exposes the
    `.pragma` sub-introspector for direct PRAGMA access::

        # Standard API
        tables = await backend.introspector.list_tables()

        # SQLite-specific
        mode = await backend.introspector.pragma.get("journal_mode")
        await backend.introspector.pragma.set("journal_mode", "WAL")
        errors = await backend.introspector.pragma.integrity_check()
    """

    def __init__(
        self,
        backend: Any,
        executor: AsyncIntrospectorExecutor,
        cache: Optional[IntrospectionCache] = None,
    ) -> None:
        super().__init__(backend, executor, cache)
        self._pragma_instance: Optional[AsyncPragmaIntrospector] = None
        self._status_instance: Optional[AsyncSQLiteStatusIntrospector] = None

    @property
    def pragma(self) -> AsyncPragmaIntrospector:
        """SQLite-specific PRAGMA sub-introspector (lazily created)."""
        if self._pragma_instance is None:
            self._pragma_instance = AsyncPragmaIntrospector(self._backend, self._executor)
        return self._pragma_instance

    @property
    def status(self) -> AsyncSQLiteStatusIntrospector:
        """SQLite status introspector (lazily created)."""
        if self._status_instance is None:
            self._status_instance = AsyncSQLiteStatusIntrospector(self._backend)
        return self._status_instance

    async def get_database_info(self) -> IntrospectionDatabaseInfo:
        """The async twin of :meth:`SQLiteIntrospector.get_database_info`.

        Same questions, awaited, and the same :meth:`parse_database_info`
        reduction -- so the two directions cannot report different encodings or
        different sizes for one database.
        """
        key = self._cache.key(IntrospectionScope.DATABASE)
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        sql, params = self.database_info_statement().to_sql()
        rows = await self._executor.execute(sql, params)
        values: Dict[str, Any] = {}
        for name in self._DATABASE_PRAGMAS:
            values[name] = self._pragma_value(await self.pragma.get(name), name)
        values["table_count"] = await self._count_tables_async()
        result = self.parse_database_info(rows, values)
        self._cache.set(key, result)
        return result

    async def _count_tables_async(self) -> Optional[int]:
        sql, params = SQLiteTableCountStatement(
            self.dialect, self.default_schema
        ).to_sql()
        return self.parse_table_count(await self._executor.execute(sql, params))

    # ------------------------------------------------------------------ #
    # Per-table storage: the async twin of the sync pair above.
    # ------------------------------------------------------------------ #

    async def collect_table_storage(
        self, schema: Optional[str] = None
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """The async twin of :meth:`SQLiteIntrospector.collect_table_storage`.

        Same two statements, awaited; the same empty-pair answer when the
        build has no ``dbstat``, so the async and sync reductions see the
        same inputs and cannot disagree.
        """
        if not self.dialect.supports_table_storage_introspection():
            return [], []
        storage_sql, storage_params = SQLiteTableStorageStatement(self.dialect, schema).to_sql()
        owner_sql, owner_params = SQLiteIndexOwnerStatement(self.dialect, schema).to_sql()
        return (
            await self._executor.execute(storage_sql, storage_params),
            await self._executor.execute(owner_sql, owner_params),
        )

    async def list_tables(
        self,
        schema: Optional[str] = None,
        include_system: bool = False,
        table_type: Optional[str] = None,
    ) -> List[IntrospectionTableInfo]:
        """The async twin of :meth:`SQLiteIntrospector.list_tables`.

        Same questions awaited, same reducer, same cache key: one direction
        of the pair fills the storage slots and the other cannot answer them
        differently.
        """
        key = self._cache.key(
            IntrospectionScope.TABLE,
            schema=schema,
            extra=f"{include_system}:{table_type}",
        )
        cached = self._cache.get(key)
        if cached is not None:
            return cached
        sql, params = self.table_list_statement(
            schema=schema,
            include_system=include_system,
            include_views=True,
            table_type=table_type,
        ).to_sql()
        tables = self.parse_tables(await self._executor.execute(sql, params), schema)
        storage_rows, index_rows = await self.collect_table_storage(schema)
        tables = self.parse_table_storage(tables, storage_rows, index_rows)
        self._cache.set(key, tables)
        return tables

    # ------------------------------------------------------------------ #
    # Override list_columns for auto-increment detection
    # ------------------------------------------------------------------ #

    async def list_columns(self, table_name: str, schema: Optional[str] = None) -> List[IntrospectionColumnInfo]:
        """List columns, with auto-increment detection from DDL."""
        target_db = schema or self.default_schema
        key = self._cache.key(IntrospectionScope.COLUMN, table_name, schema=schema)
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        sql, params = self.column_info_statement(
            table_name=table_name, schema=schema, include_hidden=True
        ).to_sql()
        rows = await self._executor.execute(sql, params)

        # Query the DDL for AUTOINCREMENT detection
        ddl = None
        ddl_sql, ddl_params = SQLiteTableDdlStatement(self.dialect, table_name).to_sql()
        ddl_result = await self._executor.execute(ddl_sql, ddl_params)
        if ddl_result and ddl_result[0].get("sql"):
            ddl = ddl_result[0]["sql"]

        unique_columns = await self._collect_unique_columns_async(table_name, target_db)

        result = self.parse_columns(
            rows, table_name, target_db, ddl=ddl, unique_columns=unique_columns
        )
        self._cache.set(key, result)
        return result

    # ------------------------------------------------------------------ #
    # Override list_indexes for SQLite's two-step index query
    # ------------------------------------------------------------------ #

    async def list_indexes(self, table_name: str, schema: Optional[str] = None) -> List[IndexInfo]:
        """List all indexes of the given table.

        SQLite requires two queries:
        1. PRAGMA index_list(table) - get index list
        2. PRAGMA index_xinfo(index) - get column info for each index
        """
        target_db = schema or self.default_schema
        key = self._cache.key(IntrospectionScope.INDEX, table_name, schema=schema)
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        # Step 1: Get index list
        index_rows = await self.pragma.index_list(table_name, target_db)
        if not index_rows:
            return []

        indexes: List[IndexInfo] = []
        for idx_row in index_rows:
            idx_name = idx_row.get("name", "")
            is_unique = bool(idx_row.get("unique", 0))
            is_primary = False  # Will be set based on origin below
            origin = idx_row.get("origin", "c")

            # Map origin to index type
            if origin == "pk":
                is_primary = True
                idx_type = IndexType.BTREE
            elif origin == "u":
                is_unique = True
                idx_type = IndexType.BTREE
            else:
                idx_type = IndexType.BTREE

            # Step 2: Get column info for this index
            col_rows = await self.pragma.index_xinfo(idx_name, target_db)
            columns: List[IndexColumnInfo] = []
            is_partial = False
            for col_row in col_rows:
                col_name = col_row.get("name")
                if col_name:
                    columns.append(
                        IndexColumnInfo(
                            name=col_name,
                            ordinal_position=col_row.get("seqno", 0) + 1,
                            is_descending=bool(col_row.get("desc", 0)),
                        )
                    )
                else:
                    is_partial = True

            # For partial indexes, extract filter_condition from DDL
            filter_condition: Optional[str] = None
            if is_partial:
                index_ddl, index_params = SQLiteIndexDdlStatement(self.dialect, idx_name).to_sql()
                ddl_result = await self._executor.execute(index_ddl, index_params)
                if ddl_result and ddl_result[0].get("sql"):
                    ddl_sql = ddl_result[0]["sql"]
                    where_at = find_word(ddl_sql, "WHERE", ignore_case=True)
                    if where_at != -1:
                        filter_condition = ddl_sql[where_at + len("WHERE"):].strip().rstrip(';')

            indexes.append(
                IndexInfo(
                    name=idx_name,
                    table_name=table_name,
                    schema=target_db,
                    is_unique=is_unique,
                    is_primary=is_primary,
                    index_type=idx_type,
                    columns=columns,
                    filter_condition=filter_condition,
                    extra={"origin": origin},
                )
            )

        self._cache.set(key, indexes)
        return indexes

    # ------------------------------------------------------------------ #
    # Neutral object state — async I/O. Same questions as the sync block,
    # awaited, and the same mixin reductions; the two directions cannot
    # disagree about a table, an index or a sequence.
    # ------------------------------------------------------------------ #

    async def _table_ddl_row(
        self, table_name: str, schema: str
    ) -> Optional[Dict[str, Any]]:
        sql, params = SQLiteTableDdlStatement(
            self.dialect, table_name, schema
        ).to_sql()
        rows = await self._executor.execute(sql, params)
        return rows[0] if rows else None

    async def _table_exists(self, table_name: str, schema: str) -> bool:
        if self._use_table_list():
            return any(
                row.get("name") == table_name
                for row in await self.pragma.table_list(schema)
            )
        return await self._table_ddl_row(table_name, schema) is not None

    async def _sequence_rows(self, schema: str) -> List[Dict[str, Any]]:
        sql, params = self.sequence_rows_statement(schema)
        rows: List[Dict[str, Any]] = await self._executor.execute(sql, params)
        return rows

    async def _state_schema(
        self, table_name: str, schema: Optional[str] = None
    ) -> Optional[str]:
        if schema is not None:
            return schema
        if self._use_table_list():
            rows = await self.pragma.table_list()
            row = self.select_table_row(rows, table_name)
            return row.get("schema") if row else None
        for candidate in await self._schema_candidates(None):
            if await self._table_ddl_row(table_name, candidate) is not None:
                return candidate
        return None

    async def _schema_candidates(self, schema: Optional[str]) -> List[str]:
        """Resolution order for an unqualified name, from the live schemas.

        The sync helper reads ``self.list_schemas()`` directly; here that
        method is a coroutine, so the names are awaited before the order is
        built rather than passed as an unrun coroutine.
        """
        return self.ordered_schema_names(await self.list_schemas(), schema)

    async def get_table_state(
        self,
        table_name: str,
        schema: Optional[str] = None,
    ) -> TableState:
        """The async twin of :meth:`SQLiteIntrospector.get_table_state`."""
        target = await self._state_schema(table_name, schema)
        if target is None:
            raise ObjectNotFoundError("Table", table_name, schema)

        row: Optional[Dict[str, Any]] = None
        ddl_row: Optional[Dict[str, Any]] = None
        if self._use_table_list():
            row = self.select_table_row(
                await self.pragma.table_list(target), table_name, target
            )
        if row is None:
            ddl_row = await self._table_ddl_row(table_name, target)
            if ddl_row is None:
                raise ObjectNotFoundError("Table", table_name, schema)

        table_type = row.get("type") if row else None
        traits = self.parse_table_traits(
            ddl_row.get("sql") if ddl_row else None,
            bool(row.get("wr", 0)) if row else None,
            bool(row.get("strict", 0)) if row else None,
        )
        raw: Dict[str, Any] = {}
        if row:
            raw["table_type"] = row.get("type")
            raw["ncol"] = row.get("ncol")
        return self.parse_table_state(
            table_name,
            target,
            self.table_kind(target, table_type),
            traits,
            raw,
        )

    async def get_partition_state(
        self,
        table_name: str,
        schema: Optional[str] = None,
        include_stats: bool = False,
    ) -> PartitionState:
        """``scheme=None``: SQLite has no partitioning."""
        await self.get_table_state(table_name, schema)
        return PartitionState(scheme=None)

    async def list_index_states(
        self,
        table_name: str,
        schema: Optional[str] = None,
    ) -> List[IndexState]:
        """Read every index, including autoindexes and partial predicates."""
        target = await self._state_schema(table_name, schema)
        if target is None:
            return []
        index_rows = await self.pragma.index_list(table_name, target)
        predicates: Dict[str, str] = {}
        for row in index_rows:
            if not row.get("partial"):
                continue
            name = row.get("name")
            if not name:
                continue
            sql, params = SQLiteIndexDdlStatement(self.dialect, name, target).to_sql()
            rows = await self._executor.execute(sql, params)
            if not rows or not rows[0].get("sql"):
                continue
            where_at = find_word(rows[0]["sql"], "WHERE", ignore_case=True)
            if where_at != -1:
                predicates[name] = (
                    rows[0]["sql"][where_at + len("WHERE"):].strip().rstrip(";")
                )
        return self.parse_index_states(index_rows, table_name, target, predicates)

    async def list_constraint_states(
        self,
        table_name: str,
        schema: Optional[str] = None,
    ) -> List[ConstraintState]:
        """Read PK, unique, check and foreign-key constraints."""
        target = await self._state_schema(table_name, schema)
        if target is None:
            return []
        if getattr(self.dialect, "supports_table_xinfo_pragma", lambda: False)():
            column_rows = await self.pragma.table_xinfo(table_name, target)
        else:
            column_rows = await self.pragma.table_info(table_name, target)
        index_rows = await self.pragma.index_list(table_name, target)
        index_columns: Dict[str, List[str]] = {}
        for row in index_rows:
            name = row.get("name")
            if not name:
                continue
            if getattr(
                self.dialect, "supports_index_xinfo_pragma", lambda: False
            )():
                xinfo = await self.pragma.index_xinfo(name, target)
            else:
                xinfo = await self.pragma.index_info(name, target)
            index_columns[name] = [
                str(col["name"]) for col in xinfo if col.get("name")
            ]
        fk_rows = await self.pragma.foreign_key_list(table_name, target)
        ddl_row = await self._table_ddl_row(table_name, target)
        fk_enabled = bool(
            self._pragma_value(await self.pragma.get("foreign_keys"), "foreign_keys")
        )
        return self.parse_constraint_states(
            table_name,
            target,
            column_rows,
            index_rows,
            index_columns,
            fk_rows,
            ddl_row.get("sql") if ddl_row else None,
            fk_enabled,
        )

    async def list_sequence_states(
        self,
        schema: Optional[str] = None,
    ) -> List[SequenceState]:
        """Read the AUTOINCREMENT counters the schema holds."""
        target = schema or self.default_schema
        if not await self._table_exists("sqlite_sequence", target):
            return []
        return self.parse_sequence_states(
            await self._sequence_rows(target), target
        )

    async def list_schemas(self) -> List[str]:
        """The database names SQLite exposes: main, temp and attached."""
        rows = sorted(
            await self.pragma.execute("database_list"),
            key=lambda row: row.get("seq", 0),
        )
        names = [row["name"] for row in rows if row.get("name")]
        ordered = ["main"]
        if "temp" in names:
            ordered.append("temp")
        ordered.extend(name for name in names if name not in ("main", "temp"))
        if "temp" not in ordered:
            ordered.insert(1, "temp")
        return ordered

    async def list_derived_objects(
        self,
        table_name: str,
        schema: Optional[str] = None,
    ) -> List[DerivedObjectState]:
        """Read the autoindexes and sequence row the declaration produced."""
        target = await self._state_schema(table_name, schema)
        if target is None:
            return []
        ddl_row = await self._table_ddl_row(table_name, target)
        if ddl_row is None:
            return []
        index_rows = await self.pragma.index_list(table_name, target)
        return self.parse_derived_objects(
            table_name, ddl_row.get("sql"), index_rows
        )

    async def item_exists(
        self,
        kind: ItemKind,
        name: str,
        schema: Optional[str] = None,
    ) -> bool:
        """Whether a table, index or sequence of this name exists."""
        if kind == ItemKind.SCHEMA:
            return name in await self.list_schemas()
        candidates = await self._schema_candidates(schema)
        if kind == ItemKind.TABLE:
            for candidate in candidates:
                if await self._table_exists(name, candidate):
                    return True
            return False
        if kind == ItemKind.INDEX:
            for candidate in candidates:
                sql, params = SQLiteIndexDdlStatement(
                    self.dialect, name, candidate
                ).to_sql()
                if await self._executor.execute(sql, params):
                    return True
            return False
        if kind == ItemKind.SEQUENCE:
            for candidate in candidates:
                if not await self._table_exists("sqlite_sequence", candidate):
                    continue
                if name == "sqlite_sequence":
                    return True
                rows = await self._sequence_rows(candidate)
                if any(row.get("name") == name for row in rows):
                    return True
            return False
        return False

    # ------------------------------------------------------------------ #
    # get_table_info override — parses rows directly instead of calling
    # list_tables() again, and populates columns/indexes/FKs in one sweep.
    # ------------------------------------------------------------------ #

    async def get_table_info(self, table_name: str, schema: Optional[str] = None) -> Optional[IntrospectionTableInfo]:
        key = self._cache.key(IntrospectionScope.TABLE, table_name, schema=schema)
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        tables = await self.list_tables(schema)
        table = next((t for t in tables if t.name == table_name), None)
        if table is None:
            return None

        # Copy to avoid mutating the object stored in the list_tables() cache
        table = copy.copy(table)
        table.columns = await self.list_columns(table_name, schema)
        table.indexes = await self.list_indexes(table_name, schema)
        table.foreign_keys = await self.list_foreign_keys(table_name, schema)
        self._cache.set(key, table)
        return table
