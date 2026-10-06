# src/rhosocial/activerecord/backend/expression/objects/routine.py
"""
Routines -- functions and procedures.

Function and procedure are peers, not parent and child: the difference is
what the engine lets you do with the result, not how the object is named or
where it lives. Both are called, never selected from.

A function *may* additionally be readable as a table, but only when it
returns a set -- and that is a property of the function's return type, not
of its identity. It is expressed where the query is built (see
:mod:`..sources`), not by making the object a source.
"""

from .base import SchemaObject

__all__ = ["RoutineObject", "Function", "Procedure"]


class RoutineObject(SchemaObject):
    """Base of the callable objects.

    Parameters, body, language, volatility and return type describe *how* the
    routine behaves; none of them is part of where it lives, so this class
    adds no slots for them. It declares no ``format_method``: being callable
    does not say how the routine is spelled, so each peer declares its own.
    """


class Function(RoutineObject):
    """A function, invoked for a value."""

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this function."""
        return "format_function_object"


class Procedure(RoutineObject):
    """A procedure, invoked for its effects."""

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this procedure."""
        return "format_procedure_object"