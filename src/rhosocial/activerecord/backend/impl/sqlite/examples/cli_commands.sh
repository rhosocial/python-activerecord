#!/bin/bash
# cli_commands.sh - Complete SQLite CLI command examples
#
# This script demonstrates all available CLI commands in the SQLite backend.
# Run this script to see examples of each command category.
#
# Usage:
#   ./cli_commands.sh [COMMAND] [OPTIONS]
#
# Commands:
#   info           - Display SQLite environment information
#   query          - Execute SQL queries
#   introspect     - Database introspection
#   status         - Display server status
#   named-expression    - Execute named queries
#   named-procedure - Execute named procedures
#   named-procedure-graph - Execute procedure graphs
#   named-connection - Manage named connections
#   all            - Run all command examples (default)

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"
export PYTHONSAFEPATH=1

# Create a test database for examples
TEST_DB="/tmp/rhosocial_cli_test.db"
rm -f "$TEST_DB"

# Initialize database with test data
init_test_db() {
    echo "Creating test database..."
    python -m rhosocial.activerecord.backend.impl.sqlite query \
        --db-file "$TEST_DB" \
        "CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, email TEXT)"
    python -m rhosocial.activerecord.backend.impl.sqlite query \
        --db-file "$TEST_DB" \
        "INSERT INTO users (name, email) VALUES ('Alice', 'alice@example.com')"
    python -m rhosocial.activerecord.backend.impl.sqlite query \
        --db-file "$TEST_DB" \
        "INSERT INTO users (name, email) VALUES ('Bob', 'bob@example.com')"
    python -m rhosocial.activerecord.backend.impl.sqlite query \
        --db-file "$TEST_DB" \
        "ALTER TABLE users ADD COLUMN tags TEXT DEFAULT '[\"a\",\"b\",\"c\"]'"
    python -m rhosocial.activerecord.backend.impl.sqlite query \
        --db-file "$TEST_DB" \
        "CREATE TABLE orders (id INTEGER PRIMARY KEY, status TEXT, user_id INTEGER, amount REAL)"
    python -m rhosocial.activerecord.backend.impl.sqlite query \
        --db-file "$TEST_DB" \
        "INSERT INTO orders (status, user_id, amount) VALUES ('pending', 100, 99.99)"
    python -m rhosocial.activerecord.backend.impl.sqlite query \
        --db-file "$TEST_DB" \
        "INSERT INTO orders (status, user_id, amount) VALUES ('shipped', 100, 199.99)"
    python -m rhosocial.activerecord.backend.impl.sqlite query \
        --db-file "$TEST_DB" \
        "CREATE TABLE inventory (id INTEGER PRIMARY KEY, order_id INTEGER, available INTEGER)"
    python -m rhosocial.activerecord.backend.impl.sqlite query \
        --db-file "$TEST_DB" \
        "INSERT INTO inventory (order_id, available) VALUES (1, 10)"
    python -m rhosocial.activerecord.backend.impl.sqlite query \
        --db-file "$TEST_DB" \
        "CREATE TABLE notifications (id INTEGER PRIMARY KEY, user_id INTEGER, type TEXT)"
    python -m rhosocial.activerecord.backend.impl.sqlite query \
        --db-file "$TEST_DB" \
        "CREATE TABLE payments (id INTEGER PRIMARY KEY, order_id INTEGER, status TEXT, transaction_id TEXT)"
    python -m rhosocial.activerecord.backend.impl.sqlite query \
        --db-file "$TEST_DB" \
        "INSERT INTO payments (order_id, status, transaction_id) VALUES (1, 'success', 'txn_001')"
    python -m rhosocial.activerecord.backend.impl.sqlite query \
        --db-file "$TEST_DB" \
        "CREATE TABLE order_records (id INTEGER PRIMARY KEY, order_id INTEGER, created_at TEXT)"
    python -m rhosocial.activerecord.backend.impl.sqlite query \
        --db-file "$TEST_DB" \
        "INSERT INTO order_records (order_id, created_at) VALUES (1, '2026-05-22')"
}

