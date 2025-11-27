# $\mathcal{B}_{\text{sqlite}}^{\rho}$ - SQLite Backend Quick Execution Tool

This `__main__.py` script provides a command-line interface to quickly execute SQL queries against a SQLite database using the `rhosocial-activerecord` SQLite backend implementation.

## Purpose

This tool is designed for:
*   Rapid testing of SQLite backend connectivity and query execution.
*   Debugging specific SQL queries or backend behaviors.
*   Interacting with file-based or in-memory SQLite databases directly from the command line.

## Usage

To run the script, navigate to the root directory of the project (where the `src` folder is located). Then, execute the module using `python -m` followed by the module path.

SQL queries can be provided as a positional argument, from a file using the `--file` flag, or piped via standard input (stdin).

```bash
python -m rhosocial.activerecord.backend.impl.sqlite [OPTIONAL_FLAGS] [YOUR_SQL_QUERY]
```

## Arguments

| Argument          | Default                                                                       | Description                                                                                                                                                                                                                                |
| :---------------- | :---------------------------------------------------------------------------- | :----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `--db-file`       | _None_                                                                        | Path to the SQLite database file. If not provided, an **in-memory database** will be used.                                                                                                                                               |
| `query`           | _None_                                                                        | **SQL query to execute.** Must be enclosed in quotes. If not provided, the tool will look for input from `--file` or stdin.                                                                                                            |
| `-f, --file`      | _None_                                                                        | Path to a file containing SQL to execute. Use this for single or multi-statement scripts.                                                                                                                                              |
| `--output`        | `table` (if rich available) or `json` (fallback)                               | Output format. Choices are `table` (rich formatted), `json`, `csv`, `tsv`.                                                                                                                                                             |
| `--executescript` | _False_                                                                       | Execute the input as a multi-statement script. Essential for running SQL dump files or files containing multiple SQL commands. Not compatible with single query argument.                                                              |
| `--log-level`     | `INFO`                                                                        | Set the logging level (e.g., `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`).                                                                                                                                                     |
| `--plain`         | _False_                                                                       | Use plain text output even if `rich` is installed.                                                                                                                                                                                       |
| `--rich-ascii`    | _False_                                                                       | Use ASCII characters for table borders. Recommended for terminals that have trouble rendering Unicode boxes.                                                                                                                         |

## Important Notes

*   **Database File Management**: If `--db-file` points to a non-existent file, SQLite will automatically create it. However, this tool does not automatically delete database files; users are responsible for managing these files. For in-memory connections (`:memory:`), different processes establish isolated connections, meaning data is not shared between them.
*   **Concurrency**: This tool does not include built-in concurrency checks. When multiple connections simultaneously access the same SQLite database file, it may lead to race conditions or locking issues, depending on the SQLite locking mechanism and transaction isolation levels. It is the user's responsibility to manage concurrent access in such scenarios.

## Examples

### 1. In-Memory Database

If you run the tool without the `--db-file` flag, it will operate on a temporary, in-memory database that is destroyed once the command finishes. This is useful for quick, non-persistent tests.

```bash
# Activate the virtual environment and set PYTHONPATH
# (Example assumes you are in the python-activerecord project root)
source .venv3.14/bin/activate
export PYTHONPATH=src

# 1. Run a query against an in-memory database (positional argument)
python -m rhosocial.activerecord.backend.impl.sqlite "SELECT sqlite_version();"

# 2. Pipe a query from a file to an in-memory database (stdin input)
cat docs/examples/sqlite_cli/sqlite_select.sql | python -m rhosocial.activerecord.backend.impl.sqlite
```

### 2. File-Based Database

To work with a persistent, file-based database, use the `--db-file` flag.

#### 2.1 Create Tables and Insert Data (using --executescript)

Use the `--executescript` flag when providing a file or stdin input that contains multiple SQL statements (e.g., a database dump or a schema creation script).

```bash
# Create and populate database from a file
python -m rhosocial.activerecord.backend.impl.sqlite --db-file my_app.db \
--file docs/examples/sqlite_cli/sqlite_example.sql --executescript

# Alternatively, pipe the file content
cat docs/examples/sqlite_cli/sqlite_example.sql | python -m rhosocial.activerecord.backend.impl.sqlite --db-file my_app.db --executescript
```

#### 2.2 Query Data (various output formats)

Retrieve data from `my_app.db` using different output formats.

```bash
# Default table output (if rich is installed)
python -m rhosocial.activerecord.backend.impl.sqlite --db-file my_app.db \
"SELECT * FROM employees WHERE role = 'Developer';"

# JSON output
python -m rhosocial.activerecord.backend.impl.sqlite --db-file my_app.db \
"SELECT id, name FROM employees WHERE name LIKE 'A%'; --output json"

# CSV output
python -m rhosocial.activerecord.backend.impl.sqlite --db-file my_app.db \
"SELECT id, name, role FROM employees ORDER BY id;" --output csv

# TSV output (pipe from file)
cat docs/examples/sqlite_cli/sqlite_select.sql | python -m rhosocial.activerecord.backend.impl.sqlite --db-file my_app.db --output tsv
```

#### 2.3 Clean Up

You can remove the test database file using your system's `rm` or `del` command.

```bash
rm my_app.db
```
