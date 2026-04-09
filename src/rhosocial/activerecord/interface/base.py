# src/rhosocial/activerecord/interface/base.py
"""
Core definitions for ActiveRecord interfaces.

This module defines the base types and enums used across the interface package.
"""

from enum import Enum, auto
from typing import TypeVar, Any, Dict, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from ..query import IQuery

# Define interface type variables
QueryT = TypeVar("QueryT", bound="IQuery")
DictT = TypeVar("DictT", bound=Dict[str, Any])


class ModelEvent(Enum):
    """Model lifecycle events that can be subscribed to.

    Events are triggered during key operations like insert, update, and delete,
    allowing custom behavior to be injected.

    The events are organized by operation type:
    - Validation events: BEFORE_VALIDATE, AFTER_VALIDATE
    - Insert events: BEFORE_INSERT, AFTER_INSERT (triggered on new record creation)
    - Update events: BEFORE_UPDATE, AFTER_UPDATE (triggered on existing record modification)
    - Delete events: BEFORE_DELETE, AFTER_DELETE
    """

    # Validation events
    BEFORE_VALIDATE = auto()
    AFTER_VALIDATE = auto()

    # Insert events (for new records)
    BEFORE_INSERT = auto()
    AFTER_INSERT = auto()

    # Update events (for existing records)
    BEFORE_UPDATE = auto()
    AFTER_UPDATE = auto()

    # Delete events
    BEFORE_DELETE = auto()
    AFTER_DELETE = auto()
