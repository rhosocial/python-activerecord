# tests/rhosocial/activerecord_test/feature/interface/test_partial_key_scope_warning.py
"""A query that leaves part of its key unconstrained is told so -- and not stopped.

The framework cannot fill the gap: no engine derives from the data which value
a missing key column should take, so a caller supplies it or reads wider than
one row. What it can do is say the difference aloud, and that is what these
tests pin -- the message appears in exactly the cases it should, and never in
the ones it should not.

No server: the warning is raised while the SQL is being built, so an
in-memory backend is enough to reach the code that raises it.
"""

from __future__ import annotations

import logging

try:
    from typing import Annotated, ClassVar, Optional
except ImportError:  # Python 3.8, where Annotated is still in typing_extensions
    from typing_extensions import Annotated
    from typing import ClassVar, Optional

import pytest

from rhosocial.activerecord.backend.impl.sqlite.backend import (
    AsyncSQLiteBackend,
    SQLiteBackend,
)
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteInMemoryConfig
from rhosocial.activerecord.base.ddl import IdentityAttribute
from rhosocial.activerecord.base.field_proxy import FieldProxy
from rhosocial.activerecord.base.fields import UseColumnAttributes
from rhosocial.activerecord.field.composite_pk import CompositePKMixin
from rhosocial.activerecord.model import ActiveRecord, AsyncActiveRecord


class _Capture(logging.Handler):
    """Collect what a model's logger says, whatever its propagate setting."""

    def __init__(self) -> None:
        super().__init__()
        self.messages: list = []

    def emit(self, record: logging.LogRecord) -> None:
        self.messages.append(record.getMessage())


class PartitionedLog(CompositePKMixin, ActiveRecord):
    """A partitioned log: surrogate generated, month supplied, job_id plain."""

    __table_name__ = "ct_job_logs_scope"
    __primary_key__ = ("id", "bucket")
    c: ClassVar[FieldProxy] = FieldProxy()

    id: Annotated[Optional[int], UseColumnAttributes(IdentityAttribute())] = None
    #: The supplied key field -- the one whose absence the warning reports.
    bucket: Optional[str] = None
    job_id: int = 0


class AsyncPartitionedLog(CompositePKMixin, AsyncActiveRecord):
    """The async twin, so both query classes are covered."""

    __table_name__ = "ct_job_logs_scope"
    __primary_key__ = ("id", "bucket")
    c: ClassVar[FieldProxy] = FieldProxy()

    id: Annotated[Optional[int], UseColumnAttributes(IdentityAttribute())] = None
    bucket: Optional[str] = None
    job_id: int = 0


class PlainModel(ActiveRecord):
    """An ordinary single-key model: nothing here can be partial."""

    __table_name__ = "ct_plain_scope"
    c: ClassVar[FieldProxy] = FieldProxy()

    id: Optional[int] = None
    name: str = ""


@pytest.fixture(autouse=True)
def captured():
    """Capture warnings from every model logger, and restore them after."""
    handler = _Capture()
    loggers = []
    for model in (PartitionedLog, AsyncPartitionedLog, PlainModel):
        logger = model.get_logger()
        logger.addHandler(handler)
        previous_level = logger.level
        logger.setLevel(logging.WARNING)
        loggers.append((logger, previous_level))
    yield handler
    for logger, previous_level in loggers:
        logger.removeHandler(handler)
        logger.setLevel(previous_level)


@pytest.fixture(scope="module", autouse=True)
def configured():
    """Bind all three models and create the tables they will be read from.

    The async twin's ``configure`` is a coroutine, so it needs a loop; this
    runs it the way a service would and then lets the backend go, because
    aiosqlite keeps worker threads that outlive a synchronous fixture.
    """
    import asyncio

    for model in (PartitionedLog, PlainModel):
        model.configure(SQLiteInMemoryConfig(), SQLiteBackend)
    loop = asyncio.new_event_loop()
    try:
        # The async twin takes the async backend, and its configure is a
        # coroutine -- neither mirror is usable with the other's.
        loop.run_until_complete(
            AsyncPartitionedLog.configure(SQLiteInMemoryConfig(), AsyncSQLiteBackend)
        )
    finally:
        loop.close()

    for model in (PartitionedLog, AsyncPartitionedLog, PlainModel):
        model.backend().execute(
            "CREATE TABLE IF NOT EXISTS %s (" % model.table_name()
            + ", ".join(
                (
                    "id INTEGER",
                    "bucket TEXT",
                    "job_id INTEGER",
                    "name TEXT",
                    "log_content TEXT",
                )
            )
            + ", PRIMARY KEY (id, bucket))"
        )
    yield
    # Only the async twin's disconnect is a coroutine; awaiting the sync
    # backend's would fail, and both were named here a moment ago.
    backend = AsyncPartitionedLog.__backend__
    if backend is not None:
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(backend.disconnect())
        finally:
            loop.close()


