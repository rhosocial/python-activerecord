"""Relational query methods implementation."""
import logging
from dataclasses import dataclass
from threading import local
from typing import Dict, TypeVar, Iterator, Any, Optional, Tuple, List, Mapping, KeysView, ValuesView, ItemsView, \
    Callable, Union, Type

from ..interface import ModelT, IQuery
from ..interface.query import ThreadSafeDict


@dataclass
class RelationConfig:
    """Configuration for relation loading."""
    name: str  # Base relation name
    nested: List[str]  # Nested relation parts
    query_modifier: Optional[Callable] = None  # Query modification function



class RelationalQueryMixin(IQuery[ModelT]):
    """Query methods for eager loading model relationships.

    This mixin adds the ability to eagerly load model relationships during queries.
    It maintains the configuration for which relations should be loaded and how
    they should be loaded.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Stores relation loading configurations by relation path
        self._eager_loads: ThreadSafeDict[str, RelationConfig] = ThreadSafeDict()
        # self._eager_loads: Dict[str, RelationConfig] = {}
        # Cache for loaded relation data, keyed by relation path and record id
        self._loaded_relations: ThreadSafeDict[str, ThreadSafeDict[int, Any]] = ThreadSafeDict()

    def with_(self, *relations: Union[str, tuple]) -> 'IQuery[ModelT]':
        """Configure eager loading for model relationships. This method allows specifying which relations
        should be loaded along with the main query results, optimizing database queries by reducing N+1 problems.

        The method supports:
        1. Simple relation loading: Load a direct relation
        2. Nested relation loading: Load relations of relations using dot notation
        3. Query modification: Customize how relations are loaded using modifier functions
        4. Multiple relation loading: Load several relations at once
        5. Chainable calls: Build relation loading incrementally

        Args:
            *relations: Variable length argument that accepts either:
                - strings: Relation paths using dot notation for nesting (e.g., "user", "user.posts")
                - tuples: Pairs of (relation_path, query_modifier) where query_modifier is a callable
                  that customizes the relation query

        Returns:
            IQuery[ModelT]: The current query instance with updated eager loading configuration

        Examples:
            # Load a single relation
            Order.query().with_("user")

            # Load nested relations
            Order.query().with_("user.posts.comments")

            # Load relation with query modification
            Order.query().with_(
                ("user", lambda q: q.where("active = ?", True))
            )

            # Load multiple relations
            Order.query().with_("user", "items", "user.posts")

            # Chain multiple with_ calls
            Order.query()\\
                .with_("user")\\
                .with_("items")\\
                .with_("user.posts")

        Implementation notes:
            - Relations are stored in _eager_loads as RelationConfig objects
            - Nested relations are processed by splitting paths and creating configs for each level
            - Duplicate relations are handled by updating existing configs
            - Query modifiers are only applied to the specified relation level
        """
        for relation in relations:
            # Handle both simple string relations and tuple relations with query modifiers
            if isinstance(relation, tuple):
                relation_path, query_modifier = relation
            else:
                relation_path, query_modifier = relation, None

            # Split the relation path into individual parts
            # For example, "user.posts.comments" becomes ["user", "posts", "comments"]
            parts = relation_path.split('.')
            current_path = []

            # Iterate through each part of the relation path to build configurations
            # at each nesting level
            for i, part in enumerate(parts):
                current_path.append(part)
                # Join the current path parts to form the full relation path at this level
                # e.g., ["user", "posts"] becomes "user.posts"
                full_path = '.'.join(current_path)

                # Determine what relations should be loaded at the next level
                # For "user.posts.comments", when processing "user", next_level would be ["posts"]
                remaining_parts = parts[i + 1:]
                next_level = remaining_parts[:1]

                if full_path in self._eager_loads:
                    # Update existing relation configuration
                    existing = self._eager_loads[full_path]

                    # Add any new nested relations that aren't already configured
                    # This prevents duplicate nested relations while allowing multiple
                    # calls to with_() to add different nested relations
                    for next_part in next_level:
                        if next_part not in existing.nested:
                            existing.nested.append(next_part)

                    # Update query modifier only if this is the targeted relation level
                    # This ensures modifiers are applied only to their specific relation,
                    # not to intermediate relations in a nested path
                    if full_path == relation_path and query_modifier is not None:
                        existing.query_modifier = query_modifier
                else:
                    # Create new relation configuration
                    # Only apply query modifier if this is the specifically targeted relation,
                    # not an intermediate relation in a nested path
                    self._add_relation_config(full_path, next_level,
                                              query_modifier if full_path == relation_path else None)

        return self

    def _add_relation_config(self, relation: str, nested: List[str], query_modifier: Optional[Callable]) -> None:
        """Add or update relation configuration.

        Internal method to manage the eager loading configuration storage.

        Args:
            relation: The current relation path
            nested: The remaining parts of the relation path
            query_modifier: Optional query modifier function
        """
        self._eager_loads[relation] = RelationConfig(
            name=relation,
            nested=nested,
            query_modifier=query_modifier
        )

    def _load_relations(self, records: List[ModelT]) -> None:
        """Main entry point for loading relations for a set of records.

        Orchestrates the loading of all configured relations, ensuring they are
        loaded in the correct order (by nesting depth).

        Args:
            records: List of model instances to load relations for
        """
        if not records or not self._eager_loads:
            return

        self._log(logging.INFO, f"Loading eager relations: {self._eager_loads.keys()}...")

        # Sort relations by nesting depth for proper loading order
        sorted_relations = sorted(
            self._eager_loads.items(),
            key=lambda x: len(x[0].split('.'))
        )

        for relation_name, config in sorted_relations:
            self._load_single_relation(records, relation_name, config)

        self._log(logging.INFO, f"Loading eager relations: {self._eager_loads.keys()}...finished.")

    def _load_single_relation(self, records: List[ModelT], relation_name: str, config: RelationConfig) -> None:
        """Load a single relation for all records.

        Handles the complete process of loading one relation, including:
        - Setting up cache
        - Getting relation metadata
        - Loading related records
        - Processing nested relations

        Args:
            records: List of parent records to load relation for
            relation_name: Name/path of the relation to load
            config: Configuration for the relation loading
        """
        # Initialize relation cache if needed
        self._log(logging.INFO, f"Loading relation: {relation_name}, config: {config}")
        if relation_name not in self._loaded_relations:
            self._loaded_relations[relation_name] = ThreadSafeDict()

        # Get relation descriptor
        relation = self._get_relation(relation_name)
        if not relation:
            self._log(logging.WARNING, f"relation name {relation_name} not found in {self.__class__.__name__}")
            return

        # Get related model class
        related_model = relation.get_related_model(self.model_class)
        if not related_model:
            self._log(logging.WARNING, f"related model {self.model_class} not found")
            return

        # Create base query and apply modifier if configured
        base_query = self._create_base_query(related_model, config)
        if not base_query:
            return

        # Delegate batch loading to relation descriptor
        loaded_data = relation.batch_load(records, base_query)

        # Get record IDs that should have relations
        record_ids = {record.id for record in records}

        # Clear cache for records that no longer have relations
        if relation_name in self._loaded_relations:
            cache = self._loaded_relations[relation_name]
            for record_id in record_ids:
                if record_id in cache and (not loaded_data or record_id not in loaded_data):
                    del cache[record_id]
                    self._log(logging.DEBUG, f"Cleared cached relation {relation_name} for record {record_id}")

        # Update cache with new data
        if loaded_data:
            for record_id, related_data in loaded_data.items():
                self._loaded_relations[relation_name][record_id] = related_data

            # Handle nested relations
            self._process_nested_relations(loaded_data, config, related_model)

    def _get_relation(self, relation_name: str) -> Optional[Any]:
        """Get relation descriptor by name."""
        if not hasattr(self.model_class, 'get_relation'):
            return None

        base_relation = relation_name.split('.')[0]
        return self.model_class.get_relation(base_relation)

    def _create_base_query(self, related_model: Type[ModelT], config: RelationConfig) -> Optional['IQuery[ModelT]']:
        """Create and configure base query for related records.

        Creates a query for the related model and applies any configured modifiers.

        Args:
            related_model: Model class for the related records
            config: Configuration containing optional query modifier

        Returns:
            Configured query instance or None if creation fails
        """
        if not hasattr(related_model, 'query'):
            return None

        base_query = related_model.query()
        if config.query_modifier:
            base_query = config.query_modifier(base_query)
        return base_query

    def _process_nested_relations(
            self,
            loaded_data: Dict[int, Any],
            config: RelationConfig,
            related_model: Type[ModelT]
    ) -> None:
        """Process nested relations if any exist.

        Handles the loading of nested relations by:
        1. Collecting all loaded related records
        2. Creating a new query for the nested relations
        3. Recursively loading the nested relations

        Args:
            loaded_data: <TODO>
            config: Configuration containing nested relations info
            related_model: Model class for the current relation
        """
        if not config.nested or not loaded_data:
            return

        # Collect all loaded records
        loaded_records = []
        for data in loaded_data.values():
            if isinstance(data, list):
                loaded_records.extend(data)
            else:
                loaded_records.append(data)

        # Collect all loaded related records
        if loaded_records:
            # Create query for nested relations
            next_query = related_model.query()
            nested_relations = ['.'.join(config.nested)]
            next_query.with_(*nested_relations)
            # Load nested relations
            next_query._load_relations(loaded_records)
