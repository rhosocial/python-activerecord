# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_query_sources_set_operation.py
from rhosocial.activerecord.backend.expression import Column, Subquery, QueryStatement
from rhosocial.activerecord.backend.expression.sources import NamedRelationRef
from rhosocial.activerecord.backend.expression.query_sources import SetOperation
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect
from rhosocial.activerecord.backend.expression.objects import Table


def _query(dialect, table, *conditions):
    return QueryStatement(
        dialect,
        select=[Column(dialect, "id"), Column(dialect, "name")],
        from_=NamedRelationRef(dialect, Table(dialect, table)),
        **({"where": conditions[0]} if conditions else {}),
    )


class TestSetOperationExpression:
    """Tests for SetOperation with UNION, INTERSECT, EXCEPT operations."""

    def test_union_operation_basic(self, dummy_dialect: DummyDialect):
        """Test basic UNION operation between two queries."""
        left_query = Subquery(dummy_dialect, "SELECT id, name FROM users WHERE age > ?", (18,))
        right_query = Subquery(dummy_dialect, "SELECT id, name FROM customers WHERE status = ?", ("active",))

        set_op = SetOperation(dummy_dialect, op="union", left=left_query, right=right_query)

        sql, params = set_op.to_sql()

        assert "UNION" in sql.upper()
        assert params == (18, "active")

    def test_union_all_operation(self, dummy_dialect: DummyDialect):
        """Test UNION ALL operation (the union_all word form)."""
        left_query = Subquery(dummy_dialect, "SELECT id FROM table1", ())
        right_query = Subquery(dummy_dialect, "SELECT id FROM table2", ())

        set_op = SetOperation(
            dummy_dialect,
            op="union_all",
            left=left_query,
            right=right_query,
        )

        sql, params = set_op.to_sql()

        assert "UNION ALL" in sql.upper()
        assert params == ()

    def test_intersect_operation(self, dummy_dialect: DummyDialect):
        """Test INTERSECT operation."""
        left_query = Subquery(dummy_dialect, "SELECT id FROM table1 WHERE col1 = ?", ("value1",))
        right_query = Subquery(dummy_dialect, "SELECT id FROM table2 WHERE col2 = ?", ("value2",))

        set_op = SetOperation(dummy_dialect, op="intersect", left=left_query, right=right_query)

        sql, params = set_op.to_sql()

        assert "INTERSECT" in sql.upper()
        assert params == ("value1", "value2")

    def test_except_operation(self, dummy_dialect: DummyDialect):
        """Test EXCEPT operation."""
        left_query = Subquery(dummy_dialect, "SELECT id FROM table1 WHERE active = ?", (True,))
        right_query = Subquery(dummy_dialect, "SELECT id FROM table2 WHERE archived = ?", (True,))

        set_op = SetOperation(dummy_dialect, op="except", left=left_query, right=right_query)

        sql, params = set_op.to_sql()

        assert "EXCEPT" in sql.upper()
        assert params == (True, True)

    def test_nested_set_operations(self, dummy_dialect: DummyDialect):
        """Test nested set operations (set operation as operand)."""
        query1 = Subquery(dummy_dialect, "SELECT id FROM table1 WHERE col = ?", ("a",))
        query2 = Subquery(dummy_dialect, "SELECT id FROM table2 WHERE col = ?", ("b",))
        query3 = Subquery(dummy_dialect, "SELECT id FROM table3 WHERE col = ?", ("c",))

        # First set operation
        inner_op = SetOperation(dummy_dialect, op="union", left=query1, right=query2)

        # Outer set operation using the inner one
        outer_op = SetOperation(dummy_dialect, op="union", left=inner_op, right=query3)

        sql, params = outer_op.to_sql()

        assert "UNION" in sql.upper()
        assert params == ("a", "b", "c")

    def test_set_operation_with_complex_queries(self, dummy_dialect: DummyDialect):
        """Test set operation with more complex query structures."""
        left_query = _query(dummy_dialect, "users")
        right_query = _query(dummy_dialect, "customers")

        set_op = SetOperation(dummy_dialect, op="union", left=left_query, right=right_query)

        sql, params = set_op.to_sql()

        assert "UNION" in sql.upper()
        assert '"users"' in sql or "SELECT" in sql
        assert '"customers"' in sql or "SELECT" in sql
        assert params == ()

    def test_set_operation_parameters_handling(self, dummy_dialect: DummyDialect):
        """Test that parameters from both sides are properly combined."""
        left_query = Subquery(dummy_dialect, "SELECT id FROM users WHERE age > ? AND status = ?", (18, "active"))
        right_query = Subquery(dummy_dialect, "SELECT id FROM customers WHERE region = ?", ("west",))

        set_op = SetOperation(dummy_dialect, op="union", left=left_query, right=right_query)

        sql, params = set_op.to_sql()

        # Should contain parameters from both queries
        assert params == (18, "active", "west")
        assert len(params) == 3

    def test_set_operation_word_forms_are_case_insensitive(self, dummy_dialect: DummyDialect):
        """The word form is accepted case-insensitively and stored lowercase."""
        left_query = Subquery(dummy_dialect, "SELECT id FROM t1", ())
        right_query = Subquery(dummy_dialect, "SELECT id FROM t2", ())

        set_op = SetOperation(dummy_dialect, op="UNION", left=left_query, right=right_query)
        assert set_op.op == "union"
        sql, _ = set_op.to_sql()
        assert "UNION" in sql.upper()

    def test_sql_symbol_spellings_are_refused(self, dummy_dialect: DummyDialect):
        """The node carries the word form only; multi-word symbols are refused."""
        left_query = Subquery(dummy_dialect, "SELECT id FROM t1", ())
        right_query = Subquery(dummy_dialect, "SELECT id FROM t2", ())

        for bad in ("UNION ALL", "union all", "OUTER UNION", "x"):
            with __import__("pytest").raises(ValueError, match="word forms"):
                SetOperation(dummy_dialect, op=bad, left=left_query, right=right_query)

    def test_get_params_carries_the_wire_shape(self, dummy_dialect: DummyDialect):
        """The node's params are exactly op + left + right."""
        left_query = Subquery(dummy_dialect, "SELECT id FROM t1", ())
        right_query = Subquery(dummy_dialect, "SELECT id FROM t2", ())

        set_op = SetOperation(dummy_dialect, op="union_all", left=left_query, right=right_query)
        params = set_op.get_params()
        assert set(params) == {"op", "left", "right"}
        assert params["op"] == "union_all"

    def test_set_operation_with_explain_basic(self, dummy_dialect: DummyDialect):
        """Test set operation with EXPLAIN clause."""
        from rhosocial.activerecord.backend.expression.statements import ExplainStatement, ExplainOptions

        left_query = Subquery(dummy_dialect, "SELECT id, name FROM users WHERE age > ?", (18,))
        right_query = Subquery(dummy_dialect, "SELECT id, name FROM customers WHERE status = ?", ("active",))

        # Create SetOperation first
        set_op = SetOperation(dummy_dialect, op="union", left=left_query, right=right_query)

        # Wrap the set operation in an EXPLAIN expression
        explain_options = ExplainOptions()
        explain_expr = ExplainStatement(dummy_dialect, set_op, explain_options)

        sql, params = explain_expr.to_sql()

        # Verify EXPLAIN is present in the SQL
        assert "EXPLAIN" in sql.upper()
        # Verify the set operation is included
        assert "UNION" in sql.upper()
        # Verify parameters are still handled
        assert params == (18, "active")

    def test_set_operation_with_explain_analyze(self, dummy_dialect: DummyDialect):
        """Test set operation with EXPLAIN ANALYZE clause."""
        from rhosocial.activerecord.backend.expression.statements import ExplainStatement, ExplainOptions, ExplainType

        left_query = Subquery(dummy_dialect, "SELECT id, name FROM users WHERE age > ?", (18,))
        right_query = Subquery(dummy_dialect, "SELECT id, name FROM customers WHERE status = ?", ("active",))

        # Create SetOperation first
        set_op = SetOperation(dummy_dialect, op="union", left=left_query, right=right_query)

        # Wrap the set operation in an EXPLAIN ANALYZE expression
        explain_options = ExplainOptions(type=ExplainType.ANALYZE)
        explain_expr = ExplainStatement(dummy_dialect, set_op, explain_options)

        sql, params = explain_expr.to_sql()

        # Verify EXPLAIN ANALYZE is present in the SQL
        assert "EXPLAIN" in sql.upper()
        assert "ANALYZE" in sql.upper()
        # Verify the set operation is included
        assert "UNION" in sql.upper()
        # Verify parameters are still handled
        assert params == (18, "active")
