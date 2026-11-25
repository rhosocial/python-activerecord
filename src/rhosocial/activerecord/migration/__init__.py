# src/rhosocial/activerecord/migration/__init__.py
"""ActiveRecord-layer migration management.

This is the $\\mathcal{A}$-side migration system: users write ``up(ctx)`` /
``down(ctx)`` logic, and this package orders, executes and previews (dry-run)
those migrations. It is deliberately separate from ``backend.migration`` (the
backend runtime system) -- backends do not participate in management, they only
supply "how-to" suggestions through the suggestion protocols.

Managed pieces (per activerecord-migration.md formalization):
- ``MigrationContext`` -- what a user's up/down logic sees (suggest + apply + dry-run).
- ``Migration`` -- a versioned up/down pair.
- ``MigrationRunner`` -- ordering, dependency checks, execution, dry-run, records.
"""

from .context import AsyncMigrationContext, MigrationContext
from .core import AsyncMigration, Migration
from .runner import (
    AsyncMigrationRunner,
    MigrationRunner,
    MigrationError,
    MigrationDependencyError,
    MigrationAlreadyAppliedError,
    MigrationNotAppliedError,
)
from .record import MigrationRecord, MigrationRecordStore, InMemoryMigrationRecordStore
from .schema_change import (
    diff_declarations, plan_changes, ChangePlan, FieldChange,
    resolve_point, resolve_suggestions, ResolvedSuggestion, SuggestionResolution,
)

__all__ = [
    "MigrationContext",
    "AsyncMigrationContext",
    "Migration",
    "AsyncMigration",
    "MigrationRunner",
    "AsyncMigrationRunner",
    "MigrationError",
    "MigrationDependencyError",
    "MigrationAlreadyAppliedError",
    "MigrationNotAppliedError",
    "MigrationRecord",
    "MigrationRecordStore",
    "InMemoryMigrationRecordStore",
    "diff_declarations",
    "plan_changes",
    "ChangePlan",
    "FieldChange",
    "resolve_point",
    "resolve_suggestions",
    "ResolvedSuggestion",
    "SuggestionResolution",
]
