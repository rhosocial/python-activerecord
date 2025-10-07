"""
Tests for relation descriptor functionality.
"""
import pytest
from typing import ClassVar

from pydantic import BaseModel

from rhosocial.activerecord.relation.base import RelationManagementMixin
from rhosocial.activerecord.relation.descriptors import BelongsTo, HasOne, HasMany


@pytest.mark.feature
@pytest.mark.relation
class TestRelationDescriptors:
    """Tests for the relation descriptor functionality."""
    
    def test_descriptor_types(self):
        """Test that relation descriptors are properly typed."""
        class TestModel(RelationManagementMixin, BaseModel):
            username: str
            department_id: int
            department: ClassVar[BelongsTo["Department"]] = BelongsTo(
                foreign_key="department_id",
                inverse_of="employees"
            )

        relation = TestModel.get_relation("department")
        assert isinstance(relation, BelongsTo)
        assert relation.foreign_key == "department_id"
        assert relation.inverse_of == "employees"

    def test_has_many_descriptor(self):
        """Test HasMany descriptor functionality."""
        class TestModel(RelationManagementMixin, BaseModel):
            name: str
            employees: ClassVar[HasMany["Employee"]] = HasMany(
                foreign_key="department_id",
                inverse_of="department"
            )

        relation = TestModel.get_relation("employees")
        assert isinstance(relation, HasMany)
        assert relation.foreign_key == "department_id"
        assert relation.inverse_of == "department"

    def test_has_one_descriptor(self):
        """Test HasOne descriptor functionality."""
        class TestModel(RelationManagementMixin, BaseModel):
            name: str
            profile: ClassVar[HasOne["Profile"]] = HasOne(
                foreign_key="author_id",
                inverse_of="author"
            )

        relation = TestModel.get_relation("profile")
        assert isinstance(relation, HasOne)
        assert relation.foreign_key == "author_id"
        assert relation.inverse_of == "author"