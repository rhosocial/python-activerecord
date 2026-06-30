# src/rhosocial/activerecord/backend/migration/exceptions.py
from rhosocial.activerecord.backend.named_expression.exceptions import ProcedureError


class MigrationError(ProcedureError):
    """Base exception for the migration system."""


class MigrationDependencyError(MigrationError):
    """Raised when a migration's dependency has not been applied yet."""


class MigrationAlreadyAppliedError(MigrationError):
    """Raised when attempting to apply an already-applied migration (UP direction)."""


class MigrationNotAppliedError(MigrationError):
    """Raised when attempting to rollback a migration that has not been applied (DOWN direction)."""


class MigrationVersionConflictError(MigrationError):
    """Raised when a version exists in the record store but belongs to a different FQN."""


class MigrationDialectError(MigrationError):
    """Raised when a migration references expressions/procedures incompatible with the current dialect."""