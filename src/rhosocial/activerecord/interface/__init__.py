# src/rhosocial/activerecord/interface/__init__.py
"""
Package interface provides core interfaces for ActiveRecord implementation.
"""
from .base import ModelEvent, ModelT, DictT, QueryT
from .model import IActiveRecord
from .query import IQuery, IActiveQuery, IAsyncActiveQuery, ICTEQuery, IAsyncCTEQuery, ISetOperationQuery, IBackend, IQueryBuilding, ThreadSafeDict
from .update import IUpdateBehavior

__all__ = [
    'IActiveRecord',
    'IUpdateBehavior',
    'ISetOperationQuery',
    'IBackend',
    'IActiveQuery',
    'IAsyncActiveQuery',
    'ICTEQuery',
    'IAsyncCTEQuery',
    'IQueryBuilding',
    'ThreadSafeDict',
    'ModelEvent',
    'IQuery',
    'ModelT',
    'DictT',
    'QueryT',
]
