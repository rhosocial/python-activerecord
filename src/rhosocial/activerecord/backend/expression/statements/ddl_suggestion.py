# src/rhosocial/activerecord/backend/expression/statements/ddl_suggestion.py
"""Backend *suggestion* data classes for DDL.

A suggestion is the backend's answer to "how should this be declared here".
It is not an expression node and not a statement: it is a small, immutable
value the framework reads and turns into DDL. The name carries ``Suggestion``
(not ``Column``) to mark it as a backend-suggested value -- the same family as
``suggested_data_types()`` / ``suggested_column_types()``.

No primary key here. Primary-key-ness is declared by the model
(``__primary_key__`` / ``IntegerPKMixin``) and rendered as an independent
column constraint; a suggestion only answers the storage question it is
named for. That is what keeps "auto-increment but not a primary key" possible.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Union

if TYPE_CHECKING:  # pragma: no cover
    from ..bases import BaseExpression
    from ..types._base import DataType


@dataclass(frozen=True)
class IntegerAutoIncrementColumnSuggestion:
    """A backend's suggested DDL for an integer auto-increment column.

    Attributes:
        type: The storage type expression (``IntegerType``, a backend's own
            integer subclass, or a pseudo-type such as PostgreSQL's SERIAL).
        auto_increment: How the value is generated on INSERT:
            - an expression node (``AutoIncrementClause`` / ``IdentityClause``)
              naming the mechanism the dialect renders;
            - ``False``: the type already absorbs the attribute and **no**
              further auto-increment clause may be added (SERIAL, SQLite where
              the INTEGER rowid carries it);
            - ``None``: no auto-increment (a plain integer type).
    """

    type: "DataType"
    auto_increment: Union["BaseExpression", bool, None] = None
