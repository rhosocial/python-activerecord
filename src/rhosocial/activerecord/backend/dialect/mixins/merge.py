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

    def format_merge_statement(self, expr: "MergeExpression") -> Tuple[str, tuple]:
        """Format MERGE statement."""
        all_params: List[Any] = []
        target_sql, target_params = expr.target.to_sql()
        all_params.extend(target_params)
        source_sql, source_params = expr.source.to_sql()
        all_params.extend(source_params)
        on_sql, on_params = expr.on_condition.to_sql()
        all_params.extend(on_params)

        merge_sql_parts = [f"MERGE INTO {target_sql}", f"USING {source_sql}", f"ON {on_sql}"]

        # Import here to avoid circular imports
        from ...expression.statements import MergeActionType

        for action in expr.when_matched:
            action_sql_parts = []
            if action.condition:
                cond_sql, cond_params = action.condition.to_sql()
                action_sql_parts.append(f"WHEN MATCHED AND {cond_sql}")
                all_params.extend(cond_params)
            else:
                action_sql_parts.append("WHEN MATCHED")

            if action.action_type == MergeActionType.UPDATE:
                assignments = []
                for col, as_expr in action.assignments.items():
                    as_sql, as_params = as_expr.to_sql()
                    assignments.append(f"{self.format_identifier(col)} = {as_sql}")
                    all_params.extend(as_params)
                action_sql_parts.append(f"THEN UPDATE SET {', '.join(assignments)}")
            elif action.action_type == MergeActionType.DELETE:
                action_sql_parts.append("THEN DELETE")
            merge_sql_parts.append(" ".join(action_sql_parts))

        for action in expr.when_not_matched:
            action_sql_parts = []
            if action.condition:
                cond_sql, cond_params = action.condition.to_sql()
                action_sql_parts.append(f"WHEN NOT MATCHED AND {cond_sql}")
                all_params.extend(cond_params)
            else:
                action_sql_parts.append("WHEN NOT MATCHED")

            if action.action_type == MergeActionType.INSERT:
                insert_cols, insert_vals = [], []
                for col, val_expr in action.assignments.items():
                    insert_cols.append(self.format_identifier(col))
                    val_sql, val_params = val_expr.to_sql()
                    insert_vals.append(val_sql)
                    all_params.extend(val_params)
                if insert_cols:
                    action_sql_parts.append(f"THEN INSERT ({', '.join(insert_cols)}) VALUES ({', '.join(insert_vals)})")
                else:
                    action_sql_parts.append("THEN INSERT DEFAULT VALUES")
            merge_sql_parts.append(" ".join(action_sql_parts))

        # Handle WHEN NOT MATCHED BY SOURCE clauses
        for action in expr.when_not_matched_by_source:
            action_sql_parts = []
            if action.condition:
                cond_sql, cond_params = action.condition.to_sql()
                action_sql_parts.append(f"WHEN NOT MATCHED BY SOURCE AND {cond_sql}")
                all_params.extend(cond_params)
            else:
                action_sql_parts.append("WHEN NOT MATCHED BY SOURCE")

            if action.action_type == MergeActionType.UPDATE:
                assignments = []
                for col, as_expr in action.assignments.items():
                    as_sql, as_params = as_expr.to_sql()
                    assignments.append(f"{self.format_identifier(col)} = {as_sql}")
                    all_params.extend(as_params)
                action_sql_parts.append(f"THEN UPDATE SET {', '.join(assignments)}")
            elif action.action_type == MergeActionType.DELETE:
                action_sql_parts.append("THEN DELETE")
            merge_sql_parts.append(" ".join(action_sql_parts))

        return " ".join(merge_sql_parts), tuple(all_params)
