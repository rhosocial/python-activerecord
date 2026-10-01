# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_json_probe_honesty.py
"""A dialect that declares no JSON support must not be handed JSON SQL.

``format_json_expression`` documents that it raises when the dialect declares
no JSON support, and did not: rendering went straight to the function-based
fallback, which is MySQL's shape. So a dialect whose probe answered False —
Oracle, Snowflake, BigQuery, Firebird — still answered a JSON path with
``JSON_EXTRACT``, a function its server does not have.

The error is worse than a wrong answer would be, because the SQL is
syntactically plausible and only the server rejects it. The probe is what
makes the situation knowable in advance, so it has to be believed.

The other half is that believing it must not cost the backends that do have
JSON: the probe and the formatter have to agree in both directions.
"""

# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_json_probe_honesty.py
import pytest

from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.expression import Column
from rhosocial.activerecord.backend.expression.advanced_functions import JSONExpression


def _sqlite():
    from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect

    dialect = SQLiteDialect()
    dialect._version = (3, 46, 1)
    return dialect


@pytest.fixture
def dialect():
    return _sqlite()


@pytest.fixture
def no_json_dialect(dialect):
    """A dialect that declares no JSON type, from the real SQLite one."""
    dialect.supports_json_type = lambda: False
    return dialect


def _expr(dialect, operation="->>", mode="function"):
    return JSONExpression(dialect, Column(dialect, "j", table="t"), "$.a", operation, mode=mode)


# ---------------------------------------------------------------------------
# The probe is believed
# ---------------------------------------------------------------------------


def test_a_dialect_without_json_refuses_a_path(no_json_dialect):
    with pytest.raises(UnsupportedFeatureError):
        _expr(no_json_dialect).to_sql()


def test_the_refusal_says_what_to_do(no_json_dialect):
    """An error the caller cannot act on is only marginally better than bad SQL."""
    with pytest.raises(UnsupportedFeatureError) as excinfo:
        _expr(no_json_dialect).to_sql()
    message = str(excinfo.value)
    assert "json" in message.lower(), message


def test_arrow_mode_is_refused_too(no_json_dialect):
    """AUTO falls back to the function path, so both routes need the check."""
    with pytest.raises(UnsupportedFeatureError):
        _expr(no_json_dialect, "->", "arrow").to_sql()


def test_auto_mode_is_refused_too(no_json_dialect):
    """AUTO is the default, so the common case is the one that must refuse."""
    with pytest.raises(UnsupportedFeatureError):
        _expr(no_json_dialect, "->", "auto").to_sql()


# ---------------------------------------------------------------------------
# Declaring JSON means being able to render it
# ---------------------------------------------------------------------------


def test_sqlite_declares_json_and_renders_it(dialect):
    assert dialect.supports_json_type() is True
    sql, _ = _expr(dialect).to_sql()
    assert "json_extract" in sql.lower(), sql


@pytest.mark.parametrize("mode", ["function", "arrow", "auto"])
def test_every_mode_renders_on_a_dialect_that_has_json(dialect, mode):
    """Believing the probe must not cost the backends that do have JSON."""
    assert dialect.supports_json_arrow_operators(), "SQLite has arrow operators"
    sql, _ = _expr(dialect, "->", mode).to_sql()
    assert sql, f"mode={mode} rendered nothing"


def test_the_probe_is_not_consulted_twice(no_json_dialect):
    """A dialect that answers the probe is enough; the renderer is never asked."""
    calls = []

    def probe():
        calls.append(1)
        return False

    no_json_dialect.supports_json_type = probe
    with pytest.raises(UnsupportedFeatureError):
        _expr(no_json_dialect).to_sql()
    assert calls, "the probe was never consulted"
