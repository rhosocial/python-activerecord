"""Tests for log level gating — ensuring expensive operations are skipped when level is disabled."""

import io
import logging
import time

import pytest

from rhosocial.activerecord.logging import LoggingConfig, SummarizerConfig
from rhosocial.activerecord.logging.mixin import LoggingMixin, BackendLoggingMixin
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend, SQLiteConnectionConfig


class TestLoggingMixinLevelGating:
    """Test that LoggingMixin skips expensive work when log level is disabled."""

    def test_log_no_output_when_level_disabled(self):
        class GatedModel(LoggingMixin):
            pass

        stream = io.StringIO()
        logger = logging.getLogger('test.gating.no_output')
        logger.handlers.clear()
        logger.setLevel(logging.WARNING)
        logger.propagate = False
        handler = logging.StreamHandler(stream)
        logger.addHandler(handler)

        GatedModel.__logging_config__ = LoggingConfig(default_level=logging.WARNING, auto_setup=False)
        GatedModel.set_logger(logger)

        try:
            GatedModel.log(logging.DEBUG, "This should not appear")
            assert stream.getvalue() == ""
        finally:
            GatedModel.set_logger(None)
            logger.handlers.clear()

    def test_log_produces_output_when_level_enabled(self):
        class GatedModel2(LoggingMixin):
            pass

        stream = io.StringIO()
        logger = logging.getLogger('test.gating.enabled')
        logger.handlers.clear()
        logger.setLevel(logging.DEBUG)
        logger.propagate = False
        handler = logging.StreamHandler(stream)
        logger.addHandler(handler)

        GatedModel2.__logging_config__ = LoggingConfig(default_level=logging.DEBUG, auto_setup=False)
        GatedModel2.set_logger(logger)

        try:
            GatedModel2.log(logging.DEBUG, "This should appear")
            assert "This should appear" in stream.getvalue()
        finally:
            GatedModel2.set_logger(None)
            logger.handlers.clear()

    def test_log_data_skips_summarization_when_level_disabled(self):
        class GatedModel3(LoggingMixin):
            pass

        stream = io.StringIO()
        logger = logging.getLogger('test.gating.log_data')
        logger.handlers.clear()
        logger.setLevel(logging.WARNING)
        logger.propagate = False
        handler = logging.StreamHandler(stream)
        logger.addHandler(handler)

        GatedModel3.__logging_config__ = LoggingConfig(default_level=logging.WARNING, auto_setup=False)
        GatedModel3.set_logger(logger)

        try:
            GatedModel3.log_data(logging.DEBUG, "Data", {"password": "secret"})
            assert stream.getvalue() == ""
        finally:
            GatedModel3.set_logger(None)
            logger.handlers.clear()

    def test_log_data_produces_output_when_level_enabled(self):
        class GatedModel4(LoggingMixin):
            pass

        stream = io.StringIO()
        logger = logging.getLogger('test.gating.log_data_enabled')
        logger.handlers.clear()
        logger.setLevel(logging.DEBUG)
        logger.propagate = False
        handler = logging.StreamHandler(stream)
        logger.addHandler(handler)

        GatedModel4.__logging_config__ = LoggingConfig(default_level=logging.DEBUG, auto_setup=False)
        GatedModel4.set_logger(logger)

        try:
            GatedModel4.log_data(logging.DEBUG, "Data", {"password": "secret"})
            output = stream.getvalue()
            assert "Data" in output
            assert "***MASKED***" in output
        finally:
            GatedModel4.set_logger(None)
            logger.handlers.clear()

    def test_log_performance_with_disabled_level(self):
        """Level gating should avoid frame walk, keeping disabled-level call overhead minimal."""
        class PerfModel(LoggingMixin):
            pass

        logger = logging.getLogger('test.gating.perf')
        logger.handlers.clear()
        logger.setLevel(logging.WARNING)
        logger.propagate = False

        PerfModel.__logging_config__ = LoggingConfig(default_level=logging.WARNING, auto_setup=False)
        PerfModel.set_logger(logger)

        try:
            start = time.monotonic()
            for _ in range(10000):
                PerfModel.log(logging.DEBUG, "skip this")
            elapsed = time.monotonic() - start
            assert elapsed < 2.0, f"10000 disabled log calls took {elapsed:.3f}s"
        finally:
            PerfModel.set_logger(None)
            logger.handlers.clear()