# Command: info
run_info() {
    echo ""
    echo "=========================================="
    echo "Command: info"
    echo "=========================================="
    echo ""

    echo "--- Basic info ---"
    python -m rhosocial.activerecord.backend.impl.sqlite info

    echo ""
    echo "--- Verbose info (protocol families) ---"
    python -m rhosocial.activerecord.backend.impl.sqlite info -v

    echo ""
    echo "--- Detailed verbose (all details) ---"
    python -m rhosocial.activerecord.backend.impl.sqlite info -vv

    echo ""
    echo "--- JSON output ---"
    python -m rhosocial.activerecord.backend.impl.sqlite info -o json
}

# Command: query
run_query() {
    echo ""
    echo "=========================================="
    echo "Command: query"
    echo "=========================================="
    echo ""

    echo "--- Simple SELECT ---"
    python -m rhosocial.activerecord.backend.impl.sqlite query \
        --db-file "$TEST_DB" \
        "SELECT * FROM users"

    echo ""
    echo "--- SELECT with WHERE ---"
    python -m rhosocial.activerecord.backend.impl.sqlite query \
        --db-file "$TEST_DB" \
        "SELECT * FROM users WHERE id = 1"

    echo ""
    echo "--- JOIN query ---"
    python -m rhosocial.activerecord.backend.impl.sqlite query \
        --db-file "$TEST_DB" \
        "SELECT u.name, o.amount FROM users u JOIN orders o ON u.id = o.user_id"

    echo ""
    echo "--- Aggregate query ---"
    python -m rhosocial.activerecord.backend.impl.sqlite query \
        --db-file "$TEST_DB" \
        "SELECT user_id, SUM(amount) as total FROM orders GROUP BY user_id"

    echo ""
    echo "--- JSON output ---"
    python -m rhosocial.activerecord.backend.impl.sqlite query \
        --db-file "$TEST_DB" \
        "SELECT * FROM users" -o json

    echo ""
    echo "--- CSV output ---"
    python -m rhosocial.activerecord.backend.impl.sqlite query \
        --db-file "$TEST_DB" \
        "SELECT * FROM users" -o csv

    echo ""
    echo "--- Using query from file ---"
    echo "SELECT * FROM users WHERE id > 0" > /tmp/test_query.sql
    python -m rhosocial.activerecord.backend.impl.sqlite query \
        --db-file "$TEST_DB" \
        -f /tmp/test_query.sql
    rm -f /tmp/test_query.sql

    echo ""
    echo "--- Using in-memory database ---"
    python -m rhosocial.activerecord.backend.impl.sqlite query \
        "SELECT 1 as test, 'hello' as greeting"
}

# Command: introspect
run_introspect() {
    echo ""
    echo "=========================================="
    echo "Command: introspect"
    echo "=========================================="
    echo ""

    echo "--- List all tables ---"
    python -m rhosocial.activerecord.backend.impl.sqlite introspect \
        --db-file "$TEST_DB" \
        tables

    echo ""
    echo "--- List all views ---"
    python -m rhosocial.activerecord.backend.impl.sqlite introspect \
        --db-file "$TEST_DB" \
        views

    echo ""
    echo "--- Get table details ---"
    python -m rhosocial.activerecord.backend.impl.sqlite introspect \
        --db-file "$TEST_DB" \
        table users

    echo ""
    echo "--- Get column details ---"
    python -m rhosocial.activerecord.backend.impl.sqlite introspect \
        --db-file "$TEST_DB" \
        columns users

    echo ""
    echo "--- Get indexes ---"
    python -m rhosocial.activerecord.backend.impl.sqlite introspect \
        --db-file "$TEST_DB" \
        indexes users

    echo ""
    echo "--- Get foreign keys ---"
    python -m rhosocial.activerecord.backend.impl.sqlite introspect \
        --db-file "$TEST_DB" \
        foreign-keys users

    echo ""
    echo "--- Get triggers ---"
    python -m rhosocial.activerecord.backend.impl.sqlite introspect \
        --db-file "$TEST_DB" \
        triggers users

    echo ""
    echo "--- Get database info ---"
    python -m rhosocial.activerecord.backend.impl.sqlite introspect \
        --db-file "$TEST_DB" \
        database

    echo ""
    echo "--- JSON output ---"
    python -m rhosocial.activerecord.backend.impl.sqlite introspect \
        --db-file "$TEST_DB" \
        tables -o json
}

