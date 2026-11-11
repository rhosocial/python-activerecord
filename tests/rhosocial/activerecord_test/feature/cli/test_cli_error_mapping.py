# tests/rhosocial/activerecord_test/feature/cli/test_cli_error_mapping.py
"""CLI error mapping: model/backend exceptions to CLI errors and exit codes."""

from rhosocial.activerecord.backend.errors import (
    BulkStateError,
    BulkValidationError,
    ConnectionError,
    IntegrityError,
    ReadOnlyError,
    RecordNotFound,
    StaleRecordError,
    UnaddressableRecordError,
    TransactionError,
)
from rhosocial.activerecord.cli import build_parser
from rhosocial.activerecord.cli.error_mapping import operation_label, translate_error
from rhosocial.activerecord.cli.errors import (
    EXIT_BACKEND_UNAVAILABLE,
    EXIT_ERROR,
    EXIT_NOT_FOUND,
    EXIT_OK,
    EXIT_READ_ONLY,
    BackendUnavailableError,
    CancelledError,
    CLIError,
    CliNotFoundError,
    ReadOnlyModelError,
    report_error,
    report_unexpected,
)


class TestErrorMapping:
    def test_cli_error_passes_through(self):
        original = CLIError("bad input")
        assert translate_error(original, operation="dml create") is original

    def test_record_not_found_becomes_cli_not_found(self):
        translated = translate_error(
            RecordNotFound("Record not found for User"),
            operation="dql get",
            model=None,
        )
        assert isinstance(translated, CliNotFoundError)
        assert translated.exit_code == EXIT_NOT_FOUND
        assert translated.__cause__ is None

    def test_record_not_found_uses_pk_context(self):
        translated = translate_error(
            RecordNotFound("Record not found for User"),
            operation="dml delete",
            pk=42,
        )
        assert translated.exit_code == EXIT_NOT_FOUND
        assert "pk=42" in translated.message

    def test_read_only_keeps_exit_six(self):
        translated = translate_error(
            ReadOnlyError("User", "dml create"), operation="dml create"
        )
        assert isinstance(translated, ReadOnlyModelError)
        assert translated.exit_code == EXIT_READ_ONLY

    def test_connection_error_is_exit_one_not_four(self):
        translated = translate_error(ConnectionError("connection refused"), operation="dql list")
        assert isinstance(translated, CLIError)
        assert translated.exit_code == EXIT_ERROR
        assert "Database connection failed during dql list" in translated.message

    def test_backend_unavailable_keeps_exit_four(self):
        translated = translate_error(
            BackendUnavailableError("cannot import"), operation="dml create"
        )
        assert translated.exit_code == EXIT_BACKEND_UNAVAILABLE
        assert isinstance(translated, BackendUnavailableError)

    def test_stale_record_mentions_both_outcomes(self):
        translated = translate_error(
            StaleRecordError(model=object, primary_key=1, expected_version=2),
            operation="dml update",
        )
        assert translated.exit_code == EXIT_ERROR
        assert "updated or deleted" in translated.message

    def test_bulk_validation_reports_item_index(self):
        translated = translate_error(
            BulkValidationError([(1, "age: Input should be <= 100")]),
            operation="dml bulk update",
        )
        assert translated.exit_code == EXIT_ERROR
        assert "item 2" in translated.message

    def test_bulk_state_error(self):
        translated = translate_error(BulkStateError("records are inconsistent"))
        assert translated.exit_code == EXIT_ERROR
        assert "Bulk operation cannot run" in translated.message

    def test_unaddressable_record_points_to_where(self):
        translated = translate_error(
            UnaddressableRecordError("KeylessUser", "Reading the primary key value")
        )
        assert translated.exit_code == EXIT_ERROR
        assert "primary key" in translated.message

    def test_integrity_error_is_exit_one(self):
        translated = translate_error(IntegrityError("duplicate key"), operation="dml create")
        assert translated.exit_code == EXIT_ERROR
        assert "Integrity constraint failed during dml create" in translated.message

    def test_transaction_error_is_exit_one_with_context(self):
        translated = translate_error(
            TransactionError("Auto-commit failed"), operation="dml create"
        )
        assert translated.exit_code == EXIT_ERROR
        assert "Database transaction failed during dml create" in translated.message

    def test_unknown_error_returns_none(self):
        assert translate_error(ValueError("unexpected")) is None


class TestOperationLabel:
    def test_dml_single(self):
        args = build_parser().parse_args(
            ["dml", "create", "--model", "m:U", "--data", "{}"]
        )
        assert operation_label(args) == "dml create"

    def test_dml_bulk(self):
        args = build_parser().parse_args(
            ["dml", "bulk", "delete", "--model", "m:U", "--data", "[]"]
        )
        assert operation_label(args) == "dml bulk delete"

    def test_dql(self):
        args = build_parser().parse_args(["dql", "aggregate", "--model", "m:U"])
        assert operation_label(args) == "dql aggregate"

    def test_set_and_cte(self):
        args = build_parser().parse_args(
            [
                "set",
                "union",
                "--left-model",
                "m:U",
                "--right-model",
                "m:U",
            ]
        )
        assert operation_label(args) == "set union"
        args = build_parser().parse_args(["cte", "run", "--query", "q:f"])
        assert operation_label(args) == "cte run"


class TestReportFormatting:
    def test_cancelled_has_no_error_prefix(self, capsys):
        report_error(CancelledError())
        err = capsys.readouterr().err
        assert err.strip() == "Operation cancelled."
        assert "Error:" not in err

    def test_cancelled_exit_code_is_zero(self):
        assert CancelledError().exit_code == EXIT_OK

    def test_unexpected_names_the_type(self, capsys):
        report_unexpected(ValueError("boom"))
        err = capsys.readouterr().err
        assert err.strip() == "Unexpected error (ValueError): boom"
        assert "Traceback" not in err

    def test_error_prefix_is_kept_for_failures(self, capsys):
        report_error(CLIError("nope"))
        err = capsys.readouterr().err
        assert err.strip() == "Error: nope"
