# src/rhosocial/activerecord/interface/model.py
"""
Core ActiveRecord model interface definition.
"""
import logging
from abc import ABC, abstractmethod
from pydantic import BaseModel
from typing import Any, Dict, ClassVar, Optional, Type, Set, Union, List, Callable, TYPE_CHECKING
from typing import Protocol
from typing_extensions import runtime_checkable

from .base import ModelEvent
from ..backend.base import StorageBackend, AsyncStorageBackend
from ..backend.config import ConnectionConfig
from ..backend.errors import DatabaseError, RecordNotFound
from ..backend.schema import DatabaseType


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
        __primary_key__ (str): Primary key column name (single-column primary keys only)
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

    def __init_subclass__(cls) -> None:
        """Initialize subclass"""
        super().__init_subclass__()




    def _save_internal(self) -> int:
        """
        Internal method for saving the record (either insert or update).

        This method determines whether to perform an insert or update operation based on
        whether this is a new record or an existing one. It handles the complete save
        process including:
        1. Data preparation with mixin processing
        2. Conditional execution of insert or update based on record state
        3. Post-save processing and event triggering
        4. Tracking reset after successful save

        For both insert and update operations, if the backend supports RETURNING clauses,
        the methods will utilize them to retrieve relevant data efficiently.

        Returns:
            int: Number of affected rows from the underlying insert or update operation
        """
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
        """Get the primary key column name.

        Returns the class's __primary_key__ attribute by default. Subclasses can override
        for dynamic primary keys.

        Note: This implementation currently supports single-column primary keys only.
        For composite primary keys, a different approach would be required.

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
    def create_from_database(cls: Type['IActiveRecord'], row: Dict[str, Any]) -> 'IActiveRecord':
        """Create instance from database record"""
        instance = cls(**row)
        instance._is_from_db = True
        instance.reset_tracking()
        return instance

    @classmethod
    def create_collection_from_database(cls: Type['IActiveRecord'], rows: List[Dict[str, Any]]) -> List['IActiveRecord']:
        """Create instance collection from database records"""
        return [cls.create_from_database(row) for row in rows]

    @classmethod
    def validate_record(cls, value: Any) -> None:
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
        """
        Save the record to database, performing insert or update as appropriate.

        This method implements the core persistence functionality. If the record is
        new (determined by is_new_record property), it performs an INSERT operation.
        If the record already exists, it performs an UPDATE operation with only
        the changed fields.

        The save operation triggers appropriate model events (BEFORE_SAVE, AFTER_SAVE)
        and handles dirty field tracking to optimize updates.

        Returns:
            int: Number of affected rows in the database
                 - For INSERT operations: typically returns 1 if successful
                 - For UPDATE operations: returns the actual number of updated rows
                   (could be 0 if no fields were changed)

        Raises:
            DatabaseError: If there are issues connecting to or executing against
                          the database
            ValidationError: If the model fails validation before saving
        """
        pass

    @abstractmethod
    def delete(self) -> int:
        """
        Delete the record from database.

        This method performs a DELETE operation for the current record. It identifies
        the record to delete using the primary key value and removes it from the database.
        The operation is performed using the model's configured backend.

        The delete operation triggers appropriate model events (BEFORE_DELETE, AFTER_DELETE)
        and updates the internal state of the record.

        Returns:
            int: Number of affected rows in the database
                 - Returns 1 if the record was successfully deleted
                 - Returns 0 if no record matched the primary key (record didn't exist)

        Raises:
            DatabaseError: If there are issues connecting to or executing against
                          the database
            ValueError: If the record doesn't have a valid primary key value
        """
        pass

    @classmethod
    @abstractmethod
    def find_one(cls: Type['IActiveRecord'], condition: Union[Any, Dict[str, Any]]) -> Optional['IActiveRecord']:
        """
        Find a single record that matches the specified condition.

        This method queries the database for a record that matches the given condition
        and returns it as an instance of the model class. If no matching record is found,
        it returns None.

        The condition can be specified in multiple ways:
        - As a primary key value (e.g., find_one(123) for primary key = 123)
        - As a dictionary of field-value pairs (e.g., find_one({'username': 'john'}))
        - As a more complex condition using expression objects

        Args:
            condition: The condition to match. Can be a primary key value, a dictionary
                      of field-value pairs, or a more complex condition expression

        Returns:
            Optional[IActiveRecord]: A model instance if a matching record is found, None otherwise

        Raises:
            DatabaseError: If there are issues connecting to or executing against
                          the database
        """
        pass

    @classmethod
    @abstractmethod
    def find_all(cls: Type['IActiveRecord'], condition: Optional[Union[List[Any], Dict[str, Any]]] = None) -> List['IActiveRecord']:
        """
        Find all records that match the specified condition.

        This method queries the database for all records that match the given condition
        and returns them as a list of model instances. If no condition is provided,
        it returns all records from the table.

        Args:
            condition: Optional condition to match. Can be:
                      - A dictionary of field-value pairs (e.g., {'status': 'active'})
                      - A list of conditions for complex queries
                      - None to return all records

        Returns:
            List[IActiveRecord]: A list of model instances that match the condition.
                         Returns an empty list if no records match.

        Raises:
            DatabaseError: If there are issues connecting to or executing against
                          the database
        """
        pass

    @classmethod
    @abstractmethod
    def find_one_or_fail(cls: Type['IActiveRecord'], condition: Union[Any, Dict[str, Any]]) -> 'IActiveRecord':
        """
        Find a single record that matches the specified condition or raise an exception.

        This method behaves like find_one() but raises a RecordNotFound exception
        if no matching record is found, instead of returning None.

        Args:
            condition: The condition to match. Can be a primary key value, a dictionary
                      of field-value pairs, or a more complex condition expression

        Returns:
            IActiveRecord: A model instance if a matching record is found

        Raises:
            RecordNotFound: If no record matches the specified condition
            DatabaseError: If there are issues connecting to or executing against
                          the database
        """
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
        """
        Check if this is a new record that hasn't been saved to the database yet.

        This property determines whether the current instance represents a record
        that exists in the database or a new record that needs to be inserted.
        Typically, a record is considered new if:
        - It was created in memory but not yet saved to the database
        - It doesn't have a valid primary key value from the database
        - It has never been persisted

        Returns:
            bool: True if this is a new record that hasn't been saved to the database,
                  False if this record already exists in the database
        """
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


@runtime_checkable
class IAsyncActiveRecord(Protocol):
    """Async ActiveRecord interface, providing asynchronous database operations methods"""

    @abstractmethod
    async def save(self) -> int:
        """
        Save the record to database asynchronously, performing insert or update as appropriate.

        This method implements the core persistence functionality. If the record is
        new (determined by is_new_record property), it performs an INSERT operation.
        If the record already exists, it performs an UPDATE operation with only
        the changed fields.

        The save operation triggers appropriate model events (BEFORE_SAVE, AFTER_SAVE)
        and handles dirty field tracking to optimize updates.

        Returns:
            int: Number of affected rows in the database
                 - For INSERT operations: typically returns 1 if successful
                 - For UPDATE operations: returns the actual number of updated rows
                   (could be 0 if no fields were changed)
        """
        pass

    @abstractmethod
    async def delete(self) -> int:
        """
        Delete the record from database asynchronously.

        This method performs a DELETE operation for the current record. It identifies
        the record to delete using the primary key value and removes it from the database.
        The operation is performed using the model's configured backend.

        The delete operation triggers appropriate model events (BEFORE_DELETE, AFTER_DELETE)
        and updates the internal state of the record.

        Returns:
            int: Number of affected rows in the database
                 - Returns 1 if the record was successfully deleted
                 - Returns 0 if no record matched the primary key (record didn't exist)

        Raises:
            DatabaseError: If there are issues connecting to or executing against
                          the database
            ValueError: If the record doesn't have a valid primary key value
        """
        pass

    @classmethod
    @abstractmethod
    async def find_one(cls: Type['IAsyncActiveRecord'], condition: Union[Any, Dict[str, Any]]) -> Optional['IAsyncActiveRecord']:
        """
        Find a single record that matches the specified condition asynchronously.

        This method queries the database for a record that matches the given condition
        and returns it as an instance of the model class. If no matching record is found,
        it returns None.

        The condition can be specified in multiple ways:
        - As a primary key value (e.g., find_one(123) for primary key = 123)
        - As a dictionary of field-value pairs (e.g., find_one({'username': 'john'}))
        - As a more complex condition using expression objects

        Args:
            condition: The condition to match. Can be a primary key value, a dictionary
                      of field-value pairs, or a more complex condition expression

        Returns:
            Optional[IAsyncActiveRecord]: A model instance if a matching record is found, None otherwise

        Raises:
            DatabaseError: If there are issues connecting to or executing against
                          the database
        """
        pass

    @classmethod
    @abstractmethod
    async def find_all(cls: Type['IAsyncActiveRecord'], condition: Optional[Union[List[Any], Dict[str, Any]]] = None) -> List['IAsyncActiveRecord']:
        """
        Find all records that match the specified condition asynchronously.

        This method queries the database for all records that match the given condition
        and returns them as a list of model instances. If no condition is provided,
        it returns all records from the table.

        Args:
            condition: Optional condition to match. Can be:
                      - A dictionary of field-value pairs (e.g., {'status': 'active'})
                      - A list of conditions for complex queries
                      - None to return all records

        Returns:
            List[IAsyncActiveRecord]: A list of model instances that match the condition.
                         Returns an empty list if no records match.

        Raises:
            DatabaseError: If there are issues connecting to or executing against
                          the database
        """
        pass

    @classmethod
    @abstractmethod
    async def find_one_or_fail(cls: Type['IAsyncActiveRecord'], condition: Union[Any, Dict[str, Any]]) -> 'IAsyncActiveRecord':
        """
        Find a single record that matches the specified condition or raise an exception asynchronously.

        This method behaves like find_one() but raises a RecordNotFound exception
        if no matching record is found, instead of returning None.

        Args:
            condition: The condition to match. Can be a primary key value, a dictionary
                      of field-value pairs, or a more complex condition expression

        Returns:
            IAsyncActiveRecord: A model instance if a matching record is found

        Raises:
            RecordNotFound: If no record matches the specified condition
            DatabaseError: If there are issues connecting to or executing against
                          the database
        """
        pass

    @abstractmethod
    async def refresh(self) -> None:
        """
        Reload record from database asynchronously.

        This method uses the current record's primary key value to re-fetch the latest data
        from the database and update all field values of the current instance.
        """
        pass
