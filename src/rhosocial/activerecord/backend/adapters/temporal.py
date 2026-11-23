# src/rhosocial/activerecord/backend/adapters/temporal.py
"""Neutral, timezone-aware datetime type for fields that store an instant.

A bare Python ``datetime`` cannot say whether it is a wall-clock reading or a
point in time: awareness lives on the value (``tzinfo``), not on the type. The
suggestion tables therefore answer a bare ``datetime`` with a naive timestamp.
``AwareDatetime`` is the explicit counterpart -- a field annotated with it
declares "this column stores an instant", so the backend suggests a
timezone-aware declaration (``TIMESTAMPTZ`` where the backend has one).
"""
import datetime
from typing import Any

from pydantic import GetCoreSchemaHandler
from pydantic_core import core_schema


class AwareDatetime(datetime.datetime):
    """A ``datetime`` field that stores an instant (timezone-aware).

    This is a real ``datetime.datetime`` subclass, not an ``Annotated`` alias:
    the DDL derivation peels ``Annotated`` metadata, so the declaration must
    survive as the field's Python type to reach the suggestion table.

    Pydantic 2 cannot build a schema for a bare ``datetime`` subclass, so this
    type supplies its own core schema. Validation delegates to ``datetime`` and
    then attaches UTC to any naive value -- an aware value keeps the offset it
    arrived with. A plain ``datetime`` input resolves to the base class, but the
    value is always aware; DDL derivation and adapter selection read the field's
    annotation type, so the runtime class is not load-bearing.

    Example::

        class Event(ActiveRecord):
            occurred_at: AwareDatetime
    """

    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> core_schema.CoreSchema:
        datetime_schema = handler.generate_schema(datetime.datetime)

        def attach_utc(value: Any) -> Any:
            if isinstance(value, datetime.datetime) and value.tzinfo is None:
                return value.replace(tzinfo=datetime.timezone.utc)
            return value

        return core_schema.no_info_after_validator_function(
            attach_utc,
            datetime_schema,
        )


class UtcDatetime(AwareDatetime):
    """An :class:`AwareDatetime` pinned to UTC.

    Semantically identical to its parent (the value's ``tzinfo`` still decides
    the offset); provided as a named alias for models that want to state the UTC
    contract explicitly in the annotation.
    """


__all__ = ["AwareDatetime", "UtcDatetime"]
