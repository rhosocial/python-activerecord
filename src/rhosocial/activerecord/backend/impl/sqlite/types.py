# src/rhosocial/activerecord/backend/impl/sqlite/types.py
from typing import Dict

# TypeMapping is used here for DDL generation (defining schema),
# distinct from runtime type adaptation.
from ...schema import DatabaseType, TypeMapping
from ...helpers import format_with_length

# This dictionary defines the mapping from generic DatabaseType (used by the ORM)
# to concrete SQLite SQL type definitions, specifically for DDL generation
# (e.g., CREATE TABLE statements).
# It utilizes TypeMapping to specify the SQL type and an optional formatting function.
SQLITE_TYPE_MAPPINGS: Dict[DatabaseType, TypeMapping] = {
    DatabaseType.TINYINT: TypeMapping("INTEGER"),
    DatabaseType.SMALLINT: TypeMapping("INTEGER"),
    DatabaseType.INTEGER: TypeMapping("INTEGER"),
    DatabaseType.BIGINT: TypeMapping("INTEGER"),
    DatabaseType.FLOAT: TypeMapping("REAL"),
    DatabaseType.DOUBLE: TypeMapping("REAL"),
    DatabaseType.DECIMAL: TypeMapping("REAL"),
    DatabaseType.CHAR: TypeMapping("TEXT", format_with_length),
    DatabaseType.VARCHAR: TypeMapping("TEXT", format_with_length),
    DatabaseType.TEXT: TypeMapping("TEXT"),
    DatabaseType.DATE: TypeMapping("TEXT"),
    DatabaseType.TIME: TypeMapping("TEXT"),
    DatabaseType.DATETIME: TypeMapping("TEXT"),
    DatabaseType.TIMESTAMP: TypeMapping("TEXT"),
    DatabaseType.BLOB: TypeMapping("BLOB"),
    DatabaseType.BOOLEAN: TypeMapping("INTEGER"),
    DatabaseType.UUID: TypeMapping("TEXT"),
    DatabaseType.JSON: TypeMapping("TEXT"),
    DatabaseType.ARRAY: TypeMapping("TEXT"),
    # SQLite specific types are set as CUSTOM
    DatabaseType.CUSTOM: TypeMapping("TEXT"),
}


class SQLiteTypes:
    """SQLite specific type constants"""
    NUMERIC = "NUMERIC"
    ROWID = "INTEGER PRIMARY KEY"
    # Add other SQLite specific types...


class SQLiteColumnType:
    """SQLite column type definition"""

    def __init__(self, sql_type: str, **constraints):
        """Initialize column type

        Args:
            sql_type: SQL type definition
            **constraints: Constraint conditions
        """
        self.sql_type = sql_type
        self.constraints = constraints

    def __str__(self):
        """Generate complete type definition statement"""
        sql_parts = [self.sql_type] # Start with the base type

        is_integer_pk = self.sql_type.upper() == "INTEGER" and self.constraints.get("primary_key")
        is_autoincrement = self.constraints.get("autoincrement")

        if is_integer_pk:
            sql_parts = ["INTEGER PRIMARY KEY"]
            if is_autoincrement:
                sql_parts.append("AUTOINCREMENT")
        elif "primary_key" in self.constraints: # Non-integer PK
            sql_parts.append("PRIMARY KEY")

        # Handle other constraints
        if "unique" in self.constraints:
            sql_parts.append("UNIQUE")
        if "not_null" in self.constraints:
            sql_parts.append("NOT NULL")
        if "default" in self.constraints:
            default_value = self.constraints["default"]
            # Ensure string defaults are quoted if they are strings but not already quoted
            if isinstance(default_value, str) and not (default_value.startswith("'") and default_value.endswith("'")):
                default_value = f"'{default_value}'"
            sql_parts.append(f"DEFAULT {default_value}")

        return " ".join(sql_parts)

    @classmethod
    def get_type(cls, db_type: DatabaseType, **params) -> 'SQLiteColumnType':
        """Create SQLite column type from generic type

        Args:
            db_type: Generic database type definition
            **params: Type parameters and constraints

        Returns:
            SQLiteColumnType: SQLite column type instance

        Raises:
            ValueError: If type is not supported
        """
        mapping = SQLITE_TYPE_MAPPINGS.get(db_type)
        if not mapping:
            raise ValueError(f"Unsupported type: {db_type}")

        sql_type = mapping.db_type
        if mapping.format_func:
            sql_type = mapping.format_func(sql_type, params)

        constraints = {k: v for k, v in params.items()
                       if k in ['primary_key', 'autoincrement', 'unique',
                                'not_null', 'default']}

        return cls(sql_type, **constraints)
