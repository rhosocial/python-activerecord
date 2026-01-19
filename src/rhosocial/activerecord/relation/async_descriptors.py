# src/rhosocial/activerecord/relation/async_descriptors.py
"""
Async relation descriptor implementations.
Provides AsyncBelongsTo, AsyncHasOne, and AsyncHasMany relationship types.
"""

import logging

from typing import Type, Any, Generic, TypeVar, Union, ForwardRef, Optional, get_type_hints, ClassVar, List, cast, Dict

from .cache import CacheConfig, InstanceCache
from .interfaces import IAsyncRelationValidation, IAsyncRelationLoader
from ..interface import IAsyncActiveRecord, IAsyncActiveQuery

U = TypeVar('U', bound=IAsyncActiveRecord)


def _evaluate_forward_ref(ref: Union[str, ForwardRef], owner: Type[Any]) -> Type[U]:
    """
    Evaluate forward reference in proper context.

    Args:
        ref: String or ForwardRef to evaluate
        owner: Owner model class for resolution context

    Returns:
        Resolved model class
    """
    import sys
    import inspect

    # Get calling frame to access local scope
    frame = inspect.currentframe()
    while frame:
        if owner.__module__ in str(frame.f_code):
            local_context = frame.f_locals
            break
        frame = frame.f_back
    else:
        local_context = {}

    module = sys.modules[owner.__module__]
    module_globals = {k: getattr(module, k) for k in dir(module)}
    owner_locals = {owner.__name__: owner}

    # Combine all contexts with priority to most specific scope
    context = {}
    context.update(module_globals)
    context.update(local_context)
    context.update(owner_locals)

    type_str = ref if isinstance(ref, str) else ref.__forward_arg__

    if isinstance(ref, ForwardRef):
        # Use official typing_extensions.evaluate_forward_ref if available
        try:
            from typing_extensions import evaluate_forward_ref
            return evaluate_forward_ref(ref, owner=owner, globals=context, locals=None)
        except ImportError:
            # Fallback: try using get_type_hints instead of direct _evaluate call
            try:
                # Create a temporary class with the forward ref to leverage get_type_hints
                temp_annotations = {'temp': ref}
                hints = get_type_hints(type('TempClass', (), {'__annotations__': temp_annotations}), globalns=context)
                return hints.get('temp', ref)
            except (NameError, AttributeError, TypeError):
                pass

    # Final fallback: direct evaluation for string references
    return eval(type_str, context, None)


