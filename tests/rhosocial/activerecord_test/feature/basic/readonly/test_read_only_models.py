# tests/rhosocial/activerecord_test/feature/basic/readonly/test_read_only_models.py
"""Read-only models refuse writes, and refuse them before any SQL is issued.

``ReadOnlyMixin`` is opt-in and orthogonal: read-only-ness is a static
declaration independent of the primary key and of the physical object the model
maps. A read-only table may have an auto-generated key, and a keyless table may
be writable.

The load-bearing assertion in this module is the **zero-SQL** one: a refused
write must raise ``ReadOnlyError`` without the backend ever seeing a statement.
A gate placed after statement construction would still pass a "does it raise?"
test while leaving the database half-written.
"""

from datetime import datetime
from typing import ClassVar, Optional

import pytest

from rhosocial.activerecord.backend.errors import ReadOnlyError
from rhosocial.activerecord.base.field_proxy import FieldProxy
from rhosocial.activerecord.field import ReadOnlyMixin, SoftDeleteMixin, TimestampMixin
from rhosocial.activerecord.interface import IReadOnlyBehavior
from rhosocial.activerecord.model import ActiveRecord


class ReadOnlyRecord(ActiveRecord, ReadOnlyMixin):
    c: ClassVar[FieldProxy] = FieldProxy()
    __table_name__ = "ar_readonly_records"
    id: Optional[int] = None
    label: str = ""


class WritableRecord(ActiveRecord):
    c: ClassVar[FieldProxy] = FieldProxy()
    __table_name__ = "ar_writable_records"
    id: Optional[int] = None
    label: str = ""


class OptedOutRecord(ActiveRecord, ReadOnlyMixin):
    """Declares the mixin but turns the flag off explicitly."""
    c: ClassVar[FieldProxy] = FieldProxy()
    __table_name__ = "ar_optedout_records"
    id: Optional[int] = None
    label: str = ""
    __read_only__ = False


class ImplementsButWritable(ActiveRecord, IReadOnlyBehavior):
    """Satisfies the interface without being read-only.

    This is the case that makes a type test the wrong gate: membership in
    ``IReadOnlyBehavior`` says a ``read_only`` method exists, not that the model
    is read-only.
    """

    c: ClassVar[FieldProxy] = FieldProxy()
    __table_name__ = "ar_implements_writable"
    id: Optional[int] = None
    label: str = ""


DDL = [
    "CREATE TABLE IF NOT EXISTS ar_readonly_records (id INTEGER PRIMARY KEY, label TEXT NOT NULL DEFAULT '')",
    "CREATE TABLE IF NOT EXISTS ar_writable_records (id INTEGER PRIMARY KEY, label TEXT NOT NULL DEFAULT '')",
    "CREATE TABLE IF NOT EXISTS ar_optedout_records (id INTEGER PRIMARY KEY, label TEXT NOT NULL DEFAULT '')",
    "CREATE TABLE IF NOT EXISTS ar_implements_writable (id INTEGER PRIMARY KEY, label TEXT NOT NULL DEFAULT '')",
]


class SqlTrace:
    """Counts every statement the driver prepares on one connection.

    Uses ``sqlite3.Connection.set_trace_callback`` rather than wrapping a
    cursor: the backend opens its own cursors internally, so a wrapped cursor
    would only ever see the statements the test issued by hand and would
    report zero for a write that had in fact been sent. The driver-level
    callback sees them all, which is what "no SQL was issued" has to mean.
    """

    def __init__(self, connection):
        self._connection = connection
        self.statements: list[str] = []
        # Appends into the list captured here, so it must be cleared in place:
        # rebinding the attribute would leave the callback writing to a list
        # nobody reads any more.
        connection.set_trace_callback(self.statements.append)

    def take(self):
        """Return the statements recorded since the last call and reset."""
        seen = list(self.statements)
        del self.statements[:]
        return seen

    def stop(self):
        self._connection.set_trace_callback(None)


@pytest.fixture
def readonly_tables(user_class):
    """Create the tables, bind the models, and yield a driver-level SQL trace."""
    backend = user_class.backend()
    for model in (ReadOnlyRecord, WritableRecord, OptedOutRecord, ImplementsButWritable):
        model.__backend__ = backend
    cursor = backend.connection.cursor()
    for statement in DDL:
        cursor.execute(statement)
    backend.connection.commit()
    cursor.close()

    trace = SqlTrace(backend.connection)
    trace.take()  # discard the DDL above
    yield backend, trace
    trace.stop()


