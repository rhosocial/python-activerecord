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
#   named-expression  Run named query examples (using dry-run)
#   named-procedure  Run named procedure examples (using dry-run)

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

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
    
    python -m rhosocial.activerecord.backend.impl.sqlite query \
        --db-file "$db_file" \
        "CREATE TABLE users (id INTEGER PRIMARY KEY, name TEXT, email TEXT)"
    
    python -m rhosocial.activerecord.backend.impl.sqlite query \
        --db-file "$db_file" \
        "CREATE TABLE orders (id INTEGER PRIMARY KEY, user_id INTEGER, status TEXT, amount REAL)"
    
    python -m rhosocial.activerecord.backend.impl.sqlite query \
        --db-file "$db_file" \
        "CREATE TABLE inventory (id INTEGER PRIMARY KEY, product TEXT, stock INTEGER)"
    
    python -m rhosocial.activerecord.backend.impl.sqlite query \
        --db-file "$db_file" \
        "CREATE TABLE products (id INTEGER PRIMARY KEY, name TEXT, price REAL)"
    
    # Insert test data
    python -m rhosocial.activerecord.backend.impl.sqlite query \
        --db-file "$db_file" \
        "INSERT INTO users (name, email) VALUES ('Alice', 'alice@example.com'), ('Bob', 'bob@example.com'), ('Charlie', 'charlie@example.com')"
    
    python -m rhosocial.activerecord.backend.impl.sqlite query \
        --db-file "$db_file" \
        "INSERT INTO orders (user_id, status, amount) VALUES (1, 'pending', 100.00), (1, 'completed', 250.00), (2, 'pending', 75.00)"
    
    python -m rhosocial.activerecord.backend.impl.sqlite query \
        --db-file "$db_file" \
        "INSERT INTO inventory (product, stock) VALUES ('Widget', 50), ('Gadget', 30), ('Gizmo', 20)"
    
    python -m rhosocial.activerecord.backend.impl.sqlite query \
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
    python -m rhosocial.activerecord.backend.impl.sqlite query \
        --db-file "$DB_FILE" \
        "SELECT * FROM users"
    
    echo ""
    echo "--- WHERE clause ---"
    python -m rhosocial.activerecord.backend.impl.sqlite query \
        --db-file "$DB_FILE" \
        "SELECT * FROM orders WHERE status = 'pending'"
    
    echo ""
    echo "--- JOIN query ---"
    python -m rhosocial.activerecord.backend.impl.sqlite query \
        --db-file "$DB_FILE" \
        "SELECT u.name, o.amount, o.status FROM users u JOIN orders o ON u.id = o.user_id"
    
    echo ""
    echo "--- Aggregate with GROUP BY ---"
    python -m rhosocial.activerecord.backend.impl.sqlite query \
        --db-file "$DB_FILE" \
        "SELECT user_id, COUNT(*) as order_count, SUM(amount) as total FROM orders GROUP BY user_id"
    
    echo ""
    echo "--- Subquery ---"
    python -m rhosocial.activerecord.backend.impl.sqlite query \
        --db-file "$DB_FILE" \
        "SELECT * FROM users WHERE id IN (SELECT user_id FROM orders WHERE amount > 100)"
    
    echo ""
    echo "--- JSON output ---"
    python -m rhosocial.activerecord.backend.impl.sqlite query \
        --db-file "$DB_FILE" \
        "SELECT * FROM products" -o json
    
    echo ""
    echo "--- CSV output ---"
    python -m rhosocial.activerecord.backend.impl.sqlite query \
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
    python -m rhosocial.activerecord.backend.impl.sqlite introspect \
        --db-file "$DB_FILE" \
        tables
    
    echo ""
    echo "--- Table details ---"
    python -m rhosocial.activerecord.backend.impl.sqlite introspect \
        --db-file "$DB_FILE" \
        table orders
    
    echo ""
    echo "--- Column details ---"
    python -m rhosocial.activerecord.backend.impl.sqlite introspect \
        --db-file "$DB_FILE" \
        columns users
    
    echo ""
    echo "--- Indexes ---"
    python -m rhosocial.activerecord.backend.impl.sqlite introspect \
        --db-file "$DB_FILE" \
        indexes orders
    
    echo ""
    echo "--- Database schema ---"
    python -m rhosocial.activerecord.backend.impl.sqlite introspect \
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
    python -m rhosocial.activerecord.backend.impl.sqlite status \
        --db-file "$DB_FILE" \
        all
    
    echo ""
    echo "--- Configuration only ---"
    python -m rhosocial.activerecord.backend.impl.sqlite status \
        --db-file "$DB_FILE" \
        config
    
    echo ""
    echo "--- Performance metrics ---"
    python -m rhosocial.activerecord.backend.impl.sqlite status \
        --db-file "$DB_FILE" \
        performance
    
    echo ""
    echo "--- Storage info ---"
    python -m rhosocial.activerecord.backend.impl.sqlite status \
        --db-file "$DB_FILE" \
        storage
    
    echo ""
    echo "--- Verbose output ---"
    python -m rhosocial.activerecord.backend.impl.sqlite status \
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
    
    MODULE="rhosocial.activerecord.backend.impl.sqlite.examples.named_queries.order_queries"
    
    echo "--- List all named queries ---"
    python -m rhosocial.activerecord.backend.impl.sqlite named-expression "$MODULE" --list
    
    echo ""
    echo "--- Describe get_order query ---"
    python -m rhosocial.activerecord.backend.impl.sqlite named-expression \
        "$MODULE.get_order" \
        --describe
    
    echo ""
    echo "--- Dry-run: Show generated SQL without executing ---"
    python -m rhosocial.activerecord.backend.impl.sqlite named-expression \
        "$MODULE.get_order" \
        --dry-run \
        --param order_id=1
    
    echo ""
    echo "--- Dry-run: Check inventory query ---"
    python -m rhosocial.activerecord.backend.impl.sqlite named-expression \
        "$MODULE.check_inventory" \
        --dry-run \
        --param order_id=1
    
    echo ""
    echo "--- Execute (uses module's internal database with sample data) ---"
    python -m rhosocial.activerecord.backend.impl.sqlite named-expression \
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
    python -m rhosocial.activerecord.backend.impl.sqlite named-procedure "$MODULE" --list
    
    echo ""
    echo "--- Describe OrderProcessingProcedure ---"
    python -m rhosocial.activerecord.backend.impl.sqlite named-procedure \
        "$MODULE.OrderProcessingProcedure" \
        --describe
    
    echo ""
    echo "--- Dry-run: Show execution plan without running ---"
    python -m rhosocial.activerecord.backend.impl.sqlite named-procedure \
        "$MODULE.OrderProcessingProcedure" \
        --dry-run \
        --param order_id=1 \
        --param user_id=100 \
        --param amount=99.99
    
    echo ""
    echo "--- Full execution (uses module's internal database) ---"
    python -m rhosocial.activerecord.backend.impl.sqlite named-procedure \
        "$MODULE.OrderProcessingProcedure" \
        --param order_id=1 \
        --param user_id=100 \
        --param amount=99.99 2>&1 || true
    
    echo ""
    echo "--- Alternative: Run the Python example directly (recommended for full execution) ---"
    echo "Running: python examples/named_procedures/order_workflow.py"
    echo ""
    cd "$SCRIPT_DIR"
    python named_procedures/order_workflow.py
    
    echo ""
    echo "Named procedure examples completed!"
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
    *)
        echo "Unknown mode: $MODE"
        echo "Available modes: all, query, introspect, status, named-expression, named-procedure"
        exit 1
        ;;
esac