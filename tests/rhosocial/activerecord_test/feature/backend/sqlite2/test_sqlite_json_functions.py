# tests/rhosocial/activerecord_test/feature/backend/sqlite2/test_sqlite_json_functions.py
"""
Tests for SQLite-specific JSON functions.
These functions are available in SQLite 3.38.0+ with the json1 extension.
"""
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
from rhosocial.activerecord.backend.impl.sqlite.functions.json import (
    json,
    json_array,
    json_object,
    json_extract,
    json_type,
    json_valid,
    json_quote,
    json_remove,
    json_set,
    json_insert,
    json_replace,
    json_patch,
    json_array_length,
    json_array_unpack,
    json_object_pack,
    json_object_retrieve,
    json_object_length,
    json_object_keys,
    json_tree,
    json_each,
)


class TestSQLiteJSONFunctions:
    """Tests for SQLite JSON functions."""

    def test_json_with_string(self, sqlite_dialect_3_38_0: SQLiteDialect):
        """Test json() with string literal."""
        result = json(sqlite_dialect_3_38_0, '{"a": 1}')
        sql, params = result.to_sql()
        assert "JSON(" in sql
        assert params == ('{"a": 1}',)

    def test_json_with_column(self, sqlite_dialect_3_38_0: SQLiteDialect):
        """Test json() with column reference."""
        col = Column(sqlite_dialect_3_38_0, "data")
        result = json(sqlite_dialect_3_38_0, col)
        sql, _ = result.to_sql()
        assert "JSON(" in sql
        assert '"data"' in sql

    def test_json_array_empty(self, sqlite_dialect_3_38_0: SQLiteDialect):
        """Test json_array() with no arguments."""
        result = json_array(sqlite_dialect_3_38_0)
        sql, _ = result.to_sql()
        assert "JSON_ARRAY()" in sql

    def test_json_array_with_values(self, sqlite_dialect_3_38_0: SQLiteDialect):
        """Test json_array() with values."""
        result = json_array(sqlite_dialect_3_38_0, 1, 2, 3)
        sql, params = result.to_sql()
        assert "JSON_ARRAY(" in sql
        assert params == (1, 2, 3)

    def test_json_array_with_mixed(self, sqlite_dialect_3_38_0: SQLiteDialect):
        """Test json_array() with mixed types."""
        result = json_array(sqlite_dialect_3_38_0, "hello", 123, Column(sqlite_dialect_3_38_0, "col"))
        sql, params = result.to_sql()
        assert "JSON_ARRAY(" in sql
        assert params == ("hello", 123)

    def test_json_object_empty(self, sqlite_dialect_3_38_0: SQLiteDialect):
        """Test json_object() with no arguments."""
        result = json_object(sqlite_dialect_3_38_0)
        sql, _ = result.to_sql()
        assert "JSON_OBJECT()" in sql

    def test_json_object_with_pairs(self, sqlite_dialect_3_38_0: SQLiteDialect):
        """Test json_object() with key-value pairs."""
        result = json_object(sqlite_dialect_3_38_0, "name", "John", "age", 30)
        sql, params = result.to_sql()
        assert "JSON_OBJECT(" in sql
        assert params == ("name", "John", "age", 30)

    def test_json_extract(self, sqlite_dialect_3_38_0: SQLiteDialect):
        """Test json_extract() with path."""
        result = json_extract(sqlite_dialect_3_38_0, Column(sqlite_dialect_3_38_0, "data"), "$.a")
        sql, params = result.to_sql()
        assert "JSON_EXTRACT(" in sql
        assert params == ("$.a",)

    def test_json_extract_multiple_paths(self, sqlite_dialect_3_38_0: SQLiteDialect):
        """Test json_extract() with multiple paths."""
        result = json_extract(
            sqlite_dialect_3_38_0,
            '{"a": 1}',
            "$.a",
            "$.b"
        )
        sql, params = result.to_sql()
        assert "JSON_EXTRACT(" in sql
        assert params == ('{"a": 1}', "$.a", "$.b")

    def test_json_type(self, sqlite_dialect_3_38_0: SQLiteDialect):
        """Test json_type() without path."""
        result = json_type(sqlite_dialect_3_38_0, Column(sqlite_dialect_3_38_0, "data"))
        sql, _ = result.to_sql()
        assert "JSON_TYPE(" in sql

    def test_json_type_with_path(self, sqlite_dialect_3_38_0: SQLiteDialect):
        """Test json_type() with path."""
        result = json_type(sqlite_dialect_3_38_0, Column(sqlite_dialect_3_38_0, "data"), "$.a")
        sql, params = result.to_sql()
        assert "JSON_TYPE(" in sql
        assert params == ("$.a",)

    def test_json_valid_true(self, sqlite_dialect_3_38_0: SQLiteDialect):
        """Test json_valid() with valid JSON."""
        result = json_valid(sqlite_dialect_3_38_0, '{"a": 1}')
        sql, params = result.to_sql()
        assert "JSON_VALID(" in sql
        assert params == ('{"a": 1}',)

    def test_json_valid_with_column(self, sqlite_dialect_3_38_0: SQLiteDialect):
        """Test json_valid() with column reference."""
        result = json_valid(sqlite_dialect_3_38_0, Column(sqlite_dialect_3_38_0, "data"))
        sql, _ = result.to_sql()
        assert "JSON_VALID(" in sql

    def test_json_quote(self, sqlite_dialect_3_38_0: SQLiteDialect):
        """Test json_quote()."""
        result = json_quote(sqlite_dialect_3_38_0, "hello")
        sql, params = result.to_sql()
        assert "JSON_QUOTE(" in sql
        assert params == ("hello",)

    def test_json_remove(self, sqlite_dialect_3_38_0: SQLiteDialect):
        """Test json_remove()."""
        result = json_remove(
            sqlite_dialect_3_38_0,
            Column(sqlite_dialect_3_38_0, "data"),
            "$.a"
        )
        sql, params = result.to_sql()
        assert "JSON_REMOVE(" in sql
        assert params == ("$.a",)

    def test_json_remove_multiple_paths(self, sqlite_dialect_3_38_0: SQLiteDialect):
        """Test json_remove() with multiple paths."""
        result = json_remove(
            sqlite_dialect_3_38_0,
            '{"a": 1, "b": 2}',
            "$.a",
            "$.b"
        )
        sql, params = result.to_sql()
        assert "JSON_REMOVE(" in sql
        assert params == ('{"a": 1, "b": 2}', "$.a", "$.b")

    def test_json_set(self, sqlite_dialect_3_38_0: SQLiteDialect):
        """Test json_set()."""
        result = json_set(
            sqlite_dialect_3_38_0,
            Column(sqlite_dialect_3_38_0, "data"),
            "$.a",
            "new_value"
        )
        sql, params = result.to_sql()
        assert "JSON_SET(" in sql
        assert params == ("$.a", "new_value")

    def test_json_set_multiple_pairs(self, sqlite_dialect_3_38_0: SQLiteDialect):
        """Test json_set() with multiple path-value pairs."""
        result = json_set(
            sqlite_dialect_3_38_0,
            '{"a": 1}',
            "$.a",
            10,
            "$.b",
            20
        )
        sql, _ = result.to_sql()
        assert "JSON_SET(" in sql

    def test_json_insert(self, sqlite_dialect_3_38_0: SQLiteDialect):
        """Test json_insert()."""
        result = json_insert(
            sqlite_dialect_3_38_0,
            Column(sqlite_dialect_3_38_0, "data"),
            "$.b",
            "new_value"
        )
        sql, params = result.to_sql()
        assert "JSON_INSERT(" in sql
        assert params == ("$.b", "new_value")

    def test_json_replace(self, sqlite_dialect_3_38_0: SQLiteDialect):
        """Test json_replace()."""
        result = json_replace(
            sqlite_dialect_3_38_0,
            Column(sqlite_dialect_3_38_0, "data"),
            "$.a",
            "replaced"
        )
        sql, params = result.to_sql()
        assert "JSON_REPLACE(" in sql
        assert params == ("$.a", "replaced")

    def test_json_patch(self, sqlite_dialect_3_38_0: SQLiteDialect):
        """Test json_patch()."""
        result = json_patch(
            sqlite_dialect_3_38_0,
            Column(sqlite_dialect_3_38_0, "target"),
            Column(sqlite_dialect_3_38_0, "patch")
        )
        sql, _ = result.to_sql()
        assert "JSON_PATCH(" in sql

    def test_json_array_length(self, sqlite_dialect_3_38_0: SQLiteDialect):
        """Test json_array_length()."""
        result = json_array_length(sqlite_dialect_3_38_0, Column(sqlite_dialect_3_38_0, "data"))
        sql, _ = result.to_sql()
        assert "JSON_ARRAY_LENGTH(" in sql

    def test_json_array_length_with_path(self, sqlite_dialect_3_38_0: SQLiteDialect):
        """Test json_array_length() with path."""
        result = json_array_length(
            sqlite_dialect_3_38_0,
            Column(sqlite_dialect_3_38_0, "data"),
            "$.items"
        )
        sql, params = result.to_sql()
        assert "JSON_ARRAY_LENGTH(" in sql
        assert params == ("$.items",)

    def test_json_object_pack(self, sqlite_dialect_3_38_0: SQLiteDialect):
        """Test json_object_pack()."""
        result = json_object_pack(
            sqlite_dialect_3_38_0,
            "key",
            "value"
        )
        sql, params = result.to_sql()
        assert "JSON_OBJECT(" in sql
        assert params == ("key", "value")

    def test_json_object_retrieve(self, sqlite_dialect_3_38_0: SQLiteDialect):
        """Test json_object_retrieve()."""
        result = json_object_retrieve(
            sqlite_dialect_3_38_0,
            Column(sqlite_dialect_3_38_0, "data"),
            "$.name"
        )
        sql, params = result.to_sql()
        assert "JSON_EXTRACT(" in sql
        assert params == ("$.name",)

    def test_json_object_length(self, sqlite_dialect_3_38_0: SQLiteDialect):
        """Test json_object_length()."""
        result = json_object_length(sqlite_dialect_3_38_0, Column(sqlite_dialect_3_38_0, "data"))
        sql, _ = result.to_sql()
        assert "JSON_OBJECT_LENGTH(" in sql

    def test_json_object_keys(self, sqlite_dialect_3_38_0: SQLiteDialect):
        """Test json_object_keys()."""
        result = json_object_keys(sqlite_dialect_3_38_0, Column(sqlite_dialect_3_38_0, "data"))
        sql, _ = result.to_sql()
        assert "JSON_OBJECT_KEYS(" in sql

    def test_json_object_keys_with_path(self, sqlite_dialect_3_38_0: SQLiteDialect):
        """Test json_object_keys() with path."""
        result = json_object_keys(sqlite_dialect_3_38_0, Column(sqlite_dialect_3_38_0, "data"), "$.nested")
        sql, params = result.to_sql()
        assert "JSON_OBJECT_KEYS(" in sql
        assert params == ("$.nested",)

    def test_json_object_length_with_path(self, sqlite_dialect_3_38_0: SQLiteDialect):
        """Test json_object_length() with path."""
        result = json_object_length(sqlite_dialect_3_38_0, Column(sqlite_dialect_3_38_0, "data"), "$.nested")
        sql, params = result.to_sql()
        assert "JSON_OBJECT_LENGTH(" in sql
        assert params == ("$.nested",)

    def test_json_array_unpack(self, sqlite_dialect_3_38_0: SQLiteDialect):
        """Test json_array_unpack()."""
        result = json_array_unpack(sqlite_dialect_3_38_0, Column(sqlite_dialect_3_38_0, "data"))
        sql, _ = result.to_sql()
        assert "JSON_ARRAY_LENGTH(" in sql

    def test_json_array_unpack_with_path(self, sqlite_dialect_3_38_0: SQLiteDialect):
        """Test json_array_unpack() with path."""
        result = json_array_unpack(sqlite_dialect_3_38_0, Column(sqlite_dialect_3_38_0, "data"), "$.items")
        sql, params = result.to_sql()
        assert "JSON_ARRAY_LENGTH(" in sql
        assert params == ("$.items",)

    def test_json_tree(self, sqlite_dialect_3_38_0: SQLiteDialect):
        """Test json_tree()."""
        result = json_tree(sqlite_dialect_3_38_0, Column(sqlite_dialect_3_38_0, "data"))
        sql, _ = result.to_sql()
        assert "JSON_TREE(" in sql

    def test_json_tree_with_path(self, sqlite_dialect_3_38_0: SQLiteDialect):
        """Test json_tree() with path."""
        result = json_tree(sqlite_dialect_3_38_0, Column(sqlite_dialect_3_38_0, "data"), "$.nested")
        sql, params = result.to_sql()
        assert "JSON_TREE(" in sql
        assert params == ("$.nested",)

    def test_json_each(self, sqlite_dialect_3_38_0: SQLiteDialect):
        """Test json_each()."""
        result = json_each(sqlite_dialect_3_38_0, Column(sqlite_dialect_3_38_0, "data"))
        sql, _ = result.to_sql()
        assert "JSON_EACH(" in sql

    def test_json_each_with_path(self, sqlite_dialect_3_38_0: SQLiteDialect):
        """Test json_each() with path."""
        result = json_each(sqlite_dialect_3_38_0, Column(sqlite_dialect_3_38_0, "data"), "$.items")
        sql, params = result.to_sql()
        assert "JSON_EACH(" in sql
        assert params == ("$.items",)

    def test_json_set_with_expression_value(self, sqlite_dialect_3_38_0: SQLiteDialect):
        """Test json_set() with expression as value."""
        result = json_set(
            sqlite_dialect_3_38_0,
            Column(sqlite_dialect_3_38_0, "data"),
            "$.a",
            Column(sqlite_dialect_3_38_0, "other")
        )
        sql, _ = result.to_sql()
        assert "JSON_SET(" in sql

    def test_json_insert_with_multiple_pairs(self, sqlite_dialect_3_38_0: SQLiteDialect):
        """Test json_insert() with multiple path-value pairs."""
        result = json_insert(
            sqlite_dialect_3_38_0,
            Column(sqlite_dialect_3_38_0, "data"),
            "$.a",
            1,
            "$.b",
            2
        )
        sql, _ = result.to_sql()
        assert "JSON_INSERT(" in sql

    def test_json_replace_with_multiple_pairs(self, sqlite_dialect_3_38_0: SQLiteDialect):
        """Test json_replace() with multiple path-value pairs."""
        result = json_replace(
            sqlite_dialect_3_38_0,
            Column(sqlite_dialect_3_38_0, "data"),
            "$.a",
            "new_a",
            "$.b",
            "new_b"
        )
        sql, _ = result.to_sql()
        assert "JSON_REPLACE(" in sql

    def test_json_patch_with_literals(self, sqlite_dialect_3_38_0: SQLiteDialect):
        """Test json_patch() with literal values."""
        result = json_patch(sqlite_dialect_3_38_0, '{"a": 1}', '{"a": 2}')
        sql, params = result.to_sql()
        assert "JSON_PATCH(" in sql
        assert params == ('{"a": 1}', '{"a": 2}')

    def test_json_with_numeric(self, sqlite_dialect_3_38_0: SQLiteDialect):
        """Test json() with numeric value converted to JSON."""
        result = json(sqlite_dialect_3_38_0, 42)
        sql, params = result.to_sql()
        assert "JSON(" in sql
        assert params == (42,)
