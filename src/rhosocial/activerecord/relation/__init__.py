# src/rhosocial/activerecord/relation/__init__.py
"""
Relations package for Python ORM-style relationship management.
Provides a flexible, type-safe way to define and manage model relationships.
"""

from .base import RelationManagementMixin
from .descriptors import RelationDescriptor, BelongsTo, HasOne, HasMany, DefaultIRelationLoader
from .async_descriptors import AsyncRelationDescriptor, AsyncBelongsTo, AsyncHasOne, AsyncHasMany, AsyncDefaultRelationLoader
from .cache import CacheConfig, GlobalCacheConfig
from .interfaces import (
    IRelationLoader,
    IRelationValidation,
    IRelationManagement,
    IAsyncRelationLoader,
    IAsyncRelationValidation
)

# from .methods import DefaultRelationLoader

__all__ = [
    'RelationDescriptor',
    'AsyncRelationDescriptor',
    'RelationManagementMixin',
    'BelongsTo',
    'HasOne',
    'HasMany',
    'AsyncBelongsTo',
    'AsyncHasOne',
    'AsyncHasMany',
    'CacheConfig',
    'GlobalCacheConfig',
    'IRelationLoader',
    'IRelationValidation',
    'IRelationManagement',
    'IAsyncRelationLoader',
    'IAsyncRelationValidation',
    'DefaultIRelationLoader',
    'AsyncDefaultRelationLoader',
]
