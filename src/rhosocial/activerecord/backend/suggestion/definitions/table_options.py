# src/rhosocial/activerecord/backend/suggestion/definitions/table_options.py
"""Value definitions for CREATE TABLE option suggestions.

A backend answer is a value (frozen dataclass), pure and zero-I/O: it reports
which character set, collation, storage engine or EXPLAIN format this dialect
recommends. The caller owns the decision; nothing here renders SQL.
"""
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class TextEncodingSuggestion:
    """The character set and collation this dialect recommends."""

    charset: str
    collation: Optional[str] = None
    reason: str = ""


@dataclass(frozen=True)
class StorageEngineSuggestion:
    """The storage engine this dialect recommends for an ordinary table."""

    engine: str
    transactional: bool = True
    reason: str = ""


@dataclass(frozen=True)
class ExplainFormatSuggestion:
    """The EXPLAIN output format this dialect recommends."""

    format: str
    reason: str = ""
