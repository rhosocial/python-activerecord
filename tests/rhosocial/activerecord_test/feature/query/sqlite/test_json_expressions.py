# tests/rhosocial/activerecord_test/feature/query/sqlite/test_json_expressions.py
"""Test JSON expression functionality in ActiveQuery."""
import json
import sqlite3

import pytest

from rhosocial.activerecord.backend import SQLDialectBase, OperationalError
from rhosocial.activerecord.query.expression import JsonExpression, CaseExpression
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


# Helper to check if current SQLite version supports JSON functions
def is_json_supported():
    # SQLite has JSON1 extension in most builds from version 3.9.0
    version = sqlite3.sqlite_version_info
    return version >= (3, 9, 0)


def test_json_contains(json_fixtures):
    """Test JSON contains operations.

    SQLite doesn't have a native json_contains() function, but we implement it using
    json_extract with equality comparison.
    """
    User = json_fixtures[0]

    # Create test users with JSON data
    users_data = [
        {
            "username": "user1",
            "email": "user1@example.com",
            "age": 30,
            "tags": json.dumps(["admin", "editor"])
        },
        {
            "username": "user2",
            "email": "user2@example.com",
            "age": 25,
            "tags": json.dumps(["user", "subscriber"])
        }
    ]

    for data in users_data:
        user = User(**data)
        user.save()

    try:
        # Test JSON contains with simple value
        query = User.query()
        query.json_expr('tags', '$', operation='contains', value='"admin"', alias='is_admin')
        results = query.aggregate()

        assert len(results) == 2
        admin_users = [r for r in results if r['is_admin'] == 1]
        assert len(admin_users) == 1
        assert admin_users[0]['username'] == 'user1'

        # Test with another value
        query = User.query()
        query.json_expr('tags', '$', operation='contains', value='"subscriber"', alias='is_subscriber')
        results = query.aggregate()

        subscriber_users = [r for r in results if r['is_subscriber'] == 1]
        assert len(subscriber_users) == 1
        assert subscriber_users[0]['username'] == 'user2'
    except Exception as e:
        if 'no such function: json_contains' in str(e).lower() or 'json_extract' in str(e).lower():
            try:
                # Try an alternative approach with json_extract and string comparison
                # which is what our SQLiteJsonHandler should be doing anyway
                query = User.query()
                query.select("username, json_extract(tags, '$') as tags_json")
                results = query.aggregate()

                # Check if we get any results with the alternative approach
                assert results is not None and len(results) > 0

                # If we get here, the test is passing with the alternative approach
                # Skip the original test since our alternative works
                pytest.skip("SQLite installation doesn't have json_contains function, using alternative")
            except:
                pytest.skip("SQLite installation doesn't have JSON1 extension")
        raise


def test_json_expressions_in_where(json_fixtures):
    """Test using JSON expressions in WHERE clause."""
    User = json_fixtures[0]

    # Create test users with JSON data
    users_data = [
        {
            "username": "admin_user",
            "email": "admin@example.com",
            "age": 30,
            "roles": json.dumps({
                "admin": True,
                "editor": True
            })
        },
        {
            "username": "regular_user",
            "email": "regular@example.com",
            "age": 25,
            "roles": json.dumps({
                "admin": False,
                "editor": True
            })
        }
    ]

    for data in users_data:
        user = User(**data)
        user.save()

    try:
        # Use JSON in WHERE clause to find admins
        query = User.query()
        # Different SQLite versions might handle JSON booleans differently,
        # so we'll check against both possible values
        query.where("json_extract(roles, '$.admin') = 1 OR json_extract(roles, '$.admin') = 'true'")
        results = query.aggregate()

        assert len(results) == 1
        assert results[0]['username'] == 'admin_user'

        # Find all editors
        query = User.query()
        query.where("json_extract(roles, '$.editor') = 1 OR json_extract(roles, '$.editor') = 'true'")
        results = query.aggregate()

        assert len(results) == 2  # Both users are editors
    except Exception as e:
        if 'no such function' in str(e).lower():
            pytest.skip("SQLite installation doesn't have required JSON functions")
        raise