class AsyncRelationDescriptor(Generic[U]):
    """
    Async descriptor for managing model relations.
    Modified to use instance-level caching for proper isolation.

    The AsyncRelationDescriptor serves as the core implementation for all async relationship types
    (AsyncBelongsTo, AsyncHasOne, AsyncHasMany). It handles model type resolution, relation validation,
    data loading, and caching. The descriptor follows Python's descriptor protocol to
    provide transparent relation access on async model instances.

    Usage:
        # In async model definition
        from typing import ClassVar
        from rhosocial.activerecord.relation.async_descriptors import AsyncHasMany, AsyncBelongsTo

        class AsyncUser(AsyncActiveRecord):
            id: int
            name: str

            # IMPORTANT: Relationship fields must be declared as ClassVar to avoid being tracked by Pydantic
            posts: ClassVar[AsyncHasMany['AsyncPost']] = AsyncHasMany(foreign_key='user_id', inverse_of='user')

        class AsyncPost(AsyncActiveRecord):
            id: int
            title: str
            user_id: int

            # IMPORTANT: Relationship fields must be declared as ClassVar to avoid being tracked by Pydantic
            user: ClassVar[AsyncBelongsTo['AsyncUser']] = AsyncBelongsTo(foreign_key='user_id', inverse_of='posts')

        # At runtime, the relations can be accessed as follows:
        user = await AsyncUser.find(1)
        posts = await user.posts()  # Returns list of related AsyncPost instances
        post = await AsyncPost.find(1)
        user = await post.user()    # Returns related AsyncUser instance

    Args:
        foreign_key: Foreign key field name used to establish the relationship
        inverse_of: Name of the inverse relation on the related model for validation
        loader: Custom loader implementation for loading related data
        validator: Custom validation implementation for relationship validation
        cache_config: Cache configuration for controlling caching behavior

    Raises:
        ValueError: If inverse relationship validation fails
        TypeError: If foreign_key is not a string or cache_config is not CacheConfig instance
    """

    def __init__(
            self,
            foreign_key: str,
            inverse_of: Optional[str] = None,
            loader: Optional[IAsyncRelationLoader[U]] = None,
            validator: Optional[IAsyncRelationValidation] = None,
            cache_config: Optional[CacheConfig] = None
    ):
        if type(foreign_key) is not str:
            raise TypeError("foreign_key must be a string")
        self.foreign_key = foreign_key
        self.inverse_of = inverse_of
        self._loader = loader or AsyncDefaultRelationLoader(self)
        self._validator = validator
        if cache_config is not None and not isinstance(cache_config, CacheConfig):
            raise TypeError("cache_config must be instance of CacheConfig")
        self._cache_config = cache_config or CacheConfig()
        self._cached_model: Optional[Type[U]] = None
        self._owner = None

    def log(self, level: int, msg: str, *args, **kwargs) -> None:
        """Log message using owner's logger.

        Args:
            level: Log level from logging module
            msg: Log message
            *args: Additional positional arguments
            **kwargs: Additional keyword arguments
        """
        if hasattr(self, '_owner') and hasattr(self._owner, 'log'):
            # Add offset to account for our log method
            if 'offset' in kwargs:
                kwargs['offset'] += 1
            else:
                kwargs['offset'] = 1
            self._owner.log(level, msg, *args, **kwargs)

    def __set_name__(self, owner: Type, name: str) -> None:
        """
        Called when the descriptor is assigned to a class attribute during class creation.

        This method implements the descriptor protocol and is automatically called when
        an AsyncRelationDescriptor is assigned as a class attribute. It performs the following:
        1. Sets the relation name and owner class
        2. Registers the relation with the owner class
        3. Creates and attaches a dynamic query method for the relation

        Args:
            owner: The model class that owns this relation descriptor
            name: The name of the attribute to which this descriptor is assigned
        """
        self.name = name
        self._owner = owner
        # self._cache.relation_name = name

        self.log(logging.DEBUG, f"Registering async relation `{name}` with `{owner.__name__}`")
        owner.register_relation(name, self)

        # Create query method that returns QuerySet for the related model
        query_method = self._create_query_method()
        setattr(owner, f"{name}_query", query_method)

    def __get__(self, instance: Any, owner: Optional[Type] = None) -> Any:
        """
        Descriptor protocol method called when accessing the relation from an instance.

        This method handles the descriptor protocol for attribute access. When accessed
        from a class, it returns the descriptor itself. When accessed from an instance,
        it creates and returns a bound relation method that can be used to access the
        related data.

        Args:
            instance: The model instance accessing the relation (None if accessed from class)
            owner: The model class that owns this descriptor

        Returns:
            If accessed from class: the descriptor itself
            If accessed from instance: a bound method for accessing related data
        """
        self.log(logging.DEBUG, f"Getting `{self.name}` async relation for {owner.__name__ if owner else 'None'}")
        if instance is None:
            return self

        # Force validation on first access
        if self._cached_model is None:
            self.log(logging.DEBUG, f"Forcing model resolution for `{self.name}`")
            self.get_related_model(owner or type(instance))

        return self._create_relation_method(instance)

    def __delete__(self, instance: Any) -> None:
        """Clear cache on deletion."""
        self.log(logging.DEBUG, f"Clearing cache for `{self.name}` relation")
        InstanceCache.delete(instance, self.name)

    def get_related_model(self, owner: Type[Any]) -> Type[U]:
        """
        Get related model class, resolving if needed.

        Args:
            owner: Owner model class

        Returns:
            Type[U]: Related model class

        Raises:
            ValueError: If model cannot be resolved
        """
        if self._cached_model is None:
            self.log(logging.DEBUG, f"Resolving related model for `{self.name}`")
            self._cached_model = self._resolve_model(owner)

            # Ensure model is fully resolved before validation
            if isinstance(self._cached_model, (str, ForwardRef)):
                self.log(logging.DEBUG, f"Evaluating forward reference: {self._cached_model}")
                self._cached_model = _evaluate_forward_ref(self._cached_model, owner)

            if self.inverse_of and self._validator:
                try:
                    self.log(logging.DEBUG, f"Validating inverse relationship: {self.inverse_of}")
                    self._validate_inverse_relationship(owner)
                except Exception as e:
                    self._cached_model = None
                    self.log(logging.ERROR, f"Invalid relationship: {str(e)}")
                    raise ValueError(f"Invalid relationship: {str(e)}")

        return self._cached_model

    def _resolve_model(self, owner: Type[Any]) -> Union[Type[U], ForwardRef, str]:
        """
        Resolve model type from annotations, handling both string and ForwardRef.

        Python 3.8+ compatible implementation that properly handles forward references.
        """
        self.log(logging.DEBUG, f"Resolving model type for {self.name}")

        # Get module globals for model resolution context
        import sys
        module = sys.modules[owner.__module__]
        module_globals = {k: getattr(module, k) for k in dir(module)}

        # First attempt with get_type_hints
        try:
            type_hints = get_type_hints(owner, localns=module_globals)
        except (NameError, AttributeError):
            # Fallback to raw annotations for forward refs
            type_hints = owner.__annotations__

        # Find descriptor field in type hints
        for name, field_type in type_hints.items():
            if getattr(owner, name, None) is self:
                # Handle ClassVar wrapper
                if hasattr(field_type, "__origin__") and field_type.__origin__ is ClassVar:
                    field_type = field_type.__args__[0]

                # Get model type from generic parameters
                if hasattr(field_type, "__origin__") and hasattr(field_type, "__args__"):
                    model_type = field_type.__args__[0]
                    self.log(logging.DEBUG, f"Resolved model type: {model_type}")
                    return model_type

        self.log(logging.ERROR, f"Unable to resolve relationship model for `{self.name}`")
        raise ValueError("Unable to resolve relationship model")

    def _validate_inverse_relationship(self, owner: Type[Any]) -> None:
        """
        Validate inverse relationship consistency.

        Raises:
            ValueError: If validation fails
        """
        self.log(logging.DEBUG, f"Validating inverse relationship: {self.inverse_of}")
        if self._validator:
            try:
                self._validator.validate(owner, self._cached_model)
                self.log(logging.DEBUG, "Inverse relationship validation successful")
            except Exception as e:
                self.log(logging.ERROR, f"Inverse relationship validation failed: {e}")
                raise

    def _create_relation_method(self, instance: Any):
        """
        Creates a bound method for accessing the relation data for a specific instance.

        This method creates a closure that binds the relation descriptor to a specific
        instance. The returned method can be used to access related data for that instance.

        Args:
            instance: The model instance for which to create the relation access method

        Returns:
            A callable method that can be used to access the related data for the instance
        """
        self.log(logging.DEBUG, f"Creating async relation method for `{self.name}`")

        async def relation_method(*args, **kwargs):
            if args or kwargs:
                return self._query.query(instance, *args, **kwargs) if self._query else None
            return await self._load_relation(instance)

        relation_method.clear_cache = lambda: InstanceCache.delete(instance, self.name)
        return relation_method

    def _create_query_method(self):
        """
        Creates a dynamic query method for the relation that returns a preconfigured query.

        This method creates a query method that is attached to the model class during
        class creation. The query is preconfigured with the appropriate foreign key
        conditions based on the relationship type (AsyncBelongsTo vs AsyncHasOne/AsyncHasMany).

        Returns:
            A callable method that takes an instance and returns a preconfigured query
        """
        self.log(logging.DEBUG, f"Creating async query method for `{self.name}`")

        def query_method(instance):
            # Force model resolution if needed
            related_model = self.get_related_model(type(instance))
            # Start with base query for the related model
            query = related_model.query()

            # Add appropriate foreign key condition based on relationship type
            if isinstance(self, AsyncBelongsTo):
                # For AsyncBelongsTo, filter by primary key matching our foreign key
                if hasattr(instance, self.foreign_key):
                    fk_value = getattr(instance, self.foreign_key)
                    if fk_value is not None:
                        # Use backend expression system instead of manual SQL string concatenation
                        backend = related_model.backend()
                        from ..backend.expression.core import Column
                        pk_column = Column(backend.dialect, related_model.primary_key(), table=related_model.table_name())
                        query = query.where(pk_column == fk_value)
            else:
                # For AsyncHasOne/AsyncHasMany, filter by foreign key matching our primary key
                pk_value = getattr(instance, instance.primary_key())
                if pk_value is not None:
                    # Use backend expression system instead of manual SQL string concatenation
                    backend = related_model.backend()
                    from ..backend.expression.core import Column
                    fk_column = Column(backend.dialect, self.foreign_key, table=related_model.table_name())
                    query = query.where(fk_column == pk_value)

            return query

        return query_method

    async def _load_relation(self, instance: Any) -> Optional[U]:
        """
        Loads the related data for a specific instance with caching support.

        This method implements the lazy-loading behavior for relations. It first checks
        the instance-level cache, and if not found, delegates to the relation loader
        to fetch the data from the database. The loaded data is then cached for future
        access.

        Args:
            instance: The model instance for which to load the related data

        Returns:
            Optional[U]: The related model instance(s) or None if not found
        """
        if self._cached_model is None:
            self.get_related_model(type(instance))

        cached = InstanceCache.get(instance, self.name, self._cache_config)
        if cached is not None:
            self.log(logging.DEBUG, f"Using cached async relation for `{self.name}`")
            return cached

        try:
            self.log(logging.DEBUG, f"Loading async relation `{self.name}` for {type(instance).__name__}")
            data = await self._loader.load(instance) if self._loader else None
            InstanceCache.set(instance, self.name, data, self._cache_config)
            return data
        except Exception as e:
            self.log(logging.ERROR, f"Error loading async relation: {e}")
            return None

    async def batch_load(self, records: List[Any], base_query: Optional[IAsyncActiveQuery]) -> Dict[int, Any]:
        """
        Batch loads related records for multiple parent records efficiently.

        This method implements an optimized loading strategy that minimizes database queries
        by loading multiple related records in a single operation. It first checks the cache
        for each record, and only loads uncached records from the database. This is a key
        component in solving the N+1 query problem.

        Args:
            records: List of parent records to load relations for
            base_query: Pre-configured query with potential filters from with_() configurations

        Returns:
            Dict mapping record IDs (using id() function) to their related data
        """
        self.log(logging.DEBUG, f"Async batch loading `{self.name}` relation for {len(records)} records")
        if self._cached_model is None:
            self.get_related_model(type(records[0]))

        result = {}
        # Try cache first
        for record in records:
            cached = InstanceCache.get(record, self.name, self._cache_config)
            if cached is not None:
                result[id(record)] = cached

        # Get records that need loading
        records_to_load = [
            record for record in records
            if id(record) not in result
        ]

        if not records_to_load:
            self.log(logging.DEBUG, f"All `{self.name}` relations found in cache")
            return result

        try:
            # Use loader to batch load remaining records
            self.log(logging.DEBUG, f"Loading {len(records_to_load)} `{self.name}` relations not in cache")
            loaded_data = await self._loader.batch_load(records_to_load, base_query)
            if loaded_data:
                # Cache and add to result
                for record_id, data in loaded_data.items():
                    for record in records_to_load:
                        if id(record) == record_id:
                            InstanceCache.set(record, self.name, data, self._cache_config)
                            break
                result.update(loaded_data)
        except Exception as e:
            self.log(logging.ERROR, f"Error in async batch loading `{self.name}` relations: {e}")

        return result


