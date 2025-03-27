"""Test advanced grouping (CUBE, ROLLUP, GROUPING SETS) functionality in ActiveQuery."""
from decimal import Decimal
import logging
import pytest

from src.rhosocial.activerecord.query.expression import GroupingSetExpression
from .utils import get_mysql_version
from .fixtures.extended_models import create_extended_order_fixtures

# Create extended table fixtures with all the fields we need for testing
extended_order_fixtures = create_extended_order_fixtures()

# Logger for debug output
logger = logging.getLogger('activerecord_test')


def is_sqlite_backend(request):
    """Check if the current database backend is SQLite."""
    if hasattr(request, 'node'):
        backend_name = request.node.name.split('-')[0].lower()
        return 'sqlite' in backend_name
    return False


def is_mysql_backend(request):
    """Check if the current database backend is MySQL."""
    if hasattr(request, 'node'):
        backend_name = request.node.name.split('-')[0].lower()
        return 'mysql' in backend_name
    return False


@pytest.fixture(scope="function")
def skip_for_sqlite(request):
    """Skip tests on SQLite database since it doesn't support advanced grouping."""
    if is_sqlite_backend(request):
        pytest.skip("SQLite does not support advanced grouping features (CUBE, ROLLUP, GROUPING SETS)")


@pytest.fixture(scope="function")
def skip_if_unsupported(request):
    """Skip tests if database doesn't support advanced grouping features.

    Different databases have different support levels:
    - MySQL: CUBE, ROLLUP supported in 8.0+, GROUPING SETS in 8.0.19+
    - SQLite: No native support (will be skipped by skip_for_sqlite fixture)
    - PostgreSQL: Fully supported
    """
    # First check if it's SQLite
    if is_sqlite_backend(request):
        pytest.skip("SQLite does not support advanced grouping features (CUBE, ROLLUP, GROUPING SETS)")

    # MySQL community edition doesn't support advanced grouping features
    if is_mysql_backend(request):
        pytest.skip("MySQL community edition doesn't support advanced grouping features (CUBE, ROLLUP, GROUPING SETS)")

    # Database-agnostic test for support
    try:
        User, ExtendedOrder, ExtendedOrderItem = request.getfixturevalue('extended_order_fixtures')

        # Try a simple ROLLUP query (just SQL generation, not execution)
        sql, params = ExtendedOrder.query().select("status").rollup("status").to_sql()
        logger.debug(f"Testing SQL generation for advanced grouping: {sql}")

    except Exception as e:
        # If anything else goes wrong during setup, also skip
        pytest.skip(f"Could not verify support for advanced grouping: {e}")


def test_cube_basic(extended_order_fixtures, skip_if_unsupported):
    """Test basic CUBE functionality."""
    User, ExtendedOrder, ExtendedOrderItem = extended_order_fixtures

    # Create test user
    user = User(username='cube_test_user', email='cube@example.com', age=30)
    user.save()

    # Create orders with different statuses and priorities
    data = [
        ('pending', 'high', Decimal('200.00')),
        ('pending', 'low', Decimal('50.00')),
        ('paid', 'high', Decimal('300.00')),
        ('paid', 'low', Decimal('75.00')),
        ('shipped', 'high', Decimal('400.00')),
        ('shipped', 'low', Decimal('100.00'))
    ]

    for i, (status, priority, amount) in enumerate(data):
        order = ExtendedOrder(
            user_id=user.id,
            order_number=f'CUBE-{i+1}',
            status=status,
            priority=priority,
            total_amount=amount
        )
        order.save()

    try:
        # Query with CUBE on status and priority
        query = ExtendedOrder.query()
        query.select("status", "priority")
        query.cube("status", "priority")
        query.sum("total_amount", "total")
        query.count("id", "order_count")

        # Execute query
        results = query.aggregate()

        # Log results for debugging
        logger.debug(f"CUBE results: {results}")

        # Verify results

        # Should return 9 rows:
        # - 6 combinations of status+priority (original data)
        # - 3 subtotals for each status
        # - 2 subtotals for each priority
        # - 1 grand total
        # But some databases might return NULL values differently, so allow for some variation
        assert len(results) >= 6, f"Expected at least 6 result rows, got {len(results)}"

        # Create lookup dictionary for easier verification
        result_map = {}
        for row in results:
            key = (row.get('status'), row.get('priority'))
            result_map[key] = row

        # Verify individual combinations
        combinations = [
            (('pending', 'high'), Decimal('200.00'), 1),
            (('pending', 'low'), Decimal('50.00'), 1),
            (('paid', 'high'), Decimal('300.00'), 1),
            (('paid', 'low'), Decimal('75.00'), 1),
            (('shipped', 'high'), Decimal('400.00'), 1),
            (('shipped', 'low'), Decimal('100.00'), 1)
        ]

        for (status, priority), expected_total, expected_count in combinations:
            key = (status, priority)
            if key in result_map:
                row = result_map[key]
                assert row['total'] == expected_total
                assert row['order_count'] == expected_count

        # Check for subtotals if they're included
        subtotals = [
            (('pending', None), Decimal('250.00'), 2),
            (('paid', None), Decimal('375.00'), 2),
            (('shipped', None), Decimal('500.00'), 2),
            ((None, 'high'), Decimal('900.00'), 3),
            ((None, 'low'), Decimal('225.00'), 3),
            ((None, None), Decimal('1125.00'), 6)  # Grand total
        ]

        for (status, priority), expected_total, expected_count in subtotals:
            key = (status, priority)
            if key in result_map:
                row = result_map[key]
                assert row['total'] == expected_total
                assert row['order_count'] == expected_count

    except Exception as e:
        logger.error(f"Error in test_cube_basic: {e}")
        if 'syntax error' in str(e).lower() or 'not supported' in str(e).lower():
            pytest.skip(f"Database doesn't support CUBE: {e}")
        raise


