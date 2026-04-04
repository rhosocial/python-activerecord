# tests/rhosocial/activerecord_test/feature/worker/conftest.py
"""
Pytest configuration for abstract WorkerPool tests.

================================================================================
DIRECTORY PURPOSE - PLEASE READ BEFORE MODIFYING
================================================================================

This directory (feature/worker/) is for ABSTRACT WorkerPool tests that do NOT
depend on any database backend. These tests validate the core functionality of
rhosocial.activerecord.worker.pool module.

WHAT BELONGS HERE:
- Tests for rhosocial.activerecord.worker.pool abstract functionality
- Tests that use simple task functions (no database I/O)
- Tests for WorkerHandle, WorkerRegistry, Future, PoolState, etc.
- Tests for graceful shutdown, orphaned task detection, etc.

WHAT DOES NOT BELONG HERE:
- Database-dependent WorkerPool tests (SQLite, MySQL, PostgreSQL, etc.)
  → Put those in feature/basic/worker/ or feature/query/worker/
- Backend-specific WorkerPool tests
  → Put those in feature/backend/{backend}/worker/

DIRECTORY STRUCTURE:
- feature/worker/ (this directory)
  → Abstract WorkerPool tests (rhosocial.activerecord.worker.pool)
- feature/basic/worker/
  → CRUD-related WorkerPool tests (database-dependent)
- feature/query/worker/
  → Query-related WorkerPool tests (transactions, database-dependent)

IMPORTANT NOTES:
- All task functions must be module-level functions (pickle-able)
- Tests should NOT import any database backend modules
- Tests should NOT use ActiveRecord models that require database connections
"""
