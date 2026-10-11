# src/rhosocial/activerecord/field/field_config.py
"""Class-construction-time validation for field mixin configuration.

Semantics mixins (``SoftDeleteMixin``, ``TimestampMixin``,
``OptimisticLockMixin``) declare *knobs* — class attributes naming a model
field, e.g. ``__deleted_at_field__ = "deleted_at"``. The model must actually
declare that field, otherwise every generated query silently references a
column that does not exist.

Why a metaclass feature handler
-------------------------------
The obvious place for such a check is the mixin's ``__init__``, and that is
where it used to live. It does not work: in the documented declaration order

.. code-block:: python

    class Order(ActiveRecord, SoftDeleteMixin):
        ...

Pydantic's ``BaseModel.__init__`` precedes the mixin in the MRO, so the
mixin's ``__init__`` never runs and the validation is skipped entirely.

``__init_subclass__`` is not a usable replacement either — it fires while
the class body is still being built, before Pydantic has collected
``model_fields``, so ``model_fields`` is empty and every knob would look
missing.

:class:`FieldConfigValidationHandler` therefore runs from the metaclass
feature-handler hook (:meth:`ActiveRecordMetaclass.__new__` step 4), which
executes after the class object exists and ``model_fields`` is complete.
Two consequences, both improvements over the previous behaviour:

* the check is independent of base-class order, and
* it fires at **class definition time** rather than at first instantiation,
  so a misconfigured model fails at import instead of at first query.
"""

from typing import Any


class FieldConfigValidationHandler:
    """Runs every mixin-declared ``_validate_model_config`` on the new class.

    A mixin opts in by declaring this handler in ``_feature_handlers`` and
    exposing a ``_validate_model_config`` classmethod. The handler discovers
    those classmethods by walking the MRO and reading each class's own
    ``__dict__`` — it never infers anything from attribute names, so adding
    a mixin is a one-line declaration rather than a naming convention to
    remember.
    """

    @classmethod
    def handle(cls, model_class: Any) -> None:
        """Validate the configuration of every field mixin on *model_class*."""
        for klass in model_class.__mro__:
            validator = klass.__dict__.get("_validate_model_config")
            if validator is not None:
                # A classmethod accessed via __dict__ is already bound to
                # `klass`; rebind it to the model under construction so the
                # error message names the model, not the mixin.
                validator.__func__(model_class)


__all__ = ["FieldConfigValidationHandler"]
