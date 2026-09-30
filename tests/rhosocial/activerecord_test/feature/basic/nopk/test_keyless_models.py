# tests/rhosocial/activerecord_test/feature/basic/nopk/test_keyless_models.py
"""Keyless models: ``__primary_key__ = None`` is a declared, supported shape.

A relation with no unique single-row key is real -- an insert-only audit log,
an aggregate projection -- and pretending otherwise produced failures that read
as accidents: ``primary_key_columns()`` returned ``(None,)``, and every
identity operation raised ``TypeError: attribute name must be string, not
'NoneType'``.

The rule this module pins:

* ``addressable()`` is the single decision point, and False means only that
  identity-based access is unavailable.
* Queries, ordering, grouping, aggregation, counting, ``pluck`` and relations
  keep working, because none of them needs identity.
* Identity-based access raises ``UnaddressableRecordError`` naming the model and
  the operation, instead of leaking a ``TypeError`` from ``getattr``.
* Keyless-ness is orthogonal to read-only-ness in both directions.

``is_new_record`` has a real decision to make here: with no key there is no
identity to inspect, so provenance decides -- a row loaded from the database is
not new, anything built in Python is.
"""

from typing import ClassVar, Optional

import pytest

from rhosocial.activerecord.backend.errors import DatabaseError, UnaddressableRecordError
from rhosocial.activerecord.base.field_proxy import FieldProxy
from rhosocial.activerecord.field import ReadOnlyMixin
from rhosocial.activerecord.model import ActiveRecord


class KeylessLog(ActiveRecord):
    """Insert-only table: no primary key at all."""
    __table_name__ = "ar_keyless_log"
    c: ClassVar[FieldProxy] = FieldProxy()
    __primary_key__ = None
    event: str = ""
    level: str = ""


class KeylessReadOnly(ActiveRecord, ReadOnlyMixin):
    """Keyless *and* read-only -- the two dimensions do not interact."""
    __table_name__ = "ar_keyless_readonly"
    c: ClassVar[FieldProxy] = FieldProxy()
    __primary_key__ = None
    event: str = ""


class ReadOnlyWithKey(ActiveRecord, ReadOnlyMixin):
    """Read-only but addressable -- the other direction."""
    __table_name__ = "ar_readonly_with_key"
    c: ClassVar[FieldProxy] = FieldProxy()
    id: Optional[int] = None
    event: str = ""


class NormalModel(ActiveRecord):
    """Control: an ordinary addressable, writable model."""
    __table_name__ = "ar_normal_model"
    c: ClassVar[FieldProxy] = FieldProxy()
    id: Optional[int] = None
    event: str = ""


DDL = [
    "CREATE TABLE IF NOT EXISTS ar_keyless_log (event TEXT NOT NULL DEFAULT '', level TEXT NOT NULL DEFAULT '')",
    "CREATE TABLE IF NOT EXISTS ar_keyless_readonly (event TEXT NOT NULL DEFAULT '')",
    "CREATE TABLE IF NOT EXISTS ar_readonly_with_key (id INTEGER PRIMARY KEY, event TEXT NOT NULL DEFAULT '')",
    "CREATE TABLE IF NOT EXISTS ar_normal_model (id INTEGER PRIMARY KEY, event TEXT NOT NULL DEFAULT '')",
]


@pytest.fixture
def keyless_tables(user_class):
    """Create the tables and bind the models to the scenario backend."""
    backend = user_class.backend()
    for model in (KeylessLog, KeylessReadOnly, ReadOnlyWithKey, NormalModel):
        model.__backend__ = backend
    cursor = backend.connection.cursor()
    for statement in DDL:
        cursor.execute(statement)
    backend.connection.commit()
    cursor.close()
    yield backend


class TestDeclaration:
    def test_none_is_an_accepted_declaration(self):
        assert KeylessLog.primary_key() is None

    def test_addressable_reports_false(self):
        assert KeylessLog.addressable() is False

    def test_addressable_reports_true_for_a_normal_model(self):
        assert NormalModel.addressable() is True

    def test_key_columns_are_empty_not_none(self):
        """Empty, so callers can iterate unconditionally."""
        assert KeylessLog.primary_key_columns() == ()
        assert KeylessLog.primary_key_fields() == ()

    def test_key_columns_never_contain_none(self):
        for model in (KeylessLog, KeylessReadOnly, ReadOnlyWithKey, NormalModel):
            assert None not in model.primary_key_columns(), model.__name__
            assert None not in model.primary_key_fields(), model.__name__

    def test_is_composite_pk_is_false(self):
        """None is not a composite key."""
        assert KeylessLog.is_composite_pk() is False

    def test_normal_model_is_unchanged(self):
        assert NormalModel.primary_key_columns() == ("id",)
        assert NormalModel.primary_key_fields() == ("id",)


class TestIsNewRecord:
    def test_a_constructed_record_is_new(self):
        assert KeylessLog(event="x").is_new_record is True

    def test_a_row_loaded_from_the_database_is_not_new(self, keyless_tables):
        KeylessLog(event="a", level="info").save()
        loaded = KeylessLog.query().where(KeylessLog.c.event == "a").one()
        assert loaded is not None
        assert loaded.is_new_record is False

    def test_addressable_models_still_decide_by_the_key(self, keyless_tables):
        assert NormalModel().is_new_record is True
        record = NormalModel(event="x")
        record.save()
        assert record.is_new_record is False


