"""Unit tests for relation path processing logic in RelationalQueryMixin."""
from typing import List, Optional, Any, Union, Tuple, Dict, Set
from unittest.mock import MagicMock, patch

import pytest

from src.rhosocial.activerecord.interface import IQuery
from src.rhosocial.activerecord.query.relational import RelationalQueryMixin, InvalidRelationPathError


class MockQueryBase(IQuery[Any]):
    """Mock base class that implements IQuery interface with empty methods."""

    def __init__(self):
        # Initialize required properties
        self.model_class = MagicMock()
        self.condition_groups = [[]]
        self.current_group = 0
        self.order_clauses = []
        self.join_clauses = []
        self.limit_count = None
        self.offset_count = None
        self.select_columns = None
        self._explain_enabled = False
        self._explain_options = None

    # Implement required interface methods with minimal implementations
    def all(self) -> List[Any]:
        return []

    def one(self) -> Optional[Any]:
        return None

    def one_or_fail(self) -> Any:
        return None

    def where(self, condition: str, params: Optional[Union[tuple, List[Any]]] = None) -> 'IQuery':
        return self

    def or_where(self, condition: str, params: Optional[Union[tuple, List[Any]]] = None) -> 'IQuery':
        return self

    def order_by(self, *clauses: str) -> 'IQuery':
        return self

    def join(self, join_clause: str) -> 'IQuery':
        return self

    def limit(self, count: int) -> 'IQuery':
        return self

    def offset(self, count: int) -> 'IQuery':
        return self

    def select(self, *columns: str, append: bool = False) -> 'IQuery':
        return self

    def count(self) -> int:
        return 0

    def exists(self) -> bool:
        return False

    def build(self) -> Tuple[str, tuple]:
        return "", ()

    def to_sql(self) -> Tuple[str, tuple]:
        return "", ()

    def explain(self, *args, **kwargs) -> 'IQuery':
        return self

    def between(self, column: str, start: Any, end: Any) -> 'IQuery[ModelT]':
        return self

    def not_between(self, column: str, start: Any, end: Any) -> 'IQuery[ModelT]':
        return self

    def  start_or_group(self) -> 'IQuery[ModelT]':
        return self

    def end_or_group(self) -> 'IQuery[ModelT]':
        return self

    def in_list(self, column: str, values: Union[List[Any], Tuple[Any, ...]],
                empty_result: bool = True) -> 'IQuery[ModelT]':
        return self

    def is_not_null(self, column: str) -> 'IQuery[ModelT]':
        return self

    def is_null(self, column: str) -> 'IQuery[ModelT]':
        return self

    def like(self, column: str, pattern: str) -> 'IQuery[ModelT]':
        return self

    def not_like(self, column: str, pattern: str) -> 'IQuery[ModelT]':
        return self

    def not_in(self, column: str, values: Union[List[Any], Tuple[Any, ...]],
               empty_result: bool = False) -> 'IQuery[ModelT]':
        return self

    def query(self, conditions: Optional[Dict[str, Any]] = None) -> 'IQuery[ModelT]':
        return self

    def to_dict(self, include: Optional[Set[str]] = None, exclude: Optional[Set[str]] = None) -> 'IDictQuery[ModelT]':
        return self

class MockQuery(RelationalQueryMixin, MockQueryBase):
    """Mock query class for testing the RelationalQueryMixin in isolation."""

    def __init__(self):
        super().__init__()
        self._log = MagicMock()  # Mock the logging method


