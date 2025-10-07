"""
Tests for relation base functionality.
"""
import pytest
from typing import ClassVar, Any, Dict, List

from pydantic import BaseModel

from rhosocial.activerecord.relation.base import RelationManagementMixin
from rhosocial.activerecord.relation.cache import CacheConfig
from rhosocial.activerecord.relation.descriptors import HasOne, HasMany, BelongsTo, RelationDescriptor
from rhosocial.activerecord.relation.interfaces import RelationLoader


@pytest.mark.feature
@pytest.mark.relation
class TestRelationDescriptor:
    """Tests for the relation descriptor functionality."""
    
    def test_relation_descriptor_init(self):
        """Test RelationDescriptor initialization."""
        # This is more of a unit test not requiring database functionality
        class CustomLoader(RelationLoader):
            def load(self, instance):
                return {"id": 1, "name": "Test"}
        
            def batch_load(self, instances: List[Any], base_query: Any) -> Dict[int, Any]:
                pass

        descriptor = RelationDescriptor(
            foreign_key="test_id",
            inverse_of="test",
            loader=CustomLoader(),
            cache_config=CacheConfig(enabled=True)
        )

        assert descriptor.foreign_key == "test_id"
        assert descriptor.inverse_of == "test"
        assert descriptor._loader is not None

    def test_relation_registration_validation(self):
        """Test validation during relation registration."""
        # This is a unit test that doesn't require database functionality
        class TestModel(RelationManagementMixin, BaseModel):
            username: str
            department_id: int
            test: ClassVar[HasOne["Other"]] = HasOne(
                foreign_key="test_id",
                inverse_of="inverse"
            )
            test: ClassVar[HasMany["Other"]] = HasMany(
                foreign_key="test_id",
                inverse_of="inverse"
            )

    def test_relation_inheritance(self):
        """Test that derived classes can override relations"""
        class ParentModel(RelationManagementMixin, BaseModel):
            username: str
            test: ClassVar[HasOne["Other"]] = HasOne(
                foreign_key="test_id",
                inverse_of="inverse"
            )

        class ChildModel(ParentModel):
            test: ClassVar[HasMany["Other"]] = HasMany(
                foreign_key="test_id",
                inverse_of="inverse"
            )

        parent_relation = ParentModel.get_relation("test")
        child_relation = ChildModel.get_relation("test")

        # Verify parent relation remains HasOne
        assert isinstance(parent_relation, HasOne)
        assert parent_relation.foreign_key == "test_id"

        # Verify child relation is overridden to HasMany
        assert isinstance(child_relation, HasMany)
        assert child_relation.foreign_key == "test_id"

        # Verify relations are different objects
        assert parent_relation is not child_relation

    def test_forward_reference_resolution(self):
        """Test resolution of forward references in relationship declarations."""
        class CircularA(RelationManagementMixin, BaseModel):
            username: str
            b: ClassVar[HasOne["CircularB"]] = HasOne(
                foreign_key="a_id",
                inverse_of="a"
            )

        class CircularB(RelationManagementMixin, BaseModel):
            username: str
            a_id: int
            a: ClassVar[BelongsTo["CircularA"]] = BelongsTo(
                foreign_key="a_id",
                inverse_of="b"
            )

        a = CircularA(username="test")
        b = CircularB(username="test", a_id=1)

        # This just tests that the models can be created without error
        assert a is not None
        assert b is not None