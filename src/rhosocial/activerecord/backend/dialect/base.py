# src/rhosocial/activerecord/backend/dialect/base.py
"""
SQL dialect abstract base class.

This module defines the minimal base that all SQL dialects must implement.
All SQL formatting logic lives in Mixin classes in mixins.py.
"""

import re
from typing import Optional, Tuple, TYPE_CHECKING

from .exceptions import ProtocolNotImplementedError, UnsupportedFeatureError
from .mixins.ddl_diff import CreateTableExpressionDiffMixin

if TYPE_CHECKING:
    from ..schema.differ import SchemaDiffer


class SQLDialectBase(CreateTableExpressionDiffMixin):
    """
    Minimal base class for SQL dialects.

    Provides only the lowest-level infrastructure:
    - identity (name, version)
    - parameter placeholder
    - identifier quoting and safety helpers
    - runtime protocol/feature checks
    - expression-level CREATE TABLE diff (generic strict implementation;
      backends override the comparison/capability hooks as needed)

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