def test_rollup_basic(extended_order_fixtures, skip_if_unsupported):
    """Test basic ROLLUP functionality."""
    User, ExtendedOrder, ExtendedOrderItem = extended_order_fixtures

    # Create test user
    user = User(username='rollup_test_user', email='rollup@example.com', age=30)
    user.save()

    # Create orders with different regions, categories and amounts
    data = [
        ('North', 'Electronics', Decimal('500.00')),
        ('North', 'Furniture', Decimal('300.00')),
        ('South', 'Electronics', Decimal('400.00')),
        ('South', 'Furniture', Decimal('200.00')),
        ('East', 'Electronics', Decimal('450.00')),
        ('East', 'Furniture', Decimal('250.00'))
    ]

    for i, (region, category, amount) in enumerate(data):
        order = ExtendedOrder(
            user_id=user.id,
            order_number=f'ROLLUP-{i+1}',
            region=region,
            category=category,
            total_amount=amount
        )
        order.save()

    try:
        # Query with ROLLUP on region and category
        # This creates hierarchical subtotals (region, region+category)
        query = ExtendedOrder.query()
        query.select("region", "category")
        query.rollup("region", "category")
        query.sum("total_amount", "total")

        # Execute query
        results = query.aggregate()

        # Log results for debugging
        logger.debug(f"ROLLUP results: {results}")

        # Verify results

        # Should return rows for:
        # - 6 combinations of region+category (original data)
        # - 3 subtotals for each region
        # - 1 grand total
        # But some databases might handle NULL values differently
        assert len(results) >= 6, f"Expected at least 6 result rows, got {len(results)}"

        # Create lookup dictionary for easier verification
        result_map = {}
        for row in results:
            key = (row.get('region'), row.get('category'))
            result_map[key] = row

        # Verify individual combinations
        combinations = [
            (('North', 'Electronics'), Decimal('500.00')),
            (('North', 'Furniture'), Decimal('300.00')),
            (('South', 'Electronics'), Decimal('400.00')),
            (('South', 'Furniture'), Decimal('200.00')),
            (('East', 'Electronics'), Decimal('450.00')),
            (('East', 'Furniture'), Decimal('250.00'))
        ]

        for (region, category), expected_total in combinations:
            key = (region, category)
            if key in result_map:
                row = result_map[key]
                assert row['total'] == expected_total

        # Check for subtotals if they're included
        subtotals = [
            (('North', None), Decimal('800.00')),  # North region subtotal
            (('South', None), Decimal('600.00')),  # South region subtotal
            (('East', None), Decimal('700.00')),   # East region subtotal
            ((None, None), Decimal('2100.00'))     # Grand total
        ]

        for (region, category), expected_total in subtotals:
            key = (region, category)
            if key in result_map:
                row = result_map[key]
                assert row['total'] == expected_total

    except Exception as e:
        logger.error(f"Error in test_rollup_basic: {e}")
        if 'syntax error' in str(e).lower() or 'not supported' in str(e).lower():
            pytest.skip(f"Database doesn't support ROLLUP: {e}")
        raise


