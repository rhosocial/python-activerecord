# src/rhosocial/activerecord/backend/impl/sqlite/expression/functions/__init__.py
"""SQLite-specific function expressions."""

import importlib

_MODULES = ('json',)


def __getattr__(name):
    """Resolve a public name from this namespace lazily."""
    for module_name in _MODULES:
        module = importlib.import_module(f'.{module_name}', __name__)
        if name in vars(module):
            value = vars(module)[name]
            globals()[name] = value
            return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
