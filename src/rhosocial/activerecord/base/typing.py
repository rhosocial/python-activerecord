# src/rhosocial/activerecord/base/typing.py
"""Type definitions for ActiveRecord implementation."""

from typing import Any, Dict, List, Optional, Union


# Common type aliases
ConditionType = Union[Any, Dict[str, Any]]
MultiConditionType = Optional[Union[List[Any], Dict[str, Any]]]
