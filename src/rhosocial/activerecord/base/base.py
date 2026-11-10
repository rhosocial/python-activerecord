# src/rhosocial/activerecord/base/base.py
"""Core BaseActiveRecord implementation."""

import logging
import inspect
from collections.abc import Mapping as MappingABC
from pydantic.fields import FieldInfo
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Mapping,
    Optional,
    Type,
    Union,
    get_origin,
    get_args,
    Tuple,
)

from ..backend.base import StorageBackend, AsyncStorageBackend
from ..backend.config import ConnectionConfig
from ..backend.errors import (
    DatabaseError,
    IntegrityError,
    RecordNotFound,
    UnaddressableRecordError,
    ValidationError as DBValidationError,
)
from ..backend.expression import (
    Column,
    ColumnBase,
    ComparisonPredicate,
    InPredicate,
    Literal,
    SQLPredicate,
)
from ..backend.expression.bases import QueryWithParams
from ..backend.options import DeleteOptions, UpdateOptions
from ..backend.options import InsertOptions, LogContext
from ..backend.type_adapter import SQLTypeAdapter
from ..interface import IActiveRecord, IAsyncActiveRecord, ModelEvent
from ..interface.update import IDataPreparationBehavior, IDeleteBehavior, IUpdateBehavior
from ..logging import LoggingConfig, LoggingMixin
from .bulk_operations import BulkOperationsMixin, AsyncBulkOperationsMixin


