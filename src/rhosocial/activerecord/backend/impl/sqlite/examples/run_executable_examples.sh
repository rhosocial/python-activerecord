#!/bin/bash
# run_executable_examples.sh - Self-contained examples for CLI commands
#
# This script demonstrates all CLI commands with actual data execution.
# Each example creates its own test data, executes, then cleans up.
#
# Usage:
#   ./run_executable_examples.sh [MODE]
#
# Modes:
#   all          Run all examples (default)
#   query        Run query command examples
#   introspect   Run introspect command examples
#   status       Run status command examples
#   named-expression       Run named expression examples
#   named-procedure        Run named procedure examples
#   named-procedure-graph  Run named procedure graph examples
#   named-migration        Run named migration examples
#   named-connection       Run named connection examples

#   DEMO_VENV_PYTHON=.venv/bin/python \\
#     PYTHONPATH=src ./run_executable_examples.sh [MODE]
#
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Locate the checkout root (the directory holding src/rhosocial) and work from
# there rather than from this examples/ directory.
#
# examples/ contains a package called types/, which shadows the standard library
# module of the same name as soon as the current directory lands on sys.path --
# and `python -m` puts it there. The result is an import error deep inside
# runpy, with no mention of the actual cause. Running from the repository root
# avoids the collision on every supported Python version; PYTHONSAFEPATH is set
# too, for 3.11+, but it cannot be relied on because the project supports 3.8.
REPO_ROOT=""
_probe="$SCRIPT_DIR"
for _ in 1 2 3 4 5 6 7 8; do
    if [ -d "$_probe/src/rhosocial" ]; then
        REPO_ROOT="$(cd "$_probe" && pwd)"
        break
    fi
    _probe="$(dirname "$_probe")"
done
if [ -z "$REPO_ROOT" ]; then
    echo "Cannot locate the repository root (no src/rhosocial above $SCRIPT_DIR)." >&2
    echo "Run this script from a checkout, or set PYTHONPATH yourself." >&2
    exit 1
fi
cd "$REPO_ROOT"
export PYTHONPATH="${PYTHONPATH:+:$PYTHONPATH}$REPO_ROOT/src"
export PYTHONSAFEPATH=1

# Bare `python` is not guaranteed to exist (many distributions only ship
# python3), and the examples run against whatever the caller has installed.
# DEMO_VENV_PYTHON selects the interpreter; the demo_*.sh drivers use the same
# variable name so one setting works for all of them.
VENV_PYTHON="${DEMO_VENV_PYTHON:-python3}"
PYTHON="$VENV_PYTHON -m rhosocial.activerecord.backend.impl.sqlite"

# Create temporary directory for test databases
TEMP_DIR="/tmp/rhosocial_cli_examples_$$"
mkdir -p "$TEMP_DIR"

# Cleanup function
cleanup() {
    rm -rf "$TEMP_DIR"
}
trap cleanup EXIT

# ============================================================
# Initialize a test database with sample data
# ============================================================
init_database() {
    local db_file="$1"
    
    $PYTHON query \
        --db-file "$db_file" \
        "CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, email TEXT)"
    
    $PYTHON query \
        --db-file "$db_file" \
        "CREATE TABLE orders (id INTEGER PRIMARY KEY, user_id INTEGER, status TEXT, amount REAL)"
    
    $PYTHON query \
        --db-file "$db_file" \
        "CREATE TABLE inventory (id INTEGER PRIMARY KEY, product TEXT, stock INTEGER)"
    
    $PYTHON query \
        --db-file "$db_file" \
        "CREATE TABLE products (id INTEGER PRIMARY KEY, name TEXT, price REAL)"
    
    # Insert test data
    $PYTHON query \
        --db-file "$db_file" \
        "INSERT INTO users (name, email) VALUES ('Alice', 'alice@example.com'), ('Bob', 'bob@example.com'), ('Charlie', 'charlie@example.com')"
    
    $PYTHON query \
        --db-file "$db_file" \
        "INSERT INTO orders (user_id, status, amount) VALUES (1, 'pending', 100.00), (1, 'completed', 250.00), (2, 'pending', 75.00)"
    
    $PYTHON query \
        --db-file "$db_file" \
        "INSERT INTO inventory (product, stock) VALUES ('Widget', 50), ('Gadget', 30), ('Gizmo', 20)"
    
    $PYTHON query \
        --db-file "$db_file" \
        "INSERT INTO products (name, price) VALUES ('Widget', 19.99), ('Gadget', 49.99), ('Gizmo', 29.99)"
}

