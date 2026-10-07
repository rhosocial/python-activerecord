# src/rhosocial/activerecord/backend/expression/objects/trigger.py
"""
Triggers -- event definitions attached to a target.

A trigger is persistent and named, but it is not a reference: there is no
``FROM my_trigger``, and its name is scoped by the object it hangs off rather
than by the schema alone. PostgreSQL makes this concrete by requiring a
trigger's name to be unique per target table, not per schema.

The target, the events, the timing, the level and the action all describe
the trigger's behaviour rather than where it lives, so the identity slots
are all this class carries.
"""

from .base import SchemaObject

__all__ = ["Trigger"]


class Trigger(SchemaObject):
    """A trigger."""

    @property
    def format_method(self) -> str:
        """The dialect formatting method that renders this trigger."""
        return "format_trigger_object"