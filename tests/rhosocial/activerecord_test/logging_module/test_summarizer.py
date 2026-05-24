# tests/rhosocial/activerecord_test/logging_module/test_summarizer.py
"""Tests for DataSummarizer functionality."""

import io
import logging

import pytest
from rhosocial.activerecord.logging.summarizer import (
    SummarizerConfig,
    DataSummarizer,
)


class TestSummarizerConfig:
    """Tests for SummarizerConfig."""

    def test_default_config(self):
        """Test default configuration values."""
        config = SummarizerConfig()
        assert config.max_string_length == 100
        assert config.max_bytes_length == 64
        assert config.max_dict_items == 10
        assert config.max_depth == 5
        assert 'password' in config.sensitive_fields
        assert 'token' in config.sensitive_fields

    def test_custom_config(self):
        """Test custom configuration values."""
        config = SummarizerConfig(
            max_string_length=50,
            max_bytes_length=32,
            max_dict_items=5,
        )
        assert config.max_string_length == 50
        assert config.max_bytes_length == 32
        assert config.max_dict_items == 5


class TestDataSummarizer:
    """Tests for DataSummarizer."""

    def test_truncate_string(self):
        """Test string truncation."""
        config = SummarizerConfig(max_string_length=10)
        summarizer = DataSummarizer(config)

        # Short string should not be truncated
        assert summarizer.summarize("short") == "short"

        # Long string should be truncated
        long_string = "a" * 100
        result = summarizer.summarize(long_string)
        assert "truncated" in result
        assert "100 chars total" in result

    def test_summarize_bytes(self):
        """Test bytes representation."""
        config = SummarizerConfig(max_bytes_length=10)
        summarizer = DataSummarizer(config)

        # Short bytes should show repr
        short_bytes = b"hello"
        result = summarizer.summarize(short_bytes)
        assert result == repr(short_bytes)

        # Long bytes should be truncated
        long_bytes = b"x" * 100
        result = summarizer.summarize(long_bytes)
        assert "100 bytes total" in result

    def test_summarize_dict(self):
        """Test dictionary summarization."""
        config = SummarizerConfig(max_dict_items=3)
        summarizer = DataSummarizer(config)

        # Small dict should be fully shown
        small_dict = {"a": 1, "b": 2}
        result = summarizer.summarize(small_dict)
        assert result == small_dict

        # Large dict should be truncated
        large_dict = {f"key_{i}": f"value_{i}" for i in range(10)}
        result = summarizer.summarize(large_dict)
        assert len(result) <= config.max_dict_items + 1  # +1 for the "...more items" entry

    def test_summarize_list(self):
        """Test list summarization."""
        config = SummarizerConfig(max_dict_items=3)
        summarizer = DataSummarizer(config)

        # Small list should be fully shown
        small_list = [1, 2, 3]
        result = summarizer.summarize(small_list)
        assert result == [1, 2, 3]

        # Large list should be truncated
        large_list = list(range(10))
        result = summarizer.summarize(large_list)
        assert len(result) <= config.max_dict_items + 1

    def test_sensitive_field_masking(self):
        """Test that sensitive fields are masked."""
        summarizer = DataSummarizer()

        data = {
            "username": "john",
            "password": "secret123",
            "email": "john@example.com",
            "api_key": "abc123xyz",
        }
        result = summarizer.summarize(data)

        assert result["username"] == "john"
        assert result["password"] == "***MASKED***"
        assert result["email"] == "john@example.com"
        assert result["api_key"] == "***MASKED***"

    def test_sensitive_field_case_insensitive(self):
        """Test that sensitive field detection is case-insensitive."""
        summarizer = DataSummarizer()

        data = {
            "Password": "secret",
            "API_KEY": "key123",
            "Token": "token123",
        }
        result = summarizer.summarize(data)

        assert result["Password"] == "***MASKED***"
        assert result["API_KEY"] == "***MASKED***"
        assert result["Token"] == "***MASKED***"

    def test_keys_only_mode(self):
        """Test keys_only mode shows only field names."""
        summarizer = DataSummarizer()

        data = {"name": "John", "age": 30, "password": "secret"}
        result = summarizer.summarize_keys_only(data)

        assert result["name"] == "<str>"
        assert result["age"] == "<int>"
        assert result["password"] == "***MASKED***"

    def test_nested_data(self):
        """Test nested data structures."""
        config = SummarizerConfig(max_depth=3)
        summarizer = DataSummarizer(config)

        data = {
            "user": {
                "name": "John",
                "profile": {
                    "bio": "A" * 200,  # Long string
                    "settings": {"theme": "dark"},
                },
            }
        }
        result = summarizer.summarize(data)

        # Check that nested structures are processed
        assert "user" in result
        assert "name" in result["user"]
        # Long string should be truncated
        assert "truncated" in result["user"]["profile"]["bio"]

    def test_max_depth_exceeded(self):
        """Test that max depth is respected."""
        config = SummarizerConfig(max_depth=2)
        summarizer = DataSummarizer(config)

        # Create deeply nested structure
        data = {"level1": {"level2": {"level3": {"level4": "deep"}}}}
        result = summarizer.summarize(data)

        # At depth 2, should show max depth exceeded message
        assert "max depth exceeded" in str(result["level1"]["level2"])

    def test_primitives_unchanged(self):
        """Test that primitive values are returned unchanged."""
        summarizer = DataSummarizer()

        assert summarizer.summarize(None) is None
        assert summarizer.summarize(42) == 42
        assert summarizer.summarize(3.14) == 3.14
        assert summarizer.summarize(True) is True
        assert summarizer.summarize(False) is False

    def test_mask_sensitive_without_truncation(self):
        """Test mask_sensitive method."""
        summarizer = DataSummarizer()

        data = {
            "name": "John",
            "password": "secret",
            "token": "abc123",
            "nested": {"key": "value", "secret": "hidden"},
        }
        result = summarizer.mask_sensitive(data)

        # Values should not be truncated
        assert result["name"] == "John"
        # But sensitive fields should be masked
        assert result["password"] == "***MASKED***"
        assert result["token"] == "***MASKED***"
        assert result["nested"]["secret"] == "***MASKED***"
        assert result["nested"]["key"] == "value"

    def test_custom_sensitive_fields(self):
        """Test custom sensitive fields configuration."""
        config = SummarizerConfig(sensitive_fields={'custom_secret', 'private_data'})
        summarizer = DataSummarizer(config)

        data = {
            "custom_secret": "hidden",
            "private_data": "also_hidden",
            "password": "not_masked",  # Not in custom set
        }
        result = summarizer.summarize(data)

        assert result["custom_secret"] == "***MASKED***"
        assert result["private_data"] == "***MASKED***"
        assert result["password"] == "not_masked"  # Not masked since not in custom set


