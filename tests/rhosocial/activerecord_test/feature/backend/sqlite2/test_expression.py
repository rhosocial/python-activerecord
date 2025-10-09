# tests/rhosocial/activerecord_test/feature/backend/sqlite2/test_expression.py
import pytest

from rhosocial.activerecord.backend.errors import DatabaseError, OperationalError


def test_update_with_expression(db, setup_test_table):
    """Test updating with an expression"""
    # Insert test data
    db.execute(
        "INSERT INTO test_table (name, age) VALUES (?, ?)",
        ("test_user", 20)
    )

    # Use expression to update age
    result = db.execute(
        "UPDATE test_table SET age = ? WHERE name = ?",
        (db.create_expression("age + 1"), "test_user")
    )

    assert result.affected_rows == 1

    # Verify update result
    row = db.execute(
        "SELECT age FROM test_table WHERE name = ?",
        ("test_user",),
        returning=True
    ).data[0]
    assert row["age"] == 21


def test_multiple_expressions(db, setup_test_table):
    """Test using multiple expressions in the same SQL"""
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
    """Test mixing regular parameters and expressions"""
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
    """Test expression containing a question mark"""
    with pytest.raises(DatabaseError):
        db.execute(
            "UPDATE test_table SET age = ? WHERE name = ?",
            (db.create_expression("age + ?"), "test_user")
        )


def test_expression_in_subquery(db, setup_test_table):
    """Test using expression in subquery"""
    # Insert test data
    result = db.execute(
        "INSERT INTO test_table (name, age) VALUES (?, ?), (?, ?)",
        ("user1", 20, "user2", 30),
        returning=False
    )
    assert result.affected_rows == 2, "Should insert two records"

    # Verify inserted data
    rows = db.execute(
        "SELECT * FROM test_table ORDER BY age",
        returning=True
    ).data
    assert len(rows) == 2, "Should have two records"
    assert rows[0]["age"] == 20, "First record age should be 20"
    assert rows[1]["age"] == 30, "Second record age should be 30"

    # Test subquery with expression
    result = db.execute(
        """
        SELECT *
        FROM test_table
        WHERE age > ?
          AND age < ?
        """,
        (
            db.create_expression("(SELECT MIN(age) FROM test_table)"),
            db.create_expression("(SELECT MAX(age) FROM test_table)")
        ),
        returning=True
    )

    assert len(result.data) == 0, "Should not have matching records since condition is MIN < age < MAX"


def test_expression_in_insert(db, setup_test_table):
    """Test using expression in INSERT statement"""
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

    assert row["age"] is None  # Since there's no data in the table yet, MAX(age) is NULL
    assert isinstance(row["created_at"], str)  # Ensure timestamp is correctly set


def test_complex_expression(db, setup_test_table):
    """Test complex expression"""
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
    """Test invalid expression"""
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
    """Test parameter count mismatch scenario"""
    db.execute(
        "INSERT INTO test_table (name, age) VALUES (?, ?)",
        ("test_user", 20)
    )

    # Case 1: Too few parameters
    with pytest.raises(ValueError, match="Parameter count mismatch: SQL needs 3 parameters but 2 were provided"):
        db.execute(
            "UPDATE test_table SET age = ? WHERE name = ? AND age = ?",
            (db.create_expression("age + 1"), "test_user")  # Missing last parameter
        )

    # Case 2: Too many parameters
    with pytest.raises(ValueError, match="Parameter count mismatch: SQL needs 2 parameters but 3 were provided"):
        db.execute(
            "UPDATE test_table SET age = ? WHERE name = ?",
            (db.create_expression("age + 1"), "test_user", 20)  # Extra parameter
        )
