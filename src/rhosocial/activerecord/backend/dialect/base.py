# src/rhosocial/activerecord/backend/dialect/base.py
"""
SQL dialect abstract base class.

This module defines the minimal base that all SQL dialects must implement.
All SQL formatting logic lives in Mixin classes in mixins.py.
"""

import warnings as _warnings
from typing import TYPE_CHECKING, Any, ClassVar, Dict, FrozenSet, Optional, Tuple, Union

from ..warnings import IdentifierQuotingWarning
from .exceptions import (
    DialectNotAdaptedException,
    ProtocolNotImplementedError,
    UnsupportedFeatureError,
)

if TYPE_CHECKING:
    import datetime as _dt
    from decimal import Decimal

    from ..schema.differ import SchemaDiffer


def _version_text(version: Tuple[int, int, int]) -> str:
    """Render a ``(major, minor, patch)`` tuple the way a server reports it.

    Used by messages that tell a caller which version a feature arrived in and
    which one is in force, so both read the same way.
    """
    return ".".join(str(part) for part in version)


class SQLDialectBase:
    """
    Minimal base class for SQL dialects.

    Provides only the lowest-level infrastructure:
    - identity (name, version)
    - parameter placeholder
    - identifier quoting and safety helpers
    - runtime protocol/feature checks

    All SQL formatting is provided by Mixin classes composed into dialect subclasses.
    """

    # Standard isolation level name mapping
    ISOLATION_LEVEL_NAMES = {
        "READ_UNCOMMITTED": "READ UNCOMMITTED",
        "READ_COMMITTED": "READ COMMITTED",
        "REPEATABLE_READ": "REPEATABLE READ",
        "SERIALIZABLE": "SERIALIZABLE",
    }

    def __init__(self) -> None:
        self.strict_validation = True
        self._version: Optional[Tuple[int, int, int]] = None
        self._reserved_words: FrozenSet[str] = frozenset()

    @property
    def version(self) -> Tuple[int, int, int]:
        if self._version is None:
            from .exceptions import DialectNotAdaptedException

            raise DialectNotAdaptedException(self.name)
        return self._version

    @version.setter
    def version(self, value: Tuple[int, int, int]) -> None:
        self._version = value

    @property
    def name(self) -> str:
        return self.__class__.__name__.replace("Dialect", "")

    def get_parameter_placeholder(self, position: int = 0) -> str:
        return "?"

    def p(self, position: int = 0) -> str:
        """Short alias for :meth:`get_parameter_placeholder`.

        The binding placeholder is the single source of truth for the SQL
        parameter marker. Every formatter must emit ``self.p()`` (never a
        hard-coded ``?`` or ``%s``) so the marker always matches the
        parameter style this dialect's backend/driver consumes.
        """
        return self.get_parameter_placeholder(position)

    def inline_sql_literal(self, value: Any) -> str:
        """Render a Python value as a safe, inline SQL literal.

        DDL clauses (CHECK / DEFAULT / partition boundaries / partial-index
        WHERE) accept no bind parameters, so their literal values render
        inline with dialect-controlled escaping — this is the single point
        of control for that rendering, backed by the three-level literal
        construction (built-in scalars → backend overrides → the
        literal-construction protocol; no ``str()`` fallback).
        """
        return self.format_literal(value)

    def get_isolation_level_name(self, level) -> str:
        level_name = level.name if hasattr(level, "name") else str(level)
        return self.ISOLATION_LEVEL_NAMES.get(level_name, level_name.replace("_", " "))

    def supports_microsecond_timestamp(self) -> bool:
        """Whether TIMESTAMP values preserve microsecond (1/1000000 s) precision.

        SQLite, MySQL, PostgreSQL and most other backends store datetimes with
        microsecond precision. Firebird's ``TIMESTAMP`` only keeps 1/10000 s
        (4 fractional digits), so backends that truncate microseconds must
        override this to return ``False``.
        """
        return True

    def supports_explain_plan(self) -> bool:
        """Whether the backend supports an EXPLAIN statement that returns rows.

        SQLite (``EXPLAIN QUERY PLAN``), MySQL/MariaDB, PostgreSQL, Oracle
        (``EXPLAIN PLAN``) and SQL Server all provide one. Firebird has no
        equivalent DSQL statement and overrides this to return ``False``.
        """
        return True

    def create_schema_differ(self) -> "SchemaDiffer":
        """Return a schema differ for this dialect's comparison rules.

        Backend dialects override this to supply backend-specific comparison
        (e.g. ``SQLiteSchemaDiffer``, ``MySQLSchemaDiffer``). The default
        returns the generic :class:`~rhosocial.activerecord.backend.schema.differ.SchemaDiffer`.
        This is the dependency-inversion point: the core never imports
        concrete backend differ implementations.
        """
        from ..schema.differ import SchemaDiffer

        return SchemaDiffer()

    def require_protocol(self, protocol_type: type, _feature_name: str, required_by: str) -> None:
        if not isinstance(self, protocol_type):
            raise ProtocolNotImplementedError(
                dialect_name=self.name,
                protocol_name=protocol_type.__name__,
                required_by=required_by,
            )

    def check_feature_support(
        self, check_method: str, feature_name: str, suggestion: Optional[str] = None
    ) -> None:
        is_supported = False
        if hasattr(self, check_method):
            is_supported = getattr(self, check_method)()
        if not is_supported:
            raise UnsupportedFeatureError(
                dialect_name=self.name, feature_name=feature_name, suggestion=suggestion
            )

    # ------------------------------------------------------------------
    # Version floors for named features (functions above all)
    # ------------------------------------------------------------------

    #: Function name -> earliest ``(major, minor, patch)`` version of this
    #: dialect that spells it. A backend declares the table; the base reads it
    #: in :meth:`function_version_floor` and enforces it in
    #: :meth:`check_function_version`.
    #:
    #: Annotated and deliberately *not* assigned here. ``SQLDialectBase`` sits
    #: ahead of every mixin in a dialect's MRO, so a default assigned on the
    #: base would shadow the table a backend's mixin declares -- the same
    #: reason the base declares no ``supports_functions``. A backend that
    #: computes its floors rather than tabulating them overrides
    #: :meth:`function_version_floor` on its dialect class, which *does*
    #: precede the base.
    function_version_floors: ClassVar[Dict[str, Tuple[int, int, int]]]

    def function_version_floor(self, func_name: str) -> Optional[Tuple[int, int, int]]:
        """Return the earliest version of this dialect that knows *func_name*.

        The query half of a version gate: the version a backend started
        spelling a function at, read from :attr:`function_version_floors`.
        ``None`` means no floor is recorded, which is not the same as
        "unsupported" -- a name nobody has measured is simply not gated here.
        Rendering consults it through :meth:`check_function_version`, so a
        recorded floor is a refusal rather than a documented observation.

        Names match case-insensitively: the core and backend factories spell
        them lower-case, the renderer spells them upper, and a caller may hand
        either to a :class:`~...expression.core.FunctionCall`.

        Args:
            func_name: The function name as the expression carries it.

        Returns:
            The floor as a ``(major, minor, patch)`` tuple, or ``None`` when
            this dialect records no floor for *func_name*.
        """
        floors: Optional[Dict[str, Tuple[int, int, int]]] = getattr(
            self, "function_version_floors", None
        )
        if not floors:
            return None
        floor = floors.get(func_name)
        if floor is None:
            floor = floors.get(func_name.lower())
        return floor

    def check_function_version(self, func_name: str) -> None:
        """Refuse a function call this dialect's version predates.

        Reads :meth:`function_version_floor` and refuses when the version in
        force is below it. This is what turns a declared floor into a gate:
        the alternative is a renderer that emits SQL the server will reject,
        which is the failure the floor was recorded to prevent.

        :class:`~.mixins.function.FunctionCallMixin` calls it while rendering a
        call, so the gate holds for every dialect that composes that mixin and
        for every caller.

        Args:
            func_name: The function name as the expression carries it.

        Raises:
            UnsupportedFeatureError: A floor is recorded for *func_name* and
                this dialect's version is below it. The message names the
                function, the floor and the version in force.

        Note:
            A dialect that has not been adapted has no version to compare
            against, so there is nothing to refuse: adaptation
            (``backend.introspect_and_adapt()``) is what makes the gate bite,
            and rendering an un-adapted dialect keeps its old permissiveness.
        """
        floor = self.function_version_floor(func_name)
        if floor is None:
            return
        try:
            version = self.version
        except DialectNotAdaptedException:
            return
        if version >= floor:
            return
        name = func_name.upper()
        raise UnsupportedFeatureError(
            dialect_name=self.name,
            feature_name=f"the {name} function on {self.name} {_version_text(version)}",
            suggestion=(
                f"{name} arrived in {self.name} {_version_text(floor)}; connect to a "
                f"server that has it, or spell the operation another way"
            ),
        )

    @property
    def reserved_words(self) -> FrozenSet[str]:
        """Return the reserved word set for this dialect.

        Returns:
            A frozenset of lowercase reserved words. Subclasses should
            override ``_reserved_words`` to provide backend-specific words.
        """
        return self._reserved_words

    def is_reserved_word(self, identifier: str) -> bool:
        """Check if identifier is a reserved word (case-insensitive).

        Args:
            identifier: The identifier to check.

        Returns:
            True if the identifier (lowercased) is in the reserved word set.
        """
        return identifier.lower() in self._reserved_words

    def format_identifier(self, identifier: str, need_quote: bool = True) -> str:
        """Format an SQL identifier.

        Note: This method formats raw identifier strings, not expression objects.
        Therefore it does NOT follow the ``(self, expr) -> Tuple[str, tuple]``
        signature convention used by expression formatters.

        Args:
            identifier: The raw identifier string to format.
            need_quote: Whether to quote the identifier. Default True.
                When False, the identifier is returned as-is without escaping.
                Users should be aware that unquoted reserved words may cause
                SQL errors.

        Returns:
            The formatted identifier string.
        """
        if not need_quote:
            if self.is_reserved_word(identifier):
                _warnings.warn(
                    f"Identifier '{identifier}' is a reserved word in {self.name} "
                    f"and may cause SQL errors without quoting.",
                    IdentifierQuotingWarning,
                    stacklevel=2,
                )
            return identifier
        escaped = identifier.replace('"', '""')
        return f'"{escaped}"'

    def escape_sql_string(self, value: str) -> str:
        """This dialect's string-escape policy, for inline literal construction.

        This is the helper the literal-construction protocol must use for
        every string component it embeds in the literal text it returns:
        single quotes are doubled so the component is safe inside a
        single-quoted SQL string. Hand-concatenated quoting is a violation
        of the protocol.

        The policy belongs to the dialect, because SQL dialects differ in
        how a string literal represents a quote: most double the quote,
        while MySQL, MariaDB and ClickHouse treat a backslash as an escape
        character and BigQuery spells a quote as a backslash-quote. So a
        dialect overrides this method rather than the framework deciding.

        It is an instance method rather than a static one because a policy
        may depend on the dialect's own state: MySQL's depends on the
        session's SQL mode, since under ``NO_BACKSLASH_ESCAPES`` a
        backslash is a literal character and must not be doubled.
        """
        return value.replace("'", "''")

    def format_literal(
        self, value: "Optional[Union[bool, int, float, Decimal, _dt.datetime, _dt.date]]"
    ) -> str:
        """Render a value as a safe inline SQL literal — the three-level
        construction.

        Used by DDL clauses (CHECK / DEFAULT / partition boundaries /
        partial-index WHERE / generated columns), which accept no bind
        parameters, and by every inline-strategy literal node. Construction
        is attempted at three levels, in order, and an unrenderable value
        fails explicitly — there is no ``str()`` fallback:

        1. **Dialect base class built-ins** — the host scalars whose inline
           form is portable or dialect-spelled: ``NULL`` and booleans render
           as keywords, numbers as numeric text (with a range check: ``NaN``
           and ``±Inf`` must never reach SQL text — ``float('inf')``
           stringifies as ``'inf'`` and would degrade to an identifier), and
           date/time values as ISO-8601 strings through the escape helper.
           Note ``bool`` is an ``int`` subclass, so the boolean dispatch runs
           before the numeric check.
        2. **Backend overrides** — host types whose literal form is
           backend-specific (``bytes`` BLOB literals, ``UUID``,
           ``timedelta`` intervals, arrays, JSON). The base class does *not*
           guess them; a backend dialect must override this method for the
           value types it supports, and leave the failure explicit for the
           ones it does not.
        3. **The literal-construction protocol** — a user-defined or
           backend-specific value type implements
           :class:`SQLLiteral`: the returned text is embedded verbatim as an
           atom. The protocol is a rendering duty, distinct from
           ``DataType`` column-type declaration.

        The returned literal is an **escaped atom** (string values are quoted
        and escaped), so any placeholder character inside it cannot be
        mistaken for a bind placeholder during placeholder resolution.
        """
        import datetime as _dt
        from decimal import Decimal

        if value is None:
            return "NULL"
        if isinstance(value, bool):
            # Portable boolean literal: 1/0 works everywhere; the
            # PostgreSQL-specific TRUE/FALSE spelling is a dialect override
            # for engines that reject 1/0 in a BOOLEAN context.
            return "TRUE" if value else "FALSE"
        if isinstance(value, Decimal):
            # Exact decimal literal; `str` preserves precision/scale without
            # the exponent form `repr` could produce.
            if not value.is_finite():
                raise ValueError("non-finite Decimal cannot be inlined into SQL")
            return str(value)
        if isinstance(value, (int, float)):
            if isinstance(value, float):
                if value != value:  # NaN
                    raise ValueError("NaN cannot be inlined into SQL")
                if value == float("inf") or value == float("-inf"):
                    raise ValueError("Inf cannot be inlined into SQL")
                return repr(value)
            return str(value)
        if isinstance(value, _dt.datetime):
            escaped = self.escape_sql_string(value.isoformat(sep=" "))
            return f"'{escaped}'"
        if isinstance(value, _dt.date):
            escaped = self.escape_sql_string(value.isoformat())
            return f"'{escaped}'"
        if isinstance(value, _dt.time):
            # A time of day is a portable quoted form like the other two, and
            # isoformat keeps the offset an aware time carries. It needs its own
            # branch because it shares neither base class with datetime/date.
            escaped = self.escape_sql_string(value.isoformat())
            return f"'{escaped}'"
        if isinstance(value, str):
            escaped = self.escape_sql_string(value)
            return f"'{escaped}'"
        # Level 3: the value type defines its own literal construction.
        from ..expression.bases import SQLLiteral

        if isinstance(value, SQLLiteral):
            text = value.__sql_literal__(self)
            if not isinstance(text, str) or not text:
                raise TypeError(
                    f"{self.name}: {value!r} implements the literal-construction "
                    f"protocol but returned {type(text).__name__}, expected a "
                    f"non-empty inline literal string."
                )
            return text
        raise TypeError(
            f"{self.name}: value {value!r} of type {type(value).__name__} "
            f"has no inline SQL literal form; use a backend-specific literal "
            f"or implement the literal-construction protocol."
        )

    def refuse_ddl_bind_parameters(self, feature: str) -> None:
        """Refuse a DDL statement whose body carries bind parameters.

        The body of a DDL statement is a query, and a query may carry bind
        parameters. Whether the engine accepts them is the dialect's
        question -- :meth:`supports_create_table_as_bind_parameters`,
        :meth:`supports_create_view_bind_parameters` and
        :meth:`supports_materialized_view_bind_parameters` answer it -- and
        this is where a dialect that answers "no" is told so: by name, with
        the way out named.

        The reason comes from the dialect
        (``_ddl_bind_parameter_reason``), so a backend that refuses binds
        for a *measured* reason says which one; the default lives on the
        core mixins, not here, because this class sits early in a dialect's
        MRO and a default here would shadow every backend's own answer.

        The way out is always the same: build the query with an inlined
        literal, so the value is in the statement's text and not in a
        parameter.
        """
        raise UnsupportedFeatureError(
            self.name,
            feature,
            suggestion=(
                f"{self._ddl_bind_parameter_reason(feature)} "
                "Build the query with an inlined literal instead."
            ),
        )