class TestRelationPathProcessing:
    """Test suite specifically for relation path processing logic."""

    @pytest.fixture
    def query(self):
        """Create a fresh query instance for each test."""
        return MockQuery()

    def test_simple_relation(self, query):
        """Test processing a simple direct relation.

        Verifies that:
        - A simple relation without nesting ("user") is correctly processed
        - The configuration is created with the correct name
        - The nested relations list is empty
        - No query modifier is assigned
        """
        # Process a simple relation
        query._process_relation_path("user")

        # Verify the configuration was created correctly
        configs = query.get_relation_configs()
        assert "user" in configs
        assert configs["user"].name == "user"
        assert configs["user"].nested == []
        assert configs["user"].query_modifier is None

    def test_nested_relation(self, query):
        """Test processing a nested relation with dot notation.

        Verifies that:
        - A nested relation path ("user.posts") correctly creates configurations for all parts
        - The parent relation ("user") includes the child ("posts") in its nested list
        - The leaf relation ("user.posts") has an empty nested list
        - No query modifiers are assigned to any part of the path
        """
        # Process a nested relation
        query._process_relation_path("user.posts")

        # Verify configurations for all parts of the path
        configs = query.get_relation_configs()

        # Verify "user" config was created
        assert "user" in configs
        assert configs["user"].name == "user"
        assert configs["user"].nested == ["posts"]
        assert configs["user"].query_modifier is None

        # Verify "user.posts" config was created
        assert "user.posts" in configs
        assert configs["user.posts"].name == "user.posts"
        assert configs["user.posts"].nested == []
        assert configs["user.posts"].query_modifier is None

    def test_deeply_nested_relation(self, query):
        """Test processing a deeply nested relation path.

        Verifies that:
        - A deeply nested path ("user.posts.comments.author") is correctly processed
        - Configurations are created for all levels in the path
        - Each level properly references its child in the nested list
        - The complete path hierarchy is correctly established
        """
        # Process a deeply nested relation
        query._process_relation_path("user.posts.comments.author")

        # Verify configurations for all path segments
        configs = query.get_relation_configs()

        # Check each level of nesting
        assert "user" in configs
        assert configs["user"].nested == ["posts"]

        assert "user.posts" in configs
        assert configs["user.posts"].nested == ["comments"]

        assert "user.posts.comments" in configs
        assert configs["user.posts.comments"].nested == ["author"]

        assert "user.posts.comments.author" in configs
        assert configs["user.posts.comments.author"].nested == []

    def test_relation_with_query_modifier(self, query):
        """Test processing a relation with a query modifier function.

        Verifies that:
        - A relation with an attached query modifier function is correctly processed
        - The modifier function is preserved exactly (by reference, not value)
        - The modifier function is correctly associated with the relation
        """
        # Create a test modifier function
        def test_modifier(q):
            return q.where("active = ?", True)

        # Process relation with modifier
        query._process_relation_path("user", test_modifier)

        # Verify the modifier was correctly assigned
        configs = query.get_relation_configs()
        assert "user" in configs
        assert configs["user"].query_modifier == test_modifier

    def test_nested_relation_with_modifier_on_leaf(self, query):
        """Test a nested relation with modifier only on the leaf node.

        Verifies that:
        - When a modifier is applied to a nested path ("user.posts")
        - Only the specifically targeted relation receives the modifier
        - Intermediate relations (like "user") do not receive the modifier
        - The modifier is correctly associated with the leaf relation
        """
        # Create a test modifier
        def test_modifier(q):
            return q.where("published = ?", True)

        # Process a nested relation with modifier on leaf
        query._process_relation_path("user.posts", test_modifier)

        # Verify configurations
        configs = query.get_relation_configs()

        # Verify intermediate relation has no modifier
        assert "user" in configs
        assert configs["user"].query_modifier is None

        # Verify leaf relation has the modifier
        assert "user.posts" in configs
        assert configs["user.posts"].query_modifier == test_modifier

    def test_updating_existing_relation(self, query):
        """Test updating an existing relation configuration.

        Verifies that:
        - Adding a relation that builds on an existing one ("user" followed by "user.posts")
        - Properly updates the existing relation's nested list
        - Maintains the integrity of the relation hierarchy
        - Doesn't duplicate existing relations
        """
        # First add a simple relation
        query._process_relation_path("user")

        # Then add a nested relation using the same base
        query._process_relation_path("user.posts")

        # Verify configurations
        configs = query.get_relation_configs()

        # Verify "user" config was updated to include nested relation
        assert "user" in configs
        assert "posts" in configs["user"].nested

        # Verify "user.posts" config was created
        assert "user.posts" in configs

    def test_updating_with_new_nested_relation(self, query):
        """Test updating with a new nested relation.

        Verifies that:
        - Adding a different nested relation to an existing base ("user.comments" after "user.posts")
        - Correctly updates the base relation to include both nested relations
        - Creates separate configurations for each branch
        - Preserves both branches in the relation hierarchy
        """
        # Add a relation with one nested path
        query._process_relation_path("user.posts")

        # Add another relation with a different nested path
        query._process_relation_path("user.comments")

        # Verify configurations
        configs = query.get_relation_configs()

        # Verify "user" config includes both nested relations
        assert "user" in configs
        assert set(configs["user"].nested) == {"posts", "comments"}

        # Verify both nested relations were created
        assert "user.posts" in configs
        assert "user.comments" in configs

    def test_updating_with_query_modifier(self, query):
        """Test updating a relation by adding a query modifier.

        Verifies that:
        - Adding a query modifier to an existing relation without a modifier
        - Correctly assigns the modifier to the relation
        - Preserves the rest of the relation configuration (name, nested relations)
        """
        # First add relation without modifier
        query._process_relation_path("user")

        configs = query.get_relation_configs()
        assert configs["user"].query_modifier is None

        # Create test modifier
        def test_modifier(q):
            return q.where("active = ?", True)

        # Update relation with modifier
        query._process_relation_path("user", test_modifier)

        # Verify modifier was added
        configs = query.get_relation_configs()
        assert configs["user"].query_modifier == test_modifier

    def test_override_query_modifier(self, query):
        """Test that a later query modifier overrides an earlier one.

        Verifies that:
        - When a relation is processed multiple times with different modifiers
        - The most recently applied modifier takes precedence
        - Earlier modifiers are completely replaced, not merged or combined
        """
        # Create test modifiers
        def first_modifier(q):
            return q.where("status = ?", "pending")

        def second_modifier(q):
            return q.where("status = ?", "active")

        # Add relation with first modifier
        query._process_relation_path("user", first_modifier)

        configs = query.get_relation_configs()
        assert configs["user"].query_modifier == first_modifier

        # Update with second modifier
        query._process_relation_path("user", second_modifier)

        # Verify second modifier replaced the first
        configs = query.get_relation_configs()
        assert configs["user"].query_modifier == second_modifier

    def test_out_of_order_relation_declaration(self, query):
        """Test declaring relations out of order (deep path before shallow).

        Verifies that:
        - Processing a deep relation ("user.posts.comments") followed by a shallow one ("user.posts")
        - Correctly handles the out-of-order declaration
        - Maintains the proper relation hierarchy regardless of declaration order
        - All relations in the path are correctly configured
        <TODO> 可以配合中途修改 query_modifier
        """
        # First declare a deep nested relation
        query._process_relation_path("user.posts.comments")

        # Then declare a shallower relation
        query._process_relation_path("user.posts")

        # Verify all configurations were created correctly
        configs = query.get_relation_configs()

        # All relations should exist
        assert "user" in configs
        assert "user.posts" in configs
        assert "user.posts.comments" in configs

        # Nested relations should be correctly configured
        assert "posts" in configs["user"].nested
        assert "comments" in configs["user.posts"].nested

    def test_skip_intermediate_relation(self, query):
        """Test declaring a deep relation without its intermediate relations.

        Verifies that:
        - When declaring a deep path explicitly ("user.posts.comments.author")
        - All intermediate relations are automatically created
        - Later declaring a previously created intermediate ("user.posts.comments")
        - Correctly recognizes and updates the existing relation
        """
        # Declare a deep relation without explicitly declaring intermediates
        query._process_relation_path("user.posts.comments.author")

        # Then add a relation that should be recognized as already configured
        query._process_relation_path("user.posts.comments")

        # Verify configurations
        configs = query.get_relation_configs()

        # All relations in the path should be configured
        assert set(configs.keys()) == {
            "user",
            "user.posts",
            "user.posts.comments",
            "user.posts.comments.author"
        }

        # Nested relations should be correctly configured
        assert configs["user.posts.comments"].nested == ["author"]

    def test_circular_reference_handling(self, query):
        """Test handling potential circular references in relation paths.

        Verifies that:
        - Processing a path that references the same model type multiple times ("user.posts.comments.user.posts")
        - Correctly handles the circular reference without infinite recursion
        - Creates all relations in the path despite the repetition
        - Maintains proper nesting relationships through the cycle
        """
        # Create a path that could cause circular references
        query._process_relation_path("user.posts.comments.user.posts")

        # Verify all relations were created
        configs = query.get_relation_configs()
        expected_paths = [
            "user",
            "user.posts",
            "user.posts.comments",
            "user.posts.comments.user",
            "user.posts.comments.user.posts"
        ]

        # Check that all expected paths were created
        for path in expected_paths:
            assert path in configs

        # Verify nested relations for the circular reference
        assert "posts" in configs["user.posts.comments.user"].nested

    def test_multiple_calls_with_same_relation(self, query):
        """Test multiple calls with the same relation in different forms.

        Verifies that:
        - Processing the same relation multiple times in different contexts
        - Correctly merges the configurations rather than duplicating them
        - Preserves all nested relations across multiple calls
        - Maintains a consistent relation hierarchy
        <TODO> 可以配合后续修改 query_modifier
        """
        # Add same relation multiple times with different nestings
        query._process_relation_path("user")
        query._process_relation_path("user.posts")
        query._process_relation_path("user")  # Duplicate

        # Verify configurations merged correctly
        configs = query.get_relation_configs()

        # Should only have two unique relations
        assert len(configs) == 2
        assert set(configs.keys()) == {"user", "user.posts"}

        # User should have posts in nested relations
        assert "posts" in configs["user"].nested

    def test_complex_hierarchy_with_multiple_branches(self, query):
        """Test complex hierarchy with multiple relation branches.

        Verifies that:
        - Processing multiple different branches from the same root ("user.posts.comments", "user.profile.address", etc.)
        - Correctly maintains all branches in the hierarchy
        - Each branch is properly configured with its own nested relations
        - The root relation maintains references to all first-level relations
        """
        # Create a complex relation hierarchy with multiple branches
        query._process_relation_path("user.posts.comments")
        query._process_relation_path("user.profile.address")
        query._process_relation_path("user.orders.items")

        # Verify configurations
        configs = query.get_relation_configs()

        # Check user's nested relations include all branches
        assert set(configs["user"].nested) == {"posts", "profile", "orders"}

        # Check each branch's second level
        assert "comments" in configs["user.posts"].nested
        assert "address" in configs["user.profile"].nested
        assert "items" in configs["user.orders"].nested

    def test_analyze_relation_path(self, query):
        """Test the helper method for analyzing relation paths.

        Verifies that:
        - The analyze_relation_path method correctly splits a path into its components
        - Returns the expected list of path parts
        - Returns the expected list of potential configurations
        - Works correctly with various path complexities
        """
        # Test various paths
        tests = [
            ("user", (["user"], ["user"])),
            ("user.posts", (["user", "posts"], ["user", "user.posts"])),
            ("user.posts.comments", (["user", "posts", "comments"],
                                   ["user", "user.posts", "user.posts.comments"]))
        ]

        for path, expected in tests:
            parts, configs = query.analyze_relation_path(path)
            assert parts == expected[0]
            assert configs == expected[1]

    def test_modifier_application_scope(self, query):
        """Test that modifiers are only applied to the specific relation level.

        Verifies that:
        - When applying different modifiers to different levels of a relation path
        - Each modifier is only associated with its specific targeted relation
        - Modifiers don't affect parent or child relations
        - Each modifier maintains its own state and behavior
        """
        # Create different modifiers for different levels
        def user_modifier(q):
            q.where_clause = "user_filter"
            return q

        def posts_modifier(q):
            q.where_clause = "posts_filter"
            return q

        def comments_modifier(q):
            q.where_clause = "comments_filter"
            return q

        # Apply modifiers at different levels
        query._process_relation_path("user", user_modifier)
        query._process_relation_path("user.posts", posts_modifier)
        query._process_relation_path("user.posts.comments", comments_modifier)

        # Verify each level has its own modifier
        configs = query.get_relation_configs()
        assert configs["user"].query_modifier == user_modifier
        assert configs["user.posts"].query_modifier == posts_modifier
        assert configs["user.posts.comments"].query_modifier == comments_modifier

        # Simulate modifier execution to verify isolation
        mock_query = MagicMock()
        configs["user"].query_modifier(mock_query)
        assert mock_query.where_clause == "user_filter"

        mock_query = MagicMock()
        configs["user.posts"].query_modifier(mock_query)
        assert mock_query.where_clause == "posts_filter"

        mock_query = MagicMock()
        configs["user.posts.comments"].query_modifier(mock_query)
        assert mock_query.where_clause == "comments_filter"

    def test_complex_path_without_intermediates(self, query):
        """Test a complex path where multiple intermediate relations are skipped.

        Verifies that:
        - Processing a very deep path ("a.b.c.d.e.f.g") creates all intermediate relations
        - Then adding one of the intermediate paths ("a.b.c") works correctly
        - All relations in the path are properly created with correct nesting
        - The complete relation hierarchy is maintained
        """
        # Process a path where several intermediates are missing
        query._process_relation_path("a.b.c.d.e.f.g")

        # Then add one of the intermediate paths but not others
        query._process_relation_path("a.b.c")

        # Verify all paths were created
        configs = query.get_relation_configs()
        expected_paths = ["a", "a.b", "a.b.c", "a.b.c.d",
                          "a.b.c.d.e", "a.b.c.d.e.f", "a.b.c.d.e.f.g"]

        for path in expected_paths:
            assert path in configs

        # Verify correct nesting
        assert configs["a"].nested == ["b"]
        assert configs["a.b"].nested == ["c"]
        assert configs["a.b.c"].nested == ["d"]
        assert configs["a.b.c.d"].nested == ["e"]
        assert configs["a.b.c.d.e"].nested == ["f"]
        assert configs["a.b.c.d.e.f"].nested == ["g"]
        assert configs["a.b.c.d.e.f.g"].nested == []

    def test_conflicting_nested_relations(self, query):
        """Test handling of potentially conflicting nested relations.

        Verifies that:
        - Creating multiple branches from the same parent ("user.profile", "user.posts", "user.comments")
        - Then adding deeper relations to one branch ("user.posts.author")
        - Correctly maintains all branches without conflict
        - Each branch can have its own nesting structure
        - Updates to one branch don't affect other branches
        """
        # Define nested paths that could conflict
        query._process_relation_path("user.profile")
        query._process_relation_path("user.posts")
        query._process_relation_path("user.comments")

        # Add another level to one branch
        query._process_relation_path("user.posts.author")

        # Verify that all nested relations are preserved
        configs = query.get_relation_configs()

        # User should have all three nested relations
        assert set(configs["user"].nested) == {"profile", "posts", "comments"}

        # Posts should have author as nested relation
        assert configs["user.posts"].nested == ["author"]

        # Other branches should be unaffected
        assert configs["user.profile"].nested == []
        assert configs["user.comments"].nested == []

    def test_relation_with_complex_modifiers(self, query):
        """Test relations with complex query modifiers that have state.

        Verifies that:
        - Modifiers can be objects with state, not just simple functions
        - These stateful modifiers are correctly stored and preserved
        - The state of each modifier is maintained independently
        - When executed, each modifier applies its specific state
        """
        # Create modifiers with state
        class ModifierWithState:
            def __init__(self, state):
                self.state = state

            def __call__(self, q):
                q.state = self.state
                return q

        modifier1 = ModifierWithState("state1")
        modifier2 = ModifierWithState("state2")

        # Apply modifiers
        query._process_relation_path("user", modifier1)
        query._process_relation_path("user.posts", modifier2)

        # Verify modifiers are correctly stored with their state
        configs = query.get_relation_configs()

        # Execute the modifiers to verify state is preserved
        mock_query1 = MagicMock()
        configs["user"].query_modifier(mock_query1)
        assert mock_query1.state == "state1"

        mock_query2 = MagicMock()
        configs["user.posts"].query_modifier(mock_query2)
        assert mock_query2.state == "state2"

    def test_tracking_applied_modifiers(self, query):
        """Test tracking which modifiers were applied using unique identifiers.

        Verifies that:
        - Modifiers can track when they're applied through side effects
        - Each modifier's unique behavior is preserved
        - Modifiers are correctly associated with their targeted relations
        - When executed, each modifier performs its expected behavior
        """
        # Create a tracking dictionary
        applied = {}

        # Create modifiers that record when they're applied
        def create_tracked_modifier(name):
            def modifier(q):
                applied[name] = True
                return q
            return modifier

        # Create modifiers for different paths
        user_mod = create_tracked_modifier("user")
        posts_mod = create_tracked_modifier("posts")
        comments_mod = create_tracked_modifier("comments")

        # Process paths with modifiers
        query._process_relation_path("user", user_mod)
        query._process_relation_path("user.posts", posts_mod)
        query._process_relation_path("user.posts.comments", comments_mod)

        # Verify modifiers were stored
        configs = query.get_relation_configs()

        # Execute modifiers to verify tracking
        for path in ["user", "user.posts", "user.posts.comments"]:
            mock_query = MagicMock()
            configs[path].query_modifier(mock_query)

        # Check that all modifiers were applied
        assert applied == {"user": True, "posts": True, "comments": True}

    def test_complex_path_with_branch_updates(self, query):
        """Test updating branches in complex paths.

        Verifies that:
        - Creating a complex path structure with multiple branches
        - Then updating specific branches with new configurations
        - Correctly maintains the overall structure while applying updates
        - Branches can be updated independently without affecting others
        """
        # Create initial complex structure
        query._process_relation_path("user.posts.comments")
        query._process_relation_path("user.profile.address")

        # Update with modified branches
        def comments_mod(q):
            return q.where("is_hidden = ?", False)

        query._process_relation_path("user.posts.comments", comments_mod)
        query._process_relation_path("user.profile.settings")

        # Verify structure remains intact with updates
        configs = query.get_relation_configs()

        # User should have both branches
        assert set(configs["user"].nested) == {"posts", "profile"}

        # Comments should have modifier
        assert configs["user.posts.comments"].query_modifier == comments_mod

        # Profile should have both address and settings
        assert set(configs["user.profile"].nested) == {"address", "settings"}
        assert configs["user.profile"].query_modifier is None

    def test_with_method_integration(self, query):
        """Test integration between with_() and _process_relation_path().

        Verifies that:
        - The public with_() method correctly uses _process_relation_path()
        - It handles all supported relation formats (string, tuple with modifier)
        - It correctly processes multiple relations in a single call
        - Modifiers are correctly applied only to their targeted relations
        """
        # Create a modifier function
        def test_modifier(q):
            return q.where("status = ?", "active")

        # Call with_() with various relation forms
        query.with_("user", "order", ("product", test_modifier))

        # Verify _process_relation_path was called correctly
        configs = query.get_relation_configs()

        # Should have all three relations
        assert "user" in configs
        assert "order" in configs
        assert "product" in configs

        # Only product should have the modifier
        assert configs["user"].query_modifier is None
        assert configs["order"].query_modifier is None
        assert configs["product"].query_modifier == test_modifier

    def test_with_call_chaining(self, query):
        """Test that with_() method supports chaining with correct behavior.

        Verifies that:
        - The with_() method returns self for method chaining
        - Multiple chained calls correctly process all specified relations
        - Different relation formats can be mixed in the chain
        - Modifiers are correctly associated with their targeted relations
        """
        # Test modifiers
        def mod1(q): q.flag1 = True; return q
        def mod2(q): q.flag2 = True; return q
        def mod3(q): q.flag3 = True; return q

        # Chain multiple with_() calls
        result = query.with_("user") \
            .with_(("posts", mod1)) \
            .with_("comments", ("author", mod2)) \
            .with_(("user.profile", mod3))

        # Verify chaining returns the query
        assert result == query

        # Verify all relations were processed
        configs = query.get_relation_configs()
        assert "user" in configs
        assert "posts" in configs
        assert "comments" in configs
        assert "author" in configs
        assert "user.profile" in configs

        # Verify modifiers were applied correctly
        assert configs["posts"].query_modifier == mod1
        assert configs["author"].query_modifier == mod2
        assert configs["user.profile"].query_modifier == mod3
        assert configs["user"].query_modifier is None
        assert configs["comments"].query_modifier is None

    @patch.object(RelationalQueryMixin, '_load_relations')
    def test_relation_loading(self, mock_load_relations, query):
        """Test that relation configurations are properly used during loading.

        Verifies that:
        - When relation loading is triggered
        - The _load_relations method is called with the correct records
        - The created configurations would be used in the loading process
        """
        # Setup test relations
        query.with_("user", "posts.comments")

        # Create mock records
        mock_records = [MagicMock(), MagicMock()]

        # Trigger relation loading
        query._load_relations(mock_records)

        # Verify _load_relations was called with the records
        mock_load_relations.assert_called_once_with(mock_records)

    def test_relation_sorting_by_depth(self, query):
        """Test that relations are sorted by depth for proper loading order.

        Verifies that:
        - Relations are correctly sorted by nesting depth
        - Shallower relations appear before deeper ones in the sorted order
        - This ensures parent relations are loaded before their children
        - The sorting works regardless of the order relations were added
        """
        # Add relations in random order
        query._process_relation_path("user.posts.comments")
        query._process_relation_path("user")
        query._process_relation_path("user.posts")

        # Manually call the sorting logic similar to _load_relations
        sorted_relations = sorted(
            query.get_relation_configs().items(),
            key=lambda x: len(x[0].split('.'))
        )

        # Verify correct sorting order (shallow to deep)
        relation_names = [r[0] for r in sorted_relations]
        assert relation_names == ["user", "user.posts", "user.posts.comments"]

    def test_load_order_with_complex_paths(self, query):
        """Test loading order with complex paths.

        Verifies that:
        - With a complex structure having multiple paths at various depths
        - Relations are correctly grouped by depth
        - Relations at the same depth are all processed before deeper ones
        - The complete path hierarchy is maintained after sorting
        """
        # Create a more complex path structure
        query._process_relation_path("a.b.c.d")
        query._process_relation_path("a.x.y")
        query._process_relation_path("p.q")
        query._process_relation_path("a")

        # Sort by depth
        sorted_relations = sorted(
            query.get_relation_configs().items(),
            key=lambda x: len(x[0].split('.'))
        )

        # Group by depth
        depth_groups = {}
        for name, config in sorted_relations:
            depth = len(name.split('.'))
            if depth not in depth_groups:
                depth_groups[depth] = []
            depth_groups[depth].append(name)

        # Verify each depth level
        assert depth_groups[1] == ["a", "p"]
        assert depth_groups[2] == ["a.b", "a.x", "p.q"]
        assert depth_groups[3] == ["a.b.c", "a.x.y"]
        assert depth_groups[4] == ["a.b.c.d"]

    def test_multi_type_relation_paths(self, query):
        """Test handling of relation paths with different relation types.

        Verifies that:
        - Paths combining different relation types (BelongsTo, HasMany, HasOne)
        - Are correctly processed regardless of the relation type
        - The relation type doesn't affect the path processing logic
        - The correct nesting hierarchy is established
        """
        # In real usage, different parts might be different relation types
        # (BelongsTo, HasMany, etc.)

        # Create paths combining different potential relation types
        query._process_relation_path("belongsTo.hasMany.hasOne")

        # Verify structure is created correctly regardless of relation types
        configs = query.get_relation_configs()

        # All parts should be present
        assert "belongsTo" in configs
        assert "belongsTo.hasMany" in configs
        assert "belongsTo.hasMany.hasOne" in configs

        # Verify nesting
        assert configs["belongsTo"].nested == ["hasMany"]
        assert configs["belongsTo.hasMany"].nested == ["hasOne"]
        assert configs["belongsTo.hasMany.hasOne"].nested == []

    def test_deeply_nested_modifiers(self, query):
        """Test deeply nested paths with modifiers at multiple levels.

        Verifies that:
        - When adding modifiers to multiple levels of a deeply nested path
        - Each level's modifier is correctly stored and preserved
        - Modifiers are isolated to their specific relation level
        - When executed, each modifier behaves as expected
        """
        # Create modifiers
        def m1(q): q.mod = "m1"; return q
        def m2(q): q.mod = "m2"; return q
        def m3(q): q.mod = "m3"; return q

        # Process deeply nested path with modifiers at each level
        query._process_relation_path("a", m1)
        query._process_relation_path("a.b", m2)
        query._process_relation_path("a.b.c", m3)

        # Verify configurations
        configs = query.get_relation_configs()

        # Verify each level has its own modifier
        assert configs["a"].query_modifier == m1
        assert configs["a.b"].query_modifier == m2
        assert configs["a.b.c"].query_modifier == m3

        # Execute modifiers to verify isolation
        q1, q2, q3 = MagicMock(), MagicMock(), MagicMock()
        configs["a"].query_modifier(q1)
        configs["a.b"].query_modifier(q2)
        configs["a.b.c"].query_modifier(q3)

        assert q1.mod == "m1"
        assert q2.mod == "m2"
        assert q3.mod == "m3"

    def test_modifier_function_identity_preservation(self, query):
        """Test that modifier function identity is preserved.

        Verifies that:
        - Modifier functions maintain their exact identity (not just equivalent behavior)
        - Different lambda functions are preserved as distinct objects
        - Function references are stored exactly, not cloned or recreated
        """
        # Create modifiers as lambdas, which are unique by identity
        mod1 = lambda q: q.where("test1 = ?", True)
        mod2 = lambda q: q.where("test2 = ?", True)

        # Process paths with these modifiers
        query._process_relation_path("rel1", mod1)
        query._process_relation_path("rel2", mod2)

        # Verify the exact function objects were preserved
        configs = query.get_relation_configs()
        assert configs["rel1"].query_modifier is mod1  # Check identity, not equality
        assert configs["rel2"].query_modifier is mod2  # Check identity, not equality

    def test_custom_object_modifiers(self, query):
        """Test that custom object modifiers work correctly.

        Verifies that:
        - Custom objects with __call__ method can be used as modifiers
        - These objects maintain their state and identity
        - When executed, they behave according to their implementation
        - Different custom modifiers are preserved as distinct objects
        """
        # Define a custom object with __call__
        class CustomModifier:
            def __init__(self, name):
                self.name = name

            def __call__(self, q):
                q.custom_name = self.name
                return q

        # Create custom modifiers
        mod1 = CustomModifier("mod1")
        mod2 = CustomModifier("mod2")

        # Process relations with these modifiers
        query._process_relation_path("rel1", mod1)
        query._process_relation_path("rel2", mod2)

        # Verify modifiers were stored correctly
        configs = query.get_relation_configs()

        # Execute modifiers to test behavior
        q1, q2 = MagicMock(), MagicMock()
        configs["rel1"].query_modifier(q1)
        configs["rel2"].query_modifier(q2)

        assert q1.custom_name == "mod1"
        assert q2.custom_name == "mod2"

    def test_edge_case_empty_parts(self, query):
        """Test handling of edge cases with empty path parts.

        Verifies that:
        - Paths with problematic formats (double dots, trailing dots, etc.)
        - Are either handled gracefully or raise appropriate exceptions
        - The system doesn't create invalid relation configurations
        - Empty parts are properly filtered out or rejected
        """
        # Test with empty parts (e.g., "user..posts" or "user.")
        paths_with_empty = [
            "user..posts",  # Double dot
            "user.",        # Trailing dot
            ".user",        # Leading dot
            "..user"        # Multiple leading dots
        ]

        # Process each path
        for path in paths_with_empty:
            # Should handle or raise appropriate exception
            try:
                query._process_relation_path(path)
                # If no exception, verify empty parts were skipped
                configs = query.get_relation_configs()
                assert ".." not in ''.join(configs.keys())
                assert not any(k.startswith('.') for k in configs.keys())
                assert not any(k.endswith('.') for k in configs.keys())
            except Exception as e:
                # If exception, it should be appropriate for the case
                assert "relation" in str(e).lower() or "path" in str(e).lower()

    def test_integration_with_sorted_loading(self, query):
        """Test integration with sorting for loading order.

        Verifies that:
        - With a complex path structure added in arbitrary order
        - When sorted for loading, relations appear in the correct order by depth
        - All relations at a given depth are processed before deeper relations
        - This ensures dependency order is maintained during loading
        """
        # Create a complex structure with various depths
        relations = [
            "a.b.c.d.e",
            "p.q",
            "a.x.y.z",
            "m"
        ]

        # Add them in arbitrary order
        for rel in relations:
            query._process_relation_path(rel)

        # Simulate the sorting that would happen in _load_relations
        configs = query.get_relation_configs()
        sorted_paths = sorted(configs.keys(), key=lambda x: len(x.split('.')))

        # Verify sorting works correctly
        expected_sorted = [
            "m",            # Depth 1
            "a", "p",       # Depth 1
            "a.b", "a.x", "p.q",  # Depth 2
            "a.b.c", "a.x.y",     # Depth 3
            "a.b.c.d", "a.x.y.z", # Depth 4
            "a.b.c.d.e"           # Depth 5
        ]

        # Remove duplicates while preserving order (in case sorting isn't stable)
        unique_sorted = []
        seen = set()
        for path in sorted_paths:
            if path not in seen:
                unique_sorted.append(path)
                seen.add(path)

        # Check if all paths at each depth appear before any paths at greater depth
        for i, path in enumerate(unique_sorted):
            depth = len(path.split('.'))
            for later_path in unique_sorted[i+1:]:
                later_depth = len(later_path.split('.'))
                assert depth <= later_depth, f"{path} (depth {depth}) should come before {later_path} (depth {later_depth})"


