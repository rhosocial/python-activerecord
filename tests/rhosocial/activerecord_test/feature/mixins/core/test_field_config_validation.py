# tests/rhosocial/activerecord_test/feature/mixins/test_field_config_validation.py
"""Field-mixin configuration is validated at class-definition time.

A semantics mixin (``SoftDeleteMixin`` / ``TimestampMixin`` /
``OptimisticLockMixin``) declares *knobs* — class attributes naming a model
field. If the model does not declare that field, every generated query
silently references a column that does not exist.

The validation used to live in each mixin's ``__init__``, which never ran in
the documented declaration order::

    class Order(ActiveRecord, SoftDeleteMixin):   # mixin's __init__ is skipped

so a misconfigured model was accepted and only failed much later, at query
time. It now runs from the metaclass feature-handler hook
(``ActiveRecordMetaclass.__new__`` step 4), which fires after the class
object exists and ``model_fields`` is complete. These tests pin that
contract: the check must be independent of base-class order, and it must
reject the class as soon as the class statement is evaluated.

No database is involved, so no provider fixture is required.
"""

# tests/rhosocial/activerecord_test/feature/mixins/test_field_config_validation.py
from datetime import datetime
from typing import Optional

import pytest
from pydantic import Field

from rhosocial.activerecord.field import (
    DefaultSoftDeleteMixin,
    OptimisticLockMixin,
    SoftDeleteMixin,
    TimestampMixin,
)
from rhosocial.activerecord.model import ActiveRecord

# ---------------------------------------------------------------------------
# Rejection — a misconfigured model must not become a class
# ---------------------------------------------------------------------------


def test_soft_delete_rejects_missing_field_with_active_record_first():
    """The documented order (mixin last) must still be validated.

    This is the regression: with validation in ``__init__`` this class
    statement succeeded and the model broke at query time instead.
    """

    with pytest.raises(TypeError, match="deleted_at_field\\(\\)"):
        type(  # noqa: F841  -- the statement itself is the assertion
            "Order",
            (ActiveRecord, SoftDeleteMixin),
            {
                "table_name": classmethod(lambda cls: "rej_soft_a"),
                "primary_key": classmethod(lambda cls: "id"),
                "__annotations__": {"id": Optional[int]},
                "deleted_at_field": classmethod(lambda cls: "no_such_field"),
            },
        )


def test_soft_delete_rejects_missing_field_with_mixin_first():
    """The other base order must behave identically."""
    with pytest.raises(TypeError, match="deleted_at_field\\(\\)"):
        type(  # noqa: F841
            "Order",
            (SoftDeleteMixin, ActiveRecord),
            {
                "table_name": classmethod(lambda cls: "rej_soft_b"),
                "primary_key": classmethod(lambda cls: "id"),
                "__annotations__": {"id": Optional[int]},
                "deleted_at_field": classmethod(lambda cls: "no_such_field"),
            },
        )


def test_timestamp_rejects_missing_field():
    with pytest.raises(TypeError, match="created_at_field\\(\\)"):
        type(  # noqa: F841
            "Article",
            (ActiveRecord, TimestampMixin),
            {
                "table_name": classmethod(lambda cls: "rej_ts"),
                "primary_key": classmethod(lambda cls: "id"),
                "__annotations__": {"id": Optional[int]},
                "created_at_field": classmethod(lambda cls: "no_such_field"),
            },
        )


def test_optimistic_lock_rejects_missing_field():
    with pytest.raises(TypeError, match="version_field\\(\\)"):
        type(  # noqa: F841
            "Account",
            (ActiveRecord, OptimisticLockMixin),
            {
                "table_name": classmethod(lambda cls: "rej_lock"),
                "primary_key": classmethod(lambda cls: "id"),
                "__annotations__": {"id": Optional[int]},
                "version_field": classmethod(lambda cls: "no_such_field"),
            },
        )


def test_optimistic_lock_rejects_non_positive_increment():
    with pytest.raises(ValueError, match="version_increment_by\\(\\)"):
        type(  # noqa: F841
            "Account",
            (ActiveRecord, OptimisticLockMixin),
            {
                "table_name": classmethod(lambda cls: "rej_lock_inc"),
                "primary_key": classmethod(lambda cls: "id"),
                "__annotations__": {"id": Optional[int], "version": int},
                "version": 1,
                "version_increment_by": classmethod(lambda cls: 0),
            },
        )


# ---------------------------------------------------------------------------
# Acceptance — correct configuration must be unaffected
# ---------------------------------------------------------------------------


def test_soft_delete_accepts_declared_field():
    class Doc(ActiveRecord, SoftDeleteMixin):
        @classmethod
        def table_name(cls):
            return "ok_soft"

        @classmethod
        def primary_key(cls):
            return "id"

        id: Optional[int] = None
        deleted_at: Optional[datetime] = Field(default=None)

    assert Doc.deleted_at_field() in Doc.model_fields


def test_timestamp_accepts_declared_fields():
    class Post(ActiveRecord, TimestampMixin):
        @classmethod
        def table_name(cls):
            return "ok_ts"

        @classmethod
        def primary_key(cls):
            return "id"

        id: Optional[int] = None
        created_at: datetime = Field(default_factory=datetime.now)
        updated_at: datetime = Field(default_factory=datetime.now)

    assert Post.created_at_field() in Post.model_fields
    assert Post.updated_at_field() in Post.model_fields


def test_optimistic_lock_accepts_declared_field():
    class Account(ActiveRecord, OptimisticLockMixin):
        @classmethod
        def table_name(cls):
            return "ok_lock"

        @classmethod
        def primary_key(cls):
            return "id"

        id: Optional[int] = None
        version: int = 1

    assert Account.version_field() in Account.model_fields


def test_default_soft_delete_mixin_declares_its_own_field():
    """The ``Default*`` mixins ship the field, so they validate themselves."""

    class Doc(ActiveRecord, DefaultSoftDeleteMixin):
        @classmethod
        def table_name(cls):
            return "ok_default_soft"

        @classmethod
        def primary_key(cls):
            return "id"

        id: Optional[int] = None

    assert "deleted_at" in Doc.model_fields


def test_validation_does_not_mask_other_feature_handlers():
    """Adding the mixin's handler must not displace the inherited ones.

    ``get_feature_handlers`` merges ``_feature_handlers`` across the MRO; a
    mixin contributing its own entry must leave the core handlers (DDL
    annotations, derived fields, adapters, column names) in place, or a model
    would silently lose them.
    """

    class Doc(ActiveRecord, SoftDeleteMixin):
        @classmethod
        def table_name(cls):
            return "ok_handlers"

        @classmethod
        def primary_key(cls):
            return "id"

        id: Optional[int] = None
        deleted_at: Optional[datetime] = Field(default=None)

    names = {h.__name__ for h in Doc.get_feature_handlers()}
    assert "FieldConfigValidationHandler" in names
    for inherited in (
        "DDLAnnotationHandler",
        "DerivedFieldHandler",
        "AdapterAnnotationHandler",
        "ColumnNameAnnotationHandler",
    ):
        assert inherited in names, f"{inherited} was displaced"
