# src/rhosocial/activerecord/base/ddl/options.py
"""Dialect-free per-column options declaration."""

from __future__ import annotations

from typing import Any, Dict, Optional


class ColumnOptions:
    """Backend-specific per-column options plus identity sequence settings.

    A plain declaration (not a renderable expression): the deriver maps its
    fields onto ``ColumnDefinition`` (``identity_start`` / ``identity_increment``
    / ``dialect_options``). Backend-specific option names use the backend's
    namespaced keys; an unknown option is rejected by the backend at render time.
    """

    def __init__(
        self,
        *,
        identity_start: Optional[int] = None,
        identity_increment: Optional[int] = None,
        dialect_options: Optional[Dict[str, Any]] = None,
    ):
        self.identity_start = identity_start
        self.identity_increment = identity_increment
        self.dialect_options: Dict[str, Any] = dict(dialect_options or {})