# Command: status
run_status() {
    echo ""
    echo "=========================================="
    echo "Command: status"
    echo "=========================================="
    echo ""

    echo "--- All status ---"
    python -m rhosocial.activerecord.backend.impl.sqlite status \
        --db-file "$TEST_DB" \
        all

    echo ""
    echo "--- Config status ---"
    python -m rhosocial.activerecord.backend.impl.sqlite status \
        --db-file "$TEST_DB" \
        config

    echo ""
    echo "--- Performance status ---"
    python -m rhosocial.activerecord.backend.impl.sqlite status \
        --db-file "$TEST_DB" \
        performance

    echo ""
    echo "--- Storage status ---"
    python -m rhosocial.activerecord.backend.impl.sqlite status \
        --db-file "$TEST_DB" \
        storage

    echo ""
    echo "--- Databases status ---"
    python -m rhosocial.activerecord.backend.impl.sqlite status \
        --db-file "$TEST_DB" \
        databases

    echo ""
    echo "--- Verbose output ---"
    python -m rhosocial.activerecord.backend.impl.sqlite status \
        --db-file "$TEST_DB" \
        all -v

    echo ""
    echo "--- JSON output ---"
    python -m rhosocial.activerecord.backend.impl.sqlite status \
        --db-file "$TEST_DB" \
        all -o json
}

