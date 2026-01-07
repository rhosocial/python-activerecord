# src/rhosocial/activerecord/query/dict_query.py
"""DictQueryMixin implementation."""

from typing import List, Optional, Set, Dict, Any, Tuple, Union
from ..interface import ModelT


class DictQueryMixin:
    """DictQueryMixin implementation for dictionary-based query results.

    This mixin provides to_dict functionality for ActiveQuery, allowing conversion
    of model instances to dictionaries. It should only be mixed into ActiveQuery
    and not used independently.

    Note: For aggregation queries (both simple and complex), to_dict() calls are ineffective
    as the results are already in dictionary format.

    This mixin is particularly useful when using select() with partial column lists
    to retrieve specific data as dictionaries rather than full model instances,
    avoiding object state inconsistency issues.
    """

    # region Instance Attributes
    model_class: type
    _backend: Any
    # Legacy attributes for backward compatibility, though not actively used
    # since or_where, start_or_group, end_or_group methods have been removed
    condition_groups: List[List[Tuple[str, tuple, str]]]
    current_group: int
    order_clauses: List[str]
    join_clauses: List[Union[str, type]]
    select_columns: Optional[List[str]]
    limit_count: Optional[int]
    offset_count: Optional[int]
    _adapt_params: bool
    _explain_enabled: bool
    _explain_options: dict
    _group_columns: List[str]
    _having_conditions: List[Tuple[str, Tuple]]
    _expressions: List[Any]
    _window_definitions: Dict[str, Dict]
    _grouping_sets: Optional[Any]
    # endregion

    def to_dict(self, include: Optional[Set[str]] = None, exclude: Optional[Set[str]] = None, direct_dict: bool = False):
        """Convert query results to dictionary format.

        Note: For aggregation queries (both simple and complex), to_dict() calls are ineffective
        as aggregation results are already in dictionary format.
        """
        pass

    def all(self) -> List[Dict[str, Any]]:
        """Return dictionary list of all results.

        For aggregation queries (both simple and complex), the results are already in dictionary format,
        so this method returns them directly without additional conversion.
        """
        # This method overrides the BaseQueryMixin.all() method to return dictionaries instead of model instances
        pass

    def one(self) -> Optional[Dict[str, Any]]:
        """Return dictionary of first result.

        For aggregation queries (both simple and complex), the result is already in dictionary format,
        so this method returns it directly without additional conversion.
        """
        # This method overrides the BaseQueryMixin.one() method to return a dictionary instead of a model instance
        pass