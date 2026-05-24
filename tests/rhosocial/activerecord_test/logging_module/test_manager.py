# tests/rhosocial/activerecord_test/logging/test_manager.py
"""Tests for logging defaults and configuration."""

import logging
import uuid

import pytest

from rhosocial.activerecord.logging import (
    configure_logging,
    get_default_logging_config,
    get_logger,
    reset_default_logging_config,
    LoggingConfig,
)
from rhosocial.activerecord.logging.mixin import BackendLoggingMixin, LoggingMixin


class TestLoggingDefaults:
    """Test framework-level logging defaults."""

    @pytest.fixture(autouse=True)
    def reset_defaults(self):
        reset_default_logging_config()
        original_model_config = LoggingMixin.__logging_config__
        original_backend_config = BackendLoggingMixin.__logging_config__
        LoggingMixin.__logging_config__ = LoggingConfig()
        BackendLoggingMixin.__logging_config__ = LoggingConfig()
        yield
        reset_default_logging_config()
        LoggingMixin.__logging_config__ = original_model_config
        BackendLoggingMixin.__logging_config__ = original_backend_config

    def test_default_configuration(self):
        config = get_default_logging_config()

        assert config.default_level == logging.DEBUG
        assert config.propagate is False
        assert config.auto_setup is True

    def test_configure_logging_level(self):
        configure_logging(level=logging.INFO)
        assert get_default_logging_config().default_level == logging.INFO

        configure_logging(level=logging.WARNING)
        assert get_default_logging_config().default_level == logging.WARNING

    def test_configure_logging_propagate(self):
        configure_logging(propagate=True)
        assert get_default_logging_config().propagate is True

        configure_logging(propagate=False)
        assert get_default_logging_config().propagate is False

    def test_get_logger_function(self):
        logger = get_logger('test_logger')
        assert logger.name == 'test_logger'

    def test_reset_configuration(self):
        configure_logging(level=logging.WARNING, propagate=True)

        reset_default_logging_config()

        assert get_default_logging_config().default_level == logging.DEBUG
        assert get_default_logging_config().propagate is False

    def test_logging_manager_public_api_removed(self):
        import rhosocial.activerecord.logging as logging_module

        assert not hasattr(logging_module, "LoggingManager")
        assert not hasattr(logging_module, "get_logging_manager")

    def test_activerecord_default_config_is_independent_from_framework_default(self):
        configure_logging(level=logging.ERROR)
        LoggingMixin.__logging_config__ = LoggingConfig(default_level=logging.INFO)

        assert get_default_logging_config().default_level == logging.ERROR
        assert LoggingMixin.get_logging_config().default_level == logging.INFO

    def test_backend_default_config_is_independent_from_activerecord_default(self):
        LoggingMixin.__logging_config__ = LoggingConfig(default_level=logging.INFO)
        BackendLoggingMixin.__logging_config__ = LoggingConfig(default_level=logging.WARNING)

        assert LoggingMixin.get_logging_config().default_level == logging.INFO
        assert BackendLoggingMixin.__logging_config__.default_level == logging.WARNING


class TestLoggingConfig:
    """Test LoggingConfig dataclass."""

    def test_default_values(self):
        config = LoggingConfig()

        assert config.default_level == logging.DEBUG
        assert config.propagate is False
        assert config.auto_setup is True
        assert config.loggers == {}

    def test_get_logger_creates_logger(self):
        config = LoggingConfig()
        logger = config.get_logger('test')

        assert logger.name == 'test'
        assert logger.level == logging.DEBUG
        assert logger.propagate is False

    def test_get_logger_propagate_setting(self):
        config = LoggingConfig(propagate=True)
        logger = config.get_logger('test_propagate')

        assert logger.propagate is True

    def test_auto_setup_adds_handler(self):
        config = LoggingConfig(auto_setup=True)
        logger = config.get_logger(f'test_auto_setup_{uuid.uuid4()}')

        assert len(logger.handlers) > 0
        assert any(isinstance(h, logging.StreamHandler) for h in logger.handlers)

    def test_auto_setup_false_no_handler(self):
        unique_name = f'test_no_auto_setup_{uuid.uuid4()}'

        config = LoggingConfig(auto_setup=False)
        logger = config.get_logger(unique_name)

        assert logger.propagate is False
        assert logger.handlers == []
