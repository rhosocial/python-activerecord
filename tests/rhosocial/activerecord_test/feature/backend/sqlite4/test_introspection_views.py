# tests/rhosocial/activerecord_test/feature/backend/sqlite4/test_introspection_views.py
"""
Tests for SQLite view introspection.

This module tests the list_views, get_view_info, and view_exists methods
for retrieving view metadata.
"""

import pytest

from rhosocial.activerecord.backend.introspection.types import (
    ViewInfo,
)


class TestListViews:
    """Tests for list_views method."""

    def test_list_views_empty_database(self, sqlite_backend):
        """Test list_views on database without views."""
        views = sqlite_backend.list_views()

        assert isinstance(views, list)
        assert len(views) == 0

    def test_list_views_with_view(self, backend_with_view):
        """Test list_views returns created views."""
        views = backend_with_view.list_views()

        view_names = [v.name for v in views]
        assert "user_posts_summary" in view_names

    def test_list_views_returns_view_info(self, backend_with_view):
        """Test that list_views returns ViewInfo objects."""
        views = backend_with_view.list_views()

        for view in views:
            assert isinstance(view, ViewInfo)

    def test_list_views_schema(self, backend_with_view):
        """Test that schema is correctly set."""
        views = backend_with_view.list_views()

        for view in views:
            assert view.schema == "main"

    def test_list_views_caching(self, backend_with_view):
        """Test that view list is cached."""
        views1 = backend_with_view.list_views()
        views2 = backend_with_view.list_views()

        # Should return the same cached list
        assert views1 is views2

    def test_list_views_exclude_system(self, sqlite_backend):
        """Test that system views are excluded by default."""
        views = sqlite_backend.list_views(include_system=False)

        # SQLite doesn't have system views like other databases
        # This test documents the expected behavior
        assert isinstance(views, list)


class TestGetViewInfo:
    """Tests for get_view_info method."""

    def test_get_view_info_existing(self, backend_with_view):
        """Test get_view_info for existing view."""
        view_info = backend_with_view.get_view_info("user_posts_summary")

        assert view_info is not None
        assert isinstance(view_info, ViewInfo)
        assert view_info.name == "user_posts_summary"
        assert view_info.schema == "main"

    def test_get_view_info_nonexistent(self, sqlite_backend):
        """Test get_view_info for non-existent view."""
        view_info = sqlite_backend.get_view_info("nonexistent")

        assert view_info is None

    def test_get_view_info_definition(self, backend_with_view):
        """Test that view definition is returned."""
        view_info = backend_with_view.get_view_info("user_posts_summary")

        assert view_info is not None
        assert view_info.definition is not None
        assert "SELECT" in view_info.definition.upper()
        assert "users" in view_info.definition.lower()

    def test_get_view_info_caching(self, backend_with_view):
        """Test that view info is cached."""
        info1 = backend_with_view.get_view_info("user_posts_summary")
        info2 = backend_with_view.get_view_info("user_posts_summary")

        # Should return the same cached object
        assert info1 is info2


class TestViewExists:
    """Tests for view_exists method."""

    def test_view_exists_true(self, backend_with_view):
        """Test view_exists returns True for existing view."""
        assert backend_with_view.view_exists("user_posts_summary") is True

    def test_view_exists_false(self, sqlite_backend):
        """Test view_exists returns False for non-existent view."""
        assert sqlite_backend.view_exists("nonexistent") is False

    def test_view_exists_distinguishes_from_table(self, backend_with_view):
        """Test that view_exists distinguishes views from tables."""
        # Tables should not be returned as views
        assert backend_with_view.view_exists("users") is False
        assert backend_with_view.table_exists("users") is True


class TestViewDetails:
    """Tests for detailed view information."""

    def test_multiple_views(self, sqlite_backend):
        """Test multiple views in database."""
        sqlite_backend.executescript("""
            CREATE VIEW view1 AS SELECT 1 AS col;
            CREATE VIEW view2 AS SELECT 2 AS col;
            CREATE VIEW view3 AS SELECT 3 AS col;
        """)

        views = sqlite_backend.list_views()

        view_names = {v.name for v in views}
        assert "view1" in view_names
        assert "view2" in view_names
        assert "view3" in view_names

    def test_complex_view_definition(self, sqlite_backend):
        """Test complex view definition."""
        sqlite_backend.executescript("""
            CREATE TABLE orders (
                id INTEGER PRIMARY KEY,
                user_id INTEGER,
                amount REAL,
                created_at TEXT
            );

            CREATE VIEW order_summary AS
            SELECT
                user_id,
                COUNT(*) AS order_count,
                SUM(amount) AS total_amount
            FROM orders
            GROUP BY user_id
            HAVING SUM(amount) > 100;
        """)

        view_info = sqlite_backend.get_view_info("order_summary")

        assert view_info is not None
        assert view_info.definition is not None
        assert "GROUP BY" in view_info.definition.upper()
        assert "HAVING" in view_info.definition.upper()

    def test_view_with_join(self, backend_with_view):
        """Test view with JOIN definition."""
        view_info = backend_with_view.get_view_info("user_posts_summary")

        assert view_info is not None
        definition = view_info.definition.upper()
        assert "JOIN" in definition or "LEFT" in definition
