# src/rhosocial/activerecord/relation/interfaces.py
"""
Core interfaces for the relations package.
Defines abstract base classes for relationship loading and querying.
"""
from abc import ABC, abstractmethod
from typing import Any, TypeVar, Generic, Optional, List, ClassVar, Dict


from ..interface import IActiveRecord, IAsyncActiveRecord, IActiveQuery, IAsyncActiveQuery

T = TypeVar('T', bound=IActiveRecord)
U = TypeVar('U', bound=IAsyncActiveRecord)


class IRelationLoader(Generic[T], ABC):
    """
    Abstract interface for loading related objects.
    Implementers define how to load related data for a given model instance.
    """

    @abstractmethod
    def load(self, instance: IActiveRecord) -> Optional[T]:
        """
        Load related data for the given model instance.

        Args:
            instance: Source model instance to load relations for (must be IActiveRecord, NOT IAsyncActiveRecord)

        Returns:
            Optional[Any]: Related model instance(s) or None if not found

        Raises:
            ValueError: If instance lacks required foreign key

        WARNING:
            This method is for synchronous models only. Do not use with IAsyncActiveRecord instances,
            as this will lead to unpredictable consequences. Use AsyncRelationLoader for async models.
        """
        pass

    @abstractmethod
    def batch_load(self, instances: List[IActiveRecord], base_query: Optional[IActiveQuery]) -> Dict[int, T]:
        """Batch load related data for multiple instances.

        Args:
            instances: List of model instances to load relations for (must be IActiveRecord, NOT IAsyncActiveRecord)
            base_query: Pre-configured query to use for loading

        Returns:
            Dict mapping instance IDs to their related data

        Raises:
            ValueError: If instances lack required keys

        WARNING:
            This method is for synchronous models only. Do not use with IAsyncActiveRecord instances,
            as this will lead to unpredictable consequences. Use AsyncRelationLoader for async models.
        """
        pass


class IAsyncRelationLoader(Generic[U], ABC):
    """
    Abstract interface for asynchronously loading related objects.
    Implementers define how to load related data for a given model instance asynchronously.
    """

    @abstractmethod
    async def load(self, instance: IAsyncActiveRecord) -> Optional[U]:
        """
        Asynchronously load related data for the given model instance.

        Args:
            instance: Source model instance to load relations for (must be IAsyncActiveRecord, NOT IActiveRecord)

        Returns:
            Optional[Any]: Related model instance(s) or None if not found

        Raises:
            ValueError: If instance lacks required foreign key

        WARNING:
            This method is for asynchronous models only. Do not use with IActiveRecord instances,
            as this will lead to unpredictable consequences. Use RelationLoader for sync models.
        """
        pass

    @abstractmethod
    async def batch_load(self, instances: List[IAsyncActiveRecord], base_query: Optional[IAsyncActiveQuery]) -> Dict[int, U]:
        """Asynchronously batch load related data for multiple instances.

        Args:
            instances: List of model instances to load relations for (must be IAsyncActiveRecord, NOT IActiveRecord)
            base_query: Pre-configured query to use for loading

        Returns:
            Dict mapping instance IDs to their related data

        Raises:
            ValueError: If instances lack required keys

        WARNING:
            This method is for asynchronous models only. Do not use with IActiveRecord instances,
            as this will lead to unpredictable consequences. Use RelationLoader for sync models.
        """
        pass


class IRelationValidation(ABC):
    """
    Abstract interface for relationship validation.
    Implementers define validation rules for relationship types.
    """

    @abstractmethod
    def validate(self, owner: IActiveRecord, related_model: IActiveRecord) -> None:
        """
        Validate relationship between two models.

        Args:
            owner: Owner model class (must be IActiveRecord, NOT IAsyncActiveRecord)
            related_model: Related model class (must be IActiveRecord, NOT IAsyncActiveRecord)

        Raises:
            ValueError: If relationship validation fails

        WARNING:
            This method is for synchronous models only. Do not use with IAsyncActiveRecord classes,
            as this will lead to unpredictable consequences. Use AsyncRelationValidation for async models.
        """
        pass


class IAsyncRelationValidation(ABC):
    """
    Abstract interface for asynchronous relationship validation.
    Implementers define validation rules for relationship types that can run asynchronously.
    """

    @abstractmethod
    def validate(self, owner: IAsyncActiveRecord, related_model: IAsyncActiveRecord) -> None:
        """
        Validate relationship between two models.

        Args:
            owner: Owner model class (must be IAsyncActiveRecord, NOT IActiveRecord)
            related_model: Related model class (must be IAsyncActiveRecord, NOT IActiveRecord)

        Raises:
            ValueError: If relationship validation fails

        WARNING:
            This method is for asynchronous models only. Do not use with IActiveRecord classes,
            as this will lead to unpredictable consequences. Use RelationValidation for sync models.
        """
        pass


class IRelationManagement(ABC):
    """Interface defining required relation management capabilities."""

    _relations: ClassVar[dict]

    @abstractmethod
    def register_relation(self, name: str, relation: Any) -> None:
        """Register a new relation.

        Args:
            name: Name of the relation to register
            relation: The relation descriptor to register

        NOTE:
            When implementing this interface for async models, ensure the relation descriptor
            is compatible with async models (e.g., AsyncRelationDescriptor, not RelationDescriptor).
            Mixing sync and async relation descriptors can lead to unpredictable consequences.
        """
        pass

    @abstractmethod
    def get_relation(self, name: str) -> Optional[Any]:
        """Get relation by name.

        Args:
            name: Name of the relation to retrieve

        Returns:
            The relation descriptor if found, None otherwise

        NOTE:
            The returned relation descriptor type depends on the model type (sync vs async).
            For async models, this should return AsyncRelationDescriptor instances.
        """
        pass

    @abstractmethod
    def get_relations(self) -> List[str]:
        """Get all relation names.

        Returns:
            List of registered relation names for this class
        """
        pass

    @abstractmethod
    def clear_relation_cache(self, name: Optional[str] = None) -> None:
        """Clear relation cache(s).

        Args:
            name: Specific relation name to clear, or None to clear all relation caches

        NOTE:
            This affects instance-level caching for relations. The cache is specific to the model instance.
        """
        pass
