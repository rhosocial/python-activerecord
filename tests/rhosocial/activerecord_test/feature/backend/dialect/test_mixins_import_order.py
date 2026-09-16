# tests/rhosocial/activerecord_test/feature/backend/dialect/test_mixins_import_order.py
"""Import-order and circular-import guards for the dialect mixins package.

``FunctionCallMixin.format_function_call`` references several modules lazily
(``...expression``, ``..protocols``, ``.filter_clause``, and
``...expression.statements.filter_clause``). This module proves that importing
the mixins package — and exercising the filter-clause path — works from a
fresh interpreter regardless of which module is imported first, so a future
top-level import cannot silently introduce a cycle.
"""

import subprocess
import sys

import pytest

pytestmark = [pytest.mark.feature, pytest.mark.backend]


# Each entry is a module imported first in a fresh interpreter. Importing a
# deep submodule first is the strictest case: the parent packages execute
# their ``__init__`` while this module is already on the stack.
_IMPORT_FIRST_TARGETS = [
    "rhosocial.activerecord.backend.dialect.mixins.function",
    "rhosocial.activerecord.backend.dialect.mixins.expression",
    "rhosocial.activerecord.backend.dialect.mixins",
    "rhosocial.activerecord.backend.expression.statements.filter_clause",
    "rhosocial.activerecord.backend.dialect",
]


def _run_in_fresh_interpreter(body: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-c", body],
        capture_output=True,
        text=True,
    )


@pytest.mark.parametrize("target", _IMPORT_FIRST_TARGETS)
def test_module_imports_without_cycle(target: str):
    """Importing any mixins submodule first must not raise ImportError."""
    result = _run_in_fresh_interpreter(f"import {target}")
    assert result.returncode == 0, (
        f"Fresh import of {target!r} failed:\n{result.stderr}"
    )


def test_format_function_call_filter_path_in_fresh_interpreter():
    """Exercise the lazy ``FilterClauseExpression`` import path in isolation.

    Importing the ``function`` mixin module first, then formatting a filtered
    function call on a fully composed dialect, must succeed. A top-level import
    of ``FilterClauseExpression`` would make this fail with an ImportError or
    AttributeError.
    """
    body = (
        "import rhosocial.activerecord.backend.dialect.mixins.function  # noqa: F401\n"
        "from rhosocial.activerecord.backend.impl.dummy import DummyDialect\n"
        "from rhosocial.activerecord.backend.expression.core import FunctionCall, Column\n"
        "\n"
        "d = DummyDialect()\n"
        "call = FunctionCall(d, 'SUM', Column(d, 'amount'))\n"
        "call.filter_predicate = (Column(d, 'amount') > 0)\n"
        "sql, params = d.format_function_call(call)\n"
        "assert 'FILTER (WHERE' in sql, sql\n"
    )
    result = _run_in_fresh_interpreter(body)
    assert result.returncode == 0, (
        "format_function_call filter path raised in a fresh interpreter:\n"
        f"{result.stderr}"
    )