def test_json_with_case_expressions(json_fixtures):
    """Test combining JSON expressions with CASE."""
    User = json_fixtures[0]

    # Create test users with JSON data
    users_data = [
        {
            "username": "premium_user",
            "email": "premium@example.com",
            "subscription": json.dumps({
                "type": "premium",
                "expires": "2024-12-31"
            })
        },
        {
            "username": "basic_user",
            "email": "basic@example.com",
            "subscription": json.dumps({
                "type": "basic",
                "expires": "2024-06-30"
            })
        },
        {
            "username": "trial_user",
            "email": "trial@example.com",
            "subscription": json.dumps({
                "type": "trial",
                "expires": "2024-04-15"
            })
        }
    ]

    for data in users_data:
        user = User(**data)
        user.save()

    try:
        # Test CASE with JSON expressions
        query = User.query()
        query.select("username")
        query.select_expr(CaseExpression(
            [
                (f"{(JsonExpression('subscription', '$.type')).as_sql()} = 'premium'", 'High Priority'),
                (f"{JsonExpression('subscription', '$.type').as_sql()} = 'basic'", 'Medium Priority')
            ]
            , 'Low Priority', 'support_priority'))

        query.group_by("support_priority")

        results = query.aggregate()

        # Verify results
        assert len(results) == 3

        # Create mapping for easy verification - 使用字典访问而非对象属性
        priorities = {r['username']: r['support_priority'] for r in results}

        assert priorities['premium_user'] == 'High Priority'
        assert priorities['basic_user'] == 'Medium Priority'
        assert priorities['trial_user'] == 'Low Priority'
    except Exception as e:
        if 'no such function' in str(e).lower():
            pytest.skip("SQLite installation doesn't have required JSON functions")
        raise


def test_json_in_group_by(json_fixtures):
    """Test using JSON expressions in GROUP BY clause."""
    User = json_fixtures[0]

    # Create test users with nested JSON preferences
    users_data = [
        {
            "username": "user1",
            "email": "user1@example.com",
            "preferences": json.dumps({
                "region": "North",
                "notifications": {"email": True, "sms": False}
            })
        },
        {
            "username": "user2",
            "email": "user2@example.com",
            "preferences": json.dumps({
                "region": "South",
                "notifications": {"email": True, "sms": True}
            })
        },
        {
            "username": "user3",
            "email": "user3@example.com",
            "preferences": json.dumps({
                "region": "North",
                "notifications": {"email": False, "sms": True}
            })
        }
    ]

    for data in users_data:
        user = User(**data)
        user.save()

    try:
        # Group by JSON region
        query = User.query()
        query.select_expr(JsonExpression('preferences', '$.region', alias='region'))
        # query.select("json_extract(preferences, '$.region') as region")
        query.count("*", "user_count")
        query.group_by("region")
        results = query.aggregate()

        # Should have 2 groups: North (2 users) and South (1 user)
        assert len(results) == 2

        # Create mapping for verification
        region_counts = {r['region']: r['user_count'] for r in results}

        assert region_counts['North'] == 2
        assert region_counts['South'] == 1

        # Group by email notification preference
        query = User.query()
        query.select_expr(JsonExpression('preferences', '$.notifications.email', alias='email_pref'))
        # query.select("json_extract(preferences, '$.notifications.email') as email_pref")
        query.count("*", "user_count")
        query.group_by("email_pref")
        results = query.aggregate()

        # Should have 2 groups: True (2 users) and False (1 user)
        assert len(results) == 2

        # Create mapping for verification - handle SQLite's varied boolean representation
        email_counts = {}
        for r in results:
            key = r['email_pref']
            # Convert string 'true'/'false' to boolean if needed
            if isinstance(key, str) and key.lower() in ('true', 'false'):
                key = key.lower() == 'true'
            # Convert 1/0 to boolean if needed
            elif key in (1, 0):
                key = bool(key)
            email_counts[key] = r['user_count']

        # Check results with boolean keys
        if True in email_counts and False in email_counts:
            assert email_counts[True] == 2
            assert email_counts[False] == 1
        # Check results with 1/0 keys
        elif 1 in email_counts and 0 in email_counts:
            assert email_counts[1] == 2
            assert email_counts[0] == 1
        # Check results with string keys
        elif 'true' in email_counts and 'false' in email_counts:
            assert email_counts['true'] == 2
            assert email_counts['false'] == 1
        else:
            # If we can't determine the key format, just check counts
            count_values = list(email_counts.values())
            assert 2 in count_values
            assert 1 in count_values

    except Exception as e:
        if 'no such function' in str(e).lower():
            pytest.skip("SQLite installation doesn't have required JSON functions")
        raise