class TestReadOnlyDeclaration:
    """The declaration, not a type test, decides."""

    def test_mixin_satisfies_the_interface(self):
        assert issubclass(ReadOnlyMixin, IReadOnlyBehavior)
        assert issubclass(ReadOnlyRecord, IReadOnlyBehavior)

    def test_read_only_reports_true(self):
        assert ReadOnlyRecord.read_only() is True

    def test_writable_model_has_no_read_only_at_all(self):
        """Opt-in: a model without the mixin does not even answer the question."""
        assert not hasattr(WritableRecord, "read_only")

    def test_writable_model_is_never_refused(self):
        WritableRecord.refuse_read_only("save")

    def test_explicit_false_opts_back_out(self):
        assert OptedOutRecord.read_only() is False
        OptedOutRecord.refuse_read_only("save")

    def test_interface_implementor_reporting_false_still_writes(self):
        """The regression a type test would introduce."""
        assert issubclass(ImplementsButWritable, IReadOnlyBehavior)
        assert ImplementsButWritable.read_only() is False
        ImplementsButWritable.refuse_read_only("save")

    def test_read_only_is_orthogonal_to_the_primary_key(self):
        assert ReadOnlyRecord.primary_key_columns() == ("id",)
        assert WritableRecord.primary_key_columns() == ("id",)


class TestInstanceWritesAreRefused:
    def test_save_raises(self, readonly_tables):
        _, _ = readonly_tables
        with pytest.raises(ReadOnlyError, match="save is not allowed on read-only model"):
            ReadOnlyRecord(label="x").save()

    def test_delete_raises(self, readonly_tables):
        _, _ = readonly_tables
        record = ReadOnlyRecord(id=1, label="x")
        record._is_from_db = True
        with pytest.raises(ReadOnlyError, match="delete is not allowed"):
            record.delete()

    def test_error_names_model_and_operation(self):
        with pytest.raises(ReadOnlyError) as excinfo:
            ReadOnlyRecord.refuse_read_only("bulk_delete")
        assert excinfo.value.model_name == "ReadOnlyRecord"
        assert excinfo.value.operation == "bulk_delete"

    def test_error_is_a_database_error(self):
        """So existing `except DatabaseError` handlers keep working."""
        from rhosocial.activerecord.backend.errors import DatabaseError

        assert issubclass(ReadOnlyError, DatabaseError)


class TestClassLevelWritesAreRefused:
    def test_bulk_create_raises(self, readonly_tables):
        with pytest.raises(ReadOnlyError, match="bulk_create"):
            ReadOnlyRecord.bulk_create([ReadOnlyRecord(label="x")])

    def test_bulk_update_raises(self, readonly_tables):
        with pytest.raises(ReadOnlyError, match="bulk_update"):
            ReadOnlyRecord.bulk_update([ReadOnlyRecord(id=1, label="x")], ["label"])

    def test_bulk_delete_raises(self, readonly_tables):
        with pytest.raises(ReadOnlyError, match="bulk_delete"):
            ReadOnlyRecord.bulk_delete([ReadOnlyRecord(id=1, label="x")])

    def test_update_all_raises(self, readonly_tables):
        with pytest.raises(ReadOnlyError, match="update_all"):
            ReadOnlyRecord.query().where(ReadOnlyRecord.c.id == 1).update_all({"label": "y"})

    def test_delete_all_raises(self, readonly_tables):
        with pytest.raises(ReadOnlyError, match="delete_all"):
            ReadOnlyRecord.query().where(ReadOnlyRecord.c.id == 1).delete_all()


class TestReadsAreNeverRefused:
    def test_query_works(self, readonly_tables):
        assert ReadOnlyRecord.query().all() == []

    def test_count_works(self, readonly_tables):
        assert ReadOnlyRecord.query().count() == 0

    def test_where_works(self, readonly_tables):
        assert ReadOnlyRecord.query().where(ReadOnlyRecord.c.label == "x").all() == []


class TestWritableControl:
    """The opt-in must not change behaviour for models that did not ask for it."""

    def test_save_succeeds(self, readonly_tables):
        record = WritableRecord(label="hello")
        record.save()
        assert record.id is not None
        assert WritableRecord.query().count() == 1

    def test_delete_succeeds(self, readonly_tables):
        record = WritableRecord(label="bye")
        record.save()
        record.delete()
        assert WritableRecord.query().count() == 0

    def test_bulk_create_succeeds(self, readonly_tables):
        WritableRecord.bulk_create([WritableRecord(label="a"), WritableRecord(label="b")])
        assert WritableRecord.query().count() >= 2

    def test_update_all_succeeds(self, readonly_tables):
        WritableRecord(label="a").save()
        WritableRecord.query().where(WritableRecord.c.label == "a").update_all({"label": "z"})
        assert WritableRecord.query().where(WritableRecord.c.label == "z").count() == 1

    def test_delete_all_succeeds(self, readonly_tables):
        WritableRecord(label="a").save()
        WritableRecord.query().where(WritableRecord.c.label == "a").delete_all()
        assert WritableRecord.query().count() == 0

    def test_model_implementing_the_interface_can_still_write(self, readonly_tables):
        record = ImplementsButWritable(label="fine")
        record.save()
        assert record.id is not None


