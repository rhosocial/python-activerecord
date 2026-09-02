# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_expression_edge_branches.py
"""Tests for expression edge branches and backend-specific behaviors.

Covers:
- Generic expression branch coverage (cast/alias on operators, get_params
  fallback paths, trim direction validation, partition clause validation).
- Generic introspection expression construction / get_params (these are
  dialect-independent structure methods).
- Backend-specific behaviors that Dummy deliberately does NOT implement:
  introspection to_sql() and ``date_diff`` must raise.
"""

import warnings

import pytest

from rhosocial.activerecord.backend.expression import (
    Column,
    Literal,
    RawSQLExpression,
    QualifiedIdentifierExpression,
    WildcardExpression,
)
from rhosocial.activerecord.backend.expression.types import (
    ArrayType,
    CharType,
    CustomType,
    DateTimeType,
    DecimalType,
    FloatType,
    IntegerType,
    IntervalType,
    TimeType,
    TimeTzType,
    TimestampType,
    TimestampTzType,
    VarCharType,
)
from rhosocial.activerecord.backend.expression.introspection import (
    ColumnInfoExpression,
    DatabaseInfoExpression,
    ForeignKeyExpression,
    IndexInfoExpression,
    TableInfoExpression,
    TableListExpression,
    TriggerInfoExpression,
    TriggerListExpression,
    ViewInfoExpression,
    ViewListExpression,
)
from rhosocial.activerecord.backend.expression.operators import BinaryArithmeticExpression
from rhosocial.activerecord.backend.expression.statements import (
    OnConflictClause,
    PartitionClause,
    PartitionStrategy,
)
from rhosocial.activerecord.backend.expression.functions.string import trim
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect


@pytest.fixture
def dialect() -> DummyDialect:
    return DummyDialect()


class TestCoreExpressionBranches:
    """Branch coverage for core/operator expressions."""

    def test_literal_cast_and_alias(self, dialect):
        expr = Literal(dialect, 42).cast("DECIMAL").as_("n")
        sql, params = expr.to_sql()
        assert "CAST" in sql or "DECIMAL" in sql
        assert "AS" in sql
        assert params == (42,)

    def test_qualified_identifier_with_schema(self, dialect):
        expr = QualifiedIdentifierExpression(dialect, schema="app", name="users")
        sql, params = expr.to_sql()
        assert sql == '"app"."users"'
        assert params == ()

    def test_qualified_identifier_without_schema(self, dialect):
        expr = QualifiedIdentifierExpression(dialect, name="users")
        sql, params = expr.to_sql()
        assert sql == '"users"'
        assert params == ()

    def test_wildcard_expression_basic(self, dialect):
        expr = WildcardExpression(dialect)
        sql, params = expr.to_sql()
        assert sql == "*"
        assert params == ()

    def test_wildcard_expression_qualified(self, dialect):
        expr = WildcardExpression(dialect, table="users", schema_name="app")
        sql, params = expr.to_sql()
        assert "*" in sql
        assert params == ()

    def test_binary_arithmetic_with_cast(self, dialect):
        expr = BinaryArithmeticExpression(dialect, "+", Column(dialect, "price"), Literal(dialect, 10))
        expr.cast("DECIMAL")
        aliased = expr.as_("total")
        sql, params = aliased.to_sql()
        assert "CAST" in sql or "DECIMAL" in sql
        assert "total" in sql

    def test_raw_sql_expression(self, dialect):
        expr = RawSQLExpression(dialect, "NOW()")
        sql, params = expr.to_sql()
        assert sql == "NOW()"
        assert params == ()


class TestGetParamsFallback:
    """get_params() attribute lookup fallback paths."""

    def test_var_positional_params(self, dialect):
        # An expression subclass whose __init__ uses *args: get_params collects
        # them as a list.
        from rhosocial.activerecord.backend.expression.bases import SQLValueExpression

        class ArgsExpr(SQLValueExpression):
            def __init__(self, dialect, *values, **kwargs):
                super().__init__(dialect)
                self._values = list(values)
                self.kwargs = dict(kwargs)
                self.extra = kwargs.get("extra")

            def to_sql(self):
                return "x", ()

        expr = ArgsExpr(dialect, 1, 2, 3, extra="x")
        params = expr.get_params()
        assert "values" in params
        assert params["values"] == [1, 2, 3]
        assert params["extra"] == "x"

    def test_get_params_missing_attribute_warns(self, dialect):
        # A subclass whose declared __init__ parameter has no matching
        # _name/name attribute triggers a warning.
        from rhosocial.activerecord.backend.expression.bases import SQLValueExpression

        class MissingAttrExpr(SQLValueExpression):
            def __init__(self, dialect, some_param):
                super().__init__(dialect)
                self._x = 1

            def to_sql(self):
                return "x", ()

        expr = MissingAttrExpr(dialect, 123)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            params = expr.get_params()
        assert any("get_params" in str(w.message) for w in caught)
        assert "some_param" not in params


