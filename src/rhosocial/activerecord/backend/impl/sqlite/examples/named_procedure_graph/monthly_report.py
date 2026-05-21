# src/rhosocial/activerecord/backend/impl/sqlite/examples/named_procedure_graph/monthly_report.py
"""Monthly sales report procedure graph.

This module provides a ProcedureGraph for generating monthly sales reports.
The graph demonstrates:
- Multiple steps with dependencies
- Parallel execution of independent steps
- Conditional execution via condition field
- Parameter interpolation

Usage:
    Python:
        >>> from rhosocial.activerecord.backend.named_expression import resolve_named_procedure_graph
        >>> graph, resolver = resolve_named_procedure_graph(
        ...     "rhosocial.activerecord.backend.impl.sqlite.examples.named_procedure_graph.monthly_report",
        ...     dialect,
        ...     {"month": "2026-04"}
        ... )
        >>> print(f"Waves: {len(graph.waves())}")

    CLI:
        $ python -m rhosocial.activerecord.backend.impl.sqlite named-procedure-graph run \\
            rhosocial.activerecord.backend.impl.sqlite.examples.named_procedure_graph.monthly_report \\
            --params '{"month": "2026-04"}' \\
            --dry-run
"""
from rhosocial.activerecord.backend.named_expression import (
    ProcedureGraph,
    StepNode,
    GraphTransactionMode,
)


def monthly_report_graph(dialect, params=None):
    """Generate monthly sales report graph.

    This graph executes:
    1. Aggregate sales data for the month
    2. Aggregate refunds data for the month (parallel with step 1)
    3. Join sales and refunds
    4. Write summary to report table

    Args:
        dialect: SQL dialect instance.
        params: Optional dict with 'month' key.

    Returns:
        ProcedureGraph instance.
    """
    month = (params or {}).get("month", "")
    return (
        ProcedureGraph(
            transaction_mode=GraphTransactionMode.AUTO,
            description=f"Monthly report for {month}",
        )
        | StepNode.query(
            "sales",
            "rhosocial.activerecord.backend.impl.sqlite.examples.named_procedure_graph.q.agg_sales",
            params={"month": month},
            label=f"Aggregate sales for {month}",
        )
        | StepNode.query(
            "refunds",
            "rhosocial.activerecord.backend.impl.sqlite.examples.named_procedure_graph.q.agg_refunds",
            params={"month": month},
            label=f"Aggregate refunds for {month}",
        )
        | StepNode.query(
            "join",
            "rhosocial.activerecord.backend.impl.sqlite.examples.named_procedure_graph.q.join_sales_refunds",
            depends_on=["sales", "refunds"],
            label="Join sales and refunds data",
        )
        | StepNode.query(
            "write",
            "rhosocial.activerecord.backend.impl.sqlite.examples.named_procedure_graph.q.write_summary",
            params={"month": month},
            depends_on=["join"],
            label="Write summary report",
        )
    )


def monthly_report_with_threshold_graph(dialect, params=None):
    """Monthly report with threshold check.

    This graph demonstrates conditional execution - only processes
    data if totals exceed a threshold.

    Args:
        dialect: SQL dialect instance.
        params: Dict with 'month' and optional 'threshold'.

    Returns:
        ProcedureGraph instance.
    """
    month = (params or {}).get("month", "")
    threshold = (params or {}).get("threshold", 1000)
    return (
        ProcedureGraph(transaction_mode=GraphTransactionMode.AUTO)
        | StepNode.query(
            "sales",
            "rhosocial.activerecord.backend.impl.sqlite.examples.named_procedure_graph.q.agg_sales",
            params={"month": month},
            bind_output={"rows[0].total": "sales_total"},
        )
        | StepNode.query(
            "check_threshold",
            "rhosocial.activerecord.backend.impl.sqlite.examples.named_procedure_graph.q.check_threshold",
            params={"threshold": threshold},
            depends_on=["sales"],
            condition="${sales_total} > " + str(threshold),
            label=f"Check if sales > {threshold}",
        )
        | StepNode.query(
            "refunds",
            "rhosocial.activerecord.backend.impl.sqlite.examples.named_procedure_graph.q.agg_refunds",
            params={"month": month},
            depends_on=["check_threshold"],
            label=f"Aggregate refunds for {month}",
        )
    )