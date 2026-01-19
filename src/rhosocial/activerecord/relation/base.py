# src/rhosocial/activerecord/relation/base.py
"""
Base classes for relation management.
Provides core descriptor and mixin implementations.
"""

from typing import Optional, List

from .cache import InstanceCache
from .descriptors import RelationDescriptor
from .interfaces import IRelationManagement


class IRelationManagementMixin(IRelationManagement):
    """
    Mixin providing relation management capabilities for ActiveRecord models.

    This mixin implements the core functionality for managing model relationships.
    It provides methods to register, retrieve, and manage relations for model classes.
    The mixin also handles instance-level caching of relation data.
    """

    @classmethod
    def _ensure_relations(cls) -> dict:
        """
        Ensures the class has its own relations dictionary.

        This method creates a separate relations dictionary for each class in the inheritance
        hierarchy to prevent sharing of relations between parent and child classes.
        It only creates the dictionary if it doesn't already exist in the class's
        own __dict__ (not inherited).

        Returns:
            The class's relations dictionary
        """
        if '_relations_dict' not in cls.__dict__:  # Check class's own dict
            cls._relations_dict = {}
        return cls._relations_dict

    @classmethod
    def register_relation(cls, name: str, relation: RelationDescriptor) -> None:
        """
        Register a relation descriptor with the given name.

        This method registers a relation descriptor to be associated with the given name
        for this class. The relation can later be retrieved using get_relation().

        Args:
            name: The name to associate with the relation
            relation: The RelationDescriptor to register
        """
        relations = cls._ensure_relations()
        # Remove 'raise ValueError' check to allow overrides
        # if name in relations:
        #     raise ValueError(f"Duplicate relation: {name}")
        relations[name] = relation

    @classmethod
    def get_relation(cls, name: str) -> Optional[RelationDescriptor]:
        """
        Get a relation descriptor by name.

        This method retrieves the RelationDescriptor registered with the given name.
        Returns None if no relation with the given name exists.

        Args:
            name: The name of the relation to retrieve

        Returns:
            The RelationDescriptor if found, None otherwise
        """
        relations = cls._ensure_relations()
        return relations.get(name)

    @classmethod
    def get_relations(cls) -> List[str]:
        """
        Get all registered relation names for this class.

        This method returns a list of all relation names that have been registered
        for this class. It does not include inherited relations.

        Returns:
            A list of relation names
        """
        relations = cls._ensure_relations()
        return list(relations.keys())

    def clear_relation_cache(self, name: Optional[str] = None) -> None:
        """
        Clear relation cache(s) for this instance.

        This method clears the cached relation data for this instance. If a specific
        relation name is provided, only that relation's cache is cleared. Otherwise,
        all relation caches for this instance are cleared.

        Args:
            name: Specific relation name to clear, or None to clear all relations

        Raises:
            ValueError: If a specific relation name is provided but doesn't exist
        """
        relations = self._ensure_relations()
        if name:
            relation = self.get_relation(name)
            if relation is None:
                raise ValueError(f"Unknown relation: {name}")
            # Clear specific relation cache using InstanceCache
            InstanceCache.delete(self, name)
        else:
            # Clear all relation caches
            for relation_name in relations:
                InstanceCache.delete(self, relation_name)
