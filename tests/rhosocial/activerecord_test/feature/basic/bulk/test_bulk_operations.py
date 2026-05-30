# tests/rhosocial/activerecord_test/feature/basic/bulk/test_bulk_operations.py
"""Tests for bulk operations (bulk_create, bulk_update, bulk_delete, update_all, delete_all)."""

import os
import tempfile
from typing import ClassVar, Optional

import pytest

from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.field import IntegerPKMixin
from rhosocial.activerecord.base.field_proxy import FieldProxy
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.backend.errors import BulkStateError, BulkValidationError
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType


def execute_sql(backend, sql: str, params=None):
    options = ExecutionOptions(stmt_type=StatementType.DDL if 'CREATE' in sql.upper() else StatementType.DML)
    return backend.execute(sql, params or (), options=options)


class BulkUser(IntegerPKMixin, ActiveRecord):
    __table_name__ = "bulk_users"
    c: ClassVar[FieldProxy] = FieldProxy()

    id: Optional[int] = None
    name: str
    age: int = 0
    email: str = ""


@pytest.fixture
def db_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    yield path
    os.unlink(path)


@pytest.fixture
def configured_model(db_path):
    config = SQLiteConnectionConfig(database=db_path)
    BulkUser.configure(config, SQLiteBackend)
    backend = BulkUser.backend()
    execute_sql(backend, """
        CREATE TABLE bulk_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            age INTEGER DEFAULT 0,
            email TEXT DEFAULT ''
        )
    """)
    yield BulkUser
    backend.disconnect()


class TestBulkCreate:
    def test_basic_bulk_create(self, configured_model):
        users = [
            BulkUser(name="Alice", age=25, email="alice@test.com"),
            BulkUser(name="Bob", age=30, email="bob@test.com"),
            BulkUser(name="Charlie", age=35, email="charlie@test.com"),
        ]
        result = BulkUser.bulk_create(users)

        assert len(result) == 3
        assert all(u.id is not None for u in result)
        assert result[0].name == "Alice"
        assert result[1].name == "Bob"
        assert result[2].name == "Charlie"

        db_users = BulkUser.find_all()
        assert len(db_users) == 3

    def test_bulk_create_empty_list(self, configured_model):
        result = BulkUser.bulk_create([])
        assert result == []

    def test_bulk_create_non_new_record_raises(self, configured_model):
        user = BulkUser(name="Alice", age=25)
        user.save()

        with pytest.raises(BulkStateError):
            BulkUser.bulk_create([user])

    def test_bulk_create_validation_failure(self, configured_model):
        from pydantic import field_validator

        class ValidatedUser(IntegerPKMixin, ActiveRecord):
            __table_name__ = "bulk_users"
            id: Optional[int] = None
            name: str
            age: int = 0
            email: str = ""

            @field_validator("name")
            @classmethod
            def name_must_not_be_empty(cls, v):
                if not v.strip():
                    raise ValueError("name must not be empty")
                return v

        ValidatedUser.configure(
            SQLiteConnectionConfig(database=configured_model.backend().config.database),
            SQLiteBackend,
        )

        valid_user = ValidatedUser(name="Alice", age=25)
        invalid_user = ValidatedUser.model_construct(id=None, name="   ", age=30, email="")
        users = [valid_user, invalid_user]
        with pytest.raises(BulkValidationError) as exc_info:
            ValidatedUser.bulk_create(users)
        assert len(exc_info.value.errors) >= 1

    def test_bulk_create_with_batch_size(self, configured_model):
        users = [BulkUser(name=f"User{i}", age=i) for i in range(10)]
        result = BulkUser.bulk_create(users, batch_size=3)

        assert len(result) == 10
        db_users = BulkUser.find_all()
        assert len(db_users) == 10

    def test_bulk_create_updates_is_from_db(self, configured_model):
        users = [BulkUser(name="Alice", age=25)]
        result = BulkUser.bulk_create(users)
        assert not result[0].is_new_record


