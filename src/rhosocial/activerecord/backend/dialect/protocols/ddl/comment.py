# src/rhosocial/activerecord/backend/dialect/protocols/ddl/comment.py
"""CommentSupport protocol.

Re-exported from :mod:`rhosocial.activerecord.backend.dialect.protocols`;
see that package for the full protocol surface and the rules the conformance
tests enforce.
"""

from typing import Tuple, Protocol, runtime_checkable, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from ....expression.statements import CommentOnExpression


@runtime_checkable
class CommentSupport(Protocol):
    """Protocol for the standalone ``COMMENT ON`` statement.

    ``COMMENT ON`` annotates an existing schema object and is deliberately
    distinct from the inline CREATE TABLE comment *clauses* (the inline
    *table*-comment clause is declared by :class:`CreateTableSupport`, the inline
    *column*-comment clause by ``DDLColumnMixin``). A dialect advertises this
    protocol when it renders the standalone statement
    (PostgreSQL/Oracle/Firebird/Snowflake); dialects whose only comment
    mechanism is the inline clause do not.
    """

    def supports_comment_on(self) -> bool:
        """Whether standalone ``COMMENT ON`` statements are supported."""
        ...  # pragma: no cover

    def format_comment_statement(self, expr: "CommentOnExpression") -> Tuple[str, tuple]:
        """Render a standalone ``COMMENT ON <object> IS '<text>'`` statement."""
        ...  # pragma: no cover


# ============================================================
# Introspection Support Protocol
# ============================================================


if TYPE_CHECKING:  # pragma: no cover
    pass