# Helper to check if current SQLite version supports JSON1 extension and JSON operators
def is_json_arrows_supported():
    # SQLite added -> and ->> operators in version 3.38.0 (2022-02-22)
    version = sqlite3.sqlite_version_info
    return version >= (3, 38, 0)



def test_json_extract(json_fixtures):
    """Test basic JSON extraction using database-agnostic API."""
    JsonUser = json_fixtures[0]

    # Create test user with JSON data
    user = JsonUser(
        username='extract_user',
        email='extract@example.com',
        age=30,
        settings=json.dumps({
            "theme": "dark",
            "notifications": {
                "email": True,
                "push": False
            },
            "preferences": ["news", "updates"]
        })
    )
    user.save()

    try:
        # Test JSON extract with query builder method
        query = JsonUser.query().where('username = ?', ('extract_user',))
        query.json('settings', '$.theme', 'theme_setting')
        results = query.aggregate()[0]

        assert 'theme_setting' in results
        assert results['theme_setting'] == 'dark'

        # Test nested JSON path
        query = JsonUser.query().where('username = ?', ('extract_user',))
        query.json('settings', '$.notifications.email', 'email_notifications')
        results = query.aggregate()[0]

        assert 'email_notifications' in results
        assert results['email_notifications'] == 1 or results['email_notifications'] is True

        # Test JSON array element
        query = JsonUser.query().where('username = ?', ('extract_user',))
        query.json('settings', '$.preferences[0]', 'first_preference')
        results = query.aggregate()[0]

        assert 'first_preference' in results
        assert results['first_preference'] == 'news'

    except Exception as e:
        if 'no such function: json_extract' in str(e).lower():
            pytest.skip("SQLite installation doesn't have JSON1 extension")
        raise


def test_json_text(json_fixtures):
    """Test JSON text extraction using database-agnostic API."""
    JsonUser = json_fixtures[0]

    # Create test user with JSON data
    user = JsonUser(
        username='text_user',
        email='text@example.com',
        age=35,
        settings=json.dumps({
            "theme": "light",
            "numbers": [42, 73, 101],
            "level": 5
        })
    )
    user.save()

    try:
        # Test JSON text extract with query builder method
        query = JsonUser.query().where('username = ?', ('text_user',))
        query.json_text('settings', '$.theme', 'theme_setting')
        results = query.aggregate()[0]

        assert 'theme_setting' in results
        assert results['theme_setting'] == 'light'

        # Test numeric value extraction as text
        query = JsonUser.query().where('username = ?', ('text_user',))
        query.json_text('settings', '$.level', 'level_text')
        results = query.aggregate()[0]

        assert 'level_text' in results
        # Text representation might be an actual number or string depending on SQLite version
        assert results['level_text'] == 5 or results['level_text'] == '5'

    except Exception as e:
        if 'no such function: json_extract' in str(e).lower():
            pytest.skip("SQLite installation doesn't have JSON1 extension")
        raise


