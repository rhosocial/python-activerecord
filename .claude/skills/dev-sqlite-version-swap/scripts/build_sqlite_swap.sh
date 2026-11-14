#!/usr/bin/env bash
# Build a libsqlite3 for a chosen version into a private directory.
#
#   build_sqlite_swap.sh <version> [prefix]
#
# The output declares SONAME libsqlite3.so.0, so Python's _sqlite3 extension
# loads it when LD_LIBRARY_PATH points at the prefix. Nothing is installed and
# nothing outside the prefix is written.

set -euo pipefail

VERSION="${1:-}"
if [ -z "$VERSION" ]; then
    echo "usage: $0 <version> [prefix]" >&2
    echo "example: $0 3.53.0" >&2
    exit 2
fi
PREFIX="${2:-$HOME/.local/sqlite-swap/$VERSION}"

# 3.53.0 -> 3530000; 3.45.1 -> 3450100. sqlite.org names the archive after
# the version digits followed by "00".
MAJOR="${VERSION%%.*}"
REST="${VERSION#*.}"
MINOR="${REST%%.*}"
if [ "$REST" = "$MINOR" ]; then
    PATCH=0
else
    PATCH="${REST#*.}"
fi
NUM="$(printf '%d%02d%02d00' "$MAJOR" "$MINOR" "$PATCH")"
ARCHIVE="sqlite-amalgamation-$NUM.zip"
BASE="https://www.sqlite.org"

mkdir -p "$PREFIX/src" "$PREFIX/lib"
cd "$PREFIX/src"

if [ ! -f "$ARCHIVE" ]; then
    if [ -n "${SQLITE_AMALGAMATION_URL:-}" ]; then
        curl -fsSL -o "$ARCHIVE" "$SQLITE_AMALGAMATION_URL"
    else
        # The download page lists only the current release, so an older
        # archive is located by probing the year directories. Pass
        # SQLITE_AMALGAMATION_YEAR to skip the probe when it is known.
        YEAR="${SQLITE_AMALGAMATION_YEAR:-}"
        if [ -z "$YEAR" ]; then
            for ((candidate = 2000; candidate <= 2100; candidate++)); do
                if curl -fsSI "$BASE/$candidate/$ARCHIVE" >/dev/null 2>&1; then
                    YEAR="$candidate"
                    break
                fi
            done
        fi
        if [ -z "$YEAR" ]; then
            echo "error: no year directory holds $ARCHIVE; set SQLITE_AMALGAMATION_URL or SQLITE_AMALGAMATION_YEAR" >&2
            exit 1
        fi
        curl -fsSL -o "$ARCHIVE" "$BASE/$YEAR/$ARCHIVE"
    fi
fi

python3 -m zipfile -e "$ARCHIVE" .
SRC="$PREFIX/src/sqlite-amalgamation-$NUM"
if [ ! -f "$SRC/sqlite3.c" ]; then
    echo "error: extraction did not produce $SRC/sqlite3.c" >&2
    exit 1
fi

CC="${CC:-cc}"
COMMON=(
    -DSQLITE_ENABLE_FTS5
    -DSQLITE_ENABLE_RTREE
    -DSQLITE_ENABLE_GEOPOLY
    -DSQLITE_ENABLE_DBSTAT_VTAB
    -DSQLITE_ENABLE_MATH_FUNCTIONS
    -DSQLITE_ENABLE_COLUMN_METADATA
    -DSQLITE_THREADSAFE=1
)

"$CC" -O2 -fPIC -shared \
    -Wl,-soname,libsqlite3.so.0 \
    -o "$PREFIX/lib/libsqlite3.so.0" \
    "$SRC/sqlite3.c" \
    "${COMMON[@]}"

ln -sf libsqlite3.so.0 "$PREFIX/lib/libsqlite3.so"

echo "built $PREFIX/lib/libsqlite3.so.0"
echo "verify with:"
echo "  LD_LIBRARY_PATH=\"$PREFIX/lib\" python3 -c 'import sqlite3; print(sqlite3.sqlite_version)'"