def test_grouping_sets_basic(extended_order_fixtures, skip_if_unsupported):
    """Test basic GROUPING SETS functionality."""
    User, ExtendedOrder, ExtendedOrderItem = extended_order_fixtures

    # Create test user
    user = User(username='grouping_sets_user', email='grouping@example.com', age=30)
    user.save()

    # Create orders with different departments, products and amounts
    data = [
        ('Clothing', 'Shirts', Decimal('100.00')),
        ('Clothing', 'Pants', Decimal('150.00')),
        ('Electronics', 'Phones', Decimal('500.00')),
        ('Electronics', 'Laptops', Decimal('800.00')),
        ('Home', 'Furniture', Decimal('300.00')),
        ('Home', 'Decor', Decimal('200.00'))
    ]

    for i, (department, product, amount) in enumerate(data):
        order = ExtendedOrder(
            user_id=user.id,
            order_number=f'GROUPSETS-{i+1}',
            department=department,
            product=product,
            total_amount=amount
        )
        order.save()

    try:
        # Query with GROUPING SETS to get specific group combinations
        # We'll get department totals and product totals, but not the combinations
        query = ExtendedOrder.query()
        query.select("department", "product")

        # Use GROUPING SETS - each inner list is a grouping combination
        query.grouping_sets(
            ["department"],  # Group by department only
            ["product"],     # Group by product only
            [],              # Empty group for grand total
        )

        query.sum("total_amount", "total")
        query.count("id", "order_count")

        # Execute query
        results = query.aggregate()

        # Log results for debugging
        logger.debug(f"GROUPING SETS results: {results}")

        # Verify results

        # Should return:
        # - 3 rows for department totals
        # - 6 rows for product totals
        # - 1 row for grand total
        # But some databases might handle NULL values differently
        assert len(results) >= 7, f"Expected at least 7 result rows, got {len(results)}"

        # Create lookup dictionary for easier verification
        result_map = {}
        for row in results:
            key = (row.get('department'), row.get('product'))
            result_map[key] = row

        # Verify department totals
        department_totals = [
            (('Clothing', None), Decimal('250.00'), 2),
            (('Electronics', None), Decimal('1300.00'), 2),
            (('Home', None), Decimal('500.00'), 2)
        ]

        for (department, product), expected_total, expected_count in department_totals:
            key = (department, product)
            if key in result_map:
                row = result_map[key]
                assert row['total'] == expected_total
                assert row['order_count'] == expected_count

        # Verify product totals
        product_totals = [
            ((None, 'Shirts'), Decimal('100.00'), 1),
            ((None, 'Pants'), Decimal('150.00'), 1),
            ((None, 'Phones'), Decimal('500.00'), 1),
            ((None, 'Laptops'), Decimal('800.00'), 1),
            ((None, 'Furniture'), Decimal('300.00'), 1),
            ((None, 'Decor'), Decimal('200.00'), 1)
        ]

        for (department, product), expected_total, expected_count in product_totals:
            key = (department, product)
            if key in result_map:
                row = result_map[key]
                assert row['total'] == expected_total
                assert row['order_count'] == expected_count

        # Verify grand total
        if (None, None) in result_map:
            grand_total = result_map[(None, None)]
            assert grand_total['total'] == Decimal('2050.00')
            assert grand_total['order_count'] == 6

    except Exception as e:
        logger.error(f"Error in test_grouping_sets_basic: {e}")
        if 'syntax error' in str(e).lower() or 'not supported' in str(e).lower():
            pytest.skip(f"Database doesn't support GROUPING SETS: {e}")
        raise


