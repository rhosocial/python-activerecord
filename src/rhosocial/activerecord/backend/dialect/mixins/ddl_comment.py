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

from ...expression.objects import SchemaObject

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

        The object renders itself, so a qualified name comes out of the
        namespace machinery rather than being assembled here; a ``column`` is
        appended after it when the target is a column of that object.
        ``comment=None`` renders ``IS NULL`` (clears the comment).  The text is
        inlined (DDL carries no bind parameters).

        Args:
            expr: The comment expression carrying ``object_type``, the
                ``object`` being commented on, ``comment`` and an optional
                ``column``.

        Returns:
            Tuple of (SQL string, parameters tuple) for the statement.

        Raises:
            TypeError: ``CommentOnExpression.object`` is not a SchemaObject. Any
            other value would be named by its own protocol inside COMMENT ON.
            UnsupportedFeatureError: If :meth:`supports_comment_on` is False.
        """
        if not isinstance(expr.object, SchemaObject):
            raise TypeError(
                f"CommentOnExpression.object must be a SchemaObject, "
                f"got {type(expr.object).__name__}"
            )
        from ..exceptions import UnsupportedFeatureError

        if not self.supports_comment_on():
            raise UnsupportedFeatureError(self.name, "COMMENT ON")

        object_type = getattr(expr.object_type, "value", expr.object_type)
        object_sql, object_params = expr.object.to_sql()
        if expr.column:
            object_sql = f"{object_sql}.{self.format_identifier(expr.column)}"

        head = f"COMMENT ON {object_type} {object_sql} IS"
        if expr.comment is None:
            return f"{head} NULL", object_params
        escaped = self._escape_sql_string(expr.comment)
        return f"{head} '{escaped}'", object_params


__all__ = ["CommentOnMixin"]
