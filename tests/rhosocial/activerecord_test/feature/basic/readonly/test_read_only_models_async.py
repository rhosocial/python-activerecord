# tests/rhosocial/activerecord_test/feature/basic/readonly/test_read_only_models_async.py
"""Async mirror of :mod:`test_read_only_models`.

``ReadOnlyMixin`` has no async variant because ``read_only()`` is a zero-I/O
predicate -- the ``field/`` convention is that an async twin is needed only when
a method issues SQL. This module exists to prove that: the same single mixin
gates every async write path.
"""

from datetime import datetime
from typing import ClassVar, Optional

import pytest

from rhosocial.activerecord.backend.errors import ReadOnlyError
from rhosocial.activerecord.base.field_proxy import FieldProxy
from rhosocial.activerecord.field import ReadOnlyMixin, SoftDeleteMixin, TimestampMixin
from rhosocial.activerecord.model import AsyncActiveRecord


class AsyncReadOnlyRecord(AsyncActiveRecord, ReadOnlyMixin):
    __table_name__ = "ar_readonly_records"
    c: ClassVar[FieldProxy] = FieldProxy()
    id: Optional[int] = None
    label: str = ""


class AsyncWritableRecord(AsyncActiveRecord):
    __table_name__ = "ar_writable_records"
    c: ClassVar[FieldProxy] = FieldProxy()
    id: Optional[int] = None
    label: str = ""


DDL = [
    "CREATE TABLE IF NOT EXISTS ar_readonly_records (id INTEGER PRIMARY KEY, label TEXT NOT NULL DEFAULT '')",
    "CREATE TABLE IF NOT EXISTS ar_writable_records (id INTEGER PRIMARY KEY, label TEXT NOT NULL DEFAULT '')",
]


@pytest.fixture
async def async_readonly_tables(async_user_class):
    """Create the tables and bind the models to the scenario backend."""
    backend = async_user_class.backend()
    for model in (AsyncReadOnlyRecord, AsyncWritableRecord):
        model.__backend__ = backend
    await backend.executescript("; ".join(DDL))
    yield backend


class TestAsyncDeclaration:
    def test_read_only_reports_true(self):
        assert AsyncReadOnlyRecord.read_only() is True

    def test_writable_model_does_not_answer(self):
        assert not hasattr(AsyncWritableRecord, "read_only")

    def test_interface_implementor_reporting_false_writes(self):
        class AsyncImplementsButWritable(AsyncActiveRecord, ReadOnlyMixin):
            __table_name__ = "ar_async_implements"
            c: ClassVar[FieldProxy] = FieldProxy()
            id: Optional[int] = None
            __read_only__ = False

        assert AsyncImplementsButWritable.read_only() is False
        AsyncImplementsButWritable.refuse_read_only("save")


class TestAsyncInstanceWritesAreRefused:
    async def test_save_raises(self, async_readonly_tables):
        with pytest.raises(ReadOnlyError, match="save is not allowed"):
            await AsyncReadOnlyRecord(label="x").save()

    async def test_delete_raises(self, async_readonly_tables):
        record = AsyncReadOnlyRecord(id=1, label="x")
        record._is_from_db = True
        with pytest.raises(ReadOnlyError, match="delete is not allowed"):
            await record.delete()


class TestAsyncClassLevelWritesAreRefused:
    async def test_bulk_create_raises(self, async_readonly_tables):
        with pytest.raises(ReadOnlyError, match="bulk_create"):
            await AsyncReadOnlyRecord.bulk_create([AsyncReadOnlyRecord(label="x")])

    async def test_bulk_update_raises(self, async_readonly_tables):
        with pytest.raises(ReadOnlyError, match="bulk_update"):
            await AsyncReadOnlyRecord.bulk_update([AsyncReadOnlyRecord(id=1, label="x")], ["label"])

    async def test_bulk_delete_raises(self, async_readonly_tables):
        with pytest.raises(ReadOnlyError, match="bulk_delete"):
            await AsyncReadOnlyRecord.bulk_delete([AsyncReadOnlyRecord(id=1, label="x")])

    async def test_update_all_raises(self, async_readonly_tables):
        query = AsyncReadOnlyRecord.query().where(AsyncReadOnlyRecord.c.id == 1)
        with pytest.raises(ReadOnlyError, match="update_all"):
            await query.update_all({"label": "y"})

    async def test_delete_all_raises(self, async_readonly_tables):
        query = AsyncReadOnlyRecord.query().where(AsyncReadOnlyRecord.c.id == 1)
        with pytest.raises(ReadOnlyError, match="delete_all"):
            await query.delete_all()


class TestAsyncReadsAreNeverRefused:
    async def test_query_works(self, async_readonly_tables):
        assert await AsyncReadOnlyRecord.query().all() == []

    async def test_count_works(self, async_readonly_tables):
        assert await AsyncReadOnlyRecord.query().count() == 0


class TestAsyncWritableControl:
    async def test_save_succeeds(self, async_readonly_tables):
        record = AsyncWritableRecord(label="hello")
        await record.save()
        assert record.id is not None

    async def test_delete_succeeds(self, async_readonly_tables):
        record = AsyncWritableRecord(label="bye")
        await record.save()
        await record.delete()

    async def test_bulk_create_succeeds(self, async_readonly_tables):
        await AsyncWritableRecord.bulk_create(
            [AsyncWritableRecord(label="a"), AsyncWritableRecord(label="b")]
        )


class TestAsyncMixinConflicts:
    def test_soft_delete_conflict_raises_at_class_definition(self):
        with pytest.raises(TypeError, match="read-only but also implements"):

            class Conflict(AsyncActiveRecord, ReadOnlyMixin, SoftDeleteMixin):
                __table_name__ = "ar_async_conflict_soft"
                c: ClassVar[FieldProxy] = FieldProxy()
                id: Optional[int] = None
                deleted_at: Optional[datetime] = None

    def test_timestamp_conflict_raises_at_class_definition(self):
        with pytest.raises(TypeError, match="read-only but also implements"):

            class Conflict(AsyncActiveRecord, ReadOnlyMixin, TimestampMixin):
                __table_name__ = "ar_async_conflict_ts"
                c: ClassVar[FieldProxy] = FieldProxy()
                id: Optional[int] = None
                created_at: Optional[datetime] = None
                updated_at: Optional[datetime] = None
