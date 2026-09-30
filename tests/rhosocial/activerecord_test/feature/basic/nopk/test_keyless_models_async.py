# tests/rhosocial/activerecord_test/feature/basic/nopk/test_keyless_models_async.py
"""Async mirror of :mod:`test_keyless_models`.

Same contract on the async model family: ``__primary_key__ = None`` is a
declared shape, ``addressable()`` is the single decision point, and every
identity operation raises ``UnaddressableRecordError`` rather than leaking a
``TypeError``.
"""

from typing import ClassVar, Optional

import pytest

from rhosocial.activerecord.backend.errors import DatabaseError, ReadOnlyError, UnaddressableRecordError
from rhosocial.activerecord.base.field_proxy import FieldProxy
from rhosocial.activerecord.field import ReadOnlyMixin
from rhosocial.activerecord.model import AsyncActiveRecord


class AsyncKeylessLog(AsyncActiveRecord):
    __table_name__ = "ar_keyless_log"
    c: ClassVar[FieldProxy] = FieldProxy()
    __primary_key__ = None
    event: str = ""
    level: str = ""


class AsyncKeylessReadOnly(AsyncActiveRecord, ReadOnlyMixin):
    __table_name__ = "ar_keyless_readonly"
    c: ClassVar[FieldProxy] = FieldProxy()
    __primary_key__ = None
    event: str = ""


class AsyncReadOnlyWithKey(AsyncActiveRecord, ReadOnlyMixin):
    __table_name__ = "ar_readonly_with_key"
    c: ClassVar[FieldProxy] = FieldProxy()
    id: Optional[int] = None
    event: str = ""


class AsyncNormalModel(AsyncActiveRecord):
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
async def async_keyless_tables(async_user_class):
    """Create the tables and bind the models to the scenario backend."""
    backend = async_user_class.backend()
    for model in (AsyncKeylessLog, AsyncKeylessReadOnly, AsyncReadOnlyWithKey, AsyncNormalModel):
        model.__backend__ = backend
    await backend.executescript("; ".join(DDL))
    yield backend


class TestDeclaration:
    def test_none_is_an_accepted_declaration(self):
        assert AsyncKeylessLog.primary_key() is None

    def test_addressable_reports_false(self):
        assert AsyncKeylessLog.addressable() is False

    def test_addressable_reports_true_for_a_normal_model(self):
        assert AsyncNormalModel.addressable() is True

    def test_key_columns_are_empty_not_none(self):
        assert AsyncKeylessLog.primary_key_columns() == ()
        assert AsyncKeylessLog.primary_key_fields() == ()

    def test_key_columns_never_contain_none(self):
        for model in (AsyncKeylessLog, AsyncKeylessReadOnly, AsyncReadOnlyWithKey, AsyncNormalModel):
            assert None not in model.primary_key_columns(), model.__name__
            assert None not in model.primary_key_fields(), model.__name__

    def test_is_composite_pk_is_false(self):
        assert AsyncKeylessLog.is_composite_pk() is False


class TestIsNewRecord:
    def test_a_constructed_record_is_new(self):
        assert AsyncKeylessLog(event="x").is_new_record is True

    async def test_a_row_loaded_from_the_database_is_not_new(self, async_keyless_tables):
        await AsyncKeylessLog(event="a", level="info").save()
        loaded = await AsyncKeylessLog.query().where(AsyncKeylessLog.c.event == "a").one()
        assert loaded is not None
        assert loaded.is_new_record is False

    async def test_addressable_models_still_decide_by_the_key(self, async_keyless_tables):
        assert AsyncNormalModel().is_new_record is True
        record = AsyncNormalModel(event="x")
        await record.save()
        assert record.is_new_record is False