class TestBulkUpdate:
    def test_basic_bulk_update(self, configured_model):
        users = [
            BulkUser(name="Alice", age=25, email="alice@test.com"),
            BulkUser(name="Bob", age=30, email="bob@test.com"),
        ]
        BulkUser.bulk_create(users)

        users[0].age = 26
        users[1].age = 31
        affected = BulkUser.bulk_update(users, ["age"])

        assert affected == 2
        reloaded = BulkUser.find_all()
        ages = sorted(u.age for u in reloaded)
        assert ages == [26, 31]

    def test_bulk_update_empty_list(self, configured_model):
        assert BulkUser.bulk_update([], ["name"]) == 0

    def test_bulk_update_empty_fields_raises(self, configured_model):
        users = [BulkUser(name="Alice", age=25)]
        BulkUser.bulk_create(users)
        with pytest.raises(ValueError, match="must not be empty"):
            BulkUser.bulk_update(users, [])

    def test_bulk_update_invalid_fields_raises(self, configured_model):
        users = [BulkUser(name="Alice", age=25)]
        BulkUser.bulk_create(users)
        with pytest.raises(ValueError, match="Invalid field names"):
            BulkUser.bulk_update(users, ["nonexistent_field"])

    def test_bulk_update_new_record_raises(self, configured_model):
        users = [BulkUser(name="Alice", age=25)]
        with pytest.raises(BulkStateError):
            BulkUser.bulk_update(users, ["age"])

    def test_bulk_update_multiple_fields(self, configured_model):
        users = [
            BulkUser(name="Alice", age=25, email="old@test.com"),
            BulkUser(name="Bob", age=30, email="old@test.com"),
        ]
        BulkUser.bulk_create(users)

        users[0].name = "Alice Updated"
        users[0].email = "new@test.com"
        users[1].name = "Bob Updated"
        users[1].email = "new2@test.com"
        affected = BulkUser.bulk_update(users, ["name", "email"])

        assert affected == 2
        reloaded = BulkUser.find_all()
        names = sorted(u.name for u in reloaded)
        assert names == ["Alice Updated", "Bob Updated"]

    def test_bulk_update_with_batch_size(self, configured_model):
        users = [BulkUser(name=f"User{i}", age=i) for i in range(10)]
        BulkUser.bulk_create(users)

        for u in users:
            u.age = u.age + 100
        affected = BulkUser.bulk_update(users, ["age"], batch_size=3)

        assert affected == 10


class TestBulkDelete:
    def test_basic_bulk_delete(self, configured_model):
        users = [
            BulkUser(name="Alice", age=25),
            BulkUser(name="Bob", age=30),
            BulkUser(name="Charlie", age=35),
        ]
        BulkUser.bulk_create(users)
        assert len(BulkUser.find_all()) == 3

        affected = BulkUser.bulk_delete(users[:2])
        assert affected == 2
        remaining = BulkUser.find_all()
        assert len(remaining) == 1
        assert remaining[0].name == "Charlie"

    def test_bulk_delete_empty_list(self, configured_model):
        assert BulkUser.bulk_delete([]) == 0

    def test_bulk_delete_new_record_raises(self, configured_model):
        users = [BulkUser(name="Alice", age=25)]
        with pytest.raises(BulkStateError):
            BulkUser.bulk_delete(users)

    def test_bulk_delete_clears_pk(self, configured_model):
        users = [BulkUser(name="Alice", age=25)]
        BulkUser.bulk_create(users)
        BulkUser.bulk_delete(users)
        assert users[0].id is None


class TestQueryUpdateAll:
    def test_basic_update_all(self, configured_model):
        users = [
            BulkUser(name="Alice", age=25, email="a@test.com"),
            BulkUser(name="Bob", age=30, email="b@test.com"),
            BulkUser(name="Charlie", age=35, email="c@test.com"),
        ]
        BulkUser.bulk_create(users)

        affected = BulkUser.query().where(BulkUser.c.age > 28).update_all(
            {"email": "updated@test.com"}
        )
        assert affected == 2

        updated = BulkUser.query().where(BulkUser.c.email == "updated@test.com").all()
        assert len(updated) == 2

    def test_update_all_no_where_raises(self, configured_model):
        with pytest.raises(ValueError, match="requires a WHERE clause"):
            BulkUser.query().update_all({"age": 0})


class TestQueryDeleteAll:
    def test_basic_delete_all(self, configured_model):
        users = [
            BulkUser(name="Alice", age=25),
            BulkUser(name="Bob", age=30),
            BulkUser(name="Charlie", age=35),
        ]
        BulkUser.bulk_create(users)

        affected = BulkUser.query().where(BulkUser.c.age > 28).delete_all()
        assert affected == 2

        remaining = BulkUser.find_all()
        assert len(remaining) == 1
        assert remaining[0].name == "Alice"

    def test_delete_all_no_where_raises(self, configured_model):
        with pytest.raises(ValueError, match="requires a WHERE clause"):
            BulkUser.query().delete_all()

    def test_delete_all_no_matches(self, configured_model):
        users = [BulkUser(name="Alice", age=25)]
        BulkUser.bulk_create(users)

        affected = BulkUser.query().where(BulkUser.c.age > 100).delete_all()
        assert affected == 0
        assert len(BulkUser.find_all()) == 1
