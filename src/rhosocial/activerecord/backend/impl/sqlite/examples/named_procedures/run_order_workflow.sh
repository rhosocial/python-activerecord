#!/bin/bash
# run_order_workflow.sh - Execute named procedure example
#
# This script demonstrates how to use the named-procedure CLI command
# to execute procedures defined in the examples/named_procedures module.
#
# Usage:
#   ./run_order_workflow.sh [OPTIONS] [PROC_NAME]
#
# Examples:
#   ./run_order_workflow.sh                  # List all procedures
#   ./run_order_workflow.sh --list          # List all procedures (explicit)
#   ./run_order_workflow.sh --describe order_workflow
#   ./run_order_workflow.sh order_workflow --param status=pending
#   ./run_order_workflow.sh order_workflow --param status=pending --dry-run
#   ./run_order_workflow.sh order_workflow --transaction step

set -e

MODULE="rhosocial.activerecord.backend.impl.sqlite.examples.named_procedures.order_workflow"

DRY_RUN=""
DESCRIBE=""
LIST=""
PROC_NAME=""
PARAMS=""
OUTPUT="table"
TRANSACTION="auto"

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
        --transaction|-t)
            TRANSACTION="$2"
            shift 2
            ;;
        -*)
            echo "Unknown option: $1" >&2
            exit 1
            ;;
        *)
            PROC_NAME="$1"
            shift
            ;;
    esac
done

# Build and execute command
if [[ -n "$LIST" ]]; then
    echo "Listing procedures in: $MODULE"
    python -m rhosocial.activerecord.backend.impl.sqlite named-procedure "$MODULE" --list -o "$OUTPUT"
elif [[ -n "$PROC_NAME" && -n "$DESCRIBE" ]]; then
    echo "Describing procedure: $MODULE.$PROC_NAME"
    python -m rhosocial.activerecord.backend.impl.sqlite named-procedure "$MODULE.$PROC_NAME" --describe
elif [[ -n "$PROC_NAME" ]]; then
    echo "Executing procedure: $MODULE.$PROC_NAME"
    python -m rhosocial.activerecord.backend.impl.sqlite named-procedure "$MODULE.$PROC_NAME" -o "$OUTPUT" --transaction "$TRANSACTION" $DRY_RUN $PARAMS
else
    echo "Usage: $0 [OPTIONS] [PROC_NAME]"
    echo ""
    echo "Options:"
    echo "  --dry-run              Show execution plan without running"
    echo "  --describe, -d         Show procedure description"
    echo "  --list, -l             List all procedures in module"
    echo "  --output FORMAT        Output format: table, json, csv, tsv"
    echo "  --param KEY=VALUE      Procedure parameter"
    echo "  --transaction MODE     Transaction mode: auto, step, none"
    echo ""
    echo "Examples:"
    echo "  $0 --list"
    echo "  $0 --describe order_workflow"
    echo "  $0 order_workflow --param status=pending"
    echo "  $0 order_workflow --param status=pending --dry-run"
    echo "  $0 order_workflow --transaction step"
    exit 0
fi