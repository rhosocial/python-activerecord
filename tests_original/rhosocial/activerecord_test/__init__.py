# tests/rhosocial/activerecord_test/__init__.py
"""RhoSocial ActiveRecord Test Package

This package provides reusable test utilities and fixtures for ActiveRecord implementations.
It can be imported by dependent packages to ensure compatibility and consistency.

Usage:
    from rhosocial.activerecord_test import *
    
    # Or import specific modules:
    from rhosocial.activerecord_test.utils import create_active_record_fixture
    from rhosocial.activerecord_test.fixtures import storage
"""

# Core test utilities
from .utils import (
    get_backend_name,
    load_schema_file,
    DBTestConfig,
    generate_test_configs,
    create_active_record_fixture,
    DB_HELPERS,
    DB_CONFIGS,
    logger
)

# Test fixtures
from . import fixtures

# Backend tests
from . import backend

# Basic functionality tests
from . import basic

# Community example tests
from . import community

# Event system tests
from . import events

# Interface tests
from . import interface

# Mixin tests
from . import mixins

# Query tests
from . import query

# Relation tests
from . import relation

__all__ = [
    # Core utilities
    'get_backend_name',
    'load_schema_file',
    'DBTestConfig',
    'generate_test_configs',
    'create_active_record_fixture',
    'DB_HELPERS',
    'DB_CONFIGS',
    'logger',

    # Test modules
    'fixtures',
    'backend',
    'basic',
    'community',
    'events',
    'interface',
    'mixins',
    'query',
    'relation',
]

__version__ = '1.0.0'
__author__ = 'RhoSocial Team'
__description__ = 'Reusable test package for ActiveRecord implementations'
