"""Type definitions for ActiveRecord implementation."""

from typing import TypeVar, Any, Dict, List, Optional, Union

# Type variable for model classes
ModelT = TypeVar('ModelT', bound='BaseActiveRecord')

# Common type aliases
ConditionType = Union[Any, Dict[str, Any]]
MultiConditionType = Optional[Union[List[Any], Dict[str, Any]]]