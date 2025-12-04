# tests/rhosocial/activerecord_test/backend/sqlite/test_types.py
import pytest

from rhosocial.activerecord.backend.impl.sqlite.types import SQLiteColumnType, SQLITE_TYPE_MAPPINGS
from rhosocial.activerecord.backend.typing import DatabaseType


class TestSQLiteColumnType:
    @pytest.mark.parametrize(
        "db_type, params, expected_sql",
        [
            # Basic types
            (DatabaseType.INTEGER, {}, "INTEGER"),
            (DatabaseType.TEXT, {}, "TEXT"),
            (DatabaseType.BOOLEAN, {}, "INTEGER"),
            (DatabaseType.FLOAT, {}, "REAL"),
            (DatabaseType.BLOB, {}, "BLOB"),
            (DatabaseType.UUID, {}, "TEXT"),
            (DatabaseType.JSON, {}, "TEXT"),
            (DatabaseType.ARRAY, {}, "TEXT"),
            (DatabaseType.DATETIME, {}, "TEXT"),
            (DatabaseType.TIMESTAMP, {}, "TEXT"),
            (DatabaseType.DATE, {}, "TEXT"),
            (DatabaseType.TIME, {}, "TEXT"),
            (DatabaseType.DECIMAL, {}, "REAL"),
            (DatabaseType.VARCHAR, {}, "TEXT"), # format_with_length is applied implicitly by TypeMapping

            # With length for CHAR/VARCHAR (though SQLite ignores it for TEXT)
            (DatabaseType.VARCHAR, {"length": 255}, "TEXT(255)"),
            (DatabaseType.CHAR, {"length": 10}, "TEXT(10)"),

            # Primary Key
            (DatabaseType.INTEGER, {"primary_key": True}, "INTEGER PRIMARY KEY"),
            # INTEGER PRIMARY KEY special handling for ROWID
            (DatabaseType.INTEGER, {"primary_key": True, "autoincrement": True}, "INTEGER PRIMARY KEY AUTOINCREMENT"),
            # Non-INTEGER PK
            (DatabaseType.TEXT, {"primary_key": True}, "TEXT PRIMARY KEY"),

            # Unique
            (DatabaseType.INTEGER, {"unique": True}, "INTEGER UNIQUE"),

            # Not Null
            (DatabaseType.TEXT, {"not_null": True}, "TEXT NOT NULL"),

            # Default
            (DatabaseType.INTEGER, {"default": 0}, "INTEGER DEFAULT 0"),
            (DatabaseType.TEXT, {"default": "'hello'"}, "TEXT DEFAULT 'hello'"),

            # Combinations
            (DatabaseType.TEXT, {"not_null": True, "unique": True}, "TEXT UNIQUE NOT NULL"),
            (DatabaseType.INTEGER, {"primary_key": True, "unique": True}, "INTEGER PRIMARY KEY UNIQUE"), # unique is redundant with PK
            (DatabaseType.INTEGER, {"primary_key": True, "autoincrement": True, "not_null": True}, "INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL"), # not_null redundant with PK

            # Custom type
            (DatabaseType.CUSTOM, {}, "TEXT"),
        ]
    )
    def test_get_type_and_str_representation(self, db_type, params, expected_sql):
        """
        Tests that get_type returns the correct SQLiteColumnType and its __str__
        method generates the expected SQL type definition.
        """
        column_type = SQLiteColumnType.get_type(db_type, **params)
        assert str(column_type) == expected_sql

    def test_unsupported_type_raises_error(self):
        """
        Tests that requesting an unsupported DatabaseType raises a ValueError.
        """
        from unittest.mock import patch
        with patch('rhosocial.activerecord.backend.impl.sqlite.types.SQLITE_TYPE_MAPPINGS', {}):
            with pytest.raises(ValueError, match="Unsupported type: DatabaseType.INTEGER"):
                SQLiteColumnType.get_type(DatabaseType.INTEGER)

    def test_primary_key_without_autoincrement(self):
        """
        Test INTEGER PRIMARY KEY without autoincrement explicitly.
        """
        column_type = SQLiteColumnType.get_type(DatabaseType.INTEGER, primary_key=True)
        assert str(column_type) == "INTEGER PRIMARY KEY"
