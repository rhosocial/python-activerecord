"""Enums for transaction management."""

from enum import Enum, auto

class IsolationLevel(Enum):
    """Database transaction isolation levels.

    Defines standard SQL isolation levels:
    - READ_UNCOMMITTED: Lowest isolation, allows dirty reads
    - READ_COMMITTED: Prevents dirty reads
    - REPEATABLE_READ: Prevents non-repeatable reads
    - SERIALIZABLE: Highest isolation, prevents phantom reads
    """
    READ_UNCOMMITTED = auto()
    READ_COMMITTED = auto()
    REPEATABLE_READ = auto()
    SERIALIZABLE = auto()