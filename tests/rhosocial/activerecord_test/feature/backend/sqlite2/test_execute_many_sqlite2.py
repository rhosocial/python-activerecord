# tests/rhosocial/activerecord_test/feature/backend/sqlite2/test_execute_many.py
def test_execute_many(db, setup_test_table):
    """Test batch insertion"""
    data = [
        ("name1", 20),
        ("name2", 30),
        ("name3", 40)
    ]
    result = db.execute_many(
        "INSERT INTO test_table (name, age) VALUES (?, ?)",
        data
    )
    assert result.affected_rows == 3
    rows = db.fetch_all("SELECT * FROM test_table ORDER BY age")
    assert len(rows) == 3
