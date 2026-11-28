# tests/rhosocial/activerecord_test/feature/rules/backend/conftest.py
"""The subject for the generic layer's namespace rules.

Core is one side of the split: it owns the shared expression vocabulary and
names no implementation. Three fields say everything the rules need, and none of
them names a backend:

``prefix = None``
    There is no owner to write in front of a class, so the naming claim does not
    apply here. It is skipped as not applicable rather than satisfied by a list of
    names to avoid -- recognising "this name looks like some backend's" would
    require the knowledge this side is defined not to have.
``excluded_dirs = ("impl",)``
    ``impl`` is the extension point where concrete implementations are
    contributed. It is not part of the generic vocabulary, so the rules do not
    scan it; the packages there are described by whoever tests them.
``open_package_root = backend/impl``
    The umbrella every distribution contributes into must stay a namespace
    package, or a backend installed elsewhere becomes invisible.
"""

from __future__ import annotations

import importlib
from pathlib import Path

import pytest

from rhosocial.activerecord.testsuite.feature.rules.contracts.subject import (
    ExpressionSubject,
    Root,
)


def backend_root() -> Path:
    """The installed generic ``backend`` package directory."""
    package = importlib.import_module("rhosocial.activerecord.backend")
    for candidate in vars(package).get("__path__", ()):
        path = Path(candidate).resolve()
        if path.is_dir():
            return path
    raise AssertionError("the installed backend package exposes no directory")


@pytest.fixture
def subject() -> ExpressionSubject:
    """Core's generic layer, described without naming any implementation."""
    root = backend_root()
    return ExpressionSubject(
        label="core",
        roots=(Root("core", root, "rhosocial.activerecord.backend"),),
        excluded_dirs=("impl",),
        open_package_root=root / "impl",
    )
