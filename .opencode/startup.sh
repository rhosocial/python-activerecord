#!/bin/bash
#
# opencode Startup Script for rhosocial-activerecord
# This script runs automatically when opencode starts in this project
#

set -e

echo ""
echo "╔══════════════════════════════════════════════════════════════╗"
echo "║     rhosocial-activerecord - AI Agent Context Loader        ║"
echo "╚══════════════════════════════════════════════════════════════╝"
echo ""

# Color definitions
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Check if we're in the right directory
if [ ! -f "pyproject.toml" ]; then
    echo "⚠️  Warning: pyproject.toml not found. Make sure you're in the project root."
    exit 1
fi

# Set PYTHONPATH if not already set
if [ -z "$PYTHONPATH" ]; then
    export PYTHONPATH=src
    echo -e "${GREEN}✓${NC} Set PYTHONPATH=src"
else
    echo -e "${GREEN}✓${NC} PYTHONPATH already set: $PYTHONPATH"
fi

# Project info
echo ""
echo -e "${BLUE}Project Information:${NC}"
echo "  Name: rhosocial-activerecord"
echo "  Type: Python ActiveRecord ORM"
echo "  Python: 3.8+ (Supports 3.13t, 3.14t free-threaded)"
echo "  Core Dep: Pydantic 2.x only"

# Check available backends
echo ""
echo -e "${BLUE}Available Backends:${NC}"
if [ -d "src/rhosocial/activerecord/backend/impl" ]; then
    for backend in src/rhosocial/activerecord/backend/impl/*/; do
        if [ -d "$backend" ]; then
            backend_name=$(basename "$backend")
            echo "  - $backend_name"
        fi
    done
fi

# Quick commands reference
echo ""
echo -e "${BLUE}Quick Commands:${NC}"
echo "  /test                    - Run all tests"
echo "  /test-feature basic      - Run basic feature tests"
echo "  /test-feature query      - Run query feature tests"
echo "  /test-backend sqlite     - Run SQLite backend tests"
echo "  /lint                    - Run code linting"
echo "  /new-feature             - Create new feature"
echo "  /new-backend             - Create new backend"

# Architecture reminder
echo ""
echo -e "${YELLOW}Architecture Principles:${NC}"
echo "  1. Expression-Dialect Separation: Expression → Dialect → SQL"
echo "  2. Sync/Async Duality: Every sync method has async counterpart"
echo "  3. Protocol-Based: Use Protocol for feature detection"
echo "  4. No ORM Dependencies: Only Pydantic, no SQLAlchemy/Django"

# Context loaded
echo ""
echo -e "${GREEN}✓${NC} Context loaded successfully!"
echo ""
echo "Use /help for more commands or start coding."
echo ""