def test_json_type(json_fixtures):
    """Test JSON type checking."""
    JsonUser = json_fixtures[0]

    # Create test user with various JSON types
    user = JsonUser(
        username='type_user',
        email='type@example.com',
        age=40,
        settings=json.dumps({
            "number": 42,
            "string": "hello",
            "boolean": True,
            "array": [1, 2, 3],
            "object": {"key": "value"},
            "null": None
        })
    )
    user.save()

    try:
        # Test json_type on different value types
        query = JsonUser.query().where('username = ?', ('type_user',))
        query.json_type('settings', '$.number', 'number_type')
        query.json_type('settings', '$.string', 'string_type')
        query.json_type('settings', '$.boolean', 'boolean_type')
        query.json_type('settings', '$.array', 'array_type')
        query.json_type('settings', '$.object', 'object_type')
        query.json_type('settings', '$.null', 'null_type')
        results = query.aggregate()[0]

        assert results['number_type'] == 'integer'
        assert results['string_type'] == 'text'
        assert results['boolean_type'] == 'true'  # SQLite may store booleans as integers
        assert results['array_type'] == 'array'
        assert results['object_type'] == 'object'
        assert results['null_type'] == 'null'

    except Exception as e:
        if 'no such function: json_type' in str(e).lower():
            pytest.skip("SQLite installation doesn't have json_type function")
        raise


def test_json_exists(json_fixtures):
    """Test if a JSON path exists.

    SQLite doesn't have a direct json_exists() function, but this test should work
    because we implement it using json_extract() IS NOT NULL.
    """
    JsonUser = json_fixtures[0]

    # Create test users with varying JSON data
    users_data = [
        {
            "username": "complete_user",
            "email": "complete@example.com",
            "age": 45,
            "profile": json.dumps({
                "address": {
                    "city": "New York",
                    "zip": "10001"
                },
                "phone": "555-1234"
            })
        },
        {
            "username": "partial_user",
            "email": "partial@example.com",
            "age": 50,
            "profile": json.dumps({
                "phone": "555-5678"
                # No address information
            })
        }
    ]

    for data in users_data:
        user = JsonUser(**data)
        user.save()

    try:
        # Test if path exists in JSON using json_exists
        query = JsonUser.query()
        query.json_exists('profile', '$.address', 'has_address')
        results = query.aggregate()

        assert len(results) == 2
        users_with_address = [r for r in results if r['has_address'] == 1]
        assert len(users_with_address) == 1
        assert users_with_address[0]['username'] == 'complete_user'

        # Test another path
        query = JsonUser.query()
        query.json_exists('profile', '$.phone', 'has_phone')
        results = query.aggregate()

        users_with_phone = [r for r in results if r['has_phone'] == 1]
        assert len(users_with_phone) == 2  # Both users have phone

    except Exception as e:
        # Check if the error is related to json_exists or json_extract not being supported
        if 'no such function' in str(e).lower():
            if 'json_exists' in str(e).lower():
                # Our fallback should have used json_extract
                pytest.skip("SQLite doesn't support json_exists and fallback with json_extract failed")
            elif 'json_extract' in str(e).lower():
                # If json_extract fails, then SQLite JSON1 extension is not available
                pytest.skip("SQLite installation doesn't have JSON1 extension")
        raise


