"""
Base classes for relation management.
Provides core descriptor and mixin implementations.
"""

from typing import Optional, List

from .descriptors import RelationDescriptor
from .interfaces import RelationManagementInterface


class RelationManagementMixin(RelationManagementInterface):
    """Mixin providing relation management capabilities."""

    @classmethod
    def _ensure_relations(cls) -> dict:
        """Ensure class has its own relations dictionary."""
        if '_relations_dict' not in cls.__dict__:  # Check class's own dict
            cls._relations_dict = {}
        return cls._relations_dict

    @classmethod
    def register_relation(cls, name: str, relation: RelationDescriptor) -> None:
        """Register relation descriptor."""
        relations = cls._ensure_relations()
        # Remove 'raise ValueError' check to allow overrides
        # if name in relations:
        #     raise ValueError(f"Duplicate relation: {name}")
        relations[name] = relation

    @classmethod
    def get_relation(cls, name: str) -> Optional[RelationDescriptor]:
        """Get relation by name."""
        relations = cls._ensure_relations()
        return relations.get(name)

    @classmethod
    def get_relations(cls) -> List[str]:
        """Get all relation names."""
        relations = cls._ensure_relations()
        return list(relations.keys())

    def clear_relation_cache(self, name: Optional[str] = None) -> None:
        """
        Clear relation cache(s).

        Args:
            name: Specific relation or None for all

        Raises:
            ValueError: If relation doesn't exist
        """
        relations = self._ensure_relations()
        if name:
            relation = self.get_relation(name)
            if relation is None:
                raise ValueError(f"Unknown relation: {name}")
            relation.__delete__(self)
        else:
            for relation in relations.values():
                relation.__delete__(self)
