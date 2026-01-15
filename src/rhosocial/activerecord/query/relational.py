# src/rhosocial/activerecord/query/relational.py
"""Improved relational query methods implementation."""
import logging
from dataclasses import dataclass
from typing import Dict, Any, Optional, List, Callable, Union, Type, Tuple

from ..interface import IQuery, ThreadSafeDict, IActiveQuery


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


class RelationalQueryMixin(IQuery):
    """
    Query mixin providing eager loading capabilities for model relationships.

    This mixin implements a comprehensive eager loading system that allows loading
    related model data alongside the primary query results. It solves the N+1 query
    problem by batching related data loading efficiently.

    Key Features:
    - Support for simple relation loading (e.g., 'posts')
    - Support for nested relation loading (e.g., 'posts.comments')
    - Support for query modifiers to customize loading behavior
    - Path validation to ensure relations exist and are accessible
    - Efficient batch loading to minimize database queries
    - Proper ordering of nested relation loading

    The mixin works by:
    1. Storing relation loading configurations when with_() is called
    2. Validating relation paths to ensure they exist
    3. Loading related data after the primary query execution
    4. Maintaining proper ordering of nested relations during loading

    Usage:
    ```python
    # Simple eager loading
    users = User.query().with_('posts').all()

    # Nested eager loading
    users = User.query().with_('posts.comments').all()

    # With query modifier
    users = User.query().with_(('posts', lambda q: q.where(Post.c.status == 'published'))).all()
    ```
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Stores relation loading configurations by relation path
        self._eager_loads: ThreadSafeDict[str, RelationConfig] = ThreadSafeDict()

    def with_(self, *relations: Union[str, tuple]) -> 'IActiveQuery':
        """
        Configure eager loading for model relationships to prevent N+1 queries.

        This method enables efficient loading of related data by batching the related
        queries together with the primary query. It accepts both simple relation names
        and complex configurations with query modifiers.

        The method performs full validation of relation paths before applying them,
        ensuring all specified relations exist and are accessible from the appropriate
        models in the path chain.

        Args:
            *relations: Variable-length argument accepting:
                - str: Simple relation path (e.g., 'posts', 'posts.comments')
                - tuple: Relation path with query modifier (e.g., ('posts', modifier_func))

                The relation path supports dot notation for nested relations:
                - 'posts' - Load posts for each user
                - 'posts.comments' - Load posts and their comments for each user
                - 'posts.author.profile' - Load nested relations three levels deep

                Query modifiers are callable functions that accept and return a query object,
                allowing customization of how related data is loaded:
                - Filtering: Only load published posts
                - Ordering: Order comments by creation date
                - Selective fields: Only load specific columns

        Returns:
            IActiveQuery: Returns self to enable method chaining

        Raises:
            InvalidRelationPathError: If the relation path format is invalid (empty, leading/
                                    trailing dots, consecutive dots)
            RelationNotFoundError: If any relation in the path doesn't exist on its respective model

        Example:
            # Simple eager loading
            users = User.query().with_('posts').all()

            # Multiple relations
            users = User.query().with_('posts', 'profile').all()

            # Nested relations
            users = User.query().with_('posts.comments').all()

            # With query modifier
            users = User.query().with_(('posts', lambda q: q.where(Post.c.status == 'published'))).all()

            # Complex scenario
            users = User.query().with_('posts', ('posts.comments', lambda q: q.order_by(Comment.c.created_at.desc()))).all()
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
        """
        Validates the format of a relation path to ensure it follows the expected syntax.

        This method performs syntactic validation of relation paths before they're
        processed further. It checks for common formatting errors that would lead
        to runtime issues.

        Args:
            relation_path: The relation path string to validate (e.g., 'posts', 'posts.comments')

        Raises:
            InvalidRelationPathError: If the path format is invalid, including:
                - Empty string: ""
                - Leading dots: ".posts"
                - Trailing dots: "posts."
                - Consecutive dots: "posts..comments"
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
        """
        Validates that all relations in a complete path exist on their respective models.

        This method performs semantic validation of the relation path by checking that
        each relation in the path exists on the appropriate model class. It traverses
        the path step by step, following the relationships from one model to the next.

        For example, with path 'posts.comments':
        1. Checks that 'posts' relation exists on the query's model class
        2. Gets the related model for 'posts' (e.g., Post)
        3. Checks that 'comments' relation exists on the Post model

        Args:
            relation_path: The full relation path to validate (e.g., 'posts.comments')

        Raises:
            RelationNotFoundError: If any relation in the path does not exist on its
                                 respective model class
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
        """
        Process a relation path and create appropriate configurations for loading.

        This method breaks down a relation path (like 'user.posts.comments') into its
        components and creates configuration entries for each level of the path.
        It handles both simple and nested relations, ensuring that the query modifier
        is applied only to the target relation (the last one in the path).

        The method creates a configuration for each segment of the path:
        - For 'user.posts.comments', it creates configs for 'user', 'user.posts', and 'user.posts.comments'
        - Each configuration tracks what nested relations need to be loaded
        - The query modifier is only applied to the final relation ('user.posts.comments')

        Args:
            relation_path: The full relation path to process (e.g., 'posts.comments')
            query_modifier: Optional function to customize the query for the target relation
                           (applied only to the deepest level of the relation path)

        Raises:
            InvalidRelationPathError: If the relation path format is invalid
            RelationNotFoundError: If any relation in the path does not exist on its respective model
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

    def _load_relations(self, records: List) -> None:
        """
        Main entry point for loading all configured relations for a set of records.

        This method orchestrates the eager loading process by coordinating the loading
        of all relations that were configured through the with_() method. It ensures
        that relations are loaded in the correct order based on their nesting depth
        to satisfy dependencies (e.g., load posts before loading posts.comments).

        The method implements an efficient loading strategy:
        1. Sorts relations by nesting depth to load parent relations before child relations
        2. Processes each relation configuration using the appropriate loading method
        3. Handles errors gracefully, continuing to load other relations even if one fails
        4. Uses batch loading to minimize the number of database queries

        Args:
            records: List of model instances for which to load the configured relations.
                     These are the primary records returned by the main query that need
                     their related data to be loaded.

        Note:
            This method is typically called after the primary query execution to load
            all configured relations in an optimized manner, preventing N+1 query problems.
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

    def _get_relation(self, relation_name: str, model_class: Type = None) -> Optional[Any]:
        """
        Get a relation descriptor by its name from the specified model class.

        This method retrieves the RelationDescriptor object for a given relation name
        from the specified model class. The RelationDescriptor contains all the information
        needed to load the related data (foreign keys, related model type, etc.).

        Args:
            relation_name: The name of the relation to retrieve (e.g., 'posts', 'author')
                          This should be the base name, not a nested path.
            model_class: The model class from which to retrieve the relation.
                        If not provided, defaults to the query's model class.

        Returns:
            RelationDescriptor object if found, None otherwise.
            The RelationDescriptor can be used to load related data efficiently.
        """
        if model_class is None:
            model_class = self.model_class

        if not hasattr(model_class, 'get_relation'):
            return None

        return model_class.get_relation(relation_name)

    def _create_base_query(self, related_model: Type, config: RelationConfig) -> Optional['IQuery']:
        """
        Create and configure a base query for loading related records.

        This method creates an initial query for the related model and applies any
        configured query modifiers. The base query serves as the starting point
        for loading related data and can be customized with filters, ordering,
        or other query modifications.

        Args:
            related_model: The model class for which to create the base query.
                          This is the class of the related records to be loaded.
            config: Configuration object that may contain a query modifier function
                   to customize the base query before execution.

        Returns:
            An IQuery instance that is ready to load related records, or None if
            the related model doesn't support query creation.

        Note:
            If a query modifier is configured, it will be applied to the base query
            to customize how the related data is loaded (e.g., adding WHERE clauses,
            ordering, etc.).
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

    def _configure_query_for_nested_relations(self, query: 'IQuery', relation_name: str,
                                              config: RelationConfig) -> None:
        """
        Configure a query to load nested relations based on the configuration.

        This method checks if there are nested relations configured for the current
        relation and adds them to the provided query. It's used during the eager
        loading process to ensure that nested relations are properly configured
        for loading.

        The method iterates through any nested relations specified in the configuration
        and adds them to the query using the with_() method. This allows for complex
        nested eager loading scenarios like 'posts.comments.author'.

        Args:
            query: The base query to configure with nested relations.
                  This query will be modified to include nested relation loading.
            relation_name: The current relation path (e.g., 'posts.comments').
                          Used to look up nested relations in the configuration.
            config: Configuration object containing information about nested relations
                   that should be loaded for the current relation.

        Note:
            This method only processes nested relations if the relation name contains
            dots (indicating it's a nested relation path).
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

    def _load_single_relation(self, records: List, relation_name: str, config: RelationConfig) -> None:
        """
        Load a single relation for all records in an optimized manner.

        This method handles the complete process of loading one specific relation for
        all the provided records. It coordinates with the relation descriptor to perform
        efficient batch loading and handles nested relations if they are configured.

        The method performs several key operations:
        1. Identifies the base relation name from the full path
        2. Retrieves the relation descriptor from the model class
        3. Gets the related model class for the relation
        4. Creates and configures a base query for loading related data
        5. Applies any configured query modifiers to customize the loading
        6. Delegates to the relation descriptor's batch_load method for efficient loading
        7. Processes any nested relations that should be loaded for the related records

        Args:
            records: List of parent records for which to load the relation data.
                     These are the records that have the relationship (e.g., users).
            relation_name: Full relation path to load (e.g., 'posts', 'posts.comments').
                          This could be a simple relation or a nested path.
            config: Configuration object containing nested relations and query modifiers
                   that affect how the relation should be loaded.

        Note:
            This method is part of the batch loading process and is designed to load
            the same relation for multiple records in a single efficient database query.
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
            related_model: Type
    ) -> None:
        """
        Process nested relations by recursively loading additional related data.

        This method handles the loading of nested relations (relations of relations)
        after the primary relation has been loaded. It implements a recursive loading
        pattern to handle arbitrarily deep relation chains.

        The method works as follows:
        1. Collects all the related records that were just loaded
        2. For each nested relation specified in the configuration:
           a. Creates a new query context for that nested relation
           b. Applies any query modifiers if configured
           c. Recursively calls the loading process for the nested relation

        For example, if loading 'posts.comments' and the posts have been loaded,
        this method will take all the loaded posts and initiate loading of their comments.

        Args:
            loaded_data: Dictionary mapping parent record IDs to the related records
                        that were just loaded (e.g., mapping user IDs to their posts)
            config: Configuration object containing information about what nested
                   relations should be loaded next (e.g., 'comments' for each 'post')
            related_model: The model class of the currently loaded related records
                          (e.g., Post class when loading comments for posts)

        Note:
            This method enables the deep eager loading capability, allowing chains
            like 'user.posts.comments.likes' to be loaded efficiently.
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