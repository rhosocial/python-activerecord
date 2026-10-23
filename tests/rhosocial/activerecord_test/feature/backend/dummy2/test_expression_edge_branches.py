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


from rhosocial.activerecord.backend.expression.functions import cast
import pytest

from rhosocial.activerecord.backend.expression.objects import Table
from rhosocial.activerecord.backend.expression.sources import NamedRelationRef
from rhosocial.activerecord.backend.expression import (
    Column,
    Literal,
    RawSQL,
    QualifiedIdentifier,
    AllColumnsWildcard,
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
    ColumnInfoQueryStatement,
    DatabaseInfoQueryStatement,
    ForeignKeyQueryStatement,
    IndexInfoQueryStatement,
    TableInfoQueryStatement,
    TableListQueryStatement,
    TriggerInfoQueryStatement,
    TriggerListQueryStatement,
    ViewInfoQueryStatement,
    ViewListQueryStatement,
)
from rhosocial.activerecord.backend.expression.operators import ArithmeticOperation
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
        expr = cast(dialect, Literal(dialect, 42), DecimalType(dialect)).as_("n")
        sql, params = expr.to_sql()
        assert "CAST" in sql or "DECIMAL" in sql
        assert "AS" in sql
        assert params == (42,)

    def test_qualified_identifier_with_schema(self, dialect):
        expr = QualifiedIdentifier(dialect, schema="app", name="users")
        sql, params = expr.to_sql()
        assert sql == '"app"."users"'
        assert params == ()

    def test_qualified_identifier_without_schema(self, dialect):
        expr = QualifiedIdentifier(dialect, name="users")
        sql, params = expr.to_sql()
        assert sql == '"users"'
        assert params == ()

    def test_wildcard_expression_basic(self, dialect):
        expr = AllColumnsWildcard(dialect)
        sql, params = expr.to_sql()
        assert sql == "*"
        assert params == ()

    def test_wildcard_expression_qualified(self, dialect):
        expr = AllColumnsWildcard(dialect, relation=NamedRelationRef(dialect, Table(dialect, "users")))
        sql, params = expr.to_sql()
        assert "*" in sql
        assert params == ()

    def test_arithmetic_operation_with_cast(self, dialect):
        expr = ArithmeticOperation(dialect, "add", Column(dialect, "price"), Literal(dialect, 10))
        casted = expr.cast(DecimalType(dialect))
        aliased = casted.as_("total")
        sql, params = aliased.to_sql()
        assert "CAST" in sql or "DECIMAL" in sql
        assert "total" in sql

    def test_raw_sql_expression(self, dialect):
        expr = RawSQL(dialect, "NOW()")
        sql, params = expr.to_sql()
        assert sql == "NOW()"
        assert params == ()


class TestGetParamsFallback:
    """get_params() attribute lookup fallback paths."""

    def test_var_positional_params(self, dialect):
        # An expression subclass whose __init__ uses *args: get_params collects
        # them as a list.
        from rhosocial.activerecord.backend.expression.bases import SQLValue

        class ArgsExpr(SQLValue):
            def __init__(self, dialect, *values, **kwargs):
                super().__init__(dialect)
                self.values = list(values)
                self.kwargs = dict(kwargs)
                self.extra = kwargs.get("extra")

            def to_sql(self):
                return "x", ()

        expr = ArgsExpr(dialect, 1, 2, 3, extra="x")
        params = expr.get_params()
        assert "values" in params
        assert params["values"] == [1, 2, 3]
        assert params["extra"] == "x"

    def test_get_params_missing_attribute_raises(self, dialect):
        """A parameter the class did not store is a defect, and it says so.

        This used to warn and carry on, which put the omission in the artifact
        with nothing to show for it: a serialized node that reconstructs into a
        different tree. Reading the parameter's own name has no fallback to
        reach for, so the AttributeError names the class and the parameter.
        """
        from rhosocial.activerecord.backend.expression.bases import SQLValue

        class MissingAttrExpr(SQLValue):
            def __init__(self, dialect, some_param):
                super().__init__(dialect)
                self._x = 1

            def to_sql(self):
                return "x", ()

        expr = MissingAttrExpr(dialect, 123)
        with pytest.raises(AttributeError, match="some_param"):
            expr.get_params()


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

    def test_to_sql_protocol_not_implemented(self, dialect):
        # The dialect property validates the binding: a minimal non-dialect
        # object is rejected at construction time (TypeError).
        class MinimalDialect:
            name = "minimal"

        with pytest.raises(TypeError, match="SQLDialectBase instance"):
            PartitionClause(MinimalDialect(), PartitionStrategy.HASH, [Column(dialect, "id")])

    def test_to_sql_protocol_partition_unsupported(self, dialect):
        # A SQLDialectBase subclass that lacks format_partition_clause raises
        # ProtocolNotImplementedError at render time.
        class MinimalDialect(DummyDialect):
            pass

        clause = PartitionClause(MinimalDialect(), PartitionStrategy.HASH, [Column(dialect, "id")])
        with pytest.raises(Exception) as exc_info:
            clause.to_sql()
        assert ("ProtocolNotImplementedError" in type(exc_info.value).__name__
                or "PartitionSupport" in str(exc_info.value))


