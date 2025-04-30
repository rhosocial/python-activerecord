"""Test recursive CTE functionality in ActiveQuery."""
from decimal import Decimal

import pytest
from .utils import create_order_fixtures, create_tree_fixtures

# Create multi-table test fixtures
order_fixtures = create_order_fixtures()
tree_fixtures = create_tree_fixtures()


def test_recursive_cte_basics(tree_fixtures):
    """Test basic recursive CTE functionality using tree structure"""
    Node = tree_fixtures[0]

    # Create a tree structure:
    # 1
    # ├── 2
    # │   ├── 4
    # │   └── 5
    # └── 3
    #     └── 6

    nodes = [
        Node(id=1, name="Root", parent_id=None),
        Node(id=2, name="Child 1", parent_id=1),
        Node(id=3, name="Child 2", parent_id=1),
        Node(id=4, name="Grandchild 1", parent_id=2),
        Node(id=5, name="Grandchild 2", parent_id=2),
        Node(id=6, name="Grandchild 3", parent_id=3),
    ]

    for node in nodes:
        node.save()

    # Define a recursive CTE to traverse the tree
    recursive_sql = """
                    SELECT id, name, parent_id, 1 as level \
                    FROM nodes \
                    WHERE id = 1
                    UNION ALL
                    SELECT n.id, n.name, n.parent_id, t.level + 1
                    FROM nodes n
                             JOIN tree t ON n.parent_id = t.id \
                    """

    query = Node.query().with_recursive_cte("tree", recursive_sql)
    query.from_cte("tree")
    query.order_by("level, id")

    results = query.to_dict(direct_dict=True).all()

    # Verify the tree traversal
    assert len(results) == 6
    assert results[0]['id'] == 1 and results[0]['level'] == 1  # Root
    assert results[1]['id'] == 2 and results[1]['level'] == 2  # Level 2
    assert results[2]['id'] == 3 and results[2]['level'] == 2  # Level 2
    assert results[3]['id'] == 4 and results[3]['level'] == 3  # Level 3
    assert results[4]['id'] == 5 and results[4]['level'] == 3  # Level 3
    assert results[5]['id'] == 6 and results[5]['level'] == 3  # Level 3


def test_recursive_cte_with_depth_limit(tree_fixtures):
    """Test recursive CTE with depth limiting condition"""
    Node = tree_fixtures[0]

    # Create a tree structure:
    # 1
    # ├── 2
    # │   ├── 4
    # │   └── 5
    # └── 3
    #     └── 6

    nodes = [
        Node(id=1, name="Root", parent_id=None),
        Node(id=2, name="Child 1", parent_id=1),
        Node(id=3, name="Child 2", parent_id=1),
        Node(id=4, name="Grandchild 1", parent_id=2),
        Node(id=5, name="Grandchild 2", parent_id=2),
        Node(id=6, name="Grandchild 3", parent_id=3),
    ]

    for node in nodes:
        node.save()

    # Define a recursive CTE with max depth limit
    recursive_sql = """
                    SELECT id, name, parent_id, 1 as level \
                    FROM nodes \
                    WHERE id = 1
                    UNION ALL
                    SELECT n.id, n.name, n.parent_id, t.level + 1
                    FROM nodes n
                             JOIN tree t ON n.parent_id = t.id
                    WHERE t.level < 2 \
                    """ #  -- Limit recursion to depth 2

    query = Node.query().with_recursive_cte("tree", recursive_sql)
    query.from_cte("tree")
    query.order_by("level, id")

    results = query.to_dict(direct_dict=True).all()

    # Verify the tree traversal is limited to 2 levels
    assert len(results) == 3
    assert results[0]['id'] == 1 and results[0]['level'] == 1  # Root
    assert results[1]['id'] == 2 and results[1]['level'] == 2  # Level 2
    assert results[2]['id'] == 3 and results[2]['level'] == 2  # Level 2


