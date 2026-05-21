#!/bin/bash
# run_order_queries.sh - Execute named queries example
#
# This script demonstrates how to use the named-expression CLI command
# to execute queries defined in the examples/named_queries module.
#
# Usage:
#   ./run_order_queries.sh [--dry-run] [QUERY_NAME] [PARAMS...]
#
# Examples:
#   ./run_order_queries.sh                  # List all queries
#   ./run_order_queries.sh --list          # List all queries (explicit)
#   ./run_order_queries.sh orders_by_status # Describe orders_by_status query
#   ./run_order_queries.sh --describe orders_by_status  # Full description
#   ./run_order_queries.sh orders_by_status --param status=pending
#   ./run_order_queries.sh orders_by_status --param status=pending --dry-run

set -e

MODULE="rhosocial.activerecord.backend.impl.sqlite.examples.named_queries.order_queries"

DRY_RUN=""
DESCRIBE=""
LIST=""
QUERY_NAME=""
PARAMS=""
OUTPUT="table"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run)
            DRY_RUN="--dry-run"
            shift
            ;;
        --describe|-d)
            DESCRIBE="--describe"
            shift
            ;;
        --list|-l)
            LIST="--list"
            shift
            ;;
        --output|-o)
            OUTPUT="$2"
            shift 2
            ;;
        --param)
            if [[ -n "$PARAMS" ]]; then
                PARAMS="$PARAMS --param $2"
            else
                PARAMS="--param $2"
            fi
            shift 2
            ;;
        -*)
            echo "Unknown option: $1" >&2
            exit 1
            ;;
        *)
            QUERY_NAME="$1"
            shift
            ;;
    esac
done

# Build and execute command
if [[ -n "$LIST" ]]; then
    echo "Listing queries in: $MODULE"
    python -m rhosocial.activerecord.backend.impl.sqlite named-expression "$MODULE" --list -o "$OUTPUT"
elif [[ -n "$QUERY_NAME" && -n "$DESCRIBE" ]]; then
    echo "Describing query: $MODULE.$QUERY_NAME"
    python -m rhosocial.activerecord.backend.impl.sqlite named-expression "$MODULE.$QUERY_NAME" --describe
elif [[ -n "$QUERY_NAME" ]]; then
    echo "Executing query: $MODULE.$QUERY_NAME"
    python -m rhosocial.activerecord.backend.impl.sqlite named-expression "$MODULE.$QUERY_NAME" -o "$OUTPUT" $DRY_RUN $PARAMS
else
    echo "Usage: $0 [OPTIONS] [QUERY_NAME]"
    echo ""
    echo "Options:"
    echo "  --dry-run         Show SQL without executing"
    echo "  --describe, -d   Show query description"
    echo "  --list, -l        List all queries in module"
    echo "  --output FORMAT   Output format: table, json, csv, tsv"
    echo "  --param KEY=VALUE Query parameter"
    echo ""
    echo "Examples:"
    echo "  $0 --list"
    echo "  $0 --describe orders_by_status"
    echo "  $0 orders_by_status --param status=pending"
    exit 0
fi