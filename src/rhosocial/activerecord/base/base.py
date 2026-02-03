# src/rhosocial/activerecord/base/base.py
"""Core BaseActiveRecord implementation."""

import inspect
import logging
from copy import deepcopy
from pydantic.fields import FieldInfo
from typing import Any, Dict, List, Optional, ClassVar, Type, Union, get_origin, get_args, Tuple, Set

from ..backend.base import StorageBackend, AsyncStorageBackend
from ..backend.config import ConnectionConfig
from ..backend.errors import DatabaseError, RecordNotFound, ValidationError as DBValidationError
from ..backend.expression import ComparisonPredicate, Column, Literal, SQLPredicate
from ..backend.expression.bases import is_sql_query_and_params
from ..backend.impl.dummy.backend import DummyBackend, AsyncDummyBackend
from ..backend.options import DeleteOptions, UpdateOptions
from ..backend.options import InsertOptions
from ..backend.type_adapter import SQLTypeAdapter
from ..interface import IActiveRecord, IAsyncActiveRecord, ActiveRecordBase, ModelEvent
from ..interface.update import IUpdateBehavior


class CustomModuleFormatter(logging.Formatter):
    def format(self, record):
        import os
        module_dir = os.path.basename(os.path.dirname(record.pathname))
        record.subpackage_module = f"{module_dir}-{record.filename}"
        return super().format(record)

