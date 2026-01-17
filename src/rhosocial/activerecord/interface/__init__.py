# src/rhosocial/activerecord/interface/__init__.py
"""
Package interface provides core interfaces for ActiveRecord implementation.
"""
from .base import ModelEvent, DictT, QueryT
from .model import IActiveRecord, IAsyncActiveRecord, ActiveRecordBase
from .query import IQuery, IAsyncQuery, IActiveQuery, IAsyncActiveQuery, ICTEQuery, IAsyncCTEQuery, ISetOperationQuery, IBackend, IAsyncBackend, IQueryBuilding, ThreadSafeDict
from .update import IUpdateBehavior

__all__ = [
    'ActiveRecordBase',
    'IActiveRecord',
    'IAsyncActiveRecord',
    'IUpdateBehavior',
    'ISetOperationQuery',
    'IBackend',
    'IAsyncBackend',
    'IQuery',
    'IAsyncQuery',
    'IActiveQuery',
    'IAsyncActiveQuery',
    'ICTEQuery',
    'IAsyncCTEQuery',
    'IQueryBuilding',
    'ThreadSafeDict',
    'ModelEvent',
    'DictT',
    'QueryT',
]
