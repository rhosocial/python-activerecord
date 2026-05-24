# tests/rhosocial/activerecord_test/logging_module/test_defaults.py
"""Tests for logging.defaults module — configure_logging, reset, and get_logger."""

import logging

import pytest

from rhosocial.activerecord.logging import (
    LoggingConfig,
    ActiveRecordFormatter,
    configure_logging,
    get_default_logging_config,
    get_logger,
    reset_default_logging_config,
)
from rhosocial.activerecord.logging.mixin import BackendLoggingMixin, LoggingMixin


class TestConfigureLoggingFormatter:
    """Cover the formatter branch in configure_logging."""

    @pytest.fixture(autouse=True)
    def reset(self):
        reset_default_logging_config()
        yield
        reset_default_logging_config()

    def test_configure_logging_formatter(self):
        formatter = ActiveRecordFormatter("%(name)s - %(message)s")
        configure_logging(formatter=formatter)
        config = get_default_logging_config()
        assert config.formatter is formatter


class TestConfigureLoggingAutoSetup:
    """Cover the auto_setup branch in configure_logging."""

    @pytest.fixture(autouse=True)
    def reset(self):
        reset_default_logging_config()
        yield
        reset_default_logging_config()

    def test_configure_logging_auto_setup_false(self):
        configure_logging(auto_setup=False)
        config = get_default_logging_config()
        assert config.auto_setup is False

    def test_configure_logging_auto_setup_true(self):
        configure_logging(auto_setup=True)
        config = get_default_logging_config()
        assert config.auto_setup is True


class TestConfigureLoggingAllParams:
    """Cover configure_logging with all parameters set at once."""

    @pytest.fixture(autouse=True)
    def reset(self):
        reset_default_logging_config()
        yield
        reset_default_logging_config()

    def test_configure_logging_all_parameters(self):
        formatter = ActiveRecordFormatter("[%(levelname)s] %(message)s")
        configure_logging(
            level=logging.WARNING,
            formatter=formatter,
            propagate=True,
            auto_setup=False,
        )
        config = get_default_logging_config()
        assert config.default_level == logging.WARNING
        assert config.formatter is formatter
        assert config.propagate is True
        assert config.auto_setup is False

    def test_configure_logging_none_params_are_noop(self):
        """Passing None for all params should not change defaults."""
        configure_logging(level=None, formatter=None, propagate=None, auto_setup=None)
        config = get_default_logging_config()
        assert config.default_level == logging.DEBUG
        assert config.propagate is False
        assert config.auto_setup is True


class TestResetDefaultLoggingConfig:
    """Cover reset_default_logging_config resetting all fields."""

    @pytest.fixture(autouse=True)
    def reset(self):
        reset_default_logging_config()
        yield
        reset_default_logging_config()

    def test_reset_restores_defaults_after_full_configure(self):
        formatter = ActiveRecordFormatter("%(message)s")
        configure_logging(
            level=logging.ERROR,
            formatter=formatter,
            propagate=True,
            auto_setup=False,
        )

        reset_default_logging_config()

        config = get_default_logging_config()
        assert config.default_level == logging.DEBUG
        assert config.propagate is False
        assert config.auto_setup is True
        assert config.formatter is not formatter


class TestGetLoggerFromDefaults:
    """Cover get_logger() function using framework-level defaults."""

    @pytest.fixture(autouse=True)
    def reset(self):
        reset_default_logging_config()
        yield
        reset_default_logging_config()

    def test_get_logger_returns_configured_logger(self):
        configure_logging(level=logging.WARNING)
        logger = get_logger("test_defaults_logger")
        assert logger.name == "test_defaults_logger"
        assert logger.level == logging.WARNING

    def test_get_logger_with_custom_formatter(self):
        formatter = ActiveRecordFormatter("CUSTOM: %(message)s")
        configure_logging(formatter=formatter, auto_setup=True)
        logger = get_logger("test_defaults_formatter")
        assert any(
            isinstance(h, logging.StreamHandler) and h.formatter is formatter
            for h in logger.handlers
        )
