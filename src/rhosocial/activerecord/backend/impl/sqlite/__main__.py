# src/rhosocial/activerecord/backend/impl/sqlite/__main__.py
"""SQLite backend command-line interface.

Provides SQL execution and database introspection capabilities.
"""
import sys

from .cli import register_commands, COMMAND_NAMES


def main():
    parser = __import__('argparse').ArgumentParser(
        description="Execute SQL queries against a SQLite backend.",
        formatter_class=__import__('argparse').RawTextHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    register_commands(subparsers)

    args = parser.parse_args()

    if args.command is None:
        cmd_list = ", ".join(f"'{c}'" for c in COMMAND_NAMES[:-1])
        print(f"Error: Please specify a command: {cmd_list}, or '{COMMAND_NAMES[-1]}'",
              file=sys.stderr)
        print("Use --help for more information.", file=sys.stderr)
        sys.exit(1)

    # 分发到对应的子命令模块
    from .cli import get_handler
    handler = get_handler(args.command)
    handler(args)


if __name__ == "__main__":
    main()
