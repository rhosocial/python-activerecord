# src/rhosocial/activerecord/backend/dialect/protocols/generatedcolumnsupport.py
"""GeneratedColumnSupport protocol.

Re-exported from :mod:`rhosocial.activerecord.backend.dialect.protocols`;
see that package for the full protocol surface and the rules the conformance
tests enforce.
"""

from typing import Protocol, runtime_checkable

@runtime_checkable
class GeneratedColumnSupport(Protocol):
    """
    Protocol for generated column (computed column) support.

    Generated columns are columns whose value is computed from an expression
    rather than being stored directly. Support varies:
    - SQLite: STORED and VIRTUAL since 3.31.0
    - PostgreSQL: STORED only (via GENERATED ALWAYS AS)
    - MySQL: STORED and VIRTUAL since 5.7
    """

    def supports_generated_columns(self) -> bool:
        """Whether generated columns are supported."""
        ...  # pragma: no cover

    def supports_stored_generated_columns(self) -> bool:
        """Whether STORED generated columns are supported."""
        ...  # pragma: no cover

    def supports_virtual_generated_columns(self) -> bool:
        """Whether VIRTUAL generated columns are supported."""
        ...  # pragma: no cover
