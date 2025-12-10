# src/rhosocial/activerecord/base/base.py
"""Core BaseActiveRecord implementation."""

import logging
from typing import Any, Dict, List, Optional, ClassVar, Type

from ..interface import IActiveRecord, ModelEvent
from ..backend.base import StorageBackend
from ..backend.errors import DatabaseError, RecordNotFound, ValidationError as DBValidationError
from ..backend.config import ConnectionConfig
from .typing import ConditionType, MultiConditionType, ModelT
from rhosocial.activerecord.backend.impl.dummy import DummyBackend  # Import DummyBackend

class BaseActiveRecord(IActiveRecord):
    """Core ActiveRecord implementation with basic CRUD operations.

    Provides:
    - Database configuration and connection management
    - Record creation and persistence
    - Change tracking
    - Event handling
    - Transaction support
    - Basic query operations
    """

    @classmethod
    def configure(cls, config: ConnectionConfig, backend_class: Type[StorageBackend]) -> None:
        """Configure storage backend for the model class.

        Args:
            config: Database connection settings
            backend_class: Storage backend implementation class

        Note:
            This method initializes the backend with full connection configuration
            and logger instance from the model class.
        """
        if not isinstance(config, ConnectionConfig):
            raise DatabaseError(f"Invalid connection config for {cls.__name__}")

        cls.__connection_config__ = config
        cls.__backend_class__ = backend_class

        # Initialize backend with full config and logger
        backend_instance = backend_class(connection_config=config)
        # Set logger if available
        if hasattr(cls, '__logger__'):
            backend_instance.logger = cls.__logger__

        cls.__backend__ = backend_instance
        # Invalidate dummy backend cache if a real backend is configured
        if hasattr(cls, '_dummy_backend') and cls._dummy_backend is not None:
            cls._dummy_backend = None # Invalidate cache by setting to None


    def __init__(self, **data):
        """Initialize ActiveRecord instance.

        Args:
            **data: Model data

        Raises:
            DatabaseError: If database is not configured for the model class
        """
        # if not hasattr(self.__class__, '__backend__') or self.__class__.__backend__ is None:
        #     raise DatabaseError(f"Database not configured for {self.__class__.__name__}")

        super().__init__(**data)
        self.reset_tracking()

    def __init_subclass__(cls) -> None:
        """Initialize subclass by merging all non-tracking fields."""
        super().__init_subclass__()
        # Collect non-tracking fields from all parent classes
        no_track_fields = set()
        for base in cls.__mro__:
            if hasattr(base, '__no_track_fields__'):
                no_track_fields.update(base.__no_track_fields__)
        cls.__no_track_fields__ = no_track_fields
        cls.__column_types_cache__ = None
        # Initialize _dummy_backend to None for each subclass
        cls._dummy_backend: Optional[DummyBackend] = None


    @property
    def is_from_db(self) -> bool:
        """Indicates if record was loaded from database"""
        return self._is_from_db

    @property
    def is_new_record(self) -> bool:
        """Determine if this is a new record.

        Checks:
        1. If primary key attribute exists
        2. If primary key value is None
        3. If dirty fields set is empty
        """
        pk_field_name = self.__class__.primary_key_field()
        pk_value = getattr(self, pk_field_name)

        # A record is new if its primary key field is None OR if it hasn't been loaded from the DB
        return pk_value is None or not self._is_from_db

    def _prepare_save_data(self) -> Dict[str, Any]:
        """Prepare data for database persistence.

        For new records, includes all fields.
        For updates, only includes modified fields.
        Processes data through all registered mixins.
        """
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
        """Post-save processing.

        Executes after successful save operation.
        Calls after_save handlers from all mixins.
        """
        bases = self.__class__.__mro__
        for base in bases:
            if hasattr(base, 'after_save') and base != BaseActiveRecord:
                after_method = getattr(base, 'after_save')
                after_method(self, is_new)

    @classmethod
    def find_one(cls: Type[ModelT], condition: ConditionType) -> Optional[ModelT]:
        """Find single record by primary key or conditions.

        Args:
            condition: Primary key value or query condition dict
                - For scalar value, queries by primary key
                - For dict, queries by conditions

        Returns:
            Optional[ModelT]: Found record or None

        Examples:
            # Query by primary key
            user = User.find_one(1)
            # Query by conditions
            user = User.find_one({'status': 1, 'type': 2})
        """
        query = cls.query()

        if isinstance(condition, dict):
            # Pass dictionary conditions directly. Type adaptation will be handled by the query builder.
            query = query.query(condition)
        else:
            # Pass scalar primary key condition directly. Type adaptation will be handled by the query builder.
            pk_field_name = cls.primary_key()
            query = query.where(f"{pk_field_name} = ?", (condition,))

        return query.one()

    @classmethod
    def find_all(cls: Type[ModelT], condition: MultiConditionType = None) -> List[ModelT]:
        """Find multiple records.

        Args:
            condition: List of primary keys or query condition dict
                - For primary key list, queries by primary keys
                - For dict, queries by conditions
                - For None, returns all records

        Returns:
            List[ModelT]: List of found records

        Examples:
            # Query by primary key list
            users = User.find_all([1, 2, 3])
            # Query by conditions
            users = User.find_all({'status': 1})
            # Query all records
            users = User.find_all()
        """
        query = cls.query()
        if condition is None:
            return query.all()

        if isinstance(condition, dict):
            # Pass dictionary conditions directly. Type adaptation will be handled by the query builder.
            query = query.query(condition)
        else: # Assumes list of primary keys
            # Pass list of primary keys directly. Type adaptation will be handled by the query builder.
            pk_field_name = cls.primary_key()
            
            if not condition:
                return []
                
            placeholders = ','.join(['?' for _ in condition])
            query = query.where(f"{pk_field_name} IN ({placeholders})", condition)

        return query.all()

    @classmethod
    def find_one_or_fail(cls: Type[ModelT], condition: ConditionType) -> ModelT:
        """Find single record, raise exception if not found.

        Args:
            condition: Primary key value or query condition dict

        Returns:
            ModelT: Found record

        Raises:
            RecordNotFound: When record is not found

        Examples:
            # Query by primary key
            user = User.find_one_or_fail(1)
            # Query by conditions
            user = User.find_one_or_fail({'status': 1, 'type': 2})
        """
        record = cls.find_one(condition)
        if record is None:
            cls.log(
                logging.WARNING,
                f"Record not found for {cls.__name__} with find_one condition: {condition}"
            )
            raise RecordNotFound(f"Record not found for {cls.__name__}")
        return record

    def save(self) -> int:
        """Save or update record.

        Returns:
            int: Number of affected rows. For insert operations, returns 1;
                 for update operations, returns actual number of updated rows
        """
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
        """Delete record.

        Returns:
            int: Number of affected rows
        """
        if not self.backend():
            raise DatabaseError("No backend configured")

        if self.is_new_record:
            return 0

        self._trigger_event(ModelEvent.BEFORE_DELETE)

        backend = self.backend()
        
        pk_name = self.primary_key()
        pk_value = getattr(self, pk_name)

        placeholder = backend.dialect.get_placeholder()
        condition = f"{self.primary_key()} = {placeholder}"
        # Pass raw pk_value to backend, it will be adapted by the query builder if _adapt_params is True.
        params = (pk_value,) 

        is_soft_delete = hasattr(self, 'prepare_delete')

        if is_soft_delete:
            self.log(logging.INFO, f"Soft deleting {self.__class__.__name__}#{pk_value}")
            data = self.prepare_delete()
            
            # The backend's update method will handle parameter adaptation for 'data'.
            # We don't need param_adapters here, assuming backend.update is updated to use _adapt_params.
            # (Which is handled by the overall plan if backend.update constructs queries using query builders)
            
            result = backend.update(
                self.table_name(),
                data, # Pass raw data, adaptation handled by backend if it uses a query builder.
                condition,
                params
            )
        else:
            self.log(logging.INFO, f"Deleting {self.__class__.__name__}#{pk_value}")
            result = backend.delete(
                self.table_name(),
                condition,
                params
            )

        affected_rows = result.affected_rows
        if affected_rows > 0:
            if not is_soft_delete:
                if hasattr(self, pk_name):
                    setattr(self, pk_name, None)
            self.reset_tracking()
            self._trigger_event(ModelEvent.AFTER_DELETE)

        return affected_rows

    def validate_custom(self) -> None:
        """Custom validation logic to be implemented by subclasses."""

    @classmethod
    def transaction(cls):
        """Return storage backend's transaction context manager."""
        if cls.backend() is None:
            raise DatabaseError("No backend configured")
        return cls.backend().transaction()

    @classmethod
    def backend(cls) -> StorageBackend:
        """Get storage backend instance.

        Returns the class's __backend__ attribute by default. Subclasses can override
        for dynamic backends.

        If no backend is explicitly configured, a DummyBackend instance is returned.
        The DummyBackend allows SQL generation but raises NotImplementedError for
        any database operations.

        Raises:
            DatabaseError: if backend class or connection config is invalid during configuration.
        """
        if cls.__backend__:
            return cls.__backend__
        
        # If a backend_class and config are set, but __backend__ is None,
        # it means the backend was never instantiated (e.g., configure was called,
        # but the actual __backend__ instance was not set yet). This should not happen
        # if `configure` is always called correctly. But for robustness:
        if cls.__backend_class__ and cls.__connection_config__:
            try:
                # Attempt to instantiate and cache the real backend now
                from rhosocial.activerecord.backend.impl.dummy import DummyBackend # Lazy import for initial backend check
                backend_instance = cls.__backend_class__(connection_config=cls.__connection_config__)
                if hasattr(cls, '__logger__'):
                    backend_instance.logger = cls.__logger__
                cls.__backend__ = backend_instance
                return cls.__backend__
            except Exception as e:
                # If instantiation fails, re-raise as a DatabaseError
                raise DatabaseError(f"Failed to instantiate configured backend: {e}") from e
        
        # Fallback to DummyBackend if no real backend is configured
        if not hasattr(cls, '_dummy_backend') or cls._dummy_backend is None:
            from rhosocial.activerecord.backend.impl.dummy import DummyBackend # Lazy import
            cls._dummy_backend = DummyBackend()
        return cls._dummy_backend

