"""
Concrete relation descriptor implementations.
Provides BelongsTo, HasOne, and HasMany relationship types.
"""

from typing import Type, Any, Generic, TypeVar, Union, ForwardRef, Optional, get_type_hints, ClassVar, List, cast, Dict

from .cache import RelationCache, CacheConfig
from .interfaces import RelationValidation, RelationManagementInterface, RelationLoader
from .. import QueryMixin
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
        try:
            return ref._evaluate(context, None, recursive_guard=set())
        except TypeError:
            try:
                return ref._evaluate(context, None, set())
            except TypeError:
                pass

    return eval(type_str, context, None)

class RelationDescriptor(Generic[T]):
    """
    Generic descriptor for managing model relations.

    Args:
        foreign_key: Foreign key field name
        inverse_of: Name of inverse relation
        loader: Custom loader implementation
        query: Custom query implementation
        validator: Custom validation implementation
        cache_config: Cache configuration

    Raises:
        ValueError: If inverse relationship validation fails
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
        self._cache = RelationCache(cache_config)
        self._cached_model: Optional[Type[T]] = None

    def __set_name__(self, owner: Type[RelationManagementInterface], name: str) -> None:
        """Set descriptor name and register with owner."""
        self.name = name
        self._cache.relation_name = name

        owner.register_relation(name, self)

        # Create query method that returns QuerySet for the related model
        query_method = self._create_query_method()
        setattr(owner, f"{name}_query", query_method)

    def __get__(self, instance: Any, owner: Optional[Type] = None) -> Any:
        """Get descriptor or create bound method."""
        # print(f"DEBUG: __get__ called for {owner.__name__ if owner else 'None'} with instance {instance}")
        if instance is None:
            return self

        # Force validation on first access
        if self._cached_model is None:
            # print("DEBUG: Forcing model resolution")
            self.get_related_model(owner or type(instance))

        return self._create_relation_method(instance)

    def __delete__(self, instance: Any) -> None:
        """Clear cache on deletion."""
        self._cache.delete(instance)

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
            self._cached_model = self._resolve_model(owner)

            # Ensure model is fully resolved before validation
            if isinstance(self._cached_model, (str, ForwardRef)):
                self._cached_model = _evaluate_forward_ref(self._cached_model, owner)

            if self.inverse_of and self._validator:
                try:
                    self._validate_inverse_relationship(owner)
                except Exception as e:
                    self._cached_model = None
                    raise ValueError(f"Invalid relationship: {str(e)}")

        return self._cached_model

    def _resolve_model(self, owner: Type[Any]) -> Union[Type[T], ForwardRef, str]:
        """
        Resolve model type from annotations, handling both string and ForwardRef.

        Python 3.8+ compatible implementation that properly handles forward references.
        """
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
                    return model_type

        raise ValueError("Unable to resolve relationship model")

    def _validate_inverse_relationship(self, owner: Type[Any]) -> None:
        """
        Validate inverse relationship consistency.

        Raises:
            ValueError: If validation fails
        """
        if self._validator:
            self._validator.validate(owner, self._cached_model)
        # Default validation logic here

    def _create_relation_method(self, instance: Any):
        """Create bound method for accessing relation."""

        def relation_method(*args, **kwargs):
            if args or kwargs:
                return self._query.query(instance, *args, **kwargs) if self._query else None
            return self._load_relation(instance)

        relation_method.clear_cache = lambda: self._cache.delete(instance)
        return relation_method

    def _create_query_method(self):
        """Create query class method."""

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
        Load relation with caching support.

        Returns:
            Optional[T]: Related data or None
        """
        if self._cached_model is None:
            self.get_related_model(type(instance))

        cached = self._cache.get(instance)
        if cached is not None:
            return cached

        try:
            data = self._loader.load(instance) if self._loader else None
            self._cache.set(instance, data)
            return data
        except Exception as e:
            print(f"Error loading relation: {e}")
            return None

    def batch_load(self, records: List[Any], base_query: Any) -> Dict[int, Any]:
        """Batch load related records for multiple parent records.

        This method delegates the actual loading to the relation loader
        while providing caching support.

        Args:
            records: List of parent records to load relations for
            base_query: Pre-configured query to use for loading

        Returns:
            Dict mapping record IDs to their related data
        """
        if self._cached_model is None:
            self.get_related_model(type(records[0]))

        result = {}
        # Try cache first
        for record in records:
            cached = self._cache.get(record)
            if cached is not None:
                result[id(record)] = cached

        # Get records that need loading
        records_to_load = [
            record for record in records
            if id(record) not in result
        ]

        if not records_to_load:
            return result

        try:
            # Use loader to batch load remaining records
            loaded_data = self._loader.batch_load(records_to_load, base_query)
            if loaded_data:
                # Cache and add to result
                for record_id, data in loaded_data.items():
                    for record in records_to_load:
                        if id(record) == record_id:
                            self._cache.set(record, data)
                            break
                result.update(loaded_data)
        except Exception as e:
            print(f"Error in batch loading: {e}")

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
    One-to-one or many-to-one relationship.
    Instance belongs to a single instance of related model.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, validator=RelationshipValidator(self), **kwargs)

