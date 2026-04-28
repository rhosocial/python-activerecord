# tests/rhosocial/activerecord_test/feature/backend/named_query/conftest.py
"""
Test fixtures for named query tests.

This module provides fixtures for testing named query functionality.
"""
import types
from unittest.mock import MagicMock
import pytest


@pytest.fixture
def mock_dialect():
    """Create a mock dialect for testing."""
    dialect = MagicMock()
    dialect._prepare_value = MagicMock(side_effect=lambda v: v)
    dialect._format_value = MagicMock(
        side_effect=lambda v: f"'{v}'" if isinstance(v, str) else str(v)
    )
    return dialect


@pytest.fixture
def mock_expression():
    """Create a mock BaseExpression that implements Executable."""
    from rhosocial.activerecord.backend.expression.executable import Executable
    from rhosocial.activerecord.backend.schema import StatementType

    class MockExpression(Executable):
        def __init__(self, sql_template: str = "SELECT 1", params: tuple = ()):
            self._sql_template = sql_template
            self._params = params

        @property
        def statement_type(self) -> StatementType:
            return StatementType.SELECT

        def to_sql(self) -> tuple:
            return self._sql_template, self._params

    return MockExpression


@pytest.fixture
def mock_non_expression():
    """Create a mock object that does NOT implement Executable."""
    return "just a string"


@pytest.fixture
def mock_backend(mock_dialect):
    """Create a mock backend for testing."""
    from unittest.mock import MagicMock

    backend = MagicMock()
    backend.dialect = mock_dialect
    backend.execute = MagicMock(return_value=MagicMock(data=[], affected_rows=0))
    return backend


@pytest.fixture
def bad_query_module():
    """Create a module with non-expression-returning functions."""

    def bad_func(dialect):
        return "not an expression"

    module = types.ModuleType("test_bad")
    module.bad_func = bad_func
    module.__all__ = ["bad_func"]
    return module


class TestCliArgs:
    """Helper class to create mock CLI args for testing."""

    @staticmethod
    def create(qualified_name: str, **kwargs):
        """Create a mock args namespace."""
        from argparse import Namespace

        defaults = {
            "qualified_name": qualified_name,
            "example": None,
            "params": [],
            "describe": False,
            "dry_run": False,
            "list_queries": False,
            "force": False,
            "explain": False,
            "rich_ascii": False,
        }
        defaults.update(kwargs)
        return Namespace(**defaults)