class AsyncRelationshipValidator(IAsyncRelationValidation):
    """Async relationship validator implementation."""

    def __init__(self, descriptor: AsyncRelationDescriptor):
        """
        Initialize validator with descriptor reference.

        Args:
            descriptor: The AsyncRelationDescriptor instance being validated
        """
        self.descriptor = descriptor

    def validate(self, owner: Type[Any], related_model: Type[Any]) -> None:
        """
        Validate relationship between models.

        Args:
            owner: Owner model class
            related_model: Related model class

        Raises:
            ValueError: If validation fails
        """
        # Ensure both models have __name__ attribute
        owner_name = getattr(owner, '__name__', str(owner))
        related_name = getattr(related_model, '__name__', str(related_model))

        if not hasattr(related_model, self.descriptor.inverse_of):
            raise ValueError(f"Inverse relationship '{self.descriptor.inverse_of}' not found in {related_name}")

        inverse_rel = getattr(related_model, self.descriptor.inverse_of)
        if not isinstance(inverse_rel, AsyncRelationDescriptor):
            raise ValueError(
                f"Inverse relationship '{self.descriptor.inverse_of}' in "
                f"{related_name} must be an AsyncRelationDescriptor"
            )

        # Check for valid relationship pairs
        valid_pairs = [
            (AsyncBelongsTo, AsyncHasOne),
            (AsyncBelongsTo, AsyncHasMany),
            (AsyncHasOne, AsyncBelongsTo),
            (AsyncHasMany, AsyncBelongsTo),
        ]

        if not any(isinstance(self.descriptor, t1) and isinstance(inverse_rel, t2)
                   for t1, t2 in valid_pairs):
            raise ValueError(
                f"Invalid relationship pair between {owner_name} and {related_name}: "
                f"{type(self.descriptor).__name__} and {type(inverse_rel).__name__}"
            )

        # Set inverse relationship name if not already set
        if inverse_rel.inverse_of is None:
            for name, value in owner.__dict__.items():
                if value is self.descriptor:
                    inverse_rel.inverse_of = name
                    break
        elif not any(value is self.descriptor for value in owner.__dict__.values()):
            raise ValueError(f"Inconsistent inverse relationship between {owner_name} and {related_name}")


