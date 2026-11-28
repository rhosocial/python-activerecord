# tests/rhosocial/activerecord_test/feature/rules/sqlite/conftest.py
"""SQLite is a concrete backend, not part of the generic core subject."""

from __future__ import annotations

import importlib

import pytest

from rhosocial.activerecord.testsuite.feature.rules.backend.support import impl_root_of
from rhosocial.activerecord.testsuite.feature.rules.contracts.subject import (
    ExpressionSubject,
    Root,
)

IMPL = "rhosocial.activerecord.backend.impl.sqlite"
PREFIX = "SQLite"


@pytest.fixture
def subject() -> ExpressionSubject:
    expression = importlib.import_module(f"{IMPL}.expression")
    root = impl_root_of(expression)
    return ExpressionSubject(
        label="sqlite",
        roots=(Root("sqlite", root, IMPL),),
        prefix=PREFIX,
        open_package_root=root,
        impl_module_prefix=IMPL,
    )


@pytest.fixture
def registry() -> object:
    module = importlib.import_module(f"{IMPL}.expression_registry")
    return module.SQLITE_EXPRESSION_REGISTRY
