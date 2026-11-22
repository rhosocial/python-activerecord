# src/rhosocial/activerecord/base/field_adapter_mixin.py
"""
This module provides a mixin for handling field-specific type adapters.
"""

import types
from typing import (
    Any,
    ClassVar,
    Dict,
    List,
    Optional,
    Tuple,
    Type,
    Union,
    get_args,
    get_origin,
    get_type_hints,
)

from ..backend.type_adapter import SQLTypeAdapter
from .fields import UseAdapter


def unwrap_optional_type(annotation: Any) -> Optional[Any]:
    """Return the payload of ``Optional[T]`` / ``Union[T, None]``.

    Args:
        annotation: A resolved field annotation.

    Returns:
        ``T`` when the annotation is a single-type optional, otherwise the
        annotation itself. A multi-type union returns ``None`` because there is
        no single Python type to suggest an adapter for.
    """
    origin = get_origin(annotation)
    is_union = origin is Union or (
        hasattr(types, "UnionType") and origin is types.UnionType
    )
    if not is_union:
        return annotation
    args = [arg for arg in get_args(annotation) if arg is not type(None)]
    if len(args) == 1:
        return args[0]
    return None


def adapter_class_identity(adapter: SQLTypeAdapter) -> Tuple[str, str]:
    """Return the identity used to match a declared adapter with an inventory."""
    adapter_cls = type(adapter)
    return adapter_cls.__module__, adapter_cls.__qualname__


class AdapterAnnotationHandler:
    """
    A feature handler for processing `@UseAdapter` annotations on model fields.
    """

    @staticmethod
    def handle(new_class: Type[Any]):
        """
        Parses annotations and attaches the `__field_adapters__` dictionary.

        A field may declare several `UseAdapter` entries (one per backend); they
        are collected in declaration order, which is also their priority order
        when more than one of them is available in a backend's inventory.
        """
        field_adapters: Dict[str, List[Tuple[SQLTypeAdapter, Type]]] = {}

        # Use get_type_hints() with include_extras=True to properly resolve
        # Annotated types. This is necessary because when using
        # 'from __future__ import annotations', __annotations__ stores
        # string representations of types rather than actual type objects,
        # which don't have __origin__, __args__, and __metadata__ attributes.
        try:
            hints = get_type_hints(new_class, include_extras=True)
        except (NameError, AttributeError, TypeError):
            # Fallback to __annotations__ if get_type_hints fails
            # (e.g., due to forward references or other issues)
            hints = getattr(new_class, "__annotations__", {})

        for field_name, field_type in hints.items():
            adapter_info = AdapterAnnotationHandler._extract_and_validate_adapter(field_name, field_type)
            if adapter_info:
                field_adapters[field_name] = adapter_info

        new_class.__field_adapters__ = field_adapters

    @staticmethod
    def _extract_and_validate_adapter(
        field_name: str, field_type: Any
    ) -> Optional[List[Tuple[SQLTypeAdapter, Type]]]:
        """
        Extracts `(SQLTypeAdapter, target_db_type)` pairs from a field's type
        annotation when `Annotated` and `UseAdapter` are used.

        Returns:
            The declared pairs in declaration order, or ``None`` when the field
            declares no `UseAdapter`.
        """
        # In Python 3.8, `Annotated` from `typing_extensions` can have identity
        # issues when compared with `is`. A structural check for `__metadata__`
        # is more robust. This is not necessary for Python 3.9+ where `Annotated`
        # is native and behaves consistently.
        if not (
            hasattr(field_type, "__origin__")
            and hasattr(field_type, "__args__")
            and hasattr(field_type, "__metadata__")
        ):
            return None

        use_adapters_found = [arg for arg in field_type.__metadata__ if isinstance(arg, UseAdapter)]
        if not use_adapters_found:
            return None

        # ``UseAdapter.__init__`` already validated that the adapter conforms to
        # the SQLTypeAdapter protocol; a field may declare one entry per backend.
        return [
            (use_adapter_instance.adapter, use_adapter_instance.target_db_type)
            for use_adapter_instance in use_adapters_found
        ]


