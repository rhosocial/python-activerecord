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
from typing import ClassVar, Optional

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

    with pytest.raises(TypeError, match="__deleted_at_field__"):
        type(  # noqa: F841  -- the statement itself is the assertion
            "Order",
            (ActiveRecord, SoftDeleteMixin),
            {
                "__table_name__": "rej_soft_a",
                "__primary_key__": "id",
                "__annotations__": {"id": Optional[int]},
                "__deleted_at_field__": "no_such_field",
            },
        )


def test_soft_delete_rejects_missing_field_with_mixin_first():
    """The other base order must behave identically."""
    with pytest.raises(TypeError, match="__deleted_at_field__"):
        type(  # noqa: F841
            "Order",
            (SoftDeleteMixin, ActiveRecord),
            {
                "__table_name__": "rej_soft_b",
                "__primary_key__": "id",
                "__annotations__": {"id": Optional[int]},
                "__deleted_at_field__": "no_such_field",
            },
        )


def test_timestamp_rejects_missing_field():
    with pytest.raises(TypeError, match="__created_at_field__"):
        type(  # noqa: F841
            "Article",
            (ActiveRecord, TimestampMixin),
            {
                "__table_name__": "rej_ts",
                "__primary_key__": "id",
                "__annotations__": {"id": Optional[int]},
                "__created_at_field__": "no_such_field",
            },
        )


def test_optimistic_lock_rejects_missing_field():
    with pytest.raises(TypeError, match="__version_field__"):
        type(  # noqa: F841
            "Account",
            (ActiveRecord, OptimisticLockMixin),
            {
                "__table_name__": "rej_lock",
                "__primary_key__": "id",
                "__annotations__": {"id": Optional[int]},
                "__version_field__": "no_such_field",
            },
        )


def test_optimistic_lock_rejects_non_positive_increment():
    with pytest.raises(ValueError, match="__version_increment_by__"):
        type(  # noqa: F841
            "Account",
            (ActiveRecord, OptimisticLockMixin),
            {
                "__table_name__": "rej_lock_inc",
                "__primary_key__": "id",
                "__annotations__": {"id": Optional[int], "version": int},
                "version": 1,
                "__version_increment_by__": 0,
            },
        )


# ---------------------------------------------------------------------------
# Acceptance — correct configuration must be unaffected
# ---------------------------------------------------------------------------


def test_soft_delete_accepts_declared_field():
    class Doc(ActiveRecord, SoftDeleteMixin):
        __table_name__ = "ok_soft"
        __primary_key__: ClassVar[str] = "id"

        id: Optional[int] = None
        deleted_at: Optional[datetime] = Field(default=None)

    assert Doc.__deleted_at_field__ in Doc.model_fields


def test_timestamp_accepts_declared_fields():
    class Post(ActiveRecord, TimestampMixin):
        __table_name__ = "ok_ts"
        __primary_key__: ClassVar[str] = "id"

        id: Optional[int] = None
        created_at: datetime = Field(default_factory=datetime.now)
        updated_at: datetime = Field(default_factory=datetime.now)

    assert Post.__created_at_field__ in Post.model_fields
    assert Post.__updated_at_field__ in Post.model_fields


def test_optimistic_lock_accepts_declared_field():
    class Account(ActiveRecord, OptimisticLockMixin):
        __table_name__ = "ok_lock"
        __primary_key__: ClassVar[str] = "id"

        id: Optional[int] = None
        version: int = 1

    assert Account.__version_field__ in Account.model_fields


def test_default_soft_delete_mixin_declares_its_own_field():
    """The ``Default*`` mixins ship the field, so they validate themselves."""

    class Doc(ActiveRecord, DefaultSoftDeleteMixin):
        __table_name__ = "ok_default_soft"
        __primary_key__: ClassVar[str] = "id"

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
        __table_name__ = "ok_handlers"
        __primary_key__: ClassVar[str] = "id"

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
