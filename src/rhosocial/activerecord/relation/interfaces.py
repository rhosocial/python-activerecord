"""
Core interfaces for the relations package.
Defines abstract base classes for relationship loading and querying.
"""
from abc import ABC, abstractmethod
from typing import Any, TypeVar, Generic, Optional, List, ClassVar, Dict

T = TypeVar('T')

class RelationLoader(Generic[T], ABC):
    """
    Abstract interface for loading related objects.
    Implementers define how to load related data for a given model instance.
    """

    @abstractmethod
    def load(self, instance: Any) -> Optional[T]:
        """
        Load related data for the given model instance.

        Args:
            instance: Source model instance to load relations for

        Returns:
            Optional[T]: Related model instance(s) or None if not found

        Raises:
            ValueError: If instance lacks required foreign key
        """
        pass

    @abstractmethod
    def batch_load(self, instances: List[Any], base_query: Any) -> Dict[int, Any]:
        """Batch load related data for multiple instances.

        Args:
            instances: List of model instances to load relations for
            base_query: Pre-configured query to use for loading

        Returns:
            Dict mapping instance IDs to their related data

        Raises:
            ValueError: If instances lack required keys
        """
        pass

class RelationValidation(ABC):
    """
    Abstract interface for relationship validation.
    Implementers define validation rules for relationship types.
    """

    @abstractmethod
    def validate(self, owner: Any, related_model: Any) -> None:
        """
        Validate relationship between two models.

        Args:
            owner: Owner model class
            related_model: Related model class

        Raises:
            ValueError: If relationship validation fails
        """
        pass

class RelationManagementInterface(ABC):
    """Interface defining required relation management capabilities."""

    _relations: ClassVar[dict]

    @abstractmethod
    def register_relation(self, name: str, relation: Any) -> None:
        """Register a new relation."""
        pass

    @abstractmethod
    def get_relation(self, name: str) -> Optional[Any]:
        """Get relation by name."""
        pass

    @abstractmethod
    def get_relations(self) -> List[str]:
        """Get all relation names."""
        pass

    @abstractmethod
    def clear_relation_cache(self, name: Optional[str] = None) -> None:
        """Clear relation cache(s)."""
        pass