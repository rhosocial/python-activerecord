#!/bin/bash
# run_named_procedure_graph.sh - Execute named procedure graph examples
#
# This script demonstrates how to use the named-procedure-graph CLI command
# to execute procedure graphs defined in the examples/named_procedure_graph module.
#
# Usage:
#   ./run_named_procedure_graph.sh [MODE] [OPTIONS] [GRAPH_NAME]
#
# Modes:
#   --list       List all procedure graphs in module
#   --describe  Show graph structure without executing
#   --validate  Validate graph (check for cycles, errors)
#   --waves     Show wave decomposition
#   (run)       Execute the graph (default)
#
# Examples:
#   ./run_named_procedure_graph.sh --list
#   ./run_named_procedure_graph.sh --describe
#   ./run_named_procedure_graph.sh --validate
#   ./run_named_procedure_graph.sh --waves
#   ./run_named_procedure_graph.sh --params '{"month":"2026-04"}'
#   ./run_named_procedure_graph.sh --dry-run --params '{"month":"2026-04"}'

set -e

MODULE="rhosocial.activerecord.backend.impl.sqlite.examples.named_procedure_graph.monthly_report"

MODE=""
PARAMS="{}"
OUTPUT="table"
DRY_RUN=""

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --list)
            MODE="--list"
            shift
            ;;
        --describe)
            MODE="--describe"
            shift
            ;;
        --validate)
            MODE="--validate"
            shift
            ;;
        --waves)
            MODE="--waves"
            shift
            ;;
        --dry-run)
            DRY_RUN="--dry-run"
            shift
            ;;
        --output|-o)
            OUTPUT="$2"
            shift 2
            ;;
        --params)
            PARAMS="$2"
            shift 2
            ;;
        -*)
            echo "Unknown option: $1" >&2
            exit 1
            ;;
        *)
            echo "Unknown argument: $1" >&2
            exit 1
            ;;
    esac
done

# Build and execute command
if [[ -n "$MODE" ]]; then
    echo "Operation: $MODE on $MODULE"
    python -m rhosocial.activerecord.backend.impl.sqlite named-procedure-graph "$MODULE" $MODE -o "$OUTPUT"
else
    echo "Executing graph: $MODULE with params: $PARAMS"
    python -m rhosocial.activerecord.backend.impl.sqlite named-procedure-graph "$MODULE" --params "$PARAMS" -o "$OUTPUT" $DRY_RUN
fi