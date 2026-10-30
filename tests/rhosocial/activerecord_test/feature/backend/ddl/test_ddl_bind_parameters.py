# tests/rhosocial/activerecord_test/feature/backend/ddl/test_ddl_bind_parameters.py
"""A DDL statement's body carries no bind parameters unless the dialect says so.

Three statements have a *query* as their body -- ``CREATE TABLE ... AS``,
``CREATE VIEW`` and ``CREATE MATERIALIZED VIEW`` -- and a query may carry
bind parameters. Whether the engine accepts them is the dialect's question,
and the answer differs by engine and by statement:

* the body of a CTAS is executed once, so a bind is meaningful where the
  engine takes one;
* the body of a view or a materialized view is *stored and run again later*,
  where a bind has no meaning -- PostgreSQL refuses both in its own words;
* Oracle's DDL statements never take bind variables at all, and the driver
  rejects the statement before the server sees it;
* MySQL's, MariaDB's and ClickHouse's "parameters" are interpolated
  client-side, so the value is baked into the stored text.

So the question is asked per dialect, and the answer is a probe:
``supports_create_table_as_bind_parameters``,
``supports_create_view_bind_parameters`` and
``supports_materialized_view_bind_parameters``. The default is ``False`` --
a DDL statement carries no bind parameters unless the dialect says it can,
which is the same rule the DEFAULT and ALTER COLUMN paths already enforce.

The rule these cases pin is that the probe is **load-bearing**: flip it and
the outcome flips with it. A probe that is only declared, and never
consulted, would let every dialect emit a statement its engine refuses.
"""

import pytest

from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.expression import (
    Column,
    CreateMaterializedViewStatement,
    CreateTableAsStatement,
    CreateViewStatement,
    Literal,
    QueryStatement,
)
from rhosocial.activerecord.backend.expression.objects import MaterializedView, Table, View
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect

#: The three statements whose body is a query, and the probe that answers
#: for each. The builders are called with a dialect and a query.
STATEMENTS = {
    "create_table_as": (
        "supports_create_table_as_bind_parameters",
        lambda d, q: CreateTableAsStatement(d, Table(d, "t"), q),
    ),
    "create_view": (
        "supports_create_view_bind_parameters",
        lambda d, q: CreateViewStatement(d, View(d, "v"), q),
    ),
    "create_materialized_view": (
        "supports_materialized_view_bind_parameters",
        lambda d, q: CreateMaterializedViewStatement(d, MaterializedView(d, "mv"), q),
    ),
}


def _dialect():
    return DummyDialect()


def _query(dialect, inline):
    return QueryStatement(
        dialect=dialect,
        select=[Literal(dialect, 1, inline=inline)],
        from_=Table(dialect, "src"),
    )


def _flipped(probe_name):
    """A dialect with exactly one probe flipped."""
    stock = getattr(_dialect(), probe_name)()
    return type(
        f"Flipped_{probe_name}",
        (DummyDialect,),
        {probe_name: lambda self: not stock},
    )()


@pytest.mark.parametrize("label", sorted(STATEMENTS))
class TestTheProbeIsLoadBearing:
    """Flipping the probe must change the statement's fate."""

    def test_the_stock_dialect_carries_the_bind(self, label):
        probe_name, build = STATEMENTS[label]
        dialect = _dialect()
        assert getattr(dialect, probe_name)() is True
        sql, params = build(dialect, _query(dialect, inline=False)).to_sql()
        assert params == (1,)
        assert "?" in sql or "%s" in sql, sql

    def test_a_flipped_probe_refuses_by_name(self, label):
        probe_name, build = STATEMENTS[label]
        dialect = _flipped(probe_name)
        with pytest.raises(UnsupportedFeatureError) as excinfo:
            build(dialect, _query(dialect, inline=False)).to_sql()
        message = str(excinfo.value)
        assert "bound parameters" in message, message
        assert "inlined literal" in message, message

    def test_an_inlined_body_renders_under_either_answer(self, label):
        """The way out is the same under both answers: inline the value."""
        probe_name, build = STATEMENTS[label]
        for dialect in (_dialect(), _flipped(probe_name)):
            sql, params = build(dialect, _query(dialect, inline=True)).to_sql()
            assert params == ()
            assert "1" in sql, sql

    def test_a_query_without_a_literal_is_never_refused(self, label):
        """The check is about bind parameters, not about queries."""
        _probe_name, build = STATEMENTS[label]
        dialect = _flipped(STATEMENTS[label][0])
        query = QueryStatement(
            dialect=dialect,
            select=[Column(dialect, "id")],
            from_=Table(dialect, "src"),
        )
        sql, params = build(dialect, query).to_sql()
        assert params == ()
