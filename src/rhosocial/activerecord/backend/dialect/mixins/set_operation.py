# src/rhosocial/activerecord/backend/dialect/mixins/set_operation.py
"""Set operation (UNION/INTERSECT/EXCEPT) formatting for the dialect layer.

Provides the capability probes and SQL rendering for compound queries that
combine two query sides. The node carries the operation as a **word form**
(``union`` / ``union_all`` / ``intersect`` / ``except``); this formatter maps
the word back to the SQL spelling and gates it behind the per-operation
probes.
"""
from typing import List, Tuple, TYPE_CHECKING

from ...expression.query_sources import SetOperationKind

if TYPE_CHECKING:  # pragma: no cover
    from ...expression.query_sources import SetOperation
    from ...expression.statements import SetOperationStatement

#: Compound-SELECT word form -> the SQL keyword this dialect spells it with.
#: Keyed by the enum, so a word that is not one of the four cannot reach here
#: and a fifth operation cannot be added without saying what it renders as.
SET_OPERATION_KEYWORD = {
    SetOperationKind.UNION: "UNION",
    SetOperationKind.UNION_ALL: "UNION ALL",
    SetOperationKind.INTERSECT: "INTERSECT",
    SetOperationKind.EXCEPT: "EXCEPT",
}


class SetOperationMixin:
    """Mixin providing set operation support and SQL formatting.

    The capability probes default to False; dialects that support compound
    queries override the ones relevant to their syntax.
    """

    def supports_union(self) -> bool:
        """Whether UNION operation is supported.

        Defaults to False; dialects that support it override this.
        """
        return False

    def supports_union_all(self) -> bool:
        """Whether UNION ALL operation is supported.

        Defaults to False; dialects that support it override this.
        """
        return False

    def supports_intersect(self) -> bool:
        """Whether INTERSECT operation is supported.

        Defaults to False; dialects that support it override this.
        """
        return False

    def supports_except(self) -> bool:
        """Whether EXCEPT operation is supported.

        Defaults to False; dialects that support it override this.
        """
        return False

    def format_set_operation(self, expr: "SetOperation") -> Tuple[str, Tuple]:
        """Format a set operation node (UNION, INTERSECT, EXCEPT).

        Args:
            expr: The node exposing ``op`` (a word form), ``left`` and
                ``right``.

        Returns:
            Tuple of (SQL string, parameters tuple).

        Raises:
            UnsupportedFeatureError: The dialect does not support the
                requested operation (the per-operation probe said no).
        """
        from ..exceptions import UnsupportedFeatureError

        probe = {
            SetOperationKind.UNION: self.supports_union,
            SetOperationKind.UNION_ALL: self.supports_union_all,
            SetOperationKind.INTERSECT: self.supports_intersect,
            SetOperationKind.EXCEPT: self.supports_except,
        }[expr.op]
        if not probe():
            raise UnsupportedFeatureError(
                self.name,
                f"{SET_OPERATION_KEYWORD[expr.op]} operation",
                f"{self.name} does not support {SET_OPERATION_KEYWORD[expr.op]}.",
            )
        left_sql, left_params = expr.left.to_sql()
        right_sql, right_params = expr.right.to_sql()
        base_sql = f"{left_sql} {SET_OPERATION_KEYWORD[expr.op]} {right_sql}"
        # Set operations at top level do not need outer parentheses.
        # When used as a subquery (e.g. in a FROM clause), the caller
        # (Subquery / QueryStatement / dql.py) adds the required wrapping.
        return base_sql, tuple(left_params + right_params)

    def format_set_operation_statement(
        self, expr: "SetOperationStatement"
    ) -> Tuple[str, Tuple]:
        """Format a compound SELECT: its parts joined by the operator word.

        The only text this method contributes is the keyword itself, mapped
        from the node's word form through the same table the binary formatter
        uses, so one spelling of ``UNION ALL`` exists in the tree and one in
        the dialect. Everything else is already rendered: each part is a real
        query statement and renders through its own ``format_query_statement``,
        keeping the projection, the identifiers and the bind parameters of
        every arm on the side that owns them.

        Args:
            expr: The node exposing ``op`` (a word form) and ``parts``.

        Returns:
            Tuple of (SQL string, parameters tuple), the parameters
            concatenated in part order.

        Raises:
            UnsupportedFeatureError: The dialect does not support the
                requested operation (the per-operation probe said no).
        """
        from ..exceptions import UnsupportedFeatureError

        if self.strict_validation:
            expr.validate(strict=True)

        probe = {
            SetOperationKind.UNION: self.supports_union,
            SetOperationKind.UNION_ALL: self.supports_union_all,
            SetOperationKind.INTERSECT: self.supports_intersect,
            SetOperationKind.EXCEPT: self.supports_except,
        }[expr.op]
        if not probe():
            raise UnsupportedFeatureError(
                self.name,
                f"{SET_OPERATION_KEYWORD[expr.op]} operation",
                f"{self.name} does not support {SET_OPERATION_KEYWORD[expr.op]}.",
            )
        keyword = SET_OPERATION_KEYWORD[expr.op]
        rendered: List[str] = []
        params: List[object] = []
        for part in expr.parts:
            part_sql, part_params = part.to_sql()
            rendered.append(part_sql)
            params.extend(part_params)
        return f" {keyword} ".join(rendered), tuple(params)
