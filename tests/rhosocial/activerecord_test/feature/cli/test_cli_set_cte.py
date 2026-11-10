# tests/rhosocial/activerecord_test/feature/cli/test_cli_set_cte.py
"""CLI SetOperation and CTE tests."""

import json

from conftest import run_cli


class TestSetOperation:
    def test_union(self, cli_env):
        code, out, _ = run_cli(
            [
                "set",
                "union",
                *cli_env.base,
                "--left-model",
                cli_env.user_model,
                "--right-model",
                cli_env.user_model,
                "--left-where",
                "age=30",
                "--right-where",
                "age=40",
                "-o",
                "json",
            ]
        )
        assert code == 0
        rows = json.loads(out)
        assert {row["id"] for row in rows} == {1, 3}

    def test_union_all(self, cli_env):
        code, out, _ = run_cli(
            [
                "set",
                "union-all",
                *cli_env.base,
                "--left-model",
                cli_env.user_model,
                "--right-model",
                cli_env.user_model,
                "--left-where",
                "age=30",
                "--right-where",
                "age=30",
                "-o",
                "json",
            ]
        )
        assert code == 0
        assert len(json.loads(out)) == 2

    def test_run_user_query(self, cli_env):
        code, out, _ = run_cli(
            [
                "set",
                "run",
                *cli_env.base,
                "--model",
                cli_env.user_model,
                "--query",
                cli_env.user_union,
                "-o",
                "json",
            ]
        )
        assert code == 0
        assert {row["id"] for row in json.loads(out)} == {1, 3}

    def test_run_rejects_active_query(self, cli_env):
        code, out, err = run_cli(
            [
                "set",
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
        assert code == 1
        assert out == ""
        assert "SetOperationQuery" in err


class TestCte:
    def test_run_user_query(self, cli_env):
        code, out, _ = run_cli(
            [
                "cte",
                "run",
                *cli_env.base,
                "--model",
                cli_env.user_model,
                "--query",
                cli_env.user_cte,
                "-o",
                "json",
            ]
        )
        assert code == 0
        assert {row["id"] for row in json.loads(out)} == {1, 3}


class TestAsyncSetCte:
    def test_async_set_run(self, cli_env):
        code, out, _ = run_cli(
            [
                "set",
                "run",
                *cli_env.async_base,
                "--model",
                cli_env.async_model,
                "--query",
                cli_env.async_user_union,
                "-o",
                "json",
            ]
        )
        assert code == 0
        assert {row["id"] for row in json.loads(out)} == {1, 3}

    def test_async_cte_run(self, cli_env):
        code, out, _ = run_cli(
            [
                "cte",
                "run",
                *cli_env.async_base,
                "--model",
                cli_env.async_model,
                "--query",
                cli_env.async_user_cte,
                "-o",
                "json",
            ]
        )
        assert code == 0
        assert {row["id"] for row in json.loads(out)} == {1, 3}
