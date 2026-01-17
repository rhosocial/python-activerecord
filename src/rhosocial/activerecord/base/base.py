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
        __primary_key__ = "id"  # Specify the database column name for the primary key

        id: Optional[int] = Field(default=None)  # Note: pydantic's primary_key=True is deprecated
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

    # Get primary key column name
    pk_column = User.primary_key()  # Returns "id"
    ```

    Note: Unlike traditional ORMs, this implementation does not rely on pydantic's
    Field(primary_key=True) for primary key detection. Instead, it uses the __primary_key__
    class attribute and the primary_key() method. This allows for more flexibility
    in primary key handling, including dynamic primary keys based on runtime conditions.

    Important: Currently, the implementation supports single-column primary keys only.
    The __primary_key__ attribute should be set to a single column name string.
    Composite primary keys are not supported in the current implementation.
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
            config: Connection configuration
            backend_class: The backend implementation class

        Note:
            This method is typically called at the application startup to initialize
            the database connection for the model. It supports different configurations
            for different models, allowing for multi-database architectures.

        Example:
            ```python
            from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
            from rhosocial.activerecord.backend.config import ConnectionConfig

            # Configure the User model to use SQLite
            config = ConnectionConfig(database="my_db.sqlite")
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
            cls._dummy_backend = None

    @classmethod
    def backend(cls) -> StorageBackend:
        """Get synchronous storage backend instance."""
        return super().backend()

    @classmethod
    def create_from_database(cls, row: Dict[str, Any]) -> 'BaseActiveRecord':
        """Create instance from database record"""
        instance = cls(**row)
        instance._is_from_db = True
        instance.reset_tracking()
        return instance

    @classmethod
    def create_collection_from_database(cls, rows: List[Dict[str, Any]]) -> List['BaseActiveRecord']:
        """Create instance collection from database records"""
        return [cls.create_from_database(row) for row in rows]

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
        self.log(logging.DEBUG, f"Raw data for insert: {data}")

        # Translate Python field names to database column names.
        # The backend's execute method will handle parameter type adaptation.
        prepared_data = self.__class__._map_fields_to_columns(data)
        self.log(logging.DEBUG, f"Data with database column names: {prepared_data}")

        self.log(logging.INFO, f"Inserting new {self.__class__.__name__}")

        # Create column_mapping for result processing (maps column names back to field names).
        # This is derived from the model's get_column_to_field_map.
        column_mapping = self.__class__.get_column_to_field_map()
        self.log(logging.DEBUG, f"Column mapping for result processing: {column_mapping}")

        # Get the column adapters for processing output (e.g., RETURNING clauses).
        column_adapters = self.get_column_adapters()
        self.log(logging.DEBUG, f"Column adapters map: {column_adapters}")

        # Call `insert` with an InsertOptions object that includes prepared data, column mapping, column adapters, and returning columns if supported.

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

        # Handle auto-increment primary key if needed.
        pk_column = self.primary_key()
        pk_field_name = self.__class__._get_field_name(pk_column)
        if (result is not None and result.affected_rows > 0 and
                pk_field_name in self.__class__.model_fields and
                prepared_data.get(pk_column) is None and
                getattr(self, pk_field_name, None) is None):

            pk_retrieved = False
            self.log(logging.DEBUG, f"Attempting to retrieve primary key '{pk_column}' for new record")

            # Get the Python field name corresponding to the primary key column
            pk_field_name = self.__class__._get_field_name(pk_column)
            self.log(logging.DEBUG, f"Primary key column '{pk_column}' maps to field '{pk_field_name}'")

            # Priority 1: Check for RETURNING data (e.g., from PostgreSQL)
            if result.data and isinstance(result.data, list) and len(result.data) > 0:
                first_row = result.data[0]
                # Result data will have already been mapped back to field names if column_mapping was used.
                if isinstance(first_row, dict) and pk_field_name in first_row:
                    pk_value = first_row[pk_field_name]
                    setattr(self, pk_field_name, pk_value)
                    pk_retrieved = True
                    self.log(logging.DEBUG, f"Retrieved primary key '{pk_field_name}' from RETURNING clause: {pk_value}")
                else:
                    self.log(logging.WARNING, f"RETURNING clause data found, but primary key field '{pk_field_name}' is missing in the result row: {first_row}")

            # Priority 2: Fallback to last_insert_id (e.g., from MySQL/SQLite)
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
                    self.log(logging.DEBUG, f"Retrieved primary key '{pk_field_name}' from last_insert_id: {pk_value}")

            # If PK still not retrieved, it's an error.
            if not pk_retrieved:
                error_msg = f"Failed to retrieve primary key '{pk_field_name}' for new record after insert."
                self.log(logging.ERROR, f"{error_msg}")
                raise DatabaseError(error_msg)

        self._is_from_db = True
        self.reset_tracking()
        return result



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
        self.log(logging.INFO, f"Starting update operation for {self.__class__.__name__} record with ID: {getattr(self, self.__class__.primary_key_field(), 'unknown')}")

        # Update existing record with enhanced conditions and expressions
        update_conditions = []
        update_expressions = {}

        # Collect additional conditions and expressions from mixins in MRO
        mro = self.__class__.__mro__
        activerecord_idx = mro.index(IActiveRecord)

        # Log the MRO traversal for debugging
        self.log(logging.DEBUG, f"Traversing MRO for IUpdateBehavior implementations: {[cls.__name__ for cls in mro[:activerecord_idx]]}")

        # Process classes that implement IUpdateBehavior interface and actually define the methods
        for cls in mro[:activerecord_idx]:
            # Check if this class implements the IUpdateBehavior interface
            if issubclass(cls, IUpdateBehavior):
                # Check if this class actually defines the IUpdateBehavior methods in its own __dict__
                # This avoids calling methods from parent classes multiple times
                defines_conditions_method = 'get_update_conditions' in cls.__dict__
                defines_expressions_method = 'get_update_expressions' in cls.__dict__

                # Only call the methods that are actually defined in this class
                if defines_conditions_method or defines_expressions_method:
                    # Log which class is contributing to update behavior
                    self.log(logging.DEBUG, f"Processing IUpdateBehavior from {cls.__name__}")

                    # Get conditions only if this class defines the method
                    if defines_conditions_method:
                        behavior_conditions = cls.get_update_conditions(self)
                        if behavior_conditions:
                            self.log(logging.DEBUG, f"  Adding {len(behavior_conditions)} condition(s) from {cls.__name__}")
                            update_conditions.extend(behavior_conditions)
                        else:
                            self.log(logging.DEBUG, f"  No conditions from {cls.__name__}")

                    # Get expressions only if this class defines the method
                    if defines_expressions_method:
                        behavior_expressions = cls.get_update_expressions(self)
                        if behavior_expressions:
                            self.log(logging.DEBUG, f"  Adding {len(behavior_expressions)} expression(s) from {cls.__name__}: {list(behavior_expressions.keys())}")
                            update_expressions.update(behavior_expressions)
                        else:
                            self.log(logging.DEBUG, f"  No expressions from {cls.__name__}")
                else:
                    # Log when a class implements IUpdateBehavior but doesn't define methods directly
                    self.log(logging.DEBUG, f"Skipping {cls.__name__} (implements IUpdateBehavior but doesn't define methods directly)")

        # Log the final collected results for debugging
        self.log(logging.INFO, f"Update operation: {len(update_conditions)} condition(s), {len(update_expressions)} expression(s) collected from mixins")
        self.log(logging.DEBUG, f"Final update conditions: {len(update_conditions)} total")
        self.log(logging.DEBUG, f"Final update expressions: {list(update_expressions.keys())}")

        # Combine original data with update expressions to form the complete assignments
        # This allows ActiveRecord to provide a unified data dictionary with both regular values and expressions
        complete_data = {**data, **update_expressions}

        self.log(logging.DEBUG, f"Complete data for SET clause: {list(complete_data.keys())}")

        # Map field names to column names for the database operation
        # This is critical for models that use UseColumn annotations
        mapped_data = self.__class__._map_fields_to_columns(complete_data)

        self.log(logging.DEBUG, f"Mapped data for SET clause: {list(mapped_data.keys())}")

        # Create column_mapping for result processing (maps column names back to field names).
        column_mapping = self.__class__.get_column_to_field_map()

        # Get the column adapters for processing output.
        column_adapters = self.get_column_adapters()

        # Get the database backend
        backend = self.backend()

        # Construct the WHERE predicate by combining primary key condition with additional conditions
        pk_name = self.primary_key() # Get primary key name (e.g., 'id')
        pk_value = getattr(self, self.__class__.primary_key_field()) # Get value of primary key field

        self.log(logging.DEBUG, f"Primary key: {pk_name} = {pk_value}")

        # Start with primary key condition
        where_predicate = ComparisonPredicate(
            backend.dialect, '=', Column(backend.dialect, pk_name), Literal(backend.dialect, pk_value)
        )

        # Combine with additional conditions from mixins using AND
        for condition in update_conditions:
            # All conditions should now be SQLPredicate objects
            if hasattr(condition, 'to_sql'):  # If it's a SQLPredicate
                where_predicate = where_predicate & condition
            else:
                # Handle other condition formats if needed
                pass

        self.log(logging.DEBUG, f"Final WHERE clause conditions: {len(update_conditions)} additional condition(s) applied")

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
            data=mapped_data,  # Combined data with both regular values and expressions, mapped to column names
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
    def find_one(
        cls: Type['BaseActiveRecord'],
        condition: Union[
            Any,
            Dict[str, Any],
            Dict['Column', Any],
            'SQLPredicate',
            Tuple[str, tuple]
        ]
    ) -> Optional['BaseActiveRecord']:
        """Find single record by primary key or conditions.

        Args:
            condition: Can be:
                - Scalar value: queries by primary key
                - Dict[str, Any]: queries by column name conditions (keys must be valid schema column names)
                - Dict[Column, Any]: queries by column object conditions (use FieldProxy for type safety)
                - SQLPredicate: direct predicate for query (use FieldProxy for column references)
                - SQLQueryAndParams: pre-built query and parameters

        Returns:
            Optional[BaseActiveRecord]: Returns at most one record even if multiple records
            match the condition, or None if no records match

        Note:
            When using dict for conditions, we do not validate column name or Column object
            against the database schema. Whether using string column names or Column objects
            (from FieldProxy), ensure they correspond to actual schema columns. When using
            FieldProxy, also ensure the columns are from the correct model/table.

        Examples:
            # Query by primary key
            user = User.find_one(1)
            # Query by conditions (column names must match schema)
            user = User.find_one({'status': 1, 'type': 2})
            # Query by column object conditions (using FieldProxy)
            user = User.find_one({User.c.status: 1, User.c.type: 2})
            # Query by SQLPredicate using FieldProxy (recommended for type safety)
            user = User.find_one(User.c.status == 1)
        """
        query = cls.query()

        if isinstance(condition, dict):
            # Convert dictionary conditions to where clauses
            for key, value in condition.items():
                if isinstance(key, Column):
                    # If key is a Column object, use it directly
                    query = query.where(key == value)
                elif isinstance(key, str):
                    # If key is a string, treat it as a column name
                    query = query.where(getattr(cls.c, key) == value)
                else:
                    raise TypeError(f"Invalid key type in condition dictionary: {type(key)}. "
                                    f"Expected str or Column, got {type(key)}")
        elif isinstance(condition, SQLPredicate):
            # Pass SQLPredicate directly to where clause
            query = query.where(condition)
        elif is_sql_query_and_params(condition):
            # Handle SQLQueryAndParams tuple
            sql, params = condition
            query = query.where(sql, params)
        else:
            # Pass scalar primary key condition directly. Type adaptation will be handled by the query builder.
            pk_field_name = cls.primary_key()
            query = query.where(f"{pk_field_name} = ?", (condition,))

        return query.one()

    @classmethod
    def find_all(
        cls: Type['BaseActiveRecord'],
        condition: Optional[Union[
            Any,
            List[Any],
            Dict[str, Any],
            Dict['Column', Any],
            'SQLPredicate',
            Tuple[str, tuple]
        ]] = None
    ) -> List['BaseActiveRecord']:
        """Find multiple records.

        Args:
            condition: Can be:
                - None: returns all records
                - List of primary keys: queries by primary keys
                - Dict[str, Any]: queries by column name conditions (keys must be valid schema column names)
                - Dict[Column, Any]: queries by column object conditions (use FieldProxy for type safety)
                - SQLPredicate: direct predicate for query (use FieldProxy for column references)
                - SQLQueryAndParams: pre-built query and parameters

        Returns:
            List[BaseActiveRecord]: List of found records

        Note:
            When using dict for conditions, we do not validate column name or Column object
            against the database schema. Whether using string column names or Column objects
            (from FieldProxy), ensure they correspond to actual schema columns. When using
            FieldProxy, also ensure the columns are from the correct model/table.

        Examples:
            # Query all records
            users = User.find_all()
            # Query by primary key list
            users = User.find_all([1, 2, 3])
            # Query by conditions (column names must match schema)
            users = User.find_all({'status': 1})
            # Query by column object conditions (using FieldProxy)
            users = User.find_all({User.c.status: 1})
            # Query by SQLPredicate using FieldProxy (recommended for type safety)
            users = User.find_all(User.c.status == 1)
        """
        query = cls.query()
        if condition is None:
            return query.all()

        if isinstance(condition, dict):
            # Convert dictionary conditions to where clauses
            for key, value in condition.items():
                if isinstance(key, Column):
                    # If key is a Column object, use it directly
                    query = query.where(key == value)
                elif isinstance(key, str):
                    # If key is a string, treat it as a column name
                    query = query.where(getattr(cls.c, key) == value)
                else:
                    raise TypeError(f"Invalid key type in condition dictionary: {type(key)}. "
                                    f"Expected str or Column, got {type(key)}")
        elif isinstance(condition, SQLPredicate):
            # Pass SQLPredicate directly to where clause
            query = query.where(condition)
        elif is_sql_query_and_params(condition):
            # Handle SQLQueryAndParams tuple
            sql, params = condition
            query = query.where(sql, params)
        else: # Assumes list of primary keys
            # Pass list of primary keys directly. Type adaptation will be handled by the query builder.
            pk_field_name = cls.primary_key()

            if not condition:
                return []

            placeholders = ','.join(['?' for _ in condition])
            query = query.where(f"{pk_field_name} IN ({placeholders})", condition)

        return query.all()

    @classmethod
    def find_one_or_fail(
        cls: Type['BaseActiveRecord'],
        condition: Union[
            Any,
            Dict[str, Any],
            Dict['Column', Any],
            'SQLPredicate',
            Tuple[str, tuple]
        ]
    ) -> 'BaseActiveRecord':
        """Find single record, raise exception if not found.

        Args:
            condition: Can be:
                - Scalar value: queries by primary key
                - Dict[str, Any]: queries by column name conditions (keys must be valid schema column names)
                - Dict[Column, Any]: queries by column object conditions (use FieldProxy for type safety)
                - SQLPredicate: direct predicate for query (use FieldProxy for column references)
                - SQLQueryAndParams: pre-built query and parameters

        Returns:
            BaseActiveRecord: Found record

        Raises:
            RecordNotFound: When record is not found

        Note:
            When using dict for conditions, we do not validate column name or Column object
            against the database schema. Whether using string column names or Column objects
            (from FieldProxy), ensure they correspond to actual schema columns. When using
            FieldProxy, also ensure the columns are from the correct model/table.

        Examples:
            # Query by primary key
            user = User.find_one_or_fail(1)
            # Query by conditions (column names must match schema)
            user = User.find_one_or_fail({'status': 1, 'type': 2})
            # Query by column object conditions (using FieldProxy)
            user = User.find_one_or_fail({User.c.status: 1, User.c.type: 2})
            # Query by SQLPredicate using FieldProxy (recommended for type safety)
            user = User.find_one_or_fail(User.c.status == 1)
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
    def backend(cls) -> AsyncStorageBackend:
        """
        Get the storage backend instance for this model class.

        This method provides access to the configured storage backend for the model class.
        It implements a lazy loading pattern where the backend is initialized on first
        access if it hasn't been explicitly configured.

        The method follows this resolution order:
        1. Returns the cached __backend__ instance if already initialized
        2. Attempts to create a backend instance if configuration exists but backend isn't initialized
        3. Falls back to an AsyncDummyBackend if no configuration exists

        The AsyncDummyBackend is a special backend implementation that allows SQL generation
        and query building without requiring an active database connection. It's useful
        for testing, schema introspection, and static analysis.

        Args:
            cls: The model class requesting the backend (implicit from @classmethod)

        Returns:
            AsyncStorageBackend: The configured backend instance for this model class.
                           Could be a real async backend (AsyncSQLite, AsyncPostgreSQL, etc.) or
                           an AsyncDummyBackend if no configuration exists.

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
            result = await backend.execute("SELECT * FROM users WHERE id = ?", (1,))
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
                from rhosocial.activerecord.backend.impl.dummy.backend import AsyncDummyBackend # Lazy import for initial backend check
                backend_instance = cls.__backend_class__(connection_config=cls.__connection_config__)
                if hasattr(cls, '__logger__'):
                    backend_instance.logger = cls.__logger__
                cls.__backend__ = backend_instance
                return cls.__backend__
            except Exception as e:
                # If instantiation fails, re-raise as a DatabaseError
                raise DatabaseError(f"Failed to instantiate configured backend: {e}") from e

        # Fallback to AsyncDummyBackend if no real backend is configured
        if not hasattr(cls, '_dummy_backend') or cls._dummy_backend is None:
            from rhosocial.activerecord.backend.impl.dummy.backend import AsyncDummyBackend # Lazy import
            cls._dummy_backend = AsyncDummyBackend()
        return cls._dummy_backend


