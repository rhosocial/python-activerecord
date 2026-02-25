# tests/rhosocial/activerecord_test/feature/query/sqlite/test_sqlite_cte_query_explain.py
"""
Tests for the EXPLAIN clause functionality with CTE queries specific to the SQLite backend.

The generic testsuite does not cover backend-specific clauses like EXPLAIN.
This file provides tests for CTEQuery and AsyncCTEQuery to ensure
the .explain() method works correctly for various CTE query types.

Note:
- These tests are specific to SQLite backend behavior for CTE EXPLAIN functionality.
"""
import pytest
from decimal import Decimal
from typing import List, Dict, Any

from rhosocial.activerecord.query import CTEQuery, AsyncCTEQuery
from rhosocial.activerecord.backend.expression import statements, core


def _validate_explain_output(plan: List[Dict[str, Any]], test_name: str = ""):
    """
    Helper to validate the structure of the EXPLAIN query plan for SQLite.
    """
    if test_name:
        print(f"\nPlan for {test_name}: {plan}") # Debug print

    assert isinstance(plan, list)
    assert len(plan) > 0
    for row in plan:
        assert isinstance(row, dict)
        # SQLite's EXPLAIN output typically includes these columns
        assert 'addr' in row or 'addr' in row  # Using 'addr' as mentioned in the original
        assert 'opcode' in row
        assert 'p1' in row
        assert 'p2' in row
        assert 'p3' in row
        assert 'p4' in row
        assert 'p5' in row
        assert 'comment' in row


