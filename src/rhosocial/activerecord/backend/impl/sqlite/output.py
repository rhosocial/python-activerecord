# src/rhosocial/activerecord/backend/impl/sqlite/output.py
import datetime
import decimal
import json
import logging
from abc import ABC, abstractmethod
from typing import Any, List, Dict

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

logger = logging.getLogger(__name__)


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


class PlainTextOutputProvider(OutputProvider):
    """Output provider for plain text logging."""

    def _json_serializer(self, obj: Any) -> str:
        if isinstance(obj, (datetime.datetime, datetime.date)):
            return obj.isoformat()
        if isinstance(obj, datetime.timedelta):
            return str(obj)
        if isinstance(obj, decimal.Decimal):
            return str(obj)
        raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")

    def display_query(self, query: str, is_async: bool):
        mode = "asynchronous" if is_async else "synchronous"
        logger.info(f"Executing {mode} query: {query}")

    def display_success(self, affected_rows: int, duration: float):
        logger.info(f"Query executed successfully. Affected rows: {affected_rows}, Duration: {duration:.4f}s")

    def display_results(self, data: List[Dict[str, Any]], **kwargs):
        logger.info("Results:")
        for row in data:
            print(json.dumps(row, indent=2, ensure_ascii=False, default=self._json_serializer))

    def display_no_data(self):
        logger.info("No data returned.")

    def display_no_result_object(self):
        logger.info("Query executed, but no result object returned.")

    def display_connection_error(self, error: Exception):
        logger.error(f"Database connection error: {error}")

    def display_query_error(self, error: Exception):
        logger.error(f"Database query error: {error}")

    def display_unexpected_error(self, error: Exception, is_async: bool):
        mode = "asynchronous" if is_async else "synchronous"
        logger.error(f"An unexpected error occurred during {mode} execution: {error}", exc_info=True)

    def display_disconnect(self, is_async: bool):
        mode = "asynchronous" if is_async else "synchronous"
        logger.info(f"Disconnected from database ({mode}).")

    def display_greeting(self):
        print("Rich library not found. We recommend installing rich for a more user-friendly output.")


if RICH_AVAILABLE:
    class RichOutputProvider(OutputProvider):
        """Output provider using the rich library for formatted output."""

        def __init__(self, console: Console, ascii_borders: bool = False):
            self.console = console
            self.box_style = box.ASCII if ascii_borders else box.SQUARE

        def display_query(self, query: str, is_async: bool):
            mode = "asynchronous" if is_async else "synchronous"
            self.console.print(f"Executing {mode} query: [bold cyan]{query}[/bold cyan]")

        def display_success(self, affected_rows: int, duration: float):
            self.console.print(f"[bold green]Query executed successfully.[/bold green] "
                               f"Affected rows: [bold cyan]{affected_rows}[/bold cyan], "
                               f"Duration: [bold cyan]{duration:.4f}s[/bold cyan]")

        def display_results(self, data: List[Dict[str, Any]], **kwargs):
            use_ascii = kwargs.get('use_ascii', False)
            box_style = box.ASCII if use_ascii else self.box_style
            if not isinstance(data, list) or not data or not all(isinstance(i, dict) for i in data):
                self.console.print(data)
                return

            table = Table(show_header=True, header_style="bold magenta", box=box_style)
            headers = data[0].keys()
            for header in headers:
                table.add_column(header, style="dim", overflow="fold")

            for row in data:
                table.add_row(*(str(v) for v in row.values()))

            self.console.print(table)

        def display_no_data(self):
            self.console.print("[yellow]No data returned.[/yellow]")

        def display_no_result_object(self):
            self.console.print("[yellow]Query executed, but no result object returned.[/yellow]")

        def display_connection_error(self, error: Exception):
            self.console.print(Panel(f"[bold]Database Connection Error[/bold]\n[red]{error}[/red]",
                                     title="[bold red]Error[/bold red]", border_style="red"))

        def display_query_error(self, error: Exception):
            self.console.print(Panel(f"[bold]Database Query Error[/bold]\n[red]{error}[/red]",
                                     title="[bold red]Error[/bold red]", border_style="red"))

        def display_unexpected_error(self, error: Exception, is_async: bool):
            mode = "asynchronous" if is_async else "synchronous"
            self.console.print(Panel(f"[bold]An unexpected error occurred during {mode} execution[/bold]\n[red]{error}[/red]",
                                     title="[bold red]Error[/bold red]", border_style="red"))

        def display_disconnect(self, is_async: bool):
            mode = "asynchronous" if is_async else "synchronous"
            self.console.print(f"[dim]Disconnected from database ({mode}).[/dim]")

        def display_greeting(self):
            self.console.print("[bold green]Rich library detected. Logging and output are beautified.[/bold green]")
