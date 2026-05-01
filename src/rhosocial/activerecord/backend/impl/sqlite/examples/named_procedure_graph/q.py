# src/rhosocial/activerecord/backend/impl/sqlite/examples/named_procedure_graph/q.py
"""Named queries supporting monthly_report_graph.

These queries are used by the ProcedureGraph examples.
Each function takes 'dialect' as first parameter and returns
a BaseExpression that implements Executable.
"""
from rhosocial.activerecord.backend.expression import (
    Select,
    Insert,
    From,
    Column,
    Where,
    GroupBy,
    Having,
    OrderBy,
    Func,
    LiteralValue,
)


def agg_sales(dialect, month: str = ""):
    """Aggregate sales for a given month.

    Args:
        dialect: SQL dialect instance.
        month: Month in YYYY-MM format.

    Returns:
        Select expression.
    """
    return (
        Select(
            func=Func("SUM", Column("amount")).as_("total"),
            func=Func("COUNT", Column("id")).as_("count"),
        )
        .from_(From(table="sales"))
        .where(Where(Column("month") == LiteralValue(month)))
    )


def agg_refunds(dialect, month: str = ""):
    """Aggregate refunds for a given month.

    Args:
        dialect: SQL dialect instance.
        month: Month in YYYY-MM format.

    Returns:
        Select expression.
    """
    return (
        Select(
            func=Func("SUM", Column("amount")).as_("total"),
            func=Func("COUNT", Column("id")).as_("count"),
        )
        .from_(From(table="refunds"))
        .where(Where(Column("month") == LiteralValue(month)))
    )


def join_sales_refunds(dialect):
    """Join sales and refunds data.

    Args:
        dialect: SQL dialect instance.

    Returns:
        Select expression joining sales and refunds.
    """
    return (
        Select(
            Column("s.month"),
            func=Func("SUM", Column("s.amount")).as_("sales_total"),
            func=Func("SUM", Column("r.amount")).as_("refunds_total"),
        )
        .from_(From(table="sales").join("refunds", on="s.id = r.sales_id"))
        .group_by(GroupBy("s.month"))
        .order_by(OrderBy("s.month"))
    )


def write_summary(dialect, month: str = ""):
    """Write summary to report table.

    Args:
        dialect: SQL dialect instance.
        month: Month in YYYY-MM format.

    Returns:
        Insert expression.
    """
    return (
        Insert(
            into="monthly_reports",
            columns=["month", "created_at"],
            values=[LiteralValue(month), Func("CURRENT_TIMESTAMP")],
        )
    )


def check_threshold(dialect, threshold: int = 1000):
    """Check if threshold is met.

    Args:
        dialect: SQL dialect instance.
        threshold: Threshold value.

    Returns:
        Select expression.
    """
    return (
        Select(LiteralValue(1))
        .where(Where(Column("total") > LiteralValue(threshold)))
    )