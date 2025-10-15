# src/rhosocial/activerecord/backend/__init__.py
"""
Database backend abstraction layer for Python ORMs.

This module provides a generic interface for database operations, with support for:
- Multiple database backends (SQLite, MySQL, PostgreSQL, etc.)
- Type mapping and conversion
- Transaction management
- SQL dialect handling
- Connection pooling
"""
# Extend the namespace path to support backend implementations from separate packages
# This is crucial for the distributed backend architecture where each database backend
# (mysql, postgresql, etc.) can be installed independently
__path__ = __import__('pkgutil').extend_path(__path__, __name__)

__version__ = "0.8.0"

from . import base
from . import dialect
from . import config
from . import typing
from . import errors
from . import helpers
from . import transaction
from . import basic_type_converter
from . import type_converters

# Core interfaces and base classes
from .base import StorageBackend, ColumnTypes
from .dialect import (
    TypeMapping,
    SQLDialectBase,
    SQLBuilder,
    SQLExpressionBase,
    ReturningOptions,
    ReturningClauseHandler,
    ExplainOptions,
    ExplainType,
    ExplainFormat,
    AggregateHandler,
    JsonOperationHandler,
    CTEHandler,
)
from .config import ConnectionConfig

# Type definitions and configuration
from .typing import (
    QueryResult,
    DatabaseValue,
    PythonValue,
    DatabaseType,
)

# Error types
from .errors import (
    DatabaseError,
    ConnectionError,
    TransactionError,
    QueryError,
    ValidationError,
    LockError,
    DeadlockError,
    IntegrityError,
    TypeConversionError,
    OperationalError,
    RecordNotFound,
    ReturningNotSupportedError,
    GroupingSetNotSupportedError,
    JsonOperationNotSupportedError,
    WindowFunctionNotSupportedError,
    CTENotSupportedError,
    IsolationLevelError,
)

# Helper functions
from .helpers import (
    convert_datetime,
    parse_datetime,
    safe_json_dumps,
    safe_json_loads,
    array_converter,
    measure_time,
    format_with_length,
    format_decimal,
)

# Transaction
from .transaction import (
    TransactionManager,
    IsolationLevel,
    TransactionState,
)

# Type Converters
from .basic_type_converter import (
    BasicTypeConverter,
    DateTimeConverter,
    BooleanConverter,
    UUIDConverter,
    JSONConverter,
    DecimalConverter,
    ArrayConverter,
    EnumConverter,
)
from .type_converters import (
    TypeConverter,
    BaseTypeConverter,
    TypeRegistry,
)

# Capabilities
from .capabilities import (
    DatabaseCapabilities,
    CapabilityCategory,
    SetOperationCapability,
    WindowFunctionCapability,
    AdvancedGroupingCapability,
    CTECapability,
    JSONCapability,
    ReturningCapability,
    TransactionCapability,
    BulkOperationCapability,
    ALL_SET_OPERATIONS,
    ALL_WINDOW_FUNCTIONS,
    ALL_CTE_FEATURES,
    ALL_JSON_OPERATIONS,
    ALL_RETURNING_FEATURES,
)

__all__ = [
    # Base classes
    'StorageBackend',
    # Dialect related
    'TypeMapping',
    'ColumnTypes',
    'SQLBuilder',
    'SQLExpressionBase',
    'ReturningOptions',
    'ReturningClauseHandler',
    'ExplainOptions',
    'ExplainType',
    'ExplainFormat',
    'AggregateHandler',
    'JsonOperationHandler',
    'CTEHandler',

    # Types and configs
    'ConnectionConfig',
    'QueryResult',
    'DatabaseValue',
    'PythonValue',
    'DatabaseType',

    # Errors
    'DatabaseError',
    'ConnectionError',
    'TransactionError',
    'QueryError',
    'ValidationError',
    'LockError',
    'DeadlockError',
    'IntegrityError',
    'TypeConversionError',
    'OperationalError',
    'RecordNotFound',
    'ReturningNotSupportedError',
    'GroupingSetNotSupportedError',
    'JsonOperationNotSupportedError',
    'WindowFunctionNotSupportedError',
    'CTENotSupportedError',
    'IsolationLevelError',

    # Helper functions
    'convert_datetime',
    'parse_datetime',
    'safe_json_dumps',
    'safe_json_loads',
    'array_converter',
    'measure_time',
    'format_with_length',
    'format_decimal',

    # Expression
    'SQLDialectBase',
    'SQLExpressionBase',

    # Transaction
    'TransactionManager',
    'IsolationLevel',
    'TransactionState',

    # Type Converters
    'BasicTypeConverter',
    'DateTimeConverter',
    'BooleanConverter',
    'UUIDConverter',
    'JSONConverter',
    'DecimalConverter',
    'ArrayConverter',
    'EnumConverter',
    'TypeConverter',
    'BaseTypeConverter',
    'TypeRegistry',
    
    # Capabilities
    'DatabaseCapabilities',
    'CapabilityCategory',
    'SetOperationCapability',
    'WindowFunctionCapability',
    'AdvancedGroupingCapability',
    'CTECapability',
    'JSONCapability',
    'ReturningCapability',
    'TransactionCapability',
    'BulkOperationCapability',
    'ALL_SET_OPERATIONS',
    'ALL_WINDOW_FUNCTIONS',
    'ALL_CTE_FEATURES',
    'ALL_JSON_OPERATIONS',
    'ALL_RETURNING_FEATURES',
]
