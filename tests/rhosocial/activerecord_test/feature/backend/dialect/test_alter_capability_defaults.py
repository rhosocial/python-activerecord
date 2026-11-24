# tests/rhosocial/activerecord_test/feature/backend/dialect/test_alter_capability_defaults.py
"""The baseline ALTER capability answers a backend inherits from core.

A default is a promise: ``supports_X() is True`` means the generic renderer can
produce a valid ``X``. These tests pin the baseline so a dead-code typo
(``return False; return True``) or a careless flip cannot silently suppress or
over-claim a capability again.
"""
import inspect

from rhosocial.activerecord.backend.dialect.mixins.ddl_table import ConstraintMixin


def test_drop_column_default_is_true():
    """DROP COLUMN is a baseline capability; the generic renderer covers it."""
    assert ConstraintMixin.supports_drop_column(None) is True


def test_no_dead_code_in_drop_column_default():
    """The default must be a single unambiguous answer, not dead code.

    Regression for a former ``return False`` followed by an unreachable
    ``return True``: the effective value was False despite the intended True,
    silently suppressing DROP COLUMN on backends that never overrode it.
    """
    source = inspect.getsource(ConstraintMixin.supports_drop_column)
    returns = [line.strip() for line in source.splitlines() if line.strip().startswith("return ")]
    assert len(returns) == 1, f"supports_drop_column has dead/ambiguous returns: {returns}"
    assert returns[0] == "return True"
