# src/rhosocial/activerecord/field/version.py
"""Module providing optimistic locking functionality.

Two classes, per "who defines the column, who declares it":

* :class:`OptimisticLockMixin` — **lock semantics only**.  Declares no
  field.  Point it at whatever integer field the model declares via
  ``__version_field__`` (and optionally ``__version_increment_by__``).
  The column name follows the standard resolution (UseColumn on the
  declared field); the field name is the model author's choice.
* :class:`DefaultOptimisticLockMixin` — adds the conventional
  ``version: int`` field (``NOT NULL``, ``ge=1``) for the common case.

The column value is *framework-managed*: users must not write it.
Enforcement is layered:

1. INSERT normalises the stored value to 1 regardless of user input.
2. The UPDATE WHERE clause uses ``_version_snapshot`` — the last value
   known to be committed to the database — so in-memory tampering cannot
   break (or bypass) the lock condition.
3. The UPDATE SET clause is a column-arithmetic expression
   (``col = col + step``) which the update pipeline applies *after*
   merging dirty-field data, overriding any user-assigned value.
4. A user-assigned version that differs from the snapshot is rejected
   outright with :class:`DatabaseError` at BEFORE_UPDATE time.

Customisation example::

    class Article(OptimisticLockMixin, ActiveRecord):
        __version_field__ = "row_version"   # the declared field's name
        __version_increment_by__ = 2        # optional

        row_version: Annotated[
            int, UseColumn("row_ver"), UseConstraint(ColumnConstraintType.NOT_NULL)
        ] = Field(default=1, ge=1)
"""

import sys
from typing import Any, ClassVar, Dict, List, Union

from pydantic import Field

from ..base.fields import UseConstraint
from ..backend.errors import DatabaseError
from ..backend.expression import SQLPredicate, SQLValueExpression
from ..backend.expression.statements.ddl_table import ColumnConstraintType
from ..backend.result import QueryResult
from ..interface import ModelEvent
from ..interface.update import IUpdateBehavior
from ..interface.model import IActiveRecord, IAsyncActiveRecord

if sys.version_info >= (3, 9):
    from typing import Annotated
else:  # pragma: no cover - 3.8 compatibility
    from typing_extensions import Annotated


