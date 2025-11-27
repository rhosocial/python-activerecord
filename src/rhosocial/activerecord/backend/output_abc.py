# src/rhosocial/activerecord/backend/output_abc.py
from abc import ABC, abstractmethod
from typing import Any, List, Dict


class OutputProvider(ABC):
    """Abstract base class for different output strategies."""

    @abstractmethod
    def display_query(self, query: str, is_async: bool):
        """Display the query being executed."""
        pass

    @abstractmethod
    def display_success(self, affected_rows: int, duration: float):
        """Display a successful execution message."""
        pass

    @abstractmethod
    def display_results(self, data: List[Dict[str, Any]], **kwargs):
        """Display query results."""
        pass

    @abstractmethod
    def display_no_data(self):
        """Display a message when no data is returned."""
        pass

    @abstractmethod
    def display_no_result_object(self):
        """Display a message when the query returns no result object."""
        pass

    @abstractmethod
    def display_connection_error(self, error: Exception):
        """Display a connection error."""
        pass

    @abstractmethod
    def display_query_error(self, error: Exception):
        """Display a query error."""
        pass

    @abstractmethod
    def display_unexpected_error(self, error: Exception, is_async: bool):
        """Display an unexpected error."""
        pass

    @abstractmethod
    def display_disconnect(self, is_async: bool):
        """Display a disconnect message."""
        pass

    @abstractmethod
    def display_greeting(self):
        """Display a greeting message."""
        pass
