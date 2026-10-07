# src/rhosocial/activerecord/backend/dialect/protocols/ddl/truncate.py
"""TruncateSupport protocol.

Re-exported from :mod:`rhosocial.activerecord.backend.dialect.protocols`;
see that package for the full protocol surface and the rules the conformance
tests enforce.
"""

from typing import Tuple, Protocol, runtime_checkable, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from ....expression.statements import TruncateExpression


@runtime_checkable
class TruncateSupport(Protocol):
    """
    Protocol for TRUNCATE TABLE support.

    TRUNCATE provides a fast way to delete all rows from a table.
    Feature support varies:
    - TRUNCATE TABLE keyword requirement
    - RESTART IDENTITY (PostgreSQL)
    - CASCADE option (PostgreSQL)
    """

    def supports_truncate(self) -> bool:
        """Whether TRUNCATE is supported."""
        ...  # pragma: no cover

    def supports_truncate_table_keyword(self) -> bool:
        """Whether TABLE keyword is required or optional in TRUNCATE."""
        ...  # pragma: no cover

    def supports_truncate_restart_identity(self) -> bool:
        """Whether RESTART IDENTITY is supported."""
        ...  # pragma: no cover

    def supports_truncate_cascade(self) -> bool:
        """Whether CASCADE option is supported."""
        ...  # pragma: no cover

    def supports_truncate_restrict(self) -> bool:
        """Whether RESTRICT option is supported."""
        ...  # pragma: no cover

    def format_truncate_statement(self, expr: "TruncateExpression") -> Tuple[str, tuple]:
        """Format TRUNCATE TABLE statement."""
        ...  # pragma: no cover
