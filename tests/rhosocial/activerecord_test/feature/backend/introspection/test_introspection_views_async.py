# tests/rhosocial/activerecord_test/feature/backend/introspection/test_introspection_views_async.py
"""Async twin of test_introspection_views.py for SQLite view introspection."""

import pytest

from rhosocial.activerecord.backend.introspection.types import (
    ViewInfo,
)


class TestAsyncListViews:
    """Tests for list_views method."""

    @pytest.mark.asyncio
    async def test_list_views_empty_database(self, async_sqlite_memory_backend):
        """Test list_views on database without views."""
        views = await async_sqlite_memory_backend.introspector.list_views()

        assert isinstance(views, list)
        assert len(views) == 0

    @pytest.mark.asyncio
    async def test_list_views_with_view(self, async_backend_with_view):
        """Test list_views returns created views."""
        views = await async_backend_with_view.introspector.list_views()

        view_names = [v.name for v in views]
        assert "user_posts_summary" in view_names

    @pytest.mark.asyncio
    async def test_list_views_returns_view_info(self, async_backend_with_view):
        """Test that list_views returns ViewInfo objects."""
        views = await async_backend_with_view.introspector.list_views()

        for view in views:
            assert isinstance(view, ViewInfo)

    @pytest.mark.asyncio
    async def test_list_views_schema(self, async_backend_with_view):
        """Test that schema is correctly set."""
        views = await async_backend_with_view.introspector.list_views()

        for view in views:
            assert view.schema == "main"

    @pytest.mark.asyncio
    async def test_list_views_caching(self, async_backend_with_view):
        """Test that view list is cached."""
        views1 = await async_backend_with_view.introspector.list_views()
        views2 = await async_backend_with_view.introspector.list_views()

        assert views1 is views2

    @pytest.mark.asyncio
    async def test_list_views_exclude_system(self, async_sqlite_memory_backend):
        """Test that system views are excluded by default."""
        views = await async_sqlite_memory_backend.introspector.list_views(include_system=False)

        assert isinstance(views, list)


class TestAsyncGetViewInfo:
    """Tests for get_view_info method."""

    @pytest.mark.asyncio
    async def test_get_view_info_existing(self, async_backend_with_view):
        """Test get_view_info for existing view."""
        view_info = await async_backend_with_view.introspector.get_view_info("user_posts_summary")

        assert view_info is not None
        assert isinstance(view_info, ViewInfo)
        assert view_info.name == "user_posts_summary"
        assert view_info.schema == "main"

    @pytest.mark.asyncio
    async def test_get_view_info_nonexistent(self, async_sqlite_memory_backend):
        """Test get_view_info for non-existent view."""
        view_info = await async_sqlite_memory_backend.introspector.get_view_info("nonexistent")

        assert view_info is None

    @pytest.mark.asyncio
    async def test_get_view_info_definition(self, async_backend_with_view):
        """Test that view definition is returned."""
        view_info = await async_backend_with_view.introspector.get_view_info("user_posts_summary")

        assert view_info is not None
        assert view_info.definition is not None
        assert "SELECT" in view_info.definition.upper()
        assert "users" in view_info.definition.lower()

    @pytest.mark.asyncio
    async def test_get_view_info_caching(self, async_backend_with_view):
        """Test that view info is cached."""
        info1 = await async_backend_with_view.introspector.get_view_info("user_posts_summary")
        info2 = await async_backend_with_view.introspector.get_view_info("user_posts_summary")

        assert info1 is info2


class TestAsyncViewExists:
    """Tests for view_exists method."""

    @pytest.mark.asyncio
    async def test_view_exists_true(self, async_backend_with_view):
        """Test view_exists returns True for existing view."""
        assert await async_backend_with_view.introspector.view_exists("user_posts_summary") is True

    @pytest.mark.asyncio
    async def test_view_exists_false(self, async_sqlite_memory_backend):
        """Test view_exists returns False for non-existent view."""
        assert await async_sqlite_memory_backend.introspector.view_exists("nonexistent") is False

    @pytest.mark.asyncio
    async def test_view_exists_distinguishes_from_table(self, async_backend_with_view):
        """Test that view_exists distinguishes views from tables."""
        assert await async_backend_with_view.introspector.view_exists("users") is False
        assert await async_backend_with_view.introspector.table_exists("users") is True


class TestAsyncViewDetails:
    """Tests for detailed view information."""

    @pytest.mark.asyncio
    async def test_multiple_views(self, async_sqlite_memory_backend):
        """Test multiple views in database."""
        await async_sqlite_memory_backend.executescript("""
            CREATE VIEW view1 AS SELECT 1 AS col;
            CREATE VIEW view2 AS SELECT 2 AS col;
            CREATE VIEW view3 AS SELECT 3 AS col;
        """)

        views = await async_sqlite_memory_backend.introspector.list_views()

        view_names = {v.name for v in views}
        assert "view1" in view_names
        assert "view2" in view_names
        assert "view3" in view_names

    @pytest.mark.asyncio
    async def test_complex_view_definition(self, async_sqlite_memory_backend):
        """Test complex view definition."""
        await async_sqlite_memory_backend.executescript("""
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

        view_info = await async_sqlite_memory_backend.introspector.get_view_info("order_summary")

        assert view_info is not None
        assert view_info.definition is not None
        assert "GROUP BY" in view_info.definition.upper()
        assert "HAVING" in view_info.definition.upper()

    @pytest.mark.asyncio
    async def test_view_with_join(self, async_backend_with_view):
        """Test view with JOIN definition."""
        view_info = await async_backend_with_view.introspector.get_view_info("user_posts_summary")

        assert view_info is not None
        definition = view_info.definition.upper()
        assert "JOIN" in definition or "LEFT" in definition