class TestOnConflictValidation:
    """INSERT on_conflict validation branch."""

    def test_non_list_on_conflict(self, dialect):
        from rhosocial.activerecord.backend.expression.statements import (
            InsertStatement,
            ValuesSource,
        )

        source = ValuesSource(dialect, [[Literal(dialect, 1)]])
        with pytest.raises(TypeError):
            InsertStatement(dialect, into=Table(dialect, 'users'), source=source, on_conflict="bad")

    def test_non_onconflict_clause_item(self, dialect):
        from rhosocial.activerecord.backend.expression.statements import (
            InsertStatement,
            ValuesSource,
        )

        source = ValuesSource(dialect, [[Literal(dialect, 1)]])
        with pytest.raises(TypeError):
            InsertStatement(dialect, into=Table(dialect, 'users'), source=source, on_conflict=["bad", "worse"])

    def test_valid_on_conflict(self, dialect):
        from rhosocial.activerecord.backend.expression.statements import (
            InsertStatement,
            ValuesSource,
        )

        source = ValuesSource(dialect, [[Literal(dialect, 1)]])
        conflict = OnConflictClause(dialect, ["id"], do_nothing=True)
        expr = InsertStatement(dialect, into=Table(dialect, 'users'), source=source, on_conflict=[conflict])
        assert expr is not None
        assert expr.on_conflict == [conflict]

    def test_validate_with_on_conflict(self, dialect):
        from rhosocial.activerecord.backend.expression.statements import (
            InsertStatement,
            ValuesSource,
        )

        source = ValuesSource(dialect, [[Literal(dialect, 1)]])
        conflict = OnConflictClause(dialect, ["id"], do_nothing=True)
        expr = InsertStatement(dialect, into=Table(dialect, 'users'), source=source, on_conflict=[conflict])
        expr.validate()

    def test_validate_on_conflict_bad_item(self, dialect):
        from rhosocial.activerecord.backend.expression.statements import (
            InsertStatement,
            ValuesSource,
        )

        source = ValuesSource(dialect, [[Literal(dialect, 1)]])
        conflict = OnConflictClause(dialect, ["id"], do_nothing=True)
        expr = InsertStatement(dialect, into=Table(dialect, 'users'), source=source, on_conflict=[conflict])
        expr.on_conflict = [conflict, "bad"]
        with pytest.raises(TypeError):
            expr.validate()


class TestIntrospectionExpressionStructure:
    """Generic introspection expression construction (dialect-independent)."""

    def test_table_list_include_system(self, dialect):
        expr = TableListQueryStatement(dialect).with_include_system(True)
        assert expr.get_params()["include_system"] is True

    def test_table_list_table_type(self, dialect):
        expr = TableListQueryStatement(dialect).with_table_type("VIEW")
        assert expr.get_params()["table_type"] == "VIEW"

    def test_table_info_include_indexes(self, dialect):
        expr = TableInfoQueryStatement(dialect, "users").with_include_indexes(True)
        assert expr.get_params()["include_indexes"] is True

    def test_table_info_include_foreign_keys(self, dialect):
        expr = TableInfoQueryStatement(dialect, "users").with_include_foreign_keys(True)
        assert expr.get_params()["include_foreign_keys"] is True

    def test_column_info_include_hidden(self, dialect):
        expr = ColumnInfoQueryStatement(dialect, "users").with_include_hidden(True)
        assert expr.get_params()["include_hidden"] is True

    def test_index_info_table_name(self, dialect):
        expr = IndexInfoQueryStatement(dialect, "users")
        assert expr.get_params()["table_name"] == "users"

    def test_foreign_key_table_name(self, dialect):
        expr = ForeignKeyQueryStatement(dialect, "users")
        assert expr.get_params()["table_name"] == "users"

    def test_view_list(self, dialect):
        expr = ViewListQueryStatement(dialect)
        assert "include_system" in expr.get_params()

    def test_view_info(self, dialect):
        expr = ViewInfoQueryStatement(dialect, "my_view").with_include_columns(True)
        params = expr.get_params()
        assert params["view_name"] == "my_view"
        assert params["include_columns"] is True

    def test_trigger_info(self, dialect):
        expr = TriggerInfoQueryStatement(dialect, "my_trigger").for_table("users")
        params = expr.get_params()
        assert params["trigger_name"] == "my_trigger"
        assert params["table_name"] == "users"

    def test_trigger_list(self, dialect):
        expr = TriggerInfoQueryStatement(dialect, "t").for_table("users")
        assert "table_name" in expr.get_params()

    def test_table_info_table_name_setter(self, dialect):
        expr = TableInfoQueryStatement(dialect, "old").with_table_name("new")
        assert expr.get_params()["table_name"] == "new"

    def test_column_info_table_name_setter(self, dialect):
        expr = ColumnInfoQueryStatement(dialect, "old").with_table_name("new")
        assert expr.get_params()["table_name"] == "new"

    def test_index_info_table_name_setter(self, dialect):
        expr = IndexInfoQueryStatement(dialect, "old").with_table_name("new")
        assert expr.get_params()["table_name"] == "new"

    def test_foreign_key_table_name_setter(self, dialect):
        expr = ForeignKeyQueryStatement(dialect, "old").with_table_name("new")
        assert expr.get_params()["table_name"] == "new"

    def test_view_info_view_name_setter(self, dialect):
        expr = ViewInfoQueryStatement(dialect, "old").with_view_name("new")
        assert expr.get_params()["view_name"] == "new"


