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

    It discovers and runs 'feature handlers' declared in the inheritance
    hierarchy (MRO) of the class being created. A mixin can register a handler
    by defining a `_feature_handlers` class attribute.
    """

    def __new__(cls, name, bases, namespace, **kwargs):
        # Step 1: Let Pydantic/Python create the class object first.
        # This gives us access to the complete MRO.
        new_class = super().__new__(cls, name, bases, namespace, **kwargs)

        # Step 2: Discover handlers by walking the MRO.
        # We use a dict as an ordered set to collect unique handlers.
        collected_handlers = {}

        # We iterate through the MRO in reverse. This ensures that handlers
        # from base classes are registered before handlers from child classes.
        for mro_class in reversed(new_class.mro()):
            if hasattr(mro_class, '_feature_handlers'):
                for handler in mro_class._feature_handlers:
                    collected_handlers[handler] = True  # Add to ordered set

        # Step 3: Run the discovered handlers on the new class.
        for handler_class in collected_handlers.keys():
            # Assuming handlers have a static `handle` method.
            handler_class.handle(new_class)

        return new_class


class MetaclassMixin(metaclass=ActiveRecordMetaclass):
    """
    A dedicated mixin to attach the ActiveRecordMetaclass.

    Inheriting from this mixin enables the model class to participate in the
    metaclass-based feature handler system.
    """
    pass
