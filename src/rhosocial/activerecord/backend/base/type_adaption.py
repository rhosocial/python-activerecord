# src/rhosocial/activerecord/backend/base/type_adaption.py
from datetime import date, datetime, time
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple, Type, Union
from uuid import UUID

from ..type_adapter import (
    SQLTypeAdapter,
    DateTimeAdapter,
    JSONAdapter,
    UUIDAdapter,
    EnumAdapter,
    BooleanAdapter,
    DecimalAdapter,
)

#: Framework-level ``(Python type, driver type)`` suggestion base.
#:
#: This is the *generic* layer of the two-level suggestion scheme: the core
#: describes what a backend-agnostic driver is expected to accept for the
#: common Python types. Every backend starts from this table, then merges its
#: own entries on top (``super().get_default_adapter_suggestions()``), because
#: the concrete backend knows its driver better than the framework does.
#:
#: Types that a driver binds natively without any conversion (``str``, ``int``,
#: ``float``, ``bytes``) are intentionally absent: their absence means
#: "pass through untouched".
CORE_DEFAULT_TYPE_MAPPINGS: Tuple[Tuple[Type, Type], ...] = (
    (bool, int),
    (datetime, str),
    (date, str),
    (time, str),
    (Decimal, float),
    (UUID, str),
    (dict, str),
    (list, str),
    (Enum, str),
)


def merge_adapter_suggestions(
    base: Dict[Type, Tuple[SQLTypeAdapter, Type]],
    overrides: Iterable[Tuple[Type, Type]],
    adapter_registry: Any,
) -> Dict[Type, Tuple[SQLTypeAdapter, Type]]:
    """Merge backend-specific ``(Python type, driver type)`` pairs onto ``base``.

    The backend layer of the suggestion scheme: entries from ``overrides``
    replace the core defaults for the same Python type (the backend decides
    what its driver really accepts), and are resolved through the backend's
    own adapter registry so only adapters that backend registered are
    suggested.

    Args:
        base: Suggestions produced by the core/default layer (mutated copy is
            not kept; a new dict is returned).
        overrides: Backend-specific ``(Python type, driver type)`` pairs.
        adapter_registry: The backend's ``TypeRegistry``.

    Returns:
        A new mapping from Python type to ``(adapter, driver type)``.
    """
    suggestions: Dict[Type, Tuple[SQLTypeAdapter, Type]] = dict(base)
    for py_type, db_type in overrides:
        adapter = adapter_registry.get_adapter(py_type, db_type)
        if adapter is not None:
            suggestions[py_type] = (adapter, db_type)
    return suggestions


def sort_and_deduplicate_adapters(adapters: Iterable[SQLTypeAdapter]) -> List[SQLTypeAdapter]:
    """Deduplicate adapters by class and return them in a deterministic order.

    Identity is the adapter's ``(module, qualname)`` pair, so two instances of
    the same adapter class count as one entry. The result is a new list sorted
    by that pair; the first instance seen for a class is kept.

    Args:
        adapters: Adapter instances, possibly containing duplicates.

    Returns:
        A new list with one instance per adapter class, sorted deterministically.
    """
    unique: Dict[Tuple[str, str], SQLTypeAdapter] = {}
    for adapter in adapters:
        adapter_cls = type(adapter)
        unique.setdefault((adapter_cls.__module__, adapter_cls.__qualname__), adapter)
    return [unique[key] for key in sorted(unique)]