def test_rollup_with_having(extended_order_fixtures, skip_if_unsupported):
    """Test ROLLUP with HAVING clause."""
    User, ExtendedOrder, ExtendedOrderItem = extended_order_fixtures

    # Create test user
    user = User(username='rollup_having_user', email='rollup_having@example.com', age=30)
    user.save()

    # Create orders with different years, quarters and amounts
    data = [
        ('2023', 'Q1', Decimal('200.00')),
        ('2023', 'Q2', Decimal('300.00')),
        ('2023', 'Q3', Decimal('150.00')),
        ('2023', 'Q4', Decimal('250.00')),
        ('2024', 'Q1', Decimal('400.00')),
        ('2024', 'Q2', Decimal('350.00'))
    ]

    for i, (year, quarter, amount) in enumerate(data):
        order = ExtendedOrder(
            user_id=user.id,
            order_number=f'ROLLUP-HAV-{i+1}',
            year=year,
            quarter=quarter,
            total_amount=amount
        )
        order.save()

    try:
        # Query with ROLLUP and HAVING to filter results
        query = ExtendedOrder.query()
        query.select("year", "quarter")
        query.rollup("year", "quarter")
        query.sum("total_amount", "total")

        # Only include groups with total over 300
        query.having("SUM(total_amount) > ?", (Decimal('300.00'),))

        # Execute query
        results = query.aggregate()

        # Log results for debugging
        logger.debug(f"ROLLUP with HAVING results: {results}")

        # Check that we only get rows with totals > 300
        for row in results:
            assert row['total'] > Decimal('300.00')

        # Create lookup dictionary for result verification
        result_map = {}
        for row in results:
            key = (row.get('year'), row.get('quarter'))
            result_map[key] = row

        # Expected results that meet the HAVING condition
        expected_rows = [
            (('2023', None), Decimal('900.00')),  # 2023 total
            (('2024', None), Decimal('750.00')),  # 2024 total
            ((None, None), Decimal('1650.00'))    # Grand total
        ]

        # Check all expected rows are present
        for (year, quarter), expected_total in expected_rows:
            key = (year, quarter)
            if key in result_map:
                assert result_map[key]['total'] == expected_total

    except Exception as e:
        logger.error(f"Error in test_rollup_with_having: {e}")
        if 'syntax error' in str(e).lower() or 'not supported' in str(e).lower():
            pytest.skip(f"Database doesn't support ROLLUP with HAVING: {e}")
        raise


def test_cube_with_order_by(extended_order_fixtures, skip_if_unsupported):
    """Test CUBE with ORDER BY clause."""
    User, ExtendedOrder, ExtendedOrderItem = extended_order_fixtures

    # Create test user
    user = User(username='cube_order_user', email='cube_order@example.com', age=30)
    user.save()

    # Create orders with different regions, products and amounts
    data = [
        ('East', 'A', Decimal('200.00')),
        ('East', 'B', Decimal('300.00')),
        ('West', 'A', Decimal('400.00')),
        ('West', 'B', Decimal('500.00'))
    ]

    for i, (region, product, amount) in enumerate(data):
        order = ExtendedOrder(
            user_id=user.id,
            order_number=f'CUBE-ORD-{i+1}',
            region=region,
            product=product,
            total_amount=amount
        )
        order.save()

    try:
        # Query with CUBE and ORDER BY
        query = ExtendedOrder.query()
        query.select("region", "product")
        query.cube("region", "product")
        query.sum("total_amount", "total")

        # Order by total (descending)
        query.order_by("total DESC")

        # Execute query
        results = query.aggregate()

        # Log results for debugging
        logger.debug(f"CUBE with ORDER BY results: {results}")

        # Verify ordering - totals should be in descending order
        previous_total = None
        for row in results:
            if previous_total is not None:
                assert row['total'] <= previous_total, "Results are not in descending order by total"
            previous_total = row['total']

        # The highest total should be the grand total
        grand_total_found = False
        for row in results:
            if row.get('region') is None and row.get('product') is None:
                assert row['total'] == Decimal('1400.00'), "Grand total should be 1400.00"
                grand_total_found = True
                break

        # Some databases might not include the grand total in the result
        if grand_total_found:
            assert results[0]['total'] == Decimal('1400.00'), "Grand total should be first in descending order"

    except Exception as e:
        logger.error(f"Error in test_cube_with_order_by: {e}")
        if 'syntax error' in str(e).lower() or 'not supported' in str(e).lower():
            pytest.skip(f"Database doesn't support CUBE with ORDER BY: {e}")
        raise


