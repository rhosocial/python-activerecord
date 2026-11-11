# tests/rhosocial/activerecord_test/feature/backend/error_taxonomy/test_error_taxonomy.py
"""Semantic error taxonomy: hierarchy, retry hints, diagnostics, CLI mapping."""

from rhosocial.activerecord.backend.errors import (
    BulkOperationError,
    BulkValidationError,
    ConcurrencyError,
    ConnectionError,
    DataError,
    DatabaseError,
    DeadlockError,
    InfrastructureError,
    IntegrityError,
    LockError,
    OperationalError,
    PolicyError,
    QueryError,
    ReadOnlyError,
    RecordError,
    RecordNotFound,
    StaleRecordError,
    TypeConversionError,
    UnaddressableRecordError,
    ValidationError,
    attach_diagnostics,
)
from rhosocial.activerecord.cli.error_mapping import translate_error
from rhosocial.activerecord.cli.errors import EXIT_READ_ONLY, CliNotFoundError, CLIError


class TestHierarchy:
    def test_every_error_is_a_database_error(self):
        errors = [
            ValidationError("bad"),
            IntegrityError("dup"),
            TypeConversionError("type"),
            RecordNotFound("missing"),
            UnaddressableRecordError("Keyless", "read"),
            ReadOnlyError("Model", "create"),
            StaleRecordError(model=object, primary_key=1, expected_version=1),
            LockError("lock"),
            DeadlockError("deadlock"),
            ConnectionError("connection"),
            OperationalError("operation"),
            QueryError("query"),
            BulkValidationError([(0, "bad")]),
            BulkOperationError("bulk"),
        ]
        assert all(isinstance(item, DatabaseError) for item in errors)

    def test_data_errors(self):
        for error in (
            ValidationError("bad"),
            IntegrityError("dup"),
            TypeConversionError("type"),
        ):
            assert isinstance(error, DataError)

    def test_record_errors(self):
        assert isinstance(RecordNotFound("missing"), RecordError)
        assert isinstance(UnaddressableRecordError("M", "read"), RecordError)

    def test_policy_errors(self):
        assert isinstance(ReadOnlyError("Model", "create"), PolicyError)

    def test_concurrency_errors(self):
        assert isinstance(LockError("lock"), ConcurrencyError)
        assert isinstance(DeadlockError("deadlock"), ConcurrencyError)
        assert isinstance(
            StaleRecordError(model=object, primary_key=1, expected_version=1),
            ConcurrencyError,
        )

    def test_infrastructure_errors(self):
        assert isinstance(ConnectionError("connection"), InfrastructureError)
        assert isinstance(OperationalError("operation"), InfrastructureError)

    def test_bulk_validation_is_both_bulk_and_data(self):
        error = BulkValidationError([(0, "bad")])
        assert isinstance(error, BulkOperationError)
        assert isinstance(error, DataError)


class TestRetryHints:
    def test_concurrency_errors_are_retryable(self):
        assert LockError("lock").retryable is True
        assert DeadlockError("deadlock").retryable is True
        assert (
            StaleRecordError(model=object, primary_key=1, expected_version=1).retryable
            is True
        )

    def test_data_and_policy_errors_are_not_retryable(self):
        assert IntegrityError("dup").retryable is False
        assert ValidationError("bad").retryable is False
        assert ReadOnlyError("Model", "create").retryable is False

    def test_infrastructure_is_not_retryable_by_default(self):
        assert ConnectionError("connection").retryable is False
        assert OperationalError("operation").retryable is False

    def test_transient_infrastructure_becomes_retryable(self):
        error = attach_diagnostics(
            OperationalError("timeout"), operation="select", transient=True
        )
        assert error.transient is True
        assert error.retryable is True



class TestDiagnostics:
    def test_attach_diagnostics_sets_fields(self):
        error = attach_diagnostics(
            IntegrityError("dup"),
            operation="insert",
            sqlstate="23505",
            driver_code=1062,
            backend="mysql",
        )
        assert error.operation == "insert"
        assert error.sqlstate == "23505"
        assert error.driver_code == 1062
        assert error.backend == "mysql"

    def test_attach_diagnostics_returns_same_instance(self):
        error = IntegrityError("dup")
        assert attach_diagnostics(error) is error

    def test_transient_false_keeps_non_retryable(self):
        error = attach_diagnostics(BackendOperational(), transient=False)
        assert error.transient is False
        assert error.retryable is False


class BackendOperational(OperationalError):
    """A backend-specific subclass, as a driver mapping would create."""


class BackendConcurrency(ConcurrencyError):
    """A backend-specific concurrency error."""


class BackendData(DataError):
    """A backend-specific data error."""


class BackendPolicy(PolicyError):
    """A backend-specific policy error."""


class TestCliCategoryMapping:
    def _translate(self, error):
        return translate_error(error, operation="dml create")

    def test_unknown_concurrency_subclass_is_exit_one(self):
        translated = self._translate(BackendConcurrency("deadlock"))
        assert isinstance(translated, CLIError)
        assert translated.exit_code == 1
        assert "Concurrency conflict" in translated.message

    def test_unknown_data_subclass_is_exit_one(self):
        translated = self._translate(BackendData("bad value"))
        assert translated.exit_code == 1
        assert "Invalid data" in translated.message

    def test_unknown_policy_subclass_without_context_is_exit_six(self):
        translated = self._translate(BackendPolicy("refused"))
        assert translated.exit_code == EXIT_READ_ONLY

    def test_record_not_found_stays_exit_three(self):
        translated = self._translate(RecordNotFound("Record not found"))
        assert isinstance(translated, CliNotFoundError)
        assert translated.exit_code == 3

