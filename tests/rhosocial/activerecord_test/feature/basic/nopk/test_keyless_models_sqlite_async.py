# tests/rhosocial/activerecord_test/feature/basic/nopk/test_keyless_models_async.py
"""Async mirror of :mod:`test_keyless_models`.

``__primary_key__ = None`` is a model declaration, not an async concern, so the
same decision points answer for both families. This module pins that an async
keyless model keeps its reads and loses only identity-based access.
"""

from typing import ClassVar, Optional

import pytest

from rhosocial.activerecord.backend.errors import (
    DatabaseError,
    ReadOnlyError,
    UnaddressableRecordError,
)
from rhosocial.activerecord.base.field_proxy import FieldProxy
from rhosocial.activerecord.field import ReadOnlyMixin
from rhosocial.activerecord.model import AsyncActiveRecord


class AsyncKeylessLog(AsyncActiveRecord):
    __table_name__ = "ro_keyless_log"
    c: ClassVar[FieldProxy] = FieldProxy()
    __primary_key__ = None
    event: str = ""
    level: str = ""


class AsyncKeylessReadOnly(AsyncActiveRecord, ReadOnlyMixin):
    __table_name__ = "ro_keyless_readonly"
    c: ClassVar[FieldProxy] = FieldProxy()
    __primary_key__ = None
    event: str = ""


class AsyncNormalModel(AsyncActiveRecord):
    __table_name__ = "ro_normal_model"
    c: ClassVar[FieldProxy] = FieldProxy()
    id: Optional[int] = None
    event: str = ""


DDL = [
    "DROP TABLE IF EXISTS ro_keyless_log",
    "CREATE TABLE ro_keyless_log (event TEXT NOT NULL DEFAULT '', level TEXT NOT NULL DEFAULT '')",
    "DROP TABLE IF EXISTS ro_keyless_readonly",
    "CREATE TABLE ro_keyless_readonly (event TEXT NOT NULL DEFAULT '')",
    "DROP TABLE IF EXISTS ro_normal_model",
    "CREATE TABLE ro_normal_model (id INTEGER PRIMARY KEY, event TEXT NOT NULL DEFAULT '')",
]


@pytest.fixture
async def async_keyless_tables(async_user_class):
    backend = async_user_class.backend()
    for model in (AsyncKeylessLog, AsyncKeylessReadOnly, AsyncNormalModel):
        model.__backend__ = backend
    await backend.executescript("; ".join(DDL))
    yield backend


class TestAsyncDeclaration:
    def test_none_is_an_accepted_declaration(self):
        assert AsyncKeylessLog.primary_key() is None

    def test_addressable_reports_false(self):
        assert AsyncKeylessLog.addressable() is False

    def test_key_columns_are_empty_not_none(self):
        assert AsyncKeylessLog.primary_key_columns() == ()
        assert AsyncKeylessLog.primary_key_fields() == ()

    def test_normal_model_is_unchanged(self):
        assert AsyncNormalModel.addressable() is True
        assert AsyncNormalModel.primary_key_columns() == ("id",)


class TestAsyncIsNewRecord:
    def test_a_constructed_record_is_new(self):
        assert AsyncKeylessLog(event="x").is_new_record is True

    async def test_a_row_loaded_from_the_database_is_not_new(self, async_keyless_tables):
        async_keyless_tables
        await AsyncKeylessLog(event="a", level="info").save()
        loaded = await AsyncKeylessLog.query().where(AsyncKeylessLog.c.event == "a").one()
        assert loaded is not None
        assert loaded.is_new_record is False


class TestAsyncQueriesKeepWorking:
    async def test_save_and_all(self, async_keyless_tables):
        async_keyless_tables
        await AsyncKeylessLog(event="a", level="info").save()
        await AsyncKeylessLog(event="b", level="warn").save()
        rows = await AsyncKeylessLog.query().order_by(AsyncKeylessLog.c.event).all()
        assert [r.event for r in rows] == ["a", "b"]

    async def test_count(self, async_keyless_tables):
        async_keyless_tables
        await AsyncKeylessLog(event="a").save()
        assert await AsyncKeylessLog.query().count() == 1

    async def test_where(self, async_keyless_tables):
        async_keyless_tables
        await AsyncKeylessLog(event="a", level="info").save()
        await AsyncKeylessLog(event="b", level="warn").save()
        rows = await AsyncKeylessLog.query().where(AsyncKeylessLog.c.level == "warn").all()
        assert [r.event for r in rows] == ["b"]

    async def test_bulk_create(self, async_keyless_tables):
        async_keyless_tables
        records = await AsyncKeylessLog.bulk_create(
            [AsyncKeylessLog(event="a", level="info"), AsyncKeylessLog(event="b", level="warn")]
        )
        assert len(records) == 2
        assert await AsyncKeylessLog.query().count() == 2


class TestAsyncKeylessBulkIdentityIsRefused:
    async def test_bulk_update_refused(self, async_keyless_tables):
        async_keyless_tables
        with pytest.raises(UnaddressableRecordError, match="bulk_update"):
            await AsyncKeylessLog.bulk_update([AsyncKeylessLog(event="a")], ["level"])

    async def test_bulk_delete_refused(self, async_keyless_tables):
        async_keyless_tables
        with pytest.raises(UnaddressableRecordError, match="bulk_delete"):
            await AsyncKeylessLog.bulk_delete([AsyncKeylessLog(event="a")])


class TestAsyncIdentityAccessIsRefused:
    async def test_find_one_by_value(self, async_keyless_tables):
        async_keyless_tables
        with pytest.raises(UnaddressableRecordError, match="find_one"):
            await AsyncKeylessLog.find_one(1)

    async def test_find_all_by_value_list(self, async_keyless_tables):
        async_keyless_tables
        with pytest.raises(UnaddressableRecordError, match="find_all"):
            await AsyncKeylessLog.find_all([1, 2])

    async def test_refresh(self, async_keyless_tables):
        async_keyless_tables
        with pytest.raises(UnaddressableRecordError, match="refresh"):
            await AsyncKeylessLog(event="x").refresh()

    def test_the_error_is_a_database_error(self):
        assert issubclass(UnaddressableRecordError, DatabaseError)


class TestAsyncNonIdentityConditionsStillWork:
    async def test_find_one_with_a_dict(self, async_keyless_tables):
        async_keyless_tables
        await AsyncKeylessLog(event="a", level="info").save()
        found = await AsyncKeylessLog.find_one({"event": "a"})
        assert found is not None and found.event == "a"

    async def test_find_all_with_no_condition(self, async_keyless_tables):
        async_keyless_tables
        await AsyncKeylessLog(event="a").save()
        assert len(await AsyncKeylessLog.find_all()) == 1


class TestAsyncOrthogonality:
    async def test_keyless_read_only_refuses_writes(self, async_keyless_tables):
        async_keyless_tables
        assert AsyncKeylessReadOnly.addressable() is False
        assert AsyncKeylessReadOnly.read_only() is True
        with pytest.raises(ReadOnlyError):
            await AsyncKeylessReadOnly(event="x").save()

    async def test_addressable_model_is_unaffected(self, async_keyless_tables):
        async_keyless_tables
        record = AsyncNormalModel(event="fine")
        await record.save()
        assert record.id is not None
        assert await AsyncNormalModel.find_one(record.id) is not None