# ============================================================
# Query Command Examples
# ============================================================
run_query_examples() {
    echo ""
    echo "=========================================="
    echo "Query Command Examples"
    echo "=========================================="
    echo ""
    
    DB_FILE="$TEMP_DIR/query_test.db"
    init_database "$DB_FILE"
    
    echo "--- Simple SELECT ---"
    $PYTHON query \
        --db-file "$DB_FILE" \
        "SELECT * FROM users"
    
    echo ""
    echo "--- WHERE clause ---"
    $PYTHON query \
        --db-file "$DB_FILE" \
        "SELECT * FROM orders WHERE status = 'pending'"
    
    echo ""
    echo "--- JOIN query ---"
    $PYTHON query \
        --db-file "$DB_FILE" \
        "SELECT u.name, o.amount, o.status FROM users u JOIN orders o ON u.id = o.user_id"
    
    echo ""
    echo "--- Aggregate with GROUP BY ---"
    $PYTHON query \
        --db-file "$DB_FILE" \
        "SELECT user_id, COUNT(*) as order_count, SUM(amount) as total FROM orders GROUP BY user_id"
    
    echo ""
    echo "--- Subquery ---"
    $PYTHON query \
        --db-file "$DB_FILE" \
        "SELECT * FROM users WHERE id IN (SELECT user_id FROM orders WHERE amount > 100)"
    
    echo ""
    echo "--- JSON output ---"
    $PYTHON query \
        --db-file "$DB_FILE" \
        "SELECT * FROM products" -o json
    
    echo ""
    echo "--- CSV output ---"
    $PYTHON query \
        --db-file "$DB_FILE" \
        "SELECT * FROM products" -o csv
    
    echo ""
    echo "Query examples completed!"
}

# ============================================================
# Introspect Command Examples
# ============================================================
run_introspect_examples() {
    echo ""
    echo "=========================================="
    echo "Introspect Command Examples"
    echo "=========================================="
    echo ""
    
    DB_FILE="$TEMP_DIR/introspect_test.db"
    init_database "$DB_FILE"
    
    echo "--- List all tables ---"
    $PYTHON introspect \
        --db-file "$DB_FILE" \
        tables
    
    echo ""
    echo "--- Table details ---"
    $PYTHON introspect \
        --db-file "$DB_FILE" \
        table orders
    
    echo ""
    echo "--- Column details ---"
    $PYTHON introspect \
        --db-file "$DB_FILE" \
        columns users
    
    echo ""
    echo "--- Indexes ---"
    $PYTHON introspect \
        --db-file "$DB_FILE" \
        indexes orders
    
    echo ""
    echo "--- Database schema ---"
    $PYTHON introspect \
        --db-file "$DB_FILE" \
        database
    
    echo ""
    echo "Introspect examples completed!"
}

# ============================================================
# Status Command Examples
# ============================================================
run_status_examples() {
    echo ""
    echo "=========================================="
    echo "Status Command Examples"
    echo "=========================================="
    echo ""
    
    DB_FILE="$TEMP_DIR/status_test.db"
    init_database "$DB_FILE"
    
    echo "--- All status ---"
    $PYTHON status \
        --db-file "$DB_FILE" \
        all
    
    echo ""
    echo "--- Configuration only ---"
    $PYTHON status \
        --db-file "$DB_FILE" \
        config
    
    echo ""
    echo "--- Performance metrics ---"
    $PYTHON status \
        --db-file "$DB_FILE" \
        performance
    
    echo ""
    echo "--- Storage info ---"
    $PYTHON status \
        --db-file "$DB_FILE" \
        storage
    
    echo ""
    echo "--- Verbose output ---"
    $PYTHON status \
        --db-file "$DB_FILE" \
        all -v
    
    echo ""
    echo "Status examples completed!"
}

