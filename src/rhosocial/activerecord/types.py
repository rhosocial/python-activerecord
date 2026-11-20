# src/rhosocial/activerecord/types.py
from enum import Enum
from typing import Optional, Union, Tuple, Dict, Any


class WriteOperation(Enum):
    """The write operation a field generator is running for.

    Generators are declared per operation on a field annotation; the write path
    passes the operation it is performing so the right generator (or "filter
    this field out") is selected. Soft-delete and restore are distinct from a
    plain update because they deliberately rewrite ``deleted_at``.
    """

    INSERT = "before_insert"
    UPDATE = "before_update"
    SOFT_DELETE = "before_soft_delete"
    RESTORE = "before_restore"

# ``None`` declares a keyless model: the relation has no single-row identity, so
# it cannot be addressed with ``find_one`` / ``find_all([pk])`` and cannot be
# updated by primary key. Inserts, queries, relations and aggregation all still
# work; see ``IActiveRecord.addressable()``.
PrimaryKeyDef = Optional[Union[str, Tuple[str, ...]]]
PrimaryKeyValue = Union[Any, Dict[str, Any]]