class TestQueriesKeepWorking:
    """None of these need identity, so none of them are affected."""

    def test_save_and_all(self, keyless_tables):
        KeylessLog(event="a", level="info").save()
        KeylessLog(event="b", level="warn").save()
        rows = KeylessLog.query().order_by(KeylessLog.c.event).all()
        assert [r.event for r in rows] == ["a", "b"]

    def test_where(self, keyless_tables):
        KeylessLog(event="a", level="info").save()
        KeylessLog(event="b", level="warn").save()
        rows = KeylessLog.query().where(KeylessLog.c.level == "warn").all()
        assert [r.event for r in rows] == ["b"]

    def test_count(self, keyless_tables):
        KeylessLog(event="a").save()
        assert KeylessLog.query().count() == 1

    def test_aggregate(self, keyless_tables):
        KeylessLog(event="a").save()
        rows = KeylessLog.query().select(KeylessLog.c.event).aggregate()
        assert [r["event"] for r in rows] == ["a"]

    def test_one(self, keyless_tables):
        KeylessLog(event="only").save()
        assert KeylessLog.query().where(KeylessLog.c.event == "only").one().event == "only"

    def test_limit_and_order_by(self, keyless_tables):
        KeylessLog(event="a").save()
        KeylessLog(event="b").save()
        rows = KeylessLog.query().order_by(KeylessLog.c.event).limit(1).all()
        assert [r.event for r in rows] == ["a"]

    def test_exists_and_count(self, keyless_tables):
        KeylessLog(event="a").save()
        assert KeylessLog.query().where(KeylessLog.c.event == "a").exists() is True
        assert KeylessLog.query().where(KeylessLog.c.event == "zz").exists() is False


class TestIdentityAccessIsRefused:
    def test_find_one_by_value(self, keyless_tables):
        with pytest.raises(UnaddressableRecordError, match="find_one"):
            KeylessLog.find_one(1)

    def test_find_all_by_value_list(self, keyless_tables):
        with pytest.raises(UnaddressableRecordError, match="find_all"):
            KeylessLog.find_all([1, 2])

    def test_refresh(self, keyless_tables):
        with pytest.raises(UnaddressableRecordError, match="refresh"):
            KeylessLog(event="x").refresh()

    def test_get_pk_value(self, keyless_tables):
        with pytest.raises(UnaddressableRecordError, match="primary key value"):
            KeylessLog(event="x")._get_pk_value()

    def test_build_pk_where_predicate(self, keyless_tables):
        with pytest.raises(UnaddressableRecordError, match="primary key predicate"):
            KeylessLog._build_pk_where_predicate(1)

    def test_the_error_names_model_and_operation(self, keyless_tables):
        with pytest.raises(UnaddressableRecordError) as excinfo:
            KeylessLog.find_one(1)
        assert excinfo.value.model_name == "KeylessLog"
        assert excinfo.value.operation == "find_one"

    def test_the_error_is_a_database_error(self):
        """So existing `except DatabaseError` handlers keep working."""
        assert issubclass(UnaddressableRecordError, DatabaseError)

    def test_the_error_suggests_the_alternative(self, keyless_tables):
        with pytest.raises(UnaddressableRecordError) as excinfo:
            KeylessLog.find_one(1)
        assert "where(...)" in str(excinfo.value)


class TestNonIdentityConditionsStillWork:
    """Only bare-key conditions are refused, not every condition."""

    def test_find_one_with_a_dict(self, keyless_tables):
        KeylessLog(event="a", level="info").save()
        found = KeylessLog.find_one({"event": "a"})
        assert found is not None and found.event == "a"

    def test_find_all_with_no_condition(self, keyless_tables):
        KeylessLog(event="a").save()
        assert len(KeylessLog.find_all()) == 1

    def test_find_one_with_a_predicate(self, keyless_tables):
        KeylessLog(event="a").save()
        found = KeylessLog.find_one(KeylessLog.c.event == "a")
        assert found is not None

    def test_find_all_with_a_dict(self, keyless_tables):
        KeylessLog(event="a", level="info").save()
        KeylessLog(event="b", level="warn").save()
        assert len(KeylessLog.find_all({"level": "warn"})) == 1


class TestOrthogonality:
    def test_keyless_and_read_only_together(self, keyless_tables):
        assert KeylessReadOnly.addressable() is False
        assert KeylessReadOnly.read_only() is True

    def test_keyless_read_only_refuses_writes(self, keyless_tables):
        from rhosocial.activerecord.backend.errors import ReadOnlyError

        with pytest.raises(ReadOnlyError):
            KeylessReadOnly(event="x").save()

    def test_read_only_but_addressable(self, keyless_tables):
        assert ReadOnlyWithKey.addressable() is True
        assert ReadOnlyWithKey.read_only() is True

    def test_read_only_with_a_key_still_refuses_by_identity(self, keyless_tables):
        """The gate order matters: read-only wins, and says so."""
        from rhosocial.activerecord.backend.errors import ReadOnlyError

        with pytest.raises(ReadOnlyError):
            ReadOnlyWithKey(event="x").save()

    def test_addressable_model_is_unaffected(self, keyless_tables):
        record = NormalModel(event="fine")
        record.save()
        assert record.id is not None
        assert NormalModel.find_one(record.id) is not None