# ============================================================
# Named Query Examples (using dry-run to show SQL)
# ============================================================
run_named_query_examples() {
    echo ""
    echo "=========================================="
    echo "Named Query Examples"
    echo "=========================================="
    echo ""
    
    MODULE="rhosocial.activerecord.backend.impl.sqlite.examples.named_expressions.order_expressions"
    
    echo "--- List all named queries ---"
    $PYTHON named-expression "$MODULE" --list
    
    echo ""
    echo "--- Describe get_order query ---"
    $PYTHON named-expression \
        "$MODULE.get_order" \
        --describe
    
    echo ""
    echo "--- Dry-run: Show generated SQL without executing ---"
    $PYTHON named-expression \
        "$MODULE.get_order" \
        --dry-run \
        --param order_id=1
    
    echo ""
    echo "--- Dry-run: Check inventory query ---"
    $PYTHON named-expression \
        "$MODULE.check_inventory" \
        --dry-run \
        --param order_id=1
    
    echo ""
    echo "--- Execute (uses module's internal database with sample data) ---"
    $PYTHON named-expression \
        "$MODULE.get_order" \
        --param order_id=1
    
    echo ""
    echo "Named query examples completed!"
}

# ============================================================
# Named Procedure Examples (using dry-run)
# ============================================================
run_named_procedure_examples() {
    echo ""
    echo "=========================================="
    echo "Named Procedure Examples"
    echo "=========================================="
    echo ""
    
    MODULE="rhosocial.activerecord.backend.impl.sqlite.examples.named_procedures.order_workflow"
    
    echo "--- List all named procedures ---"
    $PYTHON named-procedure "$MODULE" --list
    
    echo ""
    echo "--- Describe OrderProcessingProcedure ---"
    $PYTHON named-procedure \
        "$MODULE.OrderProcessingProcedure" \
        --describe
    
    echo ""
    echo "--- Dry-run: Show execution plan without running ---"
    $PYTHON named-procedure \
        "$MODULE.OrderProcessingProcedure" \
        --dry-run \
        --param order_id=1 \
        --param user_id=100 \
        --param amount=99.99
    
    echo ""
    echo "--- Full execution (uses module's internal database) ---"
    $PYTHON named-procedure \
        "$MODULE.OrderProcessingProcedure" \
        --param order_id=1 \
        --param user_id=100 \
        --param amount=99.99 2>&1 || true
    
    echo ""
    echo "--- Alternative: Run the Python example directly (recommended for full execution) ---"
    echo "Running: $VENV_PYTHON $SCRIPT_DIR/named_procedures/order_workflow.py"
    echo ""
    $VENV_PYTHON "$SCRIPT_DIR/named_procedures/order_workflow.py"
    
    echo ""
    echo "Named procedure examples completed!"
}

# ============================================================
# Named procedure graph examples
# ============================================================
run_named_procedure_graph_examples() {
    echo ""
    echo "=========================================="
    echo "Named Procedure Graph Examples"
    echo "=========================================="
    echo ""

    GRAPH_MODULE="rhosocial.activerecord.backend.impl.sqlite.examples.named_procedure_graph.monthly_report"
    GRAPH_NAME="$GRAPH_MODULE.monthly_report_graph"
    GRAPH_DB="$TEMP_DIR/graph.sqlite"

    echo "--- List all named procedure graphs ---"
    $PYTHON named-procedure-graph \
        "$GRAPH_MODULE" --list

    echo ""
    echo "--- Describe monthly_report_graph ---"
    $PYTHON named-procedure-graph \
        "$GRAPH_NAME" --describe

    echo ""
    echo "--- Validate the DAG (no execution) ---"
    $PYTHON named-procedure-graph \
        "$GRAPH_NAME" --validate

    echo ""
    echo "--- Show execution waves (topological layers) ---"
    $PYTHON named-procedure-graph \
        "$GRAPH_NAME" --waves

    echo ""
    echo "--- Dry-run against a scratch database ---"
    $PYTHON named-procedure-graph \
        --db-file "$GRAPH_DB" "$GRAPH_NAME" --dry-run

    echo ""
    echo "--- Validate the second graph too ---"
    $PYTHON named-procedure-graph \
        "$GRAPH_MODULE.monthly_report_with_threshold_graph" --validate

    echo ""
    echo "Named procedure graph examples completed!"
}

