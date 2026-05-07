# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_expression_serialization.py
"""
Tests for expression serialization and deserialization.

These tests verify that all generic expressions (not backend-specific) can be
serialized to a JSON-compatible dict and restored via deserialization.
"""

import json
import warnings

import pytest

from rhosocial.activerecord.backend.expression import (
    Column,
    Literal,
    WildcardExpression,
    FunctionCall,
    TableExpression,
    ComparisonPredicate,
    LogicalPredicate,
    InPredicate,
    LikePredicate,
    IsNullPredicate,
    IsBooleanPredicate,
    BetweenPredicate,
)
from rhosocial.activerecord.backend.expression.bases import BaseExpression
from rhosocial.activerecord.backend.expression.query_parts import (
    WhereClause,
    GroupByHavingClause,
    OrderByClause,
    LimitOffsetClause,
    ForUpdateClause,
)
from rhosocial.activerecord.backend.expression.aggregates import AggregateFunctionCall
from rhosocial.activerecord.backend.expression.serialization import (
    serialize,
    deserialize,
    ExpressionFactory,
    ExpressionRegistry,
    ExpressionDeserializationError,
)


class TestAtomExpressionRoundtrip:
    """T1: Atom expression round-trip tests."""

    def test_column_roundtrip(self, dummy_dialect):
        col = Column(dummy_dialect, "age", table="users", alias="u_age")
        restored = deserialize(serialize(col), dummy_dialect)
        assert restored.to_sql() == col.to_sql()

    @pytest.mark.parametrize(
        "value", [42, "hello", 3.14, None, True, False, ["a", "b", "c"]]
    )
    def test_literal_roundtrip(self, dummy_dialect, value):
        lit = Literal(dummy_dialect, value)
        assert deserialize(serialize(lit), dummy_dialect).to_sql() == lit.to_sql()

    def test_wildcard_roundtrip(self, dummy_dialect):
        w = WildcardExpression(dummy_dialect, table="users")
        assert deserialize(serialize(w), dummy_dialect).to_sql() == w.to_sql()

    def test_function_call_roundtrip(self, dummy_dialect):
        expr = FunctionCall(
            dummy_dialect, "COUNT", WildcardExpression(dummy_dialect), is_distinct=True
        )
        assert deserialize(serialize(expr), dummy_dialect).to_sql() == expr.to_sql()

    def test_function_call_with_multiple_args(self, dummy_dialect):
        """Test FunctionCall with VAR_POSITIONAL *args parameter."""
        expr = FunctionCall(
            dummy_dialect, "CONCAT",
            Column(dummy_dialect, "first_name"),
            Column(dummy_dialect, "last_name"),
            Literal(dummy_dialect, " "),
        )
        assert deserialize(serialize(expr), dummy_dialect).to_sql() == expr.to_sql()

    def test_table_expression_roundtrip(self, dummy_dialect):
        expr = TableExpression(dummy_dialect, "users", alias="u")
        assert deserialize(serialize(expr), dummy_dialect).to_sql() == expr.to_sql()


class TestPredicateRoundtrip:
    """T2: Predicate round-trip tests."""

    def test_comparison_predicate_roundtrip(self, dummy_dialect):
        pred = ComparisonPredicate(
            dummy_dialect,
            ">=",
            Column(dummy_dialect, "age"),
            Literal(dummy_dialect, 18),
        )
        assert deserialize(serialize(pred), dummy_dialect).to_sql() == pred.to_sql()

    def test_logical_predicate_roundtrip(self, dummy_dialect):
        p1 = ComparisonPredicate(
            dummy_dialect, "=", Column(dummy_dialect, "status"), Literal(dummy_dialect, "active")
        )
        p2 = ComparisonPredicate(
            dummy_dialect, ">", Column(dummy_dialect, "score"), Literal(dummy_dialect, 100)
        )
        combined = LogicalPredicate(dummy_dialect, "AND", p1, p2)
        assert deserialize(serialize(combined), dummy_dialect).to_sql() == combined.to_sql()

    def test_logical_predicate_with_multiple_predicates(self, dummy_dialect):
        """Test LogicalPredicate with VAR_POSITIONAL *predicates parameter."""
        p1 = ComparisonPredicate(dummy_dialect, "=", Column(dummy_dialect, "a"), Literal(dummy_dialect, 1))
        p2 = ComparisonPredicate(dummy_dialect, "=", Column(dummy_dialect, "b"), Literal(dummy_dialect, 2))
        p3 = ComparisonPredicate(dummy_dialect, "=", Column(dummy_dialect, "c"), Literal(dummy_dialect, 3))
        combined = LogicalPredicate(dummy_dialect, "AND", p1, p2, p3)
        assert deserialize(serialize(combined), dummy_dialect).to_sql() == combined.to_sql()

    def test_in_predicate_roundtrip(self, dummy_dialect):
        pred = InPredicate(
            dummy_dialect, Column(dummy_dialect, "cat"), Literal(dummy_dialect, ["A", "B", "C"])
        )
        assert deserialize(serialize(pred), dummy_dialect).to_sql() == pred.to_sql()

    def test_like_predicate_roundtrip(self, dummy_dialect):
        pred = LikePredicate(dummy_dialect, "LIKE", Column(dummy_dialect, "name"), Literal(dummy_dialect, "A%"))
        assert deserialize(serialize(pred), dummy_dialect).to_sql() == pred.to_sql()

    def test_is_null_predicate_roundtrip(self, dummy_dialect):
        pred = IsNullPredicate(dummy_dialect, Column(dummy_dialect, "deleted_at"))
        assert deserialize(serialize(pred), dummy_dialect).to_sql() == pred.to_sql()

    def test_is_boolean_predicate_roundtrip(self, dummy_dialect):
        pred = IsBooleanPredicate(dummy_dialect, Column(dummy_dialect, "active"), value=True)
        assert deserialize(serialize(pred), dummy_dialect).to_sql() == pred.to_sql()

    def test_between_predicate_roundtrip(self, dummy_dialect):
        pred = BetweenPredicate(
            dummy_dialect, Column(dummy_dialect, "age"), Literal(dummy_dialect, 18), Literal(dummy_dialect, 65)
        )
        assert deserialize(serialize(pred), dummy_dialect).to_sql() == pred.to_sql()


