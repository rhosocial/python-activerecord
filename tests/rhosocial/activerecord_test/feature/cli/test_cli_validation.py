# tests/rhosocial/activerecord_test/feature/cli/test_cli_validation.py
"""CLI validation: field constraints, bulk context, parameter checks, and errors."""

import builtins
import csv
import io
import json
import sqlite3
import sys

from conftest import run_cli
from rhosocial.activerecord.cli import interaction as cli_interaction


def _count(database, table="users"):
    conn = sqlite3.connect(str(database))
    try:
        return conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    finally:
        conn.close()


def _value(database, pk, column):
    conn = sqlite3.connect(str(database))
    try:
        row = conn.execute(
            f"SELECT {column} FROM users WHERE id = ?", (pk,)
        ).fetchone()
        return None if row is None else row[0]
    finally:
        conn.close()


class TestValidation:
    def test_create_field_constraint_failure(self, cli_env):
        code, out, err = run_cli(
            [
                "dml",
                "create",
                *cli_env.base,
                "--model",
                cli_env.validated_model,
                "--data",
                '{"id": 9, "name": "Carol", "age": 101}',
                "-o",
                "json",
            ]
        )
        assert code == 1
        assert out == ""
        assert "Invalid data for ValidatedUser" in err
        assert _count(cli_env.database) == 4

    def test_create_field_validator_failure(self, cli_env):
        code, out, err = run_cli(
            [
                "dml",
                "create",
                *cli_env.base,
                "--model",
                cli_env.validated_model,
                "--data",
                '{"id": 9, "name": "admin", "age": 30}',
                "-o",
                "json",
            ]
        )
        assert code == 1
        assert out == ""
        assert "'admin'" in err
        assert _count(cli_env.database) == 4

    def test_create_model_validator_failure(self, cli_env):
        code, out, err = run_cli(
            [
                "dml",
                "create",
                *cli_env.base,
                "--model",
                cli_env.validated_model,
                "--data",
                '{"id": 9, "name": "senior", "age": 30}',
                "-o",
                "json",
            ]
        )
        assert code == 1
        assert out == ""
        assert "senior users need age >= 60" in err
        assert _count(cli_env.database) == 4

    def test_update_field_constraint_failure(self, cli_env):
        code, out, err = run_cli(
            [
                "dml",
                "update",
                *cli_env.base,
                "--model",
                cli_env.validated_model,
                "--pk",
                "1",
                "--data",
                '{"age": 101}',
                "-o",
                "json",
            ]
        )
        assert code == 1
        assert out == ""
        assert "ValidatedUser pk=1" in err
        assert _value(cli_env.database, 1, "age") == 30

    def test_update_model_validator_failure(self, cli_env):
        code, out, err = run_cli(
            [
                "dml",
                "update",
                *cli_env.base,
                "--model",
                cli_env.validated_model,
                "--pk",
                "1",
                "--data",
                '{"name": "senior"}',
                "-o",
                "json",
            ]
        )
        assert code == 1
        assert out == ""
        assert "ValidatedUser pk=1" in err
        assert _value(cli_env.database, 1, "name") == "Alice"

    def test_bulk_create_reports_item_index(self, cli_env):
        code, out, err = run_cli(
            [
                "dml",
                "bulk",
                "create",
                *cli_env.base,
                "--model",
                cli_env.validated_model,
                "--data",
                '[{"name": "Ok", "age": 20}, {"name": "X", "age": 20}]',
                "-o",
                "json",
            ]
        )
        assert code == 1
        assert out == ""
        assert "item 2" in err
        assert _count(cli_env.database) == 4

    def test_bulk_update_reports_item_and_pk(self, cli_env):
        code, out, err = run_cli(
            [
                "dml",
                "bulk",
                "update",
                *cli_env.base,
                "--model",
                cli_env.validated_model,
                "--data",
                '[{"id": 1, "age": 31}, {"id": 2, "age": 101}]',
                "--update-fields",
                "age",
                "-o",
                "json",
            ]
        )
        assert code == 1
        assert out == ""
        assert "item 2" in err
        assert "pk=2" in err
        assert _value(cli_env.database, 2, "age") == 25

    def test_bulk_update_unknown_field(self, cli_env):
        code, out, err = run_cli(
            [
                "dml",
                "bulk",
                "update",
                *cli_env.base,
                "--model",
                cli_env.validated_model,
                "--data",
                '[{"id": 1, "nope": 1}]',
                "-o",
                "json",
            ]
        )
        assert code == 1
        assert out == ""
        assert "nope" in err
        assert "Available fields" in err

    def test_update_fields_unknown_field(self, cli_env):
        code, out, err = run_cli(
            [
                "dml",
                "bulk",
                "update",
                *cli_env.base,
                "--model",
                cli_env.validated_model,
                "--data",
                '[{"id": 1, "age": 31}]',
                "--update-fields",
                "nope",
                "-o",
                "json",
            ]
        )
        assert code == 1
        assert out == ""
        assert "nope" in err

    def test_aggregate_unknown_field(self, cli_env):
        code, out, err = run_cli(
            [
                "dql",
                "aggregate",
                *cli_env.base,
                "--model",
                cli_env.validated_model,
                "--fn",
                "avg",
                "--field",
                "nope",
                "-o",
                "json",
            ]
        )
        assert code == 1
        assert out == ""
        assert 'Unknown aggregate field "nope"' in err

    def test_aggregate_star_requires_count(self, cli_env):
        code, out, err = run_cli(
            [
                "dql",
                "aggregate",
                *cli_env.base,
                "--model",
                cli_env.validated_model,
                "--fn",
                "sum",
                "--field",
                "*",
                "-o",
                "json",
            ]
        )
        assert code == 1
        assert out == ""
        assert "--fn sum requires a concrete --field" in err

    def test_negative_limit_rejected(self, cli_env):
        code, out, err = run_cli(
            ["dql", "list", *cli_env.base, "--model", cli_env.validated_model, "--limit", "-1"]
        )
        assert code == 1
        assert out == ""
        assert "--limit must be greater than or equal to 0" in err

    def test_negative_offset_rejected(self, cli_env):
        code, out, err = run_cli(
            ["dql", "list", *cli_env.base, "--model", cli_env.validated_model, "--offset", "-1"]
        )
        assert code == 1
        assert out == ""
        assert "--offset must be greater than or equal to 0" in err

    def test_limit_zero_returns_all(self, cli_env):
        code, out, err = run_cli(
            [
                "dql",
                "list",
                *cli_env.base,
                "--model",
                cli_env.validated_model,
                "--limit",
                "0",
                "-o",
                "json",
            ]
        )
        assert code == 0
        assert len(json.loads(out)) == 4

    def test_page_zero_rejected(self, cli_env):
        code, out, err = run_cli(
            [
                "dql",
                "list",
                *cli_env.base,
                "--model",
                cli_env.validated_model,
                "--page",
                "0",
                "--page-size",
                "2",
            ]
        )
        assert code == 1
        assert out == ""
        assert "--page and --page-size must be positive" in err

    def test_keyless_get_reports_no_primary_key(self, cli_env):
        code, out, err = run_cli(
            [
                "dql",
                "get",
                *cli_env.base,
                "--model",
                cli_env.keyless_model,
                "--pk",
                "1",
            ]
        )
        assert code == 1
        assert out == ""
        assert "primary key" in err

    def test_cancel_delete_is_not_an_error(self, cli_env, monkeypatch):
        monkeypatch.setattr(cli_interaction, "is_tty", lambda: True)

        class _TtyStdin:
            def isatty(self):
                return True

        monkeypatch.setattr(sys, "stdin", _TtyStdin())
        monkeypatch.setattr(builtins, "input", lambda prompt: "n")
        code, out, err = run_cli(
            [
                "dml",
                "delete",
                *cli_env.base,
                "--model",
                cli_env.validated_model,
                "--pk",
                "1",
            ]
        )
        assert code == 0
        assert out == ""
        assert "Operation cancelled." in err
        assert "Error:" not in err
        assert _count(cli_env.database) == 4

    def test_delete_csv_has_header_and_row(self, cli_env):
        code, out, err = run_cli(
            [
                "dml",
                "delete",
                *cli_env.base,
                "--model",
                cli_env.validated_model,
                "--pk",
                "4",
                "--yes",
                "-o",
                "csv",
            ]
        )
        assert code == 0
        rows = list(csv.reader(io.StringIO(out)))
        assert rows[0] == ["action", "pk", "affected"]
        assert rows[1] == ["delete", "4", "1"]

    def test_bulk_update_tsv_has_action_and_affected(self, cli_env):
        code, out, err = run_cli(
            [
                "dml",
                "bulk",
                "update",
                *cli_env.base,
                "--model",
                cli_env.validated_model,
                "--data",
                '[{"id": 1, "age": 31}, {"id": 2, "age": 26}]',
                "--update-fields",
                "age",
                "-o",
                "tsv",
            ]
        )
        assert code == 0
        rows = list(csv.reader(io.StringIO(out), delimiter="\t"))
        assert rows[0] == ["action", "affected"]
        assert rows[1] == ["update", "2"]


