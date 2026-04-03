# tests/rhosocial/activerecord_test/logging_module/test_summarizer.py
"""Tests for DataSummarizer functionality."""

import pytest
from rhosocial.activerecord.logging.summarizer import (
    SummarizerConfig,
    DataSummarizer,
    get_default_summarizer,
    set_default_summarizer,
    summarize_data,
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


class TestGlobalSummarizer:
    """Tests for global summarizer functions."""

    def test_get_default_summarizer(self):
        """Test getting default summarizer."""
        summarizer = get_default_summarizer()
        assert isinstance(summarizer, DataSummarizer)

    def test_set_default_summarizer(self):
        """Test setting default summarizer."""
        custom_config = SummarizerConfig(max_string_length=50)
        custom_summarizer = DataSummarizer(custom_config)

        original = get_default_summarizer()
        set_default_summarizer(custom_summarizer)

        try:
            result = get_default_summarizer()
            assert result is custom_summarizer
        finally:
            # Restore original
            set_default_summarizer(original)

    def test_summarize_data_convenience(self):
        """Test convenience function."""
        data = {"key": "a" * 200}
        result = summarize_data(data)

        # Should use default summarizer
        assert "truncated" in result["key"]


class TestLoggingIntegration:
    """Tests for LoggingConfig integration with summarizer."""

    def test_logging_config_summarizer(self):
        """Test LoggingConfig.get_summarizer()."""
        from rhosocial.activerecord.logging import LoggingConfig

        config = LoggingConfig()
        summarizer = config.get_summarizer()

        assert isinstance(summarizer, DataSummarizer)

    def test_logging_config_summarize_data(self):
        """Test LoggingConfig.summarize_data()."""
        from rhosocial.activerecord.logging import LoggingConfig

        config = LoggingConfig()
        data = {"password": "secret", "bio": "A" * 200}

        # Test summary mode (default)
        result = config.summarize_data(data)
        assert result["password"] == "***MASKED***"
        assert "truncated" in result["bio"]

        # Test keys_only mode
        result = config.summarize_data(data, mode='keys_only')
        assert result["password"] == "***MASKED***"
        assert result["bio"] == "<str>"

        # Test full mode
        result = config.summarize_data(data, mode='full')
        assert result == data

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