class TestWhereClauseAndSerialization:
    """T3: WhereClause.and_() equivalence test."""

    def test_where_clause_and_serialization(self, dummy_dialect):
        p1 = ComparisonPredicate(dummy_dialect, "=", Column(dummy_dialect, "a"), Literal(dummy_dialect, 1))
        p2 = ComparisonPredicate(dummy_dialect, "=", Column(dummy_dialect, "b"), Literal(dummy_dialect, 2))

        where = WhereClause(dummy_dialect, p1)
        where.and_(p2)

        spec = serialize(where)
        restored = deserialize(spec, dummy_dialect)

        assert restored.to_sql() == where.to_sql()
        assert "LogicalPredicate" in spec["params"]["condition"]["__expr__"]["type"]
        assert spec["params"]["condition"]["__expr__"]["params"]["op"] == "AND"


class TestDeeplyNestedRoundtrip:
    """T4: Deeply nested composite expression test."""

    def test_deeply_nested_roundtrip(self, dummy_dialect):
        """WHERE (age >= 18 AND status = 'active') OR score > 100"""
        pred = (
            (Column(dummy_dialect, "age") >= Literal(dummy_dialect, 18))
            & (Column(dummy_dialect, "status") == Literal(dummy_dialect, "active"))
        ) | (Column(dummy_dialect, "score") > Literal(dummy_dialect, 100))

        assert deserialize(serialize(pred), dummy_dialect).to_sql() == pred.to_sql()


class TestAggregateRoundtrip:
    """T5: Aggregate function round-trip test."""

    def test_aggregate_function_roundtrip(self, dummy_dialect):
        expr = AggregateFunctionCall(
            dummy_dialect, "SUM", Column(dummy_dialect, "amount"), alias="total"
        )
        assert deserialize(serialize(expr), dummy_dialect).to_sql() == expr.to_sql()


class TestQueryExpressionRoundtrip:
    """T6: QueryExpression complete round-trip test."""

    def test_query_expression_roundtrip(self, dummy_dialect):
        from rhosocial.activerecord.backend.expression.statements.dql import QueryExpression

        query = QueryExpression(
            dummy_dialect,
            select=[Column(dummy_dialect, "id"), Column(dummy_dialect, "name")],
            from_=TableExpression(dummy_dialect, "users"),
            where=WhereClause(
                dummy_dialect,
                ComparisonPredicate(dummy_dialect, ">", Column(dummy_dialect, "age"), Literal(dummy_dialect, 18))
            ),
            order_by=OrderByClause(dummy_dialect, expressions=[(Column(dummy_dialect, "name"), "ASC")]),
        )
        restored = deserialize(serialize(query), dummy_dialect)
        assert query.to_sql() == restored.to_sql()


class TestRawSQLExpressionRoundtrip:
    """RawSQLExpression and RawSQLPredicate round-trip tests."""

    def test_raw_sql_expression_roundtrip(self, dummy_dialect):
        from rhosocial.activerecord.backend.expression.operators import RawSQLExpression

        expr = RawSQLExpression(dummy_dialect, expression="SELECT 1 FROM users WHERE id = ?", params=(1,))
        spec = serialize(expr)
        restored = deserialize(spec, dummy_dialect)
        assert expr.to_sql() == restored.to_sql()

    def test_raw_sql_predicate_roundtrip(self, dummy_dialect):
        from rhosocial.activerecord.backend.expression.operators import RawSQLPredicate

        pred = RawSQLPredicate(dummy_dialect, expression="id IN (SELECT id FROM admins)", params=())
        spec = serialize(pred)
        restored = deserialize(spec, dummy_dialect)
        assert pred.to_sql() == restored.to_sql()


