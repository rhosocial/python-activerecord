# src/rhosocial/activerecord/interface/model.py
"""
Core ActiveRecord model interface definition.
"""
import inspect
import logging
from abc import ABC, abstractmethod
from copy import deepcopy
from typing import Any, Dict, TypeVar, ClassVar, Optional, Type, Set, get_origin, Union, List, Callable, Tuple, \
    TYPE_CHECKING, get_args

from pydantic import BaseModel
from pydantic.fields import FieldInfo

from .base import ModelEvent
from ..backend.base import StorageBackend
from ..backend.errors import DatabaseError, RecordNotFound
from ..backend.typing import DatabaseType
from ..backend.config import ConnectionConfig

if TYPE_CHECKING:
    from ..backend.type_adapter import SQLTypeAdapter


class CustomModuleFormatter(logging.Formatter):
    def format(self, record):
        import os
        module_dir = os.path.basename(os.path.dirname(record.pathname))
        record.subpackage_module = f"{module_dir}-{record.filename}"
        return super().format(record)


# Type variable for interface
ModelT = TypeVar('ModelT', bound='IActiveRecord')

"""Utility functions for database placeholder handling."""


def replace_question_marks(sql: str, placeholder: str) -> str:
    """Replace question mark placeholders with database-specific placeholders.

    This utility function carefully replaces question marks that are used as parameter
    placeholders, while preserving question marks that might appear in string literals.

    Args:
        sql: Original SQL with question mark placeholders
        placeholder: Database-specific placeholder to use

    Returns:
        SQL with replaced placeholders
    """
    # Check if we need indexed placeholders (e.g., $1, $2, $3 for PostgreSQL)
    if placeholder.find('%d') != -1:
        # For indexed placeholders
        parts = []
        param_index = 1
        i = 0
        while i < len(sql):
            if sql[i] == '?':
                # Replace with indexed placeholder
                parts.append(placeholder % param_index)
                param_index += 1
            else:
                parts.append(sql[i])
            i += 1
        return ''.join(parts)
    else:
        # For non-indexed placeholders
        return sql.replace('?', placeholder)