class TestNoSqlIsIssued:
    """The regression guard: a refused write must not reach the database.

    Counts statements on the connection for the duration of each refused call.
    A gate placed after statement construction would still satisfy every
    "does it raise?" assertion above while leaving a statement behind.
    """

    def _statements_during(self, readonly_tables, action):
        _, trace = readonly_tables
        trace.take()
        with pytest.raises(ReadOnlyError):
            action()
        return trace.take()

    def test_save_issues_nothing(self, readonly_tables):
        assert self._statements_during(
            readonly_tables, lambda: ReadOnlyRecord(label="x").save()
        ) == []

    def test_delete_issues_nothing(self, readonly_tables):
        record = ReadOnlyRecord(id=1, label="x")
        record._is_from_db = True
        assert self._statements_during(readonly_tables, record.delete) == []

    def test_bulk_create_issues_nothing(self, readonly_tables):
        assert self._statements_during(
            readonly_tables, lambda: ReadOnlyRecord.bulk_create([ReadOnlyRecord(label="x")])
        ) == []

    def test_bulk_update_issues_nothing(self, readonly_tables):
        assert self._statements_during(
            readonly_tables, lambda: ReadOnlyRecord.bulk_update([ReadOnlyRecord(id=1)], ["label"])
        ) == []

    def test_bulk_delete_issues_nothing(self, readonly_tables):
        assert self._statements_during(
            readonly_tables, lambda: ReadOnlyRecord.bulk_delete([ReadOnlyRecord(id=1)])
        ) == []

    def test_update_all_issues_nothing(self, readonly_tables):
        assert self._statements_during(
            readonly_tables,
            lambda: ReadOnlyRecord.query().where(ReadOnlyRecord.c.id == 1).update_all({"label": "y"}),
        ) == []

    def test_delete_all_issues_nothing(self, readonly_tables):
        assert self._statements_during(
            readonly_tables, lambda: ReadOnlyRecord.query().where(ReadOnlyRecord.c.id == 1).delete_all()
        ) == []

    def test_the_trace_would_notice_a_statement_that_was_sent(self, readonly_tables):
        """Guards the guard: the recorder must see real writes.

        Without this, a recorder that silently observed nothing would make every
        assertion above pass vacuously.
        """
        _, trace = readonly_tables
        trace.take()
        WritableRecord(label="visible").save()
        seen = trace.take()
        assert any("INSERT" in stmt.upper() for stmt in seen), seen


class TestMixinConflicts:
    """Write-event mixins on a read-only model are always a mistake.

    Each registers a BEFORE_INSERT / BEFORE_UPDATE / BEFORE_DELETE handler, so
    on a read-only model the handler could never run -- the write is refused
    first. Failing at construction says so plainly instead of leaving a mixin
    that looks wired up but is dead.
    """

    def test_soft_delete_conflict_raises(self):
        with pytest.raises(TypeError, match="read-only but also implements"):

            class Conflict(ActiveRecord, ReadOnlyMixin, SoftDeleteMixin):
                c: ClassVar[FieldProxy] = FieldProxy()
                __table_name__ = "ar_conflict_soft"
                id: Optional[int] = None
                deleted_at: Optional[datetime] = None
                label: str = ""

            Conflict(label="x")

    def test_timestamp_conflict_raises(self):
        with pytest.raises(TypeError, match="read-only but also implements"):

            class Conflict(ActiveRecord, ReadOnlyMixin, TimestampMixin):
                c: ClassVar[FieldProxy] = FieldProxy()
                __table_name__ = "ar_conflict_ts"
                id: Optional[int] = None
                created_at: Optional[datetime] = None
                updated_at: Optional[datetime] = None
                label: str = ""

            Conflict(label="x")

    def test_no_conflict_without_read_only(self):
        """The same combination is fine on a writable model."""
        from rhosocial.activerecord.field import DefaultTimestampMixin

        class Fine(ActiveRecord, DefaultTimestampMixin):
            c: ClassVar[FieldProxy] = FieldProxy()
            __table_name__ = "ar_conflict_ok"
            id: Optional[int] = None

        Fine(id=1)