class TestJsonSerializable:
    """T7: JSON serialization compatibility test."""

    def test_json_serializable(self, dummy_dialect):
        """ExpressionSpec must be fully JSON-serializable"""
        expr = ComparisonPredicate(
            dummy_dialect, "=",
            Column(dummy_dialect, "status", table="orders"),
            Literal(dummy_dialect, "paid")
        )
        spec = serialize(expr)
        dumped = json.dumps(spec)
        loaded = json.loads(dumped)
        assert loaded == spec


class TestCrossDialectFastFail:
    """T8: Cross-dialect fast-fail test."""

    def test_sqlite_specific_expression_to_dummy_dialect(self, dummy_dialect):
        """Test that SQLite-specific expressions fail fast on non-SQLite dialects.

        Step 1: deserialization should succeed (SQLiteReindexExpression is a known class)
        Step 2: to_sql() should fail fast when dummy_dialect doesn't support the expression
        """
        from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
        from rhosocial.activerecord.backend.impl.sqlite.expression.reindex import SQLiteReindexExpression

        sqlite_dialect = SQLiteDialect(version=(3, 53, 0))
        expr = SQLiteReindexExpression(sqlite_dialect, table_name="users")
        spec = serialize(expr)

        assert "sqlite" in spec["type"]

        restored = deserialize(spec, dummy_dialect)
        with pytest.raises((TypeError, ValueError, NotImplementedError, AttributeError)):
            restored.to_sql()


