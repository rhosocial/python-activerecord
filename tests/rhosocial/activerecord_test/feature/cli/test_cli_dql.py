# tests/rhosocial/activerecord_test/feature/cli/test_cli_dql.py
"""CLI DQL tests: count, exists, aggregate, and user-supplied queries."""

import json

import pytest

from conftest import run_cli


class TestDql:
    def test_count_value(self, cli_env):
        code, out, _ = run_cli(
            [
                "dql",
                "count",
                *cli_env.base,
                "--model",
                cli_env.user_model,
                "-o",
                "value",
            ]
        )
        assert code == 0
        assert out.strip() == "4"

    def test_exists_value(self, cli_env):
        code, out, _ = run_cli(
            [
                "dql",
                "exists",
                *cli_env.base,
                "--model",
                cli_env.user_model,
                "--where",
                "age=99",
                "-o",
                "value",
            ]
        )
        assert code == 0
        assert out.strip() == "false"

    def test_aggregate_scalar(self, cli_env):
        code, out, _ = run_cli(
            [
                "dql",
                "aggregate",
                *cli_env.base,
                "--model",
                cli_env.user_model,
                "--fn",
                "avg",
                "--field",
                "age",
                "-o",
                "json",
            ]
        )
        assert code == 0
        assert json.loads(out) == pytest.approx(29.25)

    def test_aggregate_group_by(self, cli_env):
        code, out, _ = run_cli(
            [
                "dql",
                "aggregate",
                *cli_env.base,
                "--model",
                cli_env.user_model,
                "--fn",
                "count",
                "--field",
                "*",
                "--group-by",
                "name",
                "-o",
                "json",
            ]
        )
        assert code == 0
        rows = json.loads(out)
        names = {row["name"] for row in rows}
        assert names == {"Alice", "Bob", "Dan"}
        assert all(row["value"] >= 1 for row in rows)

    def test_run_query_factory(self, cli_env):
        code, out, err = run_cli(
            [
                "dql",
                "run",
                *cli_env.base,
                "--model",
                cli_env.user_model,
                "--query",
                cli_env.active_users,
                "-o",
                "json",
            ]
        )
        assert code == 0
        assert "default pagination" in err
        rows = json.loads(out)
        assert all(row["age"] >= 30 for row in rows)
        assert len(rows) == 2

    def test_run_rejects_non_query(self, cli_env):
        code, out, err = run_cli(
            [
                "dql",
                "run",
                *cli_env.base,
                "--model",
                cli_env.user_model,
                "--query",
                f"{cli_env.module_name}:NotAModel",
                "-o",
                "json",
            ]
        )
        assert code == 1
        assert out == ""
        assert "expected one of" in err

    def test_read_only_model_is_queryable(self, cli_env):
        code, out, _ = run_cli(
            [
                "dql",
                "list",
                *cli_env.base,
                "--model",
                cli_env.read_only_model,
                "--limit",
                "2",
                "-o",
                "json",
            ]
        )
        assert code == 0
        assert len(json.loads(out)) == 2


class TestAsyncDql:
    def test_async_list(self, cli_env):
        code, out, _ = run_cli(
            [
                "dql",
                "list",
                *cli_env.async_base,
                "--model",
                cli_env.async_model,
                "--limit",
                "2",
                "-o",
                "json",
            ]
        )
        assert code == 0
        assert len(json.loads(out)) == 2

    def test_async_count(self, cli_env):
        code, out, _ = run_cli(
            [
                "dql",
                "count",
                *cli_env.async_base,
                "--model",
                cli_env.async_model,
                "-o",
                "value",
            ]
        )
        assert code == 0
        assert out.strip() == "4"
