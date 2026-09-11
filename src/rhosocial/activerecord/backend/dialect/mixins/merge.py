# src/rhosocial/activerecord/backend/dialect/mixins/merge.py
from typing import Any, List, Tuple, TYPE_CHECKING

from ..exceptions import UnsupportedFeatureError

if TYPE_CHECKING:  # pragma: no cover
    from ...expression.statements import MergeExpression


class MergeMixin:
    """Mixin for MERGE statement support."""

    def supports_merge_statement(self) -> bool:
        """Whether MERGE statement is supported."""
        return False

    def format_merge_action(self, expr: "MergeAction") -> Tuple[str, tuple]:
        """Format a single WHEN [NOT] MATCHED action clause.

        The ``matched`` context (e.g. ``"WHEN MATCHED"``) is read from
        ``expr.matched``, set by the caller before dispatching.
        """
        from ...expression.statements import MergeActionType

        all_params: List[Any] = []
        parts = [expr.matched]
        if expr.condition is not None:
            cond_sql, cond_params = expr.condition.to_sql()
            parts.append(f"AND {cond_sql}")
            all_params.extend(cond_params)

        if expr.action_type == MergeActionType.UPDATE:
            assignments = []
            for col, as_expr in expr.assignments.items():
                as_sql, as_params = as_expr.to_sql()
                assignments.append(f"{self.format_identifier(col)} = {as_sql}")
                all_params.extend(as_params)
            parts.append(f"THEN UPDATE SET {', '.join(assignments)}")
        elif expr.action_type == MergeActionType.DELETE:
            parts.append("THEN DELETE")
        elif expr.action_type == MergeActionType.INSERT:
            insert_cols, insert_vals = [], []
            for col, val_expr in expr.assignments.items():
                insert_cols.append(self.format_identifier(col))
                val_sql, val_params = val_expr.to_sql()
                insert_vals.append(val_sql)
                all_params.extend(val_params)
            if insert_cols:
                parts.append(f"THEN INSERT ({', '.join(insert_cols)}) VALUES ({', '.join(insert_vals)})")
            else:
                parts.append("THEN INSERT DEFAULT VALUES")
        return " ".join(parts), tuple(all_params)

    def format_merge_statement(self, expr: "MergeExpression") -> Tuple[str, tuple]:
        """Format MERGE statement."""
        all_params: List[Any] = []
        target_sql, target_params = expr.target_table.to_sql()
        all_params.extend(target_params)
        source_sql, source_params = expr.source.to_sql()
        all_params.extend(source_params)
        on_sql, on_params = expr.on_condition.to_sql()
        all_params.extend(on_params)

        merge_sql_parts = [f"MERGE INTO {target_sql}", f"USING {source_sql}", f"ON {on_sql}"]

        for action in expr.when_matched:
            action.matched = "WHEN MATCHED"
            action_sql, action_params = self.format_merge_action(action)
            merge_sql_parts.append(action_sql)
            all_params.extend(action_params)

        for action in expr.when_not_matched:
            action.matched = "WHEN NOT MATCHED"
            action_sql, action_params = self.format_merge_action(action)
            merge_sql_parts.append(action_sql)
            all_params.extend(action_params)

        for action in expr.when_not_matched_by_source:
            action.matched = "WHEN NOT MATCHED BY SOURCE"
            action_sql, action_params = self.format_merge_action(action)
            merge_sql_parts.append(action_sql)
            all_params.extend(action_params)

        return " ".join(merge_sql_parts), tuple(all_params)
