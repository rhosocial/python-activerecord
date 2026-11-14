# tests/rhosocial/activerecord_test/feature/basic/find_one_or_create/test_find_one_or_create_model_async.py
"""Unit tests for ``AsyncBaseActiveRecord.find_one_or_create``."""
import logging
from typing import ClassVar, Optional

import pytest

from rhosocial.activerecord.backend.errors import IntegrityError, OperationalError
from rhosocial.activerecord.backend.expression import Column, ComparisonPredicate, Literal
from rhosocial.activerecord.backend.impl.sqlite.backend.async_backend import AsyncSQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.base.field_proxy import FieldProxy
from rhosocial.activerecord.field import IntegerPKMixin
from rhosocial.activerecord.model import AsyncActiveRecord


class AsyncFindOrCreateItem(IntegerPKMixin, AsyncActiveRecord):
    """Natural-key model with a database-generated primary key."""

    @classmethod
    def table_name(cls):
        return "find_or_create_items"

    c: ClassVar[FieldProxy] = FieldProxy()

    id: Optional[int] = None
    code: str
    alt_code: Optional[str] = None
    name: str = ""


SCHEMA = """
CREATE TABLE find_or_create_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL,
    alt_code TEXT UNIQUE,
    name TEXT NOT NULL DEFAULT ''
);
"""


@pytest.fixture
async def async_item_model(tmp_path):
    database = tmp_path / "find_one_or_create_async.sqlite"
    await AsyncFindOrCreateItem.configure(
        SQLiteConnectionConfig(database=str(database)),
        AsyncSQLiteBackend,
    )
    backend = AsyncFindOrCreateItem.backend()
    await backend.connect()
    await backend.executescript(SCHEMA)

    yield AsyncFindOrCreateItem

    await backend.disconnect()
    AsyncFindOrCreateItem.__backend__ = None


def _expression(model):
    dialect = model.backend().dialect
    return ComparisonPredicate(
        dialect, "=", Column(dialect, "code"), Literal(dialect, "x")
    )


