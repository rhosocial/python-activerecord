# tests/rhosocial/activerecord_test/logging/test_isolation.py
"""Tests to verify logging isolation - that ActiveRecord does not modify root logger."""

import logging

import pytest

from rhosocial.activerecord.logging import (
    configure_logging,
    get_logger,
    reset_default_logging_config,
    ActiveRecordFormatter,
    LoggingConfig,
)
from rhosocial.activerecord.logging.mixin import BackendLoggingMixin, LoggingMixin


class TestLoggingIsolation:
    """Test that ActiveRecord logging does not pollute the root logger."""

    @pytest.fixture(autouse=True)
    def reset_logging_state(self):
        reset_default_logging_config()
        original_model_config = LoggingMixin.__logging_config__
        original_backend_config = BackendLoggingMixin.__logging_config__
        LoggingMixin.__logging_config__ = LoggingConfig()
        BackendLoggingMixin.__logging_config__ = LoggingConfig()
        yield
        reset_default_logging_config()
        LoggingMixin.__logging_config__ = original_model_config
        BackendLoggingMixin.__logging_config__ = original_backend_config

    def test_setup_logger_does_not_modify_root(self):
        """Test that setup_logger does not modify root logger handlers."""
        root_logger = logging.getLogger()
        original_handlers = list(root_logger.handlers)

        # Explicit per-owner config so the handler requirement is unambiguous.
        model_config = LoggingConfig(default_level=logging.DEBUG, auto_setup=True)
        model_logger = model_config.get_logger("rhosocial.activerecord.model")
        model_logger.handlers[0].setFormatter(ActiveRecordFormatter())

        assert list(root_logger.handlers) == original_handlers
        model_logger.handlers.clear()
        model_logger.setLevel(logging.NOTSET)

    def test_propagate_true_by_default(self):
        """Test that loggers propagate to the application's root logger by default."""
        model_logger = LoggingMixin.__logging_config__.get_logger("rhosocial.activerecord.model")
        storage_logger = BackendLoggingMixin.__logging_config__.get_logger("rhosocial.activerecord.backend")

        assert model_logger.propagate is True
        assert storage_logger.propagate is True

    def test_propagate_can_be_disabled_for_framework_default(self):
        """Test that framework-level propagation can be disabled if a user wants it."""
        configure_logging(propagate=False)

        logger = get_logger("test_propagate_disabled")
        assert logger.propagate is False

    def test_root_logger_not_affected_by_framework_logging(self, caplog):
        """Test that framework logs don't appear in root logger when propagate=False."""
        configure_logging(propagate=False, level=logging.DEBUG)

        logger = get_logger("test_isolation_check")

        with caplog.at_level(logging.DEBUG):
            logger.debug("Test debug message")

        assert "Test debug message" not in caplog.text

    def test_custom_logger_not_modified_by_activerecord(self):
        """Test that a custom logger is not modified by ActiveRecord."""
        custom_logger = logging.getLogger("my_custom_app")
        custom_logger.setLevel(logging.WARNING)
        original_level = custom_logger.level

        LoggingMixin.__logging_config__ = LoggingConfig(default_level=logging.DEBUG)

        assert custom_logger.level == original_level

        ar_logger = LoggingMixin.__logging_config__.get_logger("rhosocial.activerecord.model")
        assert ar_logger.level == logging.DEBUG
