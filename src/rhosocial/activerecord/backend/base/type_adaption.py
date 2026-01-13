# src/rhosocial/activerecord/backend/base/type_adaption.py
from abc import abstractmethod
from typing import Any, Dict, List, Optional, Sequence, Tuple, Type, Union
from ..type_adapter import (
    SQLTypeAdapter, DateTimeAdapter, JSONAdapter, UUIDAdapter,
    EnumAdapter, BooleanAdapter, DecimalAdapter
)

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
            DateTimeAdapter(), JSONAdapter(), UUIDAdapter(), EnumAdapter(),
            BooleanAdapter(), DecimalAdapter(),
        ]
        for adapter in adapters:
            for py_type, db_types in adapter.supported_types.items():
                for db_type in db_types:
                    self.adapter_registry.register(adapter, py_type, db_type)
        self.logger.debug("Registered all standard type adapters.")

    def prepare_parameters(self, params: Union[Dict[str, Any], Sequence[Any]],
                          param_adapters: Union[Dict[str, Tuple[SQLTypeAdapter, Type]],
                                              Sequence[Optional[Tuple[SQLTypeAdapter, Type]]]]) -> Union[Dict[str, Any], Tuple[Any, ...]]:
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
    def _adapt_row_types(self, row_dict: Dict[str, Any],
                        column_adapters: Dict[str, Tuple[SQLTypeAdapter, Type]]) -> Dict[str, Any]:
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
            if value is None:
                processed_row[col_name] = None
                continue
            adapter_info = column_adapters.get(col_name)
            if adapter_info:
                adapter, py_type = adapter_info
                processed_row[col_name] = adapter.from_database(value, py_type)
            else:
                processed_row[col_name] = value
        return processed_row

    def _remap_row_columns(self, row_dict: Dict[str, Any],
                          column_mapping: Dict[str, str]) -> Dict[str, Any]:
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
            column_adapters: Dictionary for type conversion, passed to `_adapt_row_types`
            column_mapping: Dictionary for key remapping, passed to `_remap_row_columns`

        Returns:
            List of fully processed row dictionaries, or None if not a SELECT query.
            Each dictionary represents a row with Python types and field names.
        """
        if not is_select:
            return None
        try:
            rows = cursor.fetchall()
            if not rows: return []
            column_names = [desc[0].strip('"') for desc in cursor.description]
            final_results = []
            adapters = column_adapters or {}
            mapping = column_mapping or {}
            for row in rows:
                row_dict = dict(zip(column_names, row))
                adapted_row = self._adapt_row_types(row_dict, adapters)
                final_row = self._remap_row_columns(adapted_row, mapping)
                final_results.append(final_row)
            return final_results
        except Exception as e:
            self.logger.error(f"Error processing result set: {str(e)}", exc_info=True)
            raise

    @abstractmethod
    def get_default_adapter_suggestions(self) -> Dict[Type, Tuple[SQLTypeAdapter, Type]]:
        """
        Provides default type adapter suggestions for common Python types.

        This method defines a curated set of type adapter suggestions for common Python
        types, mapping them to their typical database-compatible representations.
        It retrieves necessary SQLTypeAdapter instances from the backend's
        adapter_registry. If an adapter for a specific (Python type, DB driver type)
        pair is not registered, no suggestion will be made for that Python type.

        Returns:
            Dictionary where keys are original Python types and values are
            tuples containing a SQLTypeAdapter instance and the target
            Python type expected by the driver.
        """
        pass


class AsyncTypeAdaptionMixin(TypeAdaptionMixin):
    async def _process_result_set(self, cursor, is_select, column_adapters=None, column_mapping=None) -> Optional[List[Dict]]:
        """
        Processes the full result set from an async database cursor into Python objects.

        This method orchestrates the two-step process of type adaptation and column
        name remapping for an entire result set from an async cursor. It awaits
        the fetchall operation and then applies the same processing as the sync version.

        Args:
            cursor: The async database cursor object after a query has been executed
            is_select: Flag indicating if it was a SELECT query
            column_adapters: Dictionary for type conversion, passed to `_adapt_row_types`
            column_mapping: Dictionary for key remapping, passed to `_remap_row_columns`

        Returns:
            List of fully processed row dictionaries, or None if not a SELECT query.
            Each dictionary represents a row with Python types and field names.
        """
        if not is_select:
            return None
        try:
            rows = await cursor.fetchall()
            if not rows: return []
            column_names = [desc[0].strip('"') for desc in cursor.description]
            final_results = []
            adapters = column_adapters or {}
            mapping = column_mapping or {}
            for row in rows:
                row_dict = dict(zip(column_names, row))
                adapted_row = self._adapt_row_types(row_dict, adapters)
                final_row = self._remap_row_columns(adapted_row, mapping)
                final_results.append(final_row)
            return final_results
        except Exception as e:
            self.logger.error(f"Error processing async result set: {str(e)}", exc_info=True)
            raise