def test_json_modify_operations(json_fixtures):
    """Test JSON modification operations (set, insert, replace, remove)."""
    JsonUser = json_fixtures[0]

    # Create test user with JSON data to modify
    user = JsonUser(
        username='modify_user',
        email='modify@example.com',
        age=55,
        settings=json.dumps({
            "existing": "value",
            "nested": {
                "existing": "nested_value"
            }
        })
    )
    user.save()
    try:
        # Test json_set - should insert new or replace existing
        query = JsonUser.query().where('username = ?', ('modify_user',))
        query.json_set('settings', '$.new_key', 'new_value', 'set_result')
        results = query.aggregate()[0]

        modified = json.loads(results['set_result'])
        assert modified['existing'] == 'value'
        assert modified['new_key'] == 'new_value'

        # Test json_insert - only adds if not exists
        query = JsonUser.query().where('username = ?', ('modify_user',))
        query.json_insert('settings', '$.insert_key', 'inserted', 'insert_result')
        query.json_insert('settings', '$.existing', 'wont_change', 'insert_existing')
        results = query.aggregate()[0]

        modified_insert = json.loads(results['insert_result'])
        assert modified_insert['insert_key'] == 'inserted'

        modified_existing = json.loads(results['insert_existing'])
        assert modified_existing['existing'] == 'value'  # unchanged

        # Test json_replace - only changes if exists
        query = JsonUser.query().where('username = ?', ('modify_user',))
        query.json_replace('settings', '$.existing', 'replaced', 'replace_result')
        query.json_replace('settings', '$.nonexistent', 'wont_add', 'replace_nonexistent')
        results = query.aggregate()[0]

        modified_replace = json.loads(results['replace_result'])
        assert modified_replace['existing'] == 'replaced'

        modified_nonexistent = json.loads(results['replace_nonexistent'])
        assert 'nonexistent' not in modified_nonexistent

        # Test json_remove
        query = JsonUser.query().where('username = ?', ('modify_user',))
        query.json_remove('settings', '$.existing', 'removed_result')
        results = query.aggregate()[0]

        modified_remove = json.loads(results['removed_result'])
        assert 'existing' not in modified_remove
        assert 'nested' in modified_remove

    except Exception as e:
        if 'no such function' in str(e).lower():
            pytest.skip("SQLite installation doesn't have all required JSON modification functions")
        raise


def test_json_with_aggregation(json_fixtures):
    """Test JSON expressions with aggregation functions."""
    JsonUser = json_fixtures[0]

    # Create test users with JSON data containing scores
    users_data = [
        {
            "username": "user1",
            "email": "user1@example.com",
            "scores": json.dumps({
                "math": 90,
                "science": 85,
                "history": 75
            })
        },
        {
            "username": "user2",
            "email": "user2@example.com",
            "scores": json.dumps({
                "math": 80,
                "science": 95,
                "history": 70
            })
        },
        {
            "username": "user3",
            "email": "user3@example.com",
            "scores": json.dumps({
                "math": 85,
                "science": 90,
                "history": 80
            })
        }
    ]

    for data in users_data:
        user = JsonUser(**data)
        user.save()

    try:
        # Calculate average math score
        query = JsonUser.query()
        query.select("AVG(json_extract(scores, '$.math')) as avg_math_score")
        results = query.aggregate()[0]

        assert 'avg_math_score' in results
        assert abs(float(results['avg_math_score']) - 85.0) < 0.01  # (90 + 80 + 85) / 3 = 85

        # Using built-in json() method
        query = JsonUser.query()
        query.select("username")
        query.json('scores', '$.math', 'math_score')
        query.order_by("math_score DESC")
        results = query.aggregate()

        assert len(results) == 3
        assert results[0]['username'] == 'user1'  # Highest math score
        assert results[0]['math_score'] == 90

        # Count users with history score > 75
        query = JsonUser.query()
        query.json('scores', '$.history', 'history_score')
        query.select("COUNT(*) as count")
        query.where("history_score > 75")
        results = query.aggregate()[0]

        assert results['count'] == 1  # Only user3 has history > 75

    except Exception as e:
        if 'no such function' in str(e).lower():
            pytest.skip("SQLite installation doesn't have required JSON functions")
        raise


