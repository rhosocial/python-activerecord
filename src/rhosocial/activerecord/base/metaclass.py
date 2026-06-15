# src/rhosocial/activerecord/base/metaclass.py
"""
This module defines the metaclass for the ActiveRecord base model.
"""

from pydantic._internal._model_construction import ModelMetaclass


class ActiveRecordMetaclass(ModelMetaclass):
    """
    The foundational metaclass for all ActiveRecord models.

    It discovers and runs 'feature handlers' by calling the `get_feature_handlers`
    method on the newly created class. This method is expected to be defined in
    the `IActiveRecord` interface.
    """

    def __new__(cls, name, bases, namespace, **kwargs):
        # Step 1: Let Pydantic/Python create the class object first.
        try:
            new_class = super().__new__(cls, name, bases, namespace, **kwargs)
        except RuntimeError as e:
            # TODO: This is a temporary workaround and the descriptor registration
            #       mechanism is very likely to be refactored later.
            #
            # Problem: Python 3.11 and earlier wrap exceptions raised in
            # __set_name__ with RuntimeError ("Error calling __set_name__ on ...").
            # Python 3.12+ (gh-77757) stopped wrapping them and propagates the
            # original exception directly. Unwrap here to provide a consistent
            # exception type across all supported Python versions so that
            # downstream tests can reliably assert on the original TypeError.
            #
            # Users should use relation descriptors correctly and NEVER mix sync
            # descriptors (BelongsTo/HasMany/HasOne) on async models or async
            # descriptors (AsyncBelongsTo/AsyncHasMany/AsyncHasOne) on sync models.
            # DO NOT rely on this framework-level type check for correctness in
            # production code — it exists primarily to catch accidental misuse
            # during development.
            cause = e.__cause__
            if cause is not None and isinstance(cause, TypeError):
                raise cause from None
            raise

        # Step 2: Get all handlers using the centralized method from the interface.
        # This check ensures that we only operate on classes that have this capability.
        if hasattr(new_class, "get_feature_handlers"):
            handlers = new_class.get_feature_handlers()

            # Step 3: Run the discovered handlers on the new class.
            for handler in handlers:
                # Assuming handlers have a static `handle` method.
                handler.handle(new_class)

        return new_class


class MetaclassMixin(metaclass=ActiveRecordMetaclass):
    """
    A dedicated mixin to attach the ActiveRecordMetaclass.

    Inheriting from this mixin enables the model class to participate in the
    metaclass-based feature handler system.
    """

    pass
