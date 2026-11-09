# tests/rhosocial/activerecord_test/feature/mixins/test_utc_timestamp.py
"""UtcTimestampMixin reads naive datetimes as UTC.

The mixin is field-level and backend-independent, so this module exercises
model construction and a SQLite round trip directly rather than through a
provider.  Sync and async classes share method names.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

import pytest

from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.backend.async_backend import AsyncSQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.field import (
    DefaultTimestampMixin,
    IntegerPKMixin,
    UtcTimestampMixin,
)
from rhosocial.activerecord.model import ActiveRecord, AsyncActiveRecord


class UtcEvent(UtcTimestampMixin, IntegerPKMixin, DefaultTimestampMixin, ActiveRecord):
    """Synchronous model exercising the optional UTC validator."""

    __table_name__ = "utc_events"

    id: Optional[int] = None
    name: str
    occurred_at: Optional[datetime] = None


class AsyncUtcEvent(
    UtcTimestampMixin, IntegerPKMixin, DefaultTimestampMixin, AsyncActiveRecord
):
    """Asynchronous twin with the same fields as UtcEvent."""

    __table_name__ = "utc_events"

    id: Optional[int] = None
    name: str
    occurred_at: Optional[datetime] = None


EVENTS_DDL = """
CREATE TABLE IF NOT EXISTS utc_events (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    occurred_at TEXT,
    created_at TEXT,
    updated_at TEXT
)
"""

NAIVE = datetime(2026, 1, 1, 12, 0, 0)
AWARE_OFFSET = timezone(timedelta(hours=8))
AWARE = datetime(2026, 1, 1, 12, 0, 0, tzinfo=AWARE_OFFSET)


@pytest.fixture
def utc_event_model():
    UtcEvent.configure(SQLiteConnectionConfig(database=":memory:"), SQLiteBackend)
    backend = UtcEvent.backend()
    backend.execute(EVENTS_DDL)
    yield UtcEvent
    backend.disconnect()
    UtcEvent.__backend__ = None


@pytest.fixture
async def async_utc_event_model():
    await AsyncUtcEvent.configure(
        SQLiteConnectionConfig(database=":memory:"), AsyncSQLiteBackend
    )
    backend = AsyncUtcEvent.backend()
    await backend.execute(EVENTS_DDL)
    yield AsyncUtcEvent
    await backend.disconnect()
    AsyncUtcEvent.__backend__ = None


class TestUtcTimestampMixin:
    """Synchronous behavior of UtcTimestampMixin."""

    def test_naive_datetime_is_read_as_utc(self):
        event = UtcEvent(name="deploy", occurred_at=NAIVE)

        assert event.occurred_at.tzinfo == timezone.utc
        assert event.occurred_at == NAIVE.replace(tzinfo=timezone.utc)

    def test_aware_datetime_keeps_its_offset(self):
        event = UtcEvent(name="deploy", occurred_at=AWARE)

        assert event.occurred_at == AWARE
        assert event.occurred_at.utcoffset() == timedelta(hours=8)

    def test_naive_string_is_parsed_as_utc(self):
        event = UtcEvent(name="deploy", occurred_at="2026-01-01 12:00:00")

        assert event.occurred_at.tzinfo == timezone.utc
        assert event.occurred_at == NAIVE.replace(tzinfo=timezone.utc)

    def test_non_datetime_fields_are_untouched(self):
        event = UtcEvent(name="deploy", occurred_at=NAIVE)

        assert event.name == "deploy"

    def test_optional_datetime_can_stay_none(self):
        event = UtcEvent(name="deploy")

        assert event.occurred_at is None

    def test_naive_value_compares_with_aware_clock(self):
        event = UtcEvent(name="deploy", occurred_at=NAIVE)
        now = datetime.now(timezone.utc)

        # A naive value would raise TypeError here; the mixin prevents that.
        assert event.occurred_at <= now

    def test_round_trip_keeps_utc(self, utc_event_model):
        event = utc_event_model(name="deploy", occurred_at=NAIVE)
        event.save()

        reloaded = utc_event_model.find_one(event.id)
        assert isinstance(reloaded.occurred_at, datetime)
        assert reloaded.occurred_at.tzinfo == timezone.utc
        assert reloaded.occurred_at == NAIVE.replace(tzinfo=timezone.utc)


class TestAsyncUtcTimestampMixin:
    """Asynchronous twin; method names match the synchronous class."""

    async def test_naive_datetime_is_read_as_utc(self):
        event = AsyncUtcEvent(name="deploy", occurred_at=NAIVE)

        assert event.occurred_at.tzinfo == timezone.utc
        assert event.occurred_at == NAIVE.replace(tzinfo=timezone.utc)

    async def test_aware_datetime_keeps_its_offset(self):
        event = AsyncUtcEvent(name="deploy", occurred_at=AWARE)

        assert event.occurred_at == AWARE
        assert event.occurred_at.utcoffset() == timedelta(hours=8)

    async def test_naive_string_is_parsed_as_utc(self):
        event = AsyncUtcEvent(name="deploy", occurred_at="2026-01-01 12:00:00")

        assert event.occurred_at.tzinfo == timezone.utc
        assert event.occurred_at == NAIVE.replace(tzinfo=timezone.utc)

    async def test_non_datetime_fields_are_untouched(self):
        event = AsyncUtcEvent(name="deploy", occurred_at=NAIVE)

        assert event.name == "deploy"

    async def test_optional_datetime_can_stay_none(self):
        event = AsyncUtcEvent(name="deploy")

        assert event.occurred_at is None

    async def test_naive_value_compares_with_aware_clock(self):
        event = AsyncUtcEvent(name="deploy", occurred_at=NAIVE)
        now = datetime.now(timezone.utc)

        assert event.occurred_at <= now

    async def test_round_trip_keeps_utc(self, async_utc_event_model):
        event = async_utc_event_model(name="deploy", occurred_at=NAIVE)
        await event.save()

        reloaded = await async_utc_event_model.find_one(event.id)
        assert isinstance(reloaded.occurred_at, datetime)
        assert reloaded.occurred_at.tzinfo == timezone.utc
        assert reloaded.occurred_at == NAIVE.replace(tzinfo=timezone.utc)
