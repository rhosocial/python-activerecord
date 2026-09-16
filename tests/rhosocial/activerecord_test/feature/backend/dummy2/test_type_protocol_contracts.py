# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_type_protocol_contracts.py
"""Layered correspondence contracts for the data-type protocol.

Verifies the namespace rules and the naming-family discipline that the
``DataType`` / ``DDLTypeSupport`` contracts formalize:

* ``format_data_type_*`` / ``supports_data_type_*`` 1:1 correspondence
  (dummy dialect);
* ``supports_data_types()`` mapping shape — ``{generic name: concrete
  DataType class}`` with ``value.name == key``;
* core-defined types own **pure** generic names;
* backend-defined types (SQLite impl) own **backend-prefixed** names;
* honest-unsupported semantics: rendering a type the dialect does not
  implement raises ``TypeError`` — the dialect never fakes support.
"""

import inspect
import re

import pytest

from rhosocial.activerecord.backend.expression.types import DataType
import rhosocial.activerecord.backend.expression.types as core_types  # noqa: F401
import rhosocial.activerecord.backend.impl.sqlite.expression.types as sqlite_types  # noqa: F401
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect

_CORE_TYPES_PREFIX = "rhosocial.activerecord.backend.expression.types"
_SQLITE_TYPES_PREFIX = "rhosocial.activerecord.backend.impl.sqlite"

_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")
_FORMAT_RE = re.compile(r"^format_data_type_([a-z][a-z0-9_]*)$")
_SUPPORTS_RE = re.compile(r"^supports_data_type_([a-z][a-z0-9_]*)$")


def _concrete_subclasses():
    """All concrete ``DataType`` subclasses currently loaded."""
    seen = set()
    stack = [DataType]
    while stack:
        klass = stack.pop()
        if klass in seen:
            continue
        seen.add(klass)
        stack.extend(klass.__subclasses__())
    return [klass for klass in seen if not inspect.isabstract(klass)]


def test_dummy_format_supports_correspondence():
    """Every ``format_data_type_X`` has a ``supports_data_type_X`` and vice versa."""
    format_names = set()
    supports_names = set()
    for member in dir(DummyDialect):
        match = _FORMAT_RE.match(member)
        if match:
            format_names.add(match.group(1))
            continue
        match = _SUPPORTS_RE.match(member)
        if match:
            supports_names.add(match.group(1))
    assert format_names, "dummy dialect must implement the format family"
    assert supports_names, "dummy dialect must implement the supports family"
    assert format_names == supports_names


def test_dummy_supports_data_types_mapping():
    """``supports_data_types()`` is ``{generic name: concrete DataType class}``."""
    dialect = DummyDialect()
    mapping = dialect.supports_data_types()
    assert isinstance(mapping, dict)
    assert mapping, "dummy dialect must support at least one type"
    for key, value in mapping.items():
        assert _NAME_RE.match(key), f"mapping key {key!r} must be a valid name"
        assert isinstance(value, type) and issubclass(value, DataType), \
            f"mapping value for {key!r} must be a DataType subclass"
        assert value.name == key, \
            f"mapping value {value.__name__}.name={value.name!r} != key {key!r}"
    # The mapping must cover exactly the format-family names of the dialect.
    format_names = {
        _FORMAT_RE.match(member).group(1)
        for member in dir(DummyDialect) if _FORMAT_RE.match(member)
    }
    assert set(mapping) == format_names


def test_sqlite_format_supports_correspondence():
    """SQLite dialect: format family and supports family must correspond 1:1."""
    from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
    format_names = {
        _FORMAT_RE.match(member).group(1)
        for member in dir(SQLiteDialect) if _FORMAT_RE.match(member)
    }
    supports_names = {
        _SUPPORTS_RE.match(member).group(1)
        for member in dir(SQLiteDialect) if _SUPPORTS_RE.match(member)
    }
    assert format_names, "sqlite dialect must implement the format family"
    assert supports_names, "sqlite dialect must implement the supports family"
    assert format_names == supports_names, (
        f"format-only: {sorted(format_names - supports_names)}, "
        f"supports-only: {sorted(supports_names - format_names)}"
    )


def test_sqlite_supports_data_types_mapping_merges_namespaces():
    """SQLite mapping covers both generic and sqlite_-namespaced entries."""
    from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
    mapping = SQLiteDialect().supports_data_types()
    assert "varchar" in mapping and "json" in mapping
    assert any(key.startswith("sqlite_") for key in mapping), (
        "backend dialect must merge its namespaced types into the mapping"
    )
    for key, value in mapping.items():
        assert value.name == key


def test_core_type_names_are_pure():
    """Concrete core types declare pure generic names (no backend prefix)."""
    core_types_found = [
        klass for klass in _concrete_subclasses()
        if klass is not DataType
        and klass.__module__.startswith(_CORE_TYPES_PREFIX)
    ]
    assert core_types_found, "core type classes must be loaded"
    for klass in core_types_found:
        assert klass.name is not None, \
            f"{klass.__module__}.{klass.__name__} must declare a name"
        assert _NAME_RE.match(klass.name), \
            f"core type {klass.__name__} has non-pure name {klass.name!r}"


def test_backend_type_names_are_prefixed():
    """Concrete SQLite impl types declare ``sqlite_``-prefixed names."""
    sqlite_types_found = [
        klass for klass in _concrete_subclasses()
        if klass.__module__.startswith(_SQLITE_TYPES_PREFIX)
    ]
    assert sqlite_types_found, "SQLite type classes must be loaded"
    for klass in sqlite_types_found:
        assert klass.name.startswith("sqlite_"), \
            f"backend type {klass.__name__} name {klass.name!r} " \
            f"must start with 'sqlite_'"


def test_unsupported_type_raises():
    """A type the dialect does not implement raises on render (no fake support).

    The throwaway type is defined through ``type()`` with a backend
    namespaced module path and a ``dummy_`` prefixed name so it satisfies
    the namespace enforcement while remaining unimplemented by the dummy
    dialect.
    """
    namespace = {
        "name": "dummy_nosuchtype",
        "__module__": "rhosocial.activerecord.backend.impl.dummy.expression.types",
        "__qualname__": "FakeZzzType",
        "__doc__": "Throwaway type no dialect implements.",
    }
    FakeZzzType = type("FakeZzzType", (DataType,), namespace)
    assert not hasattr(DummyDialect, "format_data_type_dummy_nosuchtype")
    assert not hasattr(DummyDialect, "supports_data_type_dummy_nosuchtype")
    dialect = DummyDialect()
    with pytest.raises(TypeError):
        FakeZzzType(dialect).to_sql()