class TestErrorHandling:
    """T10: Error handling tests."""

    def test_deserialize_unknown_type(self, dummy_dialect):
        with pytest.raises(ExpressionDeserializationError, match="NonExistentExpr"):
            deserialize(
                {"type": "fake.module.NonExistentExpr", "params": {}},
                dummy_dialect
            )

    def test_deserialize_missing_required_param(self, dummy_dialect):
        with pytest.raises(ExpressionDeserializationError, match="Failed to reconstruct"):
            deserialize({
                "type": "rhosocial.activerecord.backend.expression.core.Column",
                "params": {}
            }, dummy_dialect)

    def test_deserialize_invalid_spec_missing_type(self, dummy_dialect):
        with pytest.raises(ExpressionDeserializationError, match="missing 'type' field"):
            deserialize({"params": {}}, dummy_dialect)

    def test_deserialize_invalid_spec_missing_module(self, dummy_dialect):
        with pytest.raises(ExpressionDeserializationError, match="must be a fully qualified name"):
            deserialize({"type": "SomeType", "params": {}}, dummy_dialect)

    def test_deserialize_invalid_class_not_expression(self, dummy_dialect):
        class NotAnExpression:
            pass

        ExpressionRegistry._registry["test.module.NotAnExpression"] = NotAnExpression
        try:
            with pytest.raises(ExpressionDeserializationError, match="not a BaseExpression subclass"):
                deserialize({
                    "type": "test.module.NotAnExpression",
                    "params": {}
                }, dummy_dialect)
        finally:
            ExpressionRegistry._registry.pop("test.module.NotAnExpression", None)

    def test_reconstruct_by_name_type_error(self, dummy_dialect):
        from rhosocial.activerecord.backend.expression.serialization import _reconstruct_by_name
        with pytest.raises(ExpressionDeserializationError, match="Failed to reconstruct"):
            _reconstruct_by_name("Column", dummy_dialect, {"invalid_param": 123})

    def test_registry_ambiguous_short_name(self):
        class CustomExpression(BaseExpression):
            def __init__(self, dialect, name):
                self._name = name

            def to_sql(self):
                return "custom"

        try:
            ExpressionRegistry._registry["module1.CustomExpression"] = CustomExpression
            ExpressionRegistry._registry["module2.CustomExpression"] = CustomExpression

            with pytest.raises(ExpressionDeserializationError, match="Ambiguous short name"):
                ExpressionRegistry.lookup("CustomExpression")
        finally:
            ExpressionRegistry._registry.pop("module1.CustomExpression", None)
            ExpressionRegistry._registry.pop("module2.CustomExpression", None)

    def test_serialize_deserialize_tuple_in_params(self, dummy_dialect):
        col = Column(dummy_dialect, "status")
        in_pred = col.in_(["active", "pending", "draft"])
        spec = serialize(in_pred)
        restored = deserialize(spec, dummy_dialect)
        assert restored.to_sql() == in_pred.to_sql()

    def test_deserialize_exceeds_max_nesting_depth(self, dummy_dialect):
        inner_spec = {
            "type": "rhosocial.activerecord.backend.expression.predicates.ComparisonPredicate",
            "params": {
                "op": "=",
                "left": {"type": "rhosocial.activerecord.backend.expression.core.Column", "params": {"name": "a"}},
                "right": {"type": "rhosocial.activerecord.backend.expression.core.Literal", "params": {"value": 1}},
            },
        }

        current_spec = inner_spec
        for _ in range(65):
            current_spec = {
                "type": "rhosocial.activerecord.backend.expression.predicates.LogicalPredicate",
                "params": {"left": current_spec, "right": inner_spec, "op": "AND"},
            }

        with pytest.raises(ExpressionDeserializationError, match="exceeds maximum"):
            deserialize(current_spec, dummy_dialect)

    def test_reconstruct_varargs_predicates(self, dummy_dialect):
        from rhosocial.activerecord.backend.expression.predicates import LogicalPredicate

        p1 = ComparisonPredicate(dummy_dialect, "=", Column(dummy_dialect, "a"), Literal(dummy_dialect, 1))
        p2 = ComparisonPredicate(dummy_dialect, "=", Column(dummy_dialect, "b"), Literal(dummy_dialect, 2))
        p3 = ComparisonPredicate(dummy_dialect, "=", Column(dummy_dialect, "c"), Literal(dummy_dialect, 3))

        expr = LogicalPredicate(dummy_dialect, "AND", p1, p2, p3)
        restored = deserialize(serialize(expr), dummy_dialect)
        assert restored.to_sql() == expr.to_sql()

    def test_reconstruct_varargs_sql_operation(self, dummy_dialect):
        from rhosocial.activerecord.backend.expression.operators import SQLOperation

        col1 = Column(dummy_dialect, "a")
        col2 = Column(dummy_dialect, "b")
        expr = SQLOperation(dummy_dialect, "GREATEST", col1, col2)
        restored = deserialize(serialize(expr), dummy_dialect)
        assert restored.to_sql() == expr.to_sql()

    def test_expression_serializer_invalid_max_depth(self):
        from rhosocial.activerecord.backend.expression.serialization import ExpressionSerializer

        with pytest.raises(ValueError, match="max_depth must be a positive integer"):
            ExpressionSerializer(max_depth=0)

        with pytest.raises(ValueError, match="max_depth must be a positive integer"):
            ExpressionSerializer(max_depth=-1)

    def test_expression_serializer_invalid_warn_threshold(self):
        from rhosocial.activerecord.backend.expression.serialization import ExpressionSerializer

        with pytest.raises(ValueError, match="warn_threshold must be between 0 and 1"):
            ExpressionSerializer(warn_threshold=0)

        with pytest.raises(ValueError, match="warn_threshold must be between 0 and 1"):
            ExpressionSerializer(warn_threshold=1.1)

        with pytest.raises(ValueError, match="warn_threshold must be between 0 and 1"):
            ExpressionSerializer(warn_threshold=-0.5)

    def test_expression_serializer_warning_threshold(self, dummy_dialect):
        from rhosocial.activerecord.backend.expression.serialization import ExpressionSerializer

        serializer = ExpressionSerializer(max_depth=10, warn_threshold=0.5)

        p1 = ComparisonPredicate(dummy_dialect, "=", Column(dummy_dialect, "a"), Literal(dummy_dialect, 1))
        p2 = ComparisonPredicate(dummy_dialect, "=", Column(dummy_dialect, "b"), Literal(dummy_dialect, 2))
        p3 = ComparisonPredicate(dummy_dialect, "=", Column(dummy_dialect, "c"), Literal(dummy_dialect, 3))
        p4 = ComparisonPredicate(dummy_dialect, "=", Column(dummy_dialect, "d"), Literal(dummy_dialect, 4))

        expr = LogicalPredicate(dummy_dialect, "AND", p1, p2, p3, p4)

        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            serializer.serialize(expr)
            assert any("exceeds warning threshold" in str(warning.message) for warning in w)

    def test_expression_serializer_tuple_in_params(self, dummy_dialect):
        from rhosocial.activerecord.backend.expression.serialization import ExpressionSerializer

        serializer = ExpressionSerializer(max_depth=64)
        col = Column(dummy_dialect, "status")
        in_pred = col.in_(["active", "pending"])

        spec = serializer.serialize(in_pred)
        restored = serializer.deserialize(spec, dummy_dialect)
        assert restored.to_sql() == in_pred.to_sql()

    def test_expression_serializer_deserialize_exceeds_depth(self, dummy_dialect):
        from rhosocial.activerecord.backend.expression.serialization import ExpressionSerializer

        serializer = ExpressionSerializer(max_depth=5)

        inner_spec = {
            "type": "rhosocial.activerecord.backend.expression.core.Column",
            "params": {"name": "a"},
        }

        current_spec = inner_spec
        for _ in range(6):
            current_spec = {
                "type": "rhosocial.activerecord.backend.expression.predicates.LogicalPredicate",
                "params": {"left": current_spec, "right": inner_spec, "op": "AND"},
            }

        with pytest.raises(ExpressionDeserializationError, match="exceeds maximum"):
            serializer.deserialize(current_spec, dummy_dialect)

    def test_expression_serializer_raw_sql_with_tuple_params(self, dummy_dialect):
        from rhosocial.activerecord.backend.expression.operators import RawSQLExpression

        expr = RawSQLExpression(dummy_dialect, "SELECT * FROM t WHERE id IN (?, ?)", (1, 2))
        spec = serialize(expr)
        assert "__tuple__" in str(spec["params"])

        restored = deserialize(spec, dummy_dialect)
        assert restored.params == (1, 2)

    def test_expression_serializer_varargs_with_extra_params(self, dummy_dialect):
        from rhosocial.activerecord.backend.expression.predicates import LogicalPredicate

        p1 = ComparisonPredicate(dummy_dialect, "=", Column(dummy_dialect, "a"), Literal(dummy_dialect, 1))
        p2 = ComparisonPredicate(dummy_dialect, "=", Column(dummy_dialect, "b"), Literal(dummy_dialect, 2))
        p3 = ComparisonPredicate(dummy_dialect, "=", Column(dummy_dialect, "c"), Literal(dummy_dialect, 3))

        expr = LogicalPredicate(dummy_dialect, "AND", p1, p2, p3)
        spec = serialize(expr)

        import json
        spec_json = json.dumps(spec)
        restored = deserialize(json.loads(spec_json), dummy_dialect)
        assert restored.to_sql() == expr.to_sql()

    def test_expression_serializer_deserialize_depth_limit(self, dummy_dialect):
        from rhosocial.activerecord.backend.expression.serialization import ExpressionSerializer

        serializer = ExpressionSerializer(max_depth=3)

        inner_spec = {
            "type": "rhosocial.activerecord.backend.expression.core.Column",
            "params": {"name": "a"},
        }

        current_spec = inner_spec
        for _ in range(4):
            current_spec = {
                "type": "rhosocial.activerecord.backend.expression.predicates.LogicalPredicate",
                "params": {"left": current_spec, "right": inner_spec, "op": "AND"},
            }

        with pytest.raises(ExpressionDeserializationError, match="exceeds maximum"):
            serializer.deserialize(current_spec, dummy_dialect)

    def test_deserialize_with_tuple_directly(self, dummy_dialect):
        from rhosocial.activerecord.backend.expression.serialization import ExpressionSerializer

        serializer = ExpressionSerializer()
        result = serializer._deserialize_value((1, 2, 3), dummy_dialect, depth=0)
        assert result == (1, 2, 3)

    def test_deserialize_expression_depth_exceeded(self, dummy_dialect):
        from rhosocial.activerecord.backend.expression.serialization import ExpressionSerializer

        serializer = ExpressionSerializer(max_depth=2)
        spec = {"type": "rhosocial.activerecord.backend.expression.core.Column", "params": {"name": "a"}}

        with pytest.raises(ExpressionDeserializationError, match="exceeds maximum"):
            serializer._deserialize_expression(spec, dummy_dialect, depth=3)

    def test_reconstruct_varargs_branch(self, dummy_dialect):
        from rhosocial.activerecord.backend.expression.serialization import _reconstruct
        from rhosocial.activerecord.backend.expression.predicates import LogicalPredicate

        params = {"op": "AND", "predicates": [1, 2, 3]}
        result = _reconstruct(LogicalPredicate, dummy_dialect, params)
        assert result is not None

    def test_reconstruct_non_varargs_branch(self, dummy_dialect):
        from rhosocial.activerecord.backend.expression.serialization import _reconstruct
        from rhosocial.activerecord.backend.expression.core import Column

        params = {"name": "id", "table": "users"}
        result = _reconstruct(Column, dummy_dialect, params)
        assert result is not None

    def test_reconstruct_varargs_keyword_only_params(self, dummy_dialect):
        from rhosocial.activerecord.backend.expression.operators import SQLOperation

        col1 = Column(dummy_dialect, "a")
        col2 = Column(dummy_dialect, "b")
        expr = SQLOperation(dummy_dialect, "GREATEST", col1, col2)
        spec = serialize(expr)

        import json
        spec_json = json.dumps(spec)
        restored = deserialize(json.loads(spec_json), dummy_dialect)
        assert restored.to_sql() == expr.to_sql()

    

    def test_expression_factory_serialize(self, dummy_dialect):
        from rhosocial.activerecord.backend.expression.serialization import ExpressionFactory

        factory = ExpressionFactory(dummy_dialect)
        col = Column(dummy_dialect, "id")
        spec = factory.serialize(col)
        assert "type" in spec
        assert "params" in spec

    def test_deserialize_tuple_in_params(self, dummy_dialect):
        from rhosocial.activerecord.backend.expression.operators import RawSQLExpression

        expr = RawSQLExpression(dummy_dialect, "SELECT ?", (1, 2, 3))
        spec = serialize(expr)

        assert "params" in spec and "params" in spec["params"]
        inner_params = spec["params"]["params"]
        assert "__tuple__" in inner_params

        restored = deserialize(spec, dummy_dialect)
        assert restored.params == (1, 2, 3)

    def test_reconstruct_with_varargs_and_regular_params(self, dummy_dialect):
        from rhosocial.activerecord.backend.expression.predicates import LogicalPredicate
        from rhosocial.activerecord.backend.expression import Column, Literal

        p1 = ComparisonPredicate(dummy_dialect, "=", Column(dummy_dialect, "a"), Literal(dummy_dialect, 1))
        p2 = ComparisonPredicate(dummy_dialect, "=", Column(dummy_dialect, "b"), Literal(dummy_dialect, 2))

        expr = LogicalPredicate(dummy_dialect, "AND", p1, p2)
        spec = serialize(expr)

        restored = deserialize(spec, dummy_dialect)
        assert restored.op == "AND"
        assert len(restored.predicates) == 2


