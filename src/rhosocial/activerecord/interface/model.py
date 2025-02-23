"""
Core ActiveRecord model interface definition.
"""
import inspect
import logging
from abc import ABC, abstractmethod
from copy import deepcopy
from typing import Any, Dict, TypeVar, ClassVar, Optional, Type, Set, get_origin, Union, List, Callable

from pydantic import BaseModel
from pydantic.fields import FieldInfo

from .base import ModelEvent
from ..backend.base import StorageBackend, ColumnTypes
from ..backend.dialect import DatabaseType
from ..backend.errors import DatabaseError, RecordNotFound
from ..backend.typing import ConnectionConfig


class CustomModuleFormatter(logging.Formatter):
    def format(self, record):
        import os
        module_dir = os.path.basename(os.path.dirname(record.pathname))
        record.subpackage_module = f"{module_dir}-{record.filename}"
        return super().format(record)


# Type variable for interface
ModelT = TypeVar('ModelT', bound='IActiveRecord')


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

    # Class-level column type cache
    __column_types_cache__: ClassVar[Optional[Dict[str, DatabaseType]]] = None

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
        """Reset type cache when initializing subclass"""
        super().__init_subclass__()
        cls.__column_types_cache__ = None

    def __setattr__(self, name: str, value: Any):
        """Overridden to track field changes.

        When a field is modified, stores the original value and marks the field as dirty.
        """
        if (name in self.model_fields and
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

    def column_types(self) -> ColumnTypes:
        """Derive database column types from model field definitions.

        Returns:
            Dict mapping column names to their DatabaseType.
        """
        # Check class cache
        if self.__class__.__column_types_cache__ is not None:
            return self.__class__.__column_types_cache__

        types: Dict[str, DatabaseType] = {}
        model_fields: Dict[str, FieldInfo] = dict(self.model_fields)

        for field_name, field_info in model_fields.items():
            db_type = self.backend().type_mapper.get_pydantic_model_field_type(field_info)
            if db_type is not None:
                types[field_name] = db_type

        # Cache result in class variable
        self.__class__.__column_types_cache__ = types
        return types

    def _insert_internal(self, data) -> Any:
        # Insert new record
        self.log(logging.INFO, f"Inserting new {self.__class__.__name__}: {data}")
        result = self.backend().insert(
            self.table_name(),
            data,
            column_types=self.column_types(),
            returning=False
        )

        # Handle auto-increment primary key if needed
        pk_field = self.primary_key()
        if (result is not None and result.affected_rows > 0 and
                pk_field in self.model_fields and
                pk_field not in data and
                getattr(self, pk_field, None) is None):

            field_type = self.model_fields[pk_field].annotation
            if get_origin(field_type) in (Union, Optional):
                types = [t for t in field_type.__args__ if t is not type(None)]
                if types:
                    field_type = types[0]

            if field_type is int:
                setattr(self, pk_field, result.last_insert_id)

        self._is_from_db = True
        return result

    def _update_internal(self, data) -> Any:
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

        # Combine base condition with additional conditions
        conditions = [f"{self.primary_key()} = ?"]
        params = [getattr(self, self.primary_key())]

        # Add additional conditions
        for condition, condition_params in update_conditions:
            conditions.append(condition)
            if condition_params:
                params.extend(condition_params)

        # Combine data with additional expressions
        data.update(update_expressions)

        self.log(logging.INFO,
                 f"Updating {self.__class__.__name__}#{getattr(self, self.primary_key())}: "
                 f"data={data}, conditions={conditions}, params={params}")

        # Execute update with combined conditions
        result = self.backend().update(
            self.table_name(),
            data,
            " AND ".join(conditions),
            tuple(params),
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
