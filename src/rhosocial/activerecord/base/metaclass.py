# src/rhosocial/activerecord/base/metaclass.py
"""
This module defines the metaclass for the ActiveRecord base model.
"""
import inspect
from typing import get_origin, get_args, Dict, Any, Tuple, Type, Optional, List

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

        # Step 2: Get all handlers using the centralized method from the interface.
        # This check ensures that we only operate on classes that have this capability.
        if hasattr(new_class, 'get_feature_handlers'):
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
