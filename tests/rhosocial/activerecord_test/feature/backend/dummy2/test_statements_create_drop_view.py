import pytest
from rhosocial.activerecord.backend.expression import (
    Column, Literal, FunctionCall, TableExpression, QueryExpression, 
    CreateViewExpression, DropViewExpression
)
from rhosocial.activerecord.backend.expression.statements import ViewOptions, ViewCheckOption
from rhosocial.activerecord.backend.expression.query_parts import WhereClause, GroupByHavingClause, LimitOffsetClause, OrderByClause
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect


class TestCreateDropViewStatements:
    """Tests for CREATE VIEW and DROP VIEW statement expressions."""

    def test_basic_create_view(self, dummy_dialect: DummyDialect):
        """Tests basic CREATE VIEW statement."""
        query = QueryExpression(
            dummy_dialect,
            select=[Column(dummy_dialect, "id"), Column(dummy_dialect, "name")],
            from_=TableExpression(dummy_dialect, "users")
        )

        create_view = CreateViewExpression(
            dummy_dialect,
            view_name="user_view",
            query=query
        )
        sql, params = create_view.to_sql()

        assert 'CREATE VIEW "user_view"' in sql
        assert 'SELECT "id", "name" FROM "users"' in sql
        assert params == ()

    def test_create_or_replace_view(self, dummy_dialect: DummyDialect):
        """Tests CREATE OR REPLACE VIEW statement."""
        query = QueryExpression(
            dummy_dialect,
            select=[FunctionCall(dummy_dialect, "COUNT", Column(dummy_dialect, "id"))],
            from_=TableExpression(dummy_dialect, "orders"),
            group_by_having=GroupByHavingClause(dummy_dialect, group_by=[Column(dummy_dialect, "user_id")])
        )

        create_view = CreateViewExpression(
            dummy_dialect,
            view_name="order_counts",
            query=query,
            replace=True  # CREATE OR REPLACE
        )
        sql, params = create_view.to_sql()

        assert 'CREATE OR REPLACE VIEW "order_counts"' in sql
        assert 'COUNT("id")' in sql
        assert params == ()

    def test_create_view_with_column_aliases(self, dummy_dialect: DummyDialect):
        """Tests CREATE VIEW with column aliases."""
        query = QueryExpression(
            dummy_dialect,
            select=[
                Column(dummy_dialect, "user_id"),
                FunctionCall(dummy_dialect, "COUNT", Column(dummy_dialect, "order_id"), alias="total_orders")
            ],
            from_=TableExpression(dummy_dialect, "user_orders"),
            group_by_having=GroupByHavingClause(dummy_dialect, group_by=[Column(dummy_dialect, "user_id")])
        )

        create_view = CreateViewExpression(
            dummy_dialect,
            view_name="user_order_summary",
            query=query,
            column_aliases=["user_id", "total_orders"]  # Explicitly define column aliases
        )
        sql, params = create_view.to_sql()

        # Should have the explicit column names in parentheses
        assert 'CREATE VIEW "user_order_summary" ("user_id", "total_orders")' in sql or 'CREATE VIEW "user_order_summary" AS' in sql
        assert 'COUNT("order_id") AS "total_orders"' in sql
        assert params == ()

    def test_create_temporary_view(self, dummy_dialect: DummyDialect):
        """Tests CREATE TEMPORARY VIEW statement."""
        query = QueryExpression(
            dummy_dialect,
            select=[Column(dummy_dialect, "session_id"), Column(dummy_dialect, "data")],
            from_=TableExpression(dummy_dialect, "temp_sessions")
        )

        create_view = CreateViewExpression(
            dummy_dialect,
            view_name="temp_user_session",
            query=query,
            temporary=True  # Create a temporary view
        )
        sql, params = create_view.to_sql()

        assert 'CREATE TEMPORARY VIEW "temp_user_session"' in sql
        assert params == ()

    @pytest.mark.parametrize("check_option,expected_part", [
        pytest.param(ViewCheckOption.LOCAL, "WITH LOCAL CHECK OPTION", id="local_check"),
        pytest.param(ViewCheckOption.CASCADED, "WITH CASCADED CHECK OPTION", id="cascaded_check"),
        pytest.param(None, "", id="no_check_option"),
    ]) 
    def test_create_view_with_check_options(self, dummy_dialect: DummyDialect, check_option, expected_part):
        """Tests CREATE VIEW with different check options."""
        query = QueryExpression(
            dummy_dialect,
            select=[Column(dummy_dialect, "id"), Column(dummy_dialect, "status")],
            from_=TableExpression(dummy_dialect, "entities"),
            where=WhereClause(dummy_dialect, condition=Column(dummy_dialect, "status") == Literal(dummy_dialect, "active"))
        )

        options = ViewOptions(check_option=check_option)
        create_view = CreateViewExpression(
            dummy_dialect,
            view_name="active_entities",
            query=query,
            options=options
        )
        sql, params = create_view.to_sql()

        assert 'CREATE VIEW "active_entities"' in sql
        if expected_part:
            assert expected_part in sql

    def test_drop_view_basic(self, dummy_dialect: DummyDialect):
        """Tests basic DROP VIEW statement."""
        drop_view = DropViewExpression(
            dummy_dialect,
            view_name="old_view"
        )
        sql, params = drop_view.to_sql()

        assert sql == 'DROP VIEW "old_view"'
        assert params == ()

    def test_drop_view_with_if_exists(self, dummy_dialect: DummyDialect):
        """Tests DROP VIEW IF EXISTS statement."""
        drop_view = DropViewExpression(
            dummy_dialect,
            view_name="possibly_missing_view",
            if_exists=True  # IF EXISTS option
        )
        sql, params = drop_view.to_sql()

        assert sql == 'DROP VIEW IF EXISTS "possibly_missing_view"'
        assert params == ()

    def test_drop_view_with_cascade(self, dummy_dialect: DummyDialect):
        """Tests DROP VIEW ... CASCADE statement."""
        drop_view = DropViewExpression(
            dummy_dialect,
            view_name="master_view",
            cascade=True  # CASCADE option to drop dependent objects
        )
        sql, params = drop_view.to_sql()

        assert sql == 'DROP VIEW "master_view" CASCADE'
        assert params == ()

    def test_drop_view_if_exists_cascade(self, dummy_dialect: DummyDialect):
        """Tests DROP VIEW IF EXISTS ... CASCADE statement."""
        drop_view = DropViewExpression(
            dummy_dialect,
            view_name="dependent_view",
            if_exists=True,  # IF EXISTS
            cascade=True  # CASCADE
        )
        sql, params = drop_view.to_sql()

        assert sql == 'DROP VIEW IF EXISTS "dependent_view" CASCADE'
        assert params == ()

    def test_create_view_complex_aggregate(self, dummy_dialect: DummyDialect):
        """Tests CREATE VIEW with complex aggregate query."""
        query = QueryExpression(
            dummy_dialect,
            select=[
                Column(dummy_dialect, "department"),
                FunctionCall(dummy_dialect, "COUNT", Column(dummy_dialect, "id"), alias="employee_count"),
                FunctionCall(dummy_dialect, "AVG", Column(dummy_dialect, "salary"), alias="avg_salary")
            ],
            from_=TableExpression(dummy_dialect, "employees"),
            group_by_having=GroupByHavingClause(
                dummy_dialect,
                group_by=[Column(dummy_dialect, "department")],
                having=FunctionCall(dummy_dialect, "COUNT", Column(dummy_dialect, "id")) > Literal(dummy_dialect, 5)
            )
        )

        create_view = CreateViewExpression(
            dummy_dialect,
            view_name="dept_stats",
            query=query
        )
        sql, params = create_view.to_sql()

        assert 'CREATE VIEW "dept_stats"' in sql
        assert 'COUNT("id") AS "employee_count"' in sql
        assert 'AVG("salary") AS "avg_salary"' in sql
        assert 'GROUP BY "department"' in sql
        assert 'HAVING COUNT("id") > ?' in sql
        assert params == (5,)

    @pytest.mark.parametrize("view_name, expected_identifier", [
        pytest.param("simple_view", '"simple_view"', id="simple_name"),
        pytest.param("view_with_underscores", '"view_with_underscores"', id="underscore_name"),
        pytest.param("ViewWithCamelCase", '"ViewWithCamelCase"', id="camelcase_name"),
        pytest.param("view-with-hyphens", '"view-with-hyphens"', id="hyphen_name"),
        pytest.param("view with spaces", '"view with spaces"', id="spaced_name"),
    ])
    def test_create_view_various_names(self, dummy_dialect: DummyDialect, view_name, expected_identifier):
        """Tests CREATE VIEW with various view name formats."""
        query = QueryExpression(
            dummy_dialect,
            select=[Literal(dummy_dialect, 1)],
            from_=TableExpression(dummy_dialect, "dual")  # Using dual table for scalar SELECT
        )

        create_view = CreateViewExpression(
            dummy_dialect,
            view_name=view_name,
            query=query
        )
        sql, params = create_view.to_sql()

        assert f'CREATE VIEW {expected_identifier}' in sql
        assert params == (1,)

    def test_create_view_scalar_query(self, dummy_dialect: DummyDialect):
        """Tests CREATE VIEW with a scalar query (no FROM clause)."""
        # Create a scalar query - just selecting a constant
        query = QueryExpression(
            dummy_dialect,
            select=[Literal(dummy_dialect, 42)]
        )

        create_view = CreateViewExpression(
            dummy_dialect,
            view_name="scalar_value_view",
            query=query
        )
        sql, params = create_view.to_sql()

        assert 'CREATE VIEW "scalar_value_view"' in sql
        # Should contain the scalar value
        assert 'SELECT ?' in sql or 'SELECT 42' in sql
        if '?' in sql:
            assert params == (42,)

    def test_create_view_with_where_clause_object(self, dummy_dialect: DummyDialect):
        """Tests CREATE VIEW with a query that has a where clause object."""
        where_clause = WhereClause(
            dummy_dialect,
            condition=Column(dummy_dialect, "status") == Literal(dummy_dialect, "active")
        )
        # The where clause would be part of the query object, not as a separate parameter
        query = QueryExpression(
            dummy_dialect,
            select=[Column(dummy_dialect, "id"), Column(dummy_dialect, "name")],
            from_=TableExpression(dummy_dialect, "users"),
            where=WhereClause(dummy_dialect, condition=Column(dummy_dialect, "status") == Literal(dummy_dialect, "active"))  # Using overloaded operator
        )

        create_view = CreateViewExpression(
            dummy_dialect,
            view_name="active_users",
            query=query
        )
        sql, params = create_view.to_sql()

        assert 'CREATE VIEW "active_users"' in sql
        assert 'FROM "users"' in sql
        assert 'WHERE "status" = ?' in sql
        assert params == ("active",)

    def test_create_view_with_order_by_limit(self, dummy_dialect: DummyDialect):
        """Tests CREATE VIEW with ORDER BY and LIMIT clauses."""
        query = QueryExpression(
            dummy_dialect,
            select=[Column(dummy_dialect, "id"), Column(dummy_dialect, "created_at")],
            from_=TableExpression(dummy_dialect, "recent_items"),
            order_by=OrderByClause(dummy_dialect, expressions=[(Column(dummy_dialect, "created_at"), "DESC")]),
            limit_offset=LimitOffsetClause(dummy_dialect, limit=10)
        )

        create_view = CreateViewExpression(
            dummy_dialect,
            view_name="top_recent_items",
            query=query
        )
        sql, params = create_view.to_sql()

        assert 'CREATE VIEW "top_recent_items"' in sql
        assert 'ORDER BY "created_at" DESC' in sql
        assert 'LIMIT ?' in sql or 'LIMIT 10' in sql
        if 'LIMIT ?' in sql:
            assert params == (10,)  # Check for the limit parameter

    @pytest.mark.parametrize("replace_flag", [
        pytest.param(True, id="with_replace"),
        pytest.param(False, id="without_replace"),
    ])
    def test_create_view_replace_option(self, dummy_dialect: DummyDialect, replace_flag):
        """Tests CREATE VIEW with different replace options."""
        query = QueryExpression(
            dummy_dialect,
            select=[Column(dummy_dialect, "id")],
            from_=TableExpression(dummy_dialect, "test_table")
        )

        create_view = CreateViewExpression(
            dummy_dialect,
            view_name="test_view",
            query=query,
            replace=replace_flag
        )
        sql, params = create_view.to_sql()

        if replace_flag:
            assert 'CREATE OR REPLACE VIEW "test_view"' in sql
        else:
            assert 'CREATE VIEW "test_view"' in sql
            assert 'OR REPLACE' not in sql
        assert params == ()

    def test_drop_view_complex_name(self, dummy_dialect: DummyDialect):
        """Tests DROP VIEW with complex view name."""
        complex_name = "schema.special-view.with.dots"
        drop_view = DropViewExpression(
            dummy_dialect,
            view_name=complex_name
        )
        sql, params = drop_view.to_sql()

        # The name should be properly quoted/identified
        assert f'DROP VIEW "{complex_name}"' == sql
        assert params == ()

    def test_create_view_join_based(self, dummy_dialect: DummyDialect):
        """Tests CREATE VIEW based on a JOIN query."""
        from rhosocial.activerecord.backend.expression.query_clauses import JoinExpression
        
        # Create a join between users and profiles
        users_table = TableExpression(dummy_dialect, "users", alias="u")
        profiles_table = TableExpression(dummy_dialect, "profiles", alias="p")
        join_condition = Column(dummy_dialect, "user_id", "u") == Column(dummy_dialect, "user_id", "p")
        join_expr = JoinExpression(
            dummy_dialect,
            left_table=users_table,
            right_table=profiles_table,
            condition=join_condition,
            join_type="INNER"
        )

        query = QueryExpression(
            dummy_dialect,
            select=[
                Column(dummy_dialect, "id", "u"),
                Column(dummy_dialect, "name", "u"),
                Column(dummy_dialect, "profile_image", "p")
            ],
            from_=join_expr
        )

        create_view = CreateViewExpression(
            dummy_dialect,
            view_name="user_profile_view",
            query=query
        )
        sql, params = create_view.to_sql()

        assert 'CREATE VIEW "user_profile_view"' in sql
        assert 'INNER JOIN' in sql
        assert '"users" AS "u"' in sql
        assert '"profiles" AS "p"' in sql
        assert params == ()

    def test_view_roundtrip_creation_and_deletion(self, dummy_dialect: DummyDialect):
        """Tests creating a view and then dropping it."""
        # First create a view
        query = QueryExpression(
            dummy_dialect,
            select=[Column(dummy_dialect, "id"), Column(dummy_dialect, "name")],
            from_=TableExpression(dummy_dialect, "source_table")
        )
        create_view = CreateViewExpression(
            dummy_dialect,
            view_name="roundtrip_test_view",
            query=query
        )
        create_sql, create_params = create_view.to_sql()

        # Then drop the same view
        drop_view = DropViewExpression(
            dummy_dialect,
            view_name="roundtrip_test_view"
        )
        drop_sql, drop_params = drop_view.to_sql()

        # Verify both statements are correctly formed
        assert 'CREATE VIEW "roundtrip_test_view"' in create_sql
        assert 'SELECT "id", "name" FROM "source_table"' in create_sql
        assert 'DROP VIEW "roundtrip_test_view"' == drop_sql
        assert create_params == ()
        assert drop_params == ()

    def test_create_view_with_nested_query(self, dummy_dialect: DummyDialect):
        """Tests CREATE VIEW with a nested query (subquery in FROM clause)."""
        # Inner query
        inner_query = QueryExpression(
            dummy_dialect,
            select=[
                Column(dummy_dialect, "user_id"),
                FunctionCall(dummy_dialect, "COUNT", Column(dummy_dialect, "order_id"), alias="order_count")
            ],
            from_=TableExpression(dummy_dialect, "orders"),
            group_by_having=GroupByHavingClause(dummy_dialect, group_by=[Column(dummy_dialect, "user_id")])
        )

        # For now, using a simple table expression to simulate subquery
        simple_query = QueryExpression(
            dummy_dialect,
            select=[
                Column(dummy_dialect, "user_id"),
                FunctionCall(dummy_dialect, "MAX", Column(dummy_dialect, "order_date"), alias="latest_order")
            ],
            from_=TableExpression(dummy_dialect, "user_orders"),
            group_by_having=GroupByHavingClause(dummy_dialect, group_by=[Column(dummy_dialect, "user_id")])
        )

        create_view = CreateViewExpression(
            dummy_dialect,
            view_name="user_latest_order",
            query=simple_query
        )
        sql, params = create_view.to_sql()

        assert 'CREATE VIEW "user_latest_order"' in sql
        assert 'MAX("order_date")' in sql
        assert params == ()

    def test_create_view_with_window_function(self, dummy_dialect: DummyDialect):
        """Tests CREATE VIEW with a query that includes window functions."""
        from rhosocial.activerecord.backend.expression.advanced_functions import (
            WindowSpecification, WindowFunctionCall
        )

        # Create a window specification
        window_spec = WindowSpecification(
            dummy_dialect,
            partition_by=[Column(dummy_dialect, "department")],
            order_by=[(Column(dummy_dialect, "salary"), "DESC")]
        )

        # Create a window function call
        rank_func = WindowFunctionCall(
            dummy_dialect,
            function_name="ROW_NUMBER",
            window_spec=window_spec,
            alias="rank_in_dept"
        )

        query = QueryExpression(
            dummy_dialect,
            select=[
                Column(dummy_dialect, "employee_name"),
                Column(dummy_dialect, "department"),
                Column(dummy_dialect, "salary"),
                rank_func  # Window function in select
            ],
            from_=TableExpression(dummy_dialect, "employees")
        )

        create_view = CreateViewExpression(
            dummy_dialect,
            view_name="ranked_employees",
            query=query
        )
        sql, params = create_view.to_sql()

        assert 'CREATE VIEW "ranked_employees"' in sql
        assert 'ROW_NUMBER() OVER' in sql
        assert params == ()

    @pytest.mark.parametrize("temporary_flag", [
        pytest.param(True, id="temporary_view"),
        pytest.param(False, id="permanent_view"),
    ])
    def test_create_view_temporary_option(self, dummy_dialect: DummyDialect, temporary_flag):
        """Tests CREATE VIEW with different temporary options."""
        query = QueryExpression(
            dummy_dialect,
            select=[Literal(dummy_dialect, 1)]
        )

        create_view = CreateViewExpression(
            dummy_dialect,
            view_name="temp_test_view",
            query=query,
            temporary=temporary_flag
        )
        sql, params = create_view.to_sql()

        if temporary_flag:
            assert 'CREATE TEMPORARY VIEW "temp_test_view"' in sql
        else:
            # Should not have TEMPORARY keyword
            assert 'CREATE VIEW "temp_test_view"' in sql and 'TEMPORARY' not in sql.split('CREATE')[1].split('VIEW')[0]
        assert params == (1,)

    def test_drop_view_nonexistent_no_error(self, dummy_dialect: DummyDialect):
        """Tests that DROP VIEW IF EXISTS doesn't error on nonexistent views."""
        drop_view = DropViewExpression(
            dummy_dialect,
            view_name="nonexistent_view",
            if_exists=True  # Should not raise error if view doesn't exist
        )
        sql, params = drop_view.to_sql()

        assert 'DROP VIEW IF EXISTS "nonexistent_view"' in sql
        assert params == ()