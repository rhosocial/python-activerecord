# src/rhosocial/activerecord/backend/base/type_adaption.py
from abc import abstractmethod
from typing import Any, Dict, List, Optional, Sequence, Tuple, Type, Union
from ..type_adapter import (
    SQLTypeAdapter, DateTimeAdapter, JSONAdapter, UUIDAdapter,
    EnumAdapter, BooleanAdapter, DecimalAdapter
)

class TypeAdaptionMixin:
    def _register_default_adapters(self) -> None:
        adapters = [
            DateTimeAdapter(), JSONAdapter(), UUIDAdapter(), EnumAdapter(),
            BooleanAdapter(), DecimalAdapter(),
        ]
        for adapter in adapters:
            for py_type, db_types in adapter.supported_types.items():
                for db_type in db_types:
                    self.adapter_registry.register(adapter, py_type, db_type)
        self.logger.debug("Registered all standard type adapters.")
    def prepare_parameters(self, params: Union[Dict[str, Any], Sequence[Any]], param_adapters: Union[Dict[str, Tuple[SQLTypeAdapter, Type]], Sequence[Optional[Tuple[SQLTypeAdapter, Type]]]]) -> Union[Dict[str, Any], Tuple[Any, ...]]:
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
    def _adapt_row_types(self, row_dict: Dict[str, Any], column_adapters: Dict[str, Tuple[SQLTypeAdapter, Type]]) -> Dict[str, Any]:
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
    def _remap_row_columns(self, row_dict: Dict[str, Any], column_mapping: Dict[str, str]) -> Dict[str, Any]:
        final_row = {}
        for col_name, value in row_dict.items():
            field_name = column_mapping.get(col_name, col_name)
            final_row[field_name] = value
        return final_row
    def _process_result_set(self, cursor, is_select, column_adapters=None, column_mapping=None) -> Optional[List[Dict]]:
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
        pass

class AsyncTypeAdaptionMixin(TypeAdaptionMixin):
    async def _process_result_set(self, cursor, is_select, column_adapters=None, column_mapping=None) -> Optional[List[Dict]]:
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