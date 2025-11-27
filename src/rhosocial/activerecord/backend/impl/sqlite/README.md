# $\rho_{AR}^{sqlite}$ - SQLite Backend Quick Execution Tool

This `__main__.py` script provides a command-line interface to quickly execute SQL queries against a SQLite database using the `rhosocial-activerecord` SQLite backend implementation.

## Purpose

This tool is designed for:
*   Rapid testing of SQLite backend connectivity and query execution.
*   Debugging specific SQL queries or backend behaviors.
*   Interacting with file-based or in-memory SQLite databases directly from the command line.

## Usage

To run the script, navigate to the root directory of the project (where the `src` folder is located). Then, execute the module using `python -m` followed by the module path.

The SQL query is a **positional argument** and should be the last argument after all optional flags.

```bash
python -m rhosocial.activerecord.backend.impl.sqlite [OPTIONAL_FLAGS] "YOUR_SQL_QUERY;"
```

## Arguments

| Argument      | Default     | Description                                                                                                   |
| :------------ | :---------- | :------------------------------------------------------------------------------------------------------------ |
| `--db-file`   | _None_      | Path to the SQLite database file. If not provided, an **in-memory database** will be used.                     |
| `query`       | _Required_  | **SQL query to execute.** Must be enclosed in quotes.                                                         |
| `--log-level` | `INFO`      | Set the logging level (e.g., `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`).                              |
| `--plain`     | _False_     | Use plain text output even if `rich` is installed.                                                            |
| `--rich-ascii`| _False_     | Use ASCII characters for table borders. Recommended for terminals that have trouble rendering Unicode boxes. |

## Important Notes

*   **Database File Management**: If `--db-file` points to a non-existent file, SQLite will automatically create it. However, this tool does not automatically delete database files; users are responsible for managing these files. For in-memory connections (`:memory:`), different processes establish isolated connections, meaning data is not shared between them.
*   **Concurrency**: This tool does not include built-in concurrency checks. When multiple connections simultaneously access the same SQLite database file, it may lead to race conditions or locking issues, depending on the SQLite locking mechanism and transaction isolation levels. It is the user's responsibility to manage concurrent access in such scenarios.

## Examples

### In-Memory Database

If you run the tool without the `--db-file` flag, it will operate on a temporary, in-memory database that is destroyed once the command finishes. This is useful for quick, non-persistent tests.

```bash
# Activate the virtual environment and set PYTHONPATH
# (Example assumes you are in the python-activerecord project root)
source .venv3.14/bin/activate
export PYTHONPATH=src

# Run a query against an in-memory database
python -m rhosocial.activerecord.backend.impl.sqlite "SELECT sqlite_version();"
```

### File-Based Database

To work with a persistent, file-based database, use the `--db-file` flag.

#### 1. Create a Table in a New Database

This command will create a new file named `test.db` in your current directory.

```bash
python -m rhosocial.activerecord.backend.impl.sqlite --db-file test.db \
"CREATE TABLE contacts (id INTEGER PRIMARY KEY, name TEXT NOT NULL, email TEXT);"
```

#### 2. Insert Data

Now, let's insert some data into the `contacts` table in `test.db`.

```bash
python -m rhosocial.activerecord.backend.impl.sqlite --db-file test.db \
"INSERT INTO contacts (name, email) VALUES ('Alice', 'alice@example.com');"

python -m rhosocial.activerecord.backend.impl.sqlite --db-file test.db \
"INSERT INTO contacts (name, email) VALUES ('Bob', 'bob@example.com');"
```

#### 3. Query Data

Retrieve the data to see the results. With `rich` installed, this will be displayed in a formatted table.

```bash
python -m rhosocial.activerecord.backend.impl.sqlite --db-file test.db "SELECT * FROM contacts;"
```

#### 4. Clean Up

You can remove the test database file using your system's `rm` or `del` command.

```bash
rm test.db
```