class TestBackendLoggingMixinLevelGating:
    """Test that BackendLoggingMixin skips expensive work when log level is disabled."""

    def test_backend_log_no_output_when_level_disabled(self):
        backend = SQLiteBackend(SQLiteConnectionConfig(database=":memory:"))
        try:
            logger_name = backend._get_logger_name()
            logger = logging.getLogger(logger_name)
            original_level = logger.level
            original_handlers = list(logger.handlers)
            logger.setLevel(logging.WARNING)
            logger.handlers.clear()

            stream = io.StringIO()
            handler = logging.StreamHandler(stream)
            logger.addHandler(handler)
            logger.propagate = False

            backend.log(logging.DEBUG, "This should not appear")
            assert stream.getvalue() == ""

            logger.setLevel(original_level)
            logger.handlers.clear()
            for h in original_handlers:
                logger.addHandler(h)
        finally:
            backend.disconnect()

    def test_backend_log_data_skips_summarization_when_level_disabled(self):
        backend = SQLiteBackend(SQLiteConnectionConfig(database=":memory:"))
        try:
            logger_name = backend._get_logger_name()
            logger = logging.getLogger(logger_name)
            original_level = logger.level
            original_handlers = list(logger.handlers)
            logger.setLevel(logging.WARNING)
            logger.handlers.clear()

            stream = io.StringIO()
            handler = logging.StreamHandler(stream)
            logger.addHandler(handler)
            logger.propagate = False

            backend.log_data(logging.DEBUG, "Query", {"password": "secret"})
            assert stream.getvalue() == ""

            logger.setLevel(original_level)
            logger.handlers.clear()
            for h in original_handlers:
                logger.addHandler(h)
        finally:
            backend.disconnect()


class TestBackendLoggingMixinParity:
    """Test that BackendLoggingMixin behavior matches LoggingMixin."""

    def test_backend_log_offset_parameter_accepted(self):
        backend = SQLiteBackend(SQLiteConnectionConfig(database=":memory:"))
        try:
            logger_name = backend._get_logger_name()
            logger = logging.getLogger(logger_name)
            original_level = logger.level
            original_handlers = list(logger.handlers)
            logger.setLevel(logging.DEBUG)
            logger.handlers.clear()

            stream = io.StringIO()
            handler = logging.StreamHandler(stream)
            logger.addHandler(handler)
            logger.propagate = False

            backend.log(logging.DEBUG, "With offset", offset=1)
            assert "With offset" in stream.getvalue()

            logger.setLevel(original_level)
            logger.handlers.clear()
            for h in original_handlers:
                logger.addHandler(h)
        finally:
            backend.disconnect()

    def test_backend_log_uses_level_name_method(self):
        """Backend log() should use level-name method lookup, consistent with LoggingMixin."""
        backend = SQLiteBackend(SQLiteConnectionConfig(database=":memory:"))
        try:
            logger_name = backend._get_logger_name()
            logger = logging.getLogger(logger_name)
            original_level = logger.level
            original_handlers = list(logger.handlers)
            logger.setLevel(logging.DEBUG)
            logger.handlers.clear()

            stream = io.StringIO()
            handler = logging.StreamHandler(stream)
            logger.addHandler(handler)
            logger.propagate = False

            backend.log(logging.DEBUG, "debug msg")
            backend.log(logging.INFO, "info msg")
            backend.log(logging.WARNING, "warning msg")

            output = stream.getvalue()
            assert "debug msg" in output
            assert "info msg" in output
            assert "warning msg" in output

            logger.setLevel(original_level)
            logger.handlers.clear()
            for h in original_handlers:
                logger.addHandler(h)
        finally:
            backend.disconnect()