class AsyncDefaultRelationLoader(IAsyncRelationLoader[U]):
    """
    Default async relation loader implementation.
    """

    def __init__(self, descriptor: AsyncRelationDescriptor[U]):
        """
        Initialize the loader with a reference to its descriptor.

        Args:
            descriptor: The AsyncRelationDescriptor that owns this loader and defines
                       the relationship characteristics (foreign key, relationship type, etc.)
        """
        self.descriptor = descriptor
        self._cached_model: Optional[Type[U]] = None

    async def load(self, instance: Any) -> Optional[Union[U, List[U]]]:
        """
        Load related data for a single instance.

        This method provides a single-instance loading interface that delegates
        to the more efficient batch_load method for consistency.

        Args:
            instance: The model instance to load relations for

        Returns:
            Optional[Union[U, List[U]]]: Related data or None
            - For AsyncBelongsTo/AsyncHasOne: returns a single related model instance or None
            - For AsyncHasMany: returns a list of related model instances or empty list
        """
        # Use descriptor's log method if available
        if hasattr(self.descriptor, 'log'):
            self.descriptor.log(logging.DEBUG,
                                f"Loading async relation `{self.descriptor.name}` for instance `{type(instance).__name__}`")

        # Delegate to batch_load for consistency
        result = await self.batch_load([instance], None)
        return result.get(id(instance))

    async def batch_load(self, instances: List[Any], base_query: Optional[IAsyncActiveQuery]) -> Dict[int, Any]:
        """
        Batch load relations for multiple instances efficiently.

        This method implements the core optimization for avoiding N+1 query problems.
        It loads all related records for the given instances in a single or minimal
        number of database queries, then distributes the results to the appropriate
        instances. The method handles the differences between AsyncBelongsTo (many-to-one),
        AsyncHasOne (one-to-one), and AsyncHasMany (one-to-many) relationships appropriately.

        Args:
            instances: List of model instances to load relations for
            base_query: Pre-configured query with potential filters from with_() configurations
                       or None to create a new query

        Returns:
            Dict mapping instance IDs (using id() function) to their related data
            - For AsyncBelongsTo/AsyncHasOne: each value is a single related model instance or None
            - For AsyncHasMany: each value is a list of related model instances

        Example:
            # Efficiently load comments for multiple posts in a single query
            posts = await Post.find([1, 2, 3])
            # Instead of executing 3 separate queries (N+1 problem),
            # this method will execute 1 query to fetch all related comments
            comments_by_post = await AsyncDefaultRelationLoader(post_comments_descriptor).batch_load(posts, None)
        """
        if not instances:
            return {}

        if self._cached_model is None:
            model_class = self.descriptor.get_related_model(type(instances[0]))
            self._cached_model = model_class

        model_class = self._cached_model

        # Use provided base_query or create new one
        query = base_query if base_query is not None else model_class.query()

        result = {}
        if isinstance(self.descriptor, AsyncBelongsTo):
            # Collect unique foreign keys
            foreign_keys = {
                getattr(instance, self.descriptor.foreign_key)
                for instance in instances
                if hasattr(instance, self.descriptor.foreign_key)
                   and getattr(instance, self.descriptor.foreign_key) is not None
            }

            if not foreign_keys:
                return result

            # Load all related records using base_query with new expression system
            from ..backend.expression import Column, Literal, InPredicate

            # Create IN predicate using expression system
            pk_column = Column(query.backend().dialect, model_class.primary_key())
            # Create a literal with the list of foreign keys
            values_literal = Literal(query.backend().dialect, list(foreign_keys))
            in_predicate = InPredicate(query.backend().dialect, pk_column, values_literal)

            # Get the SQL to see what's generated
            query._log(logging.DEBUG, f"Async batch load SQL: {query.where(in_predicate).to_sql()}")

            related_records = await query.all()

            # Build lookup map
            related_map = {
                getattr(record, model_class.primary_key()): record
                for record in related_records
            }

            # Map results to instance IDs
            for instance in instances:
                fk_value = getattr(instance, self.descriptor.foreign_key, None)
                if fk_value is not None and fk_value in related_map:
                    result[id(instance)] = related_map[fk_value]

        else:  # HasOne or HasMany
            # Collect primary keys
            primary_keys = {
                getattr(instance, instance.primary_key())
                for instance in instances
                if hasattr(instance, 'primary_key')
                   and getattr(instance, instance.primary_key()) is not None
            }

            if not primary_keys:
                # Return empty list for HasMany, None for HasOne for all instances
                return {
                    id(instance): [] if isinstance(self.descriptor, AsyncHasMany) else None
                    for instance in instances
                }

            # Load all related records using base_query with new expression system
            # Keep existing conditions from base_query, only add IN condition
            # Create a clone of the query to avoid modifying the original
            if hasattr(query, 'clone'):
                query = query.clone()

            from ..backend.expression import Column, Literal, InPredicate

            # Create IN predicate using expression system
            fk_column = Column(query.backend().dialect, self.descriptor.foreign_key)
            # Create a literal with the list of primary keys
            values_literal = Literal(query.backend().dialect, list(primary_keys))
            in_predicate = InPredicate(query.backend().dialect, fk_column, values_literal)

            # Get the SQL to see what's generated
            query._log(logging.DEBUG, f"Async batch load SQL: {query.where(in_predicate).to_sql()}")

            related_records = await query.all()

            # Group by foreign key
            related_map: Dict[Any, List[Any]] = {}
            for record in related_records:
                fk_value = getattr(record, self.descriptor.foreign_key)
                if fk_value not in related_map:
                    related_map[fk_value] = []
                related_map[fk_value].append(record)

            # Map results to instance IDs, ensuring proper empty results
            for instance in instances:
                pk_value = getattr(instance, instance.primary_key(), None)
                if pk_value is not None:
                    related_data = related_map.get(pk_value, [])
                    if isinstance(self.descriptor, AsyncHasOne):
                        # For AsyncHasOne, take first record if any exists
                        related_data = related_data[0] if related_data else None
                    result[id(instance)] = related_data
                else:
                    # No primary key means no relations
                    result[id(instance)] = [] if isinstance(self.descriptor, AsyncHasMany) else None

        return result


