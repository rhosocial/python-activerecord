# tests/rhosocial/activerecord_test/feature/query/sqlite/test_json_expressions.py
"""Test JSON expression functionality in ActiveQuery using the new SQLExpression API."""
import json
import sqlite3
import pytest

from rhosocial.activerecord.backend.errors import OperationalError
from rhosocial.activerecord.base.expression import JsonExpression, CaseExpression, FunctionExpression, Column
from rhosocial.activerecord.testsuite.feature.query.conftest import json_user_fixture

# Helper to check if current SQLite version supports JSON functions
def is_json_supported():
    return sqlite3.sqlite_version_info >= (3, 9, 0)

@pytest.fixture(autouse=True)
def skip_if_no_json():
    if not is_json_supported():
        pytest.skip("SQLite installation doesn't have JSON1 extension")

@pytest.mark.skip(reason="This test needs a fixture with a JSON column 'roles' to work correctly.")
def test_json_expressions_in_where(json_user_fixture):
    """Test using JSON expressions in WHERE clause with the new API."""
    User = json_user_fixture
    User.delete_all()

    # Create test users
    User(username="admin_user", email="admin@example.com", age=30, roles=json.dumps({"admin": True, "editor": True})).save()
    User(username="regular_user", email="regular@example.com", age=25, roles=json.dumps({"admin": False, "editor": True})).save()

    # Use SQLExpression in WHERE to find admins
    # Note: SQLite returns 1 for JSON true, so we compare against the string '1' or integer 1
    admin_check = JsonExpression('roles', '->>', 'admin') == '1'
    admins = User.query().where(admin_check).all()
    
    assert len(admins) == 1
    assert admins[0].username == 'admin_user'

    # Find all editors
    editor_check = JsonExpression('roles', '->>', 'editor') == '1'
    editors = User.query().where(editor_check).all()
    assert len(editors) == 2

@pytest.mark.skip(reason="This test needs a fixture with a JSON column 'subscription' to work correctly.")
def test_json_with_case_expressions(json_user_fixture):
    """Test combining JSON expressions with CASE using the new API."""
    User = json_user_fixture
    User.delete_all()

    # Create test users
    User(username="premium_user", email="premium@example.com", subscription=json.dumps({"type": "premium"})).save()
    User(username="basic_user", email="basic@example.com", subscription=json.dumps({"type": "basic"})).save()
    User(username="trial_user", email="trial@example.com", subscription=json.dumps({"type": "trial"})).save()

    # Build expressions
    subscription_type = JsonExpression('subscription', '->>', 'type')
    is_premium = (subscription_type == 'premium')
    is_basic = (subscription_type == 'basic')
    
    priority_case = CaseExpression(
        [(is_premium, 'High Priority'), (is_basic, 'Medium Priority')],
        else_result='Low Priority'
    )

    query = User.query().select("username").select_expr(priority_case, "support_priority")
    results = query.aggregate()

    assert len(results) == 3
    priorities = {r['username']: r['support_priority'] for r in results}
    assert priorities['premium_user'] == 'High Priority'
    assert priorities['basic_user'] == 'Medium Priority'
    assert priorities['trial_user'] == 'Low Priority'

@pytest.mark.skip(reason="This test needs a fixture with a JSON column 'scores' to work correctly.")
def test_json_with_aggregation(json_user_fixture):
    """Test JSON expressions with aggregation functions using the new API."""
    User = json_user_fixture
    User.delete_all()

    # Create test users
    User(username="user1", email="user1@example.com", scores=json.dumps({"math": 90})).save()
    User(username="user2", email="user2@example.com", scores=json.dumps({"math": 80})).save()
    User(username="user3", email="user3@example.com", scores=json.dumps({"math": 85})).save()

    # Calculate average math score
    math_score_expr = FunctionExpression('CAST', JsonExpression('scores', '->>', 'math'), 'AS', 'INTEGER')
    avg_expr = FunctionExpression('AVG', math_score_expr)
    
    query = User.query().select_expr(avg_expr, "avg_math_score")
    result = query.aggregate()[0]

    assert 'avg_math_score' in result
    assert abs(float(result['avg_math_score']) - 85.0) < 0.01
