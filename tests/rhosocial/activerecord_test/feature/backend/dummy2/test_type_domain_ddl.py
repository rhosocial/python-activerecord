# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_type_domain_ddl.py
"""Tests for the generic TYPE and DOMAIN DDL protocols."""

import pytest

from rhosocial.activerecord.backend.dialect import protocols as dialect_protocols
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.dialect.mixins import (
    DataTypeMixin,
    DDLTypeMixin,
    DomainMixin,
    UserDefinedTypeMixin,
)
from rhosocial.activerecord.backend.expression import FunctionCall, Literal
from rhosocial.activerecord.backend.expression.serialization import (
    deserialize,
    deserialize_json,
    deserialize_xml,
    serialize,
    serialize_json,
    serialize_xml,
)
from rhosocial.activerecord.backend.expression.statements import (
    AddDomainCheckAction,
    AlterDomainExpression,
    AlterTypeExpression,
    CreateDomainExpression,
    CreateTypeExpression,
    DomainCheckConstraint,
    DomainNullability,
    DomainValueExpression,
    DropDomainCheckAction,
    DropDomainDefaultAction,
    DropDomainExpression,
    DropDomainNotNullAction,
    DropTypeExpression,
    RenameDomainAction,
    SetDomainDefaultAction,
    SetDomainNotNullAction,
)
from rhosocial.activerecord.backend.expression.types import IntegerType
from rhosocial.activerecord.backend.impl.dummy.expression import (
    _DummyTypeAlterAction,
    _DummyTypeDefinition,
)
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect


def _condition(dialect):
    return DomainValueExpression(dialect) > Literal(dialect, 0, inline_literals=True)


def test_legacy_names_are_same_objects():
    assert DDLTypeMixin is DataTypeMixin
    assert dialect_protocols.DDLTypeSupport is dialect_protocols.DataTypeSupport


def test_dummy_protocols_and_mixins_are_concrete(dummy_dialect):
    assert isinstance(dummy_dialect, dialect_protocols.DataTypeSupport)
    assert isinstance(dummy_dialect, dialect_protocols.UserDefinedTypeSupport)
    assert isinstance(dummy_dialect, dialect_protocols.DomainSupport)
    assert isinstance(dummy_dialect, UserDefinedTypeMixin)
    assert isinstance(dummy_dialect, DomainMixin)


def test_type_lifecycle(dummy_dialect):
    definition = _DummyTypeDefinition(dummy_dialect, IntegerType(dummy_dialect))
    create = CreateTypeExpression(
        dummy_dialect,
        "status",
        definition,
        schema_name="app",
        if_not_exists=True,
    )
    create_sql, create_params = create.to_sql()
    assert "CREATE TYPE IF NOT EXISTS" in create_sql
    assert '"app"."status"' in create_sql
    assert "AS INTEGER" in create_sql
    assert create_params == ()

    action = _DummyTypeAlterAction(dummy_dialect, "status_v2")
    alter = AlterTypeExpression(
        dummy_dialect,
        "status",
        [action],
        schema_name="app",
        if_exists=True,
    )
    alter_sql, alter_params = alter.to_sql()
    assert "ALTER TYPE IF EXISTS" in alter_sql
    assert "RENAME TO" in alter_sql
    assert alter_params == ()

    drop = DropTypeExpression(
        dummy_dialect,
        "status",
        schema_name="app",
        if_exists=True,
    )
    drop_sql, drop_params = drop.to_sql()
    assert "DROP TYPE IF EXISTS" in drop_sql
    assert '"app"."status"' in drop_sql
    assert drop_params == ()