class TestTrimDirectionValidation:
    """TRIM direction validation."""

    def test_valid_direction(self, dialect):
        expr = trim(dialect, "x", direction="BOTH")
        sql, params = expr.to_sql()
        assert sql
        assert params

    def test_invalid_direction(self, dialect):
        with pytest.raises(ValueError):
            trim(dialect, "x", direction="INVALID")


class TestPartitionClauseValidation:
    """PartitionClause validation branches."""

    def test_invalid_method_type(self, dialect):
        with pytest.raises(TypeError):
            PartitionClause(dialect, "bad", [Column(dialect, "id")])

    def test_missing_keys(self, dialect):
        with pytest.raises(ValueError):
            PartitionClause(dialect, PartitionStrategy.HASH, [])

    def test_non_expression_key(self, dialect):
        with pytest.raises(TypeError):
            PartitionClause(dialect, PartitionStrategy.HASH, ["id"])

    def test_invalid_dialect_options(self, dialect):
        with pytest.raises(TypeError):
            PartitionClause(dialect, PartitionStrategy.HASH, [Column(dialect, "id")], dialect_options="bad")

    def test_constructs_with_valid_args(self, dialect):
        clause = PartitionClause(dialect, PartitionStrategy.HASH, [Column(dialect, "id")])
        assert clause.method == PartitionStrategy.HASH.value
        assert len(clause.keys) == 1
        assert clause.dialect_options == {}

    def test_non_string_enum_value(self, dialect):
        from enum import Enum

        class Weird(Enum):
            X = 123

        class MyPartition(PartitionClause):
            strategy_type = Weird

        with pytest.raises(TypeError):
            MyPartition(dialect, Weird.X, [Column(dialect, "id")])

    def test_to_sql_unsupported(self, dialect):
        clause = PartitionClause(dialect, PartitionStrategy.HASH, [Column(dialect, "id")])
        with pytest.raises(Exception) as exc_info:
            clause.to_sql()
        assert "partition" in str(exc_info.value).lower()

    def test_to_sql_protocol_not_implemented(self):
        class MinimalDialect:
            name = "minimal"

        clause = PartitionClause(MinimalDialect(), PartitionStrategy.HASH, [Column(dialect, "id")])
        with pytest.raises(Exception) as exc_info:
            clause.to_sql()
        assert ("ProtocolNotImplementedError" in type(exc_info.value).__name__
                or "PartitionSupport" in str(exc_info.value))


class TestOnConflictValidation:
    """INSERT on_conflict validation branch."""

    def test_non_list_on_conflict(self, dialect):
        from rhosocial.activerecord.backend.expression.statements import (
            InsertExpression,
            ValuesSource,
        )

        source = ValuesSource(dialect, [[Literal(dialect, 1)]])
        with pytest.raises(TypeError):
            InsertExpression(dialect, into="users", source=source, on_conflict="bad")

    def test_non_onconflict_clause_item(self, dialect):
        from rhosocial.activerecord.backend.expression.statements import (
            InsertExpression,
            ValuesSource,
        )

        source = ValuesSource(dialect, [[Literal(dialect, 1)]])
        with pytest.raises(TypeError):
            InsertExpression(dialect, into="users", source=source, on_conflict=["bad", "worse"])

    def test_valid_on_conflict(self, dialect):
        from rhosocial.activerecord.backend.expression.statements import (
            InsertExpression,
            ValuesSource,
        )

        source = ValuesSource(dialect, [[Literal(dialect, 1)]])
        conflict = OnConflictClause(dialect, ["id"], do_nothing=True)
        expr = InsertExpression(dialect, into="users", source=source, on_conflict=[conflict])
        assert expr is not None
        assert expr.on_conflict == [conflict]

    def test_validate_with_on_conflict(self, dialect):
        from rhosocial.activerecord.backend.expression.statements import (
            InsertExpression,
            ValuesSource,
        )

        source = ValuesSource(dialect, [[Literal(dialect, 1)]])
        conflict = OnConflictClause(dialect, ["id"], do_nothing=True)
        expr = InsertExpression(dialect, into="users", source=source, on_conflict=[conflict])
        expr.validate()

    def test_validate_on_conflict_bad_item(self, dialect):
        from rhosocial.activerecord.backend.expression.statements import (
            InsertExpression,
            ValuesSource,
        )

        source = ValuesSource(dialect, [[Literal(dialect, 1)]])
        conflict = OnConflictClause(dialect, ["id"], do_nothing=True)
        expr = InsertExpression(dialect, into="users", source=source, on_conflict=[conflict])
        expr.on_conflict = [conflict, "bad"]
        with pytest.raises(TypeError):
            expr.validate()


