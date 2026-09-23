# src/rhosocial/activerecord/backend/dialect/mixins/ddl_comment.py
"""Standalone ``COMMENT ON`` dialect capability and generic formatter.

``COMMENT ON`` is a standalone statement that annotates an existing schema
object — it is *not* an inline CREATE TABLE clause.  Backends whose only
comment mechanism is the standalone statement (PostgreSQL / Oracle /
Firebird / Snowflake) advertise :meth:`CommentOnMixin.supports_comment_on`
and inherit the generic rendering here, overriding only when their grammar
differs (version gates, parameter binding, extra object kinds).
"""

from typing import Tuple, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from ...expression.statements.ddl_comment import CommentOnExpression


class CommentOnMixin:
    """Standalone ``COMMENT ON`` capability check and generic formatter."""

    def supports_comment_on(self) -> bool:
        """Whether standalone ``COMMENT ON`` statements are supported.

        Defaults to ``False``; PostgreSQL, Oracle, Firebird, and Snowflake
        override to True.
        """
        return False

    def format_comment_statement(
        self, expr: "CommentOnExpression"
    ) -> Tuple[str, tuple]:
        """Format a standalone ``COMMENT ON <object> IS '<text>'`` statement.

        Renders the portable de-facto vendor form::

            COMMENT ON <OBJECT TYPE> [<schema>.]<object> IS '<text>'

        Dotted ``object_name`` segments (``table.column``) are quoted
        segment-by-segment so the target stays a valid qualified reference.
        ``comment=None`` renders ``IS NULL`` (clears the comment).  The text is
        inlined (DDL carries no bind parameters).

        Args:
            expr: The comment expression carrying ``object_type``,
                ``object_name``, ``comment`` and an optional ``schema``.

        Returns:
            Tuple of (SQL string, parameters tuple) for the statement.

        Raises:
            UnsupportedFeatureError: If :meth:`supports_comment_on` is False.
        """
        from ..exceptions import UnsupportedFeatureError

        if not self.supports_comment_on():
            raise UnsupportedFeatureError(self.name, "COMMENT ON")

        object_type = getattr(expr.object_type, "value", expr.object_type)
        name_parts = []
        schema = getattr(expr, "schema", None)
        if schema:
            name_parts.append(self.format_identifier(schema))
        name_parts.extend(
            self.format_identifier(part) for part in str(expr.object_name).split(".")
        )
        object_sql = ".".join(name_parts)

        head = f"COMMENT ON {object_type} {object_sql} IS"
        if expr.comment is None:
            return f"{head} NULL", ()
        escaped = self._escape_sql_string(expr.comment)
        return f"{head} '{escaped}'", ()


__all__ = ["CommentOnMixin"]
