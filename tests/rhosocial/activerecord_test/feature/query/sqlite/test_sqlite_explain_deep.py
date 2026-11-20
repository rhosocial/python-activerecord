# tests/rhosocial/activerecord_test/feature/query/sqlite/test_sqlite_explain_deep.py
"""Backend-local, deep EXPLAIN tests for SQLite -- the template for other backends.

The shared testsuite contracts only assert that EXPLAIN *can run*. This file
 interprets what SQLite actually returns, which is deliberately NOT generalized
 into the testsuite because dialects disagree on plan shape:

* ``EXPLAIN QUERY PLAN`` -> rows of ``{id, parent, notused, detail}``; the
  ``detail`` text distinguishes a full ``SCAN`` from an index-backed ``SEARCH``.
* ``EXPLAIN`` (default) -> the VM bytecode rows ``{addr, opcode, p1..p5, ...}``;
  ``Count`` for ``COUNT(*)``, ``SeekRowid`` for an index-backed join, and one
  ``OpenRead`` per scanned table.

SQLite ignores the ``analyze`` / ``format`` options in its renderer; those are
checked here only for "accepted without error", while ``type`` is the option
that actually changes the output form. Other backends should substitute their
own interpretable plan evidence (e.g. Postgres ``Seq Scan`` / ``Index Scan``,
partition-pruning evidence) following the same split.
"""
from typing import Any, Dict, List

import pytest

from rhosocial.activerecord.backend.expression import ExplainType


def _details(plan: List[Dict[str, Any]]) -> List[str]:
    """Extract the human-readable strategy lines from an EXPLAIN QUERY PLAN."""
    return [str(row["detail"]) for row in plan if "detail" in row]


def _opcodes(plan: List[Dict[str, Any]]) -> List[str]:
    """Extract opcodes from SQLite's EXPLAIN bytecode output."""
    return [str(row["opcode"]) for row in plan if "opcode" in row]


@pytest.mark.sqlite
class TestSqliteExplainDeep:
    """Interpret SQLite's EXPLAIN output (synchronous)."""

    def test_query_plan_full_scan(self, order_fixtures):
        """A filter on a non-indexed column plans as a full SCAN."""
        User, _, _ = order_fixtures
        plan = User.query().where(User.c.age > 30).explain(type=ExplainType.QUERY_PLAN).aggregate()
        details = _details(plan)
        assert details, "QUERY PLAN rows must expose a 'detail' column"
        assert any("SCAN" in d for d in details), "expected a SCAN strategy"

    def test_query_plan_pk_lookup(self, order_fixtures):
        """A primary-key predicate plans as an index SEARCH, not a SCAN."""
        User, _, _ = order_fixtures
        plan = User.query().where(User.c.id == 1).explain(type=ExplainType.QUERY_PLAN).aggregate()
        details = _details(plan)
        assert any("SEARCH" in d for d in details), "expected an index SEARCH"
        assert any("INTEGER PRIMARY KEY" in d for d in details), "expected rowid PK access"

    def test_explain_type_option_last_call_wins(self, order_fixtures):
        """A later explain() overrides earlier options (last call wins)."""
        User, _, _ = order_fixtures
        plan = User.query().explain(analyze=True).explain(type=ExplainType.QUERY_PLAN).aggregate()
        # QUERY_PLAN rows have 'detail'; bytecode rows have 'opcode'.
        assert plan and "detail" in plan[0], "last explain(type=QUERY_PLAN) must take effect"
        assert "opcode" not in plan[0]

    def test_explain_analyze_and_format_accepted(self, order_fixtures):
        """Options SQLite ignores (analyze/format) are accepted without error."""
        User, _, _ = order_fixtures
        plan = User.query().explain(analyze=True, format="TEXT").aggregate()
        assert plan and "opcode" in plan[0], "default bytecode plan still returned"

    def test_bytecode_count_uses_count_opcode(self, order_fixtures):
        """COUNT(*) is planned by SQLite's dedicated Count opcode."""
        User, _, _ = order_fixtures
        plan = User.query().explain().count()
        opcodes = _opcodes(plan)
        assert "Count" in opcodes, "expected the Count opcode for COUNT(*)"

    def test_bytecode_join_uses_index_lookup(self, order_fixtures):
        """A PK-foreign-key JOIN reads both tables and seeks via the rowid index."""
        User, Order, _ = order_fixtures
        plan = User.query().join(Order, on=(User.c.id == Order.c.user_id)).explain().aggregate()
        opcodes = _opcodes(plan)
        assert opcodes.count("OpenRead") >= 2, "expected one OpenRead per joined table"
        assert "SeekRowid" in opcodes, "expected an index-backed rowid seek for the join"

    def test_query_plan_join_scans_and_searches(self, order_fixtures):
        """The high-level join plan shows one outer SCAN and one indexed SEARCH."""
        User, Order, _ = order_fixtures
        plan = User.query().join(Order, on=(User.c.id == Order.c.user_id)).explain(
            type=ExplainType.QUERY_PLAN
        ).aggregate()
        details = _details(plan)
        assert any("SCAN" in d for d in details), "expected an outer SCAN"
        assert any("SEARCH" in d for d in details), "expected an indexed inner SEARCH"


