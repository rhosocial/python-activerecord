# tests/rhosocial/activerecord_test/feature/basic/find_one_or_create/test_find_one_or_create.py
"""Unit tests for ``BaseActiveRecord.find_one_or_create`` (synchronous)."""
import logging
from typing import ClassVar, Optional

import pytest

from rhosocial.activerecord.backend.errors import IntegrityError, OperationalError
from rhosocial.activerecord.backend.expression import Column, ComparisonPredicate, Literal
from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.base.field_proxy import FieldProxy
from rhosocial.activerecord.field import IntegerPKMixin
from rhosocial.activerecord.model import ActiveRecord


class FindOrCreateItem(IntegerPKMixin, ActiveRecord):
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
def item_model(tmp_path):
    database = tmp_path / "find_one_or_create.sqlite"
    FindOrCreateItem.configure(
        SQLiteConnectionConfig(database=str(database)),
        SQLiteBackend,
    )
    backend = FindOrCreateItem.backend()
    backend.connect()
    backend.executescript(SCHEMA)

    yield FindOrCreateItem

    backend.disconnect()
    FindOrCreateItem.__backend__ = None


def _expression(model):
    dialect = model.backend().dialect
    return ComparisonPredicate(
        dialect, "=", Column(dialect, "code"), Literal(dialect, "x")
    )


