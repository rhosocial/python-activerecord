# tests/rhosocial/activerecord_test/feature/expression/test_registry_ownership.py
"""Each owner maintains its own artifact registry.

An expression artifact is data: parameters only, no dialect (§4.11.3). The
dialect is only ever needed to *render*, so a read does not require one, and a
registry is the only name authority a read needs.

Ownership follows the same split:

* core assembles core's kinds (:func:`core_registry`);
* a backend assembles its own kinds on top of core's, by composition
  (``registry_for_packages(<its package>, base=core_registry())``), never by
  core listing backends and never by merging two backends;
* an assembled registry is frozen, so two readers of the same published table
  cannot change each other's answers.

These tests state those four facts directly, plus the selection order
``deserialize`` uses when it has to pick a table.
"""

import pytest

from rhosocial.activerecord.backend.dialect.base import SQLDialectBase
from rhosocial.activerecord.backend.expression.bases import BaseExpression
from rhosocial.activerecord.backend.expression.core import Column
from rhosocial.activerecord.backend.expression.registry import (
    ExpressionRegistry,
    RegistryError,
    RegistryReason,
)
from rhosocial.activerecord.backend.expression.serialization import (
    ExpressionDeserializationError,
    core_registry,
    default_registry,
    deserialize,
    deserialize_json,
    deserialize_xml,
    registry_for_packages,
    serialize,
    serialize_json,
    serialize_xml,
)
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect
from rhosocial.activerecord.backend.impl.dummy.registry import backend_registry as dummy_registry
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
from rhosocial.activerecord.backend.impl.sqlite.expression.vacuum import SQLiteVacuumStatement
from rhosocial.activerecord.backend.impl.sqlite.registry import backend_registry as sqlite_registry

# ---------------------------------------------------------------------------
# Core owns only core's kinds
# ---------------------------------------------------------------------------


def test_core_registry_holds_core_kinds_and_no_backend_kind():
    """Core's table is exactly core's: no bundled backend leaks into it."""
    registry = core_registry()
    assert registry.is_frozen
    assert "query_statement" in registry.node_kinds()
    assert "integer_value" in registry.node_kinds()
    assert "column" in registry.node_kinds()

    kinds = registry.node_kinds()
    assert not [kind for kind in kinds if kind.startswith("sqlite_")], (
        "core's registry carries SQLite kinds; a backend's kinds belong to "
        "that backend's own registry"
    )
    assert not [kind for kind in kinds if "dummy" in kind], (
        "core's registry carries dummy kinds; a backend's kinds belong to "
        "that backend's own registry"
    )

    # A backend kind is refused by name, not resolved to a stale class.
    with pytest.raises(RegistryError) as caught:
        registry.resolve_node("sqlite_vacuum_statement")
    assert "sqlite_vacuum_statement" in str(caught.value)


def test_the_deprecated_name_is_the_core_registry():
    """``default_registry`` survives only as an alias of ``core_registry``."""
    assert default_registry() is core_registry()


# ---------------------------------------------------------------------------
# A read does not need a dialect
# ---------------------------------------------------------------------------


def test_deserialize_without_a_dialect_constructs_an_unbound_tree():
    """The artifact is data; construction does not need a dialect.

    The tree comes back unbound and renders through ``to_sql(dialect)`` — the
    dialect-free path. That is what lets an artifact be read before anyone has
    decided which backend will execute it.
    """
    built_with = DummyDialect()
    artifact = serialize(Column(built_with, "id"))

    restored = deserialize(artifact)
    assert isinstance(restored, Column)
    assert restored.name == "id"
    assert restored.to_sql(SQLiteDialect((3, 38, 0))) == ('"id"', ())

    # All three channels accept the dialect-free form.
    assert isinstance(deserialize_json(serialize_json(Column(built_with, "id"))), Column)
    assert isinstance(deserialize_xml(serialize_xml(Column(built_with, "id"))), Column)


# ---------------------------------------------------------------------------
# A backend kind is read through the dialect's own registry
# ---------------------------------------------------------------------------


def test_backend_registries_compose_core_and_stay_apart():
    """Each backend's table is core plus its own; two backends are not merged."""
    sqlite = sqlite_registry()
    dummy = dummy_registry()

    assert sqlite is SQLiteDialect().artifact_registry()
    assert dummy is DummyDialect().artifact_registry()
    assert sqlite.is_frozen and dummy.is_frozen

    assert "sqlite_vacuum_statement" in sqlite.node_kinds()
    assert "sqlite_vacuum_statement" not in dummy.node_kinds()
    assert "_dummy_type_definition" in dummy.node_kinds()
    assert "_dummy_type_definition" not in sqlite.node_kinds()

    # Core is the base of both, so a core kind resolves through either.
    for registry in (sqlite, dummy):
        assert registry.resolve_node("column") is Column