class TestTheWarningFires:
    def test_when_the_supplied_key_field_is_missing(self, captured):
        PartitionedLog.query().where(PartitionedLog.c.job_id == 7).to_sql()
        assert len(captured.messages) == 1
        assert "ct_job_logs_scope" in captured.messages[0]
        assert "bucket" in captured.messages[0]

    def test_and_says_what_the_query_will_match(self, captured):
        # The reader's mistake is thinking they wrote a row lookup, so the
        # message has to say how much is being matched.
        PartitionedLog.query().where(PartitionedLog.c.job_id == 7).to_sql()
        assert "every partition" in captured.messages[0]
        assert "not a row lookup" in captured.messages[0]

    def test_with_no_conditions_at_all(self, captured):
        PartitionedLog.query().to_sql()
        assert len(captured.messages) == 1
        assert "bucket" in captured.messages[0]

    def test_on_the_async_twin_as_well(self, captured):
        # Both query classes carry the same check, and this is what catches a
        # copy of it that was forgotten on one side.
        AsyncPartitionedLog.query().where(AsyncPartitionedLog.c.job_id == 7).to_sql()
        assert len(captured.messages) == 1
        assert "bucket" in captured.messages[0]


class TestTheWarningDoesNotFire:
    def test_when_every_key_field_is_constrained(self, captured):
        PartitionedLog.query().where(
            (PartitionedLog.c.job_id == 7) & (PartitionedLog.c.bucket == "202610")
        ).to_sql()
        assert captured.messages == []

    def test_when_the_key_field_is_constrained_by_an_in_list(self, captured):
        # The "give me these months" shape, which is a legitimate scoped read.
        PartitionedLog.query().where(
            (PartitionedLog.c.job_id == 7) & (PartitionedLog.c.bucket.in_(["202610", "202611"]))
        ).to_sql()
        assert captured.messages == []

    def test_when_the_key_field_alone_is_constrained(self, captured):
        # Reading one whole partition is the question the column is for.
        PartitionedLog.query().where(PartitionedLog.c.bucket == "202610").to_sql()
        assert captured.messages == []

    def test_on_a_single_key_model(self, captured):
        PlainModel.query().where(PlainModel.c.name == "x").to_sql()
        assert captured.messages == []

    def test_on_a_single_key_model_with_no_conditions(self, captured):
        PlainModel.query().to_sql()
        assert captured.messages == []


class TestQueryIsNotChanged:
    def test_the_sql_is_rendered_unchanged(self):
        # The warning is an observation, not a filter: it must not alter what
        # is asked, or a reader who ignores it still gets a different query.
        sql, params = PartitionedLog.query().where(PartitionedLog.c.job_id == 7).to_sql()
        assert "ct_job_logs_scope" in sql
        assert params

    def test_the_answer_is_returned_not_raised(self):
        # Nothing about a partial scope is an error.
        result = PartitionedLog.query().where(PartitionedLog.c.job_id == 7).all()
        assert result == []


class TestWalker:
    def test_sees_through_a_logical_combination(self):
        from rhosocial.activerecord.backend.expression.collect_columns import (
            referenced_columns,
        )

        query = PartitionedLog.query().where(
            (PartitionedLog.c.job_id == 7) & (PartitionedLog.c.bucket == "202610")
        )
        assert referenced_columns(query.where_clause) == {"job_id", "bucket"}

    def test_sees_through_an_in_predicate(self):
        from rhosocial.activerecord.backend.expression.collect_columns import (
            referenced_columns,
        )

        query = PartitionedLog.query().where(PartitionedLog.c.bucket.in_(["202610"]))
        assert referenced_columns(query.where_clause) == {"bucket"}

    def test_sees_through_a_null_test(self):
        from rhosocial.activerecord.backend.expression.collect_columns import (
            referenced_columns,
        )

        query = PartitionedLog.query().where(PartitionedLog.c.bucket.is_null())
        assert referenced_columns(query.where_clause) == {"bucket"}

    def test_and_through_both_sides_of_a_comparison(self):
        from rhosocial.activerecord.backend.expression.collect_columns import (
            referenced_columns,
        )

        query = PartitionedLog.query().where(PartitionedLog.c.job_id == PartitionedLog.c.job_id)
        assert referenced_columns(query.where_clause) == {"job_id"}
