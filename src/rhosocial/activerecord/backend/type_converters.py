# src/rhosocial/activerecord/backend/type_converters.py
"""
Type converter system for database backends.

This module defines the core interfaces and base classes for the protocol-based
type conversion system, allowing flexible mapping between Python objects and
database types.
"""

from abc import ABC
from typing import Any, Dict, List, Optional, Protocol, Type, Set, runtime_checkable


# Import DatabaseType from original dialect module

@runtime_checkable
class TypeConverter(Protocol):
    """
    Type converter protocol.

    This protocol defines the interface that all type converters must implement.
    Type converters are responsible for converting values between Python and
    database representations based on the target/source type.
    """

    def can_handle(self, value: Any, target_type: Any = None) -> bool:
        """
        Check if this converter can handle the given value or type.

        Args:
            value: The value to check
            target_type: Optional target type (e.g., DatabaseType enum or string)

        Returns:
            bool: True if this converter can handle the conversion
        """
        ...

    def to_database(self, value: Any, target_type: Any = None) -> Any:
        """
        Convert a Python value to its database representation.

        Args:
            value: The Python value to convert
            target_type: Optional target type hint

        Returns:
            The converted value ready for database storage
        """
        ...

    def from_database(self, value: Any, source_type: Any = None) -> Any:
        """
        Convert a database value to its Python representation.

        Args:
            value: The database value to convert
            source_type: Optional source type hint

        Returns:
            The converted Python value
        """
        ...

    @property
    def priority(self) -> int:
        """
        Get the priority of this converter.

        Higher priority converters are checked first when looking for a suitable converter.

        Returns:
            int: Priority value (higher means higher priority)
        """
        ...


class BaseTypeConverter(ABC):
    """
    Base implementation of the TypeConverter protocol.

    This class provides default implementations for the TypeConverter interface
    and serves as a base class for specific type converters.
    """

    @property
    def priority(self) -> int:
        """Default priority is 0."""
        return 0

    def can_handle(self, value: Any, target_type: Any = None) -> bool:
        """
        Default implementation always returns False.

        Subclasses should override this method to provide specific type checking.
        """
        return False

    def to_database(self, value: Any, target_type: Any = None) -> Any:
        """
        Default implementation returns the value unchanged.

        Subclasses should override this method to provide specific conversion logic.
        """
        return value

    def from_database(self, value: Any, source_type: Any = None) -> Any:
        """
        Default implementation returns the value unchanged.

        Subclasses should override this method to provide specific conversion logic.
        """
        return value


class TypeRegistry:
    """
    Registry for type converters.

    This class maintains a registry of type converters and provides methods
    to register, unregister, and find converters.
    """

    def __init__(self):
        """Initialize an empty type registry."""
        self._converters: List[TypeConverter] = []
        self._name_to_converter: Dict[str, TypeConverter] = {}
        self._type_to_converter: Dict[Any, TypeConverter] = {}
        self._cache = {}  # Cache for converter lookups

    def register(self, converter: TypeConverter, names: Optional[List[str]] = None,
                 types: Optional[List[Any]] = None) -> None:
        """
        Register a type converter.

        Args:
            converter: The converter to register
            names: Optional list of type names this converter handles
            types: Optional list of type objects this converter handles
        """
        self._converters.append(converter)
        # Sort converters by priority (highest first)
        self._converters.sort(key=lambda c: c.priority, reverse=True)

        # Register name mappings
        if names:
            for name in names:
                self._name_to_converter[name.lower()] = converter

        # Register type mappings
        if types:
            for type_obj in types:
                self._type_to_converter[type_obj] = converter

        # Clear cache after registering a new converter
        self._cache.clear()

    def unregister(self, converter_class: Type[Any]) -> None:
        """
        Unregister all converters of a specific class.

        Args:
            converter_class: The class of converters to unregister
        """
        self._converters = [c for c in self._converters if not isinstance(c, converter_class)]

        # Update name mappings
        self._name_to_converter = {name: converter for name, converter in self._name_to_converter.items()
                                   if not isinstance(converter, converter_class)}

        # Update type mappings
        self._type_to_converter = {type_obj: converter for type_obj, converter in self._type_to_converter.items()
                                   if not isinstance(converter, converter_class)}

        # Clear cache after unregistering
        self._cache.clear()

    def find_converter(self, value: Any, target_type: Any = None) -> Optional[TypeConverter]:
        """
        Find a converter that can handle the given value and target type.

        Args:
            value: The value to convert
            target_type: Optional target type hint

        Returns:
            The first converter that can handle the conversion, or None
        """
        # Check cache first
        cache_key = (type(value), target_type)
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Check type-specific converter first
        if target_type is not None and target_type in self._type_to_converter:
            converter = self._type_to_converter[target_type]
            if converter.can_handle(value, target_type):
                self._cache[cache_key] = converter
                return converter

        # Check all registered converters
        for converter in self._converters:
            if converter.can_handle(value, target_type):
                self._cache[cache_key] = converter
                return converter

        # No suitable converter found
        self._cache[cache_key] = None
        return None

    def find_converter_by_name(self, type_name: str) -> Optional[TypeConverter]:
        """
        Find a converter by type name.

        Args:
            type_name: The type name to look up

        Returns:
            Registered converter for this type name, or None
        """
        return self._name_to_converter.get(type_name.lower())

    def to_database(self, value: Any, target_type: Any = None) -> Any:
        """
        Convert a value to its database representation.

        Args:
            value: The value to convert
            target_type: Optional target type hint

        Returns:
            The converted value
        """
        if value is None:
            return None

        converter = self.find_converter(value, target_type)
        if converter:
            return converter.to_database(value, target_type)
        return value  # Return unchanged if no converter found

    def from_database(self, value: Any, source_type: Any = None) -> Any:
        """
        Convert a database value to its Python representation.

        Args:
            value: The database value to convert
            source_type: Optional source type hint

        Returns:
            The converted Python value
        """
        if value is None:
            return None

        converter = self.find_converter(value, source_type)
        if converter:
            return converter.from_database(value, source_type)
        return value  # Return unchanged if no converter found

    def clear_cache(self) -> None:
        """Clear the converter lookup cache."""
        self._cache.clear()

    def get_registered_types(self) -> Set[Any]:
        """
        Get all registered type objects.

        Returns:
            Set of registered type objects
        """
        return set(self._type_to_converter.keys())

    def get_registered_names(self) -> Set[str]:
        """
        Get all registered type names.

        Returns:
            Set of registered type names
        """
        return set(self._name_to_converter.keys())
