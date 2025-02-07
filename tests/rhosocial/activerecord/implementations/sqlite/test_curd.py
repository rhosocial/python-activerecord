from datetime import datetime
import pytest

def test_insert_success(db, setup_test_table):
    """测试插入成功"""
    result = db.insert("test_table", {
        "name": "test",
        "age": 20,
        "created_at": datetime.now()
    })
    assert result.affected_rows == 1
    assert result.last_insert_id is not None

def test_insert_with_invalid_data(db, setup_test_table):
    """测试插入无效数据"""
    with pytest.raises(Exception):  # 具体异常类型取决于实现
        db.insert("test_table", {
            "invalid_column": "value"
        })

def test_fetch_one(db, setup_test_table):
    """测试查询单条记录"""
    db.insert("test_table", {"name": "test", "age": 20})
    row = db.fetch_one("SELECT * FROM test_table WHERE name = ?", ("test",))
    assert row is not None
    assert row["name"] == "test"
    assert row["age"] == 20

def test_fetch_all(db, setup_test_table):
    """测试查询多条记录"""
    db.insert("test_table", {"name": "test1", "age": 20})
    db.insert("test_table", {"name": "test2", "age": 30})
    rows = db.fetch_all("SELECT * FROM test_table ORDER BY age")
    assert len(rows) == 2
    assert rows[0]["age"] == 20
    assert rows[1]["age"] == 30

def test_update(db, setup_test_table):
    """测试更新记录"""
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
    """测试删除记录"""
    db.insert("test_table", {"name": "test", "age": 20})
    result = db.delete("test_table", "name = ?", ("test",))
    assert result.affected_rows == 1
    row = db.fetch_one("SELECT * FROM test_table WHERE name = ?", ("test",))
    assert row is None