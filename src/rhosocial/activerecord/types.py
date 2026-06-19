# src/rhosocial/activerecord/types.py
from typing import Union, Tuple, Dict, Any

PrimaryKeyDef = Union[str, Tuple[str, ...]]
PrimaryKeyValue = Union[Any, Dict[str, Any]]
