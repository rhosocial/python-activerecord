# tests/rhosocial/activerecord_test/feature/cli/test_cli_bulk.py
"""CLI bulk DML tests."""

import io
import json

from conftest import run_cli


class TestBulkCreate:
    def test_bulk_create_json_array(self, cli_env):
        code, out, _ = run_cli(
            [
                "dml",
                "bulk",
                "create",
                *cli_env.base,
                "--model",
                cli_env.user_model,
                "--data",
                '[{"id": 5, "name": "Eve", "age": 33},'
                '{"id": 6, "name": "Frank", "age": 44}]',
                "-o",
                "json",
            ]
        )
        assert code == 0
        rows = json.loads(out)
        assert [row["id"] for row in rows] == [5, 6]

    def test_bulk_create_jsonl_from_stdin(self, cli_env, monkeypatch):
        monkeypatch.setattr(
            "sys.stdin",
            io.StringIO(
                '{"id": 7, "name": "Gina", "age": 28}\n'
                '{"id": 8, "name": "Hana", "age": 31}\n'
            ),
        )
        code, out, _ = run_cli(
            [
                "dml",
                "bulk",
                "create",
                *cli_env.base,
                "--model",
                cli_env.user_model,
                "--data",
                "@-",
                "-o",
                "jsonl",
            ]
        )
        assert code == 0
        lines = [json.loads(line) for line in out.splitlines() if line.strip()]
        assert [line["name"] for line in lines] == ["Gina", "Hana"]


class TestBulkUpdate:
    def test_bulk_update(self, cli_env):
        code, out, _ = run_cli(
            [
                "dml",
                "bulk",
                "update",
                *cli_env.base,
                "--model",
                cli_env.user_model,
                "--data",
                '[{"id": 1, "age": 31}, {"id": 2, "age": 26}]',
                "-o",
                "json",
            ]
        )
        assert code == 0
        assert json.loads(out) == {"action": "update", "affected": 2}

    def test_bulk_update_missing_record_aborts(self, cli_env):
        code, out, err = run_cli(
            [
                "dml",
                "bulk",
                "update",
                *cli_env.base,
                "--model",
                cli_env.user_model,
                "--data",
                '[{"id": 1, "age": 31}, {"id": 999, "age": 26}]',
                "-o",
                "json",
            ]
        )
        assert code == 3
        assert out == ""
        assert "999" in err

    def test_bulk_update_field_mismatch_returns_one(self, cli_env):
        code, out, err = run_cli(
            [
                "dml",
                "bulk",
                "update",
                *cli_env.base,
                "--model",
                cli_env.user_model,
                "--data",
                '[{"id": 1, "age": 31}, {"id": 2, "name": "Bobby"}]',
                "-o",
                "json",
            ]
        )
        assert code == 1
        assert out == ""
        assert "same fields" in err


class TestBulkDelete:
    def test_dry_run(self, cli_env):
        code, out, _ = run_cli(
            [
                "dml",
                "bulk",
                "delete",
                *cli_env.base,
                "--model",
                cli_env.user_model,
                "--data",
                "[1, 2]",
                "--dry-run",
                "-o",
                "json",
            ]
        )
        assert code == 0
        assert json.loads(out) == {"action": "delete", "affected": 2, "dry_run": True}

    def test_requires_yes_in_non_tty(self, cli_env):
        code, out, err = run_cli(
            [
                "dml",
                "bulk",
                "delete",
                *cli_env.base,
                "--model",
                cli_env.user_model,
                "--data",
                "[1, 2]",
                "-o",
                "json",
            ]
        )
        assert code == 5
        assert out == ""
        assert "--yes" in err

    def test_delete(self, cli_env):
        code, out, _ = run_cli(
            [
                "dml",
                "bulk",
                "delete",
                *cli_env.base,
                "--model",
                cli_env.user_model,
                "--data",
                "[1, 2]",
                "--yes",
                "-o",
                "json",
            ]
        )
        assert code == 0
        assert json.loads(out) == {"action": "delete", "affected": 2}

    def test_soft_delete(self, cli_env):
        code, out, _ = run_cli(
            [
                "dml",
                "bulk",
                "delete",
                *cli_env.base,
                "--model",
                cli_env.soft_model,
                "--data",
                "[1, 2]",
                "--yes",
                "-o",
                "json",
            ]
        )
        assert code == 0
        assert json.loads(out)["action"] == "soft_delete"

    def test_read_only_rejected(self, cli_env):
        code, out, err = run_cli(
            [
                "dml",
                "bulk",
                "delete",
                *cli_env.base,
                "--model",
                cli_env.read_only_model,
                "--data",
                "[1]",
                "--yes",
                "-o",
                "json",
            ]
        )
        assert code == 6
        assert out == ""
        assert "read-only" in err
