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

from .fields import DerivedField, UseAdapter, UseColumn


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

        # Validate no column_name conflicts with regular field column names
        regular_columns: set = set()
        try:
            all_hints = get_type_hints(new_class, include_extras=True)
        except (NameError, AttributeError, TypeError):
            all_hints = {}
        for fname, ann in all_hints.items():
            if fname in derived:
                continue
            if hasattr(ann, "__metadata__"):
                for meta in ann.__metadata__:
                    if isinstance(meta, UseColumn):
                        regular_columns.add(meta.column_name)
        for name, df in derived.items():
            if df.column_name and df.column_name in regular_columns:
                raise TypeError(
                    f"DerivedField '{name}' has UseColumn('{df.column_name}') which "
                    f"conflicts with a regular field's column name."
                )

        for name, df in derived.items():
            new_class.__derived_field_names__[id(df)] = name
            if df._source_id is not None:
                new_class.__derived_field_names__[df._source_id] = name
            setattr(new_class, name, df)

    @staticmethod
    def _extract(field_name: str, annotation: Any, owner: type) -> Optional[DerivedField]:
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

        # Form B: ClassVar[Annotated[T, DerivedField(...), UseColumn(...), UseAdapter(...)]]
        if hasattr(inner, "__metadata__") and hasattr(inner, "__args__"):
            base_type = inner.__args__[0] if inner.__args__ else Any
            found_df: Optional[DerivedField] = None
            found_column: Optional[UseColumn] = None
            found_adapter: Optional[UseAdapter] = None

            for meta in inner.__metadata__:
                if isinstance(meta, DerivedField):
                    found_df = meta
                elif isinstance(meta, UseColumn):
                    found_column = meta
                elif isinstance(meta, UseAdapter):
                    found_adapter = meta

            if found_df is not None:
                df = copy(found_df)
                df.field_name = field_name
                df._source_id = id(found_df)
                df.python_type = base_type
                if found_column is not None:
                    df.column_name = found_column.column_name
                if found_adapter is not None:
                    df.adapter = found_adapter.adapter
                return df

        return None
