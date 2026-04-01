# src/rhosocial/activerecord/backend/impl/sqlite/explain/types.py
"""
SQLite-specific EXPLAIN result types.

SQLite has two EXPLAIN modes with completely different output schemas:

1. ``EXPLAIN <stmt>``
   Returns the bytecode program SQLite uses to execute the statement.
   Columns: addr, opcode, p1, p2, p3, p4, p5, comment

2. ``EXPLAIN QUERY PLAN <stmt>``
   Returns a human-readable description of the query strategy.
   Columns: id, parent, notused, detail
"""

from typing import List, Literal, Optional

from pydantic import BaseModel

from rhosocial.activerecord.backend.explain.types import BaseExplainResult

# Index usage pattern labels shared by both result types.
IndexUsage = Literal["full_scan", "index_with_lookup", "covering_index", "unknown"]

# Bytecode opcodes that indicate an index seek (range or equality navigation).
_SEEK_OPCODES = frozenset(
    {"SeekGE", "SeekGT", "SeekLE", "SeekLT", "SeekEQ", "SeekRowid", "NotFound"}
)


class SQLiteExplainRow(BaseModel):
    """One row from ``EXPLAIN <stmt>`` (SQLite bytecode output).

    Attributes:
        addr:    Program counter address of the opcode.
        opcode:  Name of the virtual machine instruction.
        p1:      First operand.
        p2:      Second operand.
        p3:      Third operand.
        p4:      Optional string or blob operand (None when unused).
        p5:      Flags operand (integer bitmask).
        comment: Human-readable annotation (None when absent).
    """

    addr: int
    opcode: str
    p1: int
    p2: int
    p3: int
    p4: Optional[str]
    p5: int
    comment: Optional[str]


class SQLiteExplainQueryPlanRow(BaseModel):
    """One row from ``EXPLAIN QUERY PLAN <stmt>``.

    Attributes:
        id:      Row identifier (used to build the tree structure).
        parent:  ``id`` of the parent row (0 means top-level).
        notused: Reserved / unused field (always 0 in current SQLite).
        detail:  Human-readable description of the query step.
    """

    id: int
    parent: int
    notused: int
    detail: str


class SQLiteExplainResult(BaseExplainResult):
    """Result of ``EXPLAIN <stmt>`` against a SQLite backend.

    Attributes:
        rows: Typed list of SQLite bytecode rows.

    Index-usage analysis
    --------------------
    Three patterns can be identified from the VDBE bytecode:

    * **full_scan** – Single ``OpenRead`` cursor on the main table, no
      seek opcode.  Every row is visited linearly.

    * **index_with_lookup** – Two ``OpenRead`` cursors (table + index),
      at least one seek opcode.  The index narrows the candidate set, but
      the engine still jumps back to the main table to fetch non-index
      columns (``DeferredSeek`` / ``IdxRowid``).

    * **covering_index** – Single ``OpenRead`` cursor pointing to an
      index (not the main table), plus at least one seek opcode.  All
      required columns are read directly from the index; the main table
      is never opened.

    * **unknown** – Pattern not recognised (e.g. complex multi-table
      query, sub-query, or a future SQLite version uses different
      opcodes).
    """

    rows: List[SQLiteExplainRow]

    def analyze_index_usage(self) -> IndexUsage:
        """Return the index-usage pattern inferred from the bytecode.

        Returns:
            One of ``"full_scan"``, ``"index_with_lookup"``,
            ``"covering_index"``, or ``"unknown"``.
        """
        open_reads = [r for r in self.rows if r.opcode == "OpenRead"]
        has_seek = any(r.opcode in _SEEK_OPCODES for r in self.rows)

        if not has_seek:
            return "full_scan"

        if len(open_reads) == 1:
            return "covering_index"

        if len(open_reads) >= 2:
            return "index_with_lookup"

        return "unknown"

    @property
    def is_full_scan(self) -> bool:
        """True when the query performs a full table scan (no index used)."""
        return self.analyze_index_usage() == "full_scan"

    @property
    def is_index_used(self) -> bool:
        """True when at least one index is used (covering or with lookup)."""
        return self.analyze_index_usage() in ("index_with_lookup", "covering_index")

    @property
    def is_covering_index(self) -> bool:
        """True when a covering index satisfies the query without table access."""
        return self.analyze_index_usage() == "covering_index"


class SQLiteExplainQueryPlanResult(BaseExplainResult):
    """Result of ``EXPLAIN QUERY PLAN <stmt>`` against a SQLite backend.

    Attributes:
        rows: Typed list of query-plan rows.

    Index-usage analysis
    --------------------
    Three patterns are identified from the ``detail`` text emitted by
    SQLite:

    * **covering_index** – detail contains ``USING COVERING INDEX``.
    * **index_with_lookup** – detail contains ``SEARCH … USING INDEX``
      (or ``USING INTEGER PRIMARY KEY``).
    * **full_scan** – detail contains ``SCAN`` but none of the above.
    * **unknown** – none of the above keywords found.
    """

    rows: List[SQLiteExplainQueryPlanRow]

    def analyze_index_usage(self) -> IndexUsage:
        """Return the index-usage pattern inferred from the query-plan text.

        Returns:
            One of ``"full_scan"``, ``"index_with_lookup"``,
            ``"covering_index"``, or ``"unknown"``.
        """
        combined = " ".join(r.detail.upper() for r in self.rows)

        if "COVERING INDEX" in combined:
            return "covering_index"

        if "SEARCH" in combined and "USING" in combined:
            return "index_with_lookup"

        if "SCAN" in combined:
            return "full_scan"

        return "unknown"

    @property
    def is_full_scan(self) -> bool:
        """True when the query plan shows a full table scan."""
        return self.analyze_index_usage() == "full_scan"

    @property
    def is_index_used(self) -> bool:
        """True when the query plan uses at least one index."""
        return self.analyze_index_usage() in ("index_with_lookup", "covering_index")

    @property
    def is_covering_index(self) -> bool:
        """True when the query plan uses a covering index."""
        return self.analyze_index_usage() == "covering_index"