def test_domain_lifecycle(dummy_dialect):
    condition = _condition(dummy_dialect)
    check = DomainCheckConstraint(dummy_dialect, condition, name="positive")
    create = CreateDomainExpression(
        dummy_dialect,
        "positive",
        IntegerType(dummy_dialect),
        default=Literal(dummy_dialect, 1, inline_literals=True),
        nullability=DomainNullability.NOT_NULL,
        checks=[check],
        collation="pg_catalog.default",
    )
    create_sql, create_params = create.to_sql()
    assert "CREATE DOMAIN" in create_sql
    assert "VALUE > 0" in create_sql
    assert "DEFAULT 1" in create_sql
    assert 'COLLATE "pg_catalog"."default"' in create_sql
    assert "CONSTRAINT" in create_sql
    assert "CHECK" in create_sql
    assert "NOT NULL" in create_sql
    assert create_params == ()

    nullable = CreateDomainExpression(
        dummy_dialect,
        "nullable",
        IntegerType(dummy_dialect),
        nullability=DomainNullability.NULLABLE,
    )
    nullable_sql, nullable_params = nullable.to_sql()
    assert nullable_sql.endswith(" NULL")
    assert nullable_params == ()

    actions = (
        (SetDomainDefaultAction(dummy_dialect, 2), "SET DEFAULT 2"),
        (DropDomainDefaultAction(dummy_dialect), "DROP DEFAULT"),
        (SetDomainNotNullAction(dummy_dialect), "SET NOT NULL"),
        (DropDomainNotNullAction(dummy_dialect), "DROP NOT NULL"),
        (AddDomainCheckAction(dummy_dialect, check), "ADD CONSTRAINT"),
        (DropDomainCheckAction(dummy_dialect, name="positive"), "DROP CONSTRAINT"),
        (RenameDomainAction(dummy_dialect, "positive_v2"), "RENAME TO"),
    )
    for action, fragment in actions:
        alter = AlterDomainExpression(dummy_dialect, "positive", [action])
        alter_sql, alter_params = alter.to_sql()
        assert f'ALTER DOMAIN "positive" {fragment}' in alter_sql
        assert alter_params == ()

    drop = DropDomainExpression(dummy_dialect, "positive")
    drop_sql, drop_params = drop.to_sql()
    assert drop_sql == 'DROP DOMAIN "positive"'
    assert drop_params == ()


def test_dummy_rejects_multiple_ddl_actions(dummy_dialect):
    action = _DummyTypeAlterAction(dummy_dialect)
    with pytest.raises(UnsupportedFeatureError):
        AlterTypeExpression(dummy_dialect, "status", [action, action]).to_sql()

    domain_action = DropDomainDefaultAction(dummy_dialect)
    with pytest.raises(UnsupportedFeatureError):
        AlterDomainExpression(
            dummy_dialect,
            "domain",
            [domain_action, domain_action],
        ).to_sql()


def test_dummy_action_nodes_check_parent_capabilities(dummy_dialect, monkeypatch):
    definition = _DummyTypeDefinition(dummy_dialect, IntegerType(dummy_dialect))
    type_action = _DummyTypeAlterAction(dummy_dialect)
    domain_action = DropDomainDefaultAction(dummy_dialect)

    monkeypatch.setattr(type(dummy_dialect), "supports_type_objects", lambda self: False)
    with pytest.raises(UnsupportedFeatureError):
        definition.to_sql()

    monkeypatch.setattr(type(dummy_dialect), "supports_type_objects", lambda self: True)
    monkeypatch.setattr(type(dummy_dialect), "supports_alter_type", lambda self: False)
    with pytest.raises(UnsupportedFeatureError):
        type_action.to_sql()

    monkeypatch.setattr(type(dummy_dialect), "supports_alter_type", lambda self: True)
    monkeypatch.setattr(type(dummy_dialect), "supports_alter_domain", lambda self: False)
    with pytest.raises(UnsupportedFeatureError):
        domain_action.to_sql()