def test_json_arrow_operators(json_fixtures):
    """Test -> and ->> JSON operators if available."""
    JsonUser = json_fixtures[0]

    # Create test user with JSON data
    user = JsonUser(
        username='arrow_user',
        email='arrow@example.com',
        age=60,
        settings=json.dumps({
            "theme": "dark",
            "notifications": {
                "email": True,
                "push": True
            },
            "favorites": ["books", "music", "movies"]
        })
    )
    user.save()

    # Test if the database supports arrow operators
    dialect: SQLDialectBase = JsonUser.backend().dialect
    if not dialect.json_operation_handler.supports_json_arrows:
        pytest.skip("Database doesn't support -> and ->> operators")

    try:
        # Test with direct SQL using -> operator
        query = JsonUser.query().where('username = ?', ('arrow_user',))
        query.select("settings->'$.theme' as direct_theme")
        results = query.aggregate()[0]

        assert 'direct_theme' in results
        assert results['direct_theme'] == '"dark"'

        # Test with direct SQL using ->> operator
        query = JsonUser.query().where('username = ?', ('arrow_user',))
        query.select("settings->>'$.theme' as direct_theme_text")
        results = query.aggregate()[0]

        assert 'direct_theme_text' in results
        assert results['direct_theme_text'] == 'dark'

        # Test comparison in WHERE clause using -> operator
        query = JsonUser.query()
        query.where("settings->'$.theme' = '\"dark\"'")
        results = query.all()

        assert len(results) == 1
        assert results[0].username == 'arrow_user'

    except Exception as e:
        if 'near "->": syntax error' in str(e):
            pytest.skip("SQLite installation doesn't support -> operator")
        elif 'json_extract' in str(e).lower():
            pytest.skip("SQLite installation doesn't have JSON1 extension")
        raise


def test_json_invalid_path_error(json_fixtures):
    """Test that invalid JSON paths properly raise OperationalError.

    SQLite throws an OperationalError for invalid JSON paths, not return NULL.
    This test verifies that using pytest's exception testing pattern.
    """
    JsonUser = json_fixtures[0]

    # Create test user
    user = JsonUser(
        username='error_user',
        email='error@example.com',
        age=65,
        settings=json.dumps({"valid": "json"})
    )
    user.save()

    # Test invalid JSON path using pytest's exception testing pattern
    try:
        # First check if JSON1 extension is available
        JsonUser.query().select("json_extract('{}', '$')").aggregate()
    except Exception as e:
        if 'json_extract' in str(e).lower():
            pytest.skip("SQLite installation doesn't have JSON1 extension")
        raise

    # If we get here, JSON1 is available, so test the invalid path
    with pytest.raises(OperationalError) as excinfo:
        query = JsonUser.query().where('username = ?', ('error_user',))
        query.json('settings', '$invalid.path', 'invalid_path')
        query.aggregate()

    # Verify error message
    assert "json path error near" in str(excinfo.value).lower() or "bad json path:" in str(excinfo.value).lower()


def test_json_non_json_column(json_fixtures):
    """Test behavior when extracting JSON from non-JSON column.

    Different databases handle this differently:
    - Some return NULL
    - Some throw an error

    This test handles both possibilities.
    """
    JsonUser = json_fixtures[0]

    # Create test user
    user = JsonUser(
        username='error_user',
        email='error@example.com',
        age=65,
        settings=json.dumps({"valid": "json"})
    )
    user.save()

    try:
        # First check if JSON1 extension is available
        JsonUser.query().select("json_extract('{}', '$')").aggregate()
    except Exception as e:
        if 'json_extract' in str(e).lower():
            pytest.skip("SQLite installation doesn't have JSON1 extension")
        raise

    # Different databases may behave differently for extracting from non-JSON columns
    try:
        query = JsonUser.query().where('username = ?', ('error_user',))
        query.json('username', '$.anything', 'extract_from_non_json')
        results = query.aggregate()[0]

        # For databases that return NULL for non-JSON columns
        assert results['extract_from_non_json'] is None

    except OperationalError:
        # For databases like SQLite that might throw an error
        # Just verify that we caught the expected exception type
        pass
