"""
Core definitions for ActiveRecord interfaces.

This module defines the base types and enums used across the interface package.
"""
from enum import Enum, auto
from typing import TypeVar, Any, Dict

# Define interface type variables
ModelT = TypeVar('ModelT', bound='IActiveRecord')
QueryT = TypeVar('QueryT', bound='IQuery')
DictT = TypeVar('DictT', bound=Dict[str, Any])

class ModelEvent(Enum):
    """Model lifecycle events that can be subscribed to.

    Events are triggered during key operations like save and delete,
    allowing custom behavior to be injected.
    """
    BEFORE_SAVE = auto()
    AFTER_SAVE = auto()
    BEFORE_DELETE = auto()
    AFTER_DELETE = auto()
    BEFORE_VALIDATE = auto()
    AFTER_VALIDATE = auto()