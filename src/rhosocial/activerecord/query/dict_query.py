"""Dictionary query wrapper implementation."""
from typing import Generic, Any, List, Optional, Set, Dict
from ..interface import ModelT, IQuery


class DictQuery(Generic[ModelT]):
    """Wrapper for queries that return dictionary results instead of models."""

    def __init__(self, query: IQuery[ModelT], include: Optional[Set[str]] = None, exclude: Optional[Set[str]] = None):
        self._query = query  # Underlying query instance
        self._include = include  # Fields to include in result
        self._exclude = exclude  # Fields to exclude from result

    def _to_dict(self, record: ModelT) -> Dict[str, Any]:
        """Convert model instance to dictionary.

        Applies include/exclude filters if specified.
        """
        return record.model_dump(
            include=self._include,
            exclude=self._exclude
        )

    def all(self) -> List[Dict[str, Any]]:
        """Return dictionary list of all results."""
        records = self._query.all()
        return [self._to_dict(record) for record in records]

    def one(self) -> Optional[Dict[str, Any]]:
        """Return dictionary of first result."""
        record = self._query.one()
        return self._to_dict(record) if record else None

    def __getattr__(self, name: str) -> Any:
        """Delegate other query methods to original query."""
        return getattr(self._query, name)