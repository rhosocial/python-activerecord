# src/rhosocial/activerecord/backend/impl/sqlite/introspection/introspector.py
"""
SQLite concrete introspectors.

Implements SyncAbstractIntrospector and AsyncAbstractIntrospector for SQLite
databases using PRAGMA commands and the sqlite_master / sqlite_schema system
table for metadata queries.

The introspectors are exposed via ``backend.introspector`` and also provide
SQLite-specific access through ``backend.introspector.pragma``.

Key behaviours:
  - Version-aware: uses ``PRAGMA table_list`` (3.37+) or ``sqlite_master``
  - Extended column info: uses ``PRAGMA table_xinfo`` (3.26+)
  - ``_parse_*`` methods are pure Python — shared by sync and async introspectors

Design principle: Sync and Async are separate and cannot coexist.
- SyncSQLiteIntrospector: for synchronous backends
- AsyncSQLiteIntrospector: for asynchronous backends
"""

import copy
import re
import sqlite3
from typing import Any, Dict, List, Optional

from rhosocial.activerecord.backend.introspection.base import (
    IntrospectorMixin,
    SyncAbstractIntrospector,
    AsyncAbstractIntrospector,
)
from rhosocial.activerecord.backend.introspection.cache import IntrospectionCache
from rhosocial.activerecord.backend.introspection.executor import (
    SyncIntrospectorExecutor,
    AsyncIntrospectorExecutor,
)
from rhosocial.activerecord.backend.introspection.types import (
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
from .pragma_introspector import (
    SyncPragmaIntrospector,
    AsyncPragmaIntrospector,
)
from .status_introspector import (
    SyncSQLiteStatusIntrospector,
    AsyncSQLiteStatusIntrospector,
)


class SQLiteIntrospectorMixin(IntrospectorMixin):
    """Mixin providing shared SQLite-specific introspection logic.

    Both SyncSQLiteIntrospector and AsyncSQLiteIntrospector inherit
    from this mixin to share:
    - Default schema handling
    - SQLite version detection
    - SQL generation overrides
    - _parse_* implementations
    """

    def _get_default_schema(self) -> str:
        """Return the SQLite schema name for the primary database."""
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

    # Note: SQLite does NOT override _build_*_sql() methods because:
    # 1. Base class IntrospectorMixin._build_*_sql() delegates to Expression.to_sql()
    # 2. Expression.to_sql() calls Dialect.format_*_query()
    # 3. SQLiteDialect.format_*_query() generates correct PRAGMA/sqlite_master SQL
    #
    # This follows the same pattern as MySQL and PostgreSQL backends.

    # ------------------------------------------------------------------ #
    # Parse methods — pure Python, no I/O
    # ------------------------------------------------------------------ #

    def _parse_database_info(self, rows: List[Dict[str, Any]],
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

    def _parse_tables(self, rows: List[Dict[str, Any]], schema: Optional[str]) -> List[IntrospectionTableInfo]:
        tables = []
        for row in rows:
            type_str = row.get("type", "table").lower()
            if type_str == "table":
                table_type = TableType.BASE_TABLE
            elif type_str == "view":
                table_type = TableType.VIEW
            else:
                table_type = TableType.EXTERNAL

            tables.append(
                IntrospectionTableInfo(
                    name=row["name"],
                    schema=schema or self._get_default_schema(),
                    table_type=table_type,
                    row_count=None,
                    create_time=None,
                )
            )
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
        m = re.search(r"\((\d+)\s*,\s*(\d+)\)", raw_type)
        if m:
            result["numeric_precision"] = int(m.group(1))
            result["numeric_scale"] = int(m.group(2))
            return result
        m = re.search(r"\((\d+)\)", raw_type)
        if m:
            value = int(m.group(1))
            if re.match(r"^\s*(?:TIMESTAMP|TIME|DATETIME)\s*\(", raw_type, re.IGNORECASE):
                result["datetime_precision"] = value
            elif re.match(r"^\s*(?:DECIMAL|NUMERIC|FLOAT|DOUBLE|REAL)\s*\(",
                          raw_type, re.IGNORECASE):
                result["numeric_precision"] = value
            else:
                result["character_maximum_length"] = value
        return result

    def _parse_columns(self, rows: List[Dict[str, Any]], table_name: str, schema: str,
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
                continue  # Skip rowid alias columns only
            nullable = ColumnNullable.NULLABLE if row["notnull"] == 0 else ColumnNullable.NOT_NULL
            raw_type = row.get("type") or "TEXT"
            # Extract base type (e.g., "VARCHAR" from "VARCHAR(255)")
            base_type_match = re.match(r"^([A-Za-z_]+)", raw_type)
            base_type = base_type_match.group(1) if base_type_match else raw_type
            # SQLite pk field: 0 = not primary key, >0 = primary key (or part of composite PK)
            is_pk = row.get("pk", 0) > 0
            # Parse raw type string into a DataType expression
            from rhosocial.activerecord.backend.expression.types._base import DataType
            parsed = DataType.parse_data_type_str(self._backend.dialect, raw_type)
            # Auto-increment: only applies to INTEGER PRIMARY KEY with AUTOINCREMENT keyword
            is_auto_inc = is_pk and has_auto_increment
            # Generated columns (hidden=2 => virtual, hidden=3 => stored)
            is_generated = hidden in (2, 3)
            gen_expr = row.get("generated_expression") if is_generated else None
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

    def _parse_indexes(self, rows: List[Dict[str, Any]], table_name: str, schema: str) -> List[IndexInfo]:
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

    def _parse_foreign_keys(self, rows: List[Dict[str, Any]], table_name: str, schema: str) -> List[IntrospectionForeignKeyInfo]:
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

    def _parse_views(self, rows: List[Dict[str, Any]], schema: str) -> List[IntrospectionViewInfo]:
        return [IntrospectionViewInfo(name=row["name"], schema=schema, definition=row.get("sql")) for row in rows]

    def _parse_view_info(self, rows: List[Dict[str, Any]], view_name: str, schema: str) -> Optional[IntrospectionViewInfo]:
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
    def _parse_trigger_header(cls, ddl: Optional[str]):
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

    def _parse_triggers(self, rows: List[Dict[str, Any]], schema: str) -> List[IntrospectionTriggerInfo]:
        triggers = []
        for row in rows:
            timing, events = self._parse_trigger_header(row.get("sql"))
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

        sql, params = self._build_database_info_sql()
        rows = self._executor.execute(sql, params)
        values = self._collect_database_pragmas()
        values["table_count"] = self._count_tables()
        result = self._parse_database_info(rows, values)
        self._cache.set(key, result)
        return result

    def _count_tables(self) -> Optional[int]:
        """How many tables this database declares, system ones excluded."""
        sql = (
            "SELECT COUNT(*) AS table_count FROM sqlite_master "
            "WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        )
        rows = self._executor.execute(sql, ())
        if not rows:
            return None
        try:
            return int(rows[0]["table_count"])
        except (KeyError, TypeError, ValueError):
            return None


class SyncSQLiteIntrospector(SQLiteIntrospectorMixin, SyncAbstractIntrospector):
    """Synchronous introspector for SQLite backends.

    In addition to the standard SyncAbstractIntrospector interface, exposes the
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
        executor: SyncIntrospectorExecutor,
        cache: Optional[IntrospectionCache] = None,
    ) -> None:
        super().__init__(backend, executor, cache)
        self._pragma_instance: Optional[SyncPragmaIntrospector] = None
        self._status_instance: Optional[SyncSQLiteStatusIntrospector] = None

    @property
    def pragma(self) -> SyncPragmaIntrospector:
        """SQLite-specific PRAGMA sub-introspector (lazily created)."""
        if self._pragma_instance is None:
            self._pragma_instance = SyncPragmaIntrospector(self._backend, self._executor)
        return self._pragma_instance

    @property
    def status(self) -> SyncSQLiteStatusIntrospector:
        """SQLite status introspector (lazily created)."""
        if self._status_instance is None:
            self._status_instance = SyncSQLiteStatusIntrospector(self._backend)
        return self._status_instance



    # ------------------------------------------------------------------ #
    # Override list_columns for auto-increment detection
    # ------------------------------------------------------------------ #

    def list_columns(self, table_name: str, schema: Optional[str] = None) -> List[IntrospectionColumnInfo]:
        """List columns, with auto-increment detection from DDL."""
        target_db = schema or self._get_default_schema()
        key = self._cache.key(IntrospectionScope.COLUMN, table_name, schema=schema)
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        sql, params = self._build_column_info_sql(table_name, schema)
        rows = self._executor.execute(sql, params)

        # Query the DDL for AUTOINCREMENT detection, and the index pragmas for
        # uniqueness: neither fact is on the column row.
        ddl = None
        ddl_result = self._executor.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' "
            f"AND name={self.dialect.p()} AND tbl_name={self.dialect.p()}",
            (table_name, table_name),
        )
        if ddl_result and ddl_result[0].get("sql"):
            ddl = ddl_result[0]["sql"]

        unique_columns = self._collect_unique_columns(table_name, target_db)

        result = self._parse_columns(
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
        target_db = schema or self._get_default_schema()
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
                ddl_result = self._executor.execute(
                    f"SELECT sql FROM sqlite_master WHERE type='index' AND name={self.dialect.p()}",
                    (idx_name,),
                )
                if ddl_result and ddl_result[0].get("sql"):
                    ddl_sql = ddl_result[0]["sql"]
                    where_match = re.search(
                        r'\bWHERE\b\s*(.*)', ddl_sql, re.IGNORECASE | re.DOTALL
                    )
                    if where_match:
                        filter_condition = where_match.group(1).strip().rstrip(';')

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
    # get_table_info override — uses direct _parse, avoids redundant
    # list_tables() call and populates columns/indexes/FKs in one sweep.
    # ------------------------------------------------------------------ #

    def get_table_info(self, table_name: str, schema: Optional[str] = None) -> Optional[IntrospectionTableInfo]:
        schema or self._get_default_schema()
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
        """The async twin of :meth:`SyncSQLiteIntrospector.get_database_info`.

        Same questions, awaited, and the same :meth:`_parse_database_info`
        reduction -- so the two directions cannot report different encodings or
        different sizes for one database.
        """
        key = self._cache.key(IntrospectionScope.DATABASE)
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        sql, params = self._build_database_info_sql()
        rows = await self._executor.execute(sql, params)
        values: Dict[str, Any] = {}
        for name in self._DATABASE_PRAGMAS:
            values[name] = self._pragma_value(await self.pragma.get(name), name)
        values["table_count"] = await self._count_tables_async()
        result = self._parse_database_info(rows, values)
        self._cache.set(key, result)
        return result

    async def _count_tables_async(self) -> Optional[int]:
        sql = (
            "SELECT COUNT(*) AS table_count FROM sqlite_master "
            "WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        )
        rows = await self._executor.execute(sql, ())
        if not rows:
            return None
        try:
            return int(rows[0]["table_count"])
        except (KeyError, TypeError, ValueError):
            return None

    # ------------------------------------------------------------------ #
    # Override list_columns for auto-increment detection
    # ------------------------------------------------------------------ #

    async def list_columns(self, table_name: str, schema: Optional[str] = None) -> List[IntrospectionColumnInfo]:
        """List columns, with auto-increment detection from DDL."""
        target_db = schema or self._get_default_schema()
        key = self._cache.key(IntrospectionScope.COLUMN, table_name, schema=schema)
        cached = self._cache.get(key)
        if cached is not None:
            return cached

        sql, params = self._build_column_info_sql(table_name, schema)
        rows = await self._executor.execute(sql, params)

        # Query the DDL for AUTOINCREMENT detection
        ddl = None
        ddl_result = await self._executor.execute(
            "SELECT sql FROM sqlite_master WHERE type='table' "
            f"AND name={self.dialect.p()} AND tbl_name={self.dialect.p()}",
            (table_name, table_name),
        )
        if ddl_result and ddl_result[0].get("sql"):
            ddl = ddl_result[0]["sql"]

        unique_columns = await self._collect_unique_columns_async(table_name, target_db)

        result = self._parse_columns(
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
        target_db = schema or self._get_default_schema()
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
                ddl_result = await self._executor.execute(
                    f"SELECT sql FROM sqlite_master WHERE type='index' AND name={self.dialect.p()}",
                    (idx_name,),
                )
                if ddl_result and ddl_result[0].get("sql"):
                    ddl_sql = ddl_result[0]["sql"]
                    where_match = re.search(
                        r'\bWHERE\b\s*(.*)', ddl_sql, re.IGNORECASE | re.DOTALL
                    )
                    if where_match:
                        filter_condition = where_match.group(1).strip().rstrip(';')

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
    # get_table_info override — uses direct _parse, avoids redundant
    # list_tables() call and populates columns/indexes/FKs in one sweep.
    # ------------------------------------------------------------------ #

    async def get_table_info(self, table_name: str, schema: Optional[str] = None) -> Optional[IntrospectionTableInfo]:
        schema or self._get_default_schema()
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
