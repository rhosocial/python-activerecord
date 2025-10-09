# tests/rhosocial/activerecord_test/feature/backend/sqlite2/test_curd.py
from datetime import datetime
import pytest


def test_insert_success(db, setup_test_table):
    """Test successful insertion"""
    result = db.insert("test_table", {
        "name": "test",
        "age": 20,
        "created_at": datetime.now()
    })
    assert result.affected_rows == 1
    assert result.last_insert_id is not None


def test_insert_with_invalid_data(db, setup_test_table):
    """Test inserting invalid data"""
    with pytest.raises(Exception):  # Specific exception type depends on implementation
        db.insert("test_table", {
            "invalid_column": "value"
        })


def test_fetch_one(db, setup_test_table):
    """Test querying a single record"""
    db.insert("test_table", {"name": "test", "age": 20})
    row = db.fetch_one("SELECT * FROM test_table WHERE name = ?", ("test",))
    assert row is not None
    assert row["name"] == "test"
    assert row["age"] == 20


def test_fetch_all(db, setup_test_table):
    """Test querying multiple records"""
    db.insert("test_table", {"name": "test1", "age": 20})
    db.insert("test_table", {"name": "test2", "age": 30})
    rows = db.fetch_all("SELECT * FROM test_table ORDER BY age")
    assert len(rows) == 2
    assert rows[0]["age"] == 20
    assert rows[1]["age"] == 30


def test_update(db, setup_test_table):
    """Test updating a record"""
    db.insert("test_table", {"name": "test", "age": 20})
    result = db.update(
        "test_table",
        {"age": 21},
        "name = ?",
        ("test",)
    )
    assert result.affected_rows == 1
    row = db.fetch_one("SELECT * FROM test_table WHERE name = ?", ("test",))
    assert row["age"] == 21


def test_delete(db, setup_test_table):
    """Test deleting a record"""
    db.insert("test_table", {"name": "test", "age": 20})
    result = db.delete("test_table", "name = ?", ("test",))
    assert result.affected_rows == 1
    row = db.fetch_one("SELECT * FROM test_table WHERE name = ?", ("test",))
    assert row is None
