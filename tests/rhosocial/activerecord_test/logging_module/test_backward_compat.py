# tests/rhosocial/activerecord_test/logging_module/test_backward_compat.py
"""Tests for backward compatibility of the logging system."""

import logging
import pytest

from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.logging import (
    configure_logging,
    get_logging_manager,
    LoggingMixin,
)


class TestBackwardCompatibility:
    """Test that existing API continues to work."""

    def test_dunder_logger_attribute_exists(self):
        """Test that __logger__ class attribute still exists."""
        assert hasattr(ActiveRecord, '__logger__')

    def test_set_logger_method_exists(self):
        """Test that set_logger method exists and works."""
        assert hasattr(ActiveRecord, 'set_logger')

        custom_logger = logging.getLogger('test_custom')
        ActiveRecord.set_logger(custom_logger)

        assert ActiveRecord.get_logger() is custom_logger

        # Reset to default
        ActiveRecord.set_logger(None)

    def test_get_logger_method_exists(self):
        """Test that get_logger method exists."""
        assert hasattr(ActiveRecord, 'get_logger')

        logger = ActiveRecord.get_logger()
        assert logger is not None
        assert isinstance(logger, logging.Logger)

    def test_log_method_exists(self):
        """Test that log method exists."""
        assert hasattr(ActiveRecord, 'log')

    def test_setup_logger_method_exists(self):
        """Test that setup_logger method exists."""
        assert hasattr(ActiveRecord, 'setup_logger')

    def test_log_method_works(self, caplog):
        """Test that log method works correctly."""
        manager = get_logging_manager()
        manager.reset()
        configure_logging(level=logging.DEBUG, propagate=True)

        logger = ActiveRecord.get_logger()

        with caplog.at_level(logging.DEBUG):
            logger.debug("Test message from ActiveRecord")

        assert "Test message from ActiveRecord" in caplog.text

    def test_logger_inheritance(self):
        """Test that LoggingMixin is properly inherited."""
        # ActiveRecord should inherit from LoggingMixin
        assert issubclass(ActiveRecord, LoggingMixin)

    def test_class_level_logger_override(self):
        """Test that setting __logger__ directly still works."""
        custom_logger = logging.getLogger('direct_set_test')

        # Store original
        original_logger = ActiveRecord.__logger__

        try:
            ActiveRecord.__logger__ = custom_logger
            assert ActiveRecord.get_logger() is custom_logger
        finally:
            # Restore
            ActiveRecord.__logger__ = original_logger

    def test_setup_logger_only_affects_own_logger(self):
        """Test that setup_logger only affects ActiveRecord logger, not root."""
        root_logger = logging.getLogger()
        original_formatter = None
        if root_logger.handlers:
            original_formatter = root_logger.handlers[0].formatter if root_logger.handlers else None

        # Call setup_logger
        ActiveRecord.setup_logger()

        # Root logger handlers should not be modified
        if root_logger.handlers and original_formatter:
            assert root_logger.handlers[0].formatter is original_formatter
