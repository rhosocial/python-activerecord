# src/rhosocial/activerecord/backend/impl/dummy/__init__.py
from .backend import DummyBackend
from .async_backend import AsyncDummyBackend

__all__ = [
    "DummyBackend",
    "AsyncDummyBackend",
]