@pytest.mark.sqlite
class TestSqliteCTEQueryExplain:
    """Synchronous tests for EXPLAIN clause with CTEQuery."""

    def test_cte_explain_with_union_of_active_queries(self, order_fixtures):
        """
        Test EXPLAIN on CTE query that uses a UNION operation between two ActiveQuery instances.

        This test verifies that EXPLAIN works correctly with CTE queries containing UNION operations.
        """
        User, Order, OrderItem = order_fixtures

        # Create test data
        user = User(username='cte_explain_union_user', email='cte_explain_union@example.com', age=30)
        user.save()

        # Create orders for the test
        order1 = Order(user_id=user.id, order_number='CTE-EXPLAIN-UNION-001', total_amount=Decimal('100.00'), status='active')
        order2 = Order(user_id=user.id, order_number='CTE-EXPLAIN-UNION-002', total_amount=Decimal('200.00'), status='completed')
        order3 = Order(user_id=user.id, order_number='CTE-EXPLAIN-UNION-003', total_amount=Decimal('300.00'), status='pending')
        order1.save()
        order2.save()
        order3.save()

        # Get backend from model
        backend = Order.backend()

        # Create two ActiveQuery instances for the UNION operation
        active_orders_query = Order.query().where(Order.c.status == 'active')
        completed_orders_query = Order.query().where(Order.c.status == 'completed')

        # Perform UNION operation between the two ActiveQuery instances
        union_query = active_orders_query.union(completed_orders_query)

        # Create a CTE that uses the UNION operation as its source

        cte_query = CTEQuery(backend)
        cte_query.with_cte('union_orders_cte', union_query)

        # Use the new API: specify which CTE to use and apply EXPLAIN using mixins
        plan = cte_query.from_cte('union_orders_cte').select('*').explain().aggregate()

        # Validate the explain output
        _validate_explain_output(plan, "CTE UNION Query")

    def test_cte_explain_with_intersect_of_active_queries(self, order_fixtures):
        """
        Test EXPLAIN on CTE query that uses an INTERSECT operation between two ActiveQuery instances.

        This test verifies that EXPLAIN works correctly with CTE queries containing INTERSECT operations.
        """
        User, Order, OrderItem = order_fixtures

        # Create test data
        user = User(username='cte_explain_intersect_user', email='cte_explain_intersect@example.com', age=35)
        user.save()

        # Create orders for the test - we'll create some orders with specific amounts
        # to make sure there are some overlaps for the intersect operation
        order1 = Order(user_id=user.id, order_number='CTE-EXPLAIN-INTERSECT-001', total_amount=Decimal('150.00'), status='active')
        order2 = Order(user_id=user.id, order_number='CTE-EXPLAIN-INTERSECT-002', total_amount=Decimal('200.00'), status='active')
        order3 = Order(user_id=user.id, order_number='CTE-EXPLAIN-INTERSECT-003', total_amount=Decimal('150.00'), status='pending')
        order4 = Order(user_id=user.id, order_number='CTE-EXPLAIN-INTERSECT-004', total_amount=Decimal('250.00'), status='completed')
        order1.save()
        order2.save()
        order3.save()
        order4.save()

        # Get backend from model
        backend = Order.backend()

        # Create two ActiveQuery instances for the INTERSECT operation
        # First query: orders with amount > 100
        high_amount_query = Order.query().where(Order.c.total_amount > Decimal('100.00'))
        # Second query: active orders (regardless of amount)
        active_orders_query = Order.query().where(Order.c.status == 'active')

        # Perform INTERSECT operation between the two ActiveQuery instances
        intersect_query = high_amount_query.intersect(active_orders_query)

        # Create a CTE that uses the INTERSECT operation as its source
        cte_query = CTEQuery(backend)
        cte_query.with_cte('intersect_orders_cte', intersect_query)

        # Use the new API: specify which CTE to use and apply EXPLAIN using mixins
        plan = cte_query.from_cte('intersect_orders_cte').select('*').explain().aggregate()

        # Validate the explain output
        _validate_explain_output(plan, "CTE INTERSECT Query")

    def test_cte_explain_with_except_of_active_queries(self, order_fixtures):
        """
        Test EXPLAIN on CTE query that uses an EXCEPT operation between two ActiveQuery instances.

        This test verifies that EXPLAIN works correctly with CTE queries containing EXCEPT operations.
        """
        User, Order, OrderItem = order_fixtures

        # Create test data
        user = User(username='cte_explain_except_user', email='cte_explain_except@example.com', age=40)
        user.save()

        # Create orders for the test
        order1 = Order(user_id=user.id, order_number='CTE-EXPLAIN-EXCEPT-001', total_amount=Decimal('100.00'), status='active')
        order2 = Order(user_id=user.id, order_number='CTE-EXPLAIN-EXCEPT-002', total_amount=Decimal('200.00'), status='completed')
        order3 = Order(user_id=user.id, order_number='CTE-EXPLAIN-EXCEPT-003', total_amount=Decimal('300.00'), status='pending')
        order4 = Order(user_id=user.id, order_number='CTE-EXPLAIN-EXCEPT-004', total_amount=Decimal('400.00'), status='active')
        order1.save()
        order2.save()
        order3.save()
        order4.save()

        # Get backend from model
        backend = Order.backend()

        # Create two ActiveQuery instances for the EXCEPT operation
        # First query: all orders
        all_orders_query = Order.query()
        # Second query: completed orders
        completed_orders_query = Order.query().where(Order.c.status == 'completed')

        # Perform EXCEPT operation between the two ActiveQuery instances
        except_query = all_orders_query.except_(completed_orders_query)

        # Create a CTE that uses the EXCEPT operation as its source
        cte_query = CTEQuery(backend)
        cte_query.with_cte('except_orders_cte', except_query)

        # Use the new API: specify which CTE to use and apply EXPLAIN using mixins
        plan = cte_query.from_cte('except_orders_cte').select('*').explain().aggregate()

        # Validate the explain output
        _validate_explain_output(plan, "CTE EXCEPT Query")

    def test_cte_explain_with_query_expression(self, order_fixtures):
        """
        Test EXPLAIN on CTE query that uses a QueryExpression as the underlying query.

        This test verifies that EXPLAIN works correctly with CTE queries containing QueryExpression.
        """
        User, Order, OrderItem = order_fixtures

        # Create test data
        user = User(username='cte_explain_query_expr_user', email='cte_explain_query_expr@example.com', age=30)
        user.save()

        # Create orders for the test
        order1 = Order(user_id=user.id, order_number='CTE-EXPLAIN-QUERY-EXPR-001', total_amount=Decimal('100.00'), status='active')
        order2 = Order(user_id=user.id, order_number='CTE-EXPLAIN-QUERY-EXPR-002', total_amount=Decimal('200.00'), status='completed')
        order1.save()
        order2.save()

        # Get backend and dialect
        backend = Order.backend()
        dialect = backend.dialect

        # Create a QueryExpression directly (this implements ToSQLProtocol)
        from rhosocial.activerecord.backend.expression import statements, core
        query_expr = statements.QueryExpression(
            dialect,
            select=[core.Column(dialect, "id"), core.Column(dialect, "status"), core.Column(dialect, "total_amount")],
            from_=core.TableExpression(dialect, Order.table_name()),
            where=statements.WhereClause(dialect, condition=core.Column(dialect, "status") == core.Literal(dialect, 'active'))
        )

        # Create a CTE that uses the QueryExpression as its source
        cte_query = CTEQuery(backend)
        cte_query.with_cte('query_expr_cte', query_expr)

        # Use the new API: specify which CTE to use and apply EXPLAIN using mixins
        plan = cte_query.from_cte('query_expr_cte').select('*').explain().aggregate()

        # Validate the explain output
        _validate_explain_output(plan, "CTE QueryExpression")

    def test_cte_explain_with_query_expression_as_main_query(self, order_fixtures):
        """
        Test EXPLAIN on CTE query where the main query is a QueryExpression.

        This test verifies that EXPLAIN works correctly with CTE queries where the main query is a QueryExpression.
        """
        User, Order, OrderItem = order_fixtures

        # Create test data
        user = User(username='cte_explain_main_query_expr_user', email='cte_explain_main_query_expr@example.com', age=35)
        user.save()

        # Create orders for the test
        order1 = Order(user_id=user.id, order_number='CTE-EXPLAIN-MAIN-QUERY-EXPR-001', total_amount=Decimal('150.00'), status='active')
        order2 = Order(user_id=user.id, order_number='CTE-EXPLAIN-MAIN-QUERY-EXPR-002', total_amount=Decimal('250.00'), status='pending')
        order1.save()
        order2.save()

        # Get backend and dialect
        backend = Order.backend()
        dialect = backend.dialect

        # Create a CTE with a simple query
        cte_query = CTEQuery(backend)
        cte_query.with_cte('simple_orders_cte', (f"SELECT id, status, total_amount FROM {Order.table_name()} WHERE status IN (?, ?)", ('active', 'pending')))

        # Use the new API: specify which CTE to use and apply EXPLAIN using mixins
        plan = cte_query.from_cte('simple_orders_cte').select('id', 'status', 'total_amount').where("total_amount > ?", (Decimal('100.00'),)).explain().aggregate()

        # Validate the explain output
        _validate_explain_output(plan, "CTE QueryExpression as Main Query")