def test_recursive_cte_find_path(tree_fixtures):
    """Test recursive CTE to find path between nodes"""
    Node = tree_fixtures[0]

    # Create a tree structure:
    # 1
    # ├── 2
    # │   ├── 4
    # │   └── 5
    # └── 3
    #     └── 6

    nodes = [
        Node(id=1, name="Root", parent_id=None),
        Node(id=2, name="Child 1", parent_id=1),
        Node(id=3, name="Child 2", parent_id=1),
        Node(id=4, name="Grandchild 1", parent_id=2),
        Node(id=5, name="Grandchild 2", parent_id=2),
        Node(id=6, name="Grandchild 3", parent_id=3),
    ]

    for node in nodes:
        node.save()

    # Find path from root to node 5 (Root -> Child 1 -> Grandchild 2)
    recursive_sql = """
                    -- Anchor member: start with target node
                    SELECT id, name, parent_id, CAST(id AS TEXT) as path
                    FROM nodes \
                    WHERE id = 5

                    UNION ALL

                    -- Recursive member: add parent nodes
                    SELECT n.id, n.name, n.parent_id, CAST(n.id AS TEXT) || ',' || t.path
                    FROM nodes n
                             JOIN path_finder t ON n.id = t.parent_id \
                    """

    query = Node.query().with_recursive_cte("path_finder", recursive_sql)
    query.from_cte("path_finder")
    query.order_by("length(path) DESC")  # Longest path first (complete path)

    results = query.to_dict(direct_dict=True).all()

    # Verify the path
    assert len(results) == 3  # Path length is 3: Root -> Child 1 -> Grandchild 2
    assert results[0]['path'] == '1,2,5'  # Complete path with node IDs
    assert results[0]['id'] == 1  # Root node
    assert results[1]['id'] == 2  # Child 1
    assert results[2]['id'] == 5  # Grandchild 2 (target)


def test_recursive_cte_cycles(tree_fixtures):
    """Test recursive CTE with cycle detection"""
    Node = tree_fixtures[0]

    # Create a circular reference
    nodes = [
        Node(id=1, name="Node 1", parent_id=None),  # Creates a cycle
        Node(id=2, name="Node 2", parent_id=1),
        Node(id=3, name="Node 3", parent_id=2),
    ]

    for node in nodes:
        node.save()

    nodes[0].parent_id = 3
    nodes[0].save()

    # Recursive CTE with cycle detection
    recursive_sql = """
                    SELECT id, name, parent_id, 1 as level, CAST(id AS TEXT) as path
                    FROM nodes \
                    WHERE id = 1

                    UNION ALL

                    SELECT n.id, n.name, n.parent_id, t.level + 1, t.path || ',' || CAST(n.id AS TEXT)
                    FROM nodes n
                             JOIN tree t ON n.parent_id = t.id
                    -- Prevent infinite recursion by detecting cycles
                    WHERE t.path NOT LIKE '%,' || CAST(n.id AS TEXT) || '%'
                      AND t.level < 10 \
                    """ #  -- Safety limit

    query = Node.query().with_recursive_cte("tree", recursive_sql)
    query.from_cte("tree")
    query.order_by("level")

    results = query.to_dict(direct_dict=True).all()

    # Verify that the cycle was handled properly
    # Should produce a finite set of results despite cyclic references
    assert len(results) <= 10, "Query should terminate despite cycles"


def test_recursive_cte_with_aggregation(tree_fixtures):
    """Test combining recursive CTE with aggregation"""
    Node = tree_fixtures[0]

    # Create a tree structure:
    # 1
    # ├── 2
    # │   ├── 4
    # │   └── 5
    # └── 3
    #     └── 6

    nodes = [
        Node(id=1, name="Root", parent_id=None, value=100),
        Node(id=2, name="Child 1", parent_id=1, value=50),
        Node(id=3, name="Child 2", parent_id=1, value=50),
        Node(id=4, name="Grandchild 1", parent_id=2, value=20),
        Node(id=5, name="Grandchild 2", parent_id=2, value=30),
        Node(id=6, name="Grandchild 3", parent_id=3, value=50),
    ]

    for node in nodes:
        node.save()

    # First, define recursive CTE to traverse the tree
    recursive_sql = """
                    SELECT id, name, parent_id, value, 1 as level \
                    FROM nodes \
                    WHERE id = 1
                    UNION ALL
                    SELECT n.id, n.name, n.parent_id, n.value, t.level + 1
                    FROM nodes n
                             JOIN tree t ON n.parent_id = t.id \
                    """

    # Create query with CTE
    query = Node.query().with_recursive_cte("tree", recursive_sql)

    # Use CTE with aggregation by level
    query.from_cte("tree")
    query.group_by("tree.level")
    query.select("tree.level")
    query.count("*", "node_count")
    query.sum("tree.value", "total_value")

    # Order by level
    query.order_by("level")

    results = query.aggregate()

    # Verify aggregated results by level
    assert len(results) == 3  # 3 levels in the tree

    assert results[0]['level'] == 1
    assert results[0]['node_count'] == 1  # Root level
    assert results[0]['total_value'] == 100

    assert results[1]['level'] == 2
    assert results[1]['node_count'] == 2  # Two children
    assert results[1]['total_value'] == 100

    assert results[2]['level'] == 3
    assert results[2]['node_count'] == 3  # Three grandchildren
    assert results[2]['total_value'] == 100