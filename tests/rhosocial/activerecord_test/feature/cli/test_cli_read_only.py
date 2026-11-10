# tests/rhosocial/activerecord_test/feature/cli/test_cli_read_only.py
"""Read-only model behavior tests for the CLI."""

from conftest import run_cli


class TestReadOnly:
    def test_create_rejected(self, cli_env):
        code, out, err = run_cli(
            [
                "dml",
                "create",
                *cli_env.base,
                "--model",
                cli_env.read_only_model,
                "--data",
                '{"id": 99, "name": "Nope"}',
                "-o",
                "json",
            ]
        )
        assert code == 6
        assert out == ""
        assert "read-only" in err

    def test_update_rejected(self, cli_env):
        code, out, err = run_cli(
            [
                "dml",
                "update",
                *cli_env.base,
                "--model",
                cli_env.read_only_model,
                "--pk",
                "1",
                "--data",
                '{"age": 31}',
                "-o",
                "json",
            ]
        )
        assert code == 6
        assert out == ""
        assert "read-only" in err

    def test_delete_dry_run_rejected(self, cli_env):
        code, out, err = run_cli(
            [
                "dml",
                "delete",
                *cli_env.base,
                "--model",
                cli_env.read_only_model,
                "--pk",
                "1",
                "--dry-run",
                "-o",
                "json",
            ]
        )
        assert code == 6
        assert out == ""
        assert "read-only" in err

    def test_dql_still_works(self, cli_env):
        code, out, _ = run_cli(
            [
                "dql",
                "count",
                *cli_env.base,
                "--model",
                cli_env.read_only_model,
                "-o",
                "value",
            ]
        )
        assert code == 0
        assert out.strip() == "4"

    def test_async_create_rejected(self, cli_env):
        code, out, err = run_cli(
            [
                "dml",
                "create",
                *cli_env.async_base,
                "--model",
                cli_env.async_read_only_model,
                "--data",
                '{"id": 99, "name": "Nope"}',
                "-o",
                "json",
            ]
        )
        assert code == 6
        assert out == ""
        assert "read-only" in err
