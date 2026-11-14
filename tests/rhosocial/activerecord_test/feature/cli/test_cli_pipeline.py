# tests/rhosocial/activerecord_test/feature/cli/test_cli_pipeline.py
"""Pipeline, stdin, and streaming-output tests for the CLI."""

import io
import json
import sys

from support.cli import run_cli


class _BrokenPipe:
    def write(self, _value):
        raise BrokenPipeError()

    def flush(self):
        pass


class TestPipeline:
    def test_create_from_stdin(self, cli_env, monkeypatch):
        monkeypatch.setattr(
            sys, "stdin", io.StringIO('{"id": 20, "name": "Pipe", "age": 20}\n')
        )
        code, out, _ = run_cli(
            [
                "dml",
                "create",
                *cli_env.base,
                "--model",
                cli_env.user_model,
                "--data",
                "@-",
                "-o",
                "json",
            ]
        )
        assert code == 0
        assert json.loads(out)["name"] == "Pipe"

    def test_jsonl_output(self, cli_env):
        code, out, _ = run_cli(
            [
                "dql",
                "list",
                *cli_env.base,
                "--model",
                cli_env.user_model,
                "--limit",
                "2",
                "-o",
                "jsonl",
            ]
        )
        assert code == 0
        lines = [json.loads(line) for line in out.splitlines() if line.strip()]
        assert len(lines) == 2
        assert all("id" in line for line in lines)

    def test_default_output_is_json_when_captured(self, cli_env):
        code, out, _ = run_cli(
            [
                "dql",
                "list",
                *cli_env.base,
                "--model",
                cli_env.user_model,
                "--limit",
                "1",
            ]
        )
        assert code == 0
        assert isinstance(json.loads(out), list)

    def test_scalar_value(self, cli_env):
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

    def test_quiet_suppresses_pagination_note(self, cli_env):
        code, out, err = run_cli(
            [
                "dql",
                "list",
                *cli_env.base,
                "--model",
                cli_env.user_model,
                "--quiet",
                "-o",
                "json",
            ]
        )
        assert code == 0
        assert "default pagination" not in err
        assert json.loads(out)

    def test_no_header_csv(self, cli_env):
        code, out, _ = run_cli(
            [
                "dql",
                "list",
                *cli_env.base,
                "--model",
                cli_env.user_model,
                "--limit",
                "2",
                "--no-header",
                "-o",
                "csv",
            ]
        )
        assert code == 0
        lines = out.strip().splitlines()
        assert lines[0].startswith("1,Alice")

    def test_broken_pipe_is_silent(self, cli_env, monkeypatch):
        monkeypatch.setattr(sys, "stdout", _BrokenPipe())
        code = run_cli(
            [
                "dql",
                "list",
                *cli_env.base,
                "--model",
                cli_env.user_model,
                "-o",
                "jsonl",
            ],
            capture=False,
        )[0]
        assert code == 141
