# src/rhosocial/activerecord/base/derived_field_handler.py
"""
Feature handler for processing DerivedField annotations on model fields.
"""

from copy import copy
from typing import Any, ClassVar, Dict, Optional, Type, get_args, get_origin

try:
    from typing_extensions import get_type_hints
except ImportError:
    from typing import get_type_hints  # type: ignore[assignment]

from .fields import DerivedField


class DerivedFieldHandler:
    """
    Parses ClassVar[Annotated[T, DerivedField(...)]] and ClassVar[DerivedField] = DerivedField(...)
    forms, writing results to cls.__derived_fields__ and cls.__derived_field_names__.
    """

    @staticmethod
    def handle(new_class: Type[Any]):
        derived: Dict[str, DerivedField] = {}

        for klass in reversed(new_class.__mro__):
            try:
                hints = get_type_hints(klass, include_extras=True)
            except (NameError, AttributeError, TypeError):
                hints = getattr(klass, "__annotations__", {})

            for field_name, annotation in hints.items():
                df = DerivedFieldHandler._extract(field_name, annotation, klass)
                if df is not None:
                    derived[field_name] = df

        new_class.__derived_fields__ = derived
        new_class.__derived_field_names__ = {}
        for name, df in derived.items():
            new_class.__derived_field_names__[id(df)] = name
            if df._source_id is not None:
                new_class.__derived_field_names__[df._source_id] = name
            setattr(new_class, name, df)

    @staticmethod
    def _extract(field_name: str, annotation: Any, owner: type) -> Optional[DerivedField]:
        # Must be ClassVar[...] at the top level
        if get_origin(annotation) is not ClassVar:
            return None

        args = get_args(annotation)
        if not args:
            return None
        inner = args[0]

        # Form A: ClassVar[DerivedField] with class-level assignment
        val = vars(owner).get(field_name)
        if isinstance(val, DerivedField):
            df = copy(val)
            df.field_name = field_name
            df._source_id = id(val)
            return df

        # Form B: ClassVar[Annotated[T, DerivedField(...)]]
        if hasattr(inner, "__metadata__") and hasattr(inner, "__args__"):
            base_type = inner.__args__[0] if inner.__args__ else Any
            for meta in inner.__metadata__:
                if isinstance(meta, DerivedField):
                    df = copy(meta)
                    df.field_name = field_name
                    df._source_id = id(meta)
                    if df.python_type is Any:
                        df.python_type = base_type
                    return df

        return None
