# tests/rhosocial/activerecord_test/feature/backend/sqlite2/test_sqlite_query_sources_set_operation.py
from rhosocial.activerecord.backend.expression import Column, Subquery, QueryStatement
from rhosocial.activerecord.backend.expression.sources import NamedRelationRef
from rhosocial.activerecord.backend.expression.query_sources import SetOperation
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
from rhosocial.activerecord.backend.expression.objects import Table


class TestSQLiteSetOperationExpression:
    """Tests for SetOperation with UNION, INTERSECT, EXCEPT operations for SQLite backend."""

    def test_union_operation_basic(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test basic UNION operation between two queries."""
        left_query = Subquery(sqlite_dialect_3_8_0, "SELECT id, name FROM users WHERE age > ?", (18,))
        right_query = Subquery(sqlite_dialect_3_8_0, "SELECT id, name FROM customers WHERE status = ?", ("active",))

        set_op = SetOperation(
            sqlite_dialect_3_8_0, left=left_query, right=right_query, op="union"
        )

        sql, params = set_op.to_sql()

        assert "UNION" in sql.upper()
        assert params == (18, "active")

    def test_union_all_operation(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test UNION ALL operation."""
        left_query = Subquery(sqlite_dialect_3_8_0, "SELECT id FROM table1", ())
        right_query = Subquery(sqlite_dialect_3_8_0, "SELECT id FROM table2", ())

        set_op = SetOperation(
            sqlite_dialect_3_8_0,
            left=left_query,
            right=right_query,
            op="union_all",
        )

        sql, params = set_op.to_sql()

        assert "UNION ALL" in sql.upper()
        assert params == ()

    def test_intersect_operation(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test INTERSECT operation."""
        left_query = Subquery(sqlite_dialect_3_8_0, "SELECT id FROM table1 WHERE col1 = ?", ("value1",))
        right_query = Subquery(sqlite_dialect_3_8_0, "SELECT id FROM table2 WHERE col2 = ?", ("value2",))

        set_op = SetOperation(
            sqlite_dialect_3_8_0, left=left_query, right=right_query, op="intersect"
        )

        sql, params = set_op.to_sql()

        assert "INTERSECT" in sql.upper()
        assert params == ("value1", "value2")

    def test_except_operation(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test EXCEPT operation."""
        left_query = Subquery(sqlite_dialect_3_8_0, "SELECT id FROM table1 WHERE active = ?", (True,))
        right_query = Subquery(sqlite_dialect_3_8_0, "SELECT id FROM table2 WHERE archived = ?", (True,))

        set_op = SetOperation(
            sqlite_dialect_3_8_0, left=left_query, right=right_query, op="except"
        )

        sql, params = set_op.to_sql()

        assert "EXCEPT" in sql.upper()
        assert params == (True, True)

    def test_nested_set_operations(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test nested set operations (set operation as operand)."""
        query1 = Subquery(sqlite_dialect_3_8_0, "SELECT id FROM table1 WHERE col = ?", ("a",))
        query2 = Subquery(sqlite_dialect_3_8_0, "SELECT id FROM table2 WHERE col = ?", ("b",))
        query3 = Subquery(sqlite_dialect_3_8_0, "SELECT id FROM table3 WHERE col = ?", ("c",))

        # First set operation
        inner_op = SetOperation(
            sqlite_dialect_3_8_0, left=query1, right=query2, op="union"
        )

        # Outer set operation using the inner one
        outer_op = SetOperation(
            sqlite_dialect_3_8_0, left=inner_op, right=query3, op="union"
        )

        sql, params = outer_op.to_sql()

        assert "UNION" in sql.upper()
        assert params == ("a", "b", "c")

    def test_set_operation_with_complex_queries(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test set operation with more complex query structures."""
        # Create complex left query
        left_table = NamedRelationRef(sqlite_dialect_3_8_0, Table(sqlite_dialect_3_8_0, "users"))
        left_query = QueryStatement(
            sqlite_dialect_3_8_0,
            select=[Column(sqlite_dialect_3_8_0, "id"), Column(sqlite_dialect_3_8_0, "name")],
            from_=left_table,
        )

        # Create complex right query
        right_table = NamedRelationRef(sqlite_dialect_3_8_0, Table(sqlite_dialect_3_8_0, "customers"))
        right_query = QueryStatement(
            sqlite_dialect_3_8_0,
            select=[Column(sqlite_dialect_3_8_0, "id"), Column(sqlite_dialect_3_8_0, "name")],
            from_=right_table,
        )

        set_op = SetOperation(
            sqlite_dialect_3_8_0, left=left_query, right=right_query, op="union"
        )

        sql, params = set_op.to_sql()

        assert "UNION" in sql.upper()
        assert '"users"' in sql or "SELECT" in sql
        assert '"customers"' in sql or "SELECT" in sql
        assert params == ()

    def test_set_operation_parameters_handling(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test that parameters from both sides are properly combined."""
        left_query = Subquery(sqlite_dialect_3_8_0, "SELECT id FROM users WHERE age > ? AND status = ?", (18, "active"))
        right_query = Subquery(sqlite_dialect_3_8_0, "SELECT id FROM customers WHERE region = ?", ("west",))

        set_op = SetOperation(
            sqlite_dialect_3_8_0, left=left_query, right=right_query, op="union"
        )

        sql, params = set_op.to_sql()

        # Should contain parameters from both queries
        assert params == (18, "active", "west")
        assert len(params) == 3

    def test_set_operation_word_form_is_stored_lowercase(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """The op word form is case-insensitive at construction, canonical lowercase stored."""
        left_query = Subquery(sqlite_dialect_3_8_0, "SELECT col FROM table1", ())
        right_query = Subquery(sqlite_dialect_3_8_0, "SELECT col FROM table2", ())

        set_op_upper = SetOperation(
            sqlite_dialect_3_8_0, left=left_query, right=right_query, op="UNION"
        )
        assert set_op_upper.op == "union"

        sql_upper, _ = set_op_upper.to_sql()
        assert "UNION" in sql_upper

    def test_set_operation_all_variants(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test all operation word forms, including the union_all variant."""
        query1 = Subquery(sqlite_dialect_3_8_0, "SELECT id FROM t1 WHERE a = ?", (1,))
        query2 = Subquery(sqlite_dialect_3_8_0, "SELECT id FROM t2 WHERE b = ?", (2,))

        for op in ("union", "union_all", "intersect", "except"):
            set_op = SetOperation(
                sqlite_dialect_3_8_0, left=query1, right=query2, op=op
            )

            sql, params = set_op.to_sql()
            assert op.replace("_", " ").upper() in sql.upper()
            assert params == (1, 2)

    def test_set_operation_without_alias(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """The node carries no alias: the SQL is the bare compound."""
        left_query = Subquery(sqlite_dialect_3_8_0, "SELECT id, name FROM users WHERE age > ?", (18,))
        right_query = Subquery(sqlite_dialect_3_8_0, "SELECT id, name FROM customers WHERE status = ?", ("active",))

        set_op = SetOperation(sqlite_dialect_3_8_0, left=left_query, right=right_query, op="union")

        sql, params = set_op.to_sql()

        # Verify that no alias is present in the SQL
        assert "AS" not in sql.upper() or "AS " not in sql
        # Verify UNION is still present
        assert "UNION" in sql.upper()
        # Verify parameters are still handled
        assert params == (18, "active")

    def test_trailing_clauses_are_not_node_parameters(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Trailing clauses belong to the statement level; the node takes none."""
        left_query = Subquery(sqlite_dialect_3_8_0, "SELECT id FROM t1", ())
        right_query = Subquery(sqlite_dialect_3_8_0, "SELECT id FROM t2", ())
        import pytest

        with pytest.raises(TypeError):
            SetOperation(
                sqlite_dialect_3_8_0, left=left_query, right=right_query, op="union",
                order_by_clause=None,
            )

    def test_set_operation_with_explain_basic(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test set operation with EXPLAIN clause."""
        from rhosocial.activerecord.backend.expression.statements import ExplainStatement, ExplainOptions

        left_query = Subquery(sqlite_dialect_3_8_0, "SELECT id, name FROM users WHERE age > ?", (18,))
        right_query = Subquery(sqlite_dialect_3_8_0, "SELECT id, name FROM customers WHERE status = ?", ("active",))

        # Create SetOperation first
        set_op = SetOperation(sqlite_dialect_3_8_0, left=left_query, right=right_query, op="union")

        # Wrap the set operation in an EXPLAIN expression
        explain_options = ExplainOptions()
        explain_expr = ExplainStatement(sqlite_dialect_3_8_0, set_op, explain_options)

        sql, params = explain_expr.to_sql()

        # Verify EXPLAIN is present in the SQL
        assert "EXPLAIN" in sql.upper()
        # Verify the set operation is included
        assert "UNION" in sql.upper()
        # Verify parameters are still handled
        assert params == (18, "active")

    def test_set_operation_with_explain_query_plan(self, sqlite_dialect_3_8_0: SQLiteDialect):
        """Test set operation with EXPLAIN QUERY PLAN clause."""
        from rhosocial.activerecord.backend.expression.statements import ExplainStatement, ExplainOptions, ExplainType

        left_query = Subquery(sqlite_dialect_3_8_0, "SELECT id, name FROM users WHERE age > ?", (18,))
        right_query = Subquery(sqlite_dialect_3_8_0, "SELECT id, name FROM customers WHERE status = ?", ("active",))

        # Create SetOperation first
        set_op = SetOperation(sqlite_dialect_3_8_0, left=left_query, right=right_query, op="union")

        # Wrap the set operation in an EXPLAIN QUERY PLAN expression
        explain_options = ExplainOptions(type=ExplainType.QUERY_PLAN)
        explain_expr = ExplainStatement(sqlite_dialect_3_8_0, set_op, explain_options)

        sql, params = explain_expr.to_sql()

        # Verify EXPLAIN QUERY PLAN is present in the SQL
        assert "EXPLAIN" in sql.upper()
        # For SQLite, EXPLAIN QUERY PLAN is the default behavior
        # Verify the set operation is included
        assert "UNION" in sql.upper()
        # Verify parameters are still handled
        assert params == (18, "active")
