# src/rhosocial/activerecord/base/ddl/options.py
"""Dialect-free per-column options declaration."""

from __future__ import annotations

from typing import Optional


class ColumnOptions:
    """Per-column options declaration carrying typed generic column settings.

    A plain declaration (not a renderable expression): the deriver maps its
    fields onto ``ColumnDefinition``. Only **typed** fields are allowed — there
    is no ``dialect_options`` bag. Backend-specific column settings live on a
    backend's own ``XxxColumnOptions`` subclass (and are rendered by that
    backend's ``format_column_definition``).
    """

    def __init__(
        self,
        *,
        identity_start: Optional[int] = None,
        identity_increment: Optional[int] = None,
    ):
        self.identity_start = identity_start
        self.identity_increment = identity_increment