class AsyncBelongsTo(AsyncRelationDescriptor[U], Generic[U]):
    """
    Defines an AsyncBelongsTo relationship (many-to-one or one-to-one).

    This relationship type indicates that the async model instance 'belongs to' another async model
    instance. For example, an AsyncComment belongsTo an AsyncPost. The foreign key is stored on
    the model that has the AsyncBelongsTo relationship.

    Characteristics:
    - The foreign key is stored in the model that defines the AsyncBelongsTo relationship
    - Returns a single related model instance (not a collection)
    - Common examples: AsyncComment belongsTo AsyncPost, AsyncEmployee belongsTo AsyncDepartment

    Usage:
        class AsyncComment(AsyncActiveRecord):
            id: int
            content: str
            post_id: int  # Foreign key

            # IMPORTANT: Relationship fields must be declared as ClassVar to avoid being tracked by Pydantic
            # AsyncComment belongs to an AsyncPost
            post: ClassVar[AsyncBelongsTo['AsyncPost']] = AsyncBelongsTo(foreign_key='post_id', inverse_of='comments')

        class AsyncPost(AsyncActiveRecord):
            id: int
            title: str

            # IMPORTANT: Relationship fields must be declared as ClassVar to avoid being tracked by Pydantic
            # AsyncPost has many AsyncComments (inverse relationship)
            comments: ClassVar[AsyncHasMany['AsyncComment']] = AsyncHasMany(foreign_key='post_id', inverse_of='post')

        # Access the related model
        comment = await AsyncComment.find(1)
        post = await comment.post()  # Returns the related AsyncPost instance
    """

    def __init__(self, *args, **kwargs):
        """
        Initialize an AsyncBelongsTo relationship with automatic validation.

        The AsyncBelongsTo relationship automatically registers an AsyncRelationshipValidator
        to ensure the relationship is properly defined and matches with an inverse
        relationship on the related model.

        Args:
            *args: Arguments passed to parent constructor
            **kwargs: Keyword arguments passed to parent constructor
        """
        super().__init__(*args, validator=AsyncRelationshipValidator(self), **kwargs)


