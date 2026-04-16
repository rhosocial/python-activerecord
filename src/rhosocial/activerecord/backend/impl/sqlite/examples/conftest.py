# src/rhosocial/activerecord/backend/impl/sqlite/examples/conftest.py
"""
Example metadata configuration.

This file defines metadata for all examples in this directory.
The inspector reads this file to get title, dialect_protocols, and priority.
"""

EXAMPLES_META = {
    'connection/quickstart.py': {
        'title': 'Connect to SQLite and Execute Queries',
        'dialect_protocols': [],
        'priority': 10,
    },
    'ddl/create_table.py': {
        'title': 'Create Table',
        'dialect_protocols': [],
        'priority': 10,
    },
    'ddl/create_index.py': {
        'title': 'Create Index',
        'dialect_protocols': [],
        'priority': 10,
    },
    'ddl/alter_table.py': {
        'title': 'Alter Table',
        'dialect_protocols': [],
        'priority': 10,
    },
    'ddl/view.py': {
        'title': 'CREATE VIEW',
        'dialect_protocols': [],
        'priority': 10,
    },
    'update/basic.py': {
        'title': 'Update with RETURNING',
        'dialect_protocols': ['ReturningSupport'],
        'priority': 10,
    },
    'insert/with_returning.py': {
        'title': 'Insert with RETURNING',
        'dialect_protocols': ['ReturningSupport'],
        'priority': 10,
    },
    'insert/batch.py': {
        'title': 'Batch Insert',
        'dialect_protocols': [],
        'priority': 10,
    },
    'delete/basic.py': {
        'title': 'Delete with RETURNING',
        'dialect_protocols': ['ReturningSupport'],
        'priority': 10,
    },
    'transaction/basic.py': {
        'title': 'Transaction Control',
        'dialect_protocols': [],
        'priority': 10,
    },
    'transaction/exclusive.py': {
        'title': 'SQLite Transaction Modes',
        'dialect_protocols': [],
        'priority': 10,
    },
    'query/basic.py': {
        'title': 'Basic SELECT Query',
        'dialect_protocols': [],
        'priority': 10,
    },
    'query/join.py': {
        'title': 'JOIN Query',
        'dialect_protocols': [],
        'priority': 10,
    },
    'query/aggregate.py': {
        'title': 'Aggregate Query',
        'dialect_protocols': [],
        'priority': 10,
    },
    'query/subquery.py': {
        'title': 'Subquery',
        'dialect_protocols': [],
        'priority': 10,
    },
    'query/window.py': {
        'title': 'Window Functions',
        'dialect_protocols': ['WindowFunctionSupport'],
        'priority': 10,
    },
    'query/predicate.py': {
        'title': 'Complex Predicates',
        'dialect_protocols': [],
        'priority': 10,
    },
    'query/distinct.py': {
        'title': 'SELECT DISTINCT',
        'dialect_protocols': [],
        'priority': 10,
    },
    'query/union.py': {
        'title': 'UNION using SetOperationExpression',
        'dialect_protocols': [],
        'priority': 10,
    },
    'types/json_basic.py': {
        'title': 'JSON Operations',
        'dialect_protocols': ['JSONSupport'],
        'priority': 10,
    },
}
