# src/rhosocial/activerecord/backend/dialect/base.py
"""
SQL dialect abstract base class.

This module defines the minimal base that all SQL dialects must implement.
All SQL formatting logic lives in Mixin classes in mixins.py.
"""

import contextlib
import re
from contextvars import ContextVar
from typing import Any, Optional, Tuple, TYPE_CHECKING

from .exceptions import ProtocolNotImplementedError, UnsupportedFeatureError
from .mixins.ddl_diff import CreateTableExpressionDiffMixin
from .mixins.ddl_spec import DDLSpecBuildingMixin

if TYPE_CHECKING:
    from ..schema.differ import SchemaDiffer


# True while a DDL statement is being rendered: inside DDL, literal values
# must be inlined (CHECK/DEFAULT clauses accept no bind parameters). Escaping
# stays centralized in the dialect via ``inline_sql_literal``.
_ddl_inline_flag: "ContextVar[bool]" = ContextVar("ddl_inline", default=False)


class SQLDialectBase(CreateTableExpressionDiffMixin, DDLSpecBuildingMixin):
    """
    Minimal base class for SQL dialects.

    Provides only the lowest-level infrastructure:
    - identity (name, version)
    - parameter placeholder
    - identifier quoting and safety helpers
    - runtime protocol/feature checks
    - expression-level CREATE TABLE diff (generic strict implementation;
      backends override the comparison/capability hooks as needed)
    - DDL feature-spec claiming (``build_spec``; generic Spec translations
      with backend overrides)

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

    # ------------------------------------------------------------------
    # DDL inline-literal context
    # ------------------------------------------------------------------
    @staticmethod
    def is_ddl_inline() -> bool:
        """Whether a DDL statement is currently being rendered."""
        return _ddl_inline_flag.get()

    @staticmethod
    @contextlib.contextmanager
    def ddl_inline():
        """Context manager enabling inline literal rendering for DDL."""
        token = _ddl_inline_flag.set(True)
        try:
            yield
        finally:
            _ddl_inline_flag.reset(token)

    def inline_sql_literal(self, value: Any) -> str:
        """Render a Python scalar as a safe, inline SQL literal.

        Used for DDL clauses that accept no bind parameters (CHECK /
        DEFAULT / partition boundaries). Only scalar types with portable
        inline forms are handled here; backends override for type-specific
        forms (e.g. bytes, native date literals).
        """
        import datetime as _dt

        if value is None:
            return "NULL"
        if isinstance(value, bool):
            return "1" if value else "0"
        if isinstance(value, (int, float)):
            if isinstance(value, float) and value != value:  # NaN
                raise ValueError("NaN cannot be inlined into DDL")
            return repr(value) if isinstance(value, float) else str(value)
        if isinstance(value, _dt.datetime):
            escaped = self._escape_sql_string(value.isoformat(sep=" "))
            return f"'{escaped}'"
        if isinstance(value, _dt.date):
            escaped = self._escape_sql_string(value.isoformat())
            return f"'{escaped}'"
        if isinstance(value, str):
            escaped = self._escape_sql_string(value)
            return f"'{escaped}'"
        raise TypeError(
            f"{self.name}: value {value!r} of type {type(value).__name__} "
            f"has no inline DDL literal form; use a backend-specific literal."
        )

    def get_parameter_placeholder(self, position: int = 0) -> str:
        return "?"

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
                dialect_name=self.name, protocol_name=protocol_type.__name__, required_by=required_by
            )

    def check_feature_support(self, check_method: str, feature_name: str, suggestion: Optional[str] = None) -> None:
        is_supported = False
        if hasattr(self, check_method):
            is_supported = getattr(self, check_method)()
        if not is_supported:
            raise UnsupportedFeatureError(dialect_name=self.name, feature_name=feature_name, suggestion=suggestion)

    def format_identifier(self, identifier: str) -> str:
        escaped = identifier.replace('"', '""')
        return f'"{escaped}"'

    @staticmethod
    def _escape_sql_string(value: str) -> str:
        return value.replace("'", "''")

    @staticmethod
    def _validate_data_type(data_type: str) -> bool:
        return bool(re.fullmatch(r"[A-Za-z0-9\s(),]+", data_type))
