# tests/rhosocial/activerecord_test/mixins/test_timestamps.py
"""Test timestamp functionality"""
import time
from datetime import datetime

from .fixtures.models import timestamped_post


def test_timestamps(timestamped_post):
    """Test timestamp functionality"""
    # Create new record
    post = timestamped_post(title="Test Post", content="Test Content")
    post.save()

    # Verify timestamps exist and have correct type
    assert post.created_at is not None
    assert post.updated_at is not None
    assert isinstance(post.created_at, datetime)
    assert isinstance(post.updated_at, datetime)

    # Record initial timestamps
    original_created_at = post.created_at
    original_updated_at = post.updated_at

    # Wait a moment then update the record
    post.title = "Updated Title"
    time.sleep(0.1)
    post.save()

    # Verify timestamp updates
    assert post.created_at == original_created_at  # Creation time unchanged
    assert post.updated_at > original_updated_at  # Update time changed