# Command: named-expression
run_named_query() {
    echo ""
    echo "=========================================="
    echo "Command: named-expression"
    echo "=========================================="
    echo ""

    MODULE="rhosocial.activerecord.backend.impl.sqlite.examples.named_expressions.order_expressions"
    MODULE_DML="rhosocial.activerecord.backend.impl.sqlite.examples.named_expressions.order_dml"
    MODULE_DDL="rhosocial.activerecord.backend.impl.sqlite.examples.named_expressions.order_ddl"
    MODULE_CLAUSES="rhosocial.activerecord.backend.impl.sqlite.examples.named_expressions.order_clauses"
    MODULE_VERSION="rhosocial.activerecord.backend.impl.sqlite.examples.named_expressions.order_version_compare"

    echo "=== DQL (SELECT) examples ==="
    echo "--- List all queries in module ---"
    python -m rhosocial.activerecord.backend.impl.sqlite named-expression "$MODULE" --list

    echo ""
    echo "--- Describe a query ---"
    python -m rhosocial.activerecord.backend.impl.sqlite named-expression \
        "$MODULE.get_order" \
        --describe

    echo ""
    echo "--- Dry run (show SQL) ---"
    python -m rhosocial.activerecord.backend.impl.sqlite named-expression \
        "$MODULE.get_order" \
        --db-file "$TEST_DB" \
        --dry-run \
        --param order_id=1

    echo ""
    echo "--- Execute with parameters ---"
    python -m rhosocial.activerecord.backend.impl.sqlite named-expression \
        "$MODULE.get_order" \
        --db-file "$TEST_DB" \
        --param order_id=1

    echo ""
    echo "=== DML examples (INSERT / UPDATE / DELETE) ==="
    echo "--- List DML expressions ---"
    python -m rhosocial.activerecord.backend.impl.sqlite named-expression "$MODULE_DML" --list

    echo ""
    echo "--- Dry run: INSERT ---"
    python -m rhosocial.activerecord.backend.impl.sqlite named-expression \
        "$MODULE_DML.add_order" \
        --db-file "$TEST_DB" \
        --dry-run \
        --param user_id=1

    echo ""
    echo "--- Dry run: UPDATE ---"
    python -m rhosocial.activerecord.backend.impl.sqlite named-expression \
        "$MODULE_DML.update_order_status" \
        --db-file "$TEST_DB" \
        --dry-run \
        --param order_id=1 \
        --param new_status=shipped

    echo ""
    echo "--- Dry run: DELETE ---"
    python -m rhosocial.activerecord.backend.impl.sqlite named-expression \
        "$MODULE_DML.cancel_order" \
        --db-file "$TEST_DB" \
        --dry-run \
        --param order_id=999

    echo ""
    echo "=== DDL examples (CREATE / ALTER / DROP) ==="
    echo "--- List DDL expressions ---"
    python -m rhosocial.activerecord.backend.impl.sqlite named-expression "$MODULE_DDL" --list

    echo ""
    echo "--- Dry run: CREATE TABLE ---"
    python -m rhosocial.activerecord.backend.impl.sqlite named-expression \
        "$MODULE_DDL.create_orders_table" \
        --dry-run

    echo ""
    echo "--- Dry run: CREATE INDEX ---"
    python -m rhosocial.activerecord.backend.impl.sqlite named-expression \
        "$MODULE_DDL.add_orders_status_index" \
        --dry-run

    echo ""
    echo "=== CLAUSE examples (WHERE / JOIN / GROUP BY / ORDER BY) ==="
    echo "--- List clause expressions ---"
    python -m rhosocial.activerecord.backend.impl.sqlite named-expression "$MODULE_CLAUSES" --list

    echo ""
    echo "--- Dry run: WHERE ---"
    python -m rhosocial.activerecord.backend.impl.sqlite named-expression \
        "$MODULE_CLAUSES.where_example" \
        --db-file "$TEST_DB" \
        --dry-run \
        --param status=pending

    echo ""
    echo "--- Dry run: JOIN ---"
    python -m rhosocial.activerecord.backend.impl.sqlite named-expression \
        "$MODULE_CLAUSES.join_example" \
        --db-file "$TEST_DB" \
        --dry-run \
        --param user_id=1

    echo ""
    echo "--- Dry run: GROUP BY ---"
    python -m rhosocial.activerecord.backend.impl.sqlite named-expression \
        "$MODULE_CLAUSES.group_by_example" \
        --db-file "$TEST_DB" \
        --dry-run

    echo ""
    echo "--- Dry run: ORDER BY + LIMIT ---"
    python -m rhosocial.activerecord.backend.impl.sqlite named-expression \
        "$MODULE_CLAUSES.order_by_example" \
        --db-file "$TEST_DB" \
        --dry-run \
        --param limit=3

    echo ""
    echo "--- Dry run: combined (WHERE + JOIN + ORDER BY) ---"
    python -m rhosocial.activerecord.backend.impl.sqlite named-expression \
        "$MODULE_CLAUSES.compound_example" \
        --db-file "$TEST_DB" \
        --dry-run \
        --param user_id=1 \
        --param status=pending

    echo ""
    echo "=== Version-dependent: json_array_insert (SQLite 3.53.0+) ==="
    echo "--- List (3.53.0+ dialect — recognized) ---"
    python -m rhosocial.activerecord.backend.impl.sqlite named-expression \
        "$MODULE_VERSION" --list --dialect-version 3.53.0

    echo ""
    echo "--- List (pre-3.53.0 dialect — unsupported) ---"
    python -m rhosocial.activerecord.backend.impl.sqlite named-expression \
        "$MODULE_VERSION" --list --dialect-version 3.35.0

    echo ""
    echo "--- Execute with 3.53.0+ (succeeds) ---"
    python -m rhosocial.activerecord.backend.impl.sqlite named-expression \
        "$MODULE_VERSION.demo_json_array_insert" \
        --dialect-version 3.53.0 \
        --dry-run \
        --param position=0 \
        --param value=hello

    echo ""
    echo "--- Execute with pre-3.53.0 (fails) ---"
    python -m rhosocial.activerecord.backend.impl.sqlite named-expression \
        "$MODULE_VERSION.demo_json_array_insert" \
        --dialect-version 3.35.0 \
        --dry-run \
        --param position=0 \
        --param value=hello || true

    echo ""
    echo "--- Describe ---"
    python -m rhosocial.activerecord.backend.impl.sqlite named-expression \
        "$MODULE_VERSION.demo_json_array_insert" \
        --describe
}

