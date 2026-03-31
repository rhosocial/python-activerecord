# src/rhosocial/activerecord/backend/base/logging.py
"""Logging mixin for backend implementations.

This module re-exports BackendLoggingMixin from the new logging module
for backward compatibility.
"""

from ...logging import BackendLoggingMixin as LoggingMixin

__all__ = ["LoggingMixin"]
