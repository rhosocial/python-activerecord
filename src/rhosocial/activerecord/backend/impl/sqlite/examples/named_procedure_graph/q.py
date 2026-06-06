# src/rhosocial/activerecord/backend/impl/sqlite/examples/named_procedure_graph/q.py
"""Named queries supporting monthly_report_graph.

These queries are used by the ProcedureGraph examples.
Each function takes 'dialect' as first parameter and returns
a BaseExpression that implements Executable.
"""

from rhosocial.activerecord.backend.expression import (
    QueryExpression,
    Column,
    FunctionCall,
    TableExpression,
    WhereClause,
    Literal,
)


def agg_sales(dialect, month: str = ""):
    """Aggregate sales for a given month.

    Args:
        dialect: SQL dialect instance.
        month: Month in YYYY-MM format.

    Returns:
        QueryExpression.
    """
    return QueryExpression(
        dialect,
        select=[
            FunctionCall(dialect, "SUM", Column(dialect, "amount")).as_("total"),
            FunctionCall(dialect, "COUNT", Column(dialect, "id")).as_("count"),
        ],
        from_=TableExpression(dialect, "sales"),
        where=WhereClause(dialect, condition=Column(dialect, "month") == Literal(dialect, month)),
    )


def agg_refunds(dialect, month: str = ""):
    """Aggregate refunds for a given month.

    Args:
        dialect: SQL dialect instance.
        month: Month in YYYY-MM format.

    Returns:
        QueryExpression.
    """
    return QueryExpression(
        dialect,
        select=[
            FunctionCall(dialect, "SUM", Column(dialect, "amount")).as_("total"),
            FunctionCall(dialect, "COUNT", Column(dialect, "id")).as_("count"),
        ],
        from_=TableExpression(dialect, "refunds"),
        where=WhereClause(dialect, condition=Column(dialect, "month") == Literal(dialect, month)),
    )


def join_sales_refunds(dialect):
    """Join sales and refunds data.

    Args:
        dialect: SQL dialect instance.

    Returns:
        QueryExpression joining sales and refunds.
    """
    return QueryExpression(
        dialect,
        select=[
            Column(dialect, "s.month"),
            FunctionCall(dialect, "SUM", Column(dialect, "s.amount")).as_("sales_total"),
            FunctionCall(dialect, "SUM", Column(dialect, "r.amount")).as_("refunds_total"),
        ],
    )


def write_summary(dialect, month: str = ""):
    """Write summary to report table.

    Args:
        dialect: SQL dialect instance.
        month: Month in YYYY-MM format.

    Returns:
        QueryExpression.
    """
    return QueryExpression(
        dialect,
        select=[Column(dialect, "month")],
    )


def check_threshold(dialect, threshold: int = 1000):
    """Check if threshold is met.

    Args:
        dialect: SQL dialect instance.
        threshold: Threshold value.

    Returns:
        QueryExpression.
    """
    return QueryExpression(
        dialect,
        select=[Literal(dialect, 1)],
        where=WhereClause(
            dialect,
            condition=Column(dialect, "total") > Literal(dialect, threshold),
        ),
    )
