# src/rhosocial/activerecord/field/soft_delete.py
"""Module providing soft delete functionality.

Two classes, per "who defines the column, who declares it":

* :class:`SoftDeleteMixin` — **semantics only** (mark / filter / restore).
  Declares no field; point it at the model's declared datetime field via
  ``__deleted_at_field__``.
* :class:`DefaultSoftDeleteMixin` — adds the conventional
  ``deleted_at: Optional[datetime]`` field.
* :class:`AsyncSoftDeleteMixin` / :class:`DefaultAsyncSoftDeleteMixin` —
  async ``restore`` counterparts of the above.

For async models use the ``Async*`` variants, which keep sync/async on
equal footing without mixing execution models.
"""

from datetime import datetime, timezone
from typing import ClassVar, Dict, Any, Optional

from pydantic import Field

from ..backend.expression.core import Column
from ..backend.expression import ComparisonPredicate, Literal
from ..interface import ModelEvent
from ..interface.update import IDeleteBehavior
from ..query import ActiveQuery


class SoftDeleteMixin(IDeleteBehavior):
    """Soft-delete *semantics* — declares no field.

    The model (or a subclass like :class:`DefaultSoftDeleteMixin`) declares
    a datetime field and announces it via ``__deleted_at_field__``; it must
    exist or instantiation fails fast.
    """

    __deleted_at_field__: ClassVar[str] = "deleted_at"

    def __init__(self, **data):
        super().__init__(**data)
        self.__class__._validate_soft_delete_config()
        self.on(ModelEvent.BEFORE_DELETE, self._mark_as_deleted)

    @classmethod
    def _validate_soft_delete_config(cls) -> None:
        """Fail fast when the configured field name does not exist."""
        field_name = cls.__deleted_at_field__
        if field_name not in cls.model_fields:
            raise TypeError(
                f"{cls.__name__}: __deleted_at_field__ = {field_name!r} does "
                f"not name a model field. Declare the soft-delete field (e.g. "
                f"`{field_name}: Optional[datetime] = Field(default=None)`) or "
                f"use DefaultSoftDeleteMixin."
            )

    @classmethod
    def _deleted_at_column(cls) -> str:
        """The database column name for the soft-delete field (UseColumn-aware)."""
        return cls._get_column_name(cls.__deleted_at_field__)

    def _mark_as_deleted(self, instance: "SoftDeleteMixin", **kwargs):
        """Mark record as soft deleted by setting the configured field."""
        setattr(instance, self.__deleted_at_field__, datetime.now(timezone.utc))

    def prepare_delete(self) -> Dict[str, Any]:
        """Prepare soft delete data (field name as key; mapped downstream)."""
        field_name = self.__deleted_at_field__
        value = getattr(self, field_name)
        if value is None:
            raise ValueError(
                f"{field_name} not set, ensure BEFORE_DELETE event is triggered"
            )
        return {field_name: value}

    @classmethod
    def query(cls) -> "ActiveQuery":
        """Return query builder excluding soft-deleted records."""
        backend = cls.backend()
        non_deleted_condition = Column(backend.dialect, cls._deleted_at_column()).is_null()
        return super().query().where(non_deleted_condition)

    @classmethod
    def query_with_deleted(cls) -> "ActiveQuery":
        """Return query including all records (no soft delete filter)."""
        return super().query()

    @classmethod
    def query_only_deleted(cls) -> "ActiveQuery":
        """Return query for only soft-deleted records."""
        backend = cls.backend()
        deleted_condition = Column(backend.dialect, cls._deleted_at_column()).is_not_null()
        return super().query().where(deleted_condition)

    def _build_restore_condition(self):
        """Build the WHERE predicate identifying the record to restore.

        Pure computation shared by sync ``restore`` and async
        :meth:`AsyncSoftDeleteMixin.restore`; no I/O is performed here so the
        two execution models never mix.
        """
        backend = self.backend()
        dialect = backend.dialect

        if self.is_composite_pk():
            pk_cols = self.primary_key_columns()
            condition_expr = None
            for col in pk_cols:
                pk_value = getattr(self, self._get_field_name(col))
                if pk_value is not None:
                    col_expr = Column(dialect, col)
                    pred = ComparisonPredicate(dialect, "=", col_expr, Literal(dialect, pk_value))
                    condition_expr = pred if condition_expr is None else condition_expr & pred
        else:
            pk_column = Column(dialect, self.primary_key())
            pk_value = getattr(self, self.primary_key())
            condition_expr = pk_column == pk_value

        return condition_expr

    def restore(self) -> int:
        """Restore a soft-deleted record using expression system."""
        field_name = self.__deleted_at_field__
        if getattr(self, field_name) is None:
            return 0

        from ..backend.options import UpdateOptions

        condition_expr = self._build_restore_condition()
        update_options = UpdateOptions(
            table=self.table_name(),
            data={self._deleted_at_column(): None},
            where=condition_expr,
        )

        result = self.backend().update(update_options)

        if result.affected_rows > 0:
            setattr(self, field_name, None)
            self.reset_tracking()

        return result.affected_rows


class AsyncSoftDeleteMixin(SoftDeleteMixin):
    """Async counterpart of :class:`SoftDeleteMixin`.

    Inherits the semantics (knob, event registration, query classmethods,
    ``prepare_delete``) from :class:`SoftDeleteMixin` and declares no field;
    only :meth:`restore` is overridden to ``await`` the backend I/O.
    """

    async def restore(self) -> int:
        """Restore a soft-deleted record asynchronously using expression system."""
        field_name = self.__deleted_at_field__
        if getattr(self, field_name) is None:
            return 0

        from ..backend.options import UpdateOptions

        condition_expr = self._build_restore_condition()
        update_options = UpdateOptions(
            table=self.table_name(),
            data={self._deleted_at_column(): None},
            where=condition_expr,
        )

        result = await self.backend().update(update_options)

        if result.affected_rows > 0:
            setattr(self, field_name, None)
            self.reset_tracking()

        return result.affected_rows


class DefaultSoftDeleteMixin(SoftDeleteMixin):
    """Soft-delete semantics with the conventional field declared.

    Adds ``deleted_at: Optional[datetime]`` (default ``None``) so models can
    simply mix it in.  Use :class:`SoftDeleteMixin` directly when the field
    should carry a different Python name or column.
    """

    deleted_at: Optional[datetime] = Field(default=None)


class DefaultAsyncSoftDeleteMixin(AsyncSoftDeleteMixin):
    """Async soft-delete semantics with the conventional field declared."""

    deleted_at: Optional[datetime] = Field(default=None)
