#!/bin/bash
# run_monthly_report.sh - Execute monthly report procedure graph
#
# Usage:
#   ./run_monthly_report.sh [--dry-run] [--async] [MONTH]
#
# Examples:
#   ./run_monthly_report.sh              # Run for current month
#   ./run_monthly_report.sh 2026-04      # Run for April 2026
#   ./run_monthly_report.sh --dry-run 2026-04  # Dry run

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
MONTH="${1:-2026-04}"
DRY_RUN=""
ASYNC=""
FORMAT="table"

# Parse arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --dry-run)
            DRY_RUN="--dry-run"
            shift
            ;;
        --async)
            ASYNC="--async"
            shift
            ;;
        --format)
            FORMAT="$2"
            shift 2
            ;;
        -*)
            echo "Unknown option: $1" >&2
            exit 1
            ;;
        *)
            MONTH="$1"
            shift
            ;;
    esac
done

# Build command
CMD="python -m rhosocial.activerecord.backend.impl.sqlite named-procedure-graph run \\
    rhosocial.activerecord.backend.impl.sqlite.examples.named_procedure_graph.monthly_report \\
    --params '{\"month\": \"$MONTH\"}' \\
    --format $FORMAT \\
    $DRY_RUN $ASYNC"

echo "Executing: $CMD" >&2
eval $CMD