# ============================================================
# Named migration examples
# ============================================================
run_named_migration_examples() {
    echo ""
    echo "=========================================="
    echo "Named Migration Examples"
    echo "=========================================="
    echo ""

    MIGRATION_MODULE="rhosocial.activerecord.backend.impl.sqlite.examples.named_migrations.migrations"
    MIGRATION_DB="$TEMP_DIR/migrations.sqlite"

    echo "--- List all named migrations ---"
    $PYTHON named-migration \
        "$MIGRATION_MODULE" --list

    echo ""
    echo "--- Describe V001CreateUsers ---"
    $PYTHON named-migration \
        "$MIGRATION_MODULE.V001CreateUsers" --describe

    echo ""
    echo "--- Dry-run: show the DDL without applying it ---"
    $PYTHON named-migration \
        --db-file "$MIGRATION_DB" --dry-run \
        "$MIGRATION_MODULE.V001CreateUsers" --direction up

    echo ""
    echo "--- Apply V001 for real ---"
    $PYTHON named-migration \
        --db-file "$MIGRATION_DB" \
        "$MIGRATION_MODULE.V001CreateUsers" --direction up

    echo ""
    echo "--- Verify the table exists (exit code is not evidence) ---"
    $PYTHON query \
        --db-file "$MIGRATION_DB" \
        "SELECT name FROM sqlite_master WHERE type='table' AND name='users'"

    echo ""
    echo "--- Roll it back ---"
    $PYTHON named-migration \
        --db-file "$MIGRATION_DB" \
        "$MIGRATION_MODULE.V001CreateUsers" --direction down

    echo ""
    echo "--- Verify the table is gone ---"
    $PYTHON query \
        --db-file "$MIGRATION_DB" \
        "SELECT COUNT(*) AS remaining FROM sqlite_master WHERE type='table' AND name='users'"

    echo ""
    echo "--- A migration taking a parameter ---"
    $PYTHON named-migration \
        --db-file "$TEMP_DIR/params.sqlite" \
        "$MIGRATION_MODULE.V003CreateCustomTable" \
        --direction up --param table_name=example_config

    echo ""
    echo "Named migration examples completed!"
}

# ============================================================
# Named connection examples
# ============================================================
run_named_connection_examples() {
    echo ""
    echo "=========================================="
    echo "Named Connection Examples"
    echo "=========================================="
    echo ""

    CONN_BASE="rhosocial.activerecord.backend.impl.sqlite.examples.named_connections"

    echo "--- List in-memory connections ---"
    $PYTHON named-connection \
        --list "$CONN_BASE.memory"

    echo ""
    echo "--- List file-based connections ---"
    $PYTHON named-connection \
        --list "$CONN_BASE.file"

    echo ""
    echo "--- Describe a single connection (config preview, no connect) ---"
    $PYTHON named-connection \
        --describe "$CONN_BASE.memory.memory_db"

    echo ""
    echo "--- Show resolved details ---"
    $PYTHON named-connection \
        --show "$CONN_BASE.memory.memory_db"

    echo ""
    echo "Named connection examples completed!"
}

# ============================================================
# Main
# ============================================================
MODE="${1:-all}"

case "$MODE" in
    all)
        run_query_examples
        run_introspect_examples
        run_status_examples
        run_named_query_examples
        run_named_procedure_examples
        run_named_procedure_graph_examples
        run_named_migration_examples
        run_named_connection_examples
        echo ""
        echo "=========================================="
        echo "All examples completed successfully!"
        echo "=========================================="
        ;;
    query)
        run_query_examples
        ;;
    introspect)
        run_introspect_examples
        ;;
    status)
        run_status_examples
        ;;
    named-expression)
        run_named_query_examples
        ;;
    named-procedure)
        run_named_procedure_examples
        ;;
    named-procedure-graph)
        run_named_procedure_graph_examples
        ;;
    named-migration)
        run_named_migration_examples
        ;;
    named-connection)
        run_named_connection_examples
        ;;
    *)
        echo "Unknown mode: $MODE"
        echo "Available modes: all, query, introspect, status, named-expression, named-procedure,"
        echo "                  named-procedure-graph, named-migration, named-connection"
        exit 1
        ;;
esac