# src/rhosocial/activerecord/backend/migration/exceptions.py
from typing import Optional

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


class MigrationFunctionExecutionError(MigrationError):
    """Raised when a particular migration function fails.

    Carries the version and FQN so a group failure names the exact function
    instead of only reporting that the group aborted.
    """

    def __init__(
        self,
        version: str,
        fqn: str,
        cause: Optional[BaseException] = None,
        executed: Optional[list] = None,
    ):
        self.version = version
        self.fqn = fqn
        self.cause = cause
        self.executed = list(executed or [])
        self.transactional_ddl = True
        detail = f'Migration "{version}" ({fqn}) failed'
        if cause is not None:
            detail = f"{detail}: {cause}"
        super().__init__(detail)
