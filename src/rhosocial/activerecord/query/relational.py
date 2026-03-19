# src/rhosocial/activerecord/query/relational.py
"""Improved relational query methods implementation."""
import logging
from dataclasses import dataclass
from typing import Dict, Any, Optional, List, Callable, Union, Type, Tuple

from ..interface import IQuery, ThreadSafeDict, IActiveQuery
from ..relation.cache import InstanceCache


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

    def _parse_relation_arg(self, relation: Union[str, tuple]) -> Tuple[str, Optional[Callable]]:
        """Parse a single relation argument into path and modifier.

        Args:
            relation: Either a string path or a tuple of (path, modifier)

        Returns:
            Tuple of (relation_path, query_modifier)
        """
        if isinstance(relation, tuple):
            return relation[0], relation[1]
        return relation, None

    def _validate_relation(self, relation_path: str) -> None:
        """Validate a relation path for format and existence.

        Args:
            relation_path: The relation path to validate

        Raises:
            InvalidRelationPathError: If the path format is invalid
            RelationNotFoundError: If the relation doesn't exist
        """
        self._validate_relation_path(relation_path)
        self._validate_complete_relation_path(relation_path)

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

                Note: For complex modifiers, prefer using named functions instead of lambdas.
                Named functions will be displayed with their fully qualified name in warnings
                when a modifier is overwritten, making debugging easier:

                    # Recommended: named function
                    def filter_published(q):
                        return q.where(Post.c.status == 'published')
                    User.query().with_(('posts', filter_published))

                    # Avoid for complex cases: lambda (shown as <lambda> in warnings)
                    User.query().with_(('posts', lambda q: q.where(...)))

                Parameter Expansion Rule:
                    Each parameter is expanded to its full path chain. The query modifier
                    only applies to the target relation (the last one in the path),
                    not to intermediate relations:

                        ('posts.comments', modifier1) expands to:
                        - 'posts' -> None (intermediate, no modifier)
                        - 'posts.comments' -> modifier1 (target, has modifier)

                    When later parameters overwrite earlier ones:
                        ('posts.comments', m1) + ('posts.comments.user', m2) results in:
                        - 'posts' -> None (from 2nd, overwrites!)
                        - 'posts.comments' -> m2 (from 2nd, overwrites m1!)
                        - 'posts.comments.user' -> m2

                    Therefore, if you don't want a modifier to be overwritten, place it
                    later in the parameter list:

                        # m1 will be used (correct order)
                        User.query().with_(
                            ('posts.comments.user', m2),
                            ('posts.comments', m1),
                        )

                        # m2 will overwrite m1 (wrong order - m1 is lost)
                        User.query().with_(
                            ('posts.comments', m1),
                            ('posts.comments.user', m2),
                        )

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

            # With query modifier (named function recommended for complex cases)
            def filter_published(q):
                return q.where(Post.c.status == 'published')
            users = User.query().with_(('posts', filter_published)).all()

            # Complex scenario with nested relations and modifiers
            def order_comments(q):
                return q.order_by(Comment.c.created_at.desc())
            users = User.query().with_('posts', ('posts.comments', order_comments)).all()
        """
        # First validate all paths to ensure transactional behavior
        validated_relations = []

        for relation in relations:
            relation_path, query_modifier = self._parse_relation_arg(relation)

            # Validate the path before processing
            try:
                self._validate_relation(relation_path)
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

        # Always update the modifier if a modifier was provided (not None).
        # This follows Yii2 behavior: later parameters take precedence.
        if query_modifier is not None:
            # Check if modifier is changing and warn if so
            if existing.query_modifier is not None and existing.query_modifier != query_modifier:
                # Try to get meaningful function info
                def get_func_info(func: Callable) -> str:
                    qualname = getattr(func, '__qualname__', None)
                    module = getattr(func, '__module__', None)
                    if qualname and module and not qualname.startswith('<'):
                        return f"{module}.{qualname}"

                    func_name = getattr(func, '__name__', None)
                    if func_name and not func_name.startswith('<'):
                        try:
                            import inspect
                            sig = str(inspect.signature(func))
                            return f"{func_name}{sig}"
                        except Exception:
                            return func_name

                    return f"<lambda at 0x{hex(id(func))[-8:]}>"

                old_info = get_func_info(existing.query_modifier)
                new_info = get_func_info(query_modifier)
                self._log(
                    logging.WARNING,
                    f"Relation '{path}' modifier is being overwritten. "
                    f"Previous modifier: {old_info}, "
                    f"New modifier: {new_info}. "
                    f"Later parameter takes precedence. "
                    f"If you don't want it to be overwritten, place it later in the parameter list."
                )
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

    def _get_next_level_parts(self, parts: List[str], current_index: int) -> List[str]:
        """Get the next level parts from the relation path.

        Args:
            parts: The full list of path parts
            current_index: Current index in the iteration

        Returns:
            List containing the next part if exists, empty list otherwise
        """
        remaining_parts = parts[current_index + 1:]
        return remaining_parts[:1] if remaining_parts else []

    def _should_update_nested_relation(self, full_path: str, next_level: List[str]) -> bool:
        """Check if we're adding a new nested relation to an existing config.

        Args:
            full_path: The current full relation path
            next_level: The next level parts to check

        Returns:
            True if we should update with a new nested relation
        """
        if not next_level:
            return False

        existing_config = self._eager_loads[full_path]
        next_part = next_level[0]
        return next_part not in existing_config.nested

    def _determine_modifier(self, is_target: bool, is_adding_new_nested: bool,
                            query_modifier: Optional[Callable]) -> Optional[Callable]:
        """Determine the appropriate query modifier based on context.

        Rules:
        1. If this is the target relation (last part), always apply modifier
        2. If adding a NEW nested relation, apply modifier (Yii2 behavior)
        3. Otherwise, don't apply modifier

        Args:
            is_target: Whether this is the target relation
            is_adding_new_nested: Whether we're adding a new nested relation
            query_modifier: The original query modifier

        Returns:
            The appropriate modifier or None
        """
        if is_target:
            return query_modifier
        if is_adding_new_nested:
            return query_modifier
        return None

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
        parts = relation_path.split('.')
        current_path = []

        # Process each part of the path to create configurations
        for i, part in enumerate(parts):
            current_path.append(part)
            full_path = '.'.join(current_path)

            # Check if this is the target relation
            is_target_relation = (full_path == relation_path)

            # Get next level parts
            next_level = self._get_next_level_parts(parts, i)

            # Check if relation already exists
            existing = full_path in self._eager_loads

            # Determine if we're adding a new nested relation
            is_adding_new_nested = (
                existing and
                self._should_update_nested_relation(full_path, next_level)
            )

            # Determine the appropriate modifier
            current_modifier = self._determine_modifier(
                is_target_relation, is_adding_new_nested, query_modifier
            )

            if existing:
                self._update_existing_relation_config(full_path, next_level, current_modifier, is_target_relation)
            else:
                self._add_relation_config(full_path, next_level, current_modifier)

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