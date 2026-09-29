# src/rhosocial/activerecord/interface/__init__.py
"""
Package interface provides core interfaces for ActiveRecord implementation.
"""

from .base import ModelEvent, DictT, QueryT
from .model import IActiveRecord, IAsyncActiveRecord, ActiveRecordBase
from .query import (
    IQuery,
    IAsyncQuery,
    IActiveQuery,
    IAsyncActiveQuery,
    ICTEQuery,
    IAsyncCTEQuery,
    ISetOperationQuery,
    IAsyncSetOperationQuery,
    IBackend,
    IAsyncBackend,
    IQueryBuilding,
    ThreadSafeDict,
)
from .update import IReadOnlyBehavior, IUpdateBehavior

__all__ = [
    "ActiveRecordBase",
    "IActiveRecord",
    "IAsyncActiveRecord",
    "IReadOnlyBehavior",
    "IUpdateBehavior",
    "ISetOperationQuery",
    "IBackend",
    "IAsyncBackend",
    "IQuery",
    "IAsyncQuery",
    "IActiveQuery",
    "IAsyncActiveQuery",
    "ICTEQuery",
    "IAsyncCTEQuery",
    "IQueryBuilding",
    "ThreadSafeDict",
    "ModelEvent",
    "DictT",
    "QueryT",
    "IAsyncSetOperationQuery",
]
