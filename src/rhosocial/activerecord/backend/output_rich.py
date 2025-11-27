# src/rhosocial/activerecord/backend/output_rich.py
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import box
from typing import Any, List, Dict

from .output_abc import OutputProvider


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
        if not isinstance(data, list) or not all(isinstance(i, dict) for i in data):
            self.console.print(data)
            return
        
        if not data:
            self.display_no_data()
            return

        table = Table(show_header=True, header_style="bold magenta", box=box_style)
        headers = list(data[0].keys())
        for header in headers:
            table.add_column(header, style="dim", overflow="fold")

        for row in data:
            table.add_row(*[str(row[header]) for header in headers])
        
        self.console.print(table)

    def display_no_data(self):
        self.console.print("[yellow]No data returned for table output.[/yellow]")

    def display_no_result_object(self):
        self.console.print("[yellow]Query executed, but no result object returned for table output.[/yellow]")

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
        self.console.print("[bold green]Rich library detected. Using beautified table output.[/bold green]")

