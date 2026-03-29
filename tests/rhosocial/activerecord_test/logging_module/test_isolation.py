# tests/rhosocial/activerecord_test/logging/test_isolation.py
"""Tests to verify logging isolation - that ActiveRecord does not modify root logger."""

import logging
import pytest

from rhosocial.activerecord.logging import (
    configure_logging,
    get_logging_manager,
    ActiveRecordFormatter,
)


class TestLoggingIsolation:
    """Test that ActiveRecord logging does not pollute the root logger."""

    def test_setup_logger_does_not_modify_root(self):
        """Test that setup_logger does not modify root logger handlers."""
        # Get the root logger
        root_logger = logging.getLogger()

        # Store original handlers
        original_handlers = list(root_logger.handlers)

        # Configure ActiveRecord logging
        manager = get_logging_manager()
        manager.reset()

        configure_logging(
            level=logging.DEBUG,
            formatter=ActiveRecordFormatter()
        )

        # Get a model logger
        model_logger = manager.get_model_logger()

        # Setup the logger (this should NOT modify root)
        model_logger.handlers[0].setFormatter(ActiveRecordFormatter())

        # Root logger should have same handlers as before
        assert list(root_logger.handlers) == original_handlers

    def test_propagate_false_by_default(self):
        """Test that loggers do not propagate to root by default."""
        manager = get_logging_manager()
        manager.reset()

        model_logger = manager.get_model_logger()
        storage_logger = manager.get_storage_logger()

        assert model_logger.propagate is False
        assert storage_logger.propagate is False

    def test_propagate_can_be_enabled(self):
        """Test that propagate can be enabled if user wants it."""
        manager = get_logging_manager()
        manager.reset()

        configure_logging(propagate=True)

        logger = manager.get_logger('test_propagate_enabled')
        assert logger.propagate is True

    def test_root_logger_not_affected_by_activerecord_logging(self, caplog):
        """Test that ActiveRecord logs don't appear in root logger when propagate=False."""
        manager = get_logging_manager()
        manager.reset()

        # Ensure propagate is False
        configure_logging(propagate=False, level=logging.DEBUG)

        # Get a logger and log something
        logger = manager.get_logger('test_isolation_check')

        with caplog.at_level(logging.DEBUG):
            logger.debug("Test debug message")

        # The message should not be in caplog because propagate=False
        # caplog captures from root logger, and if propagate=False,
        # the log won't reach root
        assert "Test debug message" not in caplog.text

    def test_custom_logger_not_modified_by_activerecord(self):
        """Test that a custom logger is not modified by ActiveRecord."""
        # Create a custom logger
        custom_logger = logging.getLogger('my_custom_app')
        custom_logger.setLevel(logging.WARNING)
        original_level = custom_logger.level

        # Configure ActiveRecord logging
        manager = get_logging_manager()
        manager.reset()
        configure_logging(level=logging.DEBUG)

        # Custom logger should not be affected
        assert custom_logger.level == original_level

        # ActiveRecord logger should have DEBUG level
        ar_logger = manager.get_model_logger()
        assert ar_logger.level == logging.DEBUG
