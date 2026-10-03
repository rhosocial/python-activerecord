# tests/rhosocial/activerecord_test/feature/basic/ddl/test_ddl_schema_propagation.py
"""A model's namespace reaches the DDL built for it.

``__schema_name__`` used to stop at the query layer: it qualified SELECT,
INSERT, UPDATE and DELETE, while every DDL statement had to be handed a
namespace by hand at each call site. These tests cover the factories that
close that gap -- each one is reached through the model's table reference, so
declaring the namespace once is enough.
"""

import pytest

from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.expression.core import TableExpression
from rhosocial.activerecord.backend.expression.statements.ddl_alter import DropColumn
from rhosocial.activerecord.model import ActiveRecord


class Order(ActiveRecord):
    __table_name__ = "orders"
    __schema_name__ = "app"
    id: int
    name: str


class Plain(ActiveRecord):
    __table_name__ = "plain"
    id: int


@pytest.fixture
def namespaced():
    """A dialect that has namespaces to qualify into.

    SQLite, the built-in dialect, has none: a model with ``__schema_name__``
    is refused there by design, which is a different behaviour and is
    covered by the schema-capability tests.
    """
    from rhosocial.activerecord.backend.impl.dummy.backend import DummyDialect

    return DummyDialect()


class TestTableReference:
    def test_carries_the_declared_namespace(self, namespaced):
        assert Order.build_table_reference(namespaced).to_sql()[0] == '"app"."orders"'

    def test_unqualified_when_the_model_declares_none(self, namespaced):
        assert Plain.build_table_reference(namespaced).to_sql()[0] == '"plain"'

    def test_alias_is_carried(self, namespaced):
        sql = Order.build_table_reference(namespaced, alias="o").to_sql()[0]
        assert sql == '"app"."orders" AS "o"'


class TestTableStatements:
    def test_drop_table(self, namespaced):
        sql = Order.build_drop_table_statement(namespaced, if_exists=True).to_sql()[0]
        assert sql == 'DROP TABLE IF EXISTS "app"."orders"'

    def test_truncate(self, namespaced):
        sql = Order.build_truncate_statement(namespaced).to_sql()[0]
        assert sql == 'TRUNCATE TABLE "app"."orders"'

    def test_alter_table(self, namespaced):
        statement = Order.build_alter_table_statement(
            namespaced, [DropColumn(namespaced, "legacy")]
        )
        assert statement.to_sql()[0] == 'ALTER TABLE "app"."orders" DROP COLUMN "legacy"'

    def test_every_statement_agrees_on_the_namespace(self, namespaced):
        """The point of routing through one reference: they cannot drift."""
        statements = [
            Order.build_drop_table_statement(namespaced),
            Order.build_truncate_statement(namespaced),
            Order.build_alter_table_statement(namespaced, []),
            Order.build_create_index_statement(namespaced, "idx", ["name"]),
            Order.build_drop_index_statement(namespaced, "idx"),
        ]
        rendered = [s.to_sql()[0] for s in statements]
        for sql in rendered:
            assert '"app"."orders"' in sql, sql
            # The index name is qualified too, so two occurrences are correct
            # there and one everywhere else.
            expected = 2 if "INDEX" in sql else 1
            assert sql.count('"app".') == expected, sql


class TestIndexStatements:
    def test_index_inherits_the_model_namespace_by_default(self, namespaced):
        sql = Order.build_create_index_statement(
            namespaced, "idx_orders_name", ["name"]
        ).to_sql()[0]
        assert sql == 'CREATE INDEX "app"."idx_orders_name" ON "app"."orders" ("name")'

    def test_index_can_be_placed_in_another_namespace(self, namespaced):
        sql = Order.build_create_index_statement(
            namespaced, "idx", ["name"], index_schema_name="reporting"
        ).to_sql()[0]
        assert sql == 'CREATE INDEX "reporting"."idx" ON "app"."orders" ("name")'

    def test_drop_index_carries_both_namespaces(self, namespaced):
        statement = Order.build_drop_index_statement(
            namespaced, "idx", index_schema_name="reporting", if_exists=True
        )
        assert statement.index_name == "idx"
        assert statement.table.schema_name == "app"
        assert statement.schema_name == "reporting"


class TestCreateTable:
    def test_table_argument_is_a_qualified_reference(self, namespaced):
        statement = Order.build_create_table_statement(namespaced, columns=[])
        assert isinstance(statement.table, TableExpression)
        assert statement.table.schema_name == "app"
        assert statement.table.name == "orders"


class TestDialectsWithoutNamespaces:
    def test_a_dialect_without_namespaces_refuses_a_qualified_model(self):
        """SQLite has no namespace, so the model is told rather than fudged."""
        from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect

        with pytest.raises(UnsupportedFeatureError):
            Order.build_table_reference(SQLiteDialect()).to_sql()

    def test_an_unqualified_model_is_fine_there(self):
        from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect

        assert Plain.build_table_reference(SQLiteDialect()).to_sql()[0] == '"plain"'