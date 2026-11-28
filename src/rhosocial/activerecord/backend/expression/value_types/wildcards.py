# src/rhosocial/activerecord/backend/expression/value_types/wildcards.py
from typing import Optional, TYPE_CHECKING

from ..bases.bases import SQLValue

if TYPE_CHECKING:  # pragma: no cover
    from ...dialect import SQLDialectBase
    from ..sources.relation import NamedRelationRef


class AllColumnsWildcard(SQLValue):
    """Every column of a relation source: the select-list ``*``.

    Its standing is that of a column reference, and its home is the select
    list and the RETURNING clause -- the spec's first wildcard class (4.10.1).
    A bare ``*`` (``relation`` empty) lets the surrounding clause decide what
    "all columns" spans: every FROM source in a select list, the DML target
    in RETURNING. The clause's formatter injects that scope; this node does
    not know where it sits and must not probe.

    A ``relation`` present renders the qualified ``rel.*`` -- the reference
    spelling the query itself uses (the alias when aliased, the qualified
    name otherwise). Row counting is a different contract: the asterisk in
    ``COUNT(*)`` counts rows rather than expanding columns, and belongs to
    :class:`RowCountWildcard` alone.
    """

    @property
    def format_method(self) -> str:
        return "format_all_columns_wildcard"

    def __init__(
        self,
        dialect: "SQLDialectBase",
        relation: Optional["NamedRelationRef"] = None,
    ):
        super().__init__(dialect)
        self.relation = relation


class RowCountWildcard(SQLValue):
    """The asterisk that counts rows: ``COUNT(*)``'s parameter.

    The spec's second wildcard class (4.10.2). Its semantics are rows, not
    column expansion, so it accepts no relation: standard ``COUNT(*)`` takes
    the bare asterisk, and the qualified ``COUNT(t.*)`` is a different
    (non-NULL row count) that supporting backends define as their own derived
    node. The only aggregate whose contract admits this node is ``COUNT``;
    ``SUM``/``AVG``/``MAX``/``MIN`` refuse it where they are built.
    """

    @property
    def format_method(self) -> str:
        return "format_row_count_wildcard"

    def __init__(self, dialect: "SQLDialectBase"):
        super().__init__(dialect)
