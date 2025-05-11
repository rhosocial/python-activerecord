import time

import pytest

from src.rhosocial.activerecord.backend.errors import DatabaseError
from .fixtures.models import combined_article


def test_combined_update(combined_article):
    """Test combined functionality when updating records"""
    # Create and update article
    article = combined_article(title="Test", content="Test")
    article.save()
    original_updated_at = article.updated_at

    article.content = "Updated content"
    article.status = "published"
    time.sleep(0.1)
    article.save()

    # Verify updated state
    assert article.version == 2  # Version number increments
    assert article.created_at == original_updated_at  # Creation time remains unchanged
    assert article.updated_at > original_updated_at  # Update time changes


def test_combined_delete(combined_article):
    """Test combined functionality when deleting records"""
    # Create and delete article
    article = combined_article(title="Test", content="Test")
    article.save()
    article.delete()

    # Verify soft delete status
    assert article.deleted_at is not None
    assert combined_article.find_one(article.id) is None

    # Verify deleted records can be found
    found_article = combined_article.query_with_deleted().where(
        f"{combined_article.primary_key()} = ?",
        (article.id,)
    ).one()
    assert found_article is not None
    assert found_article.deleted_at is not None
    assert found_article.version == 1


def test_combined_concurrent_update(combined_article):
    """Test combined functionality during concurrent updates"""
    # Create article
    article = combined_article(title="Test", content="Test")
    article.save()

    # Simulate concurrent updates
    concurrent_article = combined_article.query_with_deleted().where(
        f"{combined_article.primary_key()} = ?",
        (article.id,)
    ).one()

    # First update succeeds
    article.content = "Updated by first"
    article.save()

    # Second update fails
    concurrent_article.content = "Updated by second"
    with pytest.raises(DatabaseError, match="Record was updated by another process"):
        concurrent_article.save()

    # Verify final state
    final_article = combined_article.find_one(article.id)
    assert final_article.content == "Updated by first"
    assert final_article.version == 2