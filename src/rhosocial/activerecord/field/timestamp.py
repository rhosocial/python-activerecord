# src/rhosocial/activerecord/field/timestamp.py
"""Module providing timestamp functionality.

Three classes, per "who defines the column, who declares it":

* :class:`TimestampMixin` — **maintenance semantics only**.  Declares no
  fields.  Point it at the model's declared timestamp fields via
  ``__created_at_field__`` / ``__updated_at_field__`` (both required).
* :class:`DefaultTimestampMixin` — adds the conventional
  ``created_at`` / ``updated_at`` fields for the common case.
* :class:`UtcTimestampMixin` — optional validation: a naive ``datetime``
  assigned to any field is read as UTC, so it compares with the aware values
  the library generates.

All timestamps are generated in Python (UTC) for consistency across
database backends.
"""

from datetime import datetime, timezone
from typing import Any, Dict, Union

try:
    from typing import Annotated
except ImportError:  # Python 3.8
    from typing_extensions import Annotated

from pydantic import Field, field_validator

from ..base.fields import UseSqlType
from ..backend.expression.types import TimestampType
from ..interface import ModelEvent
from ..interface.update import IUpdateBehavior
from ..interface.model import IActiveRecord, IAsyncActiveRecord
from .field_config import FieldConfigValidationHandler


class TimestampMixin(IUpdateBehavior):
    """Timestamp *maintenance semantics* — declares no fields.

    The model (or a subclass like :class:`DefaultTimestampMixin`) declares
    two datetime fields; the defaults are the conventional ``created_at``
    and ``updated_at``, and a model with other names overrides
    :meth:`created_at_field` / :meth:`updated_at_field`. An overriding
    answer that names no field fails at class definition.
    """

    _feature_handlers = [FieldConfigValidationHandler]

    def __init__(self, **data):
        super().__init__(**data)
        # Use separate events for INSERT and UPDATE operations
        self.on(ModelEvent.BEFORE_INSERT, self._set_timestamps_on_insert)
        self.on(ModelEvent.BEFORE_UPDATE, self._set_updated_at)

    @classmethod
    def created_at_field(cls) -> str:
        """The created-at field -- declared by overriding this method."""
        return "created_at"

    @classmethod
    def updated_at_field(cls) -> str:
        """The updated-at field -- declared by overriding this method."""
        return "updated_at"

    @classmethod
    def _validate_model_config(cls) -> None:
        """Fail fast when the configured field names do not exist.

        Invoked by :class:`FieldConfigValidationHandler` from the metaclass,
        so it runs once at class definition — see that module for why this
        cannot live in ``__init__``.
        """
        for knob, field_name in (
            ("created_at_field()", cls.created_at_field()),
            ("updated_at_field()", cls.updated_at_field()),
        ):
            if field_name not in cls.model_fields:
                raise TypeError(
                    f"{cls.__name__}: {knob} = {field_name!r} does not name a "
                    f"model field. Declare the timestamp fields (e.g. "
                    f"`{field_name}: datetime = Field(default_factory=...)`) "
                    f"or use DefaultTimestampMixin."
                )

    def _set_timestamps_on_insert(
        self, instance: Union["IActiveRecord", "IAsyncActiveRecord"], data: Dict[str, Any] = None, **kwargs
    ) -> None:
        """Set both configured timestamp fields for INSERT operations.

        Both timestamps are set to the same UTC value to ensure consistency.
        """
        now = datetime.now(timezone.utc)
        for field_name in (self.created_at_field(), self.updated_at_field()):
            setattr(instance, field_name, now)
            if data is not None:
                data[field_name] = now

    def _set_updated_at(
        self, instance: Union["IActiveRecord", "IAsyncActiveRecord"], data: Dict[str, Any] = None, **kwargs
    ) -> None:
        """Set the configured updated-at field for UPDATE operations."""
        now = datetime.now(timezone.utc)
        field_name = self.updated_at_field()
        setattr(instance, field_name, now)
        if data is not None:
            data[field_name] = now

    def get_update_conditions(self):
        """No additional WHERE conditions are needed during updates."""
        return []

    def get_update_expressions(self) -> Dict[str, Any]:
        """The updated-at field value is set by ``_set_updated_at``."""
        return {}


class DefaultTimestampMixin(TimestampMixin):
    """Timestamp semantics with the conventional fields declared.

    Adds ``created_at`` / ``updated_at`` (``datetime``, UTC default
    factory) so models can simply mix it in.  Use
    :class:`TimestampMixin` directly when the fields should carry
    different Python names or columns.
    """

    created_at: Annotated[datetime, UseSqlType(TimestampType())] = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    updated_at: Annotated[datetime, UseSqlType(TimestampType())] = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class UtcTimestampMixin:
    """Read every naive ``datetime`` as UTC.

    The library generates timestamps with ``datetime.now(timezone.utc)``,
    but a caller may assign ``datetime.now()`` (naive) or a database driver
    may return a naive value.  Comparing a naive value with an aware one
    raises ``TypeError`` far from the assignment that caused it.  Mix this in
    to attach UTC to naive datetimes while leaving non-datetime fields and
    aware values untouched -- an aware value keeps the offset it arrived with.

    Two validators are needed because input reaches a field in two shapes:
    an already-built ``datetime`` is seen by the ``before`` validator, while a
    string or number is parsed by Pydantic *after* that one and is normalized
    by the ``after`` validator.

    This is optional: models that never compare or mix caller-supplied and
    library-generated timestamps do not need it.

    Example:
        >>> class Event(UtcTimestampMixin, DefaultTimestampMixin, ActiveRecord):
        ...     __table_name__ = "events"
        ...     id: Optional[int] = None
        ...     name: str
        ...     occurred_at: datetime
        ...
        >>> event = Event(name="deploy", occurred_at=datetime(2026, 1, 1, 12))
        >>> event.occurred_at.tzinfo is timezone.utc
        True
    """

    @staticmethod
    def _as_utc(value: Any) -> Any:
        """Attach UTC to a naive datetime; leave every other value untouched."""
        if isinstance(value, datetime) and value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value

    @field_validator("*", mode="before")
    @classmethod
    def _naive_datetime_before(cls, value: Any) -> Any:
        return cls._as_utc(value)

    @field_validator("*", mode="after")
    @classmethod
    def _naive_datetime_after(cls, value: Any) -> Any:
        return cls._as_utc(value)
