# src/rhosocial/activerecord/backend/schema.py
"""
Defines types related to SQL statement classification.

This file contains enumerations used for categorizing SQL statements
during execution and processing.
"""
from enum import Enum, auto


class StatementType(Enum):
    """Explicitly defines the type of SQL statement."""
    # General categories
    DQL = auto()  # Data Query Language
    DML = auto()  # Data Manipulation Language
    DDL = auto()  # Data Definition Language
    TCL = auto()  # Transaction Control Language
    OTHER = auto()  # Other or unknown types

    # Specific DQL/DML statements
    SELECT = auto()
    INSERT = auto()
    UPDATE = auto()
    DELETE = auto()
    TRUNCATE = auto()
    MERGE = auto()

    # Procedure/Function related
    CALL = auto()
    EXECUTE = auto()

    # Explain statement type
    EXPLAIN = auto()