class TestFindOneOrCreate:
    """Natural-key lookup and create-only defaults."""

    def test_creates_when_lookup_misses(self, item_model):
        row, created = item_model.find_one_or_create(
            code="a", defaults={"name": "first"}
        )

        assert created is True
        assert row.id is not None
        assert row.code == "a"
        assert row.name == "first"
        assert row.is_new_record is False
        assert item_model.query().count() == 1

    def test_returns_existing_without_applying_defaults(self, item_model):
        first, created = item_model.find_one_or_create(
            code="a", defaults={"name": "first"}
        )
        assert created is True

        second, created = item_model.find_one_or_create(
            code="a", defaults={"name": "second"}
        )

        assert created is False
        assert second.id == first.id
        assert second.name == "first", "defaults must not update an existing row"
        assert second is not first, "the existing row is read back from the database"
        assert item_model.query().count() == 1

    def test_lookup_wins_over_defaults(self, item_model):
        row, created = item_model.find_one_or_create(
            code="b", defaults={"code": "ignored", "name": "first"}
        )

        assert created is True
        assert row.code == "b"

    def test_multiple_lookup_fields_are_all_applied(self, item_model):
        row, created = item_model.find_one_or_create(
            code="c", alt_code="c-alt", defaults={"name": "first"}
        )

        assert created is True
        row2, created2 = item_model.find_one_or_create(
            code="c", alt_code="c-alt", defaults={"name": "second"}
        )
        assert created2 is False
        assert row2.id == row.id

    def test_empty_lookup_is_rejected(self, item_model):
        with pytest.raises(ValueError, match="at least one lookup field"):
            item_model.find_one_or_create()

    def test_unknown_lookup_field_is_rejected(self, item_model):
        with pytest.raises(TypeError, match="not a field"):
            item_model.find_one_or_create(nope=1)

    def test_unknown_defaults_field_is_rejected(self, item_model):
        with pytest.raises(TypeError, match="not a field"):
            item_model.find_one_or_create(code="a", defaults={"nope": 1})

    def test_none_lookup_value_is_rejected(self, item_model):
        with pytest.raises(ValueError, match="is None"):
            item_model.find_one_or_create(code=None)

    def test_expression_lookup_value_is_rejected(self, item_model):
        with pytest.raises(TypeError, match="expression"):
            item_model.find_one_or_create(code=_expression(item_model))

    def test_expression_defaults_value_is_rejected(self, item_model):
        with pytest.raises(TypeError, match="expression"):
            item_model.find_one_or_create(
                code="a", defaults={"name": _expression(item_model)}
            )

    def test_sql_with_params_lookup_value_is_rejected(self, item_model):
        with pytest.raises(TypeError, match="expression"):
            item_model.find_one_or_create(code=("code = ?", ("a",)))

    def test_generated_primary_key_in_lookup_is_rejected(self, item_model):
        with pytest.raises(ValueError, match="generates its primary key"):
            item_model.find_one_or_create(id=1, code="a")

    def test_generated_primary_key_in_defaults_is_rejected(self, item_model):
        with pytest.raises(ValueError, match="generates its primary key"):
            item_model.find_one_or_create(code="a", defaults={"id": 1})

    def test_conflict_reread_failure_keeps_the_cause(self, item_model, monkeypatch):
        original_lookup = item_model._find_one_by_lookup
        reads = []

        def failing_lookup(cls, lookup):
            reads.append(dict(lookup))
            if len(reads) == 1:
                return original_lookup(lookup)
            raise OperationalError("reread connection lost")

        monkeypatch.setattr(
            item_model, "_find_one_by_lookup", classmethod(failing_lookup)
        )

        def racing_save(self):
            raise IntegrityError("simulated concurrent insert")

        monkeypatch.setattr(item_model, "save", racing_save)

        with pytest.raises(IntegrityError) as info:
            item_model.find_one_or_create(
                code="race", defaults={"alt_code": "race-alt"}
            )

        assert isinstance(info.value.__cause__, OperationalError)
        assert "reread connection lost" in str(info.value.__cause__)
        assert item_model.query().count() == 0

    def test_savepoint_probe_failure_logs_error(self, item_model, monkeypatch):

        manager = item_model.backend().transaction_manager
        records = []

        def spy_log(cls, level, msg, *args, **kwargs):
            records.append((level, msg))

        monkeypatch.setattr(item_model, "log", classmethod(spy_log))

        def broken_probe():
            raise RuntimeError("capability probe exploded")

        monkeypatch.setattr(manager, "supports_savepoint", broken_probe)

        row, created = item_model.find_one_or_create(code="a")

        assert created is True
        assert row.code == "a"
        error_records = [item for item in records if item[0] == logging.ERROR]
        assert error_records, "a broken probe must be reported at ERROR level"
        assert "savepoint" in error_records[0][1].lower()

    def test_savepoint_unsupported_does_not_log_error(self, item_model, monkeypatch):

        manager = item_model.backend().transaction_manager
        records = []

        def spy_log(cls, level, msg, *args, **kwargs):
            records.append((level, msg))

        monkeypatch.setattr(item_model, "log", classmethod(spy_log))
        monkeypatch.setattr(manager, "supports_savepoint", lambda: False)

        row, created = item_model.find_one_or_create(code="a")

        assert created is True
        assert not [item for item in records if item[0] == logging.ERROR]

    def test_conflict_rereads_the_winner_once(self, item_model, monkeypatch):
        calls = []
        original_lookup = item_model._find_one_by_lookup

        def counting_lookup(cls, lookup):
            calls.append(dict(lookup))
            return original_lookup(lookup)

        monkeypatch.setattr(
            item_model, "_find_one_by_lookup", classmethod(counting_lookup)
        )

        original_save = item_model.save

        def racing_save(self):
            winner = item_model(
                code=self.code, alt_code=self.alt_code, name="winner"
            )
            original_save(winner)
            raise IntegrityError("simulated concurrent insert")

        monkeypatch.setattr(item_model, "save", racing_save)

        row, created = item_model.find_one_or_create(
            code="race", defaults={"name": "loser"}
        )

        assert created is False
        assert row.name == "winner"
        assert len(calls) == 2, "the method must re-read exactly once after a conflict"

    def test_conflict_without_matching_lookup_reraises(self, item_model):
        existing = item_model(code="taken", alt_code="taken-alt", name="old")
        existing.save()

        with pytest.raises(IntegrityError):
            item_model.find_one_or_create(
                code="brand-new", defaults={"alt_code": "taken-alt"}
            )

        assert item_model.query().count() == 1

    def test_does_not_open_a_transaction(self, item_model, monkeypatch):
        manager = item_model.backend().transaction_manager

        def forbidden(*args, **kwargs):
            raise AssertionError("find_one_or_create must not manage transactions")

        monkeypatch.setattr(manager, "begin", forbidden)
        monkeypatch.setattr(manager, "commit", forbidden)
        monkeypatch.setattr(manager, "rollback", forbidden)

        row, created = item_model.find_one_or_create(code="a")

        assert created is True
        assert manager.is_active is False
        assert manager.transaction_level == 0

    def test_no_savepoint_outside_a_transaction(self, item_model, monkeypatch):
        manager = item_model.backend().transaction_manager
        savepoints = []

        def spy_savepoint(name=None):
            savepoints.append(name)
            raise AssertionError("no savepoint outside a transaction")

        monkeypatch.setattr(manager, "savepoint", spy_savepoint)

        row, created = item_model.find_one_or_create(code="a")

        assert created is True
        assert savepoints == []

    def test_savepoint_is_used_inside_a_transaction(self, item_model, monkeypatch):
        manager = item_model.backend().transaction_manager
        events = []
        original_savepoint = manager.savepoint
        original_release = manager.release

        def spy_savepoint(name=None):
            name = original_savepoint(name)
            events.append(("savepoint", name))
            return name

        def spy_release(name):
            events.append(("release", name))
            return original_release(name)

        monkeypatch.setattr(manager, "savepoint", spy_savepoint)
        monkeypatch.setattr(manager, "release", spy_release)

        with item_model.transaction():
            row, created = item_model.find_one_or_create(code="a")
            assert created is True
            assert manager.is_active is True, "the outer transaction survives"

        assert [event[0] for event in events] == ["savepoint", "release"]
        assert manager.is_active is False

    def test_conflict_rolls_back_to_savepoint_and_keeps_transaction_usable(
        self, item_model, monkeypatch
    ):
        manager = item_model.backend().transaction_manager
        rollbacks = []
        original_rollback = manager.rollback_to

        def spy_rollback(name):
            rollbacks.append(name)
            return original_rollback(name)

        monkeypatch.setattr(manager, "rollback_to", spy_rollback)

        with item_model.transaction():
            item_model(code="taken", alt_code="taken-alt", name="old").save()

            with pytest.raises(IntegrityError):
                item_model.find_one_or_create(
                    code="brand-new", defaults={"alt_code": "taken-alt"}
                )

            assert rollbacks, "the failed insert must roll back to its savepoint"
            assert manager.is_active is True
            assert item_model.query().count() == 1, "the outer transaction is still usable"

