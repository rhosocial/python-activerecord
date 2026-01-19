# src/rhosocial/activerecord/relation/__init__.py
"""
Relations package for Python ORM-style relationship management.
Provides a flexible, type-safe way to define and manage model relationships.
"""

from .base import IRelationManagementMixin
from .descriptors import RelationDescriptor, BelongsTo, HasOne, HasMany, DefaultIRelationLoader
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
    'IRelationManagementMixin',
    'BelongsTo',
    'HasOne',
    'HasMany',
    'CacheConfig',
    'GlobalCacheConfig',
    'IRelationLoader',
    'IRelationValidation',
    'IRelationManagement',
    'IAsyncRelationLoader',
    'IAsyncRelationValidation',
    'DefaultIRelationLoader',
]
