# src/rhosocial/activerecord/field/version.py
"""Module providing optimistic locking functionality.

The version column is a *real pydantic field* declared by
:class:`OptimisticLockMixin` (``version: int``, default 1, ``ge=1``).
Because it is a regular field it flows through every generic path —
DDL generation, ``model_dump``, validation, dirty tracking — with no
special-casing anywhere in the framework.

Customisation (redeclare the field on the model; field-over-field is
normal pydantic inheritance and produces no shadow warnings):

* custom DB column: ``version: Annotated[int, UseColumn("row_ver")] = 1``
* renamed Python field: ``__version_field__ = "row_version"`` plus a
  redeclared ``row_version`` field
* custom increment: ``__version_increment_by__ = 2``

The column value is *framework-managed*: users must not write it.
Enforcement is layered (see ``_handle_version_before_insert`` /
``_handle_version_before_update`` and the snapshot discipline below):

1. INSERT normalises the stored value to 1 regardless of user input.
2. The UPDATE WHERE clause uses ``_version_snapshot`` — the last value
   known to be in the database — so in-memory tampering cannot break (or
   bypass) the lock condition.
3. The UPDATE SET clause is a column-arithmetic expression
   (``col = col + step``) which the update pipeline applies *after*
   merging dirty-field data, overriding any user-assigned value.
4. A user-assigned version that differs from the snapshot is rejected
   outright with :class:`DatabaseError` at BEFORE_UPDATE time.
"""

from typing import Annotated, Any, ClassVar, Dict, List, Union

from pydantic import Field

from ..base.fields import UseConstraint
from ..backend.expression.statements.ddl_table import ColumnConstraintType

from ..backend.errors import DatabaseError
from ..backend.expression import SQLPredicate, SQLValueExpression
from ..backend.result import QueryResult
from ..interface import ModelEvent
from ..interface.update import IUpdateBehavior
from ..interface.model import IActiveRecord, IAsyncActiveRecord


_VERSION_FIELD = "version"


class OptimisticLockMixin(IUpdateBehavior):
    """Optimistic locking via a real ``version`` integer field.

    The field flows through DDL generation, serialisation and dirty
    tracking like any other field.  The mixin contributes only the *lock
    semantics* on UPDATE:

    * WHERE ``<version column> == <last known DB value>``
    * SET  ``<version column> = <version column> + increment``

    The column value is framework-managed: manual writes are rejected.
    """

    version: Annotated[int, UseConstraint(ColumnConstraintType.NOT_NULL)] = Field(
        default=1, ge=1
    )

    __version_column__: ClassVar[str] = "version"
    __version_increment_by__: ClassVar[int] = 1

    # Framework bookkeeping — deliberately private and invisible: the last
    # version value known to be committed to the database.  It must never
    # track in-memory user assignments, otherwise the lock condition could
    # be defeated.  (This is internal *state*, not a column; hiding it is
    # correct, unlike hiding the column itself.)
    _version_snapshot: int = 1

    @classmethod
    def _get_column_name(cls, field_name: str) -> str:
        """Extend column resolution with the ``__version_column__`` knob.

        Only the version field is affected; everything else defers to the
        standard UseColumn-based resolution.  Implementing the resolution
        protocol here keeps the custom name consistent across DDL
        generation, lock conditions and SET expressions without any
        special-casing in those consumers.
        """
        if field_name == _VERSION_FIELD and cls.__version_column__ != _VERSION_FIELD:
            # Explicit knob wins over any UseColumn redeclaration.
            return cls.__version_column__
        return super()._get_column_name(field_name)

    def __init__(self, **data):
        """Initialise mixin, validate configuration and register event handlers."""
        super().__init__(**data)
        self.__class__._validate_version_config()
        self._version_snapshot = self.version
        self.on(ModelEvent.BEFORE_INSERT, self._handle_version_before_insert)
        self.on(ModelEvent.AFTER_INSERT, self._handle_version_after_insert)
        self.on(ModelEvent.BEFORE_UPDATE, self._handle_version_before_update)
        self.on(ModelEvent.AFTER_UPDATE, self._handle_version_after_update)

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------
    @classmethod
    def _validate_version_config(cls) -> None:
        """Validate class-level knobs early (fail fast on misconfiguration)."""
        if cls.__version_increment_by__ <= 0:
            raise ValueError(
                f"{cls.__name__}: __version_increment_by__ must be positive, "
                f"got {cls.__version_increment_by__!r}"
            )
        if not cls.__version_column__.strip():
            raise ValueError(
                f"{cls.__name__}: __version_column__ cannot be empty."
            )

    @classmethod
    def _version_field_name(cls) -> str:
        """The Python field name carrying the version (fixed: "version")."""
        return _VERSION_FIELD

    @classmethod
    def _version_column_name(cls) -> str:
        """The database column name for the version field (UseColumn-aware)."""
        return cls._get_column_name(_VERSION_FIELD)

    @classmethod
    def _version_increment(cls) -> int:
        """The configured increment applied on each UPDATE."""
        increment = cls.__version_increment_by__
        if increment <= 0:
            raise ValueError(
                f"{cls.__name__}: __version_increment_by__ must be positive, "
                f"got {increment!r}"
            )
        return increment

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
        field_name = self._version_field_name()
        value = self._extract_returned_version(result, field_name)
        if value is not None:
            setattr(self, field_name, value)
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

        field_name = self._version_field_name()
        value = self._extract_returned_version(result, field_name)
        if value is None:
            value = self._version_snapshot + self._version_increment()
        setattr(self, field_name, value)
        self._version_snapshot = value

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    @staticmethod
    def _extract_returned_version(result: "QueryResult", field_name: str):
        """Pull the version value out of a RETURNING result, if present."""
        if result.data is None:
            return None
        rows = result.data if isinstance(result.data, list) else [result.data]
        for row in rows:
            if isinstance(row, dict) and field_name in row and row[field_name] is not None:
                return row[field_name]
        return None
