# tests/rhosocial/activerecord_test/feature/backend/sqlite/extensions/test_ext_pragma_surface.py
"""PRAGMA registry gates: the version floor, read-only refusal and availability."""

import pytest

from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect

OLDER = SQLiteDialect(version=(3, 8, 0))
NEWER = SQLiteDialect(version=(3, 26, 0))


def test_version_floor_hides_a_later_pragma():
    # ``table_xinfo`` arrived in 3.26.0 and is not in the 3.8.0 registry view.
    assert OLDER.get_pragma_info("table_xinfo") is None
    assert NEWER.get_pragma_info("table_xinfo") is not None


def test_unadapted_dialect_answers_from_the_registry():
    # With no version to compare against, the registry answer stands.
    assert SQLiteDialect().get_pragma_info("table_xinfo") is not None


def test_setting_an_unknown_pragma_is_refused():
    with pytest.raises(ValueError, match="Unknown PRAGMA"):
        OLDER.pragma_set_statement("no_such_pragma", 1)


def test_read_only_pragma_is_refused():
    with pytest.raises(ValueError, match="read-only"):
        OLDER.pragma_set_statement("integrity_check", 1)


def test_invalid_value_for_a_constrained_pragma_is_refused():
    with pytest.raises(ValueError, match="Invalid value"):
        OLDER.pragma_set_statement("journal_mode", "sometimes")


def test_is_pragma_available_is_false_for_an_unknown_name():
    assert OLDER.is_pragma_available("no_such_pragma") is False
    assert OLDER.is_pragma_available("table_xinfo") is False
    assert NEWER.is_pragma_available("table_xinfo") is True