class BaseActiveRecord(IActiveRecord):
    """
    Core ActiveRecord implementation providing the fundamental ORM functionality.
    """

    @classmethod
    def configure(cls, config: ConnectionConfig, backend_class: Type[StorageBackend]) -> None:
        if not isinstance(config, ConnectionConfig):
            raise DatabaseError(f"Invalid connection config for {cls.__name__}")

        cls.__connection_config__ = config
        cls.__backend_class__ = backend_class

        backend_instance = backend_class(connection_config=config)
        if hasattr(cls, '__logger__'):
            backend_instance.logger = cls.__logger__

        cls.__backend__ = backend_instance
        if hasattr(cls, '_dummy_backend') and cls._dummy_backend is not None:
            cls._dummy_backend = None

    @classmethod
    def backend(cls) -> StorageBackend:
        return super().backend()

    @classmethod
    def create_from_database(cls, row: Dict[str, Any]) -> 'BaseActiveRecord':
        instance = cls(**row)
        instance._is_from_db = True
        instance.reset_tracking()
        return instance

    @classmethod
    def create_collection_from_database(cls, rows: List[Dict[str, Any]]) -> List['BaseActiveRecord']:
        return [cls.create_from_database(row) for row in rows]

    def _insert_internal(self, data) -> Any:
        self.log(logging.DEBUG, f"Raw data for insert: {data}")
        prepared_data = self.__class__._map_fields_to_columns(data)
        self.log(logging.DEBUG, f"Data with database column names: {prepared_data}")
        self.log(logging.INFO, f"Inserting new {self.__class__.__name__}")
        column_mapping = self.__class__.get_column_to_field_map()
        self.log(logging.DEBUG, f"Column mapping for result processing: {column_mapping}")
        column_adapters = self.get_column_adapters()
        self.log(logging.DEBUG, f"Column adapters map: {column_adapters}")
        supports_returning = self.backend().dialect.supports_returning_clause()
        returning_columns = None
        if supports_returning:
            returning_columns = [self.primary_key()]

        insert_options = InsertOptions(
            table=self.table_name(),
            data=prepared_data,
            column_mapping=column_mapping,
            column_adapters=column_adapters,
            primary_key=self.primary_key(),
            returning_columns=returning_columns
        )
        result = self.backend().insert(insert_options)
        pk_column = self.primary_key()
        pk_field_name = self.__class__._get_field_name(pk_column)
        if (result is not None and result.affected_rows > 0 and
                pk_field_name in self.__class__.model_fields and
                prepared_data.get(pk_column) is None and
                getattr(self, pk_field_name, None) is None):

            pk_retrieved = False
            self.log(logging.DEBUG, f"Attempting to retrieve primary key '{pk_column}' for new record")
            pk_field_name = self.__class__._get_field_name(pk_column)
            self.log(logging.DEBUG, f"Primary key column '{pk_column}' maps to field '{pk_field_name}'")
            if result.data and isinstance(result.data, list) and len(result.data) > 0:
                first_row = result.data[0]
                if isinstance(first_row, dict) and pk_field_name in first_row:
                    pk_value = first_row[pk_field_name]
                    setattr(self, pk_field_name, pk_value)
                    pk_retrieved = True
                    self.log(logging.DEBUG, f"Retrieved primary key '{pk_field_name}' from RETURNING clause: {pk_value}")
                else:
                    self.log(logging.WARNING, f"RETURNING clause data found, but primary key field '{pk_field_name}' is missing in the result row: {first_row}")

            if not pk_retrieved and result.last_insert_id is not None:
                field_type = self.__class__.model_fields[pk_field_name].annotation
                if get_origin(field_type) in (Union, Optional):
                    types = [t for t in get_args(field_type) if t is not type(None)]
                    if types:
                        field_type = types[0]

                if field_type is int:
                    pk_value = result.last_insert_id
                    setattr(self, pk_field_name, pk_value)
                    pk_retrieved = True
                    self.log(logging.DEBUG, f"Retrieved primary key '{pk_field_name}' from last_insert_id: {pk_value}")
            if not pk_retrieved:
                error_msg = f"Failed to retrieve primary key '{pk_field_name}' for new record after insert."
                self.log(logging.ERROR, f"{error_msg}")
                raise DatabaseError(error_msg)

        self._is_from_db = True
        self.reset_tracking()
        return result

    def _update_internal(self, data) -> Any:
        self.log(logging.INFO, f"Starting update operation for {self.__class__.__name__} record with ID: {getattr(self, self.__class__.primary_key_field(), 'unknown')}")
        update_conditions = []
        update_expressions = {}
        mro = self.__class__.__mro__
        activerecord_idx = mro.index(IActiveRecord)
        self.log(logging.DEBUG, f"Traversing MRO for IUpdateBehavior implementations: {[cls.__name__ for cls in mro[:activerecord_idx]]}")
        for cls in mro[:activerecord_idx]:
            if issubclass(cls, IUpdateBehavior):
                defines_conditions_method = 'get_update_conditions' in cls.__dict__
                defines_expressions_method = 'get_update_expressions' in cls.__dict__
                if defines_conditions_method or defines_expressions_method:
                    self.log(logging.DEBUG, f"Processing IUpdateBehavior from {cls.__name__}")
                    if defines_conditions_method:
                        behavior_conditions = cls.get_update_conditions(self)
                        if behavior_conditions:
                            self.log(logging.DEBUG, f"  Adding {len(behavior_conditions)} condition(s) from {cls.__name__}")
                            update_conditions.extend(behavior_conditions)
                        else:
                            self.log(logging.DEBUG, f"  No conditions from {cls.__name__}")
                    if defines_expressions_method:
                        behavior_expressions = cls.get_update_expressions(self)
                        if behavior_expressions:
                            self.log(logging.DEBUG, f"  Adding {len(behavior_expressions)} expression(s) from {cls.__name__}: {list(behavior_expressions.keys())}")
                            update_expressions.update(behavior_expressions)
                        else:
                            self.log(logging.DEBUG, f"  No expressions from {cls.__name__}")
                else:
                    self.log(logging.DEBUG, f"Skipping {cls.__name__} (implements IUpdateBehavior but doesn't define methods directly)")
        self.log(logging.INFO, f"Update operation: {len(update_conditions)} condition(s), {len(update_expressions)} expression(s) collected from mixins")
        self.log(logging.DEBUG, f"Final update conditions: {len(update_conditions)} total")
        self.log(logging.DEBUG, f"Final update expressions: {list(update_expressions.keys())}")
        complete_data = {**data, **update_expressions}
        self.log(logging.DEBUG, f"Complete data for SET clause: {list(complete_data.keys())}")
        mapped_data = self.__class__._map_fields_to_columns(complete_data)
        self.log(logging.DEBUG, f"Mapped data for SET clause: {list(mapped_data.keys())}")
        column_mapping = self.__class__.get_column_to_field_map()
        column_adapters = self.get_column_adapters()
        backend = self.backend()
        pk_name = self.primary_key()
        pk_value = getattr(self, self.__class__.primary_key_field())
        self.log(logging.DEBUG, f"Primary key: {pk_name} = {pk_value}")
        where_predicate = ComparisonPredicate(
            backend.dialect, '=', Column(backend.dialect, pk_name), Literal(backend.dialect, pk_value)
        )
        for condition in update_conditions:
            if hasattr(condition, 'to_sql'):
                where_predicate = where_predicate & condition
            else:
                pass
        self.log(logging.DEBUG, f"Final WHERE clause conditions: {len(update_conditions)} additional condition(s) applied")
        supports_returning = backend.dialect.supports_returning_clause()
        returning_columns = None
        if supports_returning:
            returning_columns = [self.primary_key()]
        update_options = UpdateOptions(
            table=self.table_name(),
            data=mapped_data,
            where=where_predicate,
            column_mapping=column_mapping,
            column_adapters=column_adapters,
            returning_columns=returning_columns
        )
        self.log(logging.INFO, f"Executing update operation on table '{self.table_name()}' with {len(data)} field(s) to update")
        result = backend.update(update_options)
        self.log(logging.INFO, f"Update operation completed. Affected rows: {result.affected_rows}")
        return result

    def _prepare_save_data(self) -> Dict[str, Any]:
        is_new = self.is_new_record
        if is_new:
            data = self.model_dump(exclude={self.primary_key()} if hasattr(self, self.primary_key()) else set())
        else:
            all_data = self.model_dump()
            data = {field: all_data[field] for field in self._dirty_fields if field != self.primary_key()}
        bases = self.__class__.__mro__
        for base in bases:
            if hasattr(base, 'prepare_save_data') and base != BaseActiveRecord:
                prepare_method = getattr(base, 'prepare_save_data')
                data = prepare_method(self, data, is_new)
        return data

    def _after_save(self, is_new: bool) -> None:
        bases = self.__class__.__mro__
        for base in bases:
            if hasattr(base, 'after_save') and base != BaseActiveRecord:
                after_method = getattr(base, 'after_save')
                after_method(self, is_new)

    @classmethod
    def find_one(
        cls: Type['BaseActiveRecord'],
        condition: Union[Any, Dict[str, Any], Dict['Column', Any], 'SQLPredicate', Tuple[str, tuple]]
    ) -> Optional['BaseActiveRecord']:
        query = cls.query()
        if isinstance(condition, dict):
            for key, value in condition.items():
                if isinstance(key, Column):
                    query = query.where(key == value)
                elif isinstance(key, str):
                    query = query.where(getattr(cls.c, key) == value)
                else:
                    raise TypeError(f"Invalid key type in condition dictionary: {type(key)}. "
                                    f"Expected str or Column, got {type(key)}")
        elif isinstance(condition, SQLPredicate):
            query = query.where(condition)
        elif is_sql_query_and_params(condition):
            sql, params = condition
            query = query.where(sql, params)
        else:
            pk_field_name = cls.primary_key()
            query = query.where(f"{pk_field_name} = ?", (condition,))
        return query.one()

    @classmethod
    def find_all(
        cls: Type['BaseActiveRecord'],
        condition: Optional[Union[Any, List[Any], Dict[str, Any], Dict['Column', Any], 'SQLPredicate', Tuple[str, tuple]]] = None
    ) -> List['BaseActiveRecord']:
        query = cls.query()
        if condition is None:
            return query.all()
        if isinstance(condition, dict):
            for key, value in condition.items():
                if isinstance(key, Column):
                    query = query.where(key == value)
                elif isinstance(key, str):
                    query = query.where(getattr(cls.c, key) == value)
                else:
                    raise TypeError(f"Invalid key type in condition dictionary: {type(key)}. "
                                    f"Expected str or Column, got {type(key)}")
        elif isinstance(condition, SQLPredicate):
            query = query.where(condition)
        elif is_sql_query_and_params(condition):
            sql, params = condition
            query = query.where(sql, params)
        else: # Assumes list of primary keys
            pk_field_name = cls.primary_key()
            if not condition:
                return []
            placeholders = ','.join(['?' for _ in condition])
            query = query.where(f"{pk_field_name} IN ({placeholders})", condition)
        return query.all()

    @classmethod
    def find_one_or_fail(
        cls: Type['BaseActiveRecord'],
        condition: Union[Any, Dict[str, Any], Dict['Column', Any], 'SQLPredicate', Tuple[str, tuple]]
    ) -> 'BaseActiveRecord':
        record = cls.find_one(condition)
        if record is None:
            cls.log(logging.WARNING, f"Record not found for {cls.__name__} with find_one condition: {condition}")
            raise RecordNotFound(f"Record not found for {cls.__name__}")
        return record

    def save(self) -> int:
        if not self.backend():
            raise DatabaseError("No backend configured")
        try:
            self.validate_fields()
        except Exception as e:
            self.log(logging.ERROR, f"Validation error: {str(e)}")
            raise DBValidationError(str(e))
        if not self.is_new_record and not self.is_dirty:
            return 0
        try:
            self._trigger_event(ModelEvent.BEFORE_SAVE, is_new=self.is_new_record)
        except Exception as e:
            self.log(logging.ERROR, f"Trigger event error: {str(e)}")
            raise
        try:
            return self._save_internal()
        except Exception as e:
            self.log(logging.ERROR, f"Database error: {str(e)}")
            raise DatabaseError(str(e)) from e

    def delete(self) -> int:
        if not self.backend():
            raise DatabaseError("No backend configured")
        if self.is_new_record:
            return 0
        self._trigger_event(ModelEvent.BEFORE_DELETE)
        backend = self.backend()
        pk_name = self.primary_key()
        pk_value = getattr(self, pk_name)
        where_predicate = ComparisonPredicate(backend.dialect, '=', Column(backend.dialect, pk_name), Literal(backend.dialect, pk_value))
        is_soft_delete = hasattr(self, 'prepare_delete')
        if is_soft_delete:
            self.log(logging.INFO, f"Soft deleting {self.__class__.__name__}#{pk_value}")
            data = self.prepare_delete()
            update_opts = UpdateOptions(table=self.table_name(), data=data, where=where_predicate)
            result = backend.update(update_opts)
        else:
            self.log(logging.INFO, f"Deleting {self.__class__.__name__}#{pk_value}")
            supports_returning = backend.dialect.supports_returning_clause()
            returning_columns = None
            if supports_returning:
                returning_columns = [self.primary_key()]
            delete_opts = DeleteOptions(table=self.table_name(), where=where_predicate, returning_columns=returning_columns)
            result = backend.delete(delete_opts)
        affected_rows = result.affected_rows
        if affected_rows > 0:
            if not is_soft_delete:
                if hasattr(self, pk_name):
                    setattr(self, pk_name, None)
            self.reset_tracking()
            self._trigger_event(ModelEvent.AFTER_DELETE)
        return affected_rows

    def validate_custom(self) -> None:
        pass

    @classmethod
    def transaction(cls):
        if cls.backend() is None:
            raise DatabaseError("No backend configured")
        return cls.backend().transaction()

    # region Logging Methods

    @classmethod
    def setup_logger(cls, formatter: Optional[logging.Formatter] = None) -> None:
        if not hasattr(cls, '__logger__'):
            return
        logger = getattr(cls, '__logger__')
        if logger is None or not isinstance(logger, logging.Logger):
            return
        if formatter is None:
            formatter = CustomModuleFormatter('%(asctime)s - %(levelname)s - [%(subpackage_module)s:%(lineno)d] - %(message)s')
        if logger.handlers:
            for handler in logger.handlers:
                handler.setFormatter(formatter)
        root_logger = logging.getLogger()
        for handler in root_logger.handlers:
            if not isinstance(handler.formatter, CustomModuleFormatter):
                handler.setFormatter(formatter)

    @classmethod
    def set_logger(cls, logger: logging.Logger) -> None:
        if logger is not None and not isinstance(logger, logging.Logger):
            raise ValueError("logger must be an instance of logging.Logger")
        cls.__logger__ = logger

    @classmethod
    def log(cls, level: int, msg: str, *args, **kwargs) -> None:
        if not hasattr(cls, '__logger__'):
            return
        logger = getattr(cls, '__logger__')
        if logger is None:
            return
        if not isinstance(logger, logging.Logger):
            return
        current_frame = inspect.currentframe().f_back
        stack_level = 1
        while current_frame:
            if current_frame.f_globals['__name__'] != 'ActiveRecord':
                break
            current_frame = current_frame.f_back
            stack_level += 1
        if current_frame:
            stack_level += 1
        if "offset" in kwargs:
            stack_level += kwargs.pop("offset")
        if (logger.handlers and not any(isinstance(h.formatter, CustomModuleFormatter) for h in logger.handlers)) or \
                (not logger.handlers and not any(isinstance(h.formatter, CustomModuleFormatter) for h in logging.getLogger().handlers)):
            cls.setup_logger()
        level_name = logging.getLevelName(level).lower()
        method = getattr(logger, level_name, None)
        if method is not None:
            method(msg, *args, stacklevel=stack_level, **kwargs)
        else:
            logger.log(level, msg, *args, **kwargs)

    @classmethod
    def get_column_adapters(cls) -> Dict[str, Tuple['SQLTypeAdapter', Type]]:
        adapters_map: Dict[str, Tuple['SQLTypeAdapter', Type]] = {}
        model_fields: Dict[str, FieldInfo] = dict(cls.model_fields)
        all_suggestions = cls.backend().get_default_adapter_suggestions()
        for field_name, field_info in model_fields.items():
            column_name = cls._get_column_name(field_name)
            field_py_type = field_info.annotation
            original_type = field_py_type
            origin = get_origin(field_py_type)
            if origin is Union:
                args = [arg for arg in get_args(field_py_type) if arg is not type(None)]
                if len(args) == 1:
                    field_py_type = args[0]
                else:
                    continue
            custom_adapter_tuple = cls._get_adapter_for_field(field_name)
            if custom_adapter_tuple:
                adapter_instance, _ = custom_adapter_tuple
                adapters_map[column_name] = (adapter_instance, original_type)
                continue
            suggestion = all_suggestions.get(field_py_type)
            if suggestion:
                adapter_instance, _ = suggestion
                adapters_map[column_name] = (adapter_instance, original_type)
        return adapters_map