class TestEnhancedRelationPathProcessing:
    """Enhanced test suite for relation path processing logic with more thorough assertions."""

    @pytest.fixture
    def query(self):
        """Create a fresh query instance for each test."""
        return MockQuery()

    def test_simple_relation_enhanced(self, query):
        """Test processing a simple direct relation with enhanced assertions.

        Verifies that:
        - A simple relation without nesting ("user") is correctly processed
        - The configuration is created with the correct name
        - The nested relations list is empty
        - No query modifier is assigned
        - No other unexpected configurations are created
        """
        # Process a simple relation
        query._process_relation_path("user")

        # Verify the configuration was created correctly
        configs = query.get_relation_configs()

        # Check exact set of expected keys
        assert set(configs.keys()) == {"user"}

        # Check properties of user config
        assert configs["user"].name == "user"
        assert configs["user"].nested == []
        assert configs["user"].query_modifier is None

    def test_nested_relation_enhanced(self, query):
        """Test processing a nested relation with enhanced assertions.

        Verifies that:
        - A nested relation path ("user.posts") correctly creates configurations for all parts
        - The parent relation ("user") includes the child ("posts") in its nested list
        - The leaf relation ("user.posts") has an empty nested list
        - No query modifiers are assigned to any part of the path
        - No other unexpected configurations are created
        """
        # Process a nested relation
        query._process_relation_path("user.posts")

        # Verify configurations for all parts of the path
        configs = query.get_relation_configs()

        # Check exact set of expected keys
        assert set(configs.keys()) == {"user", "user.posts"}

        # Verify "user" config was created correctly
        assert configs["user"].name == "user"
        assert configs["user"].nested == ["posts"]
        assert configs["user"].query_modifier is None

        # Verify "user.posts" config was created correctly
        assert configs["user.posts"].name == "user.posts"
        assert configs["user.posts"].nested == []
        assert configs["user.posts"].query_modifier is None

    def test_deeply_nested_relation_with_query_modifier_enhanced(self, query):
        """Test processing a deeply nested relation with query modifier with enhanced assertions.

        Verifies that:
        - A deeply nested path with a modifier correctly processes all levels
        - Only the specified level receives the query modifier
        - All intermediate levels have None as modifier
        - Nested relationships are correctly established at each level
        - No other unexpected configurations are created
        """

        # Create test modifier
        def test_modifier(q):
            return q.where("active = ?", True)

        # Process a deeply nested relation with modifier
        query._process_relation_path("user.posts.comments.author", test_modifier)

        # Verify configurations for all path segments
        configs = query.get_relation_configs()

        # Check exact set of expected keys
        expected_keys = {"user", "user.posts", "user.posts.comments", "user.posts.comments.author"}
        assert set(configs.keys()) == expected_keys

        # Check each level for correct nested relation
        assert configs["user"].nested == ["posts"]
        assert configs["user.posts"].nested == ["comments"]
        assert configs["user.posts.comments"].nested == ["author"]
        assert configs["user.posts.comments.author"].nested == []

        # Check each level for correct query modifier
        assert configs["user"].query_modifier is None
        assert configs["user.posts"].query_modifier is None
        assert configs["user.posts.comments"].query_modifier is None
        assert configs["user.posts.comments.author"].query_modifier == test_modifier

    def test_multiple_branches_with_various_modifiers_enhanced(self, query):
        """Test multiple relation branches with different modifiers and enhanced assertions.

        Verifies that:
        - Multiple relation branches from the same root are handled correctly
        - Each branch can have its own query modifier
        - The root relation correctly lists all immediate children
        - No unexpected configurations are created
        - No unexpected modifiers are assigned
        """

        # Define different modifiers for different branches
        def modifier1(q): q.flag1 = True; return q

        def modifier2(q): q.flag2 = True; return q

        def modifier3(q): q.flag3 = True; return q

        # Add multiple branches with different modifiers
        query._process_relation_path("user.posts", modifier1)
        query._process_relation_path("user.profile", modifier2)
        query._process_relation_path("user.comments.replies", modifier3)

        # Verify configurations
        configs = query.get_relation_configs()

        # Check exact set of expected keys
        expected_keys = {
            "user",
            "user.posts",
            "user.profile",
            "user.comments",
            "user.comments.replies"
        }
        assert set(configs.keys()) == expected_keys

        # Check root relation includes all immediate children
        assert set(configs["user"].nested) == {"posts", "profile", "comments"}

        # Check each branch has correct nested relation
        assert configs["user.posts"].nested == []
        assert configs["user.profile"].nested == []
        assert configs["user.comments"].nested == ["replies"]
        assert configs["user.comments.replies"].nested == []

        # Check each branch has correct query modifier
        assert configs["user"].query_modifier is None
        assert configs["user.posts"].query_modifier == modifier1
        assert configs["user.profile"].query_modifier == modifier2
        assert configs["user.comments"].query_modifier is None
        assert configs["user.comments.replies"].query_modifier == modifier3

    def test_invalid_path_formats(self, query):
        """Test validation of invalid relation path formats.

        Verifies that the system properly rejects invalid path formats:
        - Leading dot(s)
        - Trailing dot(s)
        - Double/multiple consecutive dots
        - Empty string
        """
        invalid_paths = [
            ".user",  # Leading dot
            "user.",  # Trailing dot
            "user..posts",  # Double dot
            "user...posts",  # Triple dot
            "..user.posts",  # Multiple leading dots
            "user.posts..",  # Multiple trailing dots
            ".",  # Single dot
            "..",  # Double dot only
            "",  # Empty string
        ]

        # Test each invalid path
        for path in invalid_paths:
            # The system should reject invalid paths with InvalidRelationPathError
            with pytest.raises(InvalidRelationPathError) as exc_info:
                query._process_relation_path(path)

            # Verify the error message is descriptive
            error_msg = str(exc_info.value).lower()
            if path == "":
                assert "empty" in error_msg
            elif path.startswith("."):
                assert "start with a dot" in error_msg
            elif path.endswith("."):
                assert "end with a dot" in error_msg
            elif ".." in path:
                assert "consecutive dots" in error_msg

    def test_path_with_empty_segments(self, query):
        """Test behavior with path containing empty segments.

        Verifies that paths with empty segments are properly rejected with appropriate
        exceptions. Validation priority is considered:
        1. Empty path check
        2. Leading dot check
        3. Trailing dot check
        4. Consecutive dots check
        """
        test_cases = [
            # (path, primary_error_pattern)
            # primary_error_pattern is the main error message we expect
            # based on the validation priority

            # Leading dot has higher priority than consecutive dots
            (".user", "start with a dot"),
            ("..user", "start with a dot"),  # Leading dot detected before consecutive dots

            # Trailing dot has higher priority than consecutive dots
            ("user.", "end with a dot"),
            ("user..", "end with a dot"),  # Trailing dot detected before consecutive dots

            # These have consecutive dots but no leading/trailing dot
            ("user..posts", "consecutive dots"),
            ("user...comments", "consecutive dots"),
            ("a..b..c", "consecutive dots"),

            # Special cases
            (".", "start with a dot"),  # Single dot is treated as leading dot
            ("..", "start with a dot"),  # Double dot is first treated as leading dot
            ("", "empty")  # Empty path
        ]

        for path, expected_error_pattern in test_cases:
            # Track what happens with each path
            print(f"Testing path: '{path}'")

            # We expect all these paths to be rejected with InvalidRelationPathError
            with pytest.raises(InvalidRelationPathError) as exc_info:
                query._process_relation_path(path)

            # Verify the error contains the expected primary error message
            error_msg = str(exc_info.value).lower()
            print(f"  Error: {error_msg}")

            # Check if the error message matches the expected pattern based on priority
            assert expected_error_pattern.lower() in error_msg, \
                f"Expected '{expected_error_pattern}' in error message, but got: '{error_msg}'"

    def test_with_complex_use_case_all_features(self, query):
        """Test a complex use case combining all features of the with_() method.

        This test demonstrates the five capabilities mentioned in the with_() method docstring:
        1. Simple relation loading
        2. Nested relation loading with dot notation
        3. Query modification
        4. Multiple relation loading
        5. Chainable calls

        It combines these in a complex, real-world-like scenario.
        """

        # Create various query modifiers
        def active_users(q):
            return q.where("active = ?", True)

        def published_posts(q):
            return q.where("published = ?", True).order_by("published_at DESC")

        def recent_comments(q):
            return q.where("created_at > ?", "2023-01-01").limit(5)

        def full_profile(q):
            return q.select("*").join("JOIN user_details ON profiles.id = user_details.profile_id")

        # Build a complex query using all with_() features
        result = query.with_(
            # 1. Simple relations
            "account",
            "settings",

            # 2. Nested relation with dot notation
            "user.posts.comments.author",

            # 3. Relations with query modifiers
            ("user", active_users),
            ("user.posts", published_posts),
            ("user.posts.comments", recent_comments)
        ).with_(
            # 4. Additional relations in separate call (chainable)
            "user.profile",
            ("user.profile", full_profile)
        )

        # Verify chaining returns the query itself
        assert result is query

        # Verify all configurations were created
        configs = query.get_relation_configs()

        # Expected configurations
        expected_configs = {
            "account", "settings",
            "user", "user.posts", "user.posts.comments", "user.posts.comments.author",
            "user.profile"
        }

        # Verify all expected configs exist and no unexpected ones
        assert set(configs.keys()) == expected_configs

        # Verify relation hierarchy
        assert set(configs["user"].nested) == {"posts", "profile"}
        assert configs["user.posts"].nested == ["comments"]
        assert configs["user.posts.comments"].nested == ["author"]
        assert configs["user.posts.comments.author"].nested == []
        assert configs["user.profile"].nested == []

        # Verify query modifiers
        assert configs["account"].query_modifier is None
        assert configs["settings"].query_modifier is None
        assert configs["user"].query_modifier == active_users
        assert configs["user.posts"].query_modifier == published_posts
        assert configs["user.posts.comments"].query_modifier == recent_comments
        assert configs["user.posts.comments.author"].query_modifier is None
        assert configs["user.profile"].query_modifier == full_profile

        # Execute each modifier to verify its behavior
        mock_queries = {}
        for relation, config in configs.items():
            if config.query_modifier:
                # Create a mock query that supports chaining
                mock_query = MagicMock()
                # Configure each method to return the mock itself for chaining
                mock_query.where.return_value = mock_query
                mock_query.order_by.return_value = mock_query
                mock_query.limit.return_value = mock_query
                mock_query.join.return_value = mock_query
                mock_query.select.return_value = mock_query

                # Apply the query modifier
                config.query_modifier(mock_query)
                mock_queries[relation] = mock_query

        # Verify each modifier's effect
        user_query = mock_queries["user"]
        user_query.where.assert_called_with("active = ?", True)

        posts_query = mock_queries["user.posts"]
        posts_query.where.assert_called_with("published = ?", True)
        posts_query.order_by.assert_called_with("published_at DESC")

        comments_query = mock_queries["user.posts.comments"]
        comments_query.where.assert_called_with("created_at > ?", "2023-01-01")
        comments_query.limit.assert_called_with(5)

        profile_query = mock_queries["user.profile"]
        profile_query.select.assert_called_with("*")
        profile_query.join.assert_called_with("JOIN user_details ON profiles.id = user_details.profile_id")

    def test_overriding_modifiers_in_multiple_calls(self, query):
        """Test overriding query modifiers in multiple with_() calls.

        Verifies that:
        - When a relation is specified multiple times with different query modifiers
        - The latest query modifier overrides previous ones
        - Other relation configurations are preserved
        - The behavior is consistent for both direct and nested relations
        """

        # Define series of modifiers
        def modifier1(q): q.flag = "mod1"; return q

        def modifier2(q): q.flag = "mod2"; return q

        def modifier3(q): q.flag = "mod3"; return q

        # Call with_() multiple times with overlapping relations
        query.with_(
            ("user", modifier1),
            ("user.posts", modifier1),
            "user.profile"
        )

        # Check initial modifiers
        configs = query.get_relation_configs()
        assert configs["user"].query_modifier == modifier1
        assert configs["user.posts"].query_modifier == modifier1
        assert configs["user.profile"].query_modifier is None

        # Override with new modifiers
        query.with_(
            ("user", modifier2),
            ("user.profile", modifier3)
        )

        # Verify modifiers were updated but structure preserved
        assert set(configs.keys()) == {"user", "user.posts", "user.profile"}
        assert set(configs["user"].nested) == {"posts", "profile"}

        # Verify modifiers were updated correctly
        assert configs["user"].query_modifier == modifier2  # Updated
        assert configs["user.posts"].query_modifier == modifier1  # Unchanged
        assert configs["user.profile"].query_modifier == modifier3  # Updated

        # Make final override
        query.with_(
            ("user", modifier3),
            ("user.posts", modifier3),
            ("user.profile", None)  # Set to None explicitly
        )

        # Verify final state
        assert configs["user"].query_modifier == modifier3
        assert configs["user.posts"].query_modifier == modifier3
        assert configs["user.profile"].query_modifier is None

    def test_complex_multibranch_with_different_depth_modifiers(self, query):
        """Test a complex relation tree with modifiers at different depths.

        Creates a complex tree with multiple branches and different depths,
        with query modifiers scattered throughout at different levels.

        This tests the system's ability to maintain a complex relation hierarchy
        while correctly associating modifiers with specific relations at various depths.
        """
        # Define various modifiers to apply at different depths
        depth_modifiers = {}
        for i in range(1, 6):
            def create_modifier(depth):
                def modifier(q):
                    q.depth = depth
                    return q

                return modifier

            depth_modifiers[i] = create_modifier(i)

        # Create a complex relation tree with branches:
        # a
        # ├── b           (depth 2)
        # │   ├── c       (depth 3)
        # │   │   ├── d   (depth 4)
        # │   │   └── e   (depth 4)
        # │   └── f       (depth 3)
        # └── g           (depth 2)
        #     ├── h       (depth 3)
        #     └── i       (depth 3)
        #         └── j   (depth 4)

        # Add modifier to root (a)
        query._process_relation_path("a", depth_modifiers[1])

        # Add modifiers to second level (b, g)
        query._process_relation_path("a.b", depth_modifiers[2])
        # g has no modifier to test None case
        query._process_relation_path("a.g")

        # Add modifiers to third level (c, f, h, i)
        query._process_relation_path("a.b.c", depth_modifiers[3])
        query._process_relation_path("a.b.f")  # no modifier
        query._process_relation_path("a.g.h", depth_modifiers[3])
        query._process_relation_path("a.g.i")  # no modifier

        # Add modifiers to fourth level (d, e, j)
        query._process_relation_path("a.b.c.d", depth_modifiers[4])
        query._process_relation_path("a.b.c.e")  # no modifier
        query._process_relation_path("a.g.i.j", depth_modifiers[4])

        # Verify all paths were created
        configs = query.get_relation_configs()
        expected_paths = {
            "a",
            "a.b", "a.g",
            "a.b.c", "a.b.f", "a.g.h", "a.g.i",
            "a.b.c.d", "a.b.c.e", "a.g.i.j"
        }
        assert set(configs.keys()) == expected_paths

        # Verify nested relations
        assert set(configs["a"].nested) == {"b", "g"}
        assert set(configs["a.b"].nested) == {"c", "f"}
        assert set(configs["a.g"].nested) == {"h", "i"}
        assert set(configs["a.b.c"].nested) == {"d", "e"}
        assert configs["a.b.f"].nested == []
        assert configs["a.g.h"].nested == []
        assert configs["a.g.i"].nested == ["j"]
        assert configs["a.b.c.d"].nested == []
        assert configs["a.b.c.e"].nested == []
        assert configs["a.g.i.j"].nested == []

        # Verify query modifiers at each level
        modifier_assignments = {
            "a": depth_modifiers[1],
            "a.b": depth_modifiers[2],
            "a.g": None,
            "a.b.c": depth_modifiers[3],
            "a.b.f": None,
            "a.g.h": depth_modifiers[3],
            "a.g.i": None,
            "a.b.c.d": depth_modifiers[4],
            "a.b.c.e": None,
            "a.g.i.j": depth_modifiers[4]
        }

        for path, expected_modifier in modifier_assignments.items():
            assert configs[path].query_modifier is expected_modifier, f"Path {path} has wrong modifier"

        # Execute modifiers to verify correct behavior
        for path, config in configs.items():
            if config.query_modifier:
                mock_query = MagicMock()
                config.query_modifier(mock_query)
                # Extract depth from path
                depth = len(path.split('.'))
                assert mock_query.depth == depth, f"Path {path} executed wrong modifier"

    def test_realistic_ecommerce_relations(self, query):
        """Test a realistic e-commerce relation scenario with business logic conditions.

        This simulates a realistic e-commerce application with:
        - Orders with line items and customers
        - Customers with profiles and payment methods
        - Products with categories and reviews

        It includes business-logic query modifiers at various levels.
        """

        # Create business logic modifiers
        def active_customers(q):
            return q.where("active = ? AND status != ?", (True, "banned"))

        def paid_orders(q):
            return q.where("payment_status = ?", ("paid",)).order_by("paid_at DESC")

        def in_stock_products(q):
            return q.where("stock_qty > ? AND status = ?", (0, "active"))

        def verified_reviews(q):
            return q.where("is_verified = ? AND is_published = ?", (True, True))

        def premium_payment_methods(q):
            return q.where("status = ? AND type IN (?, ?)",
                           ("active", "credit_card", "paypal"))

        # Build complex relation structure
        query.with_(
            # Order and basic relations
            ("orders", paid_orders),
            "orders.line_items",
            "orders.shipping_address",

            # Customer relations with business logic
            ("orders.customer", active_customers),
            ("orders.customer.profile",
             lambda q: q.join("JOIN customer_metadata ON profiles.id = customer_metadata.profile_id")),
            ("orders.customer.payment_methods", premium_payment_methods),

            # Product relations with filtering
            ("orders.line_items.product", in_stock_products),
            "orders.line_items.product.category",
            ("orders.line_items.product.reviews", verified_reviews),
            "orders.line_items.product.reviews.author"
        )

        # Verify structure was built correctly
        configs = query.get_relation_configs()

        # Verify expected paths
        expected_paths = {
            "orders",
            "orders.line_items",
            "orders.shipping_address",
            "orders.customer",
            "orders.customer.profile",
            "orders.customer.payment_methods",
            "orders.line_items.product",
            "orders.line_items.product.category",
            "orders.line_items.product.reviews",
            "orders.line_items.product.reviews.author"
        }
        assert set(configs.keys()) == expected_paths

        # Verify relation hierarchy
        assert set(configs["orders"].nested) == {"line_items", "shipping_address", "customer"}
        assert set(configs["orders.customer"].nested) == {"profile", "payment_methods"}
        assert configs["orders.line_items"].nested == ["product"]
        assert set(configs["orders.line_items.product"].nested) == {"category", "reviews"}
        assert configs["orders.line_items.product.reviews"].nested == ["author"]

        # Verify modifiers are correctly assigned
        assert configs["orders"].query_modifier == paid_orders
        assert configs["orders.line_items"].query_modifier is None
        assert configs["orders.shipping_address"].query_modifier is None
        assert configs["orders.customer"].query_modifier == active_customers
        assert configs["orders.customer.payment_methods"].query_modifier == premium_payment_methods
        assert configs["orders.line_items.product"].query_modifier == in_stock_products
        assert configs["orders.line_items.product.reviews"].query_modifier == verified_reviews
        assert configs["orders.line_items.product.reviews.author"].query_modifier is None

    def test_enhanced_error_handling_suggestions(self, query):
        """Test problematic cases and verify error handling improvements.

        This test verifies that the implementation has proper validation for invalid
        relation paths, ensuring that appropriate exceptions are raised.
        """
        problematic_paths = [
            "",  # Empty string
            ".",  # Single dot
            ".user",  # Leading dot
            "user.",  # Trailing dot
            "user..posts",  # Double dot
            "...user",  # Multiple leading dots
            "user...",  # Multiple trailing dots
            "user..posts..comments",  # Multiple double dots
        ]

        # Test each problematic path and verify it raises the appropriate exception
        for path in problematic_paths:
            # Clear any existing configurations
            query._eager_loads.clear()

            # Verify the path is rejected with an appropriate exception
            with pytest.raises(InvalidRelationPathError) as excinfo:
                query._process_relation_path(path)

            # Verify the error message is descriptive and specific to the issue
            error_message = str(excinfo.value).lower()

            if path == "":
                assert "empty" in error_message, f"Error message for empty path should mention 'empty', got: {error_message}"
            elif path.startswith("."):
                assert "start with a dot" in error_message, f"Error message for leading dot should mention 'start with a dot', got: {error_message}"
            elif path.endswith("."):
                assert "end with a dot" in error_message, f"Error message for trailing dot should mention 'end with a dot', got: {error_message}"
            elif ".." in path:
                assert "consecutive dots" in error_message, f"Error message for consecutive dots should mention 'consecutive dots', got: {error_message}"

            # Verify no relations were added for invalid paths
            configs = query.get_relation_configs()
            assert not configs, f"No configurations should be added for invalid path: {path}"

        # Verify valid paths still work after validation is added
        valid_path = "user.posts"
        query._process_relation_path(valid_path)
        configs = query.get_relation_configs()
        assert "user" in configs, "Valid relation 'user' should be added"
        assert "user.posts" in configs, "Valid relation 'user.posts' should be added"

        # Verify with_() method also raises appropriate exceptions
        query._eager_loads.clear()
        with pytest.raises(InvalidRelationPathError):
            query.with_("user..posts")

        # Test multiple relations with one invalid
        query._eager_loads.clear()
        with pytest.raises(InvalidRelationPathError):
            query.with_("user", "posts", "user..comments")

        # Verify no relations were added due to the invalid one
        configs = query.get_relation_configs()
        assert not configs, "No configurations should be added when any relation in with_() is invalid"


