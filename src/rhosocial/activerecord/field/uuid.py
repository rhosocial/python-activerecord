# src/rhosocial/activerecord/field/uuid.py
"""Module providing UUID functionality."""

import sys
import uuid
from typing import Any, Dict
from pydantic import Field

from ..interface.update import IDataPreparationBehavior


class UUIDMixin(IDataPreparationBehavior):
    """Adds UUID primary key support.

    Automatically generates UUIDs for new records.

    Generation happens in Python, not in the database. That is deliberate: it
    keeps the value available before the INSERT is built, so a model can use
    its own primary key in the same transaction without a round trip, and it
    works unchanged on backends with no UUID function (SQLite has none). A
    model that would rather let the database generate the value can render
    :class:`~...expression.uuid.UUIDGenerationExpression` into a column default
    instead — the two approaches are independent.

    The field is annotated ``uuid.UUID`` and left to normal type inference for
    its column type; see :class:`~...expression.types.UUIDType` for how a
    backend declares explicit UUID storage instead.
    """

    id: uuid.UUID = Field(default_factory=uuid.uuid4)

    @classmethod
    def uuid_version(cls) -> str:
        """Which UUID variant new keys use -- ``"uuid4"`` unless overridden.

        Declared by overriding this method. ``"uuid7"`` selects the
        time-ordered variant from RFC 9562, whose leading timestamp makes
        index inserts append rather than scatter: the right choice for a
        key that is also the physical ordering of a B-tree. ``uuid4`` is
        the default because it needs no runtime support beyond Python
        itself.
        """
        return "uuid4"

    @classmethod
    def _generate_uuid(cls) -> uuid.UUID:
        """A new primary key, in the variant :meth:`uuid_version` selects.

        ``uuid7`` is probed for rather than imported: the stdlib gained it
        in Python 3.14, and this package supports 3.8 onwards, so a model
        selecting it on an older interpreter gets a message saying what is
        missing instead of an ``ImportError`` from a module import.
        """
        version = cls.uuid_version()
        if version == "uuid4":
            return uuid.uuid4()
        if version == "uuid7":
            generator = getattr(uuid, "uuid7", None)
            if generator is None:
                raise RuntimeError(
                    f"{cls.__name__} selects uuid7(), which this interpreter "
                    f"does not provide: the standard library gained it in "
                    f"Python 3.14 (RFC 9562), and the running version is "
                    f"{'.'.join(str(part) for part in sys.version_info[:3])}. "
                    f"Declare uuid_version() as 'uuid4' on this interpreter, "
                    f"or upgrade it."
                )
            return generator()
        raise ValueError(
            f"{cls.__name__}.uuid_version() returned {version!r}; the supported "
            f"variants are 'uuid4' and 'uuid7'."
        )

    def __init__(self, **data):
        pk_field = self.primary_key()
        if pk_field not in data:
            data[pk_field] = self._generate_uuid()
        super().__init__(**data)

    def prepare_save_data(self, data: Dict[str, Any], is_new: bool) -> Dict[str, Any]:
        """Prepare save data ensuring proper UUID handling

        Args:
            data: Current prepared data
            is_new: Whether this is a new record

        Returns:
            Dict[str, Any]: Processed data
        """
        pk_field = self.primary_key()

        if is_new and not getattr(self, pk_field, None):
            uuid_value = self._generate_uuid()
            setattr(self, pk_field, uuid_value)
            data[pk_field] = uuid_value
        elif pk_field not in data and getattr(self, pk_field, None):
            data[pk_field] = getattr(self, pk_field)

        parent_prepare = super().prepare_save_data if hasattr(super(), "prepare_save_data") else None
        if parent_prepare:
            data = parent_prepare(data, is_new)

        return data
