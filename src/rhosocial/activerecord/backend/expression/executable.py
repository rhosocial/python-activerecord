# src/rhosocial/activerecord/backend/expression/executable.py
"""
Executable protocol for expression validation.

This module defines the Executable protocol which expressions must implement
to be considered valid for named-query execution.
"""
from typing import Protocol, runtime_checkable

from rhosocial.activerecord.backend.schema import StatementType


@runtime_checkable
class Executable(Protocol):
    """Executable protocol - defines the interface for expressions that can be executed.

    Expressions implementing this protocol must provide a statement_type property
    that indicates what kind of SQL statement they represent.

    Usage:
        from rhosocial.activerecord.backend.expression.executable import Executable
        from rhosocial.activerecord.backend.expression.statements.dql import QueryExpression

        if isinstance(my_expression, Executable):
            stmt_type = my_expression.statement_type
    """

    @property
    def statement_type(self) -> StatementType:  # pragma: no cover
        """Return the statement type for this expression.

        Returns:
            StatementType: The type of SQL statement (DQL, DML, DDL, EXPLAIN, etc.)
        """
        ...