class OptimisticLockMixin(IUpdateBehavior):
    """Optimistic-lock *semantics* — declares no field.

    Subclasses (or the model) must declare an integer field and announce
    it via ``__version_field__``; the column name follows the standard
    resolution (``UseColumn`` on the declared field).  The mixin
    contributes the lock semantics on UPDATE:

    * WHERE ``<version column> == <last known DB value>``
    * SET  ``<version column> = <version column> + increment``

    The column value is framework-managed: manual writes are rejected.
    """

    __version_field__: ClassVar[str] = "version"
    __version_increment_by__: ClassVar[int] = 1

    # Framework bookkeeping — deliberately private and invisible: the last
    # version value known to be committed to the database.  It must never
    # track in-memory user assignments, otherwise the lock condition could
    # be defeated.  (This is internal *state*, not a column; hiding it is
    # correct, unlike hiding the column itself.)
    _version_snapshot: int = 1

    def __init__(self, **data):
        """Initialise mixin, validate configuration and register event handlers."""
        super().__init__(**data)
        self.__class__._validate_version_config()
        self._version_snapshot = self.version_value
        self.on(ModelEvent.BEFORE_INSERT, self._handle_version_before_insert)
        self.on(ModelEvent.AFTER_INSERT, self._handle_version_after_insert)
        self.on(ModelEvent.BEFORE_UPDATE, self._handle_version_before_update)
        self.on(ModelEvent.AFTER_UPDATE, self._handle_version_after_update)

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------
    @classmethod
    def _validate_version_config(cls) -> None:
        """Fail fast when ``__version_field__`` does not name a real field."""
        field_name = cls.__version_field__
        if field_name not in cls.model_fields:
            raise TypeError(
                f"{cls.__name__}: __version_field__ = {field_name!r} does not "
                f"name a model field. Declare the version field (e.g. "
                f"`{field_name}: int = Field(default=1, ge=1)`) or use "
                f"DefaultOptimisticLockMixin."
            )
        if cls.__version_increment_by__ <= 0:
            raise ValueError(
                f"{cls.__name__}: __version_increment_by__ must be positive, "
                f"got {cls.__version_increment_by__!r}"
            )

    @classmethod
    def _version_field_name(cls) -> str:
        """The Python field name carrying the version (``__version_field__``)."""
        return cls.__version_field__

    @classmethod
    def _version_column_name(cls) -> str:
        """The database column name for the version field (UseColumn-aware)."""
        return cls.get_column_name(cls.__version_field__)

    @classmethod
    def _version_increment(cls) -> int:
        """The configured increment applied on each UPDATE."""
        return cls.__version_increment_by__

    @property
    def version_value(self) -> int:
        """Current in-memory version value (of the configured field)."""
        return getattr(self, self._version_field_name())

    # ------------------------------------------------------------------
    # Lock semantics (IUpdateBehavior)
    # ------------------------------------------------------------------
    def get_update_conditions(self) -> List[SQLPredicate]:
        """Add the optimistic-lock check to the UPDATE WHERE clause.

        Uses ``_version_snapshot`` (the last committed value), never the
        in-memory field, so user-side tampering cannot alter the condition.
        """
        if self.is_new_record:
            return []
        from ..backend.expression.core import Column

        backend = self.backend()
        return [
            Column(backend.dialect, self._version_column_name())
            == self._version_snapshot
        ]

    def get_update_expressions(self) -> Dict[str, SQLValueExpression]:
        """Add the version increment to the UPDATE SET clause.

        The key is the *field name*; the update pipeline maps it to the
        column (UseColumn-aware) like any other SET entry.  Because the
        pipeline merges behaviour expressions after dirty-field data, this
        column-arithmetic expression overrides any user-assigned value.
        """
        if self.is_new_record:
            return {}
        from ..backend.expression.core import Column

        backend = self.backend()
        column = Column(backend.dialect, self._version_column_name())
        return {self._version_field_name(): column + self._version_increment()}

    # ------------------------------------------------------------------
    # Event handlers (write protection + value sync)
    # ------------------------------------------------------------------
    def _handle_version_before_insert(self, instance, *, data=None, **kwargs) -> None:
        """Normalise the version to 1 for new records (memory + insert data)."""
        field_name = self._version_field_name()
        if data is not None:
            data[field_name] = 1
        setattr(self, field_name, 1)
        self._version_snapshot = 1

    def _handle_version_before_update(self, instance, *, data=None,
                                      dirty_fields: set = None, **kwargs) -> None:
        """Reject manual version writes; the column is framework-managed."""
        field_name = self._version_field_name()
        if data is not None and field_name in data:
            if data[field_name] != self._version_snapshot:
                raise DatabaseError(
                    f"Version field {field_name!r} is managed by "
                    f"OptimisticLockMixin and cannot be set manually "
                    f"(got {data[field_name]!r}, expected {self._version_snapshot!r})."
                )

    def _handle_version_after_insert(
        self,
        instance: Union["IActiveRecord", "IAsyncActiveRecord"],
        *,
        data: Dict[str, Any] = None,
        result: "QueryResult" = None,
        **kwargs,
    ) -> None:
        """Sync the version field from RETURNING data after INSERT (default 1)."""
        value = self._extract_returned_version(result)
        if value is not None:
            setattr(self, self._version_field_name(), value)
            self._version_snapshot = value

    def _handle_version_after_update(
        self,
        instance: Union["IActiveRecord", "IAsyncActiveRecord"],
        *,
        data: Dict[str, Any] = None,
        dirty_fields: set = None,
        result: "QueryResult" = None,
        **kwargs,
    ) -> None:
        """Verify the lock and sync the version after UPDATE.

        Raises:
            DatabaseError: If optimistic lock check fails (record was
                updated by another process).
        """
        if result.affected_rows == 0:
            raise DatabaseError("Record was updated by another process")

        value = self._extract_returned_version(result)
        if value is None:
            value = self._version_snapshot + self._version_increment()
        setattr(self, self._version_field_name(), value)
        self._version_snapshot = value

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _extract_returned_version(self, result: "QueryResult"):
        """Pull the version value out of a RETURNING result, if present."""
        if result.data is None:
            return None
        rows = result.data if isinstance(result.data, list) else [result.data]
        field_name = self._version_field_name()
        for row in rows:
            if isinstance(row, dict) and field_name in row and row[field_name] is not None:
                return row[field_name]
        return None


class DefaultOptimisticLockMixin(OptimisticLockMixin):
    """Optimistic locking with the conventional ``version`` field declared.

    Adds ``version: int`` (``NOT NULL``, ``ge=1``, default 1) so models can
    simply mix it in.  Use :class:`OptimisticLockMixin` directly when the
    field should carry a different Python name or column.
    """

    version: Annotated[int, UseConstraint(ColumnConstraintType.NOT_NULL)] = Field(
        default=1, ge=1
    )
