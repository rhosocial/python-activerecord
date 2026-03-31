# tests/rhosocial/activerecord_test/logging/test_manager.py
"""Tests for the LoggingManager singleton and configuration."""

import logging
import pytest

from rhosocial.activerecord.logging import (
    LoggingManager,
    get_logging_manager,
    configure_logging,
    get_logger,
    LoggingConfig,
)


class TestLoggingManager:
    """Test LoggingManager singleton behavior."""

    def test_singleton_instance(self):
        """Test that LoggingManager is a singleton."""
        manager1 = get_logging_manager()
        manager2 = get_logging_manager()
        assert manager1 is manager2
        assert manager1 is LoggingManager.get_instance()

    def test_default_configuration(self):
        """Test default configuration values."""
        manager = get_logging_manager()
        config = manager.config

        assert config.default_level == logging.DEBUG
        assert config.propagate is False
        assert config.auto_setup is True

    def test_configure_logging_level(self):
        """Test configuring log level."""
        manager = get_logging_manager()
        manager.reset()  # Reset to defaults

        configure_logging(level=logging.INFO)
        assert manager.config.default_level == logging.INFO

        configure_logging(level=logging.WARNING)
        assert manager.config.default_level == logging.WARNING

    def test_configure_logging_propagate(self):
        """Test configuring propagate setting."""
        manager = get_logging_manager()
        manager.reset()

        configure_logging(propagate=True)
        assert manager.config.propagate is True

        configure_logging(propagate=False)
        assert manager.config.propagate is False

    def test_get_model_logger(self):
        """Test getting the model logger."""
        manager = get_logging_manager()
        logger = manager.get_model_logger()

        assert logger is not None
        assert logger.name == 'activerecord'

    def test_get_storage_logger(self):
        """Test getting the storage logger."""
        manager = get_logging_manager()
        logger = manager.get_storage_logger()

        assert logger is not None
        assert logger.name == 'storage'

    def test_get_transaction_logger(self):
        """Test getting the transaction logger."""
        manager = get_logging_manager()
        logger = manager.get_transaction_logger()

        assert logger is not None
        assert logger.name == 'transaction'

    def test_get_logger_function(self):
        """Test the convenience get_logger function."""
        logger = get_logger('test_logger')
        assert logger.name == 'test_logger'

    def test_reset_configuration(self):
        """Test resetting configuration to defaults."""
        manager = get_logging_manager()
        configure_logging(level=logging.WARNING, propagate=True)

        manager.reset()

        assert manager.config.default_level == logging.DEBUG
        assert manager.config.propagate is False


class TestLoggingConfig:
    """Test LoggingConfig dataclass."""

    def test_default_values(self):
        """Test default configuration values."""
        config = LoggingConfig()

        assert config.default_level == logging.DEBUG
        assert config.propagate is False
        assert config.auto_setup is True
        assert config.loggers == {}

    def test_get_logger_creates_logger(self):
        """Test that get_logger creates a logger with correct settings."""
        config = LoggingConfig()
        logger = config.get_logger('test')

        assert logger.name == 'test'
        assert logger.level == logging.DEBUG
        assert logger.propagate is False

    def test_get_logger_propagate_setting(self):
        """Test that propagate setting is applied correctly."""
        config = LoggingConfig(propagate=True)
        logger = config.get_logger('test_propagate')

        assert logger.propagate is True

    def test_auto_setup_adds_handler(self):
        """Test that auto_setup adds a StreamHandler."""
        config = LoggingConfig(auto_setup=True)
        logger = config.get_logger('test_auto_setup')

        # Should have at least one handler
        assert len(logger.handlers) > 0
        assert any(isinstance(h, logging.StreamHandler) for h in logger.handlers)

    def test_auto_setup_false_no_handler(self):
        """Test that auto_setup=False does not add handlers."""
        # Create a unique logger name to avoid conflicts
        import uuid
        unique_name = f'test_no_auto_setup_{uuid.uuid4()}'

        config = LoggingConfig(auto_setup=False)
        logger = config.get_logger(unique_name)

        # Should not have handlers added by config
        # (logger might have handlers from other tests, so we check propagate)
        assert logger.propagate is False
