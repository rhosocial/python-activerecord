# src/rhosocial/activerecord/backend/impl/sqlite/mixins/set_operation.py
"""
SQLite-specific set-operation module.

Set-operation formatting is provided by the core
``SetOperationMixin.format_set_operation`` (the SQLite-specific override that
used to live here rendered trailing clauses the node no longer carries, so
the core implementation is authoritative now).

This module keeps the view DDL support that shares the file.
"""

# =============================================================================
# SQLiteViewMixin — View DDL support
# =============================================================================
