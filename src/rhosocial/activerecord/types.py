# src/rhosocial/activerecord/types.py
from typing import Optional, Union, Tuple, Dict, Any

# ``None`` declares a keyless model: the relation has no single-row identity, so
# it cannot be addressed with ``find_one`` / ``find_all([pk])`` and cannot be
# updated by primary key. Inserts, queries, relations and aggregation all still
# work; see ``IActiveRecord.addressable()``.
PrimaryKeyDef = Optional[Union[str, Tuple[str, ...]]]
PrimaryKeyValue = Union[Any, Dict[str, Any]]