@pytest.mark.sqlite
@pytest.mark.asyncio
class TestAsyncSqliteExplainDeep:
    """Interpret SQLite's EXPLAIN output (asynchronous)."""

    async def test_query_plan_full_scan(self, async_order_fixtures):
        """A filter on a non-indexed column plans as a full SCAN."""
        User, _, _ = async_order_fixtures
        plan = await User.query().where(User.c.age > 30).explain(type=ExplainType.QUERY_PLAN).aggregate()
        details = _details(plan)
        assert details, "QUERY PLAN rows must expose a 'detail' column"
        assert any("SCAN" in d for d in details), "expected a SCAN strategy"

    async def test_query_plan_pk_lookup(self, async_order_fixtures):
        """A primary-key predicate plans as an index SEARCH, not a SCAN."""
        User, _, _ = async_order_fixtures
        plan = await User.query().where(User.c.id == 1).explain(type=ExplainType.QUERY_PLAN).aggregate()
        details = _details(plan)
        assert any("SEARCH" in d for d in details), "expected an index SEARCH"
        assert any("INTEGER PRIMARY KEY" in d for d in details), "expected rowid PK access"

    async def test_explain_type_option_last_call_wins(self, async_order_fixtures):
        """A later explain() overrides earlier options (last call wins)."""
        User, _, _ = async_order_fixtures
        plan = await User.query().explain(analyze=True).explain(type=ExplainType.QUERY_PLAN).aggregate()
        # QUERY_PLAN rows have 'detail'; bytecode rows have 'opcode'.
        assert plan and "detail" in plan[0], "last explain(type=QUERY_PLAN) must take effect"
        assert "opcode" not in plan[0]

    async def test_explain_analyze_and_format_accepted(self, async_order_fixtures):
        """Options SQLite ignores (analyze/format) are accepted without error."""
        User, _, _ = async_order_fixtures
        plan = await User.query().explain(analyze=True, format="TEXT").aggregate()
        assert plan and "opcode" in plan[0], "default bytecode plan still returned"

    async def test_bytecode_count_uses_count_opcode(self, async_order_fixtures):
        """COUNT(*) is planned by SQLite's dedicated Count opcode."""
        User, _, _ = async_order_fixtures
        plan = await User.query().explain().count()
        opcodes = _opcodes(plan)
        assert "Count" in opcodes, "expected the Count opcode for COUNT(*)"

    async def test_bytecode_join_uses_index_lookup(self, async_order_fixtures):
        """A PK-foreign-key JOIN reads both tables and seeks via the rowid index."""
        User, Order, _ = async_order_fixtures
        plan = await User.query().join(Order, on=(User.c.id == Order.c.user_id)).explain().aggregate()
        opcodes = _opcodes(plan)
        assert opcodes.count("OpenRead") >= 2, "expected one OpenRead per joined table"
        assert "SeekRowid" in opcodes, "expected an index-backed rowid seek for the join"

    async def test_query_plan_join_scans_and_searches(self, async_order_fixtures):
        """The high-level join plan shows one outer SCAN and one indexed SEARCH."""
        User, Order, _ = async_order_fixtures
        plan = await User.query().join(Order, on=(User.c.id == Order.c.user_id)).explain(
            type=ExplainType.QUERY_PLAN
        ).aggregate()
        details = _details(plan)
        assert any("SCAN" in d for d in details), "expected an outer SCAN"
        assert any("SEARCH" in d for d in details), "expected an indexed inner SEARCH"
