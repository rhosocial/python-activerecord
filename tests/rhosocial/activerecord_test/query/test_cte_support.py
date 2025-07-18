# tests/rhosocial/activerecord_test/query/test_cte_support.py
"""Test CTE support and version compatibility checks in ActiveQuery."""
from unittest.mock import patch

import pytest

from src.rhosocial.activerecord.backend.errors import CTENotSupportedError
from .utils import create_order_fixtures

# Create multi-table test fixtures
order_fixtures = create_order_fixtures()


def test_cte_support_detection(order_fixtures):
    """Test CTE support detection methods"""
    User, Order, OrderItem = order_fixtures

    # Test the support detection methods - these should work without errors
    # since the SQLite backend used in tests supports CTEs
    assert Order.query().supports_cte()

    # Other support methods should also return valid booleans
    recursive_support = Order.query().supports_recursive_cte()
    assert isinstance(recursive_support, bool)

    materialized_support = Order.query().supports_materialized_hint()
    assert isinstance(materialized_support, bool)

    multiple_support = Order.query().supports_multiple_ctes()
    assert isinstance(multiple_support, bool)

    dml_support = Order.query().supports_cte_in_dml()
    assert isinstance(dml_support, bool)


@patch('src.rhosocial.activerecord.query.cte.CTEQueryMixin._check_cte_support')
def test_cte_not_supported_error(mock_check, order_fixtures):
    """Test error handling when CTEs are not supported"""
    User, Order, OrderItem = order_fixtures

    # Make _check_cte_support raise CTENotSupportedError
    mock_check.side_effect = CTENotSupportedError("CTEs are not supported")

    # Attempt to use CTE should raise the error
    with pytest.raises(CTENotSupportedError) as excinfo:
        Order.query().with_cte(
            'test_cte',
            "SELECT * FROM orders"
        )

    assert "CTEs are not supported" in str(excinfo.value)


@patch('src.rhosocial.activerecord.query.cte.CTEQueryMixin.supports_recursive_cte')
def test_recursive_cte_not_supported(mock_supports_recursive, order_fixtures):
    """Test error handling when recursive CTEs are not supported"""
    User, Order, OrderItem = order_fixtures

    # Simulate lack of recursive CTE support
    mock_supports_recursive.return_value = False

    # Attempt to use recursive CTE should raise error
    with pytest.raises(CTENotSupportedError) as excinfo:
        Order.query().with_recursive_cte(
            'test_recursive',
            "SELECT * FROM orders WHERE id = 1 UNION ALL SELECT * FROM orders WHERE id > 1"
        )

    assert "Recursive CTEs are not supported" in str(excinfo.value)


@patch('src.rhosocial.activerecord.query.cte.CTEQueryMixin.supports_recursive_cte')
def test_recursive_flag_check(mock_supports_recursive, order_fixtures):
    """Test that recursive flag is properly checked"""
    User, Order, OrderItem = order_fixtures

    # Simulate lack of recursive CTE support
    mock_supports_recursive.return_value = False

    # Using with_cte with recursive=True should raise error
    with pytest.raises(CTENotSupportedError) as excinfo:
        Order.query().with_cte(
            'test_recursive',
            "SELECT * FROM orders",
            recursive=True
        )

    assert "Recursive CTEs are not supported" in str(excinfo.value)

    # Using with_cte with recursive=False should not raise error
    # We need to patch the _check_cte_support method to avoid actual checks
    with patch('src.rhosocial.activerecord.query.cte.CTEQueryMixin._check_cte_support'):
        # This should not raise an error
        Order.query().with_cte(
            'test_non_recursive',
            "SELECT * FROM orders",
            recursive=False
        )


