"""
Package interface provides core interfaces for ActiveRecord implementation.
"""
from .base import ModelEvent, ModelT, DictT, QueryT
from .model import IActiveRecord
from .query import IQuery, IDictQuery
from .update import IUpdateBehavior

__all__ = [
    'IActiveRecord',
    'IUpdateBehavior',
    'ModelEvent',
    'IQuery',
    'IDictQuery',
    'ModelT',
    'DictT',
    'QueryT',
]