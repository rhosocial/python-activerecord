# tests/rhosocial/activerecord_test/mixins/test_optimistic_lock.py
"""Test optimistic locking functionality"""
import pytest

from rhosocial.activerecord.backend.errors import DatabaseError
from .fixtures.models import versioned_product


def test_optimistic_lock(versioned_product):
    """Test optimistic locking functionality"""
    # Create new record
    product = versioned_product(name="Test Product", price=10.0)
    product.save()

    # Verify initial version
    assert product.version == 1

    # Update record
    product.price = 15.0
    product.save()

    # Verify version increment
    assert product.version == 2

    # Simulate concurrent update conflict
    product_conflict = versioned_product.find_one(product.id)
    product_conflict.price = 20.0
    product_conflict.save()  # This update succeeds, version becomes 3

    # Original record update should now fail
    product.price = 25.0  # product.version is still 2 here
    with pytest.raises(DatabaseError, match="Record was updated by another process"):
        product.save()

    # Verify final version
    latest_product = versioned_product.find_one(product.id)
    assert latest_product.version == 3
    assert latest_product.price == 20.0


def test_version_increment(versioned_product):
    """Test version number increments correctly"""
    # Create new record
    product = versioned_product(name="Test Product", price=10.0)
    product.save()

    # Verify initial version
    assert product.version == 1

    # First update
    product.price = 15.0
    product.save()
    assert product.version == 2

    # Second update
    product.price = 20.0
    product.save()
    assert product.version == 3

    # Verify version in database
    db_product = versioned_product.find_one(product.id)
    assert db_product.version == 3
