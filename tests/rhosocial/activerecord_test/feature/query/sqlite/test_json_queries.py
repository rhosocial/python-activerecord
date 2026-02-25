# tests/rhosocial/activerecord_test/feature/query/sqlite/test_json_queries.py
"""
SQLite JSON query tests.

SQLite does not have native JSON type, so JSON data is stored as TEXT
and serialized/deserialized using json.dumps/json.loads in the application.
This test verifies that JSON operations work correctly with TEXT storage.
"""
import json


def test_sqlite_json_text_operations(json_user_fixture):
    """
    Test JSON operations using TEXT storage in SQLite.
    
    SQLite stores JSON as TEXT, so the application must manually serialize
    dict/list to JSON strings using json.dumps before saving, and
    deserialize using json.loads after reading.
    """
    JsonUser = json_user_fixture

    user_data = {
        'preferences': {
            'theme': 'dark',
            'language': 'en',
            'notifications': True
        },
        'settings': {
            'privacy': 'public',
            'timezone': 'UTC'
        },
        'tags': ['developer', 'python', 'activerecord']
    }

    json_user = JsonUser(
        username='json_test_user',
        email='json@example.com',
        age=28,
        settings=json.dumps(user_data['settings']),
        tags=json.dumps(user_data['tags']),
        profile=json.dumps(user_data['preferences'])
    )
    json_user.save()

    results = JsonUser.query().where(JsonUser.c.username == 'json_test_user').all()
    assert len(results) == 1
    assert results[0].username == 'json_test_user'

    retrieved_settings = json.loads(results[0].settings)
    assert retrieved_settings['privacy'] == 'public'
    assert retrieved_settings['timezone'] == 'UTC'

    retrieved_tags = json.loads(results[0].tags)
    assert 'developer' in retrieved_tags
    assert 'python' in retrieved_tags
