#!/bin/bash
# run_all_examples.sh - Execute every example module in this directory
#
# These examples are documentation that executes. Nothing in the test suite runs
# them, so an example can drift out of step with the API it demonstrates and
# still sit there looking fine -- which is exactly what happened: 44 of 55
# examples were broken at once, most of them calling a constructor or a keyword
# that no longer exists.
#
# Usage:
#   ./run_all_examples.sh [--fast] [PATTERN]
#
#   --fast    skip the cli/*_demo.py scripts (see the note on runtime below)
#   PATTERN   only run examples whose relative path matches this substring
#
# Runtime: the ordinary examples take one to two seconds each. The three
# cli/*_demo.py scripts each spawn several CLI subprocesses and take 25-30
# seconds apiece, so the full run is around three minutes. --fast skips them.
#
# Environment:
#   DEMO_VENV_PYTHON   interpreter to use (default: python3)
#   EXAMPLES_TIMEOUT   per-example timeout in seconds (default: 45)

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# The repository root is the directory holding src/rhosocial. Examples are run
# from there, never from this directory: examples/types/ shadows the standard
# library module of that name as soon as this directory reaches sys.path, which
# running a script by path guarantees.
REPO_ROOT=""
_probe="$SCRIPT_DIR"
for _ in $(seq 1 12); do
    if [ -d "$_probe/src/rhosocial" ]; then
        REPO_ROOT="$(cd "$_probe" && pwd)"
        break
    fi
    _probe="$(dirname "$_probe")"
done
if [ -z "$REPO_ROOT" ]; then
    echo "Cannot locate the repository root (no src/rhosocial above $SCRIPT_DIR)." >&2
    exit 1
fi
cd "$REPO_ROOT"
export PYTHONPATH="${PYTHONPATH:+:$PYTHONPATH}$REPO_ROOT/src"

VENV_PYTHON="${DEMO_VENV_PYTHON:-python3}"
TIMEOUT="${EXAMPLES_TIMEOUT:-45}"

FAST=0
PATTERN=""
for arg in "$@"; do
    case "$arg" in
        --fast) FAST=1 ;;
        -h|--help) sed -n '2,25p' "$0"; exit 0 ;;
        *) PATTERN="$arg" ;;
    esac
done

PKG="rhosocial.activerecord.backend.impl.sqlite.examples"

mapfile -t EXAMPLES < <(
    cd "$SCRIPT_DIR" && find . -name '*.py' \
        ! -name '__init__.py' ! -name 'conftest.py' ! -path '*__pycache__*' \
        -printf '%P\n' | sort
)

if [ ${#EXAMPLES[@]} -eq 0 ]; then
    echo "No examples discovered under $SCRIPT_DIR" >&2
    exit 1
fi

passed=0; failed=0; skipped=0
declare -a FAILURES=()

for rel in "${EXAMPLES[@]}"; do
    if [ -n "$PATTERN" ] && [[ "$rel" != *"$PATTERN"* ]]; then
        skipped=$((skipped + 1))
        continue
    fi
    if [ "$FAST" -eq 1 ] && [[ "$rel" == cli/* ]]; then
        echo "SKIP  $rel (--fast)"
        skipped=$((skipped + 1))
        continue
    fi

    # concurrency.py lives directly in this directory, so running it by path
    # would put examples/ on sys.path and shadow the stdlib `types` module.
    # -m runs it from the package root instead.
    printf 'RUN   %-52s ' "$rel"
    if [ "$rel" = "concurrency.py" ]; then
        output="$(timeout "$TIMEOUT" "$VENV_PYTHON" -m "$PKG.concurrency" 2>&1 </dev/null)" && rc=0 || rc=$?
    else
        output="$(timeout "$TIMEOUT" "$VENV_PYTHON" "$SCRIPT_DIR/$rel" 2>&1 </dev/null)" && rc=0 || rc=$?
    fi

    if [ $rc -eq 0 ]; then
        echo "ok"
        passed=$((passed + 1))
    else
        if [ $rc -eq 124 ]; then
            echo "TIMEOUT (${TIMEOUT}s)"
        else
            echo "FAIL (exit $rc)"
        fi
        failed=$((failed + 1))
        FAILURES+=("$rel")
        # Surface the cause rather than making the reader re-run it by hand.
        echo "$output" | grep -E "^[A-Za-z_.]*(Error|Exception):" | tail -1 | sed 's/^/        /'
    fi
done

echo
echo "=========================================="
echo "passed: $passed   failed: $failed   skipped: $skipped"
if [ ${#FAILURES[@]} -gt 0 ]; then
    echo "failing examples:"
    printf '  %s\n' "${FAILURES[@]}"
fi
echo "=========================================="

[ $failed -eq 0 ]