class TestExpressionFactoryAndRegistry:
    """Test ExpressionFactory and ExpressionRegistry."""

    def test_expression_factory_create_with_kwargs(self, dummy_dialect):
        factory = ExpressionFactory(dummy_dialect)
        col = factory.create("Column", name="id", table="users")
        assert col.to_sql() == Column(dummy_dialect, "id", table="users").to_sql()

    def test_expression_factory_create_with_expression_params(self, dummy_dialect):
        factory = ExpressionFactory(dummy_dialect)
        col = factory.create("Column", name="id", table="users")
        pred = factory.create(
            "ComparisonPredicate",
            op="=",
            left=col,
            right=factory.create("Literal", value=1),
        )
        assert "id" in pred.to_sql()[0]

    def test_expression_factory_from_spec(self, dummy_dialect):
        from rhosocial.activerecord.backend.expression import Column
        col = Column(dummy_dialect, "name", table="users")
        spec = serialize(col)
        factory = ExpressionFactory(dummy_dialect)
        restored = factory._create_from_spec(spec)
        assert restored.to_sql() == col.to_sql()

    def test_expression_factory_from_spec_missing_type(self, dummy_dialect):
        factory = ExpressionFactory(dummy_dialect)
        with pytest.raises(ExpressionDeserializationError, match="missing 'type' field"):
            factory._create_from_spec({"params": {}})

    def test_expression_factory_from_spec_missing_module(self, dummy_dialect):
        factory = ExpressionFactory(dummy_dialect)
        with pytest.raises(ExpressionDeserializationError, match="must be a fully qualified name"):
            factory._create_from_spec({"type": "SomeType", "params": {}})

    def test_expression_factory_from_spec_invalid_module(self, dummy_dialect):
        factory = ExpressionFactory(dummy_dialect)
        with pytest.raises(ExpressionDeserializationError, match="not found in registry"):
            factory._create_from_spec({
                "type": "fake.module.that.does.not.exist.NonExistent",
                "params": {}
            })


