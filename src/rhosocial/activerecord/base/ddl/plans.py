# src/rhosocial/activerecord/base/ddl/plans.py
"""Typed DDL plans (creation / teardown).

A plan is an **ordered sequence of DDL statements** — e.g. a creation plan
(``CREATE TABLE`` plus any standalone ``CREATE INDEX`` the dialect requires)
or a teardown plan (``DROP INDEX`` statements first, ``DROP TABLE`` last).
Typing the plan (instead of returning a bare ``list``) keeps the abstraction
level uniform: single statements are expressions, plans are :class:`DDLPlan`.
"""

from __future__ import annotations

from typing import Any, Iterator, List

from ...backend.expression.bases import BaseExpression

__all__ = ["DDLPlan"]


class DDLPlan:
    """A typed, ordered sequence of DDL statements."""

    def __init__(self, statements: List[BaseExpression]):
        self.statements: List[BaseExpression] = list(statements)

    def __iter__(self) -> Iterator[BaseExpression]:
        return iter(self.statements)

    def __len__(self) -> int:
        return len(self.statements)

    def __getitem__(self, index: int) -> BaseExpression:
        return self.statements[index]

    def __repr__(self) -> str:
        names = ", ".join(type(statement).__name__ for statement in self.statements)
        return f"DDLPlan([{names}])"

    def to_sql(self) -> List[Any]:
        """Render every statement; DDL accepts no bind parameters, so each
        entry is a ``(sql, params)`` tuple with empty params."""
        return [statement.to_sql() for statement in self.statements]