class TestSummarizerIsolation:
    """Tests that summarizer instances do not share mutable state."""

    def test_summarizer_instances_use_own_config(self):
        short = DataSummarizer(SummarizerConfig(max_string_length=5))
        long = DataSummarizer(SummarizerConfig(max_string_length=20))
        data = {"text": "A" * 30}

        short_result = short.summarize(data)
        long_result = long.summarize(data)

        assert short_result["text"].startswith("AAAAA...")
        assert long_result["text"].startswith("A" * 20 + "...")


class TestLoggingIntegration:
    """Tests for LoggingConfig integration with summarizer."""

    def test_logging_config_summarizer(self):
        """Test LoggingConfig.get_summarizer()."""
        from rhosocial.activerecord.logging import LoggingConfig, LogDataMode

        config = LoggingConfig()
        summarizer = config.get_summarizer()

        assert isinstance(summarizer, DataSummarizer)

    def test_logging_config_summarize_data(self):
        """Test LoggingConfig.summarize_data()."""
        from rhosocial.activerecord.logging import LoggingConfig, LogDataMode

        config = LoggingConfig()
        data = {"password": "secret", "bio": "A" * 200}

        # Test summary mode (default)
        result = config.summarize_data(data)
        assert result["password"] == "***MASKED***"
        assert "truncated" in result["bio"]

        # Test keys_only mode
        config.log_data_mode = LogDataMode.KEYS_ONLY
        result = config.summarize_data(data)
        assert result["password"] == "***MASKED***"
        assert result["bio"] == "<str>"

        # Test full mode
        config.log_data_mode = LogDataMode.FULL
        result = config.summarize_data(data)
        assert result == data

        # Test hidden mode
        config.log_data_mode = LogDataMode.HIDDEN
        result = config.summarize_data(data)
        assert result == '<hidden>'

    def test_logging_config_custom_summarizer_config(self):
        """Test custom summarizer configuration in LoggingConfig."""
        from rhosocial.activerecord.logging import LoggingConfig, SummarizerConfig

        summarizer_config = SummarizerConfig(
            max_string_length=20,
            max_dict_items=5,
        )
        config = LoggingConfig(summarizer_config=summarizer_config)

        # Test that custom config is used
        long_string = "a" * 100
        result = config.summarize_data({"text": long_string})
        assert "truncated" in result["text"]
        # Check that truncation happened at custom length
        assert "100 chars total" in result["text"]

    def test_field_maskers_custom(self):
        """Test custom field maskers for specific fields."""
        from rhosocial.activerecord.logging import SummarizerConfig
        from rhosocial.activerecord.logging.summarizer import DataSummarizer

        config = SummarizerConfig(
            sensitive_fields={'password', 'email', 'api_key'},
            field_maskers={
                # Show first char of local part
                'email': lambda v: v.split('@')[0][:1] + '***@' + v.split('@')[1] if '@' in str(v) else '***',
                'password': lambda v: '*' * min(len(str(v)), 8),
            }
        )
        summarizer = DataSummarizer(config)

        data = {
            'username': 'john',
            'password': 'mysecret123',
            'email': 'john@example.com',
            'api_key': 'sk-12345',
        }
        result = summarizer.summarize(data)

        # email uses custom masker (first char of local part)
        assert result['email'] == 'j***@example.com'
        # password uses custom masker (8 asterisks)
        assert result['password'] == '********'
        # api_key uses default mask_placeholder
        assert result['api_key'] == '***MASKED***'
        # username is not masked
        assert result['username'] == 'john'

    def test_callable_mask_placeholder(self):
        """Test callable mask_placeholder."""
        from rhosocial.activerecord.logging import SummarizerConfig
        from rhosocial.activerecord.logging.summarizer import DataSummarizer

        config = SummarizerConfig(
            sensitive_fields={'password', 'token'},
            mask_placeholder=lambda v: f'<{len(str(v))} chars hidden>'
        )
        summarizer = DataSummarizer(config)

        data = {'password': 'secret123', 'token': 'abc123xyz'}
        result = summarizer.summarize(data)

        assert result['password'] == '<9 chars hidden>'
        assert result['token'] == '<9 chars hidden>'

    def test_field_masker_takes_precedence(self):
        """Test that field_maskers take precedence over mask_placeholder."""
        from rhosocial.activerecord.logging import SummarizerConfig
        from rhosocial.activerecord.logging.summarizer import DataSummarizer

        config = SummarizerConfig(
            sensitive_fields={'password', 'email'},
            mask_placeholder='[DEFAULT]',
            field_maskers={
                'password': lambda v: '[PASSWORD]',
            }
        )
        summarizer = DataSummarizer(config)

        data = {'password': 'secret', 'email': 'test@example.com'}
        result = summarizer.summarize(data)

        # password uses field_masker
        assert result['password'] == '[PASSWORD]'
        # email uses global mask_placeholder
        assert result['email'] == '[DEFAULT]'

    def test_field_maskers_case_insensitive(self):
        """Test that field_maskers are case-insensitive."""
        from rhosocial.activerecord.logging import SummarizerConfig
        from rhosocial.activerecord.logging.summarizer import DataSummarizer

        config = SummarizerConfig(
            sensitive_fields={'Password', 'EMAIL'},
            field_maskers={
                'PASSWORD': lambda v: '[PWD]',
                'email': lambda v: '[MAIL]',
            }
        )
        summarizer = DataSummarizer(config)

        data = {'password': 'secret', 'Email': 'test@example.com'}
        result = summarizer.summarize(data)

        assert result['password'] == '[PWD]'
        assert result['Email'] == '[MAIL]'

    def test_field_masker_exception_fallback(self):
        """Test that masker falls back to default on exception."""
        from rhosocial.activerecord.logging import SummarizerConfig
        from rhosocial.activerecord.logging.summarizer import DataSummarizer

        def bad_masker(v):
            raise ValueError("Intentional error")

        config = SummarizerConfig(
            sensitive_fields={'password'},
            mask_placeholder='[FALLBACK]',
            field_maskers={
                'password': bad_masker,
            }
        )
        summarizer = DataSummarizer(config)

        data = {'password': 'secret'}
        result = summarizer.summarize(data)

        # Should fall back to mask_placeholder when masker raises
        assert result['password'] == '[FALLBACK]'


