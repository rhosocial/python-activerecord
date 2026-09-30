# src/rhosocial/activerecord/field/read_only.py
"""Module providing read-only model semantics.

One class, :class:`ReadOnlyMixin`, following the "semantics only — declares
no fields" pattern of :class:`~.soft_delete.SoftDeleteMixin` and
:class:`~.version.OptimisticLockMixin`: the model declares whatever columns it
has, and the mixin supplies only the rule that writes are refused.

Typical use is a read replica, a database account whose privileges are scoped
to reads, or a model mapped onto a stored result set:

.. code-block:: python

    class AuditLog(ActiveRecord, ReadOnlyMixin):
        __table_name__ = "audit_log"
        ...

Read-only is **orthogonal** to the primary key and to the physical object the
model maps. A read-only table may still have an auto-generated primary key, and
a keyless table may still be writable. The mixin imposes no opinion on either.

A single implementation serves both the sync and the async models, because
``read_only`` is a zero-I/O predicate: the ``field/`` convention is that an
async variant is needed only when a method issues SQL (``SoftDeleteMixin`` has
one for ``restore``), and nothing here does.

Scope: this guards the framework's own write paths. ``backend.expression`` is
publicly exported, so a caller can still build and execute an UPDATE by hand.
The real guarantee is database credentials; this prevents accidents.
"""

from typing import ClassVar

from ..interface.update import IDeleteBehavior, IReadOnlyBehavior, IUpdateBehavior


class ReadOnlyMixin(IReadOnlyBehavior):
    """Read-only *semantics* — declares no fields.

    Inheriting this mixin sets ``__read_only__`` to True and makes the
    framework refuse INSERT / UPDATE / DELETE issued through the model API.
    Set ``__read_only__ = False`` explicitly to opt back out.
    """

    __read_only__: ClassVar[bool] = True

    def __init_subclass__(cls, **kwargs) -> None:
        super().__init_subclass__(**kwargs)
        cls._validate_read_only_config()

    @classmethod
    def _validate_read_only_config(cls) -> None:
        """Fail fast when write-event mixins are combined with read-only.

        Runs from ``__init_subclass__``, so the combination is rejected when
        the class is defined rather than when an instance is first built. That
        hook is used rather than ``__init__`` because a mixin's ``__init__`` is
        not reachable in the usual declaration order: with
        ``class X(ActiveRecord, ReadOnlyMixin)``, pydantic's ``BaseModel``
        sits ahead of the mixin in the MRO and its ``__init__`` does not
        delegate, so a mixin ``__init__`` never runs. (``SoftDeleteMixin`` and
        ``TimestampMixin`` validate from ``__init__`` and therefore their
        fail-fasts are inert; this mixin does not inherit that gap.)

        ``SoftDeleteMixin`` registers BEFORE_DELETE and issues an UPDATE;
        ``TimestampMixin`` and ``OptimisticLockMixin`` register
        BEFORE_UPDATE. On a read-only model those handlers can never run,
        because every write is refused first -- so the combination is always a
        mistake, and a silent one: the mixin would appear to work right up
        until a save was refused with no hint that the timestamps or the
        optimistic lock were involved.

        Detection is by interface, matching how the framework finds these
        behaviours elsewhere (``issubclass(cls, IUpdateBehavior)`` in
        ``_update_internal``, ``isinstance(self, IDeleteBehavior)`` in
        ``delete``), so a third-party behaviour mixin is caught too.
        """
        if not cls.read_only():
            return
        conflicts = []
        if issubclass(cls, IDeleteBehavior):
            conflicts.append("IDeleteBehavior (e.g. SoftDeleteMixin)")
        if issubclass(cls, IUpdateBehavior):
            conflicts.append("IUpdateBehavior (e.g. TimestampMixin, OptimisticLockMixin)")
        if conflicts:
            raise TypeError(
                f"{cls.__name__} is read-only but also implements {', '.join(conflicts)}. "
                f"Those mixins register write event handlers that can never run, because "
                f"every write is refused first. Remove read-only, or set "
                f"__read_only__ = False if the model is genuinely writable."
            )

    @classmethod
    def read_only(cls) -> bool:
        """Whether writes through framework paths must be refused.

        The single framework-wide decision point; every write gate reads this
        value. Never queries the database -- read-only-ness is a static
        declaration by the developer, not an introspection result, so a model
        without a database connection still answers correctly.

        A classmethod rather than an instance method because the gates are not
        all instance-level: ``bulk_create`` and friends are classmethods, and
        ``ActiveQuery.update_all()`` / ``delete_all()`` only hold the model
        *class*. Reading it off an instance would make the model-level
        behaviour depend on where it is asked from.

        Returns:
            bool: The declared read-only flag.
        """
        return bool(getattr(cls, "__read_only__", False))