class AsyncBaseActiveRecord(IAsyncActiveRecord):
    """
    Core Asynchronous ActiveRecord implementation providing the fundamental ORM functionality.

    The AsyncBaseActiveRecord class implements the ActiveRecord pattern in an asynchronous manner,
    where each instance represents a row in the database table. The class provides a comprehensive
    set of features for asynchronous database interaction including CRUD operations, relationship
    management, and event handling.

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
    class User(AsyncBaseActiveRecord):
        __table_name__ = "users"
        __primary_key__ = "id"  # Specify the database column name for the primary key

        id: Optional[int] = Field(default=None)  # Note: pydantic's primary_key=True is deprecated
        username: str
        email: str
        created_at: Optional[datetime] = None

    # Create new record
    user = User(username="john", email="john@example.com")
    await user.save()

    # Query records
    users = await User.where(User.c.username.like("%joh%")).all()

    # Update record
    user.email = "newemail@example.com"
    await user.save()

    # Delete record
    await user.delete()

    # Get primary key column name
    pk_column = User.primary_key()  # Returns "id"
    ```

    Note: Unlike traditional ORMs, this implementation does not rely on pydantic's
    Field(primary_key=True) for primary key detection. Instead, it uses the __primary_key__
    class attribute and the primary_key() method. This allows for more flexibility
    in primary key handling, including dynamic primary keys based on runtime conditions.

    Important: Currently, the implementation supports single-column primary keys only.
    The __primary_key__ attribute should be set to a single column name string.
    Composite primary keys are not supported in the current implementation.
    """

    @classmethod
    def configure(cls, config: ConnectionConfig, backend_class: Type[AsyncStorageBackend]) -> None:
        """
        Configure the storage backend for this model class.

        This method sets up the asynchronous database connection and storage backend for the model class.
        It should be called before performing any database operations with the model.
        The configuration is class-specific, meaning different model classes can use
        different database connections or backend implementations.

        Args:
            config: Connection configuration
            backend_class: The backend implementation class

        Note:
            This method is typically called at the application startup to initialize
            the database connection for the model. It supports different configurations
            for different models, allowing for multi-database architectures.

        Example:
            ```python
            from rhosocial.activerecord.backend.impl.sqlite_async import AsyncSQLiteBackend
            from rhosocial.activerecord.backend.config import ConnectionConfig

            # Configure the User model to use SQLite
            config = ConnectionConfig(database="my_db.sqlite")
            User.configure(config, AsyncSQLiteBackend)
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
            cls._dummy_backend = None

    @classmethod
    def backend(cls) -> AsyncStorageBackend:
        """Get asynchronous storage backend instance."""
        return super().backend()

    @classmethod
    def create_from_database(cls, row: Dict[str, Any]) -> 'AsyncBaseActiveRecord':
        """Create instance from database record"""
        instance = cls(**row)
        instance._is_from_db = True
        instance.reset_tracking()
        return instance

    @classmethod
    def create_collection_from_database(cls, rows: List[Dict[str, Any]]) -> List['AsyncBaseActiveRecord']:
        """Create instance collection from database records"""
        return [cls.create_from_database(row) for row in rows]

    async def _insert_internal(self, data) -> Any:
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
        self.log(logging.DEBUG, f"Raw data for insert: {data}")

        # Translate Python field names to database column names.
        # The backend's execute method will handle parameter type adaptation.
        prepared_data = self.__class__._map_fields_to_columns(data)
        self.log(logging.DEBUG, f"Data with database column names: {prepared_data}")

        self.log(logging.INFO, f"Inserting new {self.__class__.__name__}")

        # Create column_mapping for result processing (maps column names back to field names).
        # This is derived from the model's get_column_to_field_map.
        column_mapping = self.__class__.get_column_to_field_map()
        self.log(logging.DEBUG, f"Column mapping for result processing: {column_mapping}")

        # Get the column adapters for processing output (e.g., RETURNING clauses).
        column_adapters = self.get_column_adapters()
        self.log(logging.DEBUG, f"Column adapters map: {column_adapters}")

        # Call `insert` with an InsertOptions object that includes prepared data, column mapping, column adapters, and returning columns if supported.

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
        result = await self.backend().insert(insert_options)

        # Handle auto-increment primary key if needed.
        pk_column = self.primary_key()
        pk_field_name = self.__class__._get_field_name(pk_column)
        if (result is not None and result.affected_rows > 0 and
                pk_field_name in self.__class__.model_fields and
                prepared_data.get(pk_column) is None and
                getattr(self, pk_field_name, None) is None):

            pk_retrieved = False
            self.log(logging.DEBUG, f"Attempting to retrieve primary key '{pk_column}' for new record")

            # Get the Python field name corresponding to the primary key column
            pk_field_name = self.__class__._get_field_name(pk_column)
            self.log(logging.DEBUG, f"Primary key column '{pk_column}' maps to field '{pk_field_name}'")

            # Priority 1: Check for RETURNING data (e.g., from PostgreSQL)
            if result.data and isinstance(result.data, list) and len(result.data) > 0:
                first_row = result.data[0]
                # Result data will have already been mapped back to field names if column_mapping was used.
                if isinstance(first_row, dict) and pk_field_name in first_row:
                    pk_value = first_row[pk_field_name]
                    setattr(self, pk_field_name, pk_value)
                    pk_retrieved = True
                    self.log(logging.DEBUG, f"Retrieved primary key '{pk_field_name}' from RETURNING clause: {pk_value}")
                else:
                    self.log(logging.WARNING, f"RETURNING clause data found, but primary key field '{pk_field_name}' is missing in the result row: {first_row}")

            # Priority 2: Fallback to last_insert_id (e.g., from MySQL/SQLite)
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
                    self.log(logging.DEBUG, f"Retrieved primary key '{pk_field_name}' from last_insert_id: {pk_value}")

            # If PK still not retrieved, it's an error.
            if not pk_retrieved:
                error_msg = f"Failed to retrieve primary key '{pk_field_name}' for new record after insert."
                self.log(logging.ERROR, f"{error_msg}")
                raise DatabaseError(error_msg)

        self._is_from_db = True
        self.reset_tracking()
        return result

    async def _update_internal(self, data) -> Any:
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
        self.log(logging.INFO, f"Starting update operation for {self.__class__.__name__} record with ID: {getattr(self, self.__class__.primary_key_field(), 'unknown')}")

        # Update existing record with enhanced conditions and expressions
        update_conditions = []
        update_expressions = {}

        # Collect additional conditions and expressions from mixins in MRO
        mro = self.__class__.__mro__
        activerecord_idx = mro.index(IActiveRecord)

        # Log the MRO traversal for debugging
        self.log(logging.DEBUG, f"Traversing MRO for IUpdateBehavior implementations: {[cls.__name__ for cls in mro[:activerecord_idx]]}")

        # Process classes that implement IUpdateBehavior interface and actually define the methods
        for cls in mro[:activerecord_idx]:
            # Check if this class implements the IUpdateBehavior interface
            if issubclass(cls, IUpdateBehavior):
                # Check if this class actually defines the IUpdateBehavior methods in its own __dict__
                # This avoids calling methods from parent classes multiple times
                defines_conditions_method = 'get_update_conditions' in cls.__dict__
                defines_expressions_method = 'get_update_expressions' in cls.__dict__

                # Only call the methods that are actually defined in this class
                if defines_conditions_method or defines_expressions_method:
                    # Log which class is contributing to update behavior
                    self.log(logging.DEBUG, f"Processing IUpdateBehavior from {cls.__name__}")

                    # Get conditions only if this class defines the method
                    if defines_conditions_method:
                        behavior_conditions = cls.get_update_conditions(self)
                        if behavior_conditions:
                            self.log(logging.DEBUG, f"  Adding {len(behavior_conditions)} condition(s) from {cls.__name__}")
                            update_conditions.extend(behavior_conditions)
                        else:
                            self.log(logging.DEBUG, f"  No conditions from {cls.__name__}")

                    # Get expressions only if this class defines the method
                    if defines_expressions_method:
                        behavior_expressions = cls.get_update_expressions(self)
                        if behavior_expressions:
                            self.log(logging.DEBUG, f"  Adding {len(behavior_expressions)} expression(s) from {cls.__name__}: {list(behavior_expressions.keys())}")
                            update_expressions.update(behavior_expressions)
                        else:
                            self.log(logging.DEBUG, f"  No expressions from {cls.__name__}")
                else:
                    # Log when a class implements IUpdateBehavior but doesn't define methods directly
                    self.log(logging.DEBUG, f"Skipping {cls.__name__} (implements IUpdateBehavior but doesn't define methods directly)")

        # Log the final collected results for debugging
        self.log(logging.INFO, f"Update operation: {len(update_conditions)} condition(s), {len(update_expressions)} expression(s) collected from mixins")
        self.log(logging.DEBUG, f"Final update conditions: {len(update_conditions)} total")
        self.log(logging.DEBUG, f"Final update expressions: {list(update_expressions.keys())}")

        # Combine original data with update expressions to form the complete assignments
        # This allows ActiveRecord to provide a unified data dictionary with both regular values and expressions
        complete_data = {**data, **update_expressions}

        self.log(logging.DEBUG, f"Complete data for SET clause: {list(complete_data.keys())}")

        # Map field names to column names for the database operation
        # This is critical for models that use UseColumn annotations
        mapped_data = self.__class__._map_fields_to_columns(complete_data)

        self.log(logging.DEBUG, f"Mapped data for SET clause: {list(mapped_data.keys())}")

        # Create column_mapping for result processing (maps column names back to field names).
        column_mapping = self.__class__.get_column_to_field_map()

        # Get the column adapters for processing output.
        column_adapters = self.get_column_adapters()

        # Get the database backend
        backend = self.backend()

        # Construct the WHERE predicate by combining primary key condition with additional conditions
        pk_name = self.primary_key() # Get primary key name (e.g., 'id')
        pk_value = getattr(self, self.__class__.primary_key_field()) # Get value of primary key field

        self.log(logging.DEBUG, f"Primary key: {pk_name} = {pk_value}")

        # Start with primary key condition
        where_predicate = ComparisonPredicate(
            backend.dialect, '=', Column(backend.dialect, pk_name), Literal(backend.dialect, pk_value)
        )

        # Combine with additional conditions from mixins using AND
        for condition in update_conditions:
            # All conditions should now be SQLPredicate objects
            if hasattr(condition, 'to_sql'):  # If it's a SQLPredicate
                where_predicate = where_predicate & condition
            else:
                # Handle other condition formats if needed
                pass

        self.log(logging.DEBUG, f"Final WHERE clause conditions: {len(update_conditions)} additional condition(s) applied")

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
            data=mapped_data,  # Combined data with both regular values and expressions, mapped to column names
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
            if hasattr(base, 'prepare_save_data') and base != AsyncBaseActiveRecord:
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
            if hasattr(base, 'after_save') and base != AsyncBaseActiveRecord:
                after_method = getattr(base, 'after_save')
                after_method(self, is_new)

    async def _save_internal(self) -> int:
        """Internal save implementation.

        Handles the actual database persistence logic.
        Determines whether to insert or update based on is_new_record.
        """
        data = self._prepare_save_data()

        if self.is_new_record:
            result = await self._insert_internal(data)
        else:
            if not self.is_dirty:
                return 0
            result = await self._update_internal(data)

        self._after_save(self.is_new_record)

        return result.affected_rows

    @classmethod
    async def find_one(
        cls: Type['AsyncBaseActiveRecord'],
        condition: Union[
            Any,
            Dict[str, Any],
            Dict['Column', Any],
            'SQLPredicate',
            Tuple[str, tuple]
        ]
    ) -> Optional['AsyncBaseActiveRecord']:
        """Find single record by primary key or conditions.

        Args:
            condition: Can be:
                - Scalar value: queries by primary key
                - Dict[str, Any]: queries by column name conditions (keys must be valid schema column names)
                - Dict[Column, Any]: queries by column object conditions (use FieldProxy for type safety)
                - SQLPredicate: direct predicate for query (use FieldProxy for column references)
                - SQLQueryAndParams: pre-built query and parameters

        Returns:
            Optional[AsyncBaseActiveRecord]: Returns at most one record even if multiple records
            match the condition, or None if no records match

        Note:
            When using dict for conditions, we do not validate column name or Column object
            against the database schema. Whether using string column names or Column objects
            (from FieldProxy), ensure they correspond to actual schema columns. When using
            FieldProxy, also ensure the columns are from the correct model/table.

        Examples:
            # Query by primary key
            user = await User.find_one(1)
            # Query by conditions (column names must match schema)
            user = await User.find_one({'status': 1, 'type': 2})
            # Query by column object conditions (using FieldProxy)
            user = await User.find_one({User.c.status: 1, User.c.type: 2})
            # Query by SQLPredicate using FieldProxy (recommended for type safety)
            user = await User.find_one(User.c.status == 1)
        """
        query = cls.query()

        if isinstance(condition, dict):
            # Convert dictionary conditions to where clauses
            for key, value in condition.items():
                if isinstance(key, Column):
                    # If key is a Column object, use it directly
                    query = query.where(key == value)
                elif isinstance(key, str):
                    # If key is a string, treat it as a column name
                    query = query.where(getattr(cls.c, key) == value)
                else:
                    raise TypeError(f"Invalid key type in condition dictionary: {type(key)}. "
                                    f"Expected str or Column, got {type(key)}")
        elif isinstance(condition, SQLPredicate):
            # Pass SQLPredicate directly to where clause
            query = query.where(condition)
        elif is_sql_query_and_params(condition):
            # Handle SQLQueryAndParams tuple
            sql, params = condition
            query = query.where(sql, params)
        else:
            # Pass scalar primary key condition directly. Type adaptation will be handled by the query builder.
            pk_field_name = cls.primary_key()
            query = query.where(f"{pk_field_name} = ?", (condition,))

        return await query.one()

    @classmethod
    async def find_all(
        cls: Type['AsyncBaseActiveRecord'],
        condition: Optional[Union[
            Any,
            List[Any],
            Dict[str, Any],
            Dict['Column', Any],
            'SQLPredicate',
            Tuple[str, tuple]
        ]] = None
    ) -> List['AsyncBaseActiveRecord']:
        """Find multiple records.

        Args:
            condition: Can be:
                - None: returns all records
                - List of primary keys: queries by primary keys
                - Dict[str, Any]: queries by column name conditions (keys must be valid schema column names)
                - Dict[Column, Any]: queries by column object conditions (use FieldProxy for type safety)
                - SQLPredicate: direct predicate for query (use FieldProxy for column references)
                - SQLQueryAndParams: pre-built query and parameters

        Returns:
            List[AsyncBaseActiveRecord]: List of found records

        Note:
            When using dict for conditions, we do not validate column name or Column object
            against the database schema. Whether using string column names or Column objects
            (from FieldProxy), ensure they correspond to actual schema columns. When using
            FieldProxy, also ensure the columns are from the correct model/table.

        Examples:
            # Query all records
            users = await User.find_all()
            # Query by primary key list
            users = await User.find_all([1, 2, 3])
            # Query by conditions (column names must match schema)
            users = await User.find_all({'status': 1})
            # Query by column object conditions (using FieldProxy)
            users = await User.find_all({User.c.status: 1})
            # Query by SQLPredicate using FieldProxy (recommended for type safety)
            users = await User.find_all(User.c.status == 1)
        """
        query = cls.query()
        if condition is None:
            return await query.all()

        if isinstance(condition, dict):
            # Convert dictionary conditions to where clauses
            for key, value in condition.items():
                if isinstance(key, Column):
                    # If key is a Column object, use it directly
                    query = query.where(key == value)
                elif isinstance(key, str):
                    # If key is a string, treat it as a column name
                    query = query.where(getattr(cls.c, key) == value)
                else:
                    raise TypeError(f"Invalid key type in condition dictionary: {type(key)}. "
                                    f"Expected str or Column, got {type(key)}")
        elif isinstance(condition, SQLPredicate):
            # Pass SQLPredicate directly to where clause
            query = query.where(condition)
        elif is_sql_query_and_params(condition):
            # Handle SQLQueryAndParams tuple
            sql, params = condition
            query = query.where(sql, params)
        else: # Assumes list of primary keys
            # Pass list of primary keys directly. Type adaptation will be handled by the query builder.
            pk_field_name = cls.primary_key()

            if not condition:
                return []

            placeholders = ','.join(['?' for _ in condition])
            query = query.where(f"{pk_field_name} IN ({placeholders})", condition)

        return await query.all()

    @classmethod
    async def find_one_or_fail(
        cls: Type['AsyncBaseActiveRecord'],
        condition: Union[
            Any,
            Dict[str, Any],
            Dict['Column', Any],
            'SQLPredicate',
            Tuple[str, tuple]
        ]
    ) -> 'AsyncBaseActiveRecord':
        """Find single record, raise exception if not found.

        Args:
            condition: Can be:
                - Scalar value: queries by primary key
                - Dict[str, Any]: queries by column name conditions (keys must be valid schema column names)
                - Dict[Column, Any]: queries by column object conditions (use FieldProxy for type safety)
                - SQLPredicate: direct predicate for query (use FieldProxy for column references)
                - SQLQueryAndParams: pre-built query and parameters

        Returns:
            AsyncBaseActiveRecord: Found record

        Raises:
            RecordNotFound: When record is not found

        Note:
            When using dict for conditions, we do not validate column name or Column object
            against the database schema. Whether using string column names or Column objects
            (from FieldProxy), ensure they correspond to actual schema columns. When using
            FieldProxy, also ensure the columns are from the correct model/table.

        Examples:
            # Query by primary key
            user = await User.find_one_or_fail(1)
            # Query by conditions (column names must match schema)
            user = await User.find_one_or_fail({'status': 1, 'type': 2})
            # Query by column object conditions (using FieldProxy)
            user = await User.find_one_or_fail({User.c.status: 1, User.c.type: 2})
            # Query by SQLPredicate using FieldProxy (recommended for type safety)
            user = await User.find_one_or_fail(User.c.status == 1)
        """
        record = await cls.find_one(condition)
        if record is None:
            cls.log(
                logging.WARNING,
                f"Record not found for {cls.__name__} with find_one condition: {condition}"
            )
            raise RecordNotFound(f"Record not found for {cls.__name__}")
        return record

    async def save(self) -> int:
        """
        Save the current instance to the database asynchronously, either inserting or updating.

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
            await user.save()  # Performs INSERT

            # Update existing record
            user.email = "newemail@example.com"
            await user.save()  # Performs UPDATE with only the changed field
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
            return await self._save_internal()
        except Exception as e:
            self.log(logging.ERROR, f"Database error: {str(e)}")
            raise DatabaseError(str(e)) from e

    async def delete(self) -> int:
        """
        Delete the record from the database asynchronously.

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
            result = await backend.update(update_opts)
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
    def backend(cls) -> AsyncStorageBackend:
        """
        Get the storage backend instance for this model class.

        This method provides access to the configured storage backend for the model class.
        It implements a lazy loading pattern where the backend is initialized on first
        access if it hasn't been explicitly configured.

        The method follows this resolution order:
        1. Returns the cached __backend__ instance if already initialized
        2. Attempts to create a backend instance if configuration exists but backend isn't initialized
        3. Falls back to an AsyncDummyBackend if no configuration exists

        The AsyncDummyBackend is a special backend implementation that allows SQL generation
        and query building without requiring an active database connection. It's useful
        for testing, schema introspection, and static analysis.

        Args:
            cls: The model class requesting the backend (implicit from @classmethod)

        Returns:
            AsyncStorageBackend: The configured backend instance for this model class.
                           Could be a real async backend (AsyncSQLite, AsyncPostgreSQL, etc.) or
                           an AsyncDummyBackend if no configuration exists.

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
            result = await backend.execute("SELECT * FROM users WHERE id = ?", (1,))
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
                from rhosocial.activerecord.backend.impl.dummy.backend import AsyncDummyBackend # Lazy import for initial backend check
                backend_instance = cls.__backend_class__(connection_config=cls.__connection_config__)
                if hasattr(cls, '__logger__'):
                    backend_instance.logger = cls.__logger__
                cls.__backend__ = backend_instance
                return cls.__backend__
            except Exception as e:
                # If instantiation fails, re-raise as a DatabaseError
                raise DatabaseError(f"Failed to instantiate configured backend: {e}") from e

        # Fallback to AsyncDummyBackend if no real backend is configured
        if not hasattr(cls, '_dummy_backend') or cls._dummy_backend is None:
            from rhosocial.activerecord.backend.impl.dummy.backend import AsyncDummyBackend # Lazy import
            cls._dummy_backend = AsyncDummyBackend()
        return cls._dummy_backend

