# src/rhosocial/activerecord/field/timestamp.py
"""Module providing timestamp functionality.

Two classes, per "who defines the column, who declares it":

* :class:`TimestampMixin` — **maintenance semantics only**.  Declares no
  fields.  Point it at the model's declared timestamp fields via
  ``__created_at_field__`` / ``__updated_at_field__`` (both required).
* :class:`DefaultTimestampMixin` — adds the conventional
  ``created_at`` / ``updated_at`` fields for the common case.

All timestamps are generated in Python (UTC) for consistency across
database backends.
"""

from datetime import datetime, timezone
from typing import Any, ClassVar, Dict, Union

from pydantic import Field

from ..interface import ModelEvent
from ..interface.update import IUpdateBehavior
from ..interface.model import IActiveRecord, IAsyncActiveRecord


class TimestampMixin(IUpdateBehavior):
    """Timestamp *maintenance semantics* — declares no fields.

    The model (or a subclass like :class:`DefaultTimestampMixin`) declares
    two datetime fields and announces them via ``__created_at_field__`` /
    ``__updated_at_field__``; both must exist or instantiation fails fast.
    """

    __created_at_field__: ClassVar[str] = "created_at"
    __updated_at_field__: ClassVar[str] = "updated_at"

    def __init__(self, **data):
        super().__init__(**data)
        self.__class__._validate_timestamp_config()
        # Use separate events for INSERT and UPDATE operations
        self.on(ModelEvent.BEFORE_INSERT, self._set_timestamps_on_insert)
        self.on(ModelEvent.BEFORE_UPDATE, self._set_updated_at)

    @classmethod
    def _validate_timestamp_config(cls) -> None:
        """Fail fast when the configured field names do not exist."""
        for knob in ("__created_at_field__", "__updated_at_field__"):
            field_name = getattr(cls, knob)
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
        for knob in ("__created_at_field__", "__updated_at_field__"):
            field_name = getattr(self, knob)
            setattr(instance, field_name, now)
            if data is not None:
                data[field_name] = now

    def _set_updated_at(
        self, instance: Union["IActiveRecord", "IAsyncActiveRecord"], data: Dict[str, Any] = None, **kwargs
    ) -> None:
        """Set the configured updated-at field for UPDATE operations."""
        now = datetime.now(timezone.utc)
        field_name = self.__updated_at_field__
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

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
