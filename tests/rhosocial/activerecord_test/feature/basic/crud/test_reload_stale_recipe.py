# tests/rhosocial/activerecord_test/feature/basic/crud/test_reload_stale_recipe.py
"""``reload()``: the second half of the stale-record recipe.

A refused write means the server's row moved on. ``reload()`` takes those
values back into the same instance and re-points the optimistic lock at
them, so a retry is a retry of the change rather than a second conflict.
"""
from typing import ClassVar, Optional

from rhosocial.activerecord.backend.errors import RecordNotFound
from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.base import FieldProxy
from rhosocial.activerecord.field import OptimisticLockMixin
from rhosocial.activerecord.model import ActiveRecord, AsyncActiveRecord

import pytest


class LockedCounter(OptimisticLockMixin, ActiveRecord):
    @classmethod
    def table_name(cls):
        return "reload_counters"

    c: ClassVar[FieldProxy] = FieldProxy()

    id: Optional[int] = None
    name: str = ""
    value: int = 0
    version: int = 1


class KeylessNote(ActiveRecord):
    @classmethod
    def table_name(cls):
        return "reload_keyless"

    @classmethod
    def primary_key(cls):
        return None

    c: ClassVar[FieldProxy] = FieldProxy()

    body: str = ""


DDL = [
    'CREATE TABLE "reload_counters" ('
    '"id" INTEGER PRIMARY KEY AUTOINCREMENT, '
    '"name" TEXT NOT NULL DEFAULT \'\', '
    '"value" INTEGER NOT NULL DEFAULT 0, '
    '"version" INTEGER NOT NULL DEFAULT 1)',
]


@pytest.fixture
def counters(tmp_path):
    LockedCounter.configure(
        SQLiteConnectionConfig(database=str(tmp_path / "reload.db")), SQLiteBackend
    )
    backend = LockedCounter.backend()
    for statement in DDL:
        backend.execute(statement)
    return LockedCounter


class TestReload:
    def test_reload_takes_the_stored_values(self, counters):
        record = counters(name="c", value=1)
        record.save()

        # Another writer moves the row on.
        other = counters.find_one(record.id)
        other.value = 7
        other.save()

        record.value = 3
        record.reload()
        assert record.value == 7

    def test_reload_resets_change_tracking(self, counters):
        record = counters(name="c", value=1)
        record.save()
        record.value = 99
        assert record.is_dirty

        record.reload()
        assert not record.is_dirty
        assert record.value == 1

    def test_reload_refreshes_the_lock_snapshot(self, counters):
        record = counters(name="c", value=1)
        record.save()

        other = counters.find_one(record.id)
        other.value = 5
        other.save()

        # Without the refresh the next save would compare against the
        # pre-reload version and report a stale record that is not stale.
        record.reload()
        record.value = 6
        record.save()
        stored = counters.find_one(record.id)
        assert stored.value == 6

    def test_reload_without_a_key_value_is_refused(self, counters):
        with pytest.raises(ValueError, match="primary key"):
            counters(name="c").reload()

    def test_reload_of_a_deleted_row_raises(self, counters):
        record = counters(name="c", value=1)
        record.save()
        counters.find_one(record.id).delete()
        with pytest.raises(RecordNotFound):
            record.reload()

    def test_reload_on_a_keyless_model_is_unaddressable(self, tmp_path):
        from rhosocial.activerecord.backend.errors import UnaddressableRecordError

        KeylessNote.configure(
            SQLiteConnectionConfig(database=str(tmp_path / "keyless.db")), SQLiteBackend
        )
        KeylessNote.backend().execute(
            'CREATE TABLE "reload_keyless" ("body" TEXT NOT NULL DEFAULT \'\')'
        )
        with pytest.raises(UnaddressableRecordError, match="reload"):
            KeylessNote(body="x").reload()


class TestAsyncReload:
    @pytest.fixture
    async def async_counters(self, async_user_class):
        backend = async_user_class.backend()
        AsyncLockedCounter.__backend__ = backend
        await backend.execute('DROP TABLE IF EXISTS "reload_counters"')
        await backend.executescript("; ".join(DDL))
        yield AsyncLockedCounter
        await backend.execute('DROP TABLE IF EXISTS "reload_counters"')

    @pytest.mark.asyncio
    async def test_async_reload_takes_the_stored_values(self, async_counters):
        record = async_counters(name="c", value=1)
        await record.save()

        other = await async_counters.find_one(record.id)
        other.value = 7
        await other.save()

        record.value = 3
        await record.reload()
        assert record.value == 7

    @pytest.mark.asyncio
    async def test_async_reload_resets_change_tracking(self, async_counters):
        record = async_counters(name="c", value=1)
        await record.save()
        record.value = 99
        assert record.is_dirty

        await record.reload()
        assert not record.is_dirty
        assert record.value == 1



class AsyncLockedCounter(OptimisticLockMixin, AsyncActiveRecord):
    @classmethod
    def table_name(cls):
        return "reload_counters"

    c: ClassVar[FieldProxy] = FieldProxy()

    id: Optional[int] = None
    name: str = ""
    value: int = 0
    version: int = 1