def test_dummy_unrenderable_capabilities_are_false(dummy_dialect):
    assert dummy_dialect.supports_multiple_type_alter_actions() is False
    assert dummy_dialect.supports_multiple_domain_alter_actions() is False
    assert dummy_dialect.supports_drop_domain_if_exists() is False
    assert dummy_dialect.supports_drop_domain_cascade() is False
    assert dummy_dialect.supports_drop_domain_restrict() is False
    assert dummy_dialect.supports_unnamed_domain_check_drop() is False


def test_type_constructor_validation(dummy_dialect):
    definition = _DummyTypeDefinition(dummy_dialect, IntegerType(dummy_dialect))
    with pytest.raises(ValueError):
        CreateTypeExpression(dummy_dialect, "", definition)
    with pytest.raises(TypeError):
        CreateTypeExpression(dummy_dialect, "status", object())
    with pytest.raises(ValueError):
        CreateTypeExpression(
            dummy_dialect,
            "status",
            definition,
            if_not_exists=True,
            or_replace=True,
        )
    with pytest.raises(ValueError):
        AlterTypeExpression(dummy_dialect, "status", [])
    with pytest.raises(TypeError):
        AlterTypeExpression(dummy_dialect, "status", [object()])
    with pytest.raises(ValueError):
        DropTypeExpression(dummy_dialect, " ")


def test_domain_constructor_validation(dummy_dialect):
    with pytest.raises(TypeError):
        CreateDomainExpression(dummy_dialect, "domain", object())
    with pytest.raises(TypeError):
        CreateDomainExpression(
            dummy_dialect,
            "domain",
            IntegerType(dummy_dialect),
            nullability=None,
        )
    normalized = CreateDomainExpression(
        dummy_dialect,
        "domain",
        IntegerType(dummy_dialect),
        nullability="NOT NULL",
    )
    assert normalized.nullability is DomainNullability.NOT_NULL
    with pytest.raises(TypeError):
        DomainCheckConstraint(dummy_dialect, object())
    with pytest.raises(ValueError):
        AlterDomainExpression(dummy_dialect, "domain", [])
    with pytest.raises(ValueError):
        RenameDomainAction(dummy_dialect, "")


def test_domain_capability_gating(dummy_dialect, monkeypatch):
    named = CreateDomainExpression(
        dummy_dialect,
        "domain",
        IntegerType(dummy_dialect),
        checks=[
            DomainCheckConstraint(
                dummy_dialect,
                _condition(dummy_dialect),
                name="named",
            )
        ],
    )
    monkeypatch.setattr(type(dummy_dialect), "supports_named_domain_checks", lambda self: False)
    with pytest.raises(UnsupportedFeatureError):
        named.to_sql()

    monkeypatch.setattr(type(dummy_dialect), "supports_named_domain_checks", lambda self: True)
    monkeypatch.setattr(type(dummy_dialect), "supports_multiple_domain_checks", lambda self: False)
    multiple = CreateDomainExpression(
        dummy_dialect,
        "domain",
        IntegerType(dummy_dialect),
        checks=[
            DomainCheckConstraint(dummy_dialect, _condition(dummy_dialect)),
            DomainCheckConstraint(dummy_dialect, _condition(dummy_dialect)),
        ],
    )
    with pytest.raises(UnsupportedFeatureError):
        multiple.to_sql()

    monkeypatch.setattr(
        type(dummy_dialect),
        "supports_unnamed_domain_check_drop",
        lambda self: False,
    )
    with pytest.raises(UnsupportedFeatureError):
        DropDomainCheckAction(dummy_dialect).to_sql()


def test_domain_ddl_rejects_bind_parameters(dummy_dialect):
    default = FunctionCall(dummy_dialect, "COALESCE", Literal(dummy_dialect, 1))
    expression = CreateDomainExpression(
        dummy_dialect,
        "domain",
        IntegerType(dummy_dialect),
        default=default,
    )
    with pytest.raises(ValueError, match="bind parameters"):
        expression.to_sql()

    condition = DomainValueExpression(dummy_dialect) == Literal(dummy_dialect, 1)
    check = DomainCheckConstraint(dummy_dialect, condition)
    with pytest.raises(ValueError, match="bind parameters"):
        check.to_sql()