class IActiveRecord(BaseModel, ABC):
    """Base interface for ActiveRecord models.

    Defines core functionality that all ActiveRecord models must implement, including:
    - Database connection and configuration
    - CRUD operations
    - Field tracking for changes
    - Event handling
    - Validation

    Attributes:
        __table_name__ (str): Database table name
        __primary_key__ (str): Primary key column name
        __backend__ (StorageBackend): Database storage backend
        __backend_class__ (Type[StorageBackend]): Backend implementation class
        __connection_config__ (ConnectionConfig): Connection configuration
        __logger__ (Logger): Logger instance
        __column_types_cache__ (Dict[str, DatabaseType]): Column type cache
        _dirty_fields (Set[str]): Set of modified field names
        __no_track_fields__ (Set[str]): Fields excluded from change tracking
        _original_values (Dict): Original field values before modification
    """
    __table_name__: ClassVar[Optional[str]] = None
    __primary_key__: ClassVar[str] = 'id'
    __backend__: Optional[StorageBackend] = None
    __backend_class__: ClassVar[Type[StorageBackend]] = None
    __connection_config__: ClassVar[Optional[ConnectionConfig]] = None
    __logger__: ClassVar[logging.Logger] = logging.getLogger('activerecord')


    # Change tracking attributes
    _dirty_fields = set()  # Set of field names that have been modified
    __no_track_fields__: ClassVar[Set[str]] = set()  # Fields to exclude from change tracking
    _original_values = {}  # Original values of fields before modification

    def __init__(self, **data):
        super().__init__(**data)
        # Initialize instance event handlers
        self._is_from_db = False  # Flag indicating if record was loaded from database
        self._event_handlers = {event: [] for event in ModelEvent}  # Stores event handlers for model instance

    def __init_subclass__(cls) -> None:
        """Initialize subclass"""
        super().__init_subclass__()

    def __setattr__(self, name: str, value: Any):
        """Overridden to track field changes.

        When a field is modified, stores the original value and marks the field as dirty.
        """
        if (name in self.__class__.model_fields and
                hasattr(self, '_original_values') and
                name not in self.__class__.__no_track_fields__):
            if name not in self._original_values:
                self._original_values[name] = getattr(self, name, None)
            if value != self._original_values[name]:
                self._dirty_fields.add(name)
        super().__setattr__(name, value)

    def reset_tracking(self):
        """Reset change tracking state by clearing dirty fields and storing current values."""
        self._dirty_fields.clear()
        self._original_values = self.model_dump()

    @classmethod
    def setup_logger(cls, formatter: Optional[logging.Formatter] = None) -> None:
        """Setup logger with custom formatter.

        Args:
            cls: Class that needs logging
            formatter: Optional custom formatter. If None, will use CustomModuleFormatter
        """
        if not hasattr(cls, '__logger__'):
            return

        logger = getattr(cls, '__logger__')
        if logger is None or not isinstance(logger, logging.Logger):
            return

        # Create default formatter if none provided
        if formatter is None:
            formatter = CustomModuleFormatter(
                '%(asctime)s - %(levelname)s - [%(subpackage_module)s:%(lineno)d] - %(message)s'
            )

        # Apply formatter to all existing handlers if any
        if logger.handlers:
            for handler in logger.handlers:
                handler.setFormatter(formatter)

        # Apply formatter to root logger's handlers for cases when no handlers present
        root_logger = logging.getLogger()
        for handler in root_logger.handlers:
            if not isinstance(handler.formatter, CustomModuleFormatter):
                handler.setFormatter(formatter)

    @classmethod
    def set_logger(cls, logger: logging.Logger) -> None:
        """Set logger instance.

        Args:
            logger: Logger instance or None
        """
        if logger is not None and not isinstance(logger, logging.Logger):
            raise ValueError("logger must be an instance of logging.Logger")
        cls.__logger__ = logger

    @classmethod
    def log(cls, level: int, msg: str, *args, **kwargs) -> None:
        """Log message.

        Args:
            level: Log level
            msg: Log message
            *args: Format args
            **kwargs: Extra args
        """
        # Check if __logger__ attribute exists
        if not hasattr(cls, '__logger__'):
            return

        logger = getattr(cls, '__logger__')
        # Check if logger is None
        if logger is None:
            return

        # Check if logger is Logger type
        if not isinstance(logger, logging.Logger):
            return

        # Calculate stack level
        current_frame = inspect.currentframe().f_back
        stack_level = 1  # Include log_info itself
        while current_frame:
            if current_frame.f_globals['__name__'] != 'ActiveRecord':
                break
            current_frame = current_frame.f_back
            stack_level += 1
        if current_frame:
            stack_level += 1  # Pointed to the frame of the user code.

        # Handle offset if provided
        if "offset" in kwargs:
            stack_level += kwargs.pop("offset")

        # Ensure custom formatter is set
        if (logger.handlers and not any(isinstance(h.formatter, CustomModuleFormatter) for h in logger.handlers)) or \
                (not logger.handlers and not any(
                    isinstance(h.formatter, CustomModuleFormatter) for h in logging.getLogger().handlers)):
            cls.setup_logger()

        # Get appropriate logging method
        level_name = logging.getLevelName(level).lower()
        method = getattr(logger, level_name, None)

        # Log message
        if method is not None:
            method(msg, *args, stacklevel=stack_level, **kwargs)
        else:
            logger.log(level, msg, *args, **kwargs)

    @property
    def is_dirty(self) -> bool:
        """Check if record has changes"""
        return len(self._dirty_fields) > 0

    @property
    def dirty_fields(self) -> Set[str]:
        """Get set of changed fields"""
        return self._dirty_fields.copy()

    def get_old_attribute(self, field_name: str) -> Optional[Any]:
        """Get old attribute value."""
        return deepcopy(self._original_values[field_name])

    @classmethod
    def get_column_adapters(cls) -> Dict[str, Tuple['SQLTypeAdapter', Type]]:
        """
        Derives a mapping of column names to their corresponding SQLTypeAdapter
        and the original Python type of the field for result processing.

        This method queries the backend for its default type adapter suggestions
        and uses these to build a model-specific map for converting database
        results back into Python objects. It prioritizes user-defined adapters
        specified via annotations.
        """
        adapters_map: Dict[str, Tuple['SQLTypeAdapter', Type]] = {}
        model_fields: Dict[str, FieldInfo] = dict(cls.model_fields)
        all_suggestions = cls.backend().get_default_adapter_suggestions()

        for field_name, field_info in model_fields.items():
            # Get the original Python type of the field.
            field_py_type = field_info.annotation
            original_type = field_py_type # Keep the full original type for from_database

            # Handle complex types like Optional[T] to get the base type for suggestion lookup.
            origin = get_origin(field_py_type)
            if origin is Union:
                args = [arg for arg in get_args(field_py_type) if arg is not type(None)]
                if len(args) == 1:
                    field_py_type = args[0]
                else:
                    continue # Skip complex Unions for now.

            # Priority 1: Check for a field-specific adapter from annotations.
            custom_adapter_tuple = cls._get_adapter_for_field(field_name)
            if custom_adapter_tuple:
                adapter_instance, _ = custom_adapter_tuple
                # For reading from DB, we pair the adapter with the field's original Python type.
                adapters_map[field_name] = (adapter_instance, original_type)
                continue

            # Priority 2: Fallback to the backend's default suggestion.
            suggestion = all_suggestions.get(field_py_type)
            if suggestion:
                adapter_instance, _ = suggestion
                # The 'original_type' is crucial for 'from_database' conversion.
                adapters_map[field_name] = (adapter_instance, original_type)

        return adapters_map

    def _insert_internal(self, data) -> Any:
        self.log(logging.DEBUG, f"1. Raw data for insert: {data}")

        # Step 2: Resolve parameter adapters with the new prioritized logic.
        param_adapters: Dict[str, Tuple['SQLTypeAdapter', Type]] = {}
        all_suggestions = self.backend().get_default_adapter_suggestions()

        for field_name, py_value in data.items():
            resolved_adapter_info = None

            # Priority 1: Check for a field-specific adapter from annotations.
            custom_adapter_tuple = self.__class__._get_adapter_for_field(field_name)
            if custom_adapter_tuple:
                # User-specified adapter (adapter, target_db_type) found. Use it directly.
                resolved_adapter_info = custom_adapter_tuple

            # Priority 2: If no custom adapter was found, fall back to default suggestion.
            if not resolved_adapter_info:
                value_type = type(py_value)
                resolved_adapter_info = all_suggestions.get(value_type)

            if resolved_adapter_info:
                param_adapters[field_name] = resolved_adapter_info

        self.log(logging.DEBUG, f"2. Resolved parameter adapters: {len(param_adapters)} adapters found")

        # Step 3: Prepare the INPUT parameters using the resolved adapters.
        prepared_data = self.backend().prepare_parameters(data, param_adapters)
        self.log(logging.DEBUG, f"3. Prepared data with Python field names and adapted values: {prepared_data}")

        # Step 4: Translate Python field names to database column names.
        prepared_data = self.__class__._translate_fields_to_columns(prepared_data)
        self.log(logging.DEBUG, f"4. Prepared data with database column names and adapted values: {prepared_data}")

        self.log(logging.INFO, f"Inserting new {self.__class__.__name__}")

        # Step 5: Get the column adapters for processing output (e.g., RETURNING clauses).
        column_adapters = self.get_column_adapters()
        self.log(logging.DEBUG, f"5. Column adapters map: {column_adapters}")

        # Step 6: Call `insert` with the prepared data and column adapters.
        result = self.backend().insert(
            self.table_name(),
            prepared_data,
            column_adapters=column_adapters, # Pass column_adapters for output processing.
            returning=False,
            primary_key=self.primary_key()
        )

        # Step 7: Handle auto-increment primary key if needed.
        pk_field = self.primary_key()
        if (result is not None and result.affected_rows > 0 and
                pk_field in self.__class__.model_fields and
                pk_field not in data and
                getattr(self, pk_field, None) is None):

            pk_retrieved = False
            self.log(logging.DEBUG, f"7. Attempting to retrieve primary key '{pk_field}' for new record")

            # Step 7.1: Priority 1: Check for RETURNING data (e.g., from PostgreSQL)
            if result.data and isinstance(result.data, list) and len(result.data) > 0:
                first_row = result.data[0]
                if isinstance(first_row, dict) and pk_field in first_row:
                    pk_value = first_row[pk_field]
                    setattr(self, pk_field, pk_value)
                    pk_retrieved = True
                    self.log(logging.DEBUG, f"7.1 Retrieved primary key '{pk_field}' from RETURNING clause: {pk_value}")
                else:
                    self.log(logging.WARNING, f"7.1 RETURNING clause data found, but primary key '{pk_field}' is missing in the result row: {first_row}")

            # Step 7.2: Priority 2: Fallback to last_insert_id (e.g., from MySQL/SQLite)
            if not pk_retrieved and result.last_insert_id is not None:
                field_type = self.__class__.model_fields[pk_field].annotation
                # Handle Optional[int]
                if get_origin(field_type) in (Union, Optional):
                    types = [t for t in get_args(field_type) if t is not type(None)]
                    if types:
                        field_type = types[0]

                # last_insert_id is for integer keys.
                if field_type is int:
                    pk_value = result.last_insert_id
                    setattr(self, pk_field, pk_value)
                    pk_retrieved = True
                    self.log(logging.DEBUG, f"7.2 Retrieved primary key '{pk_field}' from last_insert_id: {pk_value}")

            # Step 7.3: If PK still not retrieved, it's an error.
            if not pk_retrieved:
                error_msg = f"Failed to retrieve primary key '{pk_field}' for new record after insert."
                self.log(logging.ERROR, f"7.3 {error_msg}")
                raise DatabaseError(error_msg)

        self._is_from_db = True
        return result

    def _update_internal(self, data) -> Any:
        """Internal method for updating an existing record with enhanced conditions and expressions.

        This method handles the construction of the update query with all necessary conditions
        and special expressions from model mixins. It properly converts placeholders to match
        the database backend's requirements.

        Args:
            data: The data dictionary to be updated

        Returns:
            The result of the update operation
        """
        # Update existing record with enhanced conditions and expressions
        update_conditions = []
        update_expressions = {}

        # Collect additional conditions and expressions from mixins
        mro = self.__class__.__mro__
        activerecord_idx = mro.index(IActiveRecord)
        for cls in mro[:activerecord_idx]:
            if (hasattr(cls, 'get_update_conditions') and
                    hasattr(cls, 'get_update_expressions')):
                # Get conditions and expressions from this class
                behavior_conditions = cls.get_update_conditions(self)
                behavior_expressions = cls.get_update_expressions(self)

                # Add to update conditions and expressions
                if behavior_conditions:
                    update_conditions.extend(behavior_conditions)
                if behavior_expressions:
                    update_expressions.update(behavior_expressions)

        # Combine data with additional expressions. This 'data' becomes the SET clause values.
        data.update(update_expressions)

        # Step 1: Resolve and prepare the SET clause parameters using the new prioritized logic.
        set_param_adapters: Dict[str, Tuple['SQLTypeAdapter', Type]] = {}
        all_suggestions = self.backend().get_default_adapter_suggestions()

        for field_name, py_value in data.items():
            resolved_adapter_info = None

            # Priority 1: Check for a field-specific adapter.
            custom_adapter_tuple = self.__class__._get_adapter_for_field(field_name)
            if custom_adapter_tuple:
                resolved_adapter_info = custom_adapter_tuple

            # Priority 2: If no custom adapter was found, fall back to default suggestion.
            if not resolved_adapter_info:
                value_type = type(py_value)
                resolved_adapter_info = all_suggestions.get(value_type)

            if resolved_adapter_info:
                set_param_adapters[field_name] = resolved_adapter_info

        self.log(logging.DEBUG, f"1. Resolved SET clause parameter adapters: {len(set_param_adapters)} adapters found")

        prepared_set_data = self.backend().prepare_parameters(data, set_param_adapters)


        # Step 2: Prepare the WHERE clause parameters.
        # (WHERE clause adaptation remains type-based as field context is not available here)
        raw_where_params_list = []
        where_conditions_list = []

        # Add primary key condition.
        pk_field_name = self.primary_key()
        pk_value = getattr(self, pk_field_name)
        
        where_conditions_list.append(f"{pk_field_name} = ?")
        raw_where_params_list.append(pk_value)

        # Add additional conditions from mixins.
        for condition_str, condition_params in update_conditions:
            where_conditions_list.append(condition_str)
            if condition_params:
                raw_where_params_list.extend(condition_params)
        
        # Build param_adapters for the WHERE clause parameters.
        where_param_adapters_sequence: List[Optional[Tuple['SQLTypeAdapter', Type]]] = []
        for raw_value in raw_where_params_list:
            value_type = type(raw_value)
            suggestion = all_suggestions.get(value_type)
            where_param_adapters_sequence.append(suggestion)

        # Prepare the WHERE clause parameters using the resolved adapters.
        prepared_where_params = self.backend().prepare_parameters(
            tuple(raw_where_params_list), # Pass as a tuple for prepare_parameters
            where_param_adapters_sequence
        )

        self.log(logging.DEBUG, f"2. Prepared WHERE clause parameters: {len(prepared_where_params)} parameters prepared")


        # Get the database backend
        backend = self.backend()

        # Get the appropriate placeholder for this database
        placeholder = backend.dialect.get_placeholder()

        # Combine base condition with additional conditions
        final_where_clause = " AND ".join(where_conditions_list)
        if placeholder != '?':
            final_where_clause = replace_question_marks(final_where_clause, placeholder)

        self.log(logging.INFO,
                 f"Updating {self.__class__.__name__}#{getattr(self, self.primary_key())}: "
                 f"set_data={prepared_set_data}, where_clause={final_where_clause}, where_params={prepared_where_params}")

        # Step 3: Get the column adapters for processing output.
        column_adapters = self.get_column_adapters()
        self.log(logging.DEBUG, f"[DEBUG] Column adapters map: {column_adapters}")

        # Step 4: Execute update with prepared SET data, prepared WHERE clause, and column adapters.
        result = backend.update(
            self.table_name(),
            prepared_set_data,
            final_where_clause,
            prepared_where_params,
            column_adapters=column_adapters
        )
        return result

    def _save_internal(self) -> int:
        is_new = self.is_new_record

        # Prepare data for saving (including mixin processing)
        data = self._prepare_save_data()
        result = self._insert_internal(data) if is_new else self._update_internal(data)

        if result is not None and result.affected_rows > 0:
            self._after_save(is_new)
            self.reset_tracking()

        self._trigger_event(ModelEvent.AFTER_SAVE, is_new=is_new, result=result)

        return result.affected_rows

    @classmethod
    def table_name(cls) -> str:
        """Get the table name for this model.

        Returns the class's __table_name__ attribute by default. Subclasses can override
        for dynamic table names.

        Returns:
            str: Database table name

        Raises:
            ValueError: If table name is not set or invalid

        Example:
            @classmethod
            def table_name(cls):
                # Monthly partitioned table
                return f"{cls.__table_name__}_{datetime.now():%Y%m}"

            @classmethod
            def table_name(cls):
                # Add table prefix
                return f"{cls.get_prefix()}{cls.__table_name__}"
        """
        if cls.__table_name__ is None:
            raise ValueError(f"table_name not set for {cls.__name__}")
        if type(cls.__table_name__) is not str:
            raise ValueError(f"table_name must be str, not {cls.__table_name__}")
        return cls.__table_name__

    @classmethod
    def primary_key(cls) -> str:
        """Get primary key name.

        Returns the class's __primary_key__ attribute by default. Subclasses can override
        for dynamic primary keys.

        Example:
            @classmethod
            def primary_key(cls):
                return f"{cls.__primary_key__}_{cls.get_shard()}"
        """
        return cls.__primary_key__

    @classmethod
    def backend(cls) -> Optional[StorageBackend]:
        """Get storage backend instance.

        Returns the class's __backend__ attribute by default. Subclasses can override
        for dynamic backends.

        Example:
            @classmethod
            def backend(cls):
                if cls.is_archive():
                    return archive_backend
                return cls.__backend__

        Raises:
            DatabaseError: if no backend is available
        """
        if not cls.__backend__:
            raise DatabaseError("No backend configured")
        return cls.__backend__

    @classmethod
    def create_from_database(cls: Type[ModelT], row: Dict[str, Any]) -> ModelT:
        """Create instance from database record"""
        instance = cls(**row)
        instance._is_from_db = True
        instance.reset_tracking()
        return instance

    @classmethod
    def create_collection_from_database(cls: Type[ModelT], rows: List[Dict[str, Any]]) -> List[ModelT]:
        """Create instance collection from database records"""
        return [cls.create_from_database(row) for row in rows]

    @classmethod
    def validate_record(cls: Type[ModelT], value: Any) -> None:
        """Execute business rule validation.

        Unlike Pydantic's data type validation, this method focuses on business rules like:
        - Field relationship validation (e.g. end date must be after start date)
        - Business constraint validation (e.g. account balance cannot be negative)
        - Uniqueness validation (e.g. username must be unique)
        - State transition validation (e.g. order status change rules)

        Args:
            value: Record instance to validate

        Raises:
            ValidationError: When business rule validation fails

        Example:
            @classmethod
            def validate_record(cls, value):
                if value.end_date <= value.start_date:
                    raise ValidationError("End date must be after start date")
        """
        pass

    def validate_fields(self, *args, **kwargs):
        """Validate model fields and business rules.

        Executes both Pydantic field validation and custom business rule validation.
        Triggers BEFORE_VALIDATE and AFTER_VALIDATE events.

        Raises:
            ValidationError: If validation fails

        Example:
            def validate_fields(self):
                super().validate_fields()
                if self.end_date <= self.start_date:
                    raise ValidationError("End date must be after start date")
        """
        self._trigger_event(ModelEvent.BEFORE_VALIDATE)
        # First execute Pydantic base validation
        self.model_validate(self.model_dump())
        # Then execute record level validation
        self.validate_record(self)
        self._trigger_event(ModelEvent.AFTER_VALIDATE)

    @abstractmethod
    def save(self) -> int:
        """Save the record to database.

        Returns:
            Number of affected rows
        """
        pass

    @abstractmethod
    def delete(self) -> int:
        """Delete the record from database.

        Returns:
            Number of affected rows
        """
        pass

    @classmethod
    @abstractmethod
    def find_one(cls: Type[ModelT], condition: Union[Any, Dict[str, Any]]) -> Optional[ModelT]:
        """Find single record by condition"""
        pass

    @classmethod
    @abstractmethod
    def find_all(cls: Type[ModelT], condition: Optional[Union[List[Any], Dict[str, Any]]] = None) -> List[ModelT]:
        """Find all records matching condition"""
        pass

    @classmethod
    @abstractmethod
    def find_one_or_fail(cls: Type[ModelT], condition: Union[Any, Dict[str, Any]]) -> ModelT:
        """Find single record or raise exception"""
        pass

    def refresh(self) -> None:
        """Reload record from database"""
        pk_value = getattr(self, self.primary_key(), None)
        if pk_value is None:
            raise DatabaseError("Cannot refresh unsaved record")

        self.log(logging.DEBUG, f"Refreshing {self.__class__.__name__}#{pk_value}")

        record: __class__ = self.find_one(pk_value)

        if record is None:
            raise RecordNotFound(f"Record not found: {self.__class__.__name__}#{pk_value}")

        # Update all field values
        self.__dict__.update(record.__dict__)

        self._is_from_db = True
        self.reset_tracking()

    @property
    @abstractmethod
    def is_new_record(self) -> bool:
        """Check if this is a new record"""
        pass

    def on(self, event: ModelEvent, handler: Callable) -> None:
        """Register event handler (instance level)"""
        if not hasattr(self, '_event_handlers'):
            self._event_handlers = {event: [] for event in ModelEvent}
        self._event_handlers[event].append(handler)

    def off(self, event: ModelEvent, handler: Callable) -> None:
        """Remove event handler (instance level)"""
        if hasattr(self, '_event_handlers') and handler in self._event_handlers[event]:
            self._event_handlers[event].remove(handler)

    def _trigger_event(self, event: ModelEvent, **kwargs) -> None:
        """Trigger event (instance level)"""
        if hasattr(self, '_event_handlers'):
            for handler in self._event_handlers[event]:
                handler(self, **kwargs)

    def _prepare_save_data(self) -> Dict[str, Any]:
        """Prepare data for saving.

        This method processes the model's fields and prepares them for saving
        to the database. It handles tracking changed fields and applying any
        necessary transformations.

        Returns:
            Dict containing the fields to be saved
        """
        data = {}
        if self.is_dirty:
            # Only include changed fields for existing records
            for field in self._dirty_fields:
                value = getattr(self, field)
                data[field] = value
        else:
            # Include all fields for new records
            data = self.model_dump()
        return data

    def _after_save(self, is_new: bool) -> None:
        """Process after save operations.

        This method is called after a successful save operation to handle
        any necessary cleanup or post-save tasks.

        Args:
            is_new: Whether this was a new record
        """
        # Mark record as from database
        self._is_from_db = True
        # Reset change tracking
        self.reset_tracking()

    @classmethod
    def get_feature_handlers(cls) -> List[Callable]:
        """
        Discovers and collects unique feature handlers from the class's MRO.

        This method walks the inheritance hierarchy (MRO) and collects all handlers
        defined in `_feature_handlers` lists within parent classes and mixins.
        It ensures that each handler is unique and maintains a consistent order.

        Returns:
            A list of unique feature handler classes, ordered by their appearance
            in the MRO.
        """
        collected_handlers = {}
        # We iterate through the MRO in reverse. This ensures that handlers
        # from base classes are registered before handlers from child classes.
        for mro_class in reversed(cls.mro()):
            if hasattr(mro_class, '_feature_handlers'):
                for handler in mro_class._feature_handlers:
                    collected_handlers[handler] = True  # Use dict for ordered set
        return list(collected_handlers.keys())
