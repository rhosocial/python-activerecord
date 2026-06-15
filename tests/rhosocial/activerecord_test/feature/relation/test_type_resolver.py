# tests/rhosocial/activerecord_test/feature/relation/test_type_resolver.py
"""Tests for the centralized type_resolver module."""

from typing import ClassVar, ForwardRef

import pytest
from pydantic import BaseModel

from rhosocial.activerecord.relation.base import RelationManagementMixin
from rhosocial.activerecord.relation.descriptors import BelongsTo, HasMany
from rhosocial.activerecord.relation.type_resolver import (
    resolve_model_fqn,
    evaluate_annotation,
    resolve_relation_type,
    _build_owner_namespace,
    _unwrap_generic_type,
)


class TestResolveModelFqn:
    def test_module_level_class(self):
        fqn = resolve_model_fqn(BaseModel)
        assert fqn == "pydantic.main.BaseModel"

    def test_nested_class_qname(self):
        class Outer:
            class Inner:
                pass

        fqn = resolve_model_fqn(Outer.Inner)
        assert "Outer.Inner" in fqn


class TestEvaluateAnnotation:
    def test_evaluate_string_ref(self):
        class MyModel(RelationManagementMixin, BaseModel):
            id: int

        result = evaluate_annotation("MyModel", MyModel)
        assert result is MyModel

    def test_evaluate_with_extra_ns(self):
        class Owner(RelationManagementMixin, BaseModel):
            id: int

        class Dynamic:
            pass

        result = evaluate_annotation("Dynamic", Owner, extra_ns={"Dynamic": Dynamic})
        assert result is Dynamic

    def test_evaluate_unresolvable_name(self):
        class Owner(RelationManagementMixin, BaseModel):
            id: int

        with pytest.raises(NameError, match="name 'NoSuchModel' is not defined"):
            evaluate_annotation("NoSuchModel", Owner)

    def test_evaluate_forward_ref_direct(self):
        class MyModel(RelationManagementMixin, BaseModel):
            id: int

        ref = ForwardRef("MyModel")
        result = evaluate_annotation(ref, MyModel)
        assert result is MyModel

    def test_evaluate_via_frame_fallback(self):
        class MyModel(RelationManagementMixin, BaseModel):
            id: int

        class Owner(RelationManagementMixin, BaseModel):
            id: int
            rel: ClassVar[BelongsTo["MyModel"]] = BelongsTo(foreign_key="my_id")

        result = evaluate_annotation("MyModel", Owner)
        assert result is MyModel


class TestBuildOwnerNamespace:
    def test_includes_owner_types(self):
        class Inner:
            pass

        class Outer(RelationManagementMixin, BaseModel):
            id: int

        setattr(Outer, "Inner", Inner)
        ns = _build_owner_namespace(Outer)
        assert "Outer" in ns
        assert "Inner" in ns
        assert ns["Inner"] is Inner


class TestUnwrapGenericType:
    def test_simple_generic(self):
        result = _unwrap_generic_type(HasMany[str], __import__("typing"))
        assert result is str

    def test_classvar_wrapped(self):
        from typing import ClassVar as CV

        cv = CV[BelongsTo[str]]
        result = _unwrap_generic_type(cv, __import__("typing"))
        assert result is str


class TestResolveRelationType:
    def test_resolve_missing_field(self):
        class Owner(RelationManagementMixin, BaseModel):
            id: int

        assert resolve_relation_type(Owner, "no_such_field") is None

    def test_resolve_type_direct(self):
        class Owner(RelationManagementMixin, BaseModel):
            id: int
            ref: int = 0

        assert resolve_relation_type(Owner, "id") is int

    def test_resolve_string_annotation(self):
        Owner = type("Owner", (dict,), {"__annotations__": {"ref": "int"}})
        result = resolve_relation_type(Owner, "ref")
        assert result is int


class TestDescriptorCompat:
    """Sync/async descriptor mixing is rejected at class creation time.
    These tests are covered comprehensively in test_descriptor_compat.py.
    This file focuses on the type_resolver utilities.
    """