def test_domain_string_default_is_escaped(dummy_dialect):
    expression = CreateDomainExpression(
        dummy_dialect,
        "domain",
        IntegerType(dummy_dialect),
        default="O'Reilly",
    )
    sql, params = expression.to_sql()
    assert "DEFAULT 'O''Reilly'" in sql
    assert params == ()


def test_sqlite_type_and_domain_fail_fast():
    dialect = SQLiteDialect(version=(3, 45, 0))
    definition = _DummyTypeDefinition(dialect, IntegerType(dialect))
    with pytest.raises(UnsupportedFeatureError):
        CreateTypeExpression(dialect, "status", definition).to_sql()
    with pytest.raises(UnsupportedFeatureError):
        DropTypeExpression(dialect, "status").to_sql()
    with pytest.raises(UnsupportedFeatureError):
        CreateDomainExpression(dialect, "domain", IntegerType(dialect)).to_sql()
    with pytest.raises(UnsupportedFeatureError):
        DropDomainExpression(dialect, "domain").to_sql()
    with pytest.raises(UnsupportedFeatureError):
        DomainValueExpression(dialect).to_sql()
    with pytest.raises(UnsupportedFeatureError):
        DomainCheckConstraint(dialect, _condition(dialect)).to_sql()


def test_sqlite_new_capabilities_are_false():
    dialect = SQLiteDialect(version=(3, 45, 0))
    for name in (
        "supports_type_objects",
        "supports_create_type",
        "supports_alter_type",
        "supports_drop_type",
        "supports_create_type_if_not_exists",
        "supports_create_type_or_replace",
        "supports_alter_type_if_exists",
        "supports_drop_type_if_exists",
        "supports_multiple_type_alter_actions",
        "supports_domains",
        "supports_create_domain",
        "supports_alter_domain",
        "supports_drop_domain",
        "supports_domain_default",
        "supports_domain_checks",
        "supports_named_domain_checks",
        "supports_multiple_domain_checks",
        "supports_domain_collation",
        "supports_multiple_domain_alter_actions",
        "supports_drop_domain_if_exists",
        "supports_drop_domain_cascade",
        "supports_drop_domain_restrict",
        "supports_unnamed_domain_check_drop",
    ):
        assert getattr(dialect, name)() is False, name
    assert dialect.supports_domain_nullability(DomainNullability.NOT_NULL) is False
    assert dialect.supports_type_definition(_DummyTypeDefinition) is False
    assert dialect.supports_type_alter_action(_DummyTypeAlterAction) is False
    assert dialect.supports_alter_domain_action(SetDomainDefaultAction) is False


def test_core_type_and_domain_roundtrips(dummy_dialect):
    definition = _DummyTypeDefinition(dummy_dialect, IntegerType(dummy_dialect))
    action = _DummyTypeAlterAction(dummy_dialect, "status_v2")
    expressions = (
        definition,
        action,
        CreateTypeExpression(dummy_dialect, "status", definition),
        AlterTypeExpression(dummy_dialect, "status", [action]),
        DropTypeExpression(dummy_dialect, "status"),
        CreateDomainExpression(dummy_dialect, "domain", IntegerType(dummy_dialect)),
        AlterDomainExpression(
            dummy_dialect,
            "domain",
            [DropDomainDefaultAction(dummy_dialect)],
        ),
        DropDomainExpression(dummy_dialect, "domain"),
    )
    codecs = (
        (serialize, deserialize),
        (serialize_json, deserialize_json),
        (serialize_xml, deserialize_xml),
    )
    for expression in expressions:
        for encoder, decoder in codecs:
            restored = decoder(encoder(expression), dummy_dialect)
            assert type(restored) is type(expression)
            assert encoder(restored) == encoder(expression)
