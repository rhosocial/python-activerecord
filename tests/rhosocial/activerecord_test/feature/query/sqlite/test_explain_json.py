# tests/rhosocial/activerecord_test/feature/query/sqlite/test_explain_json.py
"""Test explain functionality with JSON expressions for SQLite."""
import json

import pytest

from rhosocial.activerecord.testsuite.feature.query.conftest import (
    order_fixtures,
    blog_fixtures,
    json_user_fixture,
    tree_fixtures,
    extended_order_fixtures,
    combined_fixtures,
)

# Create tuple-style access for compatibility with existing tests
@pytest.fixture
def json_fixtures(json_user_fixture):
    """Wrapper to provide json_user_fixture as a tuple for existing tests."""
    return (json_user_fixture,)


def test_explain_json_expressions(json_fixtures):
    """Test explain functionality with JSON expressions."""
    User = json_fixtures[0]

    # Create test user with JSON data
    user = User(
        username='test_user',
        email='test@example.com',
        settings=json.dumps({
            "theme": "dark",
            "notifications": {"email": True}
        })
    )
    user.save()

    try:
        # Test explain with JSON extract
        query = User.query()
        query.json_expr('settings', '$.theme', alias='theme')

        plan = query.explain().aggregate()
        assert isinstance(plan, str)
        assert any(op in plan for op in ['Trace', 'Goto', 'OpenRead', 'Function'])

        # Test explain with JSON in WHERE clause
        query = User.query()
        query.where("json_extract(settings, '$.theme') = 'dark'")

        plan = query.explain().all()
        assert isinstance(plan, str)
        assert any(op in plan for op in ['Trace', 'Goto', 'OpenRead', 'Function', 'Compare'])

        # Test explain with JSON in GROUP BY
        query = User.query()
        query.select("json_extract(settings, '$.theme') as theme")
        query.count("*", "user_count")
        query.group_by("json_extract(settings, '$.theme')")

        plan = query.explain().aggregate()
        assert isinstance(plan, str)
        assert any(op in plan for op in ['Trace', 'Goto', 'OpenRead', 'Function', 'Aggregate'])
    except Exception as e:
        if 'no such function' in str(e).lower():
            pytest.skip("SQLite installation doesn't have required JSON functions")
        raise


def test_explain_json_text(json_fixtures):
    """Test explain functionality with JSON text extraction."""
    User = json_fixtures[0]

    # Create test user with JSON data
    user = User(
        username='text_user',
        email='text@example.com',
        settings=json.dumps({
            "theme": "light",
            "level": 5
        })
    )
    user.save()

    try:
        # Test explain with JSON text extraction
        query = User.query()
        query.json_text('settings', '$.theme', alias='theme_text')

        plan = query.explain().aggregate()
        assert isinstance(plan, str)
        assert any(op in plan for op in ['Trace', 'Goto', 'OpenRead', 'Function'])
    except Exception as e:
        if 'no such function' in str(e).lower():
            pytest.skip("SQLite installation doesn't have required JSON functions")
        raise


def test_explain_json_contains(json_fixtures):
    """Test explain functionality with JSON contains operation."""
    User = json_fixtures[0]

    # Create test user with JSON array data
    user = User(
        username='contains_user',
        email='contains@example.com',
        settings=json.dumps({
            "roles": ["admin", "editor"]
        })
    )
    user.save()

    try:
        # Test explain with JSON contains
        query = User.query()
        query.json_contains('settings', '$.roles', 'admin', alias='is_admin')

        plan = query.explain().aggregate()
        assert isinstance(plan, str)
        assert any(op in plan for op in ['Trace', 'Goto', 'OpenRead', 'Function'])
    except Exception as e:
        if 'no such function' in str(e).lower():
            pytest.skip("SQLite installation doesn't have required JSON functions")
        raise


def test_explain_json_exists(json_fixtures):
    """Test explain functionality with JSON exists operation."""
    User = json_fixtures[0]

    # Create test users with varying JSON data
    user1 = User(
        username='complete_user',
        email='complete@example.com',
        settings=json.dumps({
            "profile": {
                "address": "123 Main St"
            }
        })
    )
    user1.save()

    user2 = User(
        username='partial_user',
        email='partial@example.com',
        settings=json.dumps({
            "profile": {}
        })
    )
    user2.save()

    try:
        # Test explain with JSON exists
        query = User.query()
        query.json_exists('settings', '$.profile.address', alias='has_address')

        plan = query.explain().aggregate()
        assert isinstance(plan, str)
        assert any(op in plan for op in ['Trace', 'Goto', 'OpenRead', 'Function'])
    except Exception as e:
        if 'no such function' in str(e).lower():
            pytest.skip("SQLite installation doesn't have required JSON functions")
        raise


def test_explain_json_type(json_fixtures):
    """Test explain functionality with JSON type operation."""
    User = json_fixtures[0]

    # Create test user with various JSON types
    user = User(
        username='type_user',
        email='type@example.com',
        settings=json.dumps({
            "number": 42,
            "string": "hello",
            "array": [1, 2, 3],
            "object": {"key": "value"}
        })
    )
    user.save()

    try:
        # Test explain with JSON type
        query = User.query()
        query.json_type('settings', '$.number', alias='number_type')
        query.json_type('settings', '$.string', alias='string_type')
        query.json_type('settings', '$.array', alias='array_type')
        query.json_type('settings', '$.object', alias='object_type')

        plan = query.explain().aggregate()
        assert isinstance(plan, str)
        assert any(op in plan for op in ['Trace', 'Goto', 'OpenRead', 'Function'])
    except Exception as e:
        if 'no such function' in str(e).lower():
            pytest.skip("SQLite installation doesn't have required JSON functions")
        raise


def test_explain_json_modification(json_fixtures):
    """Test explain functionality with JSON modification operations."""
    User = json_fixtures[0]

    # Create test user with JSON data to modify
    user = User(
        username='modify_user',
        email='modify@example.com',
        settings=json.dumps({
            "existing": "value",
            "nested": {
                "existing": "nested_value"
            }
        })
    )
    user.save()

    try:
        # Test explain with JSON set
        query = User.query()
        query.json_set('settings', '$.new_key', 'new_value', alias='set_result')
        plan = query.explain().aggregate()
        assert isinstance(plan, str)
        assert any(op in plan for op in ['Trace', 'Goto', 'OpenRead', 'Function'])

        # Test explain with JSON insert
        query = User.query()
        query.json_insert('settings', '$.insert_key', 'inserted', alias='insert_result')
        plan = query.explain().aggregate()
        assert isinstance(plan, str)
        assert any(op in plan for op in ['Trace', 'Goto', 'OpenRead', 'Function'])

        # Test explain with JSON replace
        query = User.query()
        query.json_replace('settings', '$.existing', 'replaced', alias='replace_result')
        plan = query.explain().aggregate()
        assert isinstance(plan, str)
        assert any(op in plan for op in ['Trace', 'Goto', 'OpenRead', 'Function'])

        # Test explain with JSON remove
        query = User.query()
        query.json_remove('settings', '$.existing', alias='remove_result')
        plan = query.explain().aggregate()
        assert isinstance(plan, str)
        assert any(op in plan for op in ['Trace', 'Goto', 'OpenRead', 'Function'])
    except Exception as e:
        if 'no such function' in str(e).lower():
            pytest.skip("SQLite installation doesn't have required JSON functions")
        raise
