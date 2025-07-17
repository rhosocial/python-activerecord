# tests/rhosocial/activerecord_test/relation/test_interfaces.py
"""Tests for relation interfaces."""

from src.rhosocial.activerecord.relation.interfaces import RelationManagementInterface


def test_relation_management_interface(employee_class, department_class):
    """Test RelationManagementInterface implementation."""
    # Verify interface implementation
    assert isinstance(employee_class, type)
    assert issubclass(employee_class, RelationManagementInterface)

    # Test relation registration
    relations = employee_class.get_relations()
    assert "department" in relations

    relation = employee_class.get_relation("department")
    assert relation is not None
    assert relation.foreign_key == "department_id"
    assert relation.inverse_of == "employees"

    # Test query method creation
    assert hasattr(employee_class, "department_query")


def test_relation_cache_operations(employee):
    """Test relation cache management."""
    # Clear specific relation cache
    employee.clear_relation_cache("department")

    # Clear all relation caches
    employee.clear_relation_cache()


def test_invalid_relation_access(employee):
    """Test accessing invalid relations."""
    try:
        employee.clear_relation_cache("invalid_relation")
        assert False, "Should raise ValueError"
    except ValueError as e:
        assert "Unknown relation" in str(e)