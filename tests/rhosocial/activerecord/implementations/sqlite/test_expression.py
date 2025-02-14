import pytest

from src.rhosocial.activerecord.backend.errors import DatabaseError, OperationalError


def test_update_with_expression(db, setup_test_table):
    """测试使用表达式进行更新"""
    # 插入测试数据
    db.execute(
        "INSERT INTO test_table (name, age) VALUES (?, ?)",
        ("test_user", 20)
    )
    
    # 使用表达式更新age
    result = db.execute(
        "UPDATE test_table SET age = ? WHERE name = ?",
        (db.create_expression("age + 1"), "test_user")
    )

    assert result.affected_rows == 1

    # 验证更新结果
    row = db.execute(
        "SELECT age FROM test_table WHERE name = ?",
        ("test_user",),
        returning=True
    ).data[0]
    assert row["age"] == 21


def test_multiple_expressions(db, setup_test_table):
    """测试在同一SQL中使用多个表达式"""
    db.execute(
        "INSERT INTO test_table (name, age) VALUES (?, ?)",
        ("test_user", 20)
    )

    result = db.execute(
        "UPDATE test_table SET age = ?, name = ? WHERE name = ?",
        (
            db.create_expression("age + 10"),
            db.create_expression("name || '_updated'"),
            "test_user"
        )
    )

    assert result.affected_rows == 1

    row = db.execute(
        "SELECT name, age FROM test_table WHERE name = ?",
        ("test_user_updated",),
        returning=True
    ).data[0]
    assert row["age"] == 30
    assert row["name"] == "test_user_updated"


def test_mixed_params_and_expressions(db, setup_test_table):
    """测试混合使用普通参数和表达式"""
    db.execute(
        "INSERT INTO test_table (name, age) VALUES (?, ?)",
        ("test_user", 20)
    )

    result = db.execute(
        "UPDATE test_table SET age = ?, name = ? WHERE name = ? AND age >= ?",
        (
            db.create_expression("age * 2"),
            "new_name",
            "test_user",
            18
        )
    )

    assert result.affected_rows == 1

    row = db.execute(
        "SELECT name, age FROM test_table WHERE name = ?",
        ("new_name",),
        returning=True
    ).data[0]
    assert row["age"] == 40
    assert row["name"] == "new_name"


def test_expression_with_placeholder(db, setup_test_table):
    """测试表达式中包含问号的情况"""
    with pytest.raises(DatabaseError):
        db.execute(
            "UPDATE test_table SET age = ? WHERE name = ?",
            (db.create_expression("age + ?"), "test_user")
        )


def test_expression_in_subquery(db, setup_test_table):
    """测试在子查询中使用表达式"""
    # 插入测试数据
    result = db.execute(
        "INSERT INTO test_table (name, age) VALUES (?, ?), (?, ?)",
        ("user1", 20, "user2", 30),
        returning=False
    )
    assert result.affected_rows == 2, "应该插入两条记录"

    # 验证插入的数据
    rows = db.execute(
        "SELECT * FROM test_table ORDER BY age",
        returning=True
    ).data
    assert len(rows) == 2, "应该有两条记录"
    assert rows[0]["age"] == 20, "第一条记录age应为20"
    assert rows[1]["age"] == 30, "第二条记录age应为30"

    # 测试带表达式的子查询
    result = db.execute(
        """
        SELECT * FROM test_table 
        WHERE age > ? AND age < ?
        """,
        (
            db.create_expression("(SELECT MIN(age) FROM test_table)"),
            db.create_expression("(SELECT MAX(age) FROM test_table)")
        ),
        returning=True
    )

    assert len(result.data) == 0, "不应该有符合条件的记录，因为条件是 MIN < age < MAX"


def test_expression_in_insert(db, setup_test_table):
    """测试在INSERT语句中使用表达式"""
    db.execute(
        "INSERT INTO test_table (name, age, created_at) VALUES (?, ?, ?)",
        (
            "test_user",
            db.create_expression("(SELECT MAX(age) + 1 FROM test_table)"),
            db.create_expression("CURRENT_TIMESTAMP")
        )
    )

    row = db.execute(
        "SELECT * FROM test_table WHERE name = ?",
        ("test_user",),
        returning=True
    ).data[0]

    assert row["age"] is None  # 因为表中还没有数据，MAX(age)为NULL
    assert isinstance(row["created_at"], str)  # 确保时间戳被正确设置


def test_complex_expression(db, setup_test_table):
    """测试复杂表达式"""
    db.execute(
        "INSERT INTO test_table (name, age) VALUES (?, ?)",
        ("test_user", 20)
    )

    result = db.execute(
        "UPDATE test_table SET age = ? WHERE name = ?",
        (
            db.create_expression("""
                CASE 
                    WHEN age < 18 THEN 18 
                    WHEN age > 60 THEN 60 
                    ELSE age + 5 
                END
            """),
            "test_user"
        )
    )

    assert result.affected_rows == 1

    row = db.execute(
        "SELECT age FROM test_table WHERE name = ?",
        ("test_user",),
        returning=True
    ).data[0]
    assert row["age"] == 25


def test_invalid_expression(db, setup_test_table):
    """测试无效的表达式"""
    db.execute(
        "INSERT INTO test_table (name, age) VALUES (?, ?)",
        ("test_user", 20)
    )

    with pytest.raises(OperationalError):
        db.execute(
            "UPDATE test_table SET age = ? WHERE name = ?",
            (db.create_expression("invalid_column + 1"), "test_user")
        )


def test_expression_count_mismatch(db, setup_test_table):
    """测试参数数量不匹配的情况"""
    db.execute(
        "INSERT INTO test_table (name, age) VALUES (?, ?)",
        ("test_user", 20)
    )

    # 情况1: 参数太少
    with pytest.raises(ValueError, match="Parameter count mismatch: expected 3, got 2"):
        db.execute(
            "UPDATE test_table SET age = ? WHERE name = ? AND age = ?",
            (db.create_expression("age + 1"), "test_user")  # 缺少最后一个参数
        )

    # 情况2: 参数太多
    with pytest.raises(ValueError, match="Parameter count mismatch: expected 2, got 3"):
        db.execute(
            "UPDATE test_table SET age = ? WHERE name = ?",
            (db.create_expression("age + 1"), "test_user", 20)  # 多余的参数
        )