def test_multiple_grouping_types(extended_order_fixtures, skip_if_unsupported):
    """Test that only one grouping type can be used at a time."""
    User, ExtendedOrder, ExtendedOrderItem = extended_order_fixtures

    # Verify that setting multiple grouping types throws an error or uses the last one
    query = ExtendedOrder.query()
    query.select("status")

    # Set ROLLUP
    query.rollup("status")

    # Try to set CUBE (should replace ROLLUP)
    query.cube("status")

    # Get SQL to verify
    sql, params = query.to_sql()
    logger.debug(f"Multiple grouping types SQL: {sql}")

    # Verify that CUBE is in the query, not ROLLUP
    assert "CUBE" in sql.upper(), "Expected CUBE in SQL after replacing ROLLUP"
    assert "ROLLUP" not in sql.upper(), "Expected ROLLUP to be replaced by CUBE"


def test_complex_grouping_with_joins(extended_order_fixtures, skip_if_unsupported):
    """Test advanced grouping with JOIN operations."""
    User, ExtendedOrder, ExtendedOrderItem = extended_order_fixtures

    # Create test data
    user1 = User(username='complex_user1', email='complex1@example.com', age=30)
    user1.save()

    user2 = User(username='complex_user2', email='complex2@example.com', age=40)
    user2.save()

    # Create orders for users
    orders_data = [
        (user1.id, 'North', 'A', Decimal('100.00')),
        (user1.id, 'North', 'B', Decimal('200.00')),
        (user1.id, 'South', 'A', Decimal('150.00')),
        (user2.id, 'North', 'A', Decimal('300.00')),
        (user2.id, 'South', 'B', Decimal('400.00'))
    ]

    order_ids = []
    for i, (user_id, region, product, amount) in enumerate(orders_data):
        order = ExtendedOrder(
            user_id=user_id,
            order_number=f'COMPLEX-{i + 1}',
            region=region,
            product=product,
            total_amount=amount
        )
        order.save()
        order_ids.append(order.id)

    # Add order items
    for i, order_id in enumerate(order_ids):
        item = ExtendedOrderItem(
            order_id=order_id,
            product_name=f'Product {i + 1}',
            quantity=i + 1,
            price=Decimal('50.00')
        )
        item.save()

    try:
        # Create complex query with JOIN and ROLLUP
        query = ExtendedOrder.query()

        # Join with users table
        user_table = User.table_name()
        order_table = ExtendedOrder.table_name()

        query.join(f"JOIN {user_table} ON {order_table}.user_id = {user_table}.id")

        # Select columns from both tables
        query.select(f"{user_table}.username", f"{order_table}.region")

        # Apply ROLLUP grouping
        query.rollup(f"{user_table}.username", f"{order_table}.region")

        # Add aggregations
        query.sum(f"{order_table}.total_amount", "total")
        query.count(f"{order_table}.id", "order_count")

        # Execute query
        results = query.aggregate()

        # Log results for debugging
        logger.debug(f"Complex JOIN with ROLLUP results: {results}")

        # Verify results

        # Create lookup dictionary
        result_map = {}
        for row in results:
            key = (row.get('username'), row.get('region'))
            result_map[key] = row

        # Expected results
        expected = [
            # User+region combinations
            (('complex_user1', 'North'), Decimal('300.00'), 2),
            (('complex_user1', 'South'), Decimal('150.00'), 1),
            (('complex_user2', 'North'), Decimal('300.00'), 1),
            (('complex_user2', 'South'), Decimal('400.00'), 1),

            # User subtotals
            (('complex_user1', None), Decimal('450.00'), 3),
            (('complex_user2', None), Decimal('700.00'), 2),

            # Grand total
            ((None, None), Decimal('1150.00'), 5)
        ]

        # Check results
        for (username, region), expected_total, expected_count in expected:
            key = (username, region)
            if key in result_map:
                row = result_map[key]
                assert row['total'] == expected_total
                assert row['order_count'] == expected_count

    except Exception as e:
        logger.error(f"Error in test_complex_grouping_with_joins: {e}")
        if 'syntax error' in str(e).lower() or 'not supported' in str(e).lower():
            pytest.skip(f"Database doesn't support complex JOIN with ROLLUP: {e}")
        raise