class TestLoggingMixinCoverage:
    """Tests for LoggingMixin edge cases to improve coverage."""

    def test_set_logger_validates_type(self):
        """set_logger() should reject non-Logger objects."""
        from rhosocial.activerecord.logging.mixin import LoggingMixin

        class ValidatedModel(LoggingMixin):
            pass

        with pytest.raises(ValueError, match="logger must be an instance"):
            ValidatedModel.set_logger("not_a_logger")

    def test_set_logger_accepts_none(self):
        """set_logger(None) should clear the logger."""
        from rhosocial.activerecord.logging.mixin import LoggingMixin

        class NoneModel(LoggingMixin):
            pass

        NoneModel.set_logger(None)
        assert NoneModel.__logger__ is None

    def test_log_with_none_logger_returns(self):
        """log() with None logger should return immediately."""
        from rhosocial.activerecord.logging.mixin import LoggingMixin

        class NoneLoggerModel(LoggingMixin):
            pass

        NoneLoggerModel.set_logger(None)
        # Should not raise
        NoneLoggerModel.log(logging.DEBUG, "should not crash")

    def test_setup_formatter_modifies_handler(self):
        """setup_logger() should update handler formatters."""
        from rhosocial.activerecord.logging.mixin import LoggingMixin
        from rhosocial.activerecord.logging import LoggingConfig
        from rhosocial.activerecord.logging.formatter import ActiveRecordFormatter

        class FormatterModel(LoggingMixin):
            pass

        FormatterModel.__logging_config__ = LoggingConfig(auto_setup=True)
        logger = FormatterModel.get_logger()

        custom_formatter = ActiveRecordFormatter()
        FormatterModel.setup_logger(custom_formatter)

        for handler in logger.handlers:
            assert handler.formatter is custom_formatter

    def test_log_data_with_none_logger_returns(self):
        """log_data() with None logger should return immediately."""
        from rhosocial.activerecord.logging.mixin import LoggingMixin

        class NoLoggerModel(LoggingMixin):
            pass

        NoLoggerModel.set_logger(None)
        NoLoggerModel.log_data(logging.DEBUG, "msg", {"key": "val"})
        # Should not crash


class TestBackendLoggingMixinCoverage:
    """Tests for BackendLoggingMixin edge cases to improve coverage."""

    def test_backend_set_logger_validates_type(self):
        """Backend logger setter should reject non-Logger objects."""
        from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend, SQLiteConnectionConfig

        backend = SQLiteBackend(SQLiteConnectionConfig(database=":memory:"))
        try:
            with pytest.raises(ValueError, match="logger must be an instance"):
                backend.logger = "not_a_logger"
        finally:
            backend.disconnect()

    def test_backend_log_data_with_data(self):
        """Backend log_data() should produce output with summarized data."""
        from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend, SQLiteConnectionConfig

        backend = SQLiteBackend(SQLiteConnectionConfig(database=":memory:"))
        try:
            logger_name = backend._get_logger_name()
            logger = logging.getLogger(logger_name)
            original_level = logger.level
            original_handlers = list(logger.handlers)
            logger.setLevel(logging.DEBUG)
            logger.handlers.clear()

            stream = io.StringIO()
            handler = logging.StreamHandler(stream)
            logger.addHandler(handler)
            logger.propagate = False

            backend.log_data(logging.DEBUG, "Query", {"password": "secret"})
            output = stream.getvalue()
            assert "Query" in output
            assert "***MASKED***" in output

            logger.setLevel(original_level)
            logger.handlers.clear()
            for h in original_handlers:
                logger.addHandler(h)
        finally:
            backend.disconnect()