class TestIntrospectionExpressionStructure:
    """Generic introspection expression construction (dialect-independent)."""

    def test_table_list_include_system(self, dialect):
        expr = TableListExpression(dialect).include_system(True)
        assert expr.get_params()["include_system"] is True

    def test_table_list_table_type(self, dialect):
        expr = TableListExpression(dialect).table_type("VIEW")
        assert expr.get_params()["table_type"] == "VIEW"

    def test_table_info_include_indexes(self, dialect):
        expr = TableInfoExpression(dialect, "users").include_indexes(True)
        assert expr.get_params()["include_indexes"] is True

    def test_table_info_include_foreign_keys(self, dialect):
        expr = TableInfoExpression(dialect, "users").include_foreign_keys(True)
        assert expr.get_params()["include_foreign_keys"] is True

    def test_column_info_include_hidden(self, dialect):
        expr = ColumnInfoExpression(dialect, "users").include_hidden(True)
        assert expr.get_params()["include_hidden"] is True

    def test_index_info_table_name(self, dialect):
        expr = IndexInfoExpression(dialect, "users")
        assert expr.get_params()["table"] == "users"

    def test_foreign_key_table_name(self, dialect):
        expr = ForeignKeyExpression(dialect, "users")
        assert expr.get_params()["table"] == "users"

    def test_view_list(self, dialect):
        expr = ViewListExpression(dialect)
        assert "include_system" in expr.get_params()

    def test_view_info(self, dialect):
        expr = ViewInfoExpression(dialect, "my_view").include_columns(True)
        params = expr.get_params()
        assert params["view_name"] == "my_view"
        assert params["include_columns"] is True

    def test_trigger_info(self, dialect):
        expr = TriggerInfoExpression(dialect, "my_trigger").for_table("users")
        params = expr.get_params()
        assert params["trigger"] == "my_trigger"
        assert params["table"] == "users"

    def test_trigger_list(self, dialect):
        expr = TriggerInfoExpression(dialect, "t").for_table("users")
        assert "table" in expr.get_params()

    def test_table_info_table_name_setter(self, dialect):
        expr = TableInfoExpression(dialect, "old").table("new")
        assert expr.get_params()["table"] == "new"

    def test_column_info_table_name_setter(self, dialect):
        expr = ColumnInfoExpression(dialect, "old").table("new")
        assert expr.get_params()["table"] == "new"

    def test_index_info_table_name_setter(self, dialect):
        expr = IndexInfoExpression(dialect, "old").table("new")
        assert expr.get_params()["table"] == "new"

    def test_foreign_key_table_name_setter(self, dialect):
        expr = ForeignKeyExpression(dialect, "old").table("new")
        assert expr.get_params()["table"] == "new"

    def test_view_info_view_name_setter(self, dialect):
        expr = ViewInfoExpression(dialect, "old").view_name("new")
        assert expr.get_params()["view_name"] == "new"


