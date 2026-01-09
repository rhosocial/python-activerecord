# src/rhosocial/activerecord/interface/__init__.py
"""
Package interface provides core interfaces for ActiveRecord implementation.
"""
from .base import ModelEvent, ModelT, DictT, QueryT
from .model import IActiveRecord
from .query import IQuery, IActiveQuery, ICTEQuery, ISetOperationQuery, IDialect
from .update import IUpdateBehavior

__all__ = [
    'IActiveRecord',
    'IUpdateBehavior',
    'ISetOperationQuery',
    'IDialect',
    'IActiveQuery',
    'ICTEQuery',
    'ModelEvent',
    'IQuery',
    'ModelT',
    'DictT',
    'QueryT',
]
