# src/rhosocial/activerecord/base/base.py
"""Core BaseActiveRecord implementation."""

import inspect
import logging
from copy import deepcopy
from typing import Any, Dict, List, Optional, ClassVar, Type, Union, get_origin, get_args, Tuple, Set

from pydantic.fields import FieldInfo

from ..interface import IActiveRecord, ModelEvent
from ..backend.base import StorageBackend
from ..backend.options import InsertOptions
from ..backend.type_adapter import SQLTypeAdapter
from ..backend.errors import DatabaseError, RecordNotFound, ValidationError as DBValidationError
from ..backend.config import ConnectionConfig
from ..backend.options import DeleteOptions, UpdateOptions
from ..backend.expression import ComparisonPredicate, Column, Literal
from .typing import ConditionType, MultiConditionType, ModelT
from rhosocial.activerecord.backend.impl.dummy.backend import DummyBackend  # Import DummyBackend


class CustomModuleFormatter(logging.Formatter):
    def format(self, record):
        import os
        module_dir = os.path.basename(os.path.dirname(record.pathname))
        record.subpackage_module = f"{module_dir}-{record.filename}"
        return super().format(record)

class BaseActiveRecord(IActiveRecord):
    """
    Core ActiveRecord implementation providing the fundamental ORM functionality.

    The BaseActiveRecord class implements the ActiveRecord pattern, where each instance
    represents a row in the database table. The class provides a comprehensive set of
    features for database interaction including CRUD operations, relationship management,
    and event handling.

    Key Features:
    - Declarative model definition using type hints and Pydantic
    - Automatic schema mapping from model fields
    - Transparent database persistence
    - Dirty tracking for efficient updates
    - Comprehensive event system for lifecycle hooks
    - Flexible query interface
    - Relationship support (BelongsTo, HasOne, HasMany)
    - Transaction management
    - Type-safe database operations

    The class follows the Single Table Inheritance pattern where each model class
    corresponds to a single database table, and instances correspond to rows in that table.

    Usage:
    ```python
    class User(BaseActiveRecord):
        __table_name__ = "users"

        id: Optional[int] = Field(default=None, primary_key=True)
        username: str
        email: str
        created_at: Optional[datetime] = None

    # Create new record
    user = User(username="john", email="john@example.com")
    user.save()

    # Query records
    users = User.where(User.c.username.like("%joh%")).all()

    # Update record
    user.email = "newemail@example.com"
    user.save()

    # Delete record
    user.delete()
    ```
    """

    @classmethod
    def configure(cls, config: ConnectionConfig, backend_class: Type[StorageBackend]) -> None:
        """
        Configure the storage backend for this model class.

        This method sets up the database connection and storage backend for the model class.
        It should be called before performing any database operations with the model.
        The configuration is class-specific, meaning different model classes can use
        different database connections or backend implementations.

        Args:
            config: Connection configuration containing database settings like host,
                   port, database name, credentials, etc. The specific configuration
                   options depend on the backend implementation.
            backend_class: The StorageBackend subclass to use for database operations.
                          This allows plugging in different database implementations
                          (SQLite, PostgreSQL, MySQL, etc.) or special-purpose backends
                          (testing backends, caching backends, etc.).

        Note:
            This method affects only the current model class and its instances.
            Subclasses will inherit the configuration unless explicitly overridden.
            The configuration should typically be done during application initialization
            or before the first database operation.

        Example:
            ```python
            from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
            from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend

            config = SQLiteConnectionConfig(database="myapp.db")
            User.configure(config, SQLiteBackend)
            ```
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


    # Change tracking attributes
    _dirty_fields: set = set()  # Set of field names that have been modified
    __no_track_fields__: ClassVar[Set[str]] = set()  # Fields to exclude from change tracking
    _original_values: dict = {}  # Original values of fields before modification

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
        # Initialize instance event handlers
        self._is_from_db = False  # Flag indicating if record was loaded from database
        self._event_handlers = {event: [] for event in ModelEvent}  # Stores event handlers for model instance

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

    @property
    def is_from_db(self) -> bool:
        """Indicates if record was loaded from database"""
        return self._is_from_db

    def _insert_internal(self, data) -> Any:
        """
        Internal method for inserting a new record into the database.

        This method handles the complete insertion process including:
        1. Parameter preparation and type adaptation
        2. Field name to column name mapping
        3. Primary key retrieval using RETURNING clause if supported by the backend,
           or falling back to last_insert_id mechanism
        4. Result processing and instance state updates

        The method intelligently uses RETURNING clauses when supported by the backend
        to retrieve auto-generated primary key values, improving efficiency compared
        to separate SELECT queries.

        Args:
            data: Dictionary containing field names and values to be inserted

        Returns:
            QueryResult: Result object containing affected rows, last insert ID,
                        and returned data if RETURNING clause is used
        """
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
        prepared_data = self.__class__._map_fields_to_columns(prepared_data)
        self.log(logging.DEBUG, f"4. Prepared data with database column names and adapted values: {prepared_data}")

        self.log(logging.INFO, f"Inserting new {self.__class__.__name__}")

        # Step 5: Create column_mapping for result processing (maps column names back to field names).
        # This is derived from the model's get_column_to_field_map.
        column_mapping = self.__class__.get_column_to_field_map()
        self.log(logging.DEBUG, f"5. Column mapping for result processing: {column_mapping}")

        # Step 6: Get the column adapters for processing output (e.g., RETURNING clauses).
        column_adapters = self.get_column_adapters()
        self.log(logging.DEBUG, f"6. Column adapters map: {column_adapters}")

        # Step 7: Call `insert` with an InsertOptions object that includes prepared data, column mapping, column adapters, and returning columns if supported.

        # Determine if backend supports RETURNING clause
        supports_returning = self.backend().dialect.supports_returning_clause()

        # If backend supports RETURNING and we need to retrieve the primary key,
        # include the primary key column in returning_columns
        returning_columns = None
        if supports_returning:
            # For insert operations, we typically want to return the primary key
            # to get the auto-generated ID value
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

        # Step 8: Handle auto-increment primary key if needed.
        pk_column = self.primary_key()
        pk_field_name = self.__class__._get_field_name(pk_column)
        if (result is not None and result.affected_rows > 0 and
                pk_field_name in self.__class__.model_fields and
                prepared_data.get(pk_column) is None and
                getattr(self, pk_field_name, None) is None):

            pk_retrieved = False
            self.log(logging.DEBUG, f"8. Attempting to retrieve primary key '{pk_column}' for new record")

            # Get the Python field name corresponding to the primary key column
            pk_field_name = self.__class__._get_field_name(pk_column)
            self.log(logging.DEBUG, f"8.1 Primary key column '{pk_column}' maps to field '{pk_field_name}'")

            # Step 8.1: Priority 1: Check for RETURNING data (e.g., from PostgreSQL)
            if result.data and isinstance(result.data, list) and len(result.data) > 0:
                first_row = result.data[0]
                # Result data will have already been mapped back to field names if column_mapping was used.
                if isinstance(first_row, dict) and pk_field_name in first_row:
                    pk_value = first_row[pk_field_name]
                    setattr(self, pk_field_name, pk_value)
                    pk_retrieved = True
                    self.log(logging.DEBUG, f"8.1 Retrieved primary key '{pk_field_name}' from RETURNING clause: {pk_value}")
                else:
                    self.log(logging.WARNING, f"8.1 RETURNING clause data found, but primary key field '{pk_field_name}' is missing in the result row: {first_row}")

            # Step 8.2: Priority 2: Fallback to last_insert_id (e.g., from MySQL/SQLite)
            if not pk_retrieved and result.last_insert_id is not None:
                field_type = self.__class__.model_fields[pk_field_name].annotation
                # Handle Optional[int]
                if get_origin(field_type) in (Union, Optional):
                    types = [t for t in get_args(field_type) if t is not type(None)]
                    if types:
                        field_type = types[0]

                # last_insert_id is for integer keys.
                if field_type is int:
                    pk_value = result.last_insert_id
                    setattr(self, pk_field_name, pk_value)
                    pk_retrieved = True
                    self.log(logging.DEBUG, f"8.2 Retrieved primary key '{pk_field_name}' from last_insert_id: {pk_value}")

            # Step 8.3: If PK still not retrieved, it's an error.
            if not pk_retrieved:
                error_msg = f"Failed to retrieve primary key '{pk_field_name}' for new record after insert."
                self.log(logging.ERROR, f"8.3 {error_msg}")
                raise DatabaseError(error_msg)

        self._is_from_db = True
        self.reset_tracking()
        return result

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

    def _update_internal(self, data) -> Any:
        """
        Internal method for updating an existing record in the database.

        This method handles the complete update process including:
        1. Parameter preparation and type adaptation
        2. Field name to column name mapping
        3. WHERE clause construction using primary key
        4. Optional RETURNING clause usage if supported by the backend to retrieve
           updated record data

        The method intelligently uses RETURNING clauses when supported by the backend
        to retrieve updated record data in a single operation, improving efficiency
        compared to separate SELECT queries.

        Args:
            data: Dictionary containing field names and values to be updated

        Returns:
            QueryResult: Result object containing affected rows and returned data
                        if RETURNING clause is used
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

        # Step 1: Map Python field names in `data` to database column names.
        # This `mapped_set_data` will be used for preparing parameters.
        mapped_set_data = self.__class__._map_fields_to_columns(data)
        self.log(logging.DEBUG, f"1. SET clause raw data (Python field names): {data}")
        self.log(logging.DEBUG, f"1. SET clause mapped data (DB column names): {mapped_set_data}")

        # Step 2: Resolve and prepare the SET clause parameters using the new prioritized logic.
        set_param_adapters: Dict[str, Tuple['SQLTypeAdapter', Type]] = {}
        all_suggestions = self.backend().get_default_adapter_suggestions()

        for field_name, py_value in mapped_set_data.items(): # Iterate over mapped data to get DB column names
            resolved_adapter_info = None

            # Priority 1: Check for a field-specific adapter.
            # NOTE: Custom adapters are defined for Python field names.
            # We need to get the original field name from the mapped column name for adapter lookup.
            original_field_name = self.__class__._get_field_name(field_name)
            custom_adapter_tuple = self.__class__._get_adapter_for_field(original_field_name)
            if custom_adapter_tuple:
                resolved_adapter_info = custom_adapter_tuple

            # Priority 2: If no custom adapter was found, fall back to default suggestion.
            if not resolved_adapter_info:
                value_type = type(py_value)
                resolved_adapter_info = all_suggestions.get(value_type)

            if resolved_adapter_info:
                set_param_adapters[field_name] = resolved_adapter_info

        self.log(logging.DEBUG, f"2. Resolved SET clause parameter adapters: {len(set_param_adapters)} adapters found")

        prepared_set_data = self.backend().prepare_parameters(mapped_set_data, set_param_adapters)
        self.log(logging.DEBUG, f"2. Prepared SET clause data: {prepared_set_data}")

        # Step 3: Prepare the WHERE clause parameters.
        # (WHERE clause adaptation remains type-based as field context is not available here)
        raw_where_params_list = []
        where_conditions_list = []

        # Add primary key condition.
        pk_column = self.primary_key() # Use DB column name for WHERE clause
        pk_value = getattr(self, self.__class__.primary_key_field()) # Get value from Python field

        where_conditions_list.append(f"{pk_column} = ?")
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

        self.log(logging.DEBUG, f"3. Prepared WHERE clause parameters: {len(prepared_where_params)} parameters prepared")

        # Step 4: Create column_mapping for result processing (maps column names back to field names).
        column_mapping = self.__class__.get_column_to_field_map()
        self.log(logging.DEBUG, f"4. Column mapping for result processing: {column_mapping}")

        # Step 5: Get the column adapters for processing output.
        column_adapters = self.get_column_adapters()
        self.log(logging.DEBUG, f"5. Column adapters map: {column_adapters}")

        # Get the database backend
        backend = self.backend()

        # Get the appropriate placeholder for this database
        placeholder = backend.dialect.get_parameter_placeholder()

        # Combine base condition with additional conditions
        final_where_clause = " AND ".join(where_conditions_list)
        if placeholder != '?':
            final_where_clause = replace_question_marks(final_where_clause, placeholder)

        self.log(logging.INFO,
                 f"Updating {self.__class__.__name__}#{getattr(self, self.__class__.primary_key_field())}: "
                 f"set_data={prepared_set_data}, where_clause={final_where_clause}, where_params={prepared_where_params}")

        # Step 6: Execute update with an UpdateOptions object.
        pk_name = self.primary_key() # Get primary key name (e.g., 'id')
        pk_value = getattr(self, self.__class__.primary_key_field()) # Get value of primary key field

        # Construct the WHERE predicate using ComparisonPredicate
        where_predicate = ComparisonPredicate(
            backend.dialect, '=', Column(backend.dialect, pk_name), Literal(backend.dialect, pk_value)
        )

        # Determine if backend supports RETURNING clause
        supports_returning = backend.dialect.supports_returning_clause()

        # If backend supports RETURNING, include the primary key in returning_columns
        # to get the updated record's information
        returning_columns = None
        if supports_returning:
            # For update operations, we typically want to return the primary key
            # and possibly other important fields
            returning_columns = [self.primary_key()]

        update_options = UpdateOptions(
            table=self.table_name(),
            data=prepared_set_data, # mapped_set_data contains prepared and mapped data
            where=where_predicate,
            column_mapping=column_mapping,
            column_adapters=column_adapters,
            returning_columns=returning_columns
        )
        result = backend.update(update_options)
        return result

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
        """
        Save the current instance to the database, either inserting or updating.

        This method implements the core persistence functionality for ActiveRecord.
        If the instance is new (doesn't exist in the database), it performs an INSERT
        operation. If the instance already exists, it performs an UPDATE operation
        with only the changed fields.

        The method handles the complete save lifecycle:
        1. Prepares the data to be saved (applies type conversions, validations)
        2. Determines whether to insert or update based on primary key presence
        3. Executes the appropriate database operation
        4. Updates internal state (marks as no longer dirty)
        5. Triggers appropriate events (before_save, after_save, etc.)

        The method implements dirty tracking to optimize updates by only sending
        changed fields to the database, improving performance and reducing conflicts.

        Returns:
            int: Number of affected rows in the database
                 - For INSERT operations: typically returns 1 if successful
                 - For UPDATE operations: returns the actual number of updated rows
                   (could be 0 if no fields were changed)

        Raises:
            DatabaseError: If no backend is configured or if the save operation fails
            ValidationError: If the model fails validation before saving

        Example:
            ```python
            # Create new record
            user = User(username="john", email="john@example.com")
            user.save()  # Performs INSERT

            # Update existing record
            user.email = "newemail@example.com"
            user.save()  # Performs UPDATE with only the changed field
            ```
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
        """
        Delete the record from the database.

        This method handles the complete deletion process including:
        1. Soft delete handling if the model implements prepare_delete method
        2. Hard delete with proper WHERE clause construction using primary key
        3. Optional RETURNING clause usage if supported by the backend to retrieve
           deleted record data before removal
        4. Post-deletion processing and event triggering

        The method intelligently uses RETURNING clauses when supported by the backend
        to retrieve deleted record data in a single operation, improving efficiency
        compared to separate SELECT queries before deletion.

        Returns:
            int: Number of affected rows from the delete operation
        """
        if not self.backend():
            raise DatabaseError("No backend configured")

        if self.is_new_record:
            return 0

        self._trigger_event(ModelEvent.BEFORE_DELETE)

        backend = self.backend()
        
        pk_name = self.primary_key()
        pk_value = getattr(self, pk_name)

        where_predicate = ComparisonPredicate(
            backend.dialect, '=', Column(backend.dialect, pk_name), Literal(backend.dialect, pk_value)
        )

        is_soft_delete = hasattr(self, 'prepare_delete')

        if is_soft_delete:
            self.log(logging.INFO, f"Soft deleting {self.__class__.__name__}#{pk_value}")
            data = self.prepare_delete()
            
            update_opts = UpdateOptions(
                table=self.table_name(),
                data=data,
                where=where_predicate
            )
            result = backend.update(update_opts)
        else:
            self.log(logging.INFO, f"Deleting {self.__class__.__name__}#{pk_value}")

            # Determine if backend supports RETURNING clause
            supports_returning = backend.dialect.supports_returning_clause()

            # If backend supports RETURNING, include the primary key and other important columns
            # in returning_columns to get the deleted record's information
            returning_columns = None
            if supports_returning:
                # For delete operations, we typically want to return the primary key
                # and possibly other important fields to confirm what was deleted
                returning_columns = [self.primary_key()]

            delete_opts = DeleteOptions(
                table=self.table_name(),
                where=where_predicate,
                returning_columns=returning_columns
            )
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
        """Custom validation logic to be implemented by subclasses."""

    @classmethod
    def transaction(cls):
        """Return storage backend's transaction context manager."""
        if cls.backend() is None:
            raise DatabaseError("No backend configured")
        return cls.backend().transaction()

    # region Logging Methods

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

    @classmethod
    def get_column_adapters(cls) -> Dict[str, Tuple['SQLTypeAdapter', Type]]:
        """
        Derives a mapping of database column names to their corresponding SQLTypeAdapter
        and the original Python type of the field for result processing.

        This method queries the backend for its default type adapter suggestions
        and uses these to build a model-specific map for converting database
        results back into Python objects. It prioritizes user-defined adapters
        specified via annotations.

        The keys of the returned dictionary are database column names.
        """
        adapters_map: Dict[str, Tuple['SQLTypeAdapter', Type]] = {}
        model_fields: Dict[str, FieldInfo] = dict(cls.model_fields)
        all_suggestions = cls.backend().get_default_adapter_suggestions()

        for field_name, field_info in model_fields.items():
            # Get the database column name for this field
            column_name = cls._get_column_name(field_name)

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
                adapters_map[column_name] = (adapter_instance, original_type) # Key by column_name
                continue

            # Priority 2: Fallback to the backend's default suggestion.
            suggestion = all_suggestions.get(field_py_type)
            if suggestion:
                adapter_instance, _ = suggestion
                # The 'original_type' is crucial for 'from_database' conversion.
                adapters_map[column_name] = (adapter_instance, original_type) # Key by column_name

        return adapters_map

    @classmethod
    def backend(cls) -> StorageBackend:
        """
        Get the storage backend instance for this model class.

        This method provides access to the configured storage backend for the model class.
        It implements a lazy loading pattern where the backend is initialized on first
        access if it hasn't been explicitly configured.

        The method follows this resolution order:
        1. Returns the cached __backend__ instance if already initialized
        2. Attempts to create a backend instance if configuration exists but backend isn't initialized
        3. Falls back to a DummyBackend if no configuration exists

        The DummyBackend is a special backend implementation that allows SQL generation
        and query building without requiring an active database connection. It's useful
        for testing, schema introspection, and static analysis.

        Args:
            cls: The model class requesting the backend (implicit from @classmethod)

        Returns:
            StorageBackend: The configured backend instance for this model class.
                           Could be a real backend (SQLite, PostgreSQL, etc.) or
                           a DummyBackend if no configuration exists.

        Note:
            This method is thread-safe and implements lazy initialization. Subclasses
            can override this method to implement dynamic backend selection based
            on runtime conditions (e.g., sharding, read replicas, etc.).

        Raises:
            DatabaseError: If there are issues initializing the backend due to
                          invalid configuration or connection problems.

        Example:
            ```python
            # Get the backend for a model class
            backend = User.backend()

            # Use backend directly for low-level operations
            result = backend.execute("SELECT * FROM users WHERE id = ?", (1,))
            ```
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
                from rhosocial.activerecord.backend.impl.dummy.backend import DummyBackend # Lazy import for initial backend check
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
            from rhosocial.activerecord.backend.impl.dummy.backend import DummyBackend # Lazy import
            cls._dummy_backend = DummyBackend()
        return cls._dummy_backend