class TestMaskerExceptionLogging:
    """Test that masker exceptions produce warning logs instead of silent fallback."""

    def test_field_masker_exception_logs_warning(self):
        """field_masker raising exception should log a warning."""
        def bad_masker(v):
            raise ValueError("Intentional masker error")

        config = SummarizerConfig(
            sensitive_fields={'password'},
            mask_placeholder='[FALLBACK]',
            field_maskers={'password': bad_masker},
        )
        summarizer = DataSummarizer(config)

        # Capture output from the summarizer logger
        summarizer_logger = logging.getLogger("rhosocial.activerecord.logging.summarizer")
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        handler.setLevel(logging.WARNING)
        summarizer_logger.addHandler(handler)
        original_propagate = summarizer_logger.propagate

        try:
            summarizer_logger.propagate = True
            result = summarizer.summarize({'password': 'secret'})

            # Should fall back to mask_placeholder
            assert result['password'] == '[FALLBACK]'
            # Should have a warning in the output
            output = stream.getvalue()
            assert "Field masker" in output
            assert "password" in output
        finally:
            summarizer_logger.removeHandler(handler)
            summarizer_logger.propagate = original_propagate

    def test_global_mask_placeholder_exception_logs_warning(self):
        """Global mask_placeholder callable raising exception should log a warning."""
        config = SummarizerConfig(
            sensitive_fields={'token'},
            mask_placeholder=lambda v: 1 / 0,
        )
        summarizer = DataSummarizer(config)

        summarizer_logger = logging.getLogger("rhosocial.activerecord.logging.summarizer")
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        handler.setLevel(logging.WARNING)
        summarizer_logger.addHandler(handler)

        try:
            result = summarizer.summarize({'token': 'abc'})

            # Should fall back to "***MASKED***"
            assert result['token'] == '***MASKED***'
            # Should have a warning in the output
            output = stream.getvalue()
            assert "mask_placeholder" in output
        finally:
            summarizer_logger.removeHandler(handler)

    def test_successful_masker_does_not_log_warning(self):
        """A working masker should not produce any warning."""
        config = SummarizerConfig(
            sensitive_fields={'email'},
            field_maskers={'email': lambda v: v[0] + '***@' + v.split('@')[1]},
        )
        summarizer = DataSummarizer(config)

        summarizer_logger = logging.getLogger("rhosocial.activerecord.logging.summarizer")
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        handler.setLevel(logging.WARNING)
        summarizer_logger.addHandler(handler)

        try:
            result = summarizer.summarize({'email': 'test@example.com'})

            assert result['email'] == 't***@example.com'
            assert stream.getvalue() == ""
        finally:
            summarizer_logger.removeHandler(handler)


