# src/rhosocial/activerecord/backend/show/mixins.py
"""
Backend mixins for SHOW functionality.

This module provides mixin classes that add the show() factory method
to backends. The show() method returns a ShowFunctionality instance
that provides database-specific SHOW commands.

This pattern follows the same design as IntrospectionMixin:
- Mixin provides the public show() method
- Subclasses implement _create_show_functionality() to create the instance
- ShowFunctionality handles the actual implementation
"""

from abc import abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .functionality import ShowFunctionality, AsyncShowFunctionality


class ShowMixin:
    """Mixin for backends that support SHOW functionality.

    Provides the show() factory method that returns a ShowFunctionality
    instance. Subclasses must implement _create_show_functionality().

    Usage:
        class MySQLBackend(ShowMixin, StorageBackend):
            def _create_show_functionality(self):
                return MySQLShowFunctionality(self, self._version)

        # User code:
        result = backend.show().create_table("users")
    """

    @abstractmethod
    def _create_show_functionality(self) -> "ShowFunctionality":
        """Create a SHOW functionality instance.

        Subclasses must implement this method to return a database-specific
        ShowFunctionality instance.

        Returns:
            ShowFunctionality: Database-specific SHOW functionality instance.
        """
        ...

    def show(self) -> "ShowFunctionality":
        """Get SHOW functionality instance.

        Returns a ShowFunctionality instance that provides database-specific
        SHOW commands via method chaining.

        Returns:
            ShowFunctionality: SHOW functionality instance.

        Example:
            # MySQL SHOW commands
            result = backend.show().create_table("users")
            columns = backend.show().columns("users", full=True)
            indexes = backend.show().indexes("users")
            tables = backend.show().tables()
            databases = backend.show().databases()
        """
        return self._create_show_functionality()


class AsyncShowMixin:
    """Mixin for async backends that support SHOW functionality.

    Async version of ShowMixin. Provides the show() factory method that
    returns an AsyncShowFunctionality instance.

    Usage:
        class AsyncMySQLBackend(AsyncShowMixin, AsyncStorageBackend):
            def _create_show_functionality(self):
                return AsyncMySQLShowFunctionality(self, self._version)

        # User code:
        result = await backend.show().create_table("users")
    """

    @abstractmethod
    def _create_show_functionality(self) -> "AsyncShowFunctionality":
        """Create an async SHOW functionality instance.

        Subclasses must implement this method to return a database-specific
        AsyncShowFunctionality instance.

        Returns:
            AsyncShowFunctionality: Database-specific async SHOW functionality.
        """
        ...

    def show(self) -> "AsyncShowFunctionality":
        """Get async SHOW functionality instance.

        Returns an AsyncShowFunctionality instance that provides database-specific
        SHOW commands via method chaining. All methods are async.

        Returns:
            AsyncShowFunctionality: Async SHOW functionality instance.

        Example:
            # MySQL SHOW commands (async)
            result = await backend.show().create_table("users")
            columns = await backend.show().columns("users", full=True)
        """
        return self._create_show_functionality()