def test_the_base_dialect_answers_with_core_kinds():
    """The base dialect owns no backend, so its table is core's."""
    assert SQLDialectBase().artifact_registry() is core_registry()


def test_deserialize_selects_the_dialects_registry_for_backend_kinds():
    """``deserialize(spec, dialect)`` resolves through ``artifact_registry()``."""
    sqlite = SQLiteDialect((3, 38, 0))
    artifact = serialize(SQLiteVacuumStatement(sqlite))

    restored = deserialize(artifact, sqlite)
    assert isinstance(restored, SQLiteVacuumStatement)
    assert restored.to_sql() == ("VACUUM", ())

    # Without a dialect the selection falls back to core, which refuses the
    # backend kind by name instead of guessing.
    with pytest.raises(ExpressionDeserializationError) as caught:
        deserialize(artifact)
    assert "sqlite_vacuum_statement" in str(caught.value)


def test_an_explicit_registry_wins_over_the_dialect():
    """Selection order is explicit registry, dialect, core — in that order."""
    sqlite = SQLiteDialect((3, 38, 0))
    artifact = serialize(SQLiteVacuumStatement(sqlite))

    # The dialect could resolve this kind, but the caller's table was chosen.
    with pytest.raises(ExpressionDeserializationError) as caught:
        deserialize(artifact, sqlite, registry=core_registry())
    assert "sqlite_vacuum_statement" in str(caught.value)


# ---------------------------------------------------------------------------
# A published registry is frozen; a different set is a new registry
# ---------------------------------------------------------------------------


def test_a_frozen_registry_refuses_every_mutation_by_name():
    frozen = ExpressionRegistry().freeze()
    assert frozen.is_frozen
    assert frozen.freeze() is frozen  # idempotent

    cases = (
        lambda: frozen.register_node(Column),
        lambda: frozen.register_value_kinds(),
        lambda: frozen.unregister_node("column"),
        lambda: frozen.disable("column"),
        lambda: frozen.enable("column"),
    )
    for mutate in cases:
        with pytest.raises(RegistryError) as caught:
            mutate()
        message = str(caught.value)
        assert caught.value.reason is RegistryReason.REGISTRY_FROZEN
        assert "frozen" in message
        assert "merged()/registry_for_packages()" in message
        assert caught.value.kind


def test_a_twin_of_a_frozen_registry_is_mutable_and_cannot_change_it():
    """Narrowing a published table means copying it, never editing it."""
    frozen = core_registry()
    twin = frozen.twin()
    assert not twin.is_frozen

    twin.unregister_node("query_statement")
    assert "query_statement" not in twin.node_kinds()
    assert "query_statement" in frozen.node_kinds()
    assert "query_statement" in core_registry().node_kinds()


def test_merged_returns_the_union_frozen_and_leaves_both_inputs_alone():
    first = ExpressionRegistry()
    first.register_node(Column)
    second = ExpressionRegistry()
    second.register_value_kinds()

    fused = first.merged(second)
    assert fused.is_frozen
    assert "column" in fused.node_kinds()
    assert "integer_value" in fused.node_kinds()
    assert first.node_kinds() == ("column",)
    assert "column" not in second.node_kinds()


def test_merged_names_both_classes_when_a_kind_collides():
    """Two different classes cannot both answer one kind."""
    alien_a = type("Column", (BaseExpression,), {"__module__": "tests.alien_a"})
    alien_b = type("Column", (BaseExpression,), {"__module__": "tests.alien_b"})

    first = ExpressionRegistry()
    first.register_node(alien_a)
    second = ExpressionRegistry()
    second.register_node(alien_b)

    with pytest.raises(RegistryError) as caught:
        first.merged(second)
    message = str(caught.value)
    assert "column" in message
    assert "tests.alien_a.Column" in message
    assert "tests.alien_b.Column" in message


def test_registry_for_packages_is_the_one_assembly_entry_point():
    """Packages are a caller's argument, not a list core has to maintain."""
    assembled = registry_for_packages(
        "rhosocial.activerecord.backend.expression.core",
        freeze=False,
    )
    assert not assembled.is_frozen
    assert "column" in assembled.node_kinds()

    # A package that is not importable is skipped, not an error.
    with_missing = registry_for_packages(
        "rhosocial.activerecord.backend.expression.core",
        "no.such.package",
    )
    assert with_missing.is_frozen
    assert "column" in with_missing.node_kinds()