@pytest.mark.sqlite
@pytest.mark.asyncio
class TestAsyncSqliteCTEQueryExplain:
    """Asynchronous tests for EXPLAIN clause with AsyncCTEQuery."""

    async def test_async_cte_explain_with_union_of_active_queries(self, async_order_fixtures):
        """
        Async version of test_cte_explain_with_union_of_active_queries.
        """
        AsyncUser, AsyncOrder, AsyncOrderItem = async_order_fixtures

        # Create test data
        user = AsyncUser(username='async_cte_explain_union_user', email='async_cte_explain_union@example.com', age=30)
        await user.save()

        # Create orders for the test
        order1 = AsyncOrder(user_id=user.id, order_number='ASYNC-CTE-EXPLAIN-UNION-001', total_amount=Decimal('100.00'), status='active')
        order2 = AsyncOrder(user_id=user.id, order_number='ASYNC-CTE-EXPLAIN-UNION-002', total_amount=Decimal('200.00'), status='completed')
        order3 = AsyncOrder(user_id=user.id, order_number='ASYNC-CTE-EXPLAIN-UNION-003', total_amount=Decimal('300.00'), status='pending')
        await order1.save()
        await order2.save()
        await order3.save()

        # Get backend from model
        backend = AsyncOrder.backend()

        # Create two ActiveQuery instances for the UNION operation
        active_orders_query = AsyncOrder.query().where(AsyncOrder.c.status == 'active')
        completed_orders_query = AsyncOrder.query().where(AsyncOrder.c.status == 'completed')

        # Get the SQL and params for the UNION operation
        union_query = active_orders_query.union(completed_orders_query)
        union_sql, union_params = union_query.to_sql()

        # Create a CTE that uses the UNION SQL and params as its source
        # Pass the SQL and params as a tuple to preserve the parameters
        cte_query = AsyncCTEQuery(backend)
        cte_query.with_cte('union_orders_cte', (union_sql, union_params))

        # Use the new API: specify which CTE to use and apply EXPLAIN using mixins
        plan = await cte_query.from_cte('union_orders_cte').select('*').explain().aggregate()

        # Validate the explain output
        _validate_explain_output(plan, "Async CTE UNION Query")

    async def test_async_cte_explain_with_intersect_of_active_queries(self, async_order_fixtures):
        """
        Async version of test_cte_explain_with_intersect_of_active_queries.
        """
        AsyncUser, AsyncOrder, AsyncOrderItem = async_order_fixtures

        # Create test data
        user = AsyncUser(username='async_cte_explain_intersect_user', email='async_cte_explain_intersect@example.com', age=35)
        await user.save()

        # Create orders for the test
        order1 = AsyncOrder(user_id=user.id, order_number='ASYNC-CTE-EXPLAIN-INTERSECT-001', total_amount=Decimal('150.00'), status='active')
        order2 = AsyncOrder(user_id=user.id, order_number='ASYNC-CTE-EXPLAIN-INTERSECT-002', total_amount=Decimal('200.00'), status='active')
        order3 = AsyncOrder(user_id=user.id, order_number='ASYNC-CTE-EXPLAIN-INTERSECT-003', total_amount=Decimal('150.00'), status='pending')
        order4 = AsyncOrder(user_id=user.id, order_number='ASYNC-CTE-EXPLAIN-INTERSECT-004', total_amount=Decimal('250.00'), status='completed')
        await order1.save()
        await order2.save()
        await order3.save()
        await order4.save()

        # Get backend from model
        backend = AsyncOrder.backend()

        # Create two ActiveQuery instances for the INTERSECT operation
        # First query: orders with amount > 100
        high_amount_query = AsyncOrder.query().where(AsyncOrder.c.total_amount > Decimal('100.00'))
        # Second query: active orders (regardless of amount)
        active_orders_query = AsyncOrder.query().where(AsyncOrder.c.status == 'active')

        # Get the SQL and params for the INTERSECT operation
        intersect_query = high_amount_query.intersect(active_orders_query)
        intersect_sql, intersect_params = intersect_query.to_sql()

        # Create a CTE that uses the INTERSECT SQL and params as its source
        cte_query = AsyncCTEQuery(backend)
        cte_query.with_cte('intersect_orders_cte', (intersect_sql, intersect_params))

        # Use the new API: specify which CTE to use and apply EXPLAIN using mixins
        plan = await cte_query.from_cte('intersect_orders_cte').select('*').explain().aggregate()

        # Validate the explain output
        _validate_explain_output(plan, "Async CTE INTERSECT Query")

    async def test_async_cte_explain_with_except_of_active_queries(self, async_order_fixtures):
        """
        Async version of test_cte_explain_with_except_of_active_queries.
        """
        AsyncUser, AsyncOrder, AsyncOrderItem = async_order_fixtures

        # Create test data
        user = AsyncUser(username='async_cte_explain_except_user', email='async_cte_explain_except@example.com', age=40)
        await user.save()

        # Create orders for the test
        order1 = AsyncOrder(user_id=user.id, order_number='ASYNC-CTE-EXPLAIN-EXCEPT-001', total_amount=Decimal('100.00'), status='active')
        order2 = AsyncOrder(user_id=user.id, order_number='ASYNC-CTE-EXPLAIN-EXCEPT-002', total_amount=Decimal('200.00'), status='completed')
        order3 = AsyncOrder(user_id=user.id, order_number='ASYNC-CTE-EXPLAIN-EXCEPT-003', total_amount=Decimal('300.00'), status='pending')
        order4 = AsyncOrder(user_id=user.id, order_number='ASYNC-CTE-EXPLAIN-EXCEPT-004', total_amount=Decimal('400.00'), status='active')
        await order1.save()
        await order2.save()
        await order3.save()
        await order4.save()

        # Get backend from model
        backend = AsyncOrder.backend()

        # Create two ActiveQuery instances for the EXCEPT operation
        # First query: all orders
        all_orders_query = AsyncOrder.query()
        # Second query: completed orders
        completed_orders_query = AsyncOrder.query().where(AsyncOrder.c.status == 'completed')

        # Get the SQL and params for the EXCEPT operation
        except_query = all_orders_query.except_(completed_orders_query)
        except_sql, except_params = except_query.to_sql()

        # Create a CTE that uses the EXCEPT SQL and params as its source
        cte_query = AsyncCTEQuery(backend)
        cte_query.with_cte('except_orders_cte', (except_sql, except_params))

        # Use the new API: specify which CTE to use and apply EXPLAIN using mixins
        plan = await cte_query.from_cte('except_orders_cte').select('*').explain().aggregate()

        # Validate the explain output
        _validate_explain_output(plan, "Async CTE EXCEPT Query")

    async def test_async_cte_explain_with_query_expression(self, async_order_fixtures):
        """
        Async version of test_cte_explain_with_query_expression.
        """
        AsyncUser, AsyncOrder, AsyncOrderItem = async_order_fixtures

        # Create test data
        user = AsyncUser(username='async_cte_explain_query_expr_user', email='async_cte_explain_query_expr@example.com', age=30)
        await user.save()

        # Create orders for the test
        order1 = AsyncOrder(user_id=user.id, order_number='ASYNC-CTE-EXPLAIN-QUERY-EXPR-001', total_amount=Decimal('100.00'), status='active')
        order2 = AsyncOrder(user_id=user.id, order_number='ASYNC-CTE-EXPLAIN-QUERY-EXPR-002', total_amount=Decimal('200.00'), status='completed')
        await order1.save()
        await order2.save()

        # Get backend and dialect
        backend = AsyncOrder.backend()
        dialect = backend.dialect

        # Create a QueryExpression directly (this implements ToSQLProtocol)
        from rhosocial.activerecord.backend.expression import statements, core
        query_expr = statements.QueryExpression(
            dialect,
            select=[core.Column(dialect, "id"), core.Column(dialect, "status"), core.Column(dialect, "total_amount")],
            from_=core.TableExpression(dialect, AsyncOrder.table_name()),
            where=statements.WhereClause(dialect, condition=core.Column(dialect, "status") == core.Literal(dialect, 'active'))
        )

        # Create a CTE that uses the QueryExpression as its source
        cte_query = AsyncCTEQuery(backend)
        cte_query.with_cte('query_expr_cte', query_expr)

        # Use the new API: specify which CTE to use and apply EXPLAIN using mixins
        plan = await cte_query.from_cte('query_expr_cte').select('*').explain().aggregate()

        # Validate the explain output
        _validate_explain_output(plan, "Async CTE QueryExpression")

    async def test_async_cte_explain_with_query_expression_as_main_query(self, async_order_fixtures):
        """
        Async version of test_cte_explain_with_query_expression_as_main_query.
        """
        AsyncUser, AsyncOrder, AsyncOrderItem = async_order_fixtures

        # Create test data
        user = AsyncUser(username='async_cte_explain_main_query_expr_user', email='async_cte_explain_main_query_expr@example.com', age=35)
        await user.save()

        # Create orders for the test
        order1 = AsyncOrder(user_id=user.id, order_number='ASYNC-CTE-EXPLAIN-MAIN-QUERY-EXPR-001', total_amount=Decimal('150.00'), status='active')
        order2 = AsyncOrder(user_id=user.id, order_number='ASYNC-CTE-EXPLAIN-MAIN-QUERY-EXPR-002', total_amount=Decimal('250.00'), status='pending')
        await order1.save()
        await order2.save()

        # Get backend and dialect
        backend = AsyncOrder.backend()
        dialect = backend.dialect

        # Create a CTE with a simple query
        cte_query = AsyncCTEQuery(backend)
        cte_query.with_cte('simple_orders_cte', (f"SELECT id, status, total_amount FROM {AsyncOrder.table_name()} WHERE status IN (?, ?)", ('active', 'pending')))

        # Use the new API: specify which CTE to use and apply EXPLAIN using mixins
        plan = await cte_query.from_cte('simple_orders_cte').select('id', 'status', 'total_amount').where("total_amount > ?", (Decimal('100.00'),)).explain().aggregate()

        # Validate the explain output
        _validate_explain_output(plan, "Async CTE QueryExpression as Main Query")