class TestAsyncValidation:
    def test_create_field_constraint_failure(self, cli_env):
        code, out, err = run_cli(
            [
                "dml",
                "create",
                *cli_env.async_base,
                "--model",
                cli_env.async_validated_model,
                "--data",
                '{"id": 9, "name": "Carol", "age": 101}',
                "-o",
                "json",
            ]
        )
        assert code == 1
        assert out == ""
        assert "Invalid data for AsyncValidatedUser" in err
        assert _count(cli_env.database) == 4

    def test_create_field_validator_failure(self, cli_env):
        code, out, err = run_cli(
            [
                "dml",
                "create",
                *cli_env.async_base,
                "--model",
                cli_env.async_validated_model,
                "--data",
                '{"id": 9, "name": "admin", "age": 30}',
                "-o",
                "json",
            ]
        )
        assert code == 1
        assert out == ""
        assert "'admin'" in err
        assert _count(cli_env.database) == 4

    def test_create_model_validator_failure(self, cli_env):
        code, out, err = run_cli(
            [
                "dml",
                "create",
                *cli_env.async_base,
                "--model",
                cli_env.async_validated_model,
                "--data",
                '{"id": 9, "name": "senior", "age": 30}',
                "-o",
                "json",
            ]
        )
        assert code == 1
        assert out == ""
        assert "senior users need age >= 60" in err
        assert _count(cli_env.database) == 4

    def test_update_field_constraint_failure(self, cli_env):
        code, out, err = run_cli(
            [
                "dml",
                "update",
                *cli_env.async_base,
                "--model",
                cli_env.async_validated_model,
                "--pk",
                "1",
                "--data",
                '{"age": 101}',
                "-o",
                "json",
            ]
        )
        assert code == 1
        assert out == ""
        assert "AsyncValidatedUser pk=1" in err
        assert _value(cli_env.database, 1, "age") == 30

    def test_update_model_validator_failure(self, cli_env):
        code, out, err = run_cli(
            [
                "dml",
                "update",
                *cli_env.async_base,
                "--model",
                cli_env.async_validated_model,
                "--pk",
                "1",
                "--data",
                '{"name": "senior"}',
                "-o",
                "json",
            ]
        )
        assert code == 1
        assert out == ""
        assert "AsyncValidatedUser pk=1" in err
        assert _value(cli_env.database, 1, "name") == "Alice"

    def test_bulk_create_reports_item_index(self, cli_env):
        code, out, err = run_cli(
            [
                "dml",
                "bulk",
                "create",
                *cli_env.async_base,
                "--model",
                cli_env.async_validated_model,
                "--data",
                '[{"name": "Ok", "age": 20}, {"name": "X", "age": 20}]',
                "-o",
                "json",
            ]
        )
        assert code == 1
        assert out == ""
        assert "item 2" in err
        assert _count(cli_env.database) == 4

    def test_bulk_update_reports_item_and_pk(self, cli_env):
        code, out, err = run_cli(
            [
                "dml",
                "bulk",
                "update",
                *cli_env.async_base,
                "--model",
                cli_env.async_validated_model,
                "--data",
                '[{"id": 1, "age": 31}, {"id": 2, "age": 101}]',
                "--update-fields",
                "age",
                "-o",
                "json",
            ]
        )
        assert code == 1
        assert out == ""
        assert "item 2" in err
        assert "pk=2" in err
        assert _value(cli_env.database, 2, "age") == 25

    def test_bulk_update_unknown_field(self, cli_env):
        code, out, err = run_cli(
            [
                "dml",
                "bulk",
                "update",
                *cli_env.async_base,
                "--model",
                cli_env.async_validated_model,
                "--data",
                '[{"id": 1, "nope": 1}]',
                "-o",
                "json",
            ]
        )
        assert code == 1
        assert out == ""
        assert "nope" in err

    def test_update_fields_unknown_field(self, cli_env):
        code, out, err = run_cli(
            [
                "dml",
                "bulk",
                "update",
                *cli_env.async_base,
                "--model",
                cli_env.async_validated_model,
                "--data",
                '[{"id": 1, "age": 31}]',
                "--update-fields",
                "nope",
                "-o",
                "json",
            ]
        )
        assert code == 1
        assert out == ""
        assert "nope" in err

    def test_aggregate_unknown_field(self, cli_env):
        code, out, err = run_cli(
            [
                "dql",
                "aggregate",
                *cli_env.async_base,
                "--model",
                cli_env.async_validated_model,
                "--fn",
                "avg",
                "--field",
                "nope",
                "-o",
                "json",
            ]
        )
        assert code == 1
        assert out == ""
        assert 'Unknown aggregate field "nope"' in err

    def test_aggregate_star_requires_count(self, cli_env):
        code, out, err = run_cli(
            [
                "dql",
                "aggregate",
                *cli_env.async_base,
                "--model",
                cli_env.async_validated_model,
                "--fn",
                "sum",
                "--field",
                "*",
                "-o",
                "json",
            ]
        )
        assert code == 1
        assert out == ""
        assert "--fn sum requires a concrete --field" in err

    def test_negative_limit_rejected(self, cli_env):
        code, out, err = run_cli(
            [
                "dql",
                "list",
                *cli_env.async_base,
                "--model",
                cli_env.async_validated_model,
                "--limit",
                "-1",
            ]
        )
        assert code == 1
        assert out == ""
        assert "--limit must be greater than or equal to 0" in err

    def test_negative_offset_rejected(self, cli_env):
        code, out, err = run_cli(
            [
                "dql",
                "list",
                *cli_env.async_base,
                "--model",
                cli_env.async_validated_model,
                "--offset",
                "-1",
            ]
        )
        assert code == 1
        assert out == ""
        assert "--offset must be greater than or equal to 0" in err

    def test_limit_zero_returns_all(self, cli_env):
        code, out, err = run_cli(
            [
                "dql",
                "list",
                *cli_env.async_base,
                "--model",
                cli_env.async_validated_model,
                "--limit",
                "0",
                "-o",
                "json",
            ]
        )
        assert code == 0
        assert len(json.loads(out)) == 4

    def test_page_zero_rejected(self, cli_env):
        code, out, err = run_cli(
            [
                "dql",
                "list",
                *cli_env.async_base,
                "--model",
                cli_env.async_validated_model,
                "--page",
                "0",
                "--page-size",
                "2",
            ]
        )
        assert code == 1
        assert out == ""
        assert "--page and --page-size must be positive" in err

    def test_keyless_get_reports_no_primary_key(self, cli_env):
        code, out, err = run_cli(
            [
                "dql",
                "get",
                *cli_env.base,
                "--model",
                cli_env.keyless_model,
                "--pk",
                "1",
            ]
        )
        assert code == 1
        assert out == ""
        assert "primary key" in err

    def test_cancel_delete_is_not_an_error(self, cli_env, monkeypatch):
        monkeypatch.setattr(cli_interaction, "is_tty", lambda: True)

        class _TtyStdin:
            def isatty(self):
                return True

        monkeypatch.setattr(sys, "stdin", _TtyStdin())
        monkeypatch.setattr(builtins, "input", lambda prompt: "n")
        code, out, err = run_cli(
            [
                "dml",
                "delete",
                *cli_env.async_base,
                "--model",
                cli_env.async_validated_model,
                "--pk",
                "1",
            ]
        )
        assert code == 0
        assert out == ""
        assert "Operation cancelled." in err
        assert "Error:" not in err
        assert _count(cli_env.database) == 4

    def test_delete_csv_has_header_and_row(self, cli_env):
        code, out, err = run_cli(
            [
                "dml",
                "delete",
                *cli_env.async_base,
                "--model",
                cli_env.async_validated_model,
                "--pk",
                "4",
                "--yes",
                "-o",
                "csv",
            ]
        )
        assert code == 0
        rows = list(csv.reader(io.StringIO(out)))
        assert rows[0] == ["action", "pk", "affected"]
        assert rows[1] == ["delete", "4", "1"]

    def test_bulk_update_tsv_has_action_and_affected(self, cli_env):
        code, out, err = run_cli(
            [
                "dml",
                "bulk",
                "update",
                *cli_env.async_base,
                "--model",
                cli_env.async_validated_model,
                "--data",
                '[{"id": 1, "age": 31}, {"id": 2, "age": 26}]',
                "--update-fields",
                "age",
                "-o",
                "tsv",
            ]
        )
        assert code == 0
        rows = list(csv.reader(io.StringIO(out), delimiter="\t"))
        assert rows[0] == ["action", "affected"]
        assert rows[1] == ["update", "2"]