class AsyncHasOne(AsyncRelationDescriptor[U], Generic[U]):
    """
    Defines an AsyncHasOne relationship (one-to-one).

    This relationship type indicates that the async model instance 'has one' related instance.
    For example, an AsyncUser hasOne AsyncProfile. The foreign key is typically stored on the
    related model (the 'one' side).

    Characteristics:
    - The foreign key is stored in the related model
    - Returns a single related model instance (not a collection)
    - Common examples: AsyncUser hasOne AsyncProfile, AsyncOrder hasOne AsyncInvoice

    Usage:
        class AsyncUser(AsyncActiveRecord):
            id: int
            name: str

            # IMPORTANT: Relationship fields must be declared as ClassVar to avoid being tracked by Pydantic
            # AsyncUser has one AsyncProfile
            profile: ClassVar[AsyncHasOne['AsyncProfile']] = AsyncHasOne(foreign_key='user_id', inverse_of='user')

        class AsyncProfile(AsyncActiveRecord):
            id: int
            bio: str
            user_id: int  # Foreign key

            # IMPORTANT: Relationship fields must be declared as ClassVar to avoid being tracked by Pydantic
            # AsyncProfile belongs to an AsyncUser (inverse relationship)
            user: ClassVar[AsyncBelongsTo['AsyncUser']] = AsyncBelongsTo(foreign_key='user_id', inverse_of='profile')

        # Access the related model
        user = await AsyncUser.find(1)
        profile = await user.profile()  # Returns the related AsyncProfile instance
    """

    def __init__(self, *args, **kwargs):
        """
        Initialize an AsyncHasOne relationship with automatic validation.

        The AsyncHasOne relationship automatically registers an AsyncRelationshipValidator
        to ensure the relationship is properly defined and matches with an inverse
        relationship on the related model.

        Args:
            *args: Arguments passed to parent constructor
            **kwargs: Keyword arguments passed to parent constructor
        """
        super().__init__(*args, validator=AsyncRelationshipValidator(self), **kwargs)


