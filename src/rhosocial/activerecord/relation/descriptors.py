# src/rhosocial/activerecord/relation/descriptors.py
"""
Concrete relation descriptor implementations.
Provides BelongsTo, HasOne, and HasMany relationship types.
"""

import logging
from typing import Type, Any, Generic, TypeVar, Union, ForwardRef, Optional, get_type_hints, ClassVar, List, cast, Dict

from .cache import CacheConfig, InstanceCache
from .interfaces import RelationValidation, RelationManagementInterface, RelationLoader
from ..base import QueryMixin
from ..interface import IActiveRecord

T = TypeVar('T')


def _evaluate_forward_ref(ref: Union[str, ForwardRef], owner: Type[Any]) -> Type[T]:
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


class RelationDescriptor(Generic[T]):
    """
    Generic descriptor for managing model relations.
    Modified to use instance-level caching for proper isolation.

    The RelationDescriptor serves as the core implementation for all relationship types
    (BelongsTo, HasOne, HasMany). It handles model type resolution, relation validation,
    data loading, and caching. The descriptor follows Python's descriptor protocol to
    provide transparent relation access on model instances.

    Usage:
        # In model definition
        from typing import ClassVar
        from rhosocial.activerecord.relation.descriptors import HasMany, BelongsTo

        class User(ActiveRecord):
            id: int
            name: str

            # IMPORTANT: Relationship fields must be declared as ClassVar to avoid being tracked by Pydantic
            posts: ClassVar[HasMany['Post']] = HasMany(foreign_key='user_id', inverse_of='user')

        class Post(ActiveRecord):
            id: int
            title: str
            user_id: int

            # IMPORTANT: Relationship fields must be declared as ClassVar to avoid being tracked by Pydantic
            user: ClassVar[BelongsTo['User']] = BelongsTo(foreign_key='user_id', inverse_of='posts')

        # At runtime, the relations can be accessed as follows:
        user = User.find(1)
        posts = user.posts()  # Returns list of related Post instances
        post = Post.find(1)
        user = post.user()    # Returns related User instance

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
            loader: Optional[RelationLoader[T]] = None,
            validator: Optional[RelationValidation] = None,
            cache_config: Optional[CacheConfig] = None
    ):
        if type(foreign_key) is not str:
            raise TypeError("foreign_key must be a string")
        self.foreign_key = foreign_key
        self.inverse_of = inverse_of
        self._loader = loader or DefaultRelationLoader(self)
        self._validator = validator
        if cache_config is not None and not isinstance(cache_config, CacheConfig):
            raise TypeError("cache_config must be instance of CacheConfig")
        self._cache_config = cache_config or CacheConfig()
        self._cached_model: Optional[Type[T]] = None
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

    def __set_name__(self, owner: Type[RelationManagementInterface], name: str) -> None:
        """
        Called when the descriptor is assigned to a class attribute during class creation.

        This method implements the descriptor protocol and is automatically called when
        a RelationDescriptor is assigned as a class attribute. It performs the following:
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

        self.log(logging.DEBUG, f"Registering relation `{name}` with `{owner.__name__}`")
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
        self.log(logging.DEBUG, f"Getting `{self.name}` relation for {owner.__name__ if owner else 'None'}")
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

    def get_related_model(self, owner: Type[Any]) -> Type[T]:
        """
        Get related model class, resolving if needed.

        Args:
            owner: Owner model class

        Returns:
            Type[T]: Related model class

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

    def _resolve_model(self, owner: Type[Any]) -> Union[Type[T], ForwardRef, str]:
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
        self.log(logging.DEBUG, f"Creating relation method for `{self.name}`")

        def relation_method(*args, **kwargs):
            if args or kwargs:
                return self._query.query(instance, *args, **kwargs) if self._query else None
            return self._load_relation(instance)

        relation_method.clear_cache = lambda: self._cache.delete(instance)
        return relation_method

    def _create_query_method(self):
        """
        Creates a dynamic query method for the relation that returns a preconfigured query.

        This method creates a query method that is attached to the model class during
        class creation. The query is preconfigured with the appropriate foreign key
        conditions based on the relationship type (BelongsTo vs HasOne/HasMany).

        Returns:
            A callable method that takes an instance and returns a preconfigured query
        """
        self.log(logging.DEBUG, f"Creating query method for `{self.name}`")

        def query_method(instance):
            # Force model resolution if needed
            related_model = self.get_related_model(type(instance))
            # Start with base query for the related model
            query = related_model.query()

            # Add appropriate foreign key condition based on relationship type
            if isinstance(self, BelongsTo):
                # For BelongsTo, filter by primary key matching our foreign key
                if hasattr(instance, self.foreign_key):
                    fk_value = getattr(instance, self.foreign_key)
                    if fk_value is not None:
                        query = query.where(
                            f"{related_model.primary_key()} = ?",
                            (fk_value,)
                        )
            else:
                # For HasOne/HasMany, filter by foreign key matching our primary key
                pk_value = getattr(instance, instance.primary_key())
                if pk_value is not None:
                    query = query.where(
                        f"{self.foreign_key} = ?",
                        (pk_value,)
                    )

            return query

        return query_method

    def _load_relation(self, instance: Any) -> Optional[T]:
        """
        Loads the related data for a specific instance with caching support.

        This method implements the lazy-loading behavior for relations. It first checks
        the instance-level cache, and if not found, delegates to the relation loader
        to fetch the data from the database. The loaded data is then cached for future
        access.

        Args:
            instance: The model instance for which to load the related data

        Returns:
            Optional[T]: The related model instance(s) or None if not found
        """
        if self._cached_model is None:
            self.get_related_model(type(instance))

        cached = InstanceCache.get(instance, self.name, self._cache_config)
        if cached is not None:
            self.log(logging.DEBUG, f"Using cached relation for `{self.name}`")
            return cached

        try:
            self.log(logging.DEBUG, f"Loading relation `{self.name}` for {type(instance).__name__}")
            data = self._loader.load(instance) if self._loader else None
            InstanceCache.set(instance, self.name, data, self._cache_config)
            return data
        except Exception as e:
            self.log(logging.ERROR, f"Error loading relation: {e}")
            return None

    def batch_load(self, records: List[Any], base_query: Any) -> Dict[int, Any]:
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
        self.log(logging.DEBUG, f"Batch loading `{self.name}` relation for {len(records)} records")
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
            loaded_data = self._loader.batch_load(records_to_load, base_query)
            if loaded_data:
                # Cache and add to result
                for record_id, data in loaded_data.items():
                    for record in records_to_load:
                        if id(record) == record_id:
                            InstanceCache.set(record, self.name, data, self._cache_config)
                            break
                result.update(loaded_data)
        except Exception as e:
            self.log(logging.ERROR, f"Error in batch loading `{self.name}` relations: {e}")

        return result


class RelationshipValidator(RelationValidation):
    """Default relationship validator implementation."""

    def __init__(self, descriptor: RelationDescriptor):
        """
        Initialize validator with descriptor reference.

        Args:
            descriptor: The RelationDescriptor instance being validated
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
        if not isinstance(inverse_rel, RelationDescriptor):
            raise ValueError(
                f"Inverse relationship '{self.descriptor.inverse_of}' in "
                f"{related_name} must be a RelationDescriptor"
            )

        # Check for valid relationship pairs
        valid_pairs = [
            (BelongsTo, HasOne),
            (BelongsTo, HasMany),
            (HasOne, BelongsTo),
            (HasMany, BelongsTo),
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


class BelongsTo(RelationDescriptor[T], Generic[T]):
    """
    Defines a BelongsTo relationship (many-to-one or one-to-one).

    This relationship type indicates that the model instance 'belongs to' another model
    instance. For example, a Comment belongsTo a Post. The foreign key is stored on
    the model that has the BelongsTo relationship.

    Characteristics:
    - The foreign key is stored in the model that defines the BelongsTo relationship
    - Returns a single related model instance (not a collection)
    - Common examples: Comment belongsTo Post, Employee belongsTo Department

    Usage:
        class Comment(ActiveRecord):
            id: int
            content: str
            post_id: int  # Foreign key

            # IMPORTANT: Relationship fields must be declared as ClassVar to avoid being tracked by Pydantic
            # Comment belongs to a Post
            post: ClassVar[BelongsTo['Post']] = BelongsTo(foreign_key='post_id', inverse_of='comments')

        class Post(ActiveRecord):
            id: int
            title: str

            # IMPORTANT: Relationship fields must be declared as ClassVar to avoid being tracked by Pydantic
            # Post has many Comments (inverse relationship)
            comments: ClassVar[HasMany['Comment']] = HasMany(foreign_key='post_id', inverse_of='post')

        # Access the related model
        comment = Comment.find(1)
        post = comment.post()  # Returns the related Post instance
    """

    def __init__(self, *args, **kwargs):
        """
        Initialize a BelongsTo relationship with automatic validation.

        The BelongsTo relationship automatically registers a RelationshipValidator
        to ensure the relationship is properly defined and matches with an inverse
        relationship on the related model.

        Args:
            *args: Arguments passed to parent constructor
            **kwargs: Keyword arguments passed to parent constructor
        """
        super().__init__(*args, validator=RelationshipValidator(self), **kwargs)


class HasOne(RelationDescriptor[T], Generic[T]):
    """
    Defines a HasOne relationship (one-to-one).

    This relationship type indicates that the model instance 'has one' related instance.
    For example, a User hasOne Profile. The foreign key is typically stored on the
    related model (the 'one' side).

    Characteristics:
    - The foreign key is stored in the related model
    - Returns a single related model instance (not a collection)
    - Common examples: User hasOne Profile, Order hasOne Invoice

    Usage:
        class User(ActiveRecord):
            id: int
            name: str

            # IMPORTANT: Relationship fields must be declared as ClassVar to avoid being tracked by Pydantic
            # User has one Profile
            profile: ClassVar[HasOne['Profile']] = HasOne(foreign_key='user_id', inverse_of='user')

        class Profile(ActiveRecord):
            id: int
            bio: str
            user_id: int  # Foreign key

            # IMPORTANT: Relationship fields must be declared as ClassVar to avoid being tracked by Pydantic
            # Profile belongs to a User (inverse relationship)
            user: ClassVar[BelongsTo['User']] = BelongsTo(foreign_key='user_id', inverse_of='profile')

        # Access the related model
        user = User.find(1)
        profile = user.profile()  # Returns the related Profile instance
    """

    def __init__(self, *args, **kwargs):
        """
        Initialize a HasOne relationship with automatic validation.

        The HasOne relationship automatically registers a RelationshipValidator
        to ensure the relationship is properly defined and matches with an inverse
        relationship on the related model.

        Args:
            *args: Arguments passed to parent constructor
            **kwargs: Keyword arguments passed to parent constructor
        """
        super().__init__(*args, validator=RelationshipValidator(self), **kwargs)


class HasMany(RelationDescriptor[T], Generic[T]):
    """
    Defines a HasMany relationship (one-to-many).

    This relationship type indicates that the model instance 'has many' related instances.
    For example, a Post hasMany Comments. The foreign key is stored on the related models.

    Characteristics:
    - The foreign key is stored in the related models
    - Returns a collection of related model instances
    - Common examples: Post hasMany Comments, User hasMany Orders

    Usage:
        class Post(ActiveRecord):
            id: int
            title: str

            # IMPORTANT: Relationship fields must be declared as ClassVar to avoid being tracked by Pydantic
            # Post has many Comments
            comments: ClassVar[HasMany['Comment']] = HasMany(foreign_key='post_id', inverse_of='post')

        class Comment(ActiveRecord):
            id: int
            content: str
            post_id: int  # Foreign key

            # IMPORTANT: Relationship fields must be declared as ClassVar to avoid being tracked by Pydantic
            # Comment belongs to a Post (inverse relationship)
            post: ClassVar[BelongsTo['Post']] = BelongsTo(foreign_key='post_id', inverse_of='comments')

        # Access the related models
        post = Post.find(1)
        comments = post.comments()  # Returns list of related Comment instances
    """

    def __init__(self, *args, **kwargs):
        """
        Initialize a HasMany relationship with automatic validation.

        The HasMany relationship automatically registers a RelationshipValidator
        to ensure the relationship is properly defined and matches with an inverse
        relationship on the related model.

        Args:
            *args: Arguments passed to parent constructor
            **kwargs: Keyword arguments passed to parent constructor
        """
        super().__init__(*args, validator=RelationshipValidator(self), **kwargs)


R = TypeVar('R', bound=Union[IActiveRecord, QueryMixin])


class DefaultRelationLoader(RelationLoader[R]):
    """
    Default implementation of relation loading logic.

    This class implements the standard algorithm for loading related data. It handles
    the differences between relationship types (BelongsTo vs HasOne vs HasMany) and
    implements efficient batch loading strategies to minimize database queries.

    The loader is responsible for:
    1. Determining the appropriate query conditions based on the relationship type
    2. Executing the database query to fetch related records
    3. Handling the differences between single-object (BelongsTo/HasOne) and
       multi-object (HasMany) relationships
    4. Implementing batch loading to avoid N+1 query problems
    """

    def __init__(self, descriptor: RelationDescriptor):
        """
        Initializes the loader with a reference to its descriptor.

        Args:
            descriptor: The RelationDescriptor that owns this loader and defines
                       the relationship characteristics (foreign key, relationship type, etc.)
        """
        self.descriptor = descriptor
        self._cached_model: Optional[Type[R]] = None

    def load(self, instance: Any) -> Optional[Union[R, List[R]]]:
        """
        Load relation for a single instance.

        This method provides a single-instance loading interface that delegates
        to the more efficient batch_load method for consistency.

        Args:
            instance: The model instance to load relations for

        Returns:
            Optional[Union[R, List[R]]]: Related data or None
            - For BelongsTo/HasOne: returns a single related model instance or None
            - For HasMany: returns a list of related model instances or empty list
        """
        # Use descriptor's log method if available
        if hasattr(self.descriptor, 'log'):
            self.descriptor.log(logging.DEBUG,
                                f"Loading relation `{self.descriptor.name}` for instance `{type(instance).__name__}`")

        # Delegate to batch_load for consistency
        result = self.batch_load([instance], None)
        return result.get(id(instance))

    def batch_load(self, instances: List[Any], base_query: Optional['IQuery']) -> Dict[int, Any]:
        """
        Batch load relations for multiple instances efficiently.

        This method implements the core optimization for avoiding N+1 query problems.
        It loads all related records for the given instances in a single or minimal
        number of database queries, then distributes the results to the appropriate
        instances. The method handles the differences between BelongsTo (many-to-one),
        HasOne (one-to-one), and HasMany (one-to-many) relationships appropriately.

        Args:
            instances: List of model instances to load relations for
            base_query: Pre-configured query with potential filters from with_() configurations
                       or None to create a new query

        Returns:
            Dict mapping instance IDs (using id() function) to their related data
            - For BelongsTo/HasOne: each value is a single related model instance or None
            - For HasMany: each value is a list of related model instances

        Example:
            # Efficiently load comments for multiple posts in a single query
            posts = Post.find([1, 2, 3])
            # Instead of executing 3 separate queries (N+1 problem),
            # this method will execute 1 query to fetch all related comments
            comments_by_post = DefaultRelationLoader(post_comments_descriptor).batch_load(posts, None)
        """
        if not instances:
            return {}

        if self._cached_model is None:
            model_class = self.descriptor.get_related_model(type(instances[0]))
            self._cached_model = model_class

        model_class = cast(Type[Union[IActiveRecord, QueryMixin]], self._cached_model)

        # Use provided base_query or create new one
        query = base_query if base_query is not None else model_class.query()

        result = {}
        if isinstance(self.descriptor, BelongsTo):
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
            query._log(logging.DEBUG, f"Batch load SQL: {query.where(in_predicate).to_sql()}")

            related_records = query.all()

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
                    id(instance): [] if isinstance(self.descriptor, HasMany) else None
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
            query._log(logging.DEBUG, f"Batch load SQL: {query.where(in_predicate).to_sql()}")

            related_records = query.all()

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
                    if isinstance(self.descriptor, HasOne):
                        # For HasOne, take first record if any exists
                        related_data = related_data[0] if related_data else None
                    result[id(instance)] = related_data
                else:
                    # No primary key means no relations
                    result[id(instance)] = [] if isinstance(self.descriptor, HasMany) else None

        return result

