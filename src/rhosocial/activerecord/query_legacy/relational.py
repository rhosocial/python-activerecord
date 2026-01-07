# src/rhosocial/activerecord/query/relational.py
"""Improved relational query methods implementation."""
import logging
from dataclasses import dataclass
from typing import Dict, Any, Optional, List, Callable, Union, Type, Tuple

from ..interface import ModelT, IQuery
from ..interface.query import ThreadSafeDict


class InvalidRelationPathError(Exception):
    """Exception raised when an invalid relation path is provided."""
    pass


class RelationNotFoundError(Exception):
    """Exception raised when a requested relation does not exist on the model."""
    pass


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

    def with_(self, *relations: Union[str, tuple]) -> 'IQuery[ModelT]':
        """Configure eager loading for model relationships.

        This method allows specifying which relations should be loaded along with
        the main query results, optimizing database queries by reducing N+1 problems.

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

        Raises:
            InvalidRelationPathError: If an invalid relation path format is provided
                (e.g., empty string, leading/trailing dots, consecutive dots)
            RelationNotFoundError: If a relation specified in the path does not exist on the model
        """
        # First validate all paths to ensure transactional behavior
        validated_relations = []

        for relation in relations:
            if isinstance(relation, tuple):
                relation_path, query_modifier = relation
            else:
                relation_path, query_modifier = relation, None

            # Validate the path before processing
            try:
                self._validate_relation_path(relation_path)
                # Always validate relation existence
                self._validate_complete_relation_path(relation_path)
                validated_relations.append((relation_path, query_modifier))
            except InvalidRelationPathError as e:
                self._log(logging.ERROR, f"Invalid relation path: {e}")
                raise  # Re-raise after logging, without adding any relations
            except RelationNotFoundError as e:
                self._log(logging.ERROR, f"Relation not found: {e}")
                raise  # Always raise relation not found errors

        # If we get here, all paths are valid, so we can process them
        for relation_path, query_modifier in validated_relations:
            self._process_relation_path(relation_path, query_modifier)

        return self

    def _validate_relation_path(self, relation_path: str) -> None:
        """Validate a relation path format.

        Checks for common issues in relation path format:
        - Empty string
        - Leading/trailing dots
        - Consecutive dots

        Args:
            relation_path: The relation path to validate

        Raises:
            InvalidRelationPathError: If the path format is invalid
        """
        if not relation_path:
            raise InvalidRelationPathError("Relation path cannot be empty")

        if relation_path.startswith('.'):
            raise InvalidRelationPathError(f"Relation path cannot start with a dot: '{relation_path}'")

        if relation_path.endswith('.'):
            raise InvalidRelationPathError(f"Relation path cannot end with a dot: '{relation_path}'")

        if '..' in relation_path:
            raise InvalidRelationPathError(f"Relation path cannot contain consecutive dots: '{relation_path}'")

    def _validate_relation_exists(self, relation_name: str, model_class=None) -> None:
        """Validate that a relation exists on the model.

        Args:
            relation_name: The name of the relation to check
            model_class: The model class to check (defaults to the query's model class)

        Raises:
            RelationNotFoundError: If the relation does not exist on the model
        """
        if model_class is None:
            model_class = self.model_class

        # Check if the relation exists on the model
        if not hasattr(model_class, relation_name) or not hasattr(model_class,
                                                                  'get_relation') or not model_class.get_relation(
            relation_name):
            raise RelationNotFoundError(f"Relation '{relation_name}' not found on {model_class.__name__}")

    def _validate_complete_relation_path(self, relation_path: str) -> None:
        """Validate that all relations in a complete path exist on appropriate models.

        This method traverses the entire relation path, validating each part
        on the correct model class. It handles circular references by properly
        tracking the model class at each step in the chain.

        Args:
            relation_path: The full relation path to validate

        Raises:
            RelationNotFoundError: If any relation in the path does not exist
            on its respective model
        """
        parts = relation_path.split('.')
        current_model_class = self.model_class

        for i, part in enumerate(parts):
            # Validate that this relation exists on the current model
            if not hasattr(current_model_class, part) or not hasattr(current_model_class,
                                                                     'get_relation') or not current_model_class.get_relation(
                part):
                raise RelationNotFoundError(f"Relation '{part}' not found on {current_model_class.__name__}")

            # If not the last part, update the model class for the next iteration
            if i < len(parts) - 1:
                try:
                    relation = current_model_class.get_relation(part)
                    if relation:
                        # Get the related model for the next iteration
                        next_model_class = relation.get_related_model(current_model_class)
                        if next_model_class:
                            current_model_class = next_model_class
                        else:
                            self._log(logging.WARNING,
                                      f"Could not determine related model for relation '{part}' on {current_model_class.__name__}")
                            raise RelationNotFoundError(
                                f"Could not determine related model for relation '{part}' on {current_model_class.__name__}")
                    else:
                        self._log(logging.WARNING,
                                  f"Relation '{part}' not found on {current_model_class.__name__} during model tracking")
                        raise RelationNotFoundError(f"Relation '{part}' not found on {current_model_class.__name__}")
                except Exception as e:
                    if not isinstance(e, RelationNotFoundError):
                        self._log(logging.WARNING, f"Error tracking model class: {e}")
                    raise

    def _update_existing_relation_config(self, path: str, next_level: List[str],
                                         query_modifier: Optional[Callable], is_target_relation: bool) -> None:
        """Update an existing relation configuration.

        Args:
            path: The relation path to update
            next_level: The next level relations to add
            query_modifier: Query modifier to apply (if any)
            is_target_relation: Whether this is the specific target relation
        """
        existing = self._eager_loads[path]

        # Add any new nested relations that aren't already configured
        # This prevents duplicate nested relations while allowing multiple
        # calls to with_() to add different nested relations
        for next_part in next_level:
            if next_part not in existing.nested:
                existing.nested.append(next_part)

        # Update query modifier only if this is the targeted relation level
        # and a modifier was provided or is explicitly set to None
        if is_target_relation:
            # Always update the modifier if this is the target relation,
            # whether it's a new modifier or explicitly None
            existing.query_modifier = query_modifier

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

    def _process_relation_path(self, relation_path: str, query_modifier: Optional[Callable] = None) -> None:
        """Process a relation path and add relation configurations.

        This method handles the traversal of a relation path, generating configurations
        for each part of the path. It ensures proper nesting and handles both direct
        and nested relations, including circular references.

        Args:
            relation_path: The full relation path (e.g., "user.posts.comments")
            query_modifier: Optional query modifier function to apply to the target relation

        Raises:
            InvalidRelationPathError: If the path format is invalid
            RelationNotFoundError: If any relation in the path does not exist
        """
        # Validate the path format first
        self._validate_relation_path(relation_path)

        # Split the relation path into individual parts
        # For example, "user.posts.comments" becomes ["user", "posts", "comments"]
        parts = relation_path.split('.')
        current_path = []

        # Process each part of the path to create configurations
        for i, part in enumerate(parts):
            # Build the current path incrementally
            current_path.append(part)

            # Join the current path parts to form the full relation path at this level
            # e.g., ["user", "posts"] becomes "user.posts"
            full_path = '.'.join(current_path)

            # Determine what relations should be loaded at the next level
            # For "user.posts.comments", when processing "user", next_level would be ["posts"]
            remaining_parts = parts[i + 1:]
            next_level = remaining_parts[:1] if remaining_parts else []

            # Check if this is the exact target relation we want to modify
            is_target_relation = (full_path == relation_path)

            # Apply query modifier only to the target relation, not to intermediate relations
            current_modifier = query_modifier if is_target_relation else None

            if full_path in self._eager_loads:
                # Update existing relation configuration
                self._update_existing_relation_config(full_path, next_level, current_modifier, is_target_relation)
            else:
                # Create new relation configuration
                self._add_relation_config(full_path, next_level, current_modifier)

    def _load_relations(self, records: List[ModelT]) -> None:
        """Main entry point for loading relations for a set of records.

        Orchestrates the loading of all configured relations, ensuring they are
        loaded in the correct order (by nesting depth).

        Args:
            records: List of model instances to load relations for
        """
        if not records or not self._eager_loads:
            return

        self._log(logging.INFO, f"Loading eager relations: {list(self._eager_loads.keys())}...")

        # Sort relations by nesting depth for proper loading order
        sorted_relations = sorted(
            self._eager_loads.items(),
            key=lambda x: len(x[0].split('.'))
        )

        for relation_name, config in sorted_relations:
            try:
                self._load_single_relation(records, relation_name, config)
            except Exception as e:
                self._log(logging.ERROR, f"Error loading relation {relation_name}: {e}")

    def _get_relation(self, relation_name: str, model_class: Type[ModelT] = None) -> Optional[Any]:
        """Get relation descriptor by name.

        Gets the direct relation descriptor for a base relation name.

        Args:
            relation_name: Base relation name
            model_class: Model class to get relation from (defaults to query model)

        Returns:
            Relation descriptor or None if not found
        """
        if model_class is None:
            model_class = self.model_class

        if not hasattr(model_class, 'get_relation'):
            return None

        return model_class.get_relation(relation_name)

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

        # Apply query modifier if configured
        if config.query_modifier:
            try:
                # Apply the modifier and ensure it returns a query
                self._log(logging.DEBUG, f"Applying query modifier for relation {config.name}: {config.query_modifier}")
                modified_query = config.query_modifier(base_query)

                # If modifier returns None or something invalid, use the original query
                return modified_query if isinstance(modified_query, IQuery) else base_query
            except Exception as e:
                # Log error but continue with base query
                self._log(logging.ERROR, f"Error applying query modifier: {e}")
                return base_query

        return base_query

    def _configure_query_for_nested_relations(self, query: 'IQuery[ModelT]', relation_name: str,
                                              config: RelationConfig) -> None:
        """Configure a query to load nested relations.

        Args:
            query: Base query to configure
            relation_name: Current relation path
            config: Relation configuration
        """
        # Only needed for nested relations
        if '.' not in relation_name:
            return

        # If there are nested relations, add them to the query
        if config.nested:
            for nested_rel in config.nested:
                # Build full path for the nested relation
                full_nested_path = f"{relation_name}.{nested_rel}"

                # Check if we have a configuration for this nested relation
                if full_nested_path in self._eager_loads:
                    nested_config = self._eager_loads[full_nested_path]

                    # Apply with modifier if one exists
                    if nested_config.query_modifier:
                        query = query.with_((nested_rel, nested_config.query_modifier))
                    else:
                        query = query.with_(nested_rel)
                else:
                    # Simple addition without modifier
                    query = query.with_(nested_rel)

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
        # Extract base relation name (e.g., "user" from "user.posts.comments")
        parts = relation_name.split('.')
        base_relation_name = parts[0]

        # Skip if this is a nested relation but not the first level we're processing
        # Those will be handled by the recursive loading
        if len(parts) > 1 and parts[0] != relation_name.split('.')[0]:
            return

        # Get relation descriptor
        relation = self._get_relation(base_relation_name)
        if not relation:
            self._log(logging.WARNING, f"Relation name {base_relation_name} not found in {self.model_class.__name__}")
            return

        # Get related model class
        related_model = relation.get_related_model(self.model_class)
        if not related_model:
            self._log(logging.WARNING, f"Related model for {self.model_class.__name__} not found")
            return

        # Create base query and apply modifier if configured
        base_query = self._create_base_query(related_model, config)
        if not base_query:
            return

        # Clone the query to avoid modifying the original
        if hasattr(base_query, 'clone'):
            base_query = base_query.clone()

        # Configure query for nested relations
        self._configure_query_for_nested_relations(base_query, relation_name, config)

        # Delegate batch loading to relation descriptor
        try:
            loaded_data = relation.batch_load(records, base_query)
        except Exception as e:
            self._log(logging.ERROR, f"Error batch loading relation '{relation_name}': {e}")
            return

        # Process nested relations if there are any in the configuration
        if loaded_data and config.nested:
            self._process_nested_relations(loaded_data, config, related_model)

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
            loaded_data: Dictionary mapping parent record IDs to loaded related records
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

        # Skip if no records were loaded
        if not loaded_records:
            return

        # For each nested relation, create and execute a query to load it
        for nested_relation in config.nested:
            # Debug information to help identify where issues occur
            self._log(logging.DEBUG,
                      f"Processing nested relation '{nested_relation}' for config '{config.name}' on model {related_model.__name__}")

            # Build full nested path
            full_nested_path = f"{config.name}.{nested_relation}"

            # Check if we have a configuration for this nested relation
            nested_config = self._eager_loads.get(full_nested_path)
            if not nested_config:
                self._log(logging.WARNING, f"Missing configuration for nested relation: {full_nested_path}")
                continue

            # Create query for this nested relation
            next_query = related_model.query()

            # Apply the nested relation with its modifier (if any)
            if nested_config.query_modifier:
                next_query = next_query.with_((nested_relation, nested_config.query_modifier))
            else:
                next_query = next_query.with_(nested_relation)

            # Execute the query to load this nested relation for all records
            try:
                next_query._load_relations(loaded_records)
            except Exception as e:
                # Catch and log errors but allow other relations to be processed
                self._log(logging.ERROR, f"Error loading nested relation '{nested_relation}': {e}")

    def get_relation_configs(self) -> Dict[str, RelationConfig]:
        """Get all relation configurations.

        For testing purposes, allows access to the internal relation configurations.

        Returns:
            Dict[str, RelationConfig]: Copy of the eager load configurations
        """
        return dict(self._eager_loads)

    def analyze_relation_path(self, relation_path: str) -> Tuple[List[str], List[str]]:
        """Analyze a relation path for testing purposes.

        Splits a relation path and returns the parts and potential configurations.

        Args:
            relation_path: Relation path to analyze

        Returns:
            Tuple containing:
            - List of path parts (e.g., ["user", "posts", "comments"])
            - List of potential configurations (e.g., ["user", "user.posts", "user.posts.comments"])

        Raises:
            InvalidRelationPathError: If the path format is invalid
        """
        # Validate the path first
        self._validate_relation_path(relation_path)

        parts = relation_path.split('.')
        configs = []
        current = []

        for part in parts:
            current.append(part)
            configs.append('.'.join(current))

        return parts, configs