class TestCrossTypeDataTypes:
    """Cross-type inequality branches (type(self) is not type(other))."""

    def test_datetime_types_inequality(self):
        assert TimeType(precision=6) != DateTimeType(precision=6)
        assert TimeTzType(precision=2) != TimeType(precision=2)
        assert DateTimeType(precision=6) != TimestampType(precision=6)
        assert TimestampType(precision=6) != TimestampTzType(precision=6)
        assert TimestampTzType(precision=0) != DateTimeType(precision=0)
        assert IntervalType(fields="YEAR") != TimeType(precision=1)

    def test_string_types_inequality(self):
        assert CharType(length=10) != VarCharType(length=10)
        assert VarCharType(length=10) != CharType(length=10)
        assert CharType(length=10) != CustomType(raw="CHAR(10)")

    def test_numeric_types_inequality(self):
        assert FloatType(precision=24) != DecimalType(precision=10, scale=2)
        assert DecimalType(precision=10, scale=2) != FloatType(precision=24)
        assert FloatType(precision=24) != IntegerType()

    def test_array_and_custom_inequality(self):
        assert ArrayType(element_type=IntegerType()) != ArrayType(element_type=CharType(length=10))
        assert ArrayType(element_type=IntegerType()) != CharType(length=10)
        assert ArrayType(element_type=IntegerType()).is_equivalent(CharType(length=10)) is False
        assert CustomType(raw="geometry") != IntegerType()

    def test_hash_branches(self):
        assert hash(CharType(length=10)) == hash(CharType(length=10))
        assert hash(DecimalType(precision=10, scale=2)) == hash(DecimalType(precision=10, scale=2))

    def test_timetz_timestamptz_equality(self):
        assert TimeTzType(precision=2) == TimeTzType(precision=2)
        assert TimeTzType(precision=2) != TimeTzType(precision=3)
        assert TimestampTzType(precision=0) == TimestampTzType(precision=0)
        assert TimestampTzType(precision=0) != TimestampTzType(precision=1)

    def test_trigger_info_trigger_name_setter(self, dialect):
        from rhosocial.activerecord.backend.expression.introspection import TriggerInfoExpression

        expr = TriggerInfoExpression(dialect, "old").trigger("new")
        assert expr.get_params()["trigger"] == "new"


class TestXmlFunctionsTupleArgs:
    """xmlattributes/xmlforest accept (value, name) tuples."""

    def test_xmlattributes_plain(self, dialect):
        from rhosocial.activerecord.backend.expression.functions.xml import xmlattributes

        expr = xmlattributes(dialect, "v")
        sql, params = expr.to_sql()
        assert "XMLATTRIBUTES" in sql

    def test_xmlattributes_tuple(self, dialect):
        from rhosocial.activerecord.backend.expression.functions.xml import xmlattributes

        expr = xmlattributes(dialect, (Column(dialect, "id"), "the_id"))
        sql, params = expr.to_sql()
        assert "XMLATTRIBUTES" in sql
        assert "the_id" in sql

    def test_xmlforest_plain(self, dialect):
        from rhosocial.activerecord.backend.expression.functions.xml import xmlforest

        expr = xmlforest(dialect, "v")
        sql, params = expr.to_sql()
        assert "XMLFOREST" in sql

    def test_xmlforest_tuple(self, dialect):
        from rhosocial.activerecord.backend.expression.functions.xml import xmlforest

        expr = xmlforest(dialect, (Column(dialect, "name"), "full_name"))
        sql, params = expr.to_sql()
        assert "XMLFOREST" in sql
        assert "full_name" in sql


class TestColumnDefinitionValidation:
    """ColumnDefinition data_type validation."""

    def test_non_data_type_raises(self, dialect):
        from rhosocial.activerecord.backend.expression.statements.ddl_table import ColumnDefinition

        with pytest.raises(TypeError):
            ColumnDefinition(name="x", data_type="BAD")

    def test_valid_data_type(self, dialect):
        from rhosocial.activerecord.backend.expression.statements.ddl_table import ColumnDefinition
        from rhosocial.activerecord.backend.expression.types import IntegerType

        col = ColumnDefinition(name="id", data_type=IntegerType())
        assert col.name == "id"
        assert isinstance(col.data_type, IntegerType)


class TestIntrospectionToSqlUnsupported:
    """Introspection to_sql() is backend-specific and unsupported on Dummy."""

    @pytest.mark.parametrize(
        "factory",
        [
            lambda d: DatabaseInfoExpression(d),
            lambda d: TableListExpression(d),
            lambda d: TableInfoExpression(d, "users"),
            lambda d: ColumnInfoExpression(d, "users"),
            lambda d: IndexInfoExpression(d, "users"),
            lambda d: ForeignKeyExpression(d, "users"),
            lambda d: ViewListExpression(d),
            lambda d: ViewInfoExpression(d, "v"),
            lambda d: TriggerListExpression(d),
            lambda d: TriggerInfoExpression(d, "t"),
        ],
    )
    def test_to_sql_raises(self, dialect, factory):
        expr = factory(dialect)
        with pytest.raises(Exception) as exc_info:
            expr.to_sql()
        assert "support" in str(exc_info.value) or "introspection" in str(exc_info.value).lower()