class TestCrossTypeDataTypes:
    """Cross-type inequality branches (type(self) is not type(other))."""

    def test_datetime_types_inequality(self):
        assert TimeType(None, 6) != DateTimeType(None, 6)
        assert TimeTzType(None, 2) != TimeType(None, 2)
        assert DateTimeType(None, 6) != TimestampType(None, 6)
        assert TimestampType(None, 6) != TimestampTzType(None, 6)
        assert TimestampTzType(None, 0) != DateTimeType(None, 0)
        assert IntervalType(None, "YEAR") != TimeType(None, 1)

    def test_string_types_inequality(self):
        assert CharType(None, 10) != VarCharType(None, 10)
        assert VarCharType(None, 10) != CharType(None, 10)
        assert CharType(None, 10) != CustomType(None, raw="CHAR(10)")

    def test_numeric_types_inequality(self):
        assert FloatType(None, 24) != DecimalType(None, 10, 2)
        assert DecimalType(None, 10, 2) != FloatType(None, 24)
        assert FloatType(None, 24) != IntegerType()

    def test_array_and_custom_inequality(self):
        assert ArrayType(None, element_type=IntegerType()) != ArrayType(None, element_type=CharType(None, 10))
        assert ArrayType(None, element_type=IntegerType()) != CharType(None, 10)
        assert ArrayType(None, element_type=IntegerType()) != CharType(None, 10)
        assert CustomType(None, raw="geometry") != IntegerType()

    def test_hash_branches(self):
        assert hash(CharType(None, 10)) == hash(CharType(None, 10))
        assert hash(DecimalType(None, 10, 2)) == hash(DecimalType(None, 10, 2))

    def test_timetz_timestamptz_equality(self):
        assert TimeTzType(None, 2) == TimeTzType(None, 2)
        assert TimeTzType(None, 2) != TimeTzType(None, 3)
        assert TimestampTzType(None, 0) == TimestampTzType(None, 0)
        assert TimestampTzType(None, 0) != TimestampTzType(None, 1)

    def test_trigger_info_trigger_name_setter(self, dialect):
        from rhosocial.activerecord.backend.expression.introspection import TriggerInfoQueryStatement

        expr = TriggerInfoQueryStatement(dialect, "old").with_trigger_name("new")
        assert expr.get_params()["trigger_name"] == "new"


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
            ColumnDefinition(dialect, name="x", data_type="BAD")

    def test_valid_data_type(self, dialect):
        from rhosocial.activerecord.backend.expression.statements.ddl_table import ColumnDefinition
        from rhosocial.activerecord.backend.expression.types import IntegerType

        col = ColumnDefinition(dialect, name="id", data_type=IntegerType(dialect))
        assert col.name == "id"
        assert isinstance(col.data_type, IntegerType)


class TestIntrospectionToSqlUnsupported:
    """Introspection to_sql() is backend-specific and unsupported on Dummy."""

    @pytest.mark.parametrize(
        "factory",
        [
            lambda d: DatabaseInfoQueryStatement(d),
            lambda d: TableListQueryStatement(d),
            lambda d: TableInfoQueryStatement(d, "users"),
            lambda d: ColumnInfoQueryStatement(d, "users"),
            lambda d: IndexInfoQueryStatement(d, "users"),
            lambda d: ForeignKeyQueryStatement(d, "users"),
            lambda d: ViewListQueryStatement(d),
            lambda d: ViewInfoQueryStatement(d, "v"),
            lambda d: TriggerListQueryStatement(d),
            lambda d: TriggerInfoQueryStatement(d, "t"),
        ],
    )
    def test_to_sql_raises(self, dialect, factory):
        expr = factory(dialect)
        with pytest.raises(Exception) as exc_info:
            expr.to_sql()
        assert "support" in str(exc_info.value) or "introspection" in str(exc_info.value).lower()
