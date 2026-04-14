# src/rhosocial/activerecord/backend/impl/sqlite/examples/conftest.py
"""
Example metadata configuration.

This file defines metadata for all examples in this directory.
The inspector reads this file to get title, dialect_protocols, and priority.
"""

EXAMPLES_META = {
    'ddl/create_table.py': {
        'title': 'Create Table',
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
}