class TestQueriesKeepWorking:
    async def test_save_and_all(self, async_keyless_tables):
        await AsyncKeylessLog(event="a", level="info").save()
        await AsyncKeylessLog(event="b", level="warn").save()
        rows = await AsyncKeylessLog.query().order_by(AsyncKeylessLog.c.event).all()
        assert [r.event for r in rows] == ["a", "b"]

    async def test_where(self, async_keyless_tables):
        await AsyncKeylessLog(event="a", level="info").save()
        await AsyncKeylessLog(event="b", level="warn").save()
        rows = await AsyncKeylessLog.query().where(AsyncKeylessLog.c.level == "warn").all()
        assert [r.event for r in rows] == ["b"]

    async def test_count_and_exists(self, async_keyless_tables):
        await AsyncKeylessLog(event="a").save()
        assert await AsyncKeylessLog.query().count() == 1
        assert await AsyncKeylessLog.query().where(AsyncKeylessLog.c.event == "a").exists() is True

    async def test_aggregate(self, async_keyless_tables):
        await AsyncKeylessLog(event="a").save()
        rows = await AsyncKeylessLog.query().select(AsyncKeylessLog.c.event).aggregate()
        assert [r["event"] for r in rows] == ["a"]

    async def test_limit_and_order_by(self, async_keyless_tables):
        await AsyncKeylessLog(event="a").save()
        await AsyncKeylessLog(event="b").save()
        rows = await AsyncKeylessLog.query().order_by(AsyncKeylessLog.c.event).limit(1).all()
        assert [r.event for r in rows] == ["a"]


class TestIdentityAccessIsRefused:
    async def test_find_one_by_value(self, async_keyless_tables):
        with pytest.raises(UnaddressableRecordError, match="find_one"):
            await AsyncKeylessLog.find_one(1)

    async def test_find_all_by_value_list(self, async_keyless_tables):
        with pytest.raises(UnaddressableRecordError, match="find_all"):
            await AsyncKeylessLog.find_all([1, 2])

    async def test_refresh(self, async_keyless_tables):
        with pytest.raises(UnaddressableRecordError, match="refresh"):
            await AsyncKeylessLog(event="x").refresh()

    async def test_get_pk_value(self, async_keyless_tables):
        with pytest.raises(UnaddressableRecordError, match="primary key value"):
            AsyncKeylessLog(event="x")._get_pk_value()

    async def test_build_pk_where_predicate(self, async_keyless_tables):
        with pytest.raises(UnaddressableRecordError, match="primary key predicate"):
            AsyncKeylessLog._build_pk_where_predicate(1)

    async def test_the_error_names_model_and_operation(self, async_keyless_tables):
        with pytest.raises(UnaddressableRecordError) as excinfo:
            await AsyncKeylessLog.find_one(1)
        assert excinfo.value.model_name == "AsyncKeylessLog"
        assert excinfo.value.operation == "find_one"

    def test_the_error_is_a_database_error(self):
        assert issubclass(UnaddressableRecordError, DatabaseError)


class TestNonIdentityConditionsStillWork:
    async def test_find_one_with_a_dict(self, async_keyless_tables):
        await AsyncKeylessLog(event="a", level="info").save()
        found = await AsyncKeylessLog.find_one({"event": "a"})
        assert found is not None and found.event == "a"

    async def test_find_all_with_no_condition(self, async_keyless_tables):
        await AsyncKeylessLog(event="a").save()
        assert len(await AsyncKeylessLog.find_all()) == 1

    async def test_find_one_with_a_predicate(self, async_keyless_tables):
        await AsyncKeylessLog(event="a").save()
        found = await AsyncKeylessLog.find_one(AsyncKeylessLog.c.event == "a")
        assert found is not None


class TestOrthogonality:
    def test_keyless_and_read_only_together(self, async_keyless_tables):
        assert AsyncKeylessReadOnly.addressable() is False
        assert AsyncKeylessReadOnly.read_only() is True

    async def test_keyless_read_only_refuses_writes(self, async_keyless_tables):
        with pytest.raises(ReadOnlyError):
            await AsyncKeylessReadOnly(event="x").save()

    def test_read_only_but_addressable(self, async_keyless_tables):
        assert AsyncReadOnlyWithKey.addressable() is True
        assert AsyncReadOnlyWithKey.read_only() is True

    async def test_read_only_with_a_key_still_refuses_by_identity(self, async_keyless_tables):
        with pytest.raises(ReadOnlyError):
            await AsyncReadOnlyWithKey(event="x").save()

    async def test_addressable_model_is_unaffected(self, async_keyless_tables):
        record = AsyncNormalModel(event="fine")
        await record.save()
        assert record.id is not None
        assert await AsyncNormalModel.find_one(record.id) is not None