class HasOne(RelationDescriptor[T], Generic[T]):
    """
    One-to-one relationship.
    Instance has one related instance.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, validator=RelationshipValidator(self), **kwargs)

class HasMany(RelationDescriptor[T], Generic[T]):
    """
    One-to-many relationship.
    Instance has multiple related instances.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, validator=RelationshipValidator(self), **kwargs)

R = TypeVar('R', bound=Union[IActiveRecord, QueryMixin])

class DefaultRelationLoader(RelationLoader[R]):
    """Default implementation of relation loading logic."""

    def __init__(self, descriptor: RelationDescriptor):
        self.descriptor = descriptor
        self._cached_model: Optional[Type[R]] = None

    # [deprecated]
    def __load(self, instance: Any) -> Optional[Union[R, List[R]]]:

        if self._cached_model is None:
            model_class = self.descriptor.get_related_model(type(instance))
            self._cached_model = model_class

        model_class = cast(Type[Union[IActiveRecord, QueryMixin]], self._cached_model)

        if isinstance(self.descriptor, BelongsTo):
            if not hasattr(instance, self.descriptor.foreign_key):
                raise ValueError(f"Missing foreign key: {self.descriptor.foreign_key}")
            foreign_key_value = getattr(instance, self.descriptor.foreign_key)
            if foreign_key_value is None:
                return None

            return model_class.query().where(
                f"{model_class.primary_key()} = ?",
                (foreign_key_value,)
            ).one()

        elif isinstance(self.descriptor, (HasOne, HasMany)):
            primary_key_value = getattr(instance, instance.primary_key())
            if primary_key_value is None:
                return [] if isinstance(self.descriptor, HasMany) else None

            query = model_class.query().where(
                f"{self.descriptor.foreign_key} = ?",
                (primary_key_value,)
            )

            conditions = getattr(self.descriptor, 'conditions', {})
            for condition, value in conditions.items():
                query = query.where(condition, (value,))

            order_by = getattr(self.descriptor, 'order_by', None)
            if order_by:
                if isinstance(order_by, str):
                    query = query.order_by(order_by)
                elif isinstance(order_by, list):
                    query = query.order_by(*order_by)
                else:
                    raise ValueError("Invalid order_by conditions")

            return query.one() if isinstance(self.descriptor, HasOne) else query.all()

        return None

    def load(self, instance: Any) -> Optional[Union[R, List[R]]]:
        """Load relation for a single instance."""
        # Delegate to batch_load for consistency
        result = self.batch_load([instance], None)
        return result.get(id(instance))

    def batch_load(self, instances: List[Any], base_query: Optional['IQuery']) -> Dict[int, Any]:
        """Batch load relations for multiple instances.

        Uses the provided base_query if available, otherwise creates a new one.
        The base_query may contain conditions from with_() configurations.

        Args:
            instances: List of model instances to load relations for
            base_query: Pre-configured query with conditions from with_()

        Returns:
            Dict mapping instance IDs to their related data
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

            # Load all related records using base_query
            related_records = query.where(
                f"{model_class.primary_key()} IN ({','.join('?' * len(foreign_keys))})",
                list(foreign_keys)
            ).all()

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

            # Load all related records using base_query
            related_records = query.where(
                f"{self.descriptor.foreign_key} IN ({','.join('?' * len(primary_keys))})",
                list(primary_keys)
            ).all()

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
                        related_data = related_data[0] if related_data else None
                    result[id(instance)] = related_data
                else:
                    result[id(instance)] = [] if isinstance(self.descriptor, HasMany) else None

        return result