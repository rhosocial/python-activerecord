# src/rhosocial/activerecord/relation/__init__.py
"""
Relations package for Python ORM-style relationship management.
Provides a flexible, type-safe way to define and manage model relationships.
"""

from .base import RelationManagementMixin
from .descriptors import RelationDescriptor, BelongsTo, HasOne, HasMany, DefaultRelationLoader
from .cache import CacheConfig, GlobalCacheConfig
from .interfaces import (
    RelationLoader,
    RelationValidation,
    RelationManagementInterface,
    AsyncRelationLoader,
    AsyncRelationValidation
)

# from .methods import DefaultRelationLoader

__all__ = [
    'RelationDescriptor',
    'RelationManagementMixin',
    'BelongsTo',
    'HasOne',
    'HasMany',
    'CacheConfig',
    'GlobalCacheConfig',
    'RelationLoader',
    'RelationValidation',
    'RelationManagementInterface',
    'AsyncRelationLoader',
    'AsyncRelationValidation',
    'DefaultRelationLoader',
]