class TypeAdaptionMixin:
    def _register_default_adapters(self) -> None:
        """
        Registers default type adapters to the adapter registry.

        This method registers standard type adapters for common Python types
        to their corresponding database-compatible types. These adapters handle
        the conversion between Python native types and database driver types
        for common data types like datetime, JSON, UUID, etc.

        The adapters are registered in the backend's adapter registry, making
        them available for use in parameter preparation and result processing.
        """
        adapters = [
            DateTimeAdapter(),
            JSONAdapter(),
            UUIDAdapter(),
            EnumAdapter(),
            BooleanAdapter(),
            DecimalAdapter(),
        ]
        for adapter in adapters:
            for py_type, db_types in adapter.supported_types.items():
                for db_type in db_types:
                    self.adapter_registry.register(adapter, py_type, db_type)
        self.logger.debug("Registered all standard type adapters.")

    def prepare_parameters(
        self,
        params: Union[Dict[str, Any], Sequence[Any]],
        param_adapters: Union[Dict[str, Tuple[SQLTypeAdapter, Type]], Sequence[Optional[Tuple[SQLTypeAdapter, Type]]]],
    ) -> Union[Dict[str, Any], Tuple[Any, ...]]:
        """
        Prepares parameters for database execution by applying type adapters.

        This method converts Python parameter values to database-compatible types
        using the provided type adapters. It handles both dictionary and sequence
        parameter formats, applying the appropriate adapter to each parameter.

        Args:
            params: Parameters to convert. Can be a dictionary mapping parameter
                   names to values, or a sequence of parameter values.
            param_adapters: Type adapters to apply. Can be a dictionary mapping
                           parameter names to (adapter, target_type) tuples,
                           or a sequence of (adapter, target_type) tuples
                           corresponding to the parameters in the same order.

        Returns:
            Converted parameters in the same format as input (dict or tuple).
            Dictionary parameters return a dictionary, sequence parameters
            return a tuple with converted values.

        Raises:
            ValueError: If the length of params and param_adapters don't match
                       for sequence inputs.
            TypeError: If unsupported parameter types are provided.
        """
        if not params or not param_adapters:
            return tuple(params) if isinstance(params, Sequence) else params

        if isinstance(params, dict) and isinstance(param_adapters, dict):
            converted_params = params.copy()
            for key, adapter_info in param_adapters.items():
                if key in converted_params and adapter_info and converted_params[key] is not None:
                    adapter, db_type = adapter_info
                    original_value = converted_params[key]
                    converted_params[key] = adapter.to_database(original_value, db_type)
            return converted_params

        if isinstance(params, Sequence) and isinstance(param_adapters, Sequence):
            if len(params) != len(param_adapters):
                raise ValueError("Length of params and param_adapters must match")
            converted_params = list(params)
            for i, adapter_info in enumerate(param_adapters):
                if adapter_info and converted_params[i] is not None:
                    adapter, db_type = adapter_info
                    original_value = converted_params[i]
                    converted_params[i] = adapter.to_database(original_value, db_type)
            return tuple(converted_params)

        raise TypeError("Unsupported types for params and param_adapters.")

    def adapt_row_types(
        self, row_dict: Dict[str, Any], column_adapters: Dict[str, Tuple[SQLTypeAdapter, Type]]
    ) -> Dict[str, Any]:
        """
        Converts database column values back to Python types using column adapters.

        This method processes a single row dictionary, applying type adapters to
        convert database-native values back to their corresponding Python types.
        It handles both adapted and non-adapted columns appropriately.

        Args:
            row_dict: Dictionary mapping column names to database values for a single row
            column_adapters: Dictionary mapping column names to (adapter, target_type) tuples
                           specifying how to convert each column's value back to Python

        Returns:
            Dictionary with the same structure as input, but with values converted
            to their appropriate Python types where adapters were specified.
        """
        processed_row = {}
        for col_name, value in row_dict.items():
            adapter_info = column_adapters.get(col_name)
            if adapter_info:
                adapter, original_type = adapter_info
                if value is None:
                    result = adapter.from_database(value, original_type)
                    processed_row[col_name] = result
                else:
                    processed_row[col_name] = adapter.from_database(value, original_type)
            elif value is None:
                processed_row[col_name] = None
            else:
                processed_row[col_name] = value
        return processed_row

    def remap_row_columns(self, row_dict: Dict[str, Any], column_mapping: Dict[str, str]) -> Dict[str, Any]:
        """
        Maps database column names to Python field names in a result row.

        This method renames keys in the row dictionary according to the provided
        column mapping. It's used to convert database column names back to the
        corresponding Python field names as defined in the model.

        Args:
            row_dict: Dictionary mapping column names to values for a single row
            column_mapping: Dictionary mapping database column names to Python field names

        Returns:
            Dictionary with field names as keys instead of column names, preserving
            the same values. Keys not present in the mapping are preserved as-is.
        """
        final_row = {}
        for col_name, value in row_dict.items():
            field_name = column_mapping.get(col_name, col_name)
            final_row[field_name] = value
        return final_row

    def _process_result_set(self, cursor, is_select, column_adapters=None, column_mapping=None) -> Optional[List[Dict]]:
        """
        Processes the full result set from a database cursor into Python objects.

        This method orchestrates the two-step process of type adaptation and column
        name remapping for an entire result set. It fetches all rows from the cursor,
        applies type conversion using column adapters, and renames columns to field
        names using the column mapping.

        Args:
            cursor: The database cursor object after a query has been executed
            is_select: Flag indicating if it was a SELECT query
            column_adapters: Dictionary for type conversion, passed to `adapt_row_types`
            column_mapping: Dictionary for key remapping, passed to `remap_row_columns`

        Returns:
            List of fully processed row dictionaries, or None if not a SELECT query.
            Each dictionary represents a row with Python types and field names.
        """
        if not is_select:
            return None
        try:
            rows = cursor.fetchall()
            if not rows:
                return []
            column_names = [desc[0].strip('"') for desc in cursor.description]
            final_results = []
            adapters = column_adapters or {}
            mapping = column_mapping or {}
            for row in rows:
                row_dict = dict(zip(column_names, row))
                adapted_row = self.adapt_row_types(row_dict, adapters)
                final_row = self.remap_row_columns(adapted_row, mapping)
                final_results.append(final_row)
            return final_results
        except Exception as e:
            self.logger.error(f"Error processing result set: {str(e)}", exc_info=True)
            raise

    def get_default_adapter_suggestions(self) -> Dict[Type, Tuple[SQLTypeAdapter, Type]]:
        """Provide the framework-level default type adapter suggestions.

        This is the generic layer of the two-level scheme. It maps the common
        Python types to the driver representations described by
        :data:`CORE_DEFAULT_TYPE_MAPPINGS`, resolving them through this
        backend's adapter registry (an adapter that is not registered is simply
        not suggested).

        Backends extend it by overriding this method, merging their own
        entries onto the return value of ``super().get_default_adapter_suggestions()``
        (see :func:`merge_adapter_suggestions`): the core table is the base
        every backend builds on, and the backend completes it with what its
        driver actually accepts.

        Returns:
            Dictionary where keys are original Python types and values are
            tuples containing a SQLTypeAdapter instance and the target
            Python type expected by the driver.
        """
        suggestions: Dict[Type, Tuple[SQLTypeAdapter, Type]] = {}
        for py_type, db_type in CORE_DEFAULT_TYPE_MAPPINGS:
            adapter = self.adapter_registry.get_adapter(py_type, db_type)
            if adapter is not None:
                suggestions[py_type] = (adapter, db_type)
            else:
                self.logger.debug(
                    f"No core default adapter for ({py_type.__name__}, {db_type.__name__})."
                )
        return suggestions

    def get_type_adapters(self) -> List[SQLTypeAdapter]:
        """Return the adapter instances this backend provides.

        This is a plain inventory: it says which adapters exist for this backend.
        It carries no suggestion/default/priority semantics; the caller decides.

        The default implementation derives the inventory from
        :meth:`get_default_adapter_suggestions`, keeping only the adapter
        (first element of each tuple), deduplicated by adapter class and sorted
        by ``(module, qualname)``. Backends with a richer registry should
        override this method and enumerate that registry directly.

        Returns:
            A new list with one instance per adapter class, in deterministic order.
        """
        suggestions = self.get_default_adapter_suggestions()
        return sort_and_deduplicate_adapters(suggestion[0] for suggestion in suggestions.values())


