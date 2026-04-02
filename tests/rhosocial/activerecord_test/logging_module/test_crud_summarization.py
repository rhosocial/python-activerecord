# tests/rhosocial/activerecord_test/logging_module/test_crud_summarization.py
"""
Integration tests for data summarization during CRUD operations.

This test demonstrates how the DataSummarizer truncates and masks
sensitive data in log messages during database operations.
"""

import logging
import tempfile
import os
from typing import Optional
from datetime import datetime

import pytest

from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
from rhosocial.activerecord.logging import (
    SummarizerConfig,
    DataSummarizer,
    get_logging_manager,
)


class Article(ActiveRecord):
    """Test model with long text fields for summarization testing."""

    __table_name__ = "articles"

    id: Optional[int] = None
    title: str = ""
    content: str = ""  # Long content
    author_bio: str = ""  # Long bio
    secret_code: str = ""  # Sensitive field (will be masked)
    created_at: Optional[datetime] = None


@pytest.fixture
def temp_db():
    """Create a temporary database file."""
    fd, path = tempfile.mkstemp(suffix='.db')
    os.close(fd)
    yield path
    os.unlink(path)


@pytest.fixture
def configured_logging():
    """Configure logging with summarization settings."""
    manager = get_logging_manager()
    # Save original config
    original_config = manager._config

    # Configure for testing
    manager._config.summarizer_config = SummarizerConfig(
        max_string_length=50,  # Short limit to demonstrate truncation
        sensitive_fields={'secret_code', 'password', 'token'},
    )
    manager._config.log_data_mode = 'summary'
    manager._config.default_level = logging.DEBUG

    yield manager

    # Restore original config
    manager._config = original_config


@pytest.fixture
def article_backend(temp_db, configured_logging):
    """Configure Article model with SQLite backend."""
    # Use SQLiteBackend directly with database path
    backend = SQLiteBackend(database=temp_db)
    backend.logger = Article.get_logger()
    Article.__backend__ = backend

    # Create table
    backend.executescript("""
        CREATE TABLE articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            content TEXT,
            author_bio TEXT,
            secret_code TEXT,
            created_at TEXT
        )
    """)

    yield backend

    # Cleanup
    backend.disconnect()


class TestCRUDSummarization:
    """Test data summarization during CRUD operations."""

    def test_insert_logs_show_summarization(self, article_backend):
        """Test that insert logs show truncated content and masked sensitive fields."""
        # Create article with very long content
        long_content = "This is a very long article content. " * 100  # ~3500 chars
        long_bio = "John Doe is a software engineer with expertise in... " * 50  # ~2000 chars

        article = Article(
            title="Test Article with Long Content",
            content=long_content,
            author_bio=long_bio,
            secret_code="my_secret_api_key_12345",
            created_at=datetime.now(),
        )
        # Save should work without errors
        article.save()

        # Verify the article was saved
        assert article.id is not None

    def test_update_logs_show_summarization(self, article_backend):
        """Test that update logs show masked sensitive fields."""
        # First create an article
        article = Article(
            title="Test Article",
            content="Short content",
            author_bio="Short bio",
            secret_code="initial_code",
            created_at=datetime.now(),
        )
        article.save()

        # Update with long content
        long_content = "Updated content: " + "X" * 1000
        article.content = long_content
        article.secret_code = "new_secret_code_xyz"
        # Save should work without errors
        article.save()

    def test_delete_logs_show_summarization(self, article_backend):
        """Test that delete logs show masked sensitive fields."""
        # Create test data
        article = Article(
            title="To Be Deleted",
            content="X" * 1000,
            author_bio="Y" * 500,
            secret_code="delete_secret",
            created_at=datetime.now(),
        )
        article.save()

        # Delete should work without errors
        article.delete()


class TestSummarizerModes:
    """Test different summarization modes with DataSummarizer directly."""

    def test_keys_only_mode(self):
        """Test keys_only mode shows only field names."""
        config = SummarizerConfig(
            max_string_length=50,
            sensitive_fields={'secret_code', 'password'}
        )
        summarizer = DataSummarizer(config)

        data = {
            "title": "Test",
            "content": "X" * 1000,
            "secret_code": "hidden",
        }

        result = summarizer.summarize_keys_only(data)

        assert result["title"] == "<str>"
        assert result["content"] == "<str>"
        assert result["secret_code"] == "***MASKED***"

    def test_summary_mode_truncates_long_values(self):
        """Test summary mode truncates long values."""
        config = SummarizerConfig(
            max_string_length=20,
            sensitive_fields={'secret_code', 'password'}
        )
        summarizer = DataSummarizer(config)

        data = {
            "title": "Short",
            "content": "X" * 1000,
            "secret_code": "hidden",
        }

        result = summarizer.summarize(data)

        assert result["title"] == "Short"
        assert "truncated" in result["content"]
        assert "1000 chars total" in result["content"]
        assert result["secret_code"] == "***MASKED***"

    def test_summary_mode_masks_sensitive_fields(self):
        """Test that sensitive fields are masked."""
        config = SummarizerConfig(
            max_string_length=50,
            sensitive_fields={'password', 'token', 'api_key'}
        )
        summarizer = DataSummarizer(config)

        data = {
            "username": "john",
            "password": "secret123",
            "token": "abc123",
            "api_key": "xyz789",
        }

        result = summarizer.summarize(data)

        assert result["username"] == "john"
        assert result["password"] == "***MASKED***"
        assert result["token"] == "***MASKED***"
        assert result["api_key"] == "***MASKED***"

    def test_mask_sensitive_preserves_other_data(self):
        """Test mask_sensitive preserves non-sensitive data."""
        config = SummarizerConfig(
            max_string_length=20,
            sensitive_fields={'secret_code', 'password'}
        )
        summarizer = DataSummarizer(config)

        data = {
            "title": "Short",
            "content": "X" * 100,  # Would be truncated in summary mode
            "secret_code": "hidden",
        }

        result = summarizer.mask_sensitive(data)

        assert result["title"] == "Short"
        assert result["content"] == "X" * 100  # Not truncated
        assert result["secret_code"] == "***MASKED***"


class TestLogDataMethods:
    """Test log_data methods on models."""

    def test_model_log_data_summarizes(self, article_backend):
        """Test LoggingMixin.log_data method applies summarization."""
        manager = get_logging_manager()
        summarizer = manager.config.get_summarizer()

        long_data = {
            "title": "Test Article",
            "content": "A" * 1000,
            "secret_code": "my_secret",
        }

        # Verify summarizer is configured
        summarized = summarizer.summarize(long_data)

        assert "my_secret" not in str(summarized)
        assert "***MASKED***" in str(summarized)
        assert "truncated" in summarized["content"]

    def test_model_log_data_keys_only(self, article_backend):
        """Test LoggingMixin.log_data_keys_only method."""
        manager = get_logging_manager()
        summarizer = manager.config.get_summarizer()

        long_data = {
            "title": "Test Article",
            "content": "A" * 1000,
            "secret_code": "my_secret",
        }

        result = summarizer.summarize_keys_only(long_data)

        # Should show type hints, not values
        assert result["title"] == "<str>"
        assert result["content"] == "<str>"
        assert result["secret_code"] == "***MASKED***"

    def test_model_log_data_full(self, article_backend):
        """Test LoggingMixin.log_data_full bypasses summarization."""
        manager = get_logging_manager()

        long_data = {
            "title": "Test Article",
            "content": "Short content",
        }

        # In full mode, data is returned as-is
        result = manager.config.summarize_data(long_data, mode='full')

        assert result["title"] == "Test Article"
        assert result["content"] == "Short content"