class TestAsyncFindOneOrCreate:
    """Natural-key lookup and create-only defaults, asynchronously."""

    async def test_creates_when_lookup_misses(self, async_item_model):
        row, created = await async_item_model.find_one_or_create(
            code="a", defaults={"name": "first"}
        )

        assert created is True
        assert row.id is not None
        assert row.code == "a"
        assert row.name == "first"
        assert row.is_new_record is False
        assert await async_item_model.query().count() == 1

    async def test_returns_existing_without_applying_defaults(self, async_item_model):
        first, created = await async_item_model.find_one_or_create(
            code="a", defaults={"name": "first"}
        )
        assert created is True

        second, created = await async_item_model.find_one_or_create(
            code="a", defaults={"name": "second"}
        )

        assert created is False
        assert second.id == first.id
        assert second.name == "first", "defaults must not update an existing row"
        assert second is not first, "the existing row is read back from the database"
        assert await async_item_model.query().count() == 1

    async def test_lookup_wins_over_defaults(self, async_item_model):
        row, created = await async_item_model.find_one_or_create(
            code="b", defaults={"code": "ignored", "name": "first"}
        )

        assert created is True
        assert row.code == "b"

    async def test_multiple_lookup_fields_are_all_applied(self, async_item_model):
        row, created = await async_item_model.find_one_or_create(
            code="c", alt_code="c-alt", defaults={"name": "first"}
        )

        assert created is True
        row2, created2 = await async_item_model.find_one_or_create(
            code="c", alt_code="c-alt", defaults={"name": "second"}
        )
        assert created2 is False
        assert row2.id == row.id

    async def test_empty_lookup_is_rejected(self, async_item_model):
        with pytest.raises(ValueError, match="at least one lookup field"):
            await async_item_model.find_one_or_create()

    async def test_unknown_lookup_field_is_rejected(self, async_item_model):
        with pytest.raises(TypeError, match="not a field"):
            await async_item_model.find_one_or_create(nope=1)

    async def test_unknown_defaults_field_is_rejected(self, async_item_model):
        with pytest.raises(TypeError, match="not a field"):
            await async_item_model.find_one_or_create(code="a", defaults={"nope": 1})

    async def test_none_lookup_value_is_rejected(self, async_item_model):
        with pytest.raises(ValueError, match="is None"):
            await async_item_model.find_one_or_create(code=None)

    async def test_expression_lookup_value_is_rejected(self, async_item_model):
        with pytest.raises(TypeError, match="expression"):
            await async_item_model.find_one_or_create(
                code=_expression(async_item_model)
            )

    async def test_expression_defaults_value_is_rejected(self, async_item_model):
        with pytest.raises(TypeError, match="expression"):
            await async_item_model.find_one_or_create(
                code="a", defaults={"name": _expression(async_item_model)}
            )

    async def test_sql_with_params_lookup_value_is_rejected(self, async_item_model):
        with pytest.raises(TypeError, match="expression"):
            await async_item_model.find_one_or_create(code=("code = ?", ("a",)))

    async def test_generated_primary_key_in_lookup_is_rejected(self, async_item_model):
        with pytest.raises(ValueError, match="generates its primary key"):
            await async_item_model.find_one_or_create(id=1, code="a")

    async def test_generated_primary_key_in_defaults_is_rejected(
        self, async_item_model
    ):
        with pytest.raises(ValueError, match="generates its primary key"):
            await async_item_model.find_one_or_create(code="a", defaults={"id": 1})

    async def test_conflict_reread_failure_keeps_the_cause(
        self, async_item_model, monkeypatch
    ):
        original_lookup = async_item_model._find_one_by_lookup
        reads = []

        async def failing_lookup(cls, lookup):
            reads.append(dict(lookup))
            if len(reads) == 1:
                return await original_lookup(lookup)
            raise OperationalError("reread connection lost")

        monkeypatch.setattr(
            async_item_model, "_find_one_by_lookup", classmethod(failing_lookup)
        )

        async def racing_save(self):
            raise IntegrityError("simulated concurrent insert")

        monkeypatch.setattr(async_item_model, "save", racing_save)

        with pytest.raises(IntegrityError) as info:
            await async_item_model.find_one_or_create(
                code="race", defaults={"alt_code": "race-alt"}
            )

        assert isinstance(info.value.__cause__, OperationalError)
        assert "reread connection lost" in str(info.value.__cause__)
        assert await async_item_model.query().count() == 0

    async def test_savepoint_probe_failure_logs_error(
        self, async_item_model, monkeypatch
    ):
        manager = async_item_model.backend().transaction_manager
        records = []

        def spy_log(cls, level, msg, *args, **kwargs):
            records.append((level, msg))

        monkeypatch.setattr(async_item_model, "log", classmethod(spy_log))

        async def broken_probe():
            raise RuntimeError("capability probe exploded")

        monkeypatch.setattr(manager, "supports_savepoint", broken_probe)

        row, created = await async_item_model.find_one_or_create(code="a")

        assert created is True
        assert row.code == "a"
        error_records = [item for item in records if item[0] == logging.ERROR]
        assert error_records, "a broken probe must be reported at ERROR level"
        assert "savepoint" in error_records[0][1].lower()

    async def test_savepoint_unsupported_does_not_log_error(
        self, async_item_model, monkeypatch
    ):
        manager = async_item_model.backend().transaction_manager
        records = []

        def spy_log(cls, level, msg, *args, **kwargs):
            records.append((level, msg))

        monkeypatch.setattr(async_item_model, "log", classmethod(spy_log))

        async def unsupported():
            return False

        monkeypatch.setattr(manager, "supports_savepoint", unsupported)

        row, created = await async_item_model.find_one_or_create(code="a")

        assert created is True
        assert not [item for item in records if item[0] == logging.ERROR]

    async def test_conflict_rereads_the_winner_once(self, async_item_model, monkeypatch):
        calls = []
        original_lookup = async_item_model._find_one_by_lookup

        async def counting_lookup(cls, lookup):
            calls.append(dict(lookup))
            return await original_lookup(lookup)

        monkeypatch.setattr(
            async_item_model, "_find_one_by_lookup", classmethod(counting_lookup)
        )

        original_save = async_item_model.save

        async def racing_save(self):
            winner = async_item_model(
                code=self.code, alt_code=self.alt_code, name="winner"
            )
            await original_save(winner)
            raise IntegrityError("simulated concurrent insert")

        monkeypatch.setattr(async_item_model, "save", racing_save)

        row, created = await async_item_model.find_one_or_create(
            code="race", defaults={"name": "loser"}
        )

        assert created is False
        assert row.name == "winner"
        assert len(calls) == 2, "the method must re-read exactly once after a conflict"

    async def test_conflict_without_matching_lookup_reraises(self, async_item_model):
        existing = async_item_model(
            code="taken", alt_code="taken-alt", name="old"
        )
        await existing.save()

        with pytest.raises(IntegrityError):
            await async_item_model.find_one_or_create(
                code="brand-new", defaults={"alt_code": "taken-alt"}
            )

        assert await async_item_model.query().count() == 1

    async def test_does_not_open_a_transaction(self, async_item_model, monkeypatch):
        manager = async_item_model.backend().transaction_manager

        async def forbidden(*args, **kwargs):
            raise AssertionError("find_one_or_create must not manage transactions")

        monkeypatch.setattr(manager, "begin", forbidden)
        monkeypatch.setattr(manager, "commit", forbidden)
        monkeypatch.setattr(manager, "rollback", forbidden)

        row, created = await async_item_model.find_one_or_create(code="a")

        assert created is True
        assert manager.is_active is False
        assert manager.transaction_level == 0

    async def test_no_savepoint_outside_a_transaction(
        self, async_item_model, monkeypatch
    ):
        manager = async_item_model.backend().transaction_manager
        savepoints = []

        async def spy_savepoint(name=None):
            savepoints.append(name)
            raise AssertionError("no savepoint outside a transaction")

        monkeypatch.setattr(manager, "savepoint", spy_savepoint)

        row, created = await async_item_model.find_one_or_create(code="a")

        assert created is True
        assert savepoints == []

    async def test_savepoint_is_used_inside_a_transaction(
        self, async_item_model, monkeypatch
    ):
        manager = async_item_model.backend().transaction_manager
        events = []
        original_savepoint = manager.savepoint
        original_release = manager.release

        async def spy_savepoint(name=None):
            name = await original_savepoint(name)
            events.append(("savepoint", name))
            return name

        async def spy_release(name):
            events.append(("release", name))
            return await original_release(name)

        monkeypatch.setattr(manager, "savepoint", spy_savepoint)
        monkeypatch.setattr(manager, "release", spy_release)

        async with async_item_model.transaction():
            row, created = await async_item_model.find_one_or_create(code="a")
            assert created is True
            assert manager.is_active is True, "the outer transaction survives"

        assert [event[0] for event in events] == ["savepoint", "release"]
        assert manager.is_active is False

    async def test_conflict_rolls_back_to_savepoint_and_keeps_transaction_usable(
        self, async_item_model, monkeypatch
    ):
        manager = async_item_model.backend().transaction_manager
        rollbacks = []
        original_rollback = manager.rollback_to

        async def spy_rollback(name):
            rollbacks.append(name)
            return await original_rollback(name)

        monkeypatch.setattr(manager, "rollback_to", spy_rollback)

        async with async_item_model.transaction():
            await async_item_model(
                code="taken", alt_code="taken-alt", name="old"
            ).save()

            with pytest.raises(IntegrityError):
                await async_item_model.find_one_or_create(
                    code="brand-new", defaults={"alt_code": "taken-alt"}
                )

            assert rollbacks, "the failed insert must roll back to its savepoint"
            assert manager.is_active is True
            assert await async_item_model.query().count() == 1, (
                "the outer transaction is still usable"
            )
