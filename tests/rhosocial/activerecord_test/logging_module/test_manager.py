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
        logger = get_logger("test_logger")
        assert logger.name == "test_logger"

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
        logger = config.get_logger("test")

        assert logger.name == "test"
        assert logger.level == logging.DEBUG
        assert logger.propagate is False

    def test_get_logger_propagate_setting(self):
        config = LoggingConfig(propagate=True)
        logger = config.get_logger("test_propagate")

        assert logger.propagate is True

    def test_auto_setup_adds_handler(self):
        config = LoggingConfig(auto_setup=True)
        logger = config.get_logger(f"test_auto_setup_{uuid.uuid4()}")

        assert len(logger.handlers) > 0
        assert any(isinstance(h, logging.StreamHandler) for h in logger.handlers)

    def test_auto_setup_false_no_handler(self):
        unique_name = f"test_no_auto_setup_{uuid.uuid4()}"

        config = LoggingConfig(auto_setup=False)
        logger = config.get_logger(unique_name)

        assert logger.propagate is False
        assert logger.handlers == []


class TestLoggingConfigThreadSafety:
    """Test thread safety of LoggingConfig cache operations."""

    def test_concurrent_get_summarizer_returns_consistent_results(self):
        """Concurrent get_summarizer() calls should return consistent results without errors."""
        import threading

        config = LoggingConfig()
        results = []
        errors = []

        def worker():
            try:
                s = config.get_summarizer()
                results.append(s)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker) for _ in range(20)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        assert all(r is results[0] for r in results)

    def test_concurrent_get_summarizer_with_logger_name(self):
        """Concurrent get_summarizer(logger_name) calls should not corrupt the dict."""
        import threading

        config = LoggingConfig()
        logger_names = [
            "rhosocial.activerecord.backend.sqlite",
            "rhosocial.activerecord.backend.mysql",
            "rhosocial.activerecord.model.User",
        ]
        errors = []

        def worker(name):
            try:
                config.get_summarizer(name)
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=worker, args=(name,)) for name in logger_names * 7]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        for name in logger_names:
            s1 = config.get_summarizer(name)
            s2 = config.get_summarizer(name)
            assert s1 is s2

    def test_concurrent_setattr_and_get_summarizer(self):
        """Concurrent summarizer_config changes and get_summarizer calls should not crash."""
        import threading
        from rhosocial.activerecord.logging import SummarizerConfig

        config = LoggingConfig()
        errors = []

        def reader():
            for _ in range(50):
                try:
                    config.get_summarizer()
                except Exception as e:
                    errors.append(e)

        def writer():
            for _ in range(10):
                config.summarizer_config = SummarizerConfig(max_string_length=20)

        threads = [
            threading.Thread(target=reader),
            threading.Thread(target=writer),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors

    def test_lock_prevents_stale_cache_after_config_change(self):
        """Cache should be cleared after summarizer_config change."""
        from rhosocial.activerecord.logging import SummarizerConfig

        config = LoggingConfig()
        original = config.get_summarizer()
        assert original.config.max_string_length == 100

        config.summarizer_config = SummarizerConfig(max_string_length=50)
        updated = config.get_summarizer()
        assert updated is not original
        assert updated.config.max_string_length == 50


class TestGetLoggerIdempotency:
    """Test that get_logger() is idempotent and does not overwrite on repeated calls."""

    def test_get_logger_does_not_overwrite_level_on_second_call(self):
        """Second get_logger() call should not overwrite user-customized level."""
        config = LoggingConfig(default_level=logging.DEBUG)
        name = f"test_idempotent_level_{uuid.uuid4()}"
        logging.getLogger(name).handlers.clear()

        logger = config.get_logger(name)
        assert logger.level == logging.DEBUG

        logger.setLevel(logging.WARNING)

        logger2 = config.get_logger(name)
        assert logger2 is logger
        assert logger2.level == logging.WARNING

    def test_get_logger_adds_handler_only_once(self):
        """auto_setup should only add a handler on the first get_logger() call."""
        config = LoggingConfig(auto_setup=True)
        name = f"test_handler_once_{uuid.uuid4()}"
        logging.getLogger(name).handlers.clear()

        logger1 = config.get_logger(name)
        handler_count = len(logger1.handlers)

        logger2 = config.get_logger(name)
        assert len(logger2.handlers) == handler_count

    def test_auto_setup_not_duplicated_in_log_method(self):
        """LoggingMixin.log() should not duplicate auto_setup handler addition."""
        from rhosocial.activerecord.logging.mixin import LoggingMixin

        class TestModel(LoggingMixin):
            pass

        TestModel.__logging_config__ = LoggingConfig(default_level=logging.DEBUG, auto_setup=True)
        logger = TestModel.get_logger()
        handler_count_before = len(logger.handlers)

        TestModel.log(logging.DEBUG, "test message")
        assert len(logger.handlers) == handler_count_before


class TestLoggerConfigCoverage:
    """Tests for LoggerConfig and LoggingConfig edge cases."""

    def test_logger_config_create_logger(self):
        """Test LoggerConfig.create_logger() method."""
        from rhosocial.activerecord.logging.config import LoggerConfig

        handler = logging.StreamHandler()
        config = LoggerConfig(
            name="test.logger_config.create",
            level=logging.WARNING,
            propagate=True,
            handlers=[handler],
        )
        logger = config.create_logger()
        assert logger.name == "test.logger_config.create"
        assert logger.level == logging.WARNING
        assert logger.propagate is True
        assert handler in logger.handlers

    def test_logging_config_get_logger_with_logger_config(self):
        """Test get_logger() with per-logger LoggerConfig."""
        from rhosocial.activerecord.logging import LoggingConfig
        from rhosocial.activerecord.logging.config import LoggerConfig

        handler = logging.StreamHandler()
        lc = LoggerConfig(
            name="test.per_logger.configured",
            level=logging.ERROR,
            propagate=True,
            handlers=[handler],
        )
        config = LoggingConfig(
            default_level=logging.DEBUG,
            loggers={"test.per_logger.configured": lc},
        )
        logger = config.get_logger("test.per_logger.configured")
        assert logger.level == logging.ERROR
        assert logger.propagate is True

    def test_logging_config_add_logger_config(self):
        """Test add_logger_config() method."""
        from rhosocial.activerecord.logging import LoggingConfig, LogDataMode
        from rhosocial.activerecord.logging.config import LoggerConfig

        config = LoggingConfig()
        lc = LoggerConfig(name="test.added_logger", log_data_mode=LogDataMode.KEYS_ONLY)
        config.add_logger_config(lc)

        assert "test.added_logger" in config.loggers
        summarizer = config.get_summarizer("test.added_logger")
        assert summarizer is not None

    def test_logging_config_resolve_log_data_mode_none_returns_summary(self):
        """When mode resolves to None, should default to SUMMARY."""
        from rhosocial.activerecord.logging import LoggingConfig, LogDataMode
        from rhosocial.activerecord.logging.config import LoggerConfig

        config = LoggingConfig(log_data_mode=LogDataMode.SUMMARY)
        lc = LoggerConfig(name="test.null_mode", log_data_mode=None)
        config.loggers["test.null_mode"] = lc

        # LoggerConfig has None log_data_mode, so falls back to global
        mode = config.resolve_log_data_mode("test.null_mode")
        assert mode == LogDataMode.SUMMARY

    def test_logging_config_get_summarizer_with_logger_specific_config(self):
        """get_summarizer() with logger_name should use LoggerConfig.summarizer_config."""
        from rhosocial.activerecord.logging import LoggingConfig, SummarizerConfig
        from rhosocial.activerecord.logging.config import LoggerConfig

        custom_sc = SummarizerConfig(max_string_length=42)
        lc = LoggerConfig(name="test.custom_summarizer", summarizer_config=custom_sc)
        config = LoggingConfig(loggers={"test.custom_summarizer": lc})

        summarizer = config.get_summarizer("test.custom_summarizer")
        assert summarizer.config.max_string_length == 42

    def test_logging_config_validate_log_data_mode(self):
        """_validate_log_data_mode should accept valid modes."""
        from rhosocial.activerecord.logging import LoggingConfig, LogDataMode

        config = LoggingConfig()
        # Should not raise
        config._validate_log_data_mode(LogDataMode.SUMMARY)
        config._validate_log_data_mode(None)