class TestExpressionRegistry:
    """Test ExpressionRegistry."""

    def test_registry_lookup_found(self):
        from rhosocial.activerecord.backend.expression import Column
        result = ExpressionRegistry.lookup("Column")
        assert result is Column

    def test_registry_lookup_not_found(self):
        with pytest.raises(ExpressionDeserializationError, match="not found in registry"):
            ExpressionRegistry.lookup("NonExistentClass")

    def test_registry_lookup_registered_class(self):
        result = ExpressionRegistry.lookup("Column")
        assert result is not None

    def test_reconstruct_by_name_not_found(self, dummy_dialect):
        from rhosocial.activerecord.backend.expression.serialization import _reconstruct_by_name
        with pytest.raises(ExpressionDeserializationError, match="not found in registry"):
            _reconstruct_by_name("NonExistentExpression", dummy_dialect, {})

    def test_registry_lookup_not_found_2(self):
        with pytest.raises(ExpressionDeserializationError, match="not found in registry"):
            ExpressionRegistry.lookup("SomeClass")

    def test_registry_lookup_not_found_3(self):
        with pytest.raises(ExpressionDeserializationError, match="not found in registry"):
            ExpressionRegistry.lookup("NonExistentClass")

    


class TestExpressionFactory:
    """T11: ExpressionFactory interface test."""

    def test_expression_factory_create(self, dummy_dialect):
        factory = ExpressionFactory(dummy_dialect)

        col = factory.create("Column", name="user_id", table="orders")
        assert isinstance(col, Column)
        assert col.get_params()["name"] == "user_id"

    def test_expression_factory_nested(self, dummy_dialect):
        factory = ExpressionFactory(dummy_dialect)

        pred = factory.create(
            "ComparisonPredicate",
            op="=",
            left=factory.create("Column", name="status"),
            right=factory.create("Literal", value="paid"),
        )
        assert isinstance(pred, ComparisonPredicate)
        sql, params = pred.to_sql()
        assert "status" in sql


