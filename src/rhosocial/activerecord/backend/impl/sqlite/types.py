from typing import Dict

from ...dialect import DatabaseType, TypeMapping
from ...helpers import format_with_length

# SQLite type mapping configuration
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
        sql = self.sql_type

        # Handle primary key
        if "primary_key" in self.constraints:
            # For INTEGER PRIMARY KEY, it's an auto-incrementing primary key
            if self.sql_type.upper() == "INTEGER":
                sql = SQLiteTypes.ROWID
            else:
                sql += " PRIMARY KEY"

        # Handle auto-increment
        if "autoincrement" in self.constraints and sql != SQLiteTypes.ROWID:
            sql += " AUTOINCREMENT"

        # Handle other constraints
        if "unique" in self.constraints:
            sql += " UNIQUE"
        if "not_null" in self.constraints:
            sql += " NOT NULL"
        if "default" in self.constraints:
            sql += f" DEFAULT {self.constraints['default']}"

        return sql

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