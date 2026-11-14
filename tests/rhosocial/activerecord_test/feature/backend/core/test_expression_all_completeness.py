# tests/rhosocial/activerecord_test/feature/backend/test_expression_all_completeness.py
"""Guard: every class imported in expression/__init__.py must appear in __all__.

This catches the failure mode where a new expression class is imported in
``expression/__init__.py`` but forgotten from the ``__all__`` list — meaning
``from ... import *`` and ``__all__``-based discovery silently miss it.
"""

import ast
import pytest

pytestmark = [pytest.mark.feature, pytest.mark.backend]


def _collect_imported_names(module_path: str) -> set:
    """Return {name} for every name imported in ``expression/__init__.py``."""
    with open(module_path) as f:
        tree = ast.parse(f.read(), filename=module_path)
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                names.add(alias.asname or alias.name)
    return names


def _collect_all_names(module_path: str) -> set:
    """Return {name} for every name in the ``__all__`` list."""
    with open(module_path) as f:
        tree = ast.parse(f.read(), filename=module_path)
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__all__":
                    return {elt.value for elt in node.value.elts if isinstance(elt, ast.Constant)}
    return set()


def test_imported_names_in_all():
    """Every name imported in expression/__init__.py must appear in __all__."""
    import rhosocial.activerecord.backend.expression as expr_pkg
    init_path = expr_pkg.__spec__.submodule_search_locations[0] + "/__init__.py"

    imported = _collect_imported_names(init_path)
    exported = _collect_all_names(init_path)

    # Internal/private names that are imported but intentionally not exported
    allowlist = {
        "Enum",          # from enum import Enum
        "runtime_checkable",  # from typing
    }

    missing = imported - exported - allowlist
    assert not missing, (
        f"expression/__init__.py imports {len(missing)} name(s) not in __all__: "
        f"{sorted(missing)}. Add them to __all__ or to allowlist in this test."
    )