@patch('src.rhosocial.activerecord.query.cte.CTEQueryMixin.supports_materialized_hint')
def test_materialized_hint_check(mock_supports_materialized, order_fixtures):
    """Test handling of materialized hints when not supported"""
    User, Order, OrderItem = order_fixtures

    # Simulate lack of materialized hint support
    mock_supports_materialized.return_value = False

    # Using materialized hint when not supported should log warning but not error
    with patch('src.rhosocial.activerecord.query.cte.CTEQueryMixin._log') as mock_log:
        with patch('src.rhosocial.activerecord.query.cte.CTEQueryMixin._check_cte_support'):
            query = Order.query().with_cte(
                'test_materialized',
                "SELECT * FROM orders",
                materialized=True
            )

            # Verify warning was logged
            any_warning_logged = False
            for call in mock_log.call_args_list:
                call_args, call_kwargs = call
                if call_args and len(call_args) >= 2:
                    if "not supported" in str(call_args[1]) and "ignored" in str(call_args[1]):
                        any_warning_logged = True
                        break

            assert any_warning_logged, "No warning was logged for unsupported materialized hint"

            # Verify the materialized hint was set to None
            assert query._ctes['test_materialized']['materialized'] is None


@patch('src.rhosocial.activerecord.query.cte.CTEQueryMixin.supports_multiple_ctes')
def test_multiple_ctes_check(mock_supports_multiple, order_fixtures):
    """Test error handling when multiple CTEs are not supported"""
    User, Order, OrderItem = order_fixtures

    # Simulate lack of multiple CTE support
    mock_supports_multiple.return_value = False

    # The first CTE should work fine with proper mocking
    with patch('src.rhosocial.activerecord.query.cte.CTEQueryMixin._check_cte_support'):
        query = Order.query().with_cte(
            'first_cte',
            "SELECT * FROM orders"
        )

    # Adding a second CTE should raise error
    with pytest.raises(CTENotSupportedError) as excinfo:
        query.with_cte(
            'second_cte',
            "SELECT * FROM orders"
        )

    assert "Multiple CTEs are not supported" in str(excinfo.value)


def test_undefined_cte_error(order_fixtures):
    """Test error handling when attempting to use undefined CTE"""
    User, Order, OrderItem = order_fixtures

    # Attempt to use CTE that wasn't defined
    with pytest.raises(ValueError) as excinfo:
        Order.query().from_cte('undefined_cte')

    assert "has not been defined" in str(excinfo.value)
    assert "Use with_cte() first" in str(excinfo.value)


def test_cte_build_clause(order_fixtures):
    """Test the _build_cte_clause internal method"""
    User, Order, OrderItem = order_fixtures

    # Initialize a query with a CTE
    query = Order.query().with_cte(
        'test_cte',
        "SELECT * FROM orders"
    )

    # Call the internal _build_cte_clause method
    clause, params = query._build_cte_clause()

    # Verify the clause contains the CTE name and basic WITH syntax
    assert clause is not None
    assert "WITH" in clause
    assert "test_cte" in clause
    assert "SELECT * FROM orders" in clause

    # Verify parameters
    assert isinstance(params, list)
    assert len(params) == 0  # No parameters in this example

    # Test with parameters
    subquery = Order.query().where('id > ?', (5,))
    query = Order.query().with_cte(
        'param_cte',
        subquery
    )

    clause, params = query._build_cte_clause()
    assert clause is not None
    assert "WITH" in clause
    assert "param_cte" in clause
    assert len(params) == 1
    assert params[0] == 5


@patch('src.rhosocial.activerecord.query.cte.CTEQueryMixin.supports_recursive_cte')
def test_build_clause_recursive_check(mock_supports_recursive, order_fixtures):
    """Test _build_cte_clause checks recursive support before building SQL"""
    User, Order, OrderItem = order_fixtures

    # First allow recursive CTEs to create the query
    mock_supports_recursive.return_value = True

    query = Order.query().with_cte(
        'test_recursive',
        "SELECT * FROM orders",
        recursive=True
    )

    # Now simulate recursive CTEs not being supported when building
    mock_supports_recursive.return_value = False

    # Building the clause should raise error due to lack of recursive support
    with pytest.raises(CTENotSupportedError) as excinfo:
        query._build_cte_clause()

    assert "Recursive CTEs are not supported" in str(excinfo.value)
