# src/rhosocial/activerecord/backend/dialect/protocols/query/column_type.py
"""ColumnTypeSupport protocol.

Re-exported from :mod:`rhosocial.activerecord.backend.dialect.protocols`;
see that package for the full protocol surface and the rules the conformance
tests enforce.
"""

from typing import Any, Dict, Optional, Protocol, Type, TYPE_CHECKING, runtime_checkable

if TYPE_CHECKING:  # pragma: no cover
    from ....expression.column_types import ColumnBase


@runtime_checkable
class ColumnTypeSupport(Protocol):
    """Which column class each common Python type means on this dialect.

    The protocol answers two questions and chooses nothing. Choosing a class
    for a field's annotation is the model layer's lookup: it normalises the
    annotation against the keys of these tables and fails, naming the field,
    when neither table answers.

    ``suggested_column_types()``
        The table the model layer reads when a field does not declare its own
        column class. Keys are the common Python types the framework defines:
        ``bool``, ``int``, ``float``, ``decimal.Decimal``, ``str``, ``bytes``,
        ``bytearray``, ``datetime.date``, ``datetime.time``,
        ``datetime.datetime``, ``datetime.timedelta``, ``uuid.UUID``,
        ``dict``, ``list``, ``tuple``, ``set``, ``frozenset``, ``enum.Enum``.
        **Every key must be answered.** A value is a
        :class:`~...expression.column_types.ColumnBase` subclass, or ``None``
        for "this backend genuinely has no column class for it" — the last
        resort, for a value no workaround can express, never a first answer.
        A missing key is an omission, not a decision.

    ``suggested_extra_column_types()``
        The backend's own vocabulary. Keys are Python types the framework does
        not model (a ``Point``, a ``complex``); values are ``ColumnBase``
        subclasses. A type the backend does not offer is simply absent.

    Both are methods, not class attributes, so the answer may depend on the
    server version or build; both return fresh dicts so a caller cannot mutate
    what later lookups will read. There is no inherited default: a table in
    core would be a guess about a server core has never seen.
    """

    def suggested_column_types(self) -> Dict[Any, Optional[Type["ColumnBase"]]]: ...

    def suggested_extra_column_types(self) -> Dict[Any, Type["ColumnBase"]]: ...
