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
        new_class = super().__new__(cls, name, bases, namespace, **kwargs)

        # Step 2: Validate relation descriptor type compatibility.
        # Sync descriptors (BelongsTo/HasMany/HasOne) must not be used on async
        # models (AsyncActiveRecord), and async descriptors must not be used on
        # sync models.  This validation runs here (after __set_name__ has
        # registered all descriptors) rather than inside __set_name__ because
        # Python < 3.12 wraps exceptions raised in __set_name__ with
        # RuntimeError, which breaks downstream tests that catch TypeError.
        relations = new_class.__dict__.get("_relations_dict")
        if relations:
            from rhosocial.activerecord.relation.descriptors import (
                RelationDescriptor,
            )
            from rhosocial.activerecord.relation.async_descriptors import (
                AsyncRelationDescriptor,
            )
            from rhosocial.activerecord.interface import (
                IActiveRecord,
                IAsyncActiveRecord,
            )

            for rel_name, desc in relations.items():
                if isinstance(desc, RelationDescriptor) and issubclass(
                    new_class, IAsyncActiveRecord
                ):
                    raise TypeError(
                        f"Sync relation descriptor `{rel_name}` cannot be used "
                        f"on async model `{name}`. "
                        f"Use AsyncBelongsTo/AsyncHasMany/AsyncHasOne from "
                        f"rhosocial.activerecord.relation.async_descriptors "
                        f"instead."
                    )
                if (
                    isinstance(desc, AsyncRelationDescriptor)
                    and issubclass(new_class, IActiveRecord)
                    and not issubclass(new_class, IAsyncActiveRecord)
                ):
                    raise TypeError(
                        f"Async relation descriptor `{rel_name}` cannot be used "
                        f"on sync model `{name}`. "
                        f"Use BelongsTo/HasMany/HasOne from "
                        f"rhosocial.activerecord.relation.descriptors instead."
                    )

        # Step 3: Get all handlers using the centralized method from the interface.
        # This check ensures that we only operate on classes that have this capability.
        if hasattr(new_class, "get_feature_handlers"):
            handlers = new_class.get_feature_handlers()

            # Step 4: Run the discovered handlers on the new class.
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