class AsyncTypeAdaptionMixin(TypeAdaptionMixin):
    async def _process_result_set(
        self, cursor, is_select, column_adapters=None, column_mapping=None
    ) -> Optional[List[Dict]]:
        """
        Processes the full result set from an async database cursor into Python objects.

        This method orchestrates the two-step process of type adaptation and column
        name remapping for an entire result set from an async cursor. It awaits
        the fetchall operation and then applies the same processing as the sync version.

        Args:
            cursor: The async database cursor object after a query has been executed
            is_select: Flag indicating if it was a SELECT query
            column_adapters: Dictionary for type conversion, passed to `adapt_row_types`
            column_mapping: Dictionary for key remapping, passed to `remap_row_columns`

        Returns:
            List of fully processed row dictionaries, or None if not a SELECT query.
            Each dictionary represents a row with Python types and field names.
        """
        if not is_select:
            return None
        try:
            rows = await cursor.fetchall()
            if not rows:
                return []
            column_names = [desc[0].strip('"') for desc in cursor.description]
            final_results = []
            adapters = column_adapters or {}
            mapping = column_mapping or {}
            for row in rows:
                row_dict = dict(zip(column_names, row))
                adapted_row = self.adapt_row_types(row_dict, adapters)
                final_row = self.remap_row_columns(adapted_row, mapping)
                final_results.append(final_row)
            return final_results
        except Exception as e:
            self.logger.error(f"Error processing async result set: {str(e)}", exc_info=True)
            raise
