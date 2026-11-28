# src/rhosocial/activerecord/backend/expression/operators/__init__.py
"""Expression namespace: operators.

Every public name from the modules in this namespace is re-exported so
callers can keep importing it from this package."""

import importlib

_MODULES = ('operators',)


def __getattr__(name):
    """Resolve a public name from this namespace lazily (no import cycles)."""
    for module_name in _MODULES:
        module = importlib.import_module(f'.{module_name}', __name__)
        if name in vars(module):
            value = vars(module)[name]
            globals()[name] = value  # cache so vars()/inspect see the name
            return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
