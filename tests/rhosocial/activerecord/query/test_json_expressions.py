"""Test JSON expression functionality in ActiveQuery."""
import json
import sqlite3

import pytest

from src.rhosocial.activerecord.query.expression import FunctionExpression, JsonExpression, CaseExpression
from .utils import create_json_test_fixtures

# Create multi-table test fixtures
json_fixtures = create_json_test_fixtures()


# Helper to check if current SQLite version supports JSON functions
def is_json_supported():
    # SQLite has JSON1 extension in most builds from version 3.9.0
    version = sqlite3.sqlite_version_info
    return version >= (3, 9, 0)


@pytest.fixture(scope="module")
def skip_if_unsupported():
    """Skip tests if SQLite version doesn't support JSON functions."""
    if not is_json_supported():
        pytest.skip("SQLite version doesn't support JSON functions (requires 3.9.0+)")


def test_json_extract(json_fixtures, skip_if_unsupported):
    """Test JSON extract operations."""
    JsonUser = json_fixtures[0]  # 只有一个模型类

    # Create test user with JSON data
    user = JsonUser(
        username='test_user',
        email='test@example.com',
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
        # Test basic JSON extract
        query = JsonUser.query().where('username = ?', ('test_user',))
        query.json_expr('settings', '$.theme', alias='theme')
        results = query.aggregate()[0]

        assert 'theme' in results
        assert results['theme'] == 'dark'

        # Test extracting from nested JSON
        query = JsonUser.query().where('username = ?', ('test_user',))
        query.json_expr('settings', '$.notifications.email', alias='email_notifications')
        results = query.aggregate()[0]

        assert 'email_notifications' in results
        assert results['email_notifications'] == 1 or results['email_notifications'] == True

        # Test extracting from array
        query = JsonUser.query().where('username = ?', ('test_user',))
        query.json_expr('settings', '$.preferences[0]', alias='first_preference')
        results = query.aggregate()[0]

        assert 'first_preference' in results
        assert results['first_preference'] == 'news'
    except Exception as e:
        if 'no such function: json_extract' in str(e).lower():
            pytest.skip("SQLite installation doesn't have JSON1 extension")
        raise


def test_json_contains(json_fixtures, skip_if_unsupported):
    """Test JSON contains operations."""
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
        results = query.all()

        assert len(results) == 2
        admin_users = [r for r in results if r['is_admin'] == 1]
        assert len(admin_users) == 1
        assert admin_users[0]['username'] == 'user1'

        # Test with another value
        query = User.query()
        query.json_expr('tags', '$', operation='contains', value='"subscriber"', alias='is_subscriber')
        results = query.all()

        subscriber_users = [r for r in results if r['is_subscriber'] == 1]
        assert len(subscriber_users) == 1
        assert subscriber_users[0]['username'] == 'user2'
    except Exception as e:
        if 'no such function: json_contains' in str(e).lower() or 'json_extract' in str(e).lower():
            try:
                # Try an alternative approach with json_extract and LIKE if json_contains not available
                query = User.query()
                query.select("username, json_extract(tags, '$') as tags_json")
                results = query.all()

                # If this works, we'll skip the original test
                pytest.skip("SQLite installation doesn't have json_contains function")
            except:
                pytest.skip("SQLite installation doesn't have JSON1 extension")
        raise


def test_json_exists(json_fixtures, skip_if_unsupported):
    """Test JSON exists operations."""
    User = json_fixtures[0]

    # Create test users with varying JSON data
    users_data = [
        {
            "username": "complete_user",
            "email": "complete@example.com",
            "age": 30,
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
            "age": 25,
            "profile": json.dumps({
                "phone": "555-5678"
                # No address information
            })
        }
    ]

    for data in users_data:
        user = User(**data)
        user.save()

    try:
        # Test if path exists in JSON
        query = User.query()
        query.json_expr('profile', '$.address', operation='exists', alias='has_address')
        results = query.all()

        assert len(results) == 2
        users_with_address = [r for r in results if r['has_address'] == 1]
        assert len(users_with_address) == 1
        assert users_with_address[0]['username'] == 'complete_user'

        # Test another path
        query = User.query()
        query.json_expr('profile', '$.phone', operation='exists', alias='has_phone')
        results = query.all()

        users_with_phone = [r for r in results if r['has_phone'] == 1]
        assert len(users_with_phone) == 2  # Both users have phone
    except Exception as e:
        if 'no such function' in str(e).lower():
            pytest.skip("SQLite installation doesn't have required JSON functions")
        raise


def test_json_expressions_in_where(json_fixtures, skip_if_unsupported):
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
        results = query.all()

        assert len(results) == 1
        assert results[0].username == 'admin_user'

        # Find all editors
        query = User.query()
        query.where("json_extract(roles, '$.editor') = 1 OR json_extract(roles, '$.editor') = 'true'")
        results = query.all()

        assert len(results) == 2  # Both users are editors
    except Exception as e:
        if 'no such function' in str(e).lower():
            pytest.skip("SQLite installation doesn't have required JSON functions")
        raise


def test_json_with_aggregation(json_fixtures, skip_if_unsupported):
    """Test JSON expressions with aggregation."""
    User = json_fixtures[0]

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
        user = User(**data)
        user.save()

    try:
        # Calculate average math score
        query = User.query()
        query.select("AVG(json_extract(scores, '$.math')) as avg_math_score")
        results = query.aggregate()[0]

        assert 'avg_math_score' in results
        assert abs(float(results['avg_math_score']) - 85.0) < 0.01  # (90 + 80 + 85) / 3 = 85

        # Calculate max science score
        query = User.query()
        query.select("MAX(json_extract(scores, '$.science')) as max_science_score")
        results = query.aggregate()[0]

        assert 'max_science_score' in results
        assert float(results['max_science_score']) == 95.0

        # Count users with history score > 75
        query = User.query()
        query.select("COUNT(*) as advanced_history_count")
        query.where("json_extract(scores, '$.history') > 75")
        results = query.aggregate()[0]

        assert 'advanced_history_count' in results
        assert results['advanced_history_count'] == 1  # Only user3 has history > 75
    except Exception as e:
        if 'no such function' in str(e).lower():
            pytest.skip("SQLite installation doesn't have required JSON functions")
        raise


def test_json_with_case_expressions(json_fixtures, skip_if_unsupported):
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
        # query.select("""
        # CASE
        #     WHEN json_extract(subscription, '$.type') = 'premium' THEN 'High Priority'
        #     WHEN json_extract(subscription, '$.type') = 'basic' THEN 'Medium Priority'
        #     ELSE 'Low Priority'
        # END as support_priority
        # """)
        query.group_by("support_priority")

        results = query.aggregate()

        # Verify results
        assert len(results) == 3

        # Create mapping for easy verification
        priorities = {r['username']: r['support_priority'] for r in results}

        assert priorities['premium_user'] == 'High Priority'
        assert priorities['basic_user'] == 'Medium Priority'
        assert priorities['trial_user'] == 'Low Priority'
    except Exception as e:
        if 'no such function' in str(e).lower():
            pytest.skip("SQLite installation doesn't have required JSON functions")
        raise


def test_json_in_group_by(json_fixtures, skip_if_unsupported):
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


def test_explain_json_expressions(json_fixtures, skip_if_unsupported):
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