# src/rhosocial/activerecord/backend/named_connection/cli.py
"""
CLI utilities for named connection functionality.

This module provides reusable functions to add named-connection subcommand
to various CLI tools (like sqlite backend CLI). It handles connection
configuration from both explicit parameters and named connection sources.

Features:
    - Configure connections via explicit parameters (host, port, etc.)
    - Configure connections via named connection (qualified name)
    - Explicit parameters override named connection parameters
    - List all connections in a module
    - Show connection description

Usage Example:
    >>> # Using named connection (SQLite)
    >>> prog --named-connection myapp.connections.wal_db --param journal_mode=WAL

    >>> # Using named connection (MySQL)
    >>> prog --named-connection myapp.connections.prod_db --param database=myapp

    >>> # Using named connection with parameter overrides
    >>> prog --named-connection myapp.connections.wal_db \\
    ...     --param journal_mode=DELETE --param timeout=30

    >>> # Using explicit parameters (SQLite)
    >>> prog --db-file myapp.db --db-type sqlite

Note:
    This module is for backend CLI tools. For programmatic access
    to named connections, use NamedConnectionResolver directly.
"""
import argparse
import sys
from typing import Any, Callable, Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from rhosocial.activerecord.backend.config import BaseConfig


# CLI-specific exceptions
class NamedConnectionCliError(Exception):
    """Base exception for CLI-specific named connection errors."""
    pass


def parse_params(params: list) -> Dict[str, str]:
    """Parse --param KEY=VALUE into a dictionary.

    Args:
        params: List of parameter strings in 'KEY=VALUE' format.

    Returns:
        Dict[str, str]: Dictionary mapping parameter names to values.
    """
    result = {}
    for param in params:
        if "=" in param:
            key, value = param.split("=", 1)
            result[key] = value
        else:
            print(
                f"Warning: Invalid parameter format: {param}. Use KEY=VALUE",
                file=sys.stderr,
            )
    return result


def resolve_connection_config(
    args: Any,
    named_connection_resolver_factory: Callable[[str], "NamedConnectionResolver"],
) -> Optional["BaseConfig"]:
    """Resolve connection config from CLI arguments.

    This function resolves connection configuration from either:
    1. Named connection (qualified name via --named-connection)
    2. Explicit parameters (--host, --port, --database, etc.)

    Priority: Explicit parameters override named connection parameters.

    Args:
        args: Parsed command-line arguments namespace. Must contain:
            - named_connection: Optional qualified name for named connection
            - param: List of KEY=VALUE parameter overrides
        named_connection_resolver_factory: Factory to create resolver.

    Returns:
        BaseConfig: The resolved connection config, or None if no config source.
    """
    named_conn = getattr(args, "named_connection", None)
    user_params = getattr(args, "param", [])

    if user_params:
        user_params = parse_params(user_params)
    else:
        user_params = {}

    # Case 1: Named connection provided
    if named_conn:
        resolver = named_connection_resolver_factory(named_conn).load()
        config = resolver.resolve(user_params)
        return config

    # Case 2: Explicit parameters provided
    explicit_params = _extract_explicit_params(args)
    if explicit_params:
        return _create_config_from_params(explicit_params)

    return None


def _extract_explicit_params(args: Any) -> Dict[str, Any]:
    """Extract explicit connection parameters from args.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Dict with connection parameters found in args.
    """
    params = {}

    # Common connection parameters
    common_params = [
        ("host", "host"),
        ("port", "port"),
        ("database", "database"),
        ("username", "username"),
        ("password", "password"),
        ("db_file", "database"),  # SQLite specific
        ("db_type", "driver_type"),
    ]

    for arg_name, config_name in common_params:
        value = getattr(args, arg_name, None)
        if value is not None:
            params[config_name] = value

    return params


def _create_config_from_params(params: Dict[str, Any]) -> "BaseConfig":
    """Create a config object from explicit parameters.

    Args:
        params: Dictionary of connection parameters.

    Returns:
        BaseConfig: A ConnectionConfig or backend-specific config.
    """
    # Import here to avoid circular imports
    from rhosocial.activerecord.backend.config import ConnectionConfig

    return ConnectionConfig(**params)


