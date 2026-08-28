# tests/rhosocial/activerecord_test/feature/backend/cli/named_series/__init__.py
"""Self-contained fixture modules for deep-testing the named series.

The named series is progressive:
    named-connection (access) -> named-expression (single query)
    -> named-procedure (orchestration) -> named-procedure-graph (DAG)
    -> named-migration (schema).

These modules are import-safe: importing them performs no I/O.  Tables are
created by the migrations themselves (run via the named-migration CLI).
"""
