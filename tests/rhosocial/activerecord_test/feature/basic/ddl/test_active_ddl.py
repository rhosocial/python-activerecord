# tests/rhosocial/activerecord_test/feature/basic/ddl/test_active_ddl.py
"""Tests for the source-bound ActiveDDL expression factory."""

from rhosocial.activerecord.backend.expression.statements.ddl_alter import (
    AlterTableExpression,
    DropColumn,
)
from rhosocial.activerecord.backend.expression.statements.ddl_comment import (
    CommentObjectType,
    CommentOnExpression,
)
from rhosocial.activerecord.backend.expression.statements.ddl_index import CreateIndexExpression
from rhosocial.activerecord.backend.expression.statements.ddl_table import (
    CreateTableExpression,
    IndexDefinition,
)
from rhosocial.activerecord.backend.expression.statements.ddl_view import (
    CreateViewExpression,
    DropViewExpression,
)
from rhosocial.activerecord.backend.impl.dummy import DummyDialect
from rhosocial.activerecord.base import DDLSource
from rhosocial.activerecord.ddl import ActiveDDL, AsyncActiveDDL


class FakeSource:
    """Minimal DDLSource implementation with no ActiveRecord dependency."""

    @classmethod
    def table_name(cls):
        return "fake_records"

    @classmethod
    def schema_name(cls):
        return None

    @classmethod
    def primary_key_columns(cls):
        return ("id",)

    @classmethod
    def is_composite_pk(cls):
        return False

    @classmethod
    def ddl_field_names(cls):
        return ("id", "name", "computed")

    @classmethod
    def is_derived_field(cls, field):
        return field == "computed"

    @classmethod
    def field_python_type(cls, field):
        return int if field == "id" else str

    @classmethod
    def field_is_optional(cls, field):
        return False

    @classmethod
    def column_name(cls, field):
        return field

    @classmethod
    def column_type(cls, field):
        return None

    @classmethod
    def column_constraints(cls, field):
        return []

    @classmethod
    def column_attributes(cls, field):
        return []

    @classmethod
    def column_indexes(cls, field):
        return []

    @classmethod
    def column_comment(cls, field):
        return None

    @classmethod
    def generated_column(cls, field):
        return None

    @classmethod
    def column_options(cls, field):
        return None

    @classmethod
    def table_options(cls):
        return None

    @classmethod
    def table_storage_options(cls):
        return None

    @classmethod
    def table_partition(cls):
        return None

    @classmethod
    def table_indexes(cls):
        return [IndexDefinition(None, name="idx_fake_records_name", columns=["name"])]

    @classmethod
    def create_table_statement_classes(cls):
        return None

    @classmethod
    def table_constraints(cls):
        return []

    @classmethod
    def table_inherits(cls):
        return None

    @classmethod
    def table_tablespace(cls):
        return None


class FakeBackend:
    """Backend double exposing only the bound dialect."""

    def __init__(self):
        self.dialect = DummyDialect()


def test_active_ddl_generates_expressions_without_active_record():
    assert isinstance(FakeSource, DDLSource)
    ddl = ActiveDDL(FakeSource, FakeBackend())

    create_table = ddl.create_table()
    assert isinstance(create_table, CreateTableExpression)
    assert [column.name for column in create_table.columns] == ["id", "name"]

    create_index = ddl.create_index("idx_fake_records_name", ("name",))
    assert isinstance(create_index, CreateIndexExpression)
    assert create_index.index_name == "idx_fake_records_name"

    derived_index = ddl.create_index()
    assert derived_index.index_name == "idx_fake_records_name"
    assert ddl.drop_index().index_name == "idx_fake_records_name"

    alter_table = ddl.alter_table([DropColumn(ddl.dialect, "name")])
    assert isinstance(alter_table, AlterTableExpression)

    comment = ddl.comment_on(CommentObjectType.COLUMN, "fake_records.name", "Name")
    assert isinstance(comment, CommentOnExpression)
    assert ddl.comment_on().object_name == "fake_records"

    view = ddl.create_view("fake_records_view", object())
    assert isinstance(view, CreateViewExpression)
    assert isinstance(ddl.drop_view("fake_records_view"), DropViewExpression)

    assert not hasattr(ddl, "to_sql")
    assert not hasattr(ddl, "execute")
    assert not hasattr(ddl, "create_indexes")
    assert not hasattr(ddl, "drop_indexes")


def test_active_ddl_exposes_partition_lifecycle_factory():
    ddl = ActiveDDL(FakeSource, FakeBackend())
    lifecycle = ddl.partition_lifecycle()
    assert lifecycle.table.name == "fake_records"
    assert lifecycle.capabilities().operations == frozenset()


def test_async_active_ddl_generates_the_same_expression_surface():
    sync_ddl = ActiveDDL(FakeSource, FakeBackend())
    async_ddl = AsyncActiveDDL(FakeSource, FakeBackend())

    assert type(async_ddl.create_table()) is type(sync_ddl.create_table())
    assert not hasattr(async_ddl, "to_sql")
    assert not hasattr(async_ddl, "execute")
