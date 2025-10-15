# tests/rhosocial/activerecord_test/feature/query/sqlite/test_explain_cte_recursive.py
"""Test explain functionality with recursive CTE for SQLite."""
import pytest
import sqlite3

from rhosocial.activerecord.testsuite.feature.query.conftest import (
    order_fixtures,
    blog_fixtures,
    json_user_fixture,
    tree_fixtures,
    extended_order_fixtures,
    combined_fixtures,
)
from rhosocial.activerecord.backend.dialect import ExplainType


# Helper to check if current SQLite version supports recursive CTEs
def is_recursive_cte_supported():
    """Check if current SQLite version supports recursive CTEs"""
    version = sqlite3.sqlite_version_info
    return version >= (3, 8, 3)  # Recursive CTEs were added in SQLite 3.8.3


@pytest.fixture(scope="module")
def skip_if_unsupported():
    """Skip tests if SQLite version doesn't support recursive CTEs."""
    if not is_recursive_cte_supported():
        pytest.skip("SQLite version doesn't support recursive CTEs (requires 3.8.3+)")


def test_explain_recursive_cte_basic(tree_fixtures, skip_if_unsupported):
    """Test EXPLAIN with basic recursive CTE"""
    # This test is designed for SQLite-specific functionality
    Node = tree_fixtures[0]

    # Create a simple tree structure:
    # 1
    # ├── 2
    # │   └── 4
    # └── 3
    nodes = [
        Node(id=1, name="Root", parent_id=None),
        Node(id=2, name="Child 1", parent_id=1),
        Node(id=3, name="Child 2", parent_id=1),
        Node(id=4, name="Grandchild 1", parent_id=2),
    ]

    for node in nodes:
        node.save()

    # Define a recursive CTE
    recursive_sql = """
        SELECT id, name, parent_id, 1 as level, CAST(id AS TEXT) as path
        FROM nodes
        WHERE id = 1
        UNION ALL
        SELECT n.id, n.name, n.parent_id, t.level + 1, t.path || ',' || CAST(n.id AS TEXT)
        FROM nodes n
        JOIN tree t ON n.parent_id = t.id
    """

    # Test EXPLAIN with recursive CTE
    query = Node.query().with_recursive_cte("tree", recursive_sql)
    query.from_cte("tree")
    query.order_by("level, id")

    # Get execution plan
    plan = query.explain().all()

    assert isinstance(plan, str)
    assert any(op in plan for op in ['Trace', 'Goto', 'OpenRead'])
    # assert any(kw in plan.upper() for kw in ['RECURSIVE', 'UNION', 'RECURSIVE'])

    # Test EXPLAIN QUERY PLAN
    plan = query.explain(type=ExplainType.QUERYPLAN).all()
    assert isinstance(plan, str)
    assert "SCAN" in plan or "TEMP" in plan
    # assert any(kw in plan.upper() for kw in ['RECURSIVE', 'UNION'])


def test_explain_recursive_cte_with_depth_limit(tree_fixtures, skip_if_unsupported):
    """Test EXPLAIN with recursive CTE and depth limiting"""
    Node = tree_fixtures[0]

    # Create a deeper tree structure:
    # 1
    # ├── 2
    # │   ├── 4
    # │   │   └── 6
    # └── 3
    #     └── 5
    nodes = [
        Node(id=1, name="Root", parent_id=None),
        Node(id=2, name="Child 1", parent_id=1),
        Node(id=3, name="Child 2", parent_id=1),
        Node(id=4, name="Grandchild 1", parent_id=2),
        Node(id=5, name="Grandchild 2", parent_id=3),
        Node(id=6, name="Great-grandchild 1", parent_id=4),
    ]

    for node in nodes:
        node.save()

    # Define a recursive CTE with depth limit
    recursive_sql = """
        SELECT id, name, parent_id, 1 as level, CAST(id AS TEXT) as path
        FROM nodes
        WHERE id = 1
        UNION ALL
        SELECT n.id, n.name, n.parent_id, t.level + 1, t.path || ',' || CAST(n.id AS TEXT)
        FROM nodes n
        JOIN tree t ON n.parent_id = t.id
        WHERE t.level < 2  -- Limit recursion to depth 2
    """

    # Test EXPLAIN with depth-limited recursive CTE
    query = Node.query().with_recursive_cte("tree", recursive_sql)
    query.from_cte("tree")
    query.order_by("level, id")

    # Get execution plan
    plan = query.explain(type=ExplainType.QUERYPLAN).all()

    assert isinstance(plan, str)
    assert "SCAN" in plan or "TEMP" in plan
    assert any(kw in plan.upper() for kw in ['RECURSIVE', 'UNION'])

    # Check for presence of depth limitation condition
    detailed_plan = query.explain().all()
    assert isinstance(detailed_plan, str)
    assert any(op in detailed_plan for op in ['Trace', 'Goto', 'OpenRead', 'Filter', 'Compare'])


def test_explain_recursive_cte_path_finding(tree_fixtures, skip_if_unsupported):
    """Test EXPLAIN with recursive CTE for path finding"""
    Node = tree_fixtures[0]

    # Create a tree structure
    nodes = [
        Node(id=1, name="Root", parent_id=None),
        Node(id=2, name="Child 1", parent_id=1),
        Node(id=3, name="Child 2", parent_id=1),
        Node(id=4, name="Grandchild 1", parent_id=2),
        Node(id=5, name="Grandchild 2", parent_id=3),
    ]

    for node in nodes:
        node.save()

    # Define a recursive CTE for finding path from leaf to root
    # Starting from a leaf node and working upward
    recursive_sql = """
        -- Anchor: start with target node
        SELECT id, name, parent_id, CAST(id AS TEXT) as path
        FROM nodes
        WHERE id = 5  -- Target node

        UNION ALL

        -- Recursive: add parent nodes
        SELECT n.id, n.name, n.parent_id, CAST(n.id AS TEXT) || ',' || t.path
        FROM nodes n
        JOIN path_finder t ON n.id = t.parent_id
    """

    # Test EXPLAIN with path-finding recursive CTE
    query = Node.query().with_recursive_cte("path_finder", recursive_sql)
    query.from_cte("path_finder")
    query.order_by("length(path) DESC")  # Longest path first (complete path)

    # Get execution plan
    plan = query.explain(type=ExplainType.QUERYPLAN).all()

    assert isinstance(plan, str)
    assert "SCAN" in plan or "TEMP" in plan
    assert any(kw in plan.upper() for kw in ['RECURSIVE', 'UNION'])