class TestQueryPartsRoundtrip:
    """Query parts round-trip tests."""

    def test_group_by_having_roundtrip(self, dummy_dialect):
        agg = AggregateFunctionCall(dummy_dialect, "COUNT")
        pred = ComparisonPredicate(dummy_dialect, ">", agg, Literal(dummy_dialect, 10))
        expr = GroupByHavingClause(
            dummy_dialect,
            [Column(dummy_dialect, "dept")],
            pred,
        )
        assert deserialize(serialize(expr), dummy_dialect).to_sql() == expr.to_sql()

    def test_order_by_clause_roundtrip(self, dummy_dialect):
        expr = OrderByClause(
            dummy_dialect,
            [(Column(dummy_dialect, "name"), "ASC"), (Column(dummy_dialect, "age"), "DESC")]
        )
        assert deserialize(serialize(expr), dummy_dialect).to_sql() == expr.to_sql()

    def test_limit_offset_clause_roundtrip(self, dummy_dialect):
        expr = LimitOffsetClause(dummy_dialect, limit=10, offset=20)
        assert deserialize(serialize(expr), dummy_dialect).to_sql() == expr.to_sql()

    def test_for_update_clause_roundtrip(self, dummy_dialect):
        expr = ForUpdateClause(dummy_dialect, nowait=True, skip_locked=True)
        assert deserialize(serialize(expr), dummy_dialect).to_sql() == expr.to_sql()


class TestIntrospectionExpressionRoundtrip:
    """Introspection expression round-trip tests (generic dialect)."""

    def test_table_list_expression_default_params_schema_omitted(self, dummy_dialect):
        from rhosocial.activerecord.backend.expression.introspection import TableListExpression
        expr = TableListExpression(dummy_dialect)
        spec = serialize(expr)
        assert "schema" not in spec["params"]
        assert spec["params"]["include_views"] is True
        assert spec["params"]["include_system"] is False

    def test_table_list_expression_with_schema_roundtrip(self, dummy_dialect):
        from rhosocial.activerecord.backend.expression.introspection import TableListExpression
        expr = TableListExpression(dummy_dialect, schema="main", include_views=False)
        spec = serialize(expr)
        assert spec["params"]["schema"] == "main"
        restored = deserialize(spec, dummy_dialect)
        assert restored.get_params() == expr.get_params()

    def test_table_info_expression_roundtrip(self, dummy_dialect):
        from rhosocial.activerecord.backend.expression.introspection import TableInfoExpression
        expr = TableInfoExpression(dummy_dialect, "users", schema="public")
        assert deserialize(serialize(expr), dummy_dialect).get_params() == expr.get_params()

    def test_column_info_expression_schema_omitted(self, dummy_dialect):
        from rhosocial.activerecord.backend.expression.introspection import ColumnInfoExpression
        expr = ColumnInfoExpression(dummy_dialect, "users")
        spec = serialize(expr)
        assert "schema" not in spec["params"]

    def test_column_info_expression_with_schema_roundtrip(self, dummy_dialect):
        from rhosocial.activerecord.backend.expression.introspection import ColumnInfoExpression
        expr = ColumnInfoExpression(dummy_dialect, "users", schema="main")
        restored = deserialize(serialize(expr), dummy_dialect)
        assert restored.get_params() == expr.get_params()

    def test_index_info_expression_roundtrip(self, dummy_dialect):
        from rhosocial.activerecord.backend.expression.introspection import IndexInfoExpression
        expr = IndexInfoExpression(dummy_dialect, "users", "idx_users_name")
        restored = deserialize(serialize(expr), dummy_dialect)
        assert restored.get_params() == expr.get_params()

    def test_foreign_key_expression_roundtrip(self, dummy_dialect):
        from rhosocial.activerecord.backend.expression.introspection import ForeignKeyExpression
        expr = ForeignKeyExpression(dummy_dialect, "users", "profiles")
        restored = deserialize(serialize(expr), dummy_dialect)
        assert restored.get_params() == expr.get_params()

    def test_view_list_expression_roundtrip(self, dummy_dialect):
        from rhosocial.activerecord.backend.expression.introspection import ViewListExpression
        expr = ViewListExpression(dummy_dialect, schema="main")
        restored = deserialize(serialize(expr), dummy_dialect)
        assert restored.get_params() == expr.get_params()

    def test_view_info_expression_roundtrip(self, dummy_dialect):
        from rhosocial.activerecord.backend.expression.introspection import ViewInfoExpression
        expr = ViewInfoExpression(dummy_dialect, "user_stats", schema="public")
        restored = deserialize(serialize(expr), dummy_dialect)
        assert restored.get_params() == expr.get_params()

    def test_trigger_list_expression_roundtrip(self, dummy_dialect):
        from rhosocial.activerecord.backend.expression.introspection import TriggerListExpression
        expr = TriggerListExpression(dummy_dialect, schema="main")
        restored = deserialize(serialize(expr), dummy_dialect)
        assert restored.get_params() == expr.get_params()

    def test_trigger_info_expression_roundtrip(self, dummy_dialect):
        from rhosocial.activerecord.backend.expression.introspection import TriggerInfoExpression
        expr = TriggerInfoExpression(dummy_dialect, "trg_update_user", schema="main")
        restored = deserialize(serialize(expr), dummy_dialect)
        assert restored.get_params() == expr.get_params()


