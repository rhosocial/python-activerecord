# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_statements_create_drop_schema.py
import pytest
from rhosocial.activerecord.backend.expression.statements import (
    CreateSchemaExpression, DropSchemaExpression
)
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect


class TestCreateDropSchemaStatements:
    """Tests for CREATE SCHEMA and DROP SCHEMA statements."""

    def test_basic_create_schema(self, dummy_dialect: DummyDialect):
        """Tests basic CREATE SCHEMA statement."""
        create_schema = CreateSchemaExpression(
            dummy_dialect,
            schema_name="my_schema"
        )
        sql, params = create_schema.to_sql()

        assert sql == 'CREATE SCHEMA "my_schema"'
        assert params == ()

    def test_create_schema_with_if_not_exists(self, dummy_dialect: DummyDialect):
        """Tests CREATE SCHEMA IF NOT EXISTS statement."""
        create_schema = CreateSchemaExpression(
            dummy_dialect,
            schema_name="my_schema",
            if_not_exists=True
        )
        sql, params = create_schema.to_sql()

        assert sql == 'CREATE SCHEMA IF NOT EXISTS "my_schema"'
        assert params == ()

    def test_create_schema_with_authorization(self, dummy_dialect: DummyDialect):
        """Tests CREATE SCHEMA with AUTHORIZATION clause."""
        create_schema = CreateSchemaExpression(
            dummy_dialect,
            schema_name="app_schema",
            authorization="app_user"
        )
        sql, params = create_schema.to_sql()

        assert 'CREATE SCHEMA "app_schema"' in sql
        assert 'AUTHORIZATION "app_user"' in sql
        assert params == ()

    def test_create_schema_if_not_exists_with_authorization(self, dummy_dialect: DummyDialect):
        """Tests CREATE SCHEMA IF NOT EXISTS with AUTHORIZATION."""
        create_schema = CreateSchemaExpression(
            dummy_dialect,
            schema_name="secure_schema",
            if_not_exists=True,
            authorization="admin"
        )
        sql, params = create_schema.to_sql()

        assert 'CREATE SCHEMA IF NOT EXISTS "secure_schema"' in sql
        assert 'AUTHORIZATION "admin"' in sql
        assert params == ()

    def test_basic_drop_schema(self, dummy_dialect: DummyDialect):
        """Tests basic DROP SCHEMA statement."""
        drop_schema = DropSchemaExpression(
            dummy_dialect,
            schema_name="old_schema"
        )
        sql, params = drop_schema.to_sql()

        assert sql == 'DROP SCHEMA "old_schema"'
        assert params == ()

    def test_drop_schema_with_if_exists(self, dummy_dialect: DummyDialect):
        """Tests DROP SCHEMA IF EXISTS statement."""
        drop_schema = DropSchemaExpression(
            dummy_dialect,
            schema_name="test_schema",
            if_exists=True
        )
        sql, params = drop_schema.to_sql()

        assert sql == 'DROP SCHEMA IF EXISTS "test_schema"'
        assert params == ()

    def test_drop_schema_with_cascade(self, dummy_dialect: DummyDialect):
        """Tests DROP SCHEMA CASCADE statement."""
        drop_schema = DropSchemaExpression(
            dummy_dialect,
            schema_name="legacy_schema",
            cascade=True
        )
        sql, params = drop_schema.to_sql()

        assert sql == 'DROP SCHEMA "legacy_schema" CASCADE'
        assert params == ()

    def test_drop_schema_if_exists_with_cascade(self, dummy_dialect: DummyDialect):
        """Tests DROP SCHEMA IF EXISTS CASCADE statement."""
        drop_schema = DropSchemaExpression(
            dummy_dialect,
            schema_name="deprecated_schema",
            if_exists=True,
            cascade=True
        )
        sql, params = drop_schema.to_sql()

        assert sql == 'DROP SCHEMA IF EXISTS "deprecated_schema" CASCADE'
        assert params == ()

    @pytest.mark.parametrize("schema_name,expected_identifier", [
        pytest.param("simple_schema", '"simple_schema"', id="simple_name"),
        pytest.param("schema_with_underscores", '"schema_with_underscores"', id="underscore_name"),
        pytest.param("SchemaWithCamelCase", '"SchemaWithCamelCase"', id="camelcase_name"),
        pytest.param("schema-with-hyphens", '"schema-with-hyphens"', id="hyphen_name"),
        pytest.param("schema with spaces", '"schema with spaces"', id="spaced_name"),
    ])
    def test_create_schema_various_names(self, dummy_dialect: DummyDialect, schema_name, expected_identifier):
        """Tests CREATE SCHEMA with various schema name formats."""
        create_schema = CreateSchemaExpression(
            dummy_dialect,
            schema_name=schema_name
        )
        sql, params = create_schema.to_sql()

        assert f'CREATE SCHEMA {expected_identifier}' == sql
        assert params == ()

    def test_schema_roundtrip_creation_and_deletion(self, dummy_dialect: DummyDialect):
        """Tests creating a schema and then dropping it."""
        create_schema = CreateSchemaExpression(
            dummy_dialect,
            schema_name="roundtrip_test"
        )
        create_sql, create_params = create_schema.to_sql()

        drop_schema = DropSchemaExpression(
            dummy_dialect,
            schema_name="roundtrip_test"
        )
        drop_sql, drop_params = drop_schema.to_sql()

        assert create_sql == 'CREATE SCHEMA "roundtrip_test"'
        assert drop_sql == 'DROP SCHEMA "roundtrip_test"'
        assert create_params == ()
        assert drop_params == ()

    def test_schema_with_special_characters(self, dummy_dialect: DummyDialect):
        """Tests schema names with special characters are properly quoted."""
        create_schema = CreateSchemaExpression(
            dummy_dialect,
            schema_name='schema"name'
        )
        sql, params = create_schema.to_sql()

        assert sql == 'CREATE SCHEMA "schema""name"'
        assert params == ()

    def test_schema_with_unicode_characters(self, dummy_dialect: DummyDialect):
        """Tests schema names with unicode characters."""
        create_schema = CreateSchemaExpression(
            dummy_dialect,
            schema_name="用户模式"
        )
        sql, params = create_schema.to_sql()

        assert sql == 'CREATE SCHEMA "用户模式"'
        assert params == ()