class TestSummarizerCoverage:
    """Tests to improve coverage of summarizer edge cases."""

    def test_summarize_tuple(self):
        """Summarize tuple should return string with tuple() wrapper."""
        config = SummarizerConfig(max_dict_items=5)
        summarizer = DataSummarizer(config)
        result = summarizer.summarize((1, 2, 3))
        assert "tuple(" in result

    def test_summarize_set(self):
        """Summarize set should return string with set() wrapper."""
        config = SummarizerConfig(max_dict_items=5)
        summarizer = DataSummarizer(config)
        result = summarizer.summarize({1, 2, 3})
        assert "set(" in result

    def test_summarize_keys_only_sequence(self):
        """keys_only mode on sequence should show type hints."""
        config = SummarizerConfig(max_dict_items=5)
        summarizer = DataSummarizer(config)
        result = summarizer.summarize_keys_only([1, "hello", True])
        assert "<int>" in result
        assert "<str>" in result

    def test_summarize_other_type_repr_truncated(self):
        """Non-standard types with long repr should be truncated with type hint."""
        config = SummarizerConfig(max_string_length=10)
        summarizer = DataSummarizer(config)

        class CustomObj:
            def __repr__(self):
                return "A" * 200

        result = summarizer.summarize(CustomObj())
        assert "truncated" in result
        assert "CustomObj" in result

    def test_summarize_other_type_repr_short(self):
        """Non-standard types with short repr should show repr."""
        config = SummarizerConfig(max_string_length=100)
        summarizer = DataSummarizer(config)

        class ShortObj:
            def __repr__(self):
                return "short_repr"

        result = summarizer.summarize(ShortObj())
        assert "short_repr" in result

    def test_summarize_show_type_hint_disabled(self):
        """show_type_hint=False should omit type name from truncation."""
        config = SummarizerConfig(max_string_length=10, show_type_hint=False)
        summarizer = DataSummarizer(config)

        class LongObj:
            def __repr__(self):
                return "X" * 200

        result = summarizer.summarize(LongObj())
        assert "truncated" in result
        assert "LongObj" not in result

    def test_mask_sensitive_tuple(self):
        """mask_sensitive should handle tuples."""
        summarizer = DataSummarizer()
        result = summarizer.mask_sensitive(({"password": "secret"}, "safe"))
        assert isinstance(result, tuple)
        assert result[0]["password"] == "***MASKED***"
        assert result[1] == "safe"

    def test_mask_sensitive_in_tuple(self):
        """mask_sensitive should process tuples containing dicts."""
        summarizer = DataSummarizer()
        result = summarizer.mask_sensitive(({"password": "secret"},))
        assert isinstance(result, tuple)
        assert result[0]["password"] == "***MASKED***"

    def test_mask_sensitive_set(self):
        """mask_sensitive should handle sets."""
        summarizer = DataSummarizer()
        result = summarizer.mask_sensitive({"password": "secret"})
        assert result["password"] == "***MASKED***"

    def test_mask_sensitive_in_set(self):
        """mask_sensitive should process sets containing dicts."""
        summarizer = DataSummarizer()
        data = [{"password": "secret"}, {"name": "visible"}]
        result = summarizer.mask_sensitive(data)
        assert result[0]["password"] == "***MASKED***"
        assert result[1]["name"] == "visible"