class TestDDLRoundtrip:
    """Test DDL expression serialization and deserialization."""

    def test_create_table_expression_roundtrip(self, dummy_dialect):
        from rhosocial.activerecord.backend.expression.statements.ddl_table import (
            CreateTableExpression,
            ColumnDefinition,
            ColumnConstraint,
            ColumnConstraintType,
        )

        col_def = ColumnDefinition(
            "id", "INTEGER", constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY)]
        )
        expr = CreateTableExpression(dummy_dialect, table="users", columns=[col_def])
        restored = deserialize(serialize(expr), dummy_dialect)
        assert restored.to_sql() == expr.to_sql()

    def test_create_index_expression_roundtrip(self, dummy_dialect):
        from rhosocial.activerecord.backend.expression.statements.ddl_index import CreateIndexExpression

        expr = CreateIndexExpression(dummy_dialect, "idx_name", "users", ["name", "age"])
        restored = deserialize(serialize(expr), dummy_dialect)
        assert restored.get_params() == expr.get_params()

    def test_drop_index_expression_roundtrip(self, dummy_dialect):
        from rhosocial.activerecord.backend.expression.statements.ddl_index import DropIndexExpression

        expr = DropIndexExpression(dummy_dialect, "idx_name")
        restored = deserialize(serialize(expr), dummy_dialect)
        assert restored.get_params() == expr.get_params()

    def test_create_schema_expression_roundtrip(self, dummy_dialect):
        from rhosocial.activerecord.backend.expression.statements.ddl_schema import CreateSchemaExpression

        expr = CreateSchemaExpression(dummy_dialect, "myschema")
        restored = deserialize(serialize(expr), dummy_dialect)
        assert restored.get_params() == expr.get_params()

    def test_drop_schema_expression_roundtrip(self, dummy_dialect):
        from rhosocial.activerecord.backend.expression.statements.ddl_schema import DropSchemaExpression

        expr = DropSchemaExpression(dummy_dialect, "myschema", cascade=True)
        restored = deserialize(serialize(expr), dummy_dialect)
        assert restored.get_params() == expr.get_params()

    def test_create_view_expression_roundtrip(self, dummy_dialect):
        from rhosocial.activerecord.backend.expression.statements.ddl_view import CreateViewExpression

        expr = CreateViewExpression(dummy_dialect, view_name="user_view", query="SELECT * FROM users")
        restored = deserialize(serialize(expr), dummy_dialect)
        assert restored.get_params() == expr.get_params()

    def test_drop_view_expression_roundtrip(self, dummy_dialect):
        from rhosocial.activerecord.backend.expression.statements.ddl_view import DropViewExpression

        expr = DropViewExpression(dummy_dialect, "user_view")
        restored = deserialize(serialize(expr), dummy_dialect)
        assert restored.get_params() == expr.get_params()

    def test_truncate_expression_roundtrip(self, dummy_dialect):
        from rhosocial.activerecord.backend.expression.statements.ddl_truncate import TruncateExpression

        expr = TruncateExpression(dummy_dialect, "users", cascade=True)
        restored = deserialize(serialize(expr), dummy_dialect)
        assert restored.get_params() == expr.get_params()

    def test_explain_expression_roundtrip(self, dummy_dialect):
        from rhosocial.activerecord.backend.expression.statements.explain import ExplainExpression
        from rhosocial.activerecord.backend.expression import Column

        expr = ExplainExpression(dummy_dialect, statement=Column(dummy_dialect, "users"))
        restored = deserialize(serialize(expr), dummy_dialect)
        assert restored.get_params() == expr.get_params()