# Command: named-procedure
run_named_procedure() {
    echo ""
    echo "=========================================="
    echo "Command: named-procedure"
    echo "=========================================="
    echo ""

    MODULE="rhosocial.activerecord.backend.impl.sqlite.examples.named_procedures.order_workflow"

    echo "--- List all procedures in module ---"
    python -m rhosocial.activerecord.backend.impl.sqlite named-procedure "$MODULE" --list

    echo ""
    echo "--- Describe a procedure ---"
    python -m rhosocial.activerecord.backend.impl.sqlite named-procedure \
        "$MODULE.OrderProcessingProcedure" \
        --describe

    echo ""
    echo "--- Dry run (show execution plan) ---"
    python -m rhosocial.activerecord.backend.impl.sqlite named-procedure \
        "$MODULE.OrderProcessingProcedure" \
        --dry-run \
        --db-file "$TEST_DB" \
        --param order_id=1 \
        --param user_id=100

    echo ""
    echo "--- Transaction modes ---"
    echo "--- Step transaction ---"
    python -m rhosocial.activerecord.backend.impl.sqlite named-procedure \
        "$MODULE.OrderProcessingProcedure" \
        --db-file "$TEST_DB" \
        --param order_id=1 \
        --param user_id=100 \
        --transaction step

    echo "--- None transaction ---"
    python -m rhosocial.activerecord.backend.impl.sqlite named-procedure \
        "$MODULE.OrderProcessingProcedure" \
        --db-file "$TEST_DB" \
        --param order_id=1 \
        --param user_id=100 \
        --transaction none

    echo ""
    echo "=========================================="
    echo "All named-procedure examples completed successfully!"
    echo "=========================================="
}

# Command: named-procedure-graph
run_named_procedure_graph() {
    echo ""
    echo "=========================================="
    echo "Command: named-procedure-graph"
    echo "=========================================="
    echo ""

    MODULE="rhosocial.activerecord.backend.impl.sqlite.examples.named_procedure_graph.monthly_report"

    echo "--- List all graphs in module ---"
    python -m rhosocial.activerecord.backend.impl.sqlite named-procedure-graph "$MODULE" --list

    echo ""
    echo "--- Describe graph structure ---"
    python -m rhosocial.activerecord.backend.impl.sqlite named-procedure-graph "$MODULE.monthly_report_graph" --describe

    echo ""
    echo "--- Validate graph ---"
    python -m rhosocial.activerecord.backend.impl.sqlite named-procedure-graph "$MODULE.monthly_report_graph" --validate

    echo ""
    echo "--- Show wave decomposition ---"
    python -m rhosocial.activerecord.backend.impl.sqlite named-procedure-graph "$MODULE.monthly_report_graph" --waves

    echo ""
    echo "--- Dry run ---"
    python -m rhosocial.activerecord.backend.impl.sqlite named-procedure-graph "$MODULE.monthly_report_graph" \
        --params '{"month":"2026-04"}' \
        --dry-run
}

# Command: named-connection
run_named_connection() {
    echo ""
    echo "=========================================="
    echo "Command: named-connection"
    echo "=========================================="
    echo ""

    MODULE="rhosocial.activerecord.backend.impl.sqlite.examples.named_connections"

    echo "--- List connections in module ---"
    python -m rhosocial.activerecord.backend.impl.sqlite named-connection --list "$MODULE"

    echo ""
    echo "--- Show connection (example with existing connection) ---"
    python -m rhosocial.activerecord.backend.impl.sqlite named-connection --show "$MODULE.memory_db"

    echo ""
    echo "--- Describe connection (dry-run) ---"
    python -m rhosocial.activerecord.backend.impl.sqlite named-connection --describe "$MODULE.file_db_wal"
}

# Main
COMMAND="${1:-all}"

case "$COMMAND" in
    info)
        run_info
        ;;
    query)
        init_test_db
        run_query
        ;;
    introspect)
        init_test_db
        run_introspect
        ;;
    status)
        init_test_db
        run_status
        ;;
    named-expression)
        init_test_db
        run_named_query
        ;;
    named-procedure)
        init_test_db
        run_named_procedure
        ;;
    named-procedure-graph)
        run_named_procedure_graph
        ;;
    named-connection)
        run_named_connection
        ;;
    all)
        init_test_db
        run_info
        run_query
        run_introspect
        run_status
        run_named_query
        run_named_procedure
        run_named_procedure_graph
        run_named_connection
        echo ""
        echo "=========================================="
        echo "All examples completed!"
        echo "=========================================="
        ;;
    *)
        echo "Unknown command: $COMMAND"
        echo "Available commands: info, query, introspect, status, named-expression, named-procedure, named-procedure-graph, named-connection, all"
        exit 1
        ;;
esac

# Cleanup
rm -f "$TEST_DB"

echo ""
echo "Test database cleaned up."