def create_named_connection_parser(
    subparsers: argparse._SubParsersAction,
    parent_parser: argparse.ArgumentParser,
    epilog: str = None,
) -> argparse.ArgumentParser:
    """Create the named-connection subcommand parser.

    This function adds a 'named-connection' subcommand to an argparse-based
    CLI tool for discovering and describing named connections.

    Args:
        subparsers: The subparsers action from the main parser.
        parent_parser: Parent parser with common arguments.
        epilog: Custom examples text.

    Returns:
        argparse.ArgumentParser: The created parser for named-connection subcommand.
    """
    if epilog is None:
        epilog = """Examples:
  # List all connections in a module
  %(prog)s --list myapp.connections

  # Show connection details (without sensitive data)
  %(prog)s --show myapp.connections.prod_db

  # Resolve connection config to JSON (dry-run)
  %(prog)s --describe myapp.connections.wal_db --param journal_mode=WAL
"""
    nc_parser = subparsers.add_parser(
        "named-connection",
        help="Manage named database connections",
        parents=[parent_parser],
        epilog=epilog,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Positional argument for qualified name or module
    nc_parser.add_argument(
        "qualified_name",
        nargs="?",
        help="Module or connection qualified name (required for --show and --describe, optional for --list).",
    )

    # Primary mode: list connections in a module
    nc_parser.add_argument(
        "--list",
        action="store_true",
        dest="list_connections",
        help="List all named connections in the given module.",
    )
    nc_parser.add_argument(
        "--show",
        dest="show_connection",
        metavar="QUALIFIED_NAME",
        help="Show detailed info for a specific named connection.",
    )
    nc_parser.add_argument(
        "--describe",
        dest="describe_connection",
        metavar="QUALIFIED_NAME",
        help="Show connection configuration preview (dry-run mode).",
    )

    return nc_parser


def handle_named_connection(
    args: Any,
    named_connection_resolver_factory: Callable[[str], "NamedConnectionResolver"],
) -> None:
    """Handle named-connection subcommand execution.

    Args:
        args: Parsed command-line arguments namespace.
        named_connection_resolver_factory: Factory to create resolver.
    """
    # Show help message if no arguments provided
    if not args.list_connections and not args.show_connection and not args.describe_connection:
        print("Named Connection CLI")
        print("=" * 50)
        print("Usage:")
        print("  # List connections in a module")
        print("  named-connection --list <module_name>")
        print("")
        print("  # Show detailed info for a connection")
        print("  named-connection --show <qualified_name>")
        print("")
        print("  # Describe connection config (dry-run)")
        print("  named-connection --describe <qualified_name> [--param KEY=VALUE]")
        print("")
        print("Examples:")
        print("  named-connection --list myapp.connections")
        print("  named-connection --show myapp.connections.prod_db")
        print("  named-connection --describe myapp.connections.wal_db --param timeout=30")
        print("")
        print("For full help: named-connection --help")
        return

    if args.list_connections:
        module_name = args.qualified_name
        if not module_name:
            print("Error: --list requires a module name", file=sys.stderr)
            sys.exit(1)

        try:
            from . import list_named_connections_in_module
            connections = list_named_connections_in_module(module_name)

            if not connections:
                print(f"No named connections found in module: {module_name}")
                return

            print(f"Module: {module_name}")
            print(f"{'Name':<30} {'Parameters':<40} {'Brief':<30}")
            print("-" * 100)
            for conn in connections:
                params = conn["signature"]
                brief = conn["brief"][:27] + "..." if len(conn["brief"]) > 30 else conn["brief"]
                print(f"{conn['name']:<30} {params:<40} {brief:<30}")

        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        return

    if args.show_connection:
        try:
            resolver = named_connection_resolver_factory(args.show_connection).load()
            info = resolver.describe()

            print(f"Connection: {info['qualified_name']}")
            print(f"Type: {'Class' if info['is_class'] else 'Function'}")
            print(f"Docstring: {info['docstring']}")
            print(f"Signature: {info['signature']}")
            print("Parameters:")
            for name, param in info["parameters"].items():
                default_str = f" default={param['default']}" if param['has_default'] else ""
                print(f"  {name} {param['type']}{default_str}")

            if info.get("config_preview"):
                print("Config Preview (non-sensitive fields):")
                for key, value in info["config_preview"].items():
                    print(f"  {key}: {value}")

        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        return

    if args.describe_connection:
        try:
            resolver = named_connection_resolver_factory(args.describe_connection).load()
            params = parse_params(getattr(args, "param", []))
            config = resolver.resolve(params)

            print("Resolved Configuration:")
            config_dict = config.to_dict()
            for key, value in config_dict.items():
                # Filter sensitive fields for display
                if key.lower() in ("password", "secret", "token", "api_key"):
                    value = "****"
                print(f"  {key}: {value}")

        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)
        return