class BaseActiveRecord(BulkOperationsMixin, LoggingMixin, IActiveRecord):
    """
    Core ActiveRecord implementation providing the fundamental ORM functionality.
    """

    @classmethod
    def configure(
        cls,
        config: Union[ConnectionConfig, Callable[..., ConnectionConfig]],
        backend_class: Type[StorageBackend],
        *,
        logging_config: Optional[LoggingConfig] = None,
    ) -> None:
        """Configure the model with a database backend.

        Args:
            config: A ConnectionConfig instance, or a callable that returns one.
                When a callable is provided (e.g., a named connection function),
                it is invoked automatically to obtain the ConnectionConfig.
                Use functools.partial or lambda to pass parameters to the callable.
            backend_class: The StorageBackend subclass to use.
            logging_config: Optional class-level logging configuration.

        Example:
            # With ConnectionConfig instance
            User.configure(SQLiteConnectionConfig(database=":memory:"), SQLiteBackend)

            # With callable (named connection function)
            from myapp.connections import prod_db
            User.configure(prod_db, MySQLBackend)

            # With partial for parameters
            from functools import partial
            User.configure(partial(prod_db, pool_size=20), MySQLBackend)
        """
        if callable(config) and not isinstance(config, ConnectionConfig):
            config = config()

        if not isinstance(config, ConnectionConfig):
            raise DatabaseError(f"Invalid connection config for {cls.__name__}")

        cls.__connection_config__ = config
        cls.__backend_class__ = backend_class
        if logging_config is not None:
            cls.__logging_config__ = logging_config

        backend_instance = backend_class(connection_config=config, logging_config=logging_config)
        backend_instance.logger = cls.get_logger()

        cls.__backend__ = backend_instance
        if hasattr(cls, "_dummy_backend") and cls._dummy_backend is not None:
            cls._dummy_backend = None

        backend_instance.introspect_and_adapt()

    @classmethod
    def backend(cls) -> StorageBackend:
        """Get storage backend instance with context awareness.

        Returns the appropriate backend:
        1. Sync context backend (transaction/connection) if available
        2. Class-level backend as fallback
        """
        from ..connection.pool import get_current_backend

        # Sync context takes priority
        context_backend = get_current_backend()
        if context_backend is not None:
            return context_backend

        # Fallback to parent implementation
        return super().backend()

    @classmethod
    def create_from_database(cls, row: Dict[str, Any]) -> "BaseActiveRecord":
        derived_fields = getattr(cls, "__derived_fields__", {})
        if derived_fields:
            model_data = {k: v for k, v in row.items() if k in cls.model_fields}
            extra_data = {k: v for k, v in row.items() if k not in cls.model_fields}
        else:
            model_data = row
            extra_data = {}

        instance = cls(**model_data)
        instance._is_from_db = True
        instance.reset_tracking()

        if derived_fields:
            col_to_field = {df.column_name: name for name, df in derived_fields.items() if df.column_name is not None}
            for name in derived_fields:
                instance.__dict__[name] = None
            for k, v in extra_data.items():
                field_name = col_to_field.get(k, k)
                df = derived_fields.get(field_name)
                if df is not None and df.adapter is not None:
                    v = df.adapter.from_database(v, df.python_type)
                instance.__dict__[field_name] = v

        return instance

    @classmethod
    def create_collection_from_database(cls, rows: List[Dict[str, Any]]) -> List["BaseActiveRecord"]:
        return [cls.create_from_database(row) for row in rows]

    def _get_pk_value(self) -> Any:
        """Extract primary key value from the current instance.

        Single-column PK returns a scalar value.
        Composite PK returns a dict {column_name: value, ...}.

        Raises:
            UnaddressableRecordError: If the model declares no primary key, so
                there is no identity to read.
        """
        cls = self.__class__
        if not cls.addressable():
            raise UnaddressableRecordError(cls.__name__, "Reading the primary key value")
        cols = cls.primary_key_columns()
        fields = cls.primary_key_fields()
        if not cls.is_composite_pk():
            return getattr(self, fields[0])
        return {col: getattr(self, field) for col, field in zip(cols, fields)}

    @classmethod
    def _build_pk_where_predicate(cls, pk_value: Any) -> "SQLPredicate":
        """Build a WHERE predicate for primary key lookup.

        Single-column PK: pk_value is scalar, generates "col = value"
        Composite PK: pk_value must be dict, generates "col1 = v1 AND col2 = v2"

        The dict keys may be column names or Python field names — field names are
        transparently mapped to column names when a direct column-name lookup fails.

        Raises:
            UnaddressableRecordError: If the model declares no primary key, so
                there is no column to match on.
        """
        if not cls.addressable():
            raise UnaddressableRecordError(cls.__name__, "Building a primary key predicate")
        dialect = cls.backend().dialect
        columns = cls.primary_key_columns()

        if not cls.is_composite_pk():
            return ComparisonPredicate(dialect, "=", Column(dialect, columns[0]), Literal(dialect, pk_value))

        if not isinstance(pk_value, dict):
            raise TypeError(
                f"{cls.__name__} has composite primary key {columns}, "
                f"pk_value must be a dict, got {type(pk_value).__name__}"
            )
        predicates = []
        for col in columns:
            val = pk_value.get(col)
            if val is None and col not in pk_value:
                field_name = cls._get_field_name(col)
                val = pk_value.get(field_name)
            if val is None:
                raise ValueError(f"Primary key column '{col}' has value None")
            predicates.append(
                ComparisonPredicate(dialect, "=", Column(dialect, col), Literal(dialect, val))
            )
        result = predicates[0]
        for p in predicates[1:]:
            result = result & p
        return result

    def _insert_internal(self, data) -> Any:
        """
        Internal method to perform the actual insertion of data into the database.

        This method handles the complete insertion process including:
        1. Preparing data with column mappings and adapters
        2. Creating insert options with appropriate configurations
        3. Executing the insert operation via the backend
        4. Processing the result, including retrieving primary key if needed
        5. Updating the instance with the retrieved primary key value
        6. Marking the instance as loaded from the database and resetting tracking

        Args:
            data: Dictionary containing the field names and values to insert

        Returns:
            The result object from the backend insert operation

        Raises:
            DatabaseError: If there's an issue retrieving the primary key after insert
            ValidationError: If a required primary key field has no value
            ReadOnlyError: If the model is read-only
        """
        self.refuse_read_only("insert")
        self.__class__._missing_key_fields_on_insert(self)
        self.log_data(logging.DEBUG, "Raw data for insert", data)
        prepared_data = self.__class__._map_fields_to_columns(data)
        generated = self.__class__.get_generated_columns()
        if generated:
            prepared_data = {
                k: v for k, v in prepared_data.items() if k not in generated
            }
        self.log_data(logging.DEBUG, "Data with database column names", prepared_data)
        self.log(logging.DEBUG, f"Inserting new {self.__class__.__name__}")
        column_mapping = self.__class__.get_column_to_field_map()
        self.log(logging.DEBUG, f"Column mapping for result processing: {column_mapping}")
        column_adapters = self.get_column_adapters()
        self.log(logging.DEBUG, f"Column adapters map: {column_adapters}")
        supports_returning = self.backend().dialect.supports_returning_insert()
        returning_columns = None
        if supports_returning:
            returning_columns = list(self.primary_key_columns())

        insert_options = InsertOptions(
            table=self.table_name(),
            schema_name=self.schema_name(),
            data=prepared_data,
            column_mapping=column_mapping,
            column_adapters=column_adapters,
            primary_key=self.primary_key(),
            returning_columns=returning_columns,
            log_context=LogContext(
                model=self.__class__,
                operation="insert",
                object_name=self.table_name(),
                schema=self.schema_name(),
            ),
        )
        result = self.backend().insert(insert_options)
        # A keyless model has nothing for the database to generate, so there is
        # nothing to read back either. Without the addressable() guard the loop
        # below iterates an empty column list and indexes it.
        if self.__class__.__pk_auto_generated__ and self.__class__.addressable():
            pk_columns = self.primary_key_columns()
            pk_retrieved = False
            for col in pk_columns:
                field = self.__class__._get_field_name(col)
                if (
                    field in self.__class__.model_fields
                    and prepared_data.get(col) is None
                    and getattr(self, field, None) is None
                ):
                    retrieved_val = None
                    if result.data and isinstance(result.data, list) and len(result.data) > 0:
                        first_row = result.data[0]
                        if isinstance(first_row, dict) and field in first_row:
                            retrieved_val = first_row[field]
                        elif isinstance(first_row, dict) and col in first_row:
                            retrieved_val = first_row[col]
                    if retrieved_val is None and col == pk_columns[0] and result.last_insert_id is not None:
                        import types
                        field_type = self.__class__.model_fields[field].annotation
                        origin = get_origin(field_type)
                        if origin in (Union, Optional) or origin is types.UnionType:
                            type_args = [t for t in get_args(field_type) if t is not type(None)]
                            if type_args:
                                field_type = type_args[0]
                        if field_type is int:
                            retrieved_val = result.last_insert_id
                    if retrieved_val is not None:
                        setattr(self, field, retrieved_val)
                        pk_retrieved = True
                elif (
                    field in self.__class__.model_fields
                    and getattr(self, field, None) is not None
                ):
                    pk_retrieved = True
            if not pk_retrieved and not self.__class__.is_composite_pk():
                pk_column = pk_columns[0]
                pk_field_name = self.__class__._get_field_name(pk_column)
                error_msg = f"Failed to retrieve primary key '{pk_field_name}' for new record after insert."
                self.log(logging.ERROR, f"{error_msg}")
                raise DatabaseError(error_msg)

        self._is_from_db = True
        self.reset_tracking()
        return result

    def _update_internal(self, data) -> Any:
        """
        Internal method to perform the actual update of data in the database.

        This method handles the complete update process including:
        1. Collecting update conditions and expressions from IUpdateBehavior implementations
        2. Preparing data with column mappings and adapters
        3. Creating update options with appropriate configurations
        4. Executing the update operation via the backend
        5. Returning the result of the update operation

        Args:
            data: Dictionary containing the field names and values to update

        Returns:
            The result object from the backend update operation

        Raises:
            ReadOnlyError: If the model is read-only
        """
        self.refuse_read_only("update")
        self.log(
            logging.DEBUG,
            f"Starting update operation for {self.__class__.__name__} record: "
            f"{self._get_pk_value()}",
        )
        update_conditions = []
        update_expressions = {}
        mro = self.__class__.__mro__
        activerecord_idx = mro.index(IActiveRecord)
        self.log(
            logging.DEBUG,
            f"Traversing MRO for IUpdateBehavior implementations: {[cls.__name__ for cls in mro[:activerecord_idx]]}",
        )
        for cls in mro[:activerecord_idx]:
            if issubclass(cls, IUpdateBehavior):
                defines_conditions_method = "get_update_conditions" in cls.__dict__
                defines_expressions_method = "get_update_expressions" in cls.__dict__
                if defines_conditions_method or defines_expressions_method:
                    self.log(logging.DEBUG, f"Processing IUpdateBehavior from {cls.__name__}")
                    if defines_conditions_method:
                        behavior_conditions = cls.get_update_conditions(self)
                        if behavior_conditions:
                            self.log(
                                logging.DEBUG, f"  Adding {len(behavior_conditions)} condition(s) from {cls.__name__}"
                            )
                            update_conditions.extend(behavior_conditions)
                        else:
                            self.log(logging.DEBUG, f"  No conditions from {cls.__name__}")
                    if defines_expressions_method:
                        behavior_expressions = cls.get_update_expressions(self)
                        if behavior_expressions:
                            self.log(
                                logging.DEBUG,
                                f"  Adding {len(behavior_expressions)} expression(s) from {cls.__name__}: "
                                f"{list(behavior_expressions.keys())}",
                            )
                            update_expressions.update(behavior_expressions)
                        else:
                            self.log(logging.DEBUG, f"  No expressions from {cls.__name__}")
                else:
                    self.log(
                        logging.DEBUG,
                        f"Skipping {cls.__name__} (implements IUpdateBehavior but doesn't define methods directly)",
                    )
        self.log(
            logging.DEBUG,
            f"Update operation: {len(update_conditions)} condition(s), "
            f"{len(update_expressions)} expression(s) collected from mixins",
        )
        self.log(logging.DEBUG, f"Final update conditions: {len(update_conditions)} total")
        self.log(logging.DEBUG, f"Final update expressions: {list(update_expressions.keys())}")
        complete_data = {**data, **update_expressions}
        self.log(logging.DEBUG, f"Complete data for SET clause: {list(complete_data.keys())}")
        mapped_data = self.__class__._map_fields_to_columns(complete_data)
        self.log(logging.DEBUG, f"Mapped data for SET clause: {list(mapped_data.keys())}")
        column_mapping = self.__class__.get_column_to_field_map()
        column_adapters = self.get_column_adapters()
        backend = self.backend()
        pk_value = self._get_pk_value()
        self.log(logging.DEBUG, f"Primary key value: {pk_value}")
        where_predicate = self._build_pk_where_predicate(pk_value)
        for condition in update_conditions:
            if isinstance(condition, SQLPredicate):
                where_predicate = where_predicate & condition
            else:
                self.log(
                    logging.WARNING,
                    f"Skipping non-predicate condition in update: {condition} (type: {type(condition)})",
                )
        self.log(
            logging.DEBUG, f"Final WHERE clause conditions: {len(update_conditions)} additional condition(s) applied"
        )
        supports_returning = backend.dialect.supports_returning_update()
        returning_columns = None
        if supports_returning:
            returning_columns = list(self.primary_key_columns())
        update_options = UpdateOptions(
            table=self.table_name(),
            schema_name=self.schema_name(),
            data=mapped_data,
            where=where_predicate,
            column_mapping=column_mapping,
            column_adapters=column_adapters,
            returning_columns=returning_columns,
            primary_key=self.primary_key(),
            log_context=LogContext(
                model=self.__class__,
                operation="update",
                object_name=self.table_name(),
                schema=self.schema_name(),
            ),
        )
        self.log(
            logging.DEBUG,
            f"Executing update operation on table '{self.table_name()}' with {len(data)} field(s) to update",
        )
        result = backend.update(update_options)
        return result

    def _prepare_save_data(self) -> Dict[str, Any]:
        is_new = self.is_new_record
        pk_fields = set(self.__class__.primary_key_fields())
        generated = set(self.__class__.get_generated_columns())
        if is_new:
            data = self.model_dump(exclude=self.__class__._insert_pk_exclusions())
        else:
            all_data = self.model_dump()
            data = {field: all_data[field] for field in self._dirty_fields if field not in pk_fields}
        # Generated columns are database-computed: never insert/update them.
        if generated:
            data = {k: v for k, v in data.items() if k not in generated}
        bases = self.__class__.__mro__
        for base in bases:
            if issubclass(base, IDataPreparationBehavior) and base not in (
                IDataPreparationBehavior, BaseActiveRecord
            ):
                prepare_method = base.prepare_save_data
                data = prepare_method(self, data, is_new)
        return data

    def _after_save(self, is_new: bool) -> None:
        bases = self.__class__.__mro__
        for base in bases:
            if hasattr(base, "after_save") and base != BaseActiveRecord:
                after_method = base.after_save
                after_method(self, is_new)

    @classmethod
    def find_one(
        cls: Type["BaseActiveRecord"],
        condition: Union[Any, Dict[str, Any], Dict["ColumnBase", Any], "SQLPredicate", Tuple[str, tuple]],
        *,
        derived: Union[bool, str, list, dict] = False,
        extra_derived: Optional[Dict[str, Any]] = None,
    ) -> Optional["BaseActiveRecord"]:
        query = cls.query()
        if isinstance(condition, SQLPredicate):
            query = query.where(condition)
        elif isinstance(condition, dict):
            if cls.is_composite_pk():
                query = query.where(cls._build_pk_where_predicate(condition))
            else:
                for key, value in condition.items():
                    if isinstance(key, ColumnBase):
                        # An explicit node, not the column's own operator: the
                        # key may be a bare Column reference (whose class offers
                        # no operations by design) and the query must not care.
                        query = query.where(
                            ComparisonPredicate(key.dialect, "=", key, Literal(key.dialect, value))
                        )
                    elif isinstance(key, str):
                        column = getattr(cls.c, key)
                        query = query.where(
                            ComparisonPredicate(column.dialect, "=", column, Literal(column.dialect, value))
                        )
                    else:
                        raise TypeError(
                            f"Invalid key type in condition dictionary: {type(key)}. "
                            f"Expected str or Column, got {type(key)}"
                        )
        elif isinstance(condition, tuple) and cls.is_composite_pk():
            cols = cls.primary_key_columns()
            if len(condition) != len(cols):
                raise ValueError(f"Expected {len(cols)} pk values, got {len(condition)}")
            pk_dict = dict(zip(cols, condition))
            query = query.where(cls._build_pk_where_predicate(pk_dict))
        elif QueryWithParams.holds(condition):
            sql, params = condition
            query = query.where(sql, params)
        elif not cls.is_composite_pk():
            if not cls.addressable():
                raise UnaddressableRecordError(cls.__name__, "find_one")
            pk_field_name = cls.primary_key()
            dialect = cls.backend().dialect
            pk_column = Column(dialect, pk_field_name)
            query = query.where(
                ComparisonPredicate(dialect, "=", pk_column, Literal(dialect, condition))
            )
        else:
            raise TypeError(
                f"{cls.__name__} has composite primary key; "
                "pass a dict or tuple as condition"
            )
        cls._apply_derived_to_query(query, derived, extra_derived)
        return query.one()

    @classmethod
    def find_all(
        cls: Type["BaseActiveRecord"],
        condition: Optional[
            Union[Any, List[Any], Dict[str, Any], Dict["ColumnBase", Any], "SQLPredicate", Tuple[str, tuple]]
        ] = None,
        *,
        derived: Union[bool, str, list, dict] = False,
        extra_derived: Optional[Dict[str, Any]] = None,
    ) -> List["BaseActiveRecord"]:
        query = cls.query()
        if condition is None:
            cls._apply_derived_to_query(query, derived, extra_derived)
            return query.all()
        if isinstance(condition, SQLPredicate):
            query = query.where(condition)
        elif isinstance(condition, dict):
            if cls.is_composite_pk():
                query = query.where(cls._build_pk_where_predicate(condition))
            else:
                for key, value in condition.items():
                    if isinstance(key, ColumnBase):
                        # An explicit node, not the column's own operator: the
                        # key may be a bare Column reference (whose class offers
                        # no operations by design) and the query must not care.
                        query = query.where(
                            ComparisonPredicate(key.dialect, "=", key, Literal(key.dialect, value))
                        )
                    elif isinstance(key, str):
                        column = getattr(cls.c, key)
                        query = query.where(
                            ComparisonPredicate(column.dialect, "=", column, Literal(column.dialect, value))
                        )
                    else:
                        raise TypeError(
                            f"Invalid key type in condition dictionary: {type(key)}. "
                            f"Expected str or Column, got {type(key)}"
                        )
        elif isinstance(condition, list):
            if not condition:
                return []
            if cls.is_composite_pk():
                cols = cls.primary_key_columns()
                predicates = []
                for item in condition:
                    if isinstance(item, tuple):
                        pk_dict = dict(zip(cols, item))
                    elif isinstance(item, dict):
                        pk_dict = item
                    else:
                        raise TypeError("Composite PK list items must be dict or tuple")
                    predicates.append(cls._build_pk_where_predicate(pk_dict))
                combined = predicates[0]
                for p in predicates[1:]:
                    combined = combined | p
                query = query.where(combined)
            else:
                if not cls.addressable():
                    raise UnaddressableRecordError(cls.__name__, "find_all")
                pk_field_name = cls.primary_key()
                dialect = cls.backend().dialect
                query = query.where(
                    InPredicate(dialect, Column(dialect, pk_field_name), Literal(dialect, tuple(condition)))
                )
        elif QueryWithParams.holds(condition):
            sql, params = condition
            query = query.where(sql, params)
        else:  # Assumes list of primary keys (backward compat)
            if not cls.addressable():
                raise UnaddressableRecordError(cls.__name__, "find_all")
            pk_field_name = cls.primary_key()
            if not condition:
                return []
            dialect = cls.backend().dialect
            query = query.where(
                InPredicate(dialect, Column(dialect, pk_field_name), Literal(dialect, tuple(condition)))
            )
        cls._apply_derived_to_query(query, derived, extra_derived)
        return query.all()

    @classmethod
    def find_one_or_fail(
        cls: Type["BaseActiveRecord"],
        condition: Union[Any, Dict[str, Any], Dict["ColumnBase", Any], "SQLPredicate", Tuple[str, tuple]],
        *,
        derived: Union[bool, str, list, dict] = False,
        extra_derived: Optional[Dict[str, Any]] = None,
    ) -> "BaseActiveRecord":
        record = cls.find_one(condition, derived=derived, extra_derived=extra_derived)
        if record is None:
            cls.log(logging.DEBUG, f"Record not found for {cls.__name__} with find_one condition: {condition}")
            raise RecordNotFound(f"Record not found for {cls.__name__}")
        return record

    @classmethod
    def _check_lookup_value(cls, field: str, value: Any) -> None:
        """Reject lookup values that cannot be compared by equality."""
        if value is None:
            raise ValueError(
                f"lookup value for {field!r} is None; an equality lookup needs a concrete value"
            )
        if isinstance(value, (ColumnBase, SQLPredicate)) or QueryWithParams.holds(value):
            raise TypeError(
                f"lookup value for {field!r} is an expression; find_one_or_create only supports "
                "plain equality values"
            )

    @classmethod
    def _prepare_find_or_create_inputs(
        cls,
        lookup: Dict[str, Any],
        defaults: Optional[Mapping[str, Any]],
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Validate ``lookup`` / ``defaults`` and return the create values.

        ``lookup`` is the natural key and must name at least one model field.
        ``defaults`` fill the remaining fields on creation only, so ``lookup``
        wins when both name the same field.

        Raises:
            ValueError: The lookup is empty; a lookup value is ``None``; or
                ``lookup`` / ``defaults`` name a database-generated primary
                key field.
            TypeError: A key is not a model field, a value is an expression, or
                ``defaults`` is neither a mapping nor ``None``.
        """
        if not lookup:
            raise ValueError(
                f"{cls.__name__}.find_one_or_create needs at least one lookup field; "
                "an empty lookup would return an arbitrary row"
            )
        if defaults is None:
            default_values: Dict[str, Any] = {}
        elif isinstance(defaults, MappingABC):
            default_values = dict(defaults)
        else:
            raise TypeError(
                f"defaults must be a mapping or None, got {type(defaults).__name__}"
            )

        model_fields = cls.model_fields
        cleaned_lookup: Dict[str, Any] = {}
        for field, value in lookup.items():
            if not isinstance(field, str) or field not in model_fields:
                raise TypeError(f"{field!r} is not a field of {cls.__name__}")
            cls._check_lookup_value(field, value)
            cleaned_lookup[field] = value

        cleaned_defaults: Dict[str, Any] = {}
        for field, value in default_values.items():
            if not isinstance(field, str) or field not in model_fields:
                raise TypeError(f"{field!r} is not a field of {cls.__name__} (in defaults)")
            if isinstance(value, (ColumnBase, SQLPredicate)) or QueryWithParams.holds(value):
                raise TypeError(
                    f"defaults value for {field!r} is an expression; find_one_or_create only "
                    "supports plain values"
                )
            cleaned_defaults[field] = value

        if cls.__pk_auto_generated__:
            key_fields = [
                field
                for field in cls.primary_key_fields()
                if field in cleaned_lookup or field in cleaned_defaults
            ]
            if key_fields:
                raise ValueError(
                    f"{cls.__name__} generates its primary key in the database; do not pass "
                    f"{key_fields} in lookup or defaults. Use the natural key instead."
                )

        create_values = dict(cleaned_defaults)
        create_values.update(cleaned_lookup)
        return cleaned_lookup, create_values

    @classmethod
    def _find_one_by_lookup(cls, lookup: Dict[str, Any]) -> Optional["BaseActiveRecord"]:
        """Return the first row matching every field in ``lookup`` by equality."""
        query = cls.query()
        condition = None
        for field, value in lookup.items():
            column = getattr(cls.c, field)
            comparison = ComparisonPredicate(
                column.dialect, "=", column, Literal(column.dialect, value)
            )
            condition = comparison if condition is None else condition & comparison
        query = query.where(condition)
        return query.one()

    @classmethod
    def _open_savepoint_if_usable(cls) -> Optional[str]:
        """Open a savepoint only when already inside a transaction that supports one."""
        backend = cls.backend()
        if backend is None:
            return None
        manager = backend.transaction_manager
        if not callable(getattr(manager, "supports_savepoint", None)):
            return None
        try:
            if not manager.supports_savepoint():
                return None
            if not getattr(manager, "is_active", False):
                return None
            return manager.savepoint()
        except Exception:
            cls.log(
                logging.ERROR,
                "Could not probe savepoint support for find_one_or_create; "
                "continuing without one",
                exc_info=True,
            )
            return None

    @classmethod
    def _rollback_to_savepoint(cls, savepoint: Optional[str]) -> None:
        """Best-effort recovery to a savepoint; never masks the original failure."""
        if savepoint is None:
            return
        manager = cls.backend().transaction_manager
        try:
            manager.rollback_to(savepoint)
            manager.release(savepoint)
        except Exception as exc:
            cls.log(logging.WARNING, f"Could not roll back to savepoint {savepoint}: {exc}")

    @classmethod
    def _release_savepoint(cls, savepoint: Optional[str]) -> None:
        """Best-effort release of a savepoint after a successful insert."""
        if savepoint is None:
            return
        manager = cls.backend().transaction_manager
        try:
            manager.release(savepoint)
        except Exception as exc:
            cls.log(logging.WARNING, f"Could not release savepoint {savepoint}: {exc}")

    @classmethod
    def find_one_or_create(
        cls: Type["BaseActiveRecord"],
        *,
        defaults: Optional[Mapping[str, Any]] = None,
        **lookup: Any,
    ) -> Tuple["BaseActiveRecord", bool]:
        """Return ``(row, created)`` for the row matching ``lookup``.

        ``lookup`` is a natural key: every keyword names a model field and is
        compared by equality. ``defaults`` fill the remaining fields **on
        creation only**; an existing row is returned untouched.

        The method does not open, commit or roll back a transaction. It runs on
        the connection and transaction context the caller already has, so the
        caller may wrap the call in ``Model.transaction()`` when the lookup and
        insert must share a transaction. Inside an active transaction that
        supports savepoints, a savepoint is used to recover from a failed
        insert; it is a recovery point, not a transaction boundary.

        The lookup is matched with ``query.one()``. The caller must ensure the
        lookup columns carry a unique constraint: without one several rows can
        match, and which row is returned is undefined. The method neither
        inspects nor validates database constraints.

        Args:
            defaults: Values used only when the row is created. When a key also
                appears in ``lookup``, the lookup value wins because it defines
                the identity being searched for.
            **lookup: At least one model field. Only plain equality values are
                accepted; expressions are rejected.

        Returns:
            ``(row, created)``. ``created`` is True only when this call
            inserted the row, in which case ``row`` is the new instance. When a
            concurrent caller inserted the same key first, the winner is
            returned with ``created=False``.

        Raises:
            ValueError: ``lookup`` is empty, contains ``None``, or names a
                database-generated primary key field.
            TypeError: A lookup/defaults key is not a model field, or a value
                is an expression.
            IntegrityError: The insert failed for a constraint that the lookup
                does not explain; re-raised rather than hidden.
        """
        lookup_values, create_values = cls._prepare_find_or_create_inputs(lookup, defaults)

        existing = cls._find_one_by_lookup(lookup_values)
        if existing is not None:
            return existing, False

        row = cls(**create_values)
        savepoint = cls._open_savepoint_if_usable()
        try:
            row.save()
        except IntegrityError as exc:
            cls._rollback_to_savepoint(savepoint)
            try:
                winner = cls._find_one_by_lookup(lookup_values)
            except Exception as read_failure:
                raise exc from read_failure
            if winner is not None:
                return winner, False
            raise exc
        except BaseException:
            cls._rollback_to_savepoint(savepoint)
            raise
        else:
            cls._release_savepoint(savepoint)
            return row, True

    def save(self) -> int:
        """
        Save the record to database, performing insert or update as appropriate.

        This method implements the core persistence functionality. If the record is
        new (determined by is_new_record property), it performs an INSERT operation.
        If the record already exists and has changes, it performs an UPDATE operation with only
        the changed fields.

        The save operation triggers appropriate model events:
        - For new records: BEFORE_INSERT, AFTER_INSERT
        - For existing records: BEFORE_UPDATE, AFTER_UPDATE

        It also handles dirty field tracking to optimize updates.

        Returns:
            int: Number of affected rows in the database
                 - For INSERT operations: typically returns 1 if successful
                 - For UPDATE operations: returns the actual number of updated rows
                   (could be 0 if no fields were changed)

        Raises:
            DatabaseError: If there are issues connecting to or executing against
                          the database
            ValidationError: If the model fails validation before saving
            ReadOnlyError: If the model is read-only
        """
        self.refuse_read_only("save")
        if not self.backend():
            raise DatabaseError("No backend configured")
        try:
            self.validate_fields()
        except Exception as e:
            self.log(logging.DEBUG, f"Validation error, exception will be re-raised: {str(e)}")
            raise DBValidationError(str(e)) from e
        if not self.is_new_record and not self.is_dirty:
            return 0
        try:
            return self._save_internal()
        except DatabaseError:
            raise
        except Exception as e:
            self.log(logging.DEBUG, f"Database error, exception will be re-raised: {str(e)}")
            raise DatabaseError(str(e)) from e

    def delete(self) -> int:
        """
        Delete the record from database.

        This method performs a DELETE operation for the current record. It identifies
        the record to delete using the primary key value and removes it from the database.
        The operation is performed using the model's configured backend.

        The delete operation triggers appropriate model events (BEFORE_DELETE, AFTER_DELETE)
        and updates the internal state of the record. If the model has a 'prepare_delete' method,
        a soft delete is performed by updating the record instead of removing it.

        Returns:
            int: Number of affected rows in the database
                 - Returns 1 if the record was successfully deleted
                 - Returns 0 if no record matched the primary key (record didn't exist)

        Raises:
            DatabaseError: If there are issues connecting to or executing against
                          the database
            ValueError: If the record doesn't have a valid primary key value
            ReadOnlyError: If the model is read-only
        """
        self.refuse_read_only("delete")
        if not self.backend():
            raise DatabaseError("No backend configured")
        if self.is_new_record:
            return 0
        self._trigger_event(ModelEvent.BEFORE_DELETE)
        backend = self.backend()
        pk_value = self._get_pk_value()
        where_predicate = self._build_pk_where_predicate(pk_value)
        is_soft_delete = isinstance(self, IDeleteBehavior)
        if is_soft_delete:
            self.log(logging.DEBUG, f"Soft deleting {self.__class__.__name__}#{pk_value}")
            data = self.prepare_delete()
            update_opts = UpdateOptions(
                table=self.table_name(),
                schema_name=self.schema_name(),
                data=data,
                where=where_predicate,
                log_context=LogContext(
                    model=self.__class__,
                    operation="soft_delete",
                    object_name=self.table_name(),
                    schema=self.schema_name(),
                ),
            )
            result = backend.update(update_opts)
        else:
            self.log(logging.DEBUG, f"Deleting {self.__class__.__name__}#{pk_value}")
            supports_returning = backend.dialect.supports_returning_delete()
            returning_columns = None
            if supports_returning:
                returning_columns = list(self.primary_key_columns())
            delete_opts = DeleteOptions(
                table=self.table_name(),
                schema_name=self.schema_name(),
                where=where_predicate,
                returning_columns=returning_columns,
                log_context=LogContext(
                    model=self.__class__,
                    operation="delete",
                    object_name=self.table_name(),
                    schema=self.schema_name(),
                ),
            )
            result = backend.delete(delete_opts)
        affected_rows = result.affected_rows
        if affected_rows > 0:
            if not is_soft_delete:
                for pk_field in self.__class__.primary_key_fields():
                    if hasattr(self, pk_field):
                        setattr(self, pk_field, None)
            self.reset_tracking()
            self._is_from_db = False
            self._trigger_event(ModelEvent.AFTER_DELETE)
        return affected_rows

    def validate_custom(self) -> None:
        pass

    @classmethod
    def transaction(cls):
        if cls.backend() is None:
            raise DatabaseError("No backend configured")
        return cls.backend().transaction()

    @classmethod
    def get_column_adapters(cls) -> Dict[str, Tuple["SQLTypeAdapter", Type]]:
        adapters_map: Dict[str, Tuple["SQLTypeAdapter", Type]] = {}
        model_fields: Dict[str, FieldInfo] = dict(cls.model_fields)
        all_suggestions = cls.backend().get_default_adapter_suggestions()
        for field_name, field_info in model_fields.items():
            column_name = cls.get_column_name(field_name)
            field_py_type = field_info.annotation
            original_type = field_py_type
            origin = get_origin(field_py_type)
            # Support both Optional (Python 3.8+) and UnionType (Python 3.10+)
            import types

            is_union_type = origin in (Union, Optional) or (hasattr(types, "UnionType") and origin is types.UnionType)
            if is_union_type:
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


class AsyncBaseActiveRecord(AsyncBulkOperationsMixin, LoggingMixin, IAsyncActiveRecord):
    """
    Core Async ActiveRecord implementation providing the fundamental ORM functionality.
    """

    async def _trigger_event(self, event: ModelEvent, **kwargs) -> None:
        """Trigger event asynchronously, awaiting coroutine handlers.

        Async counterpart of :meth:`ActiveRecordBase._trigger_event` (same
        name, ``async``/``await`` only). Sync handlers are invoked normally;
        async handlers (coroutine functions) are awaited so that I/O
        performed inside them (e.g. nested ``await child.save()``) actually
        runs. Sync/async event handling stays on equal footing without
        mixing execution models.
        """
        if hasattr(self, "_event_handlers"):
            for handler in self._event_handlers[event]:
                result = handler(self, **kwargs)
                if inspect.isawaitable(result):
                    await result

    async def validate_fields(self, *args, **kwargs):
        """Validate model fields asynchronously, awaiting coroutine handlers.

        Async counterpart of :meth:`ActiveRecordBase.validate_fields`
        (same name, ``async``/``await`` only). Pydantic validation and
        ``validate_record`` remain synchronous (no I/O); only the
        BEFORE_VALIDATE / AFTER_VALIDATE event triggers are awaited so that
        async handlers run without mixing execution models.
        """
        await self._trigger_event(ModelEvent.BEFORE_VALIDATE)
        self.model_validate(self.model_dump())
        self.validate_record(self)
        await self._trigger_event(ModelEvent.AFTER_VALIDATE)

    def _get_pk_value(self) -> Any:
        cls = self.__class__
        if not cls.addressable():
            raise UnaddressableRecordError(cls.__name__, "Reading the primary key value")
        cols = cls.primary_key_columns()
        fields = cls.primary_key_fields()
        if not cls.is_composite_pk():
            return getattr(self, fields[0])
        return {col: getattr(self, field) for col, field in zip(cols, fields)}

    @classmethod
    def _build_pk_where_predicate(cls, pk_value: Any) -> "SQLPredicate":
        if not cls.addressable():
            raise UnaddressableRecordError(cls.__name__, "Building a primary key predicate")
        dialect = cls.backend().dialect
        columns = cls.primary_key_columns()

        if not cls.is_composite_pk():
            return ComparisonPredicate(dialect, "=", Column(dialect, columns[0]), Literal(dialect, pk_value))

        if not isinstance(pk_value, dict):
            raise TypeError(
                f"{cls.__name__} has composite primary key {columns}, "
                f"pk_value must be a dict, got {type(pk_value).__name__}"
            )
        predicates = []
        for col in columns:
            val = pk_value.get(col)
            if val is None and col not in pk_value:
                field_name = cls._get_field_name(col)
                val = pk_value.get(field_name)
            if val is None:
                raise ValueError(f"Primary key column '{col}' has value None")
            predicates.append(
                ComparisonPredicate(dialect, "=", Column(dialect, col), Literal(dialect, val))
            )
        result = predicates[0]
        for p in predicates[1:]:
            result = result & p
        return result

    @classmethod
    async def configure(
        cls,
        config: Union[ConnectionConfig, Callable[..., ConnectionConfig]],
        backend_class: Type[AsyncStorageBackend],
        *,
        logging_config: Optional[LoggingConfig] = None,
    ) -> None:
        """Configure the model with an async database backend.

        Args:
            config: A ConnectionConfig instance, or a callable that returns one.
                When a callable is provided (e.g., a named connection function),
                it is invoked automatically to obtain the ConnectionConfig.
                Use functools.partial or lambda to pass parameters to the callable.
            backend_class: The AsyncStorageBackend subclass to use.
            logging_config: Optional class-level logging configuration.

        Example:
            # With ConnectionConfig instance
            await AsyncUser.configure(SQLiteConnectionConfig(database=":memory:"), AsyncSQLiteBackend)

            # With callable (named connection function)
            from myapp.connections import prod_db
            await AsyncUser.configure(prod_db, AsyncMySQLBackend)

            # With partial for parameters
            from functools import partial
            await AsyncUser.configure(partial(prod_db, pool_size=20), AsyncMySQLBackend)
        """
        if callable(config) and not isinstance(config, ConnectionConfig):
            config = config()

        if not isinstance(config, ConnectionConfig):
            raise DatabaseError(f"Invalid connection config for {cls.__name__}")

        cls.__connection_config__ = config
        cls.__backend_class__ = backend_class
        if logging_config is not None:
            cls.__logging_config__ = logging_config

        backend_instance = backend_class(connection_config=config, logging_config=logging_config)
        backend_instance.logger = cls.get_logger()

        cls.__backend__ = backend_instance
        if hasattr(cls, "_dummy_backend") and cls._dummy_backend is not None:
            cls._dummy_backend = None

        await backend_instance.introspect_and_adapt()

    @classmethod
    def backend(cls) -> AsyncStorageBackend:
        """Get storage backend instance with context awareness.

        Returns the appropriate backend:
        1. Async context backend (transaction/connection) if available
        2. Class-level backend as fallback
        """
        from ..connection.pool import get_current_async_backend

        # Async context takes priority
        context_backend = get_current_async_backend()
        if context_backend is not None:
            return context_backend

        # Fallback to parent implementation
        return super().backend()

    @classmethod
    def create_from_database(cls, row: Dict[str, Any]) -> "AsyncBaseActiveRecord":
        derived_fields = getattr(cls, "__derived_fields__", {})
        if derived_fields:
            model_data = {k: v for k, v in row.items() if k in cls.model_fields}
            extra_data = {k: v for k, v in row.items() if k not in cls.model_fields}
        else:
            model_data = row
            extra_data = {}

        instance = cls(**model_data)
        instance._is_from_db = True
        instance.reset_tracking()

        if derived_fields:
            col_to_field = {df.column_name: name for name, df in derived_fields.items() if df.column_name is not None}
            for name in derived_fields:
                instance.__dict__[name] = None
            for k, v in extra_data.items():
                field_name = col_to_field.get(k, k)
                df = derived_fields.get(field_name)
                if df is not None and df.adapter is not None:
                    v = df.adapter.from_database(v, df.python_type)
                instance.__dict__[field_name] = v

        return instance

    @classmethod
    def create_collection_from_database(cls, rows: List[Dict[str, Any]]) -> List["AsyncBaseActiveRecord"]:
        return [cls.create_from_database(row) for row in rows]

    async def _insert_internal(self, data) -> Any:
        """
        Internal method to perform the actual insertion of data into the database asynchronously.

        This method handles the complete insertion process including:
        1. Preparing data with column mappings and adapters
        2. Creating insert options with appropriate configurations
        3. Executing the insert operation via the backend asynchronously
        4. Processing the result, including retrieving primary key if needed
        5. Updating the instance with the retrieved primary key value
        6. Marking the instance as loaded from the database and resetting tracking

        Args:
            data: Dictionary containing the field names and values to insert

        Returns:
            The result object from the backend insert operation

        Raises:
            DatabaseError: If there's an issue retrieving the primary key after insert
            ValidationError: If a required primary key field has no value
            ReadOnlyError: If the model is read-only
        """
        self.refuse_read_only("insert")
        self.__class__._missing_key_fields_on_insert(self)
        self.log_data(logging.DEBUG, "Raw data for insert", data)
        prepared_data = self.__class__._map_fields_to_columns(data)
        generated = self.__class__.get_generated_columns()
        if generated:
            prepared_data = {
                k: v for k, v in prepared_data.items() if k not in generated
            }
        self.log_data(logging.DEBUG, "Data with database column names", prepared_data)
        self.log(logging.DEBUG, f"Inserting new {self.__class__.__name__}")
        column_mapping = self.__class__.get_column_to_field_map()
        self.log(logging.DEBUG, f"Column mapping for result processing: {column_mapping}")
        column_adapters = self.get_column_adapters()
        self.log(logging.DEBUG, f"Column adapters map: {column_adapters}")
        supports_returning = self.backend().dialect.supports_returning_insert()
        returning_columns = None
        if supports_returning:
            returning_columns = list(self.primary_key_columns())

        insert_options = InsertOptions(
            table=self.table_name(),
            schema_name=self.schema_name(),
            data=prepared_data,
            column_mapping=column_mapping,
            column_adapters=column_adapters,
            primary_key=self.primary_key(),
            returning_columns=returning_columns,
            log_context=LogContext(
                model=self.__class__,
                operation="insert",
                object_name=self.table_name(),
                schema=self.schema_name(),
            ),
        )
        result = await self.backend().insert(insert_options)
        # A keyless model has nothing for the database to generate, so there is
        # nothing to read back either. Without the addressable() guard the loop
        # below iterates an empty column list and indexes it.
        if self.__class__.__pk_auto_generated__ and self.__class__.addressable():
            pk_columns = self.primary_key_columns()
            pk_retrieved = False
            for col in pk_columns:
                field = self.__class__._get_field_name(col)
                if (
                    field in self.__class__.model_fields
                    and prepared_data.get(col) is None
                    and getattr(self, field, None) is None
                ):
                    retrieved_val = None
                    if result.data and isinstance(result.data, list) and len(result.data) > 0:
                        first_row = result.data[0]
                        if isinstance(first_row, dict) and field in first_row:
                            retrieved_val = first_row[field]
                        elif isinstance(first_row, dict) and col in first_row:
                            retrieved_val = first_row[col]
                    if retrieved_val is None and col == pk_columns[0] and result.last_insert_id is not None:
                        import types
                        field_type = self.__class__.model_fields[field].annotation
                        origin = get_origin(field_type)
                        if origin in (Union, Optional) or origin is types.UnionType:
                            type_args = [t for t in get_args(field_type) if t is not type(None)]
                            if type_args:
                                field_type = type_args[0]
                        if field_type is int:
                            retrieved_val = result.last_insert_id
                    if retrieved_val is not None:
                        setattr(self, field, retrieved_val)
                        pk_retrieved = True
                elif (
                    field in self.__class__.model_fields
                    and getattr(self, field, None) is not None
                ):
                    pk_retrieved = True
            if not pk_retrieved and not self.__class__.is_composite_pk():
                pk_column = pk_columns[0]
                pk_field_name = self.__class__._get_field_name(pk_column)
                error_msg = f"Failed to retrieve primary key '{pk_field_name}' for new record after insert."
                self.log(logging.ERROR, f"{error_msg}")
                raise DatabaseError(error_msg)

        self._is_from_db = True
        self.reset_tracking()
        return result

    async def _update_internal(self, data) -> Any:
        """
        Internal method to perform the actual update of data in the database asynchronously.

        This method handles the complete update process including:
        1. Collecting update conditions and expressions from IUpdateBehavior implementations
        2. Preparing data with column mappings and adapters
        3. Creating update options with appropriate configurations
        4. Executing the update operation via the backend asynchronously
        5. Returning the result of the update operation

        Args:
            data: Dictionary containing the field names and values to update

        Returns:
            The result object from the backend update operation

        Raises:
            ReadOnlyError: If the model is read-only
        """
        self.refuse_read_only("update")
        self.log(
            logging.DEBUG,
            f"Starting update operation for {self.__class__.__name__} record: "
            f"{self._get_pk_value()}",
        )
        update_conditions = []
        update_expressions = {}
        mro = self.__class__.__mro__
        activerecord_idx = mro.index(IAsyncActiveRecord)
        self.log(
            logging.DEBUG,
            f"Traversing MRO for IUpdateBehavior implementations: {[cls.__name__ for cls in mro[:activerecord_idx]]}",
        )
        for cls in mro[:activerecord_idx]:
            if issubclass(cls, IUpdateBehavior):
                defines_conditions_method = "get_update_conditions" in cls.__dict__
                defines_expressions_method = "get_update_expressions" in cls.__dict__
                if defines_conditions_method or defines_expressions_method:
                    self.log(logging.DEBUG, f"Processing IUpdateBehavior from {cls.__name__}")
                    if defines_conditions_method:
                        behavior_conditions = cls.get_update_conditions(self)
                        if behavior_conditions:
                            self.log(
                                logging.DEBUG, f"  Adding {len(behavior_conditions)} condition(s) from {cls.__name__}"
                            )
                            update_conditions.extend(behavior_conditions)
                        else:
                            self.log(logging.DEBUG, f"  No conditions from {cls.__name__}")
                    if defines_expressions_method:
                        behavior_expressions = cls.get_update_expressions(self)
                        if behavior_expressions:
                            self.log(
                                logging.DEBUG,
                                f"  Adding {len(behavior_expressions)} expression(s) from {cls.__name__}: "
                                f"{list(behavior_expressions.keys())}",
                            )
                            update_expressions.update(behavior_expressions)
                        else:
                            self.log(logging.DEBUG, f"  No expressions from {cls.__name__}")
                else:
                    self.log(
                        logging.DEBUG,
                        f"Skipping {cls.__name__} (implements IUpdateBehavior but doesn't define methods directly)",
                    )
        self.log(
            logging.DEBUG,
            f"Update operation: {len(update_conditions)} condition(s), "
            f"{len(update_expressions)} expression(s) collected from mixins",
        )
        self.log(logging.DEBUG, f"Final update conditions: {len(update_conditions)} total")
        self.log(logging.DEBUG, f"Final update expressions: {list(update_expressions.keys())}")
        complete_data = {**data, **update_expressions}
        self.log(logging.DEBUG, f"Complete data for SET clause: {list(complete_data.keys())}")
        mapped_data = self.__class__._map_fields_to_columns(complete_data)
        self.log(logging.DEBUG, f"Mapped data for SET clause: {list(mapped_data.keys())}")
        column_mapping = self.__class__.get_column_to_field_map()
        column_adapters = self.get_column_adapters()
        backend = self.backend()
        pk_value = self._get_pk_value()
        self.log(logging.DEBUG, f"Primary key value: {pk_value}")
        where_predicate = self._build_pk_where_predicate(pk_value)
        for condition in update_conditions:
            if isinstance(condition, SQLPredicate):
                where_predicate = where_predicate & condition
            else:
                self.log(
                    logging.WARNING,
                    f"Skipping non-predicate condition in update: {condition} (type: {type(condition)})",
                )
        self.log(
            logging.DEBUG, f"Final WHERE clause conditions: {len(update_conditions)} additional condition(s) applied"
        )
        supports_returning = backend.dialect.supports_returning_update()
        returning_columns = None
        if supports_returning:
            returning_columns = list(self.primary_key_columns())
        update_options = UpdateOptions(
            table=self.table_name(),
            schema_name=self.schema_name(),
            data=mapped_data,
            where=where_predicate,
            column_mapping=column_mapping,
            column_adapters=column_adapters,
            returning_columns=returning_columns,
            primary_key=self.primary_key(),
            log_context=LogContext(
                model=self.__class__,
                operation="update",
                object_name=self.table_name(),
                schema=self.schema_name(),
            ),
        )
        self.log(
            logging.DEBUG,
            f"Executing update operation on table '{self.table_name()}' with {len(data)} field(s) to update",
        )
        result = await backend.update(update_options)
        return result

    def _prepare_save_data(self) -> Dict[str, Any]:
        is_new = self.is_new_record
        pk_fields = set(self.__class__.primary_key_fields())
        generated = set(self.__class__.get_generated_columns())
        if is_new:
            data = self.model_dump(exclude=self.__class__._insert_pk_exclusions())
        else:
            all_data = self.model_dump()
            data = {field: all_data[field] for field in self._dirty_fields if field not in pk_fields}
        # Generated columns are database-computed: never insert/update them.
        if generated:
            data = {k: v for k, v in data.items() if k not in generated}
        bases = self.__class__.__mro__
        for base in bases:
            if issubclass(base, IDataPreparationBehavior) and base not in (
                IDataPreparationBehavior, AsyncBaseActiveRecord
            ):
                prepare_method = base.prepare_save_data
                data = prepare_method(self, data, is_new)
        return data

    def _after_save(self, is_new: bool) -> None:
        bases = self.__class__.__mro__
        for base in bases:
            if hasattr(base, "after_save") and base != AsyncBaseActiveRecord:
                after_method = base.after_save
                after_method(self, is_new)

    @classmethod
    async def find_one(
        cls: Type["AsyncBaseActiveRecord"],
        condition: Union[Any, Dict[str, Any], Dict["ColumnBase", Any], "SQLPredicate", Tuple[str, tuple]],
        *,
        derived: Union[bool, str, list, dict] = False,
        extra_derived: Optional[Dict[str, Any]] = None,
    ) -> Optional["AsyncBaseActiveRecord"]:
        query = cls.query()
        if isinstance(condition, SQLPredicate):
            query = query.where(condition)
        elif isinstance(condition, dict):
            if cls.is_composite_pk():
                query = query.where(cls._build_pk_where_predicate(condition))
            else:
                for key, value in condition.items():
                    if isinstance(key, ColumnBase):
                        # An explicit node, not the column's own operator: the
                        # key may be a bare Column reference (whose class offers
                        # no operations by design) and the query must not care.
                        query = query.where(
                            ComparisonPredicate(key.dialect, "=", key, Literal(key.dialect, value))
                        )
                    elif isinstance(key, str):
                        column = getattr(cls.c, key)
                        query = query.where(
                            ComparisonPredicate(column.dialect, "=", column, Literal(column.dialect, value))
                        )
                    else:
                        raise TypeError(
                            f"Invalid key type in condition dictionary: {type(key)}. "
                            f"Expected str or Column, got {type(key)}"
                        )
        elif isinstance(condition, tuple) and cls.is_composite_pk():
            cols = cls.primary_key_columns()
            if len(condition) != len(cols):
                raise ValueError(f"Expected {len(cols)} pk values, got {len(condition)}")
            pk_dict = dict(zip(cols, condition))
            query = query.where(cls._build_pk_where_predicate(pk_dict))
        elif QueryWithParams.holds(condition):
            sql, params = condition
            query = query.where(sql, params)
        elif not cls.is_composite_pk():
            if not cls.addressable():
                raise UnaddressableRecordError(cls.__name__, "find_one")
            pk_field_name = cls.primary_key()
            dialect = cls.backend().dialect
            pk_column = Column(dialect, pk_field_name)
            query = query.where(
                ComparisonPredicate(dialect, "=", pk_column, Literal(dialect, condition))
            )
        else:
            raise TypeError(
                f"{cls.__name__} has composite primary key; "
                "pass a dict or tuple as condition"
            )
        cls._apply_derived_to_query(query, derived, extra_derived)
        return await query.one()

    @classmethod
    async def find_all(
        cls: Type["AsyncBaseActiveRecord"],
        condition: Optional[
            Union[Any, List[Any], Dict[str, Any], Dict["ColumnBase", Any], "SQLPredicate", Tuple[str, tuple]]
        ] = None,
        *,
        derived: Union[bool, str, list, dict] = False,
        extra_derived: Optional[Dict[str, Any]] = None,
    ) -> List["AsyncBaseActiveRecord"]:
        query = cls.query()
        if condition is None:
            cls._apply_derived_to_query(query, derived, extra_derived)
            return await query.all()
        if isinstance(condition, SQLPredicate):
            query = query.where(condition)
        elif isinstance(condition, dict):
            if cls.is_composite_pk():
                query = query.where(cls._build_pk_where_predicate(condition))
            else:
                for key, value in condition.items():
                    if isinstance(key, ColumnBase):
                        # An explicit node, not the column's own operator: the
                        # key may be a bare Column reference (whose class offers
                        # no operations by design) and the query must not care.
                        query = query.where(
                            ComparisonPredicate(key.dialect, "=", key, Literal(key.dialect, value))
                        )
                    elif isinstance(key, str):
                        column = getattr(cls.c, key)
                        query = query.where(
                            ComparisonPredicate(column.dialect, "=", column, Literal(column.dialect, value))
                        )
                    else:
                        raise TypeError(
                            f"Invalid key type in condition dictionary: {type(key)}. "
                            f"Expected str or Column, got {type(key)}"
                        )
        elif isinstance(condition, list):
            if not condition:
                return []
            if cls.is_composite_pk():
                cols = cls.primary_key_columns()
                predicates = []
                for item in condition:
                    if isinstance(item, tuple):
                        pk_dict = dict(zip(cols, item))
                    elif isinstance(item, dict):
                        pk_dict = item
                    else:
                        raise TypeError("Composite PK list items must be dict or tuple")
                    predicates.append(cls._build_pk_where_predicate(pk_dict))
                combined = predicates[0]
                for p in predicates[1:]:
                    combined = combined | p
                query = query.where(combined)
            else:
                if not cls.addressable():
                    raise UnaddressableRecordError(cls.__name__, "find_all")
                pk_field_name = cls.primary_key()
                dialect = cls.backend().dialect
                query = query.where(
                    InPredicate(dialect, Column(dialect, pk_field_name), Literal(dialect, tuple(condition)))
                )
        elif QueryWithParams.holds(condition):
            sql, params = condition
            query = query.where(sql, params)
        else:  # Assumes list of primary keys (backward compat)
            if not cls.addressable():
                raise UnaddressableRecordError(cls.__name__, "find_all")
            pk_field_name = cls.primary_key()
            if not condition:
                return []
            dialect = cls.backend().dialect
            query = query.where(
                InPredicate(dialect, Column(dialect, pk_field_name), Literal(dialect, tuple(condition)))
            )
        cls._apply_derived_to_query(query, derived, extra_derived)
        return await query.all()

    @classmethod
    async def find_one_or_fail(
        cls: Type["AsyncBaseActiveRecord"],
        condition: Union[Any, Dict[str, Any], Dict["ColumnBase", Any], "SQLPredicate", Tuple[str, tuple]],
        *,
        derived: Union[bool, str, list, dict] = False,
        extra_derived: Optional[Dict[str, Any]] = None,
    ) -> "AsyncBaseActiveRecord":
        record = await cls.find_one(condition, derived=derived, extra_derived=extra_derived)
        if record is None:
            cls.log(logging.DEBUG, f"Record not found for {cls.__name__} with find_one condition: {condition}")
            raise RecordNotFound(f"Record not found for {cls.__name__}")
        return record

    @classmethod
    def _check_lookup_value(cls, field: str, value: Any) -> None:
        """Reject lookup values that cannot be compared by equality."""
        if value is None:
            raise ValueError(
                f"lookup value for {field!r} is None; an equality lookup needs a concrete value"
            )
        if isinstance(value, (ColumnBase, SQLPredicate)) or QueryWithParams.holds(value):
            raise TypeError(
                f"lookup value for {field!r} is an expression; find_one_or_create only supports "
                "plain equality values"
            )

    @classmethod
    def _prepare_find_or_create_inputs(
        cls,
        lookup: Dict[str, Any],
        defaults: Optional[Mapping[str, Any]],
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Validate ``lookup`` / ``defaults`` and return the create values.

        ``lookup`` is the natural key and must name at least one model field.
        ``defaults`` fill the remaining fields on creation only, so ``lookup``
        wins when both name the same field.

        Raises:
            ValueError: The lookup is empty; a lookup value is ``None``; or
                ``lookup`` / ``defaults`` name a database-generated primary
                key field.
            TypeError: A key is not a model field, a value is an expression, or
                ``defaults`` is neither a mapping nor ``None``.
        """
        if not lookup:
            raise ValueError(
                f"{cls.__name__}.find_one_or_create needs at least one lookup field; "
                "an empty lookup would return an arbitrary row"
            )
        if defaults is None:
            default_values: Dict[str, Any] = {}
        elif isinstance(defaults, MappingABC):
            default_values = dict(defaults)
        else:
            raise TypeError(
                f"defaults must be a mapping or None, got {type(defaults).__name__}"
            )

        model_fields = cls.model_fields
        cleaned_lookup: Dict[str, Any] = {}
        for field, value in lookup.items():
            if not isinstance(field, str) or field not in model_fields:
                raise TypeError(f"{field!r} is not a field of {cls.__name__}")
            cls._check_lookup_value(field, value)
            cleaned_lookup[field] = value

        cleaned_defaults: Dict[str, Any] = {}
        for field, value in default_values.items():
            if not isinstance(field, str) or field not in model_fields:
                raise TypeError(f"{field!r} is not a field of {cls.__name__} (in defaults)")
            if isinstance(value, (ColumnBase, SQLPredicate)) or QueryWithParams.holds(value):
                raise TypeError(
                    f"defaults value for {field!r} is an expression; find_one_or_create only "
                    "supports plain values"
                )
            cleaned_defaults[field] = value

        if cls.__pk_auto_generated__:
            key_fields = [
                field
                for field in cls.primary_key_fields()
                if field in cleaned_lookup or field in cleaned_defaults
            ]
            if key_fields:
                raise ValueError(
                    f"{cls.__name__} generates its primary key in the database; do not pass "
                    f"{key_fields} in lookup or defaults. Use the natural key instead."
                )

        create_values = dict(cleaned_defaults)
        create_values.update(cleaned_lookup)
        return cleaned_lookup, create_values

    @classmethod
    async def _find_one_by_lookup(cls, lookup: Dict[str, Any]) -> Optional["AsyncBaseActiveRecord"]:
        """Return the first row matching every field in ``lookup`` by equality."""
        query = cls.query()
        condition = None
        for field, value in lookup.items():
            column = getattr(cls.c, field)
            comparison = ComparisonPredicate(
                column.dialect, "=", column, Literal(column.dialect, value)
            )
            condition = comparison if condition is None else condition & comparison
        query = query.where(condition)
        return await query.one()

    @classmethod
    async def _open_savepoint_if_usable(cls) -> Optional[str]:
        """Open a savepoint only when already inside a transaction that supports one."""
        backend = cls.backend()
        if backend is None:
            return None
        manager = backend.transaction_manager
        if not callable(getattr(manager, "supports_savepoint", None)):
            return None
        try:
            if not await manager.supports_savepoint():
                return None
            if not getattr(manager, "is_active", False):
                return None
            return await manager.savepoint()
        except Exception:
            cls.log(
                logging.ERROR,
                "Could not probe savepoint support for find_one_or_create; "
                "continuing without one",
                exc_info=True,
            )
            return None

    @classmethod
    async def _rollback_to_savepoint(cls, savepoint: Optional[str]) -> None:
        """Best-effort recovery to a savepoint; never masks the original failure."""
        if savepoint is None:
            return
        manager = cls.backend().transaction_manager
        try:
            await manager.rollback_to(savepoint)
            await manager.release(savepoint)
        except Exception as exc:
            cls.log(logging.WARNING, f"Could not roll back to savepoint {savepoint}: {exc}")

    @classmethod
    async def _release_savepoint(cls, savepoint: Optional[str]) -> None:
        """Best-effort release of a savepoint after a successful insert."""
        if savepoint is None:
            return
        manager = cls.backend().transaction_manager
        try:
            await manager.release(savepoint)
        except Exception as exc:
            cls.log(logging.WARNING, f"Could not release savepoint {savepoint}: {exc}")

    @classmethod
    async def find_one_or_create(
        cls: Type["AsyncBaseActiveRecord"],
        *,
        defaults: Optional[Mapping[str, Any]] = None,
        **lookup: Any,
    ) -> Tuple["AsyncBaseActiveRecord", bool]:
        """Return ``(row, created)`` for the row matching ``lookup`` asynchronously.

        ``lookup`` is a natural key: every keyword names a model field and is
        compared by equality. ``defaults`` fill the remaining fields **on
        creation only**; an existing row is returned untouched.

        The method does not open, commit or roll back a transaction. It runs on
        the connection and transaction context the caller already has, so the
        caller may wrap the call in ``Model.transaction()`` when the lookup and
        insert must share a transaction. Inside an active transaction that
        supports savepoints, a savepoint is used to recover from a failed
        insert; it is a recovery point, not a transaction boundary.

        The lookup is matched with ``query.one()``. The caller must ensure the
        lookup columns carry a unique constraint: without one several rows can
        match, and which row is returned is undefined. The method neither
        inspects nor validates database constraints.

        Args:
            defaults: Values used only when the row is created. When a key also
                appears in ``lookup``, the lookup value wins because it defines
                the identity being searched for.
            **lookup: At least one model field. Only plain equality values are
                accepted; expressions are rejected.

        Returns:
            ``(row, created)``. ``created`` is True only when this call
            inserted the row, in which case ``row`` is the new instance. When a
            concurrent caller inserted the same key first, the winner is
            returned with ``created=False``.

        Raises:
            ValueError: ``lookup`` is empty, contains ``None``, or names a
                database-generated primary key field.
            TypeError: A lookup/defaults key is not a model field, or a value
                is an expression.
            IntegrityError: The insert failed for a constraint that the lookup
                does not explain; re-raised rather than hidden.
        """
        lookup_values, create_values = cls._prepare_find_or_create_inputs(lookup, defaults)

        existing = await cls._find_one_by_lookup(lookup_values)
        if existing is not None:
            return existing, False

        row = cls(**create_values)
        savepoint = await cls._open_savepoint_if_usable()
        try:
            await row.save()
        except IntegrityError as exc:
            await cls._rollback_to_savepoint(savepoint)
            try:
                winner = await cls._find_one_by_lookup(lookup_values)
            except Exception as read_failure:
                raise exc from read_failure
            if winner is not None:
                return winner, False
            raise exc
        except BaseException:
            await cls._rollback_to_savepoint(savepoint)
            raise
        else:
            await cls._release_savepoint(savepoint)
            return row, True

    async def save(self) -> int:
        """
        Save the record to database asynchronously, performing insert or update as appropriate.

        This method implements the core persistence functionality. If the record is
        new (determined by is_new_record property), it performs an INSERT operation.
        If the record already exists and has changes, it performs an UPDATE operation with only
        the changed fields.

        The save operation triggers appropriate model events:
        - For new records: BEFORE_INSERT, AFTER_INSERT
        - For existing records: BEFORE_UPDATE, AFTER_UPDATE

        It also handles dirty field tracking to optimize updates.

        Returns:
            int: Number of affected rows in the database
                 - For INSERT operations: typically returns 1 if successful
                 - For UPDATE operations: returns the actual number of updated rows
                   (could be 0 if no fields were changed)

        Raises:
            DatabaseError: If there are issues connecting to or executing against
                          the database
            ValidationError: If the model fails validation before saving
            ReadOnlyError: If the model is read-only
        """
        self.refuse_read_only("save")
        if not self.backend():
            raise DatabaseError("No backend configured")
        try:
            await self.validate_fields()
        except Exception as e:
            self.log(logging.DEBUG, f"Validation error, exception will be re-raised: {str(e)}")
            raise DBValidationError(str(e)) from e
        if not self.is_new_record and not self.is_dirty:
            return 0
        try:
            return await self._save_internal()
        except DatabaseError:
            raise
        except Exception as e:
            self.log(logging.DEBUG, f"Database error, exception will be re-raised: {str(e)}")
            raise DatabaseError(str(e)) from e

    async def delete(self) -> int:
        """
        Delete the record from database asynchronously.

        This method performs a DELETE operation for the current record. It identifies
        the record to delete using the primary key value and removes it from the database.
        The operation is performed using the model's configured backend.

        The delete operation triggers appropriate model events (BEFORE_DELETE, AFTER_DELETE)
        and updates the internal state of the record. If the model has a 'prepare_delete' method,
        a soft delete is performed by updating the record instead of removing it.

        Returns:
            int: Number of affected rows in the database
                 - Returns 1 if the record was successfully deleted
                 - Returns 0 if no record matched the primary key (record didn't exist)

        Raises:
            DatabaseError: If there are issues connecting to or executing against
                          the database
            ValueError: If the record doesn't have a valid primary key value
            ReadOnlyError: If the model is read-only
        """
        self.refuse_read_only("delete")
        if not self.backend():
            raise DatabaseError("No backend configured")
        if self.is_new_record:
            return 0
        await self._trigger_event(ModelEvent.BEFORE_DELETE)
        backend = self.backend()
        pk_value = self._get_pk_value()
        where_predicate = self._build_pk_where_predicate(pk_value)
        is_soft_delete = isinstance(self, IDeleteBehavior)
        if is_soft_delete:
            self.log(logging.DEBUG, f"Soft deleting {self.__class__.__name__}#{pk_value}")
            data = self.prepare_delete()
            update_opts = UpdateOptions(
                table=self.table_name(),
                schema_name=self.schema_name(),
                data=data,
                where=where_predicate,
                log_context=LogContext(
                    model=self.__class__,
                    operation="soft_delete",
                    object_name=self.table_name(),
                    schema=self.schema_name(),
                ),
            )
            result = await backend.update(update_opts)
        else:
            self.log(logging.DEBUG, f"Deleting {self.__class__.__name__}#{pk_value}")
            supports_returning = backend.dialect.supports_returning_delete()
            returning_columns = None
            if supports_returning:
                returning_columns = list(self.primary_key_columns())
            delete_opts = DeleteOptions(
                table=self.table_name(),
                schema_name=self.schema_name(),
                where=where_predicate,
                returning_columns=returning_columns,
                log_context=LogContext(
                    model=self.__class__,
                    operation="delete",
                    object_name=self.table_name(),
                    schema=self.schema_name(),
                ),
            )
            result = await backend.delete(delete_opts)
        affected_rows = result.affected_rows
        if affected_rows > 0:
            if not is_soft_delete:
                for pk_field in self.__class__.primary_key_fields():
                    if hasattr(self, pk_field):
                        setattr(self, pk_field, None)
            self.reset_tracking()
            self._is_from_db = False
            await self._trigger_event(ModelEvent.AFTER_DELETE)
        return affected_rows

    def validate_custom(self) -> None:
        pass

    @classmethod
    def transaction(cls):
        if cls.backend() is None:
            raise DatabaseError("No backend configured")
        return cls.backend().transaction()

    @classmethod
    def get_column_adapters(cls) -> Dict[str, Tuple["SQLTypeAdapter", Type]]:
        adapters_map: Dict[str, Tuple["SQLTypeAdapter", Type]] = {}
        model_fields: Dict[str, FieldInfo] = dict(cls.model_fields)
        all_suggestions = cls.backend().get_default_adapter_suggestions()
        for field_name, field_info in model_fields.items():
            column_name = cls.get_column_name(field_name)
            field_py_type = field_info.annotation
            original_type = field_py_type
            origin = get_origin(field_py_type)
            # Support both Optional (Python 3.8+) and UnionType (Python 3.10+)
            import types

            is_union_type = origin in (Union, Optional) or (hasattr(types, "UnionType") and origin is types.UnionType)
            if is_union_type:
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