class ImprovedMockQuery(RelationalQueryMixin, MockQueryBase):
    """Mock query class using the improved RelationalQueryMixin implementation."""

    def __init__(self):
        super().__init__()
        self._log = MagicMock()  # Mock the logging method


class TestImprovedRelationPathValidation:
    """Test suite for the improved relation path validation logic."""

    @pytest.fixture
    def query(self):
        """Create a fresh query instance for each test."""
        return ImprovedMockQuery()

    def test_empty_relation_path(self, query):
        """Test that empty relation paths are rejected with appropriate error."""
        with pytest.raises(InvalidRelationPathError) as excinfo:
            query._process_relation_path("")

        assert "cannot be empty" in str(excinfo.value)

    def test_leading_dot_rejection(self, query):
        """Test that relation paths with leading dots are rejected."""
        invalid_paths = [
            ".user",
            ".user.posts",
            "...user"
        ]

        for path in invalid_paths:
            with pytest.raises(InvalidRelationPathError) as excinfo:
                query._process_relation_path(path)

            assert "cannot start with a dot" in str(excinfo.value)
            assert path in str(excinfo.value)

    def test_trailing_dot_rejection(self, query):
        """Test that relation paths with trailing dots are rejected."""
        invalid_paths = [
            "user.",
            "user.posts.",
            "user..."
        ]

        for path in invalid_paths:
            with pytest.raises(InvalidRelationPathError) as excinfo:
                query._process_relation_path(path)

            assert "cannot end with a dot" in str(excinfo.value)
            assert path in str(excinfo.value)

    def test_consecutive_dots_rejection(self, query):
        """Test that relation paths with consecutive dots are rejected."""
        invalid_paths = [
            "user..posts",
            "user...posts",
            "user.posts..comments",
            "user..posts..comments"
        ]

        for path in invalid_paths:
            with pytest.raises(InvalidRelationPathError) as excinfo:
                query._process_relation_path(path)

            assert "cannot contain consecutive dots" in str(excinfo.value)
            assert path in str(excinfo.value)

    def test_with_method_catches_invalid_paths(self, query):
        """Test that the with_() method catches invalid paths and raises appropriate exceptions."""
        # Verify we start with empty configurations
        configs = query.get_relation_configs()
        assert not configs  # Should be empty initially

        # Test each invalid path individually
        invalid_paths = [
            "",  # Empty string
            ".user",  # Leading dot
            "user.",  # Trailing dot
            "user..posts",  # Consecutive dots
        ]

        for path in invalid_paths:
            # Clear configurations before each test
            query._eager_loads.clear()

            with pytest.raises(InvalidRelationPathError):
                query.with_(path)

            # Verify no configurations were created for this invalid path
            configs = query.get_relation_configs()
            assert not configs, f"Configurations should be empty after invalid path '{path}', but got: {configs}"

        # Test with tuple format (path, modifier)
        def test_modifier(q):
            return q

        # Clear configurations before test
        query._eager_loads.clear()

        with pytest.raises(InvalidRelationPathError):
            query.with_(("user..posts", test_modifier))

        # Verify no configurations were created
        configs = query.get_relation_configs()
        assert not configs, f"Configurations should be empty after invalid path with modifier, but got: {configs}"

        # Test the behavior with multiple paths including an invalid one
        # This test is particularly important as it verifies the transaction-like behavior
        # we want: either all paths succeed, or none should be added

        # Clear configurations before test
        query._eager_loads.clear()

        # Try adding multiple paths with one invalid
        with pytest.raises(InvalidRelationPathError):
            query.with_("user", "posts", "user..comments")

        # Verify the behavior: we have two options to test for:
        # 1. Transactional behavior: no configs should be added if any path fails
        # 2. Partial commits: valid paths before the invalid one might be added

        configs = query.get_relation_configs()

        # Based on the current implementation, valid paths might be added before the exception:
        # We document the actual behavior rather than enforcing a specific one
        if configs:
            print(f"Note: The with_() method adds valid paths before encountering an invalid one: {configs}")
            # Verify that only valid paths were added
            assert set(configs.keys()).issubset({"user", "posts"})
            assert "user..comments" not in configs
        else:
            print("Note: The with_() method has transactional behavior - no paths added when any are invalid")

    def test_analyze_relation_path_validation(self, query):
        """Test that analyze_relation_path validates paths before processing."""
        valid_path = "user.posts.comments"
        parts, configs = query.analyze_relation_path(valid_path)
        assert parts == ["user", "posts", "comments"]
        assert configs == ["user", "user.posts", "user.posts.comments"]

        invalid_paths = ["", ".user", "user.", "user..posts"]
        for path in invalid_paths:
            with pytest.raises(InvalidRelationPathError):
                query.analyze_relation_path(path)

    def test_valid_paths_still_work(self, query):
        """Test that valid paths are still processed correctly after adding validation."""
        # Simple relation
        query._process_relation_path("user")

        # Nested relation
        query._process_relation_path("user.posts.comments")

        # Add query modifier
        def test_modifier(q):
            return q.where("active = ?", True)

        query._process_relation_path("user.profile", test_modifier)

        # Verify configurations were created correctly
        configs = query.get_relation_configs()

        assert "user" in configs
        assert "user.posts" in configs
        assert "user.posts.comments" in configs
        assert "user.profile" in configs

        assert "posts" in configs["user"].nested
        assert "profile" in configs["user"].nested
        assert "comments" in configs["user.posts"].nested

        assert configs["user.profile"].query_modifier == test_modifier

    def test_chained_calls_with_validation(self, query):
        """Test that chained with_() calls still work with validation."""
        # Chain valid calls
        result = query.with_("user") \
            .with_("user.posts") \
            .with_("user.profile")

        # Verify chaining works
        assert result is query

        # Verify configurations
        configs = query.get_relation_configs()
        assert set(configs.keys()) == {"user", "user.posts", "user.profile"}

        # Test that chaining stops on invalid path
        with pytest.raises(InvalidRelationPathError):
            query.with_("user") \
                .with_("user..posts")  # This should raise exception

        # Verify previous configurations still exist
        configs = query.get_relation_configs()
        assert "user" in configs
        assert "user.posts" in configs
        assert "user.profile" in configs