class FieldAdapterMixin:
    """
    Provides field-specific SQL type adapter functionality.

    It provides runtime methods and registers the AdapterAnnotationHandler
    to be run by the metaclass system at class creation time.
    """

    _feature_handlers = [AdapterAnnotationHandler]

    __field_adapters__: ClassVar[Dict[str, List[Tuple[SQLTypeAdapter, Type]]]] = {}

    @classmethod
    def get_field_type_adapters(cls) -> Dict[str, Optional[Tuple[SQLTypeAdapter, Type]]]:
        """Select the runtime adapter for every model field.

        The selection is per field, in this order:

        1. the field's declared `UseAdapter` entries, in declaration order;
           the first one whose adapter class exists in this backend's
           inventory wins, so a field can declare one adapter per backend;
           when none of the declared adapters is in the inventory (custom
           adapters are not registered by the backend), the first declaration
           is used as-is;
        2. otherwise the backend's default suggestions for the field's Python
           type (the core table completed by the backend);
        3. otherwise ``None``, meaning the value is passed through untouched.

        The returned target type is the *driver* type declared by
        ``UseAdapter`` (or by the backend's suggestion table). On the read path
        the target is the field's Python type, which is available from the
        model's annotations.

        Returns:
            A new dictionary mapping field names to ``(adapter, target_type)``
            pairs, or ``None`` for fields that need no conversion.
        """
        backend = cls.backend()
        declared_map = getattr(cls, "__field_adapters__", None) or {}

        inventory: set = set()
        inventory_getter = getattr(backend, "get_type_adapters", None)
        if callable(inventory_getter):
            for adapter in inventory_getter():
                inventory.add(adapter_class_identity(adapter))

        suggestions = backend.suggest_data_adapters().table

        adapters_by_field: Dict[str, Optional[Tuple[SQLTypeAdapter, Type]]] = {}
        for field_name, field_info in cls.model_fields.items():
            declared = declared_map.get(field_name)
            if declared:
                selected = None
                for adapter, target in declared:
                    if adapter_class_identity(adapter) in inventory:
                        selected = (adapter, target)
                        break
                adapters_by_field[field_name] = selected or declared[0]
                continue

            lookup_type = unwrap_optional_type(field_info.annotation)
            adapters_by_field[field_name] = cls._lookup_default_adapter(suggestions, lookup_type)
        return adapters_by_field

    @classmethod
    def _field_python_type(cls, field_name: str) -> Optional[Any]:
        """Return the field's declared Python type, unwrapping ``Optional``."""
        field_info = cls.model_fields.get(field_name)
        if field_info is None:
            return None
        return unwrap_optional_type(field_info.annotation)

    @classmethod
    def _adapt_fields_for_write(cls, data: Dict[str, Any]) -> Dict[str, Any]:
        """Convert field values to the driver representation before binding.

        Every field with a selected adapter is converted exactly once, through
        ``adapter.to_database(value, declared_target)``. SQL expressions are
        left untouched: they are rendered by the statement builder, not bound
        as values.

        Args:
            data: Mapping of field names to Python values.

        Returns:
            A new mapping with converted values, keyed by field name.
        """
        adapters = cls.get_field_type_adapters()
        converted: Dict[str, Any] = {}
        for field_name, value in data.items():
            adapter_info = adapters.get(field_name)
            if adapter_info is not None and not hasattr(value, "to_sql"):
                adapter, target = adapter_info
                converted[field_name] = adapter.to_database(value, target)
            else:
                converted[field_name] = value
        return converted

    @classmethod
    def _adapt_row_from_database(cls, row: Dict[str, Any]) -> Dict[str, Any]:
        """Map a raw driver row to field names and convert its values.

        The backend returns column names and untouched driver values; this is
        the ActiveRecord half of the contract, the exact mirror of
        :meth:`_adapt_fields_for_write`.

        The field's declared annotation is passed as ``original_type`` in
        addition to the unwrapped Python type: a driver can store one database
        value for two Python types (Oracle cannot tell ``''`` from ``NULL``), so
        an adapter's ``_on_none_from_database`` has to know whether the field
        admits ``None`` to decide between the payload and the default.

        Args:
            row: Mapping of column names to raw driver values.

        Returns:
            A new mapping keyed by field name with converted values.
        """
        adapters = cls.get_field_type_adapters()
        column_to_field = cls.get_column_to_field_map()
        converted: Dict[str, Any] = {}
        for column_name, value in row.items():
            field_name = column_to_field.get(column_name, column_name)
            adapter_info = adapters.get(field_name)
            target = cls._field_python_type(field_name)
            if adapter_info is None or target is None:
                converted[field_name] = value
                continue
            adapter, _ = adapter_info
            field_info = cls.model_fields.get(field_name)
            if field_info is None:
                converted[field_name] = adapter.from_database(value, target)
            else:
                converted[field_name] = adapter.from_database(
                    value, target, original_type=field_info.annotation
                )
        return converted

    @classmethod
    def _adapt_result_rows(cls, result: Any) -> Any:
        """Convert RETURNING rows of a write result to field values.

        Backends return raw column-keyed rows; the model converts them exactly
        the same way it converts a SELECT result.

        Args:
            result: The backend write result (it carries a ``data`` list).

        Returns:
            The same result object, with ``data`` converted in place.
        """
        data = getattr(result, "data", None)
        if isinstance(data, list) and data:
            result.data = [
                cls._adapt_row_from_database(row) if isinstance(row, dict) else row
                for row in data
            ]
        return result

    @staticmethod
    def _lookup_default_adapter(
        suggestions: Dict[Type, Tuple[SQLTypeAdapter, Type]],
        annotation: Any,
    ) -> Optional[Tuple[SQLTypeAdapter, Type]]:
        """Find the backend default suggestion for an annotation's Python type."""
        if annotation is None:
            return None
        # ``list[str]`` / ``dict[str, Any]`` are parametrised containers: their
        # adapter is registered for the bare ``list`` / ``dict`` type.
        lookup_type = get_origin(annotation) or annotation
        suggestion = suggestions.get(lookup_type)
        if suggestion is not None:
            return suggestion
        # Enumerations (and any other subclass) are registered under their base
        # type; pick the most derived matching key deterministically.
        if isinstance(lookup_type, type):
            matches = [
                key
                for key in suggestions
                if isinstance(key, type)
                and key is not lookup_type
                and issubclass(lookup_type, key)
            ]
            if matches:
                matches.sort(key=lambda key: (-len(key.__mro__), key.__module__, key.__qualname__))
                return suggestions[matches[0]]
        return None