class AsyncHasMany(AsyncRelationDescriptor[U], Generic[U]):
    """
    Defines an AsyncHasMany relationship (one-to-many).

    This relationship type indicates that the async model instance 'has many' related instances.
    For example, an AsyncUser hasMany AsyncPosts. The foreign key is stored on the related model (the 'many' side).

    Characteristics:
    - The foreign key is stored in the related model
    - Returns a list of related model instances
    - Common examples: AsyncUser hasMany AsyncPosts, AsyncCategory hasMany AsyncProducts

    Usage:
        class AsyncUser(AsyncActiveRecord):
            id: int
            name: str

            # IMPORTANT: Relationship fields must be declared as ClassVar to avoid being tracked by Pydantic
            # AsyncUser has many AsyncPosts
            posts: ClassVar[AsyncHasMany['AsyncPost']] = AsyncHasMany(foreign_key='user_id', inverse_of='user')

        class AsyncPost(AsyncActiveRecord):
            id: int
            title: str
            user_id: int  # Foreign key

            # IMPORTANT: Relationship fields must be declared as ClassVar to avoid being tracked by Pydantic
            # AsyncPost belongs to an AsyncUser (inverse relationship)
            user: ClassVar[AsyncBelongsTo['AsyncUser']] = AsyncBelongsTo(foreign_key='user_id', inverse_of='posts')

        # Access the related models
        user = await AsyncUser.find(1)
        posts = await user.posts()  # Returns a list of related AsyncPost instances
    """

    def __init__(self, *args, **kwargs):
        """
        Initialize an AsyncHasMany relationship with automatic validation.

        The AsyncHasMany relationship automatically registers an AsyncRelationshipValidator
        to ensure the relationship is properly defined and matches with an inverse
        relationship on the related model.

        Args:
            *args: Arguments passed to parent constructor
            **kwargs: Keyword arguments passed to parent constructor
        """
        super().__init__(*args, validator=AsyncRelationshipValidator(self), **kwargs)