class AsyncBaseActiveRecord(IAsyncActiveRecord):
    """
    Core Async ActiveRecord implementation providing the fundamental ORM functionality.
    """

    @classmethod
    def configure(cls, config: ConnectionConfig, backend_class: Type[AsyncStorageBackend]) -> None:
        if not isinstance(config, ConnectionConfig):
            raise DatabaseError(f"Invalid connection config for {cls.__name__}")

        cls.__connection_config__ = config
        cls.__backend_class__ = backend_class

        backend_instance = backend_class(connection_config=config)
        if hasattr(cls, '__logger__'):
            backend_instance.logger = cls.__logger__

        cls.__backend__ = backend_instance
        if hasattr(cls, '_dummy_backend') and cls._dummy_backend is not None:
            cls._dummy_backend = None

    @classmethod
    def backend(cls) -> AsyncStorageBackend:
        return super().backend()

    @classmethod
    def create_from_database(cls, row: Dict[str, Any]) -> 'AsyncBaseActiveRecord':
        instance = cls(**row)
        instance._is_from_db = True
        instance.reset_tracking()
        return instance

    @classmethod
    def create_collection_from_database(cls, rows: List[Dict[str, Any]]) -> List['AsyncBaseActiveRecord']:
        return [cls.create_from_database(row) for row in rows]

    async def _insert_internal(self, data) -> Any:
        self.log(logging.DEBUG, f"Raw data for insert: {data}")
        prepared_data = self.__class__._map_fields_to_columns(data)
        self.log(logging.DEBUG, f"Data with database column names: {prepared_data}")
        self.log(logging.INFO, f"Inserting new {self.__class__.__name__}")
        column_mapping = self.__class__.get_column_to_field_map()
        self.log(logging.DEBUG, f"Column mapping for result processing: {column_mapping}")
        column_adapters = self.get_column_adapters()
        self.log(logging.DEBUG, f"Column adapters map: {column_adapters}")
        supports_returning = self.backend().dialect.supports_returning_clause()
        returning_columns = None
        if supports_returning:
            returning_columns = [self.primary_key()]

        insert_options = InsertOptions(
            table=self.table_name(),
            data=prepared_data,
            column_mapping=column_mapping,
            column_adapters=column_adapters,
            primary_key=self.primary_key(),
            returning_columns=returning_columns
        )
        result = await self.backend().insert(insert_options)
        pk_column = self.primary_key()
        pk_field_name = self.__class__._get_field_name(pk_column)
        if (result is not None and result.affected_rows > 0 and
                pk_field_name in self.__class__.model_fields and
                prepared_data.get(pk_column) is None and
                getattr(self, pk_field_name, None) is None):

            pk_retrieved = False
            self.log(logging.DEBUG, f"Attempting to retrieve primary key '{pk_column}' for new record")
            pk_field_name = self.__class__._get_field_name(pk_column)
            self.log(logging.DEBUG, f"Primary key column '{pk_column}' maps to field '{pk_field_name}'")
            if result.data and isinstance(result.data, list) and len(result.data) > 0:
                first_row = result.data[0]
                if isinstance(first_row, dict) and pk_field_name in first_row:
                    pk_value = first_row[pk_field_name]
                    setattr(self, pk_field_name, pk_value)
                    pk_retrieved = True
                    self.log(logging.DEBUG, f"Retrieved primary key '{pk_field_name}' from RETURNING clause: {pk_value}")
                else:
                    self.log(logging.WARNING, f"RETURNING clause data found, but primary key field '{pk_field_name}' is missing in the result row: {first_row}")

            if not pk_retrieved and result.last_insert_id is not None:
                field_type = self.__class__.model_fields[pk_field_name].annotation
                if get_origin(field_type) in (Union, Optional):
                    types = [t for t in get_args(field_type) if t is not type(None)]
                    if types:
                        field_type = types[0]

                if field_type is int:
                    pk_value = result.last_insert_id
                    setattr(self, pk_field_name, pk_value)
                    pk_retrieved = True
                    self.log(logging.DEBUG, f"Retrieved primary key '{pk_field_name}' from last_insert_id: {pk_value}")
            if not pk_retrieved:
                error_msg = f"Failed to retrieve primary key '{pk_field_name}' for new record after insert."
                self.log(logging.ERROR, f"{error_msg}")
                raise DatabaseError(error_msg)

        self._is_from_db = True
        self.reset_tracking()
        return result

    async def _update_internal(self, data) -> Any:
        self.log(logging.INFO, f"Starting update operation for {self.__class__.__name__} record with ID: {getattr(self, self.__class__.primary_key_field(), 'unknown')}")
        update_conditions = []
        update_expressions = {}
        mro = self.__class__.__mro__
        activerecord_idx = mro.index(IAsyncActiveRecord)
        self.log(logging.DEBUG, f"Traversing MRO for IUpdateBehavior implementations: {[cls.__name__ for cls in mro[:activerecord_idx]]}")
        for cls in mro[:activerecord_idx]:
            if issubclass(cls, IUpdateBehavior):
                defines_conditions_method = 'get_update_conditions' in cls.__dict__
                defines_expressions_method = 'get_update_expressions' in cls.__dict__
                if defines_conditions_method or defines_expressions_method:
                    self.log(logging.DEBUG, f"Processing IUpdateBehavior from {cls.__name__}")
                    if defines_conditions_method:
                        behavior_conditions = cls.get_update_conditions(self)
                        if behavior_conditions:
                            self.log(logging.DEBUG, f"  Adding {len(behavior_conditions)} condition(s) from {cls.__name__}")
                            update_conditions.extend(behavior_conditions)
                        else:
                            self.log(logging.DEBUG, f"  No conditions from {cls.__name__}")
                    if defines_expressions_method:
                        behavior_expressions = cls.get_update_expressions(self)
                        if behavior_expressions:
                            self.log(logging.DEBUG, f"  Adding {len(behavior_expressions)} expression(s) from {cls.__name__}: {list(behavior_expressions.keys())}")
                            update_expressions.update(behavior_expressions)
                        else:
                            self.log(logging.DEBUG, f"  No expressions from {cls.__name__}")
                else:
                    self.log(logging.DEBUG, f"Skipping {cls.__name__} (implements IUpdateBehavior but doesn't define methods directly)")
        self.log(logging.INFO, f"Update operation: {len(update_conditions)} condition(s), {len(update_expressions)} expression(s) collected from mixins")
        self.log(logging.DEBUG, f"Final update conditions: {len(update_conditions)} total")
        self.log(logging.DEBUG, f"Final update expressions: {list(update_expressions.keys())}")
        complete_data = {**data, **update_expressions}
        self.log(logging.DEBUG, f"Complete data for SET clause: {list(complete_data.keys())}")
        mapped_data = self.__class__._map_fields_to_columns(complete_data)
        self.log(logging.DEBUG, f"Mapped data for SET clause: {list(mapped_data.keys())}")
        column_mapping = self.__class__.get_column_to_field_map()
        column_adapters = self.get_column_adapters()
        backend = self.backend()
        pk_name = self.primary_key()
        pk_value = getattr(self, self.__class__.primary_key_field())
        self.log(logging.DEBUG, f"Primary key: {pk_name} = {pk_value}")
        where_predicate = ComparisonPredicate(
            backend.dialect, '=', Column(backend.dialect, pk_name), Literal(backend.dialect, pk_value)
        )
        for condition in update_conditions:
            if hasattr(condition, 'to_sql'):
                where_predicate = where_predicate & condition
            else:
                pass
        self.log(logging.DEBUG, f"Final WHERE clause conditions: {len(update_conditions)} additional condition(s) applied")
        supports_returning = backend.dialect.supports_returning_clause()
        returning_columns = None
        if supports_returning:
            returning_columns = [self.primary_key()]
        update_options = UpdateOptions(
            table=self.table_name(),
            data=mapped_data,
            where=where_predicate,
            column_mapping=column_mapping,
            column_adapters=column_adapters,
            returning_columns=returning_columns
        )
        self.log(logging.INFO, f"Executing update operation on table '{self.table_name()}' with {len(data)} field(s) to update")
        result = await backend.update(update_options)
        self.log(logging.INFO, f"Update operation completed. Affected rows: {result.affected_rows}")
        return result

    def _prepare_save_data(self) -> Dict[str, Any]:
        is_new = self.is_new_record
        if is_new:
            data = self.model_dump(exclude={self.primary_key()} if hasattr(self, self.primary_key()) else set())
        else:
            all_data = self.model_dump()
            data = {field: all_data[field] for field in self._dirty_fields if field != self.primary_key()}
        bases = self.__class__.__mro__
        for base in bases:
            if hasattr(base, 'prepare_save_data') and base != AsyncBaseActiveRecord:
                prepare_method = getattr(base, 'prepare_save_data')
                data = prepare_method(self, data, is_new)
        return data

    def _after_save(self, is_new: bool) -> None:
        bases = self.__class__.__mro__
        for base in bases:
            if hasattr(base, 'after_save') and base != AsyncBaseActiveRecord:
                after_method = getattr(base, 'after_save')
                after_method(self, is_new)

    @classmethod
    async def find_one(
        cls: Type['AsyncBaseActiveRecord'],
        condition: Union[Any, Dict[str, Any], Dict['Column', Any], 'SQLPredicate', Tuple[str, tuple]]
    ) -> Optional['AsyncBaseActiveRecord']:
        query = cls.query()
        if isinstance(condition, dict):
            for key, value in condition.items():
                if isinstance(key, Column):
                    query = query.where(key == value)
                elif isinstance(key, str):
                    query = query.where(getattr(cls.c, key) == value)
                else:
                    raise TypeError(f"Invalid key type in condition dictionary: {type(key)}. "
                                    f"Expected str or Column, got {type(key)}")
        elif isinstance(condition, SQLPredicate):
            query = query.where(condition)
        elif is_sql_query_and_params(condition):
            sql, params = condition
            query = query.where(sql, params)
        else:
            pk_field_name = cls.primary_key()
            query = query.where(f"{pk_field_name} = ?", (condition,))
        return await query.one()

    @classmethod
    async def find_all(
        cls: Type['AsyncBaseActiveRecord'],
        condition: Optional[Union[Any, List[Any], Dict[str, Any], Dict['Column', Any], 'SQLPredicate', Tuple[str, tuple]]] = None
    ) -> List['AsyncBaseActiveRecord']:
        query = cls.query()
        if condition is None:
            return await query.all()
        if isinstance(condition, dict):
            for key, value in condition.items():
                if isinstance(key, Column):
                    query = query.where(key == value)
                elif isinstance(key, str):
                    query = query.where(getattr(cls.c, key) == value)
                else:
                    raise TypeError(f"Invalid key type in condition dictionary: {type(key)}. "
                                    f"Expected str or Column, got {type(key)}")
        elif isinstance(condition, SQLPredicate):
            query = query.where(condition)
        elif is_sql_query_and_params(condition):
            sql, params = condition
            query = query.where(sql, params)
        else: # Assumes list of primary keys
            pk_field_name = cls.primary_key()
            if not condition:
                return []
            placeholders = ','.join(['?' for _ in condition])
            query = query.where(f"{pk_field_name} IN ({placeholders})", condition)
        return await query.all()

    @classmethod
    async def find_one_or_fail(
        cls: Type['AsyncBaseActiveRecord'],
        condition: Union[Any, Dict[str, Any], Dict['Column', Any], 'SQLPredicate', Tuple[str, tuple]]
    ) -> 'AsyncBaseActiveRecord':
        record = await cls.find_one(condition)
        if record is None:
            cls.log(logging.WARNING, f"Record not found for {cls.__name__} with find_one condition: {condition}")
            raise RecordNotFound(f"Record not found for {cls.__name__}")
        return record

    async def save(self) -> int:
        if not self.backend():
            raise DatabaseError("No backend configured")
        try:
            self.validate_fields()
        except Exception as e:
            self.log(logging.ERROR, f"Validation error: {str(e)}")
            raise DBValidationError(str(e))
        if not self.is_new_record and not self.is_dirty:
            return 0
        try:
            self._trigger_event(ModelEvent.BEFORE_SAVE, is_new=self.is_new_record)
        except Exception as e:
            self.log(logging.ERROR, f"Trigger event error: {str(e)}")
            raise
        try:
            return await self._save_internal()
        except Exception as e:
            self.log(logging.ERROR, f"Database error: {str(e)}")
            raise DatabaseError(str(e)) from e

    async def delete(self) -> int:
        if not self.backend():
            raise DatabaseError("No backend configured")
        if self.is_new_record:
            return 0
        self._trigger_event(ModelEvent.BEFORE_DELETE)
        backend = self.backend()
        pk_name = self.primary_key()
        pk_value = getattr(self, pk_name)
        where_predicate = ComparisonPredicate(backend.dialect, '=', Column(backend.dialect, pk_name), Literal(backend.dialect, pk_value))
        is_soft_delete = hasattr(self, 'prepare_delete')
        if is_soft_delete:
            self.log(logging.INFO, f"Soft deleting {self.__class__.__name__}#{pk_value}")
            data = self.prepare_delete()
            update_opts = UpdateOptions(table=self.table_name(), data=data, where=where_predicate)
            result = await backend.update(update_opts)
        else:
            self.log(logging.INFO, f"Deleting {self.__class__.__name__}#{pk_value}")
            supports_returning = backend.dialect.supports_returning_clause()
            returning_columns = None
            if supports_returning:
                returning_columns = [self.primary_key()]
            delete_opts = DeleteOptions(table=self.table_name(), where=where_predicate, returning_columns=returning_columns)
            result = await backend.delete(delete_opts)
        affected_rows = result.affected_rows
        if affected_rows > 0:
            if not is_soft_delete:
                if hasattr(self, pk_name):
                    setattr(self, pk_name, None)
            self.reset_tracking()
            self._trigger_event(ModelEvent.AFTER_DELETE)
        return affected_rows

    def validate_custom(self) -> None:
        pass

    @classmethod
    def transaction(cls):
        if cls.backend() is None:
            raise DatabaseError("No backend configured")
        return cls.backend().transaction()

    # region Logging Methods

    @classmethod
    def setup_logger(cls, formatter: Optional[logging.Formatter] = None) -> None:
        if not hasattr(cls, '__logger__'):
            return
        logger = getattr(cls, '__logger__')
        if logger is None or not isinstance(logger, logging.Logger):
            return
        if formatter is None:
            formatter = CustomModuleFormatter('%(asctime)s - %(levelname)s - [%(subpackage_module)s:%(lineno)d] - %(message)s')
        if logger.handlers:
            for handler in logger.handlers:
                handler.setFormatter(formatter)
        root_logger = logging.getLogger()
        for handler in root_logger.handlers:
            if not isinstance(handler.formatter, CustomModuleFormatter):
                handler.setFormatter(formatter)

    @classmethod
    def set_logger(cls, logger: logging.Logger) -> None:
        if logger is not None and not isinstance(logger, logging.Logger):
            raise ValueError("logger must be an instance of logging.Logger")
        cls.__logger__ = logger

    @classmethod
    def log(cls, level: int, msg: str, *args, **kwargs) -> None:
        if not hasattr(cls, '__logger__'):
            return
        logger = getattr(cls, '__logger__')
        if logger is None:
            return
        if not isinstance(logger, logging.Logger):
            return
        current_frame = inspect.currentframe().f_back
        stack_level = 1
        while current_frame:
            if current_frame.f_globals['__name__'] != 'ActiveRecord':
                break
            current_frame = current_frame.f_back
            stack_level += 1
        if current_frame:
            stack_level += 1
        if "offset" in kwargs:
            stack_level += kwargs.pop("offset")
        if (logger.handlers and not any(isinstance(h.formatter, CustomModuleFormatter) for h in logger.handlers)) or \
                (not logger.handlers and not any(isinstance(h.formatter, CustomModuleFormatter) for h in logging.getLogger().handlers)):
            cls.setup_logger()
        level_name = logging.getLevelName(level).lower()
        method = getattr(logger, level_name, None)
        if method is not None:
            method(msg, *args, stacklevel=stack_level, **kwargs)
        else:
            logger.log(level, msg, *args, **kwargs)

    @classmethod
    def get_column_adapters(cls) -> Dict[str, Tuple['SQLTypeAdapter', Type]]:
        adapters_map: Dict[str, Tuple['SQLTypeAdapter', Type]] = {}
        model_fields: Dict[str, FieldInfo] = dict(cls.model_fields)
        all_suggestions = cls.backend().get_default_adapter_suggestions()
        for field_name, field_info in model_fields.items():
            column_name = cls._get_column_name(field_name)
            field_py_type = field_info.annotation
            original_type = field_py_type
            origin = get_origin(field_py_type)
            if origin is Union:
                args = [arg for arg in get_args(field_py_type) if arg is not type(None)]
                if len(args) == 1:
                    field_py_type = args[0]
                else:
                    continue
            custom_adapter_tuple = cls._get_adapter_for_field(field_name)
            if custom_adapter_tuple:
                adapter_instance, _ = custom_adapter_tuple
                adapters_map[column_name] = (adapter_instance, original_type)
                continue
            suggestion = all_suggestions.get(field_py_type)
            if suggestion:
                adapter_instance, _ = suggestion
                adapters_map[column_name] = (adapter_instance, original_type)
        return adapters_map
