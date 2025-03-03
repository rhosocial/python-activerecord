def test_transaction_commit(db, setup_test_table):
    """测试事务提交"""
    with db.transaction():
        db.insert("test_table", {"name": "test", "age": 20})
    row = db.fetch_one("SELECT * FROM test_table WHERE name = ?", ("test",))
    assert row is not None

def test_transaction_rollback(db, setup_test_table):
    """测试事务回滚"""
    try:
        with db.transaction():
            db.insert("test_table", {"name": "test", "age": 20})
            raise Exception("Force rollback")
    except Exception:
        pass
    row = db.fetch_one("SELECT * FROM test_table WHERE name = ?", ("test",))
    assert row is None

def test_nested_transaction(db, setup_test_table):
    """测试嵌套事务"""
    with db.transaction():
        db.insert("test_table", {"name": "outer", "age": 20})
        with db.transaction():
            db.insert("test_table", {"name": "inner", "age": 30})
    rows = db.fetch_all("SELECT * FROM test_table ORDER BY age")
    assert len(rows) == 2