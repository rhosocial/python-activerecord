# tests/rhosocial/activerecord_test/logging_module/test_logger_summarization.py
"""Tests for per-logger data summarization configuration."""

import pytest

from rhosocial.activerecord.logging import (
    get_logging_manager,
    LoggerConfig,
    SummarizerConfig,
)


class TestPerLoggerSummarization:
    """Test per-logger data summarization configuration."""

    @pytest.fixture(autouse=True)
    def reset_logging_manager(self):
        """Reset logging manager before and after each test."""
        manager = get_logging_manager()
        manager.reset()
        yield
        manager.reset()

    def test_global_summarization_mode(self):
        """Test global summarization mode is applied when no logger-specific config."""
        manager = get_logging_manager()
        config = manager.config

        # Set global mode
        config.log_data_mode = 'summary'

        test_data = {'username': 'john', 'password': 'secret', 'bio': 'A' * 200}

        # Without logger name, uses global config
        result = config.summarize_data(test_data)
        assert '***MASKED***' in str(result)
        assert 'truncated' in str(result)

    def test_logger_specific_mode_overrides_global(self):
        """Test logger-specific mode overrides global mode."""
        manager = get_logging_manager()
        config = manager.config

        # Set global mode to summary
        config.log_data_mode = 'summary'

        # Set backend to keys_only
        backend_config = LoggerConfig(
            name='rhosocial.activerecord.backend',
            log_data_mode='keys_only',
        )
        config.add_logger_config(backend_config)

        test_data = {'username': 'john', 'password': 'secret'}

        # Global mode
        global_result = config.summarize_data(test_data)
        assert 'john' in str(global_result)  # summary shows values

        # Backend mode
        backend_result = config.summarize_data(test_data, logger_name='rhosocial.activerecord.backend')
        assert 'john' not in str(backend_result)  # keys_only hides values
        assert '<str>' in str(backend_result)

    def test_hierarchical_inheritance(self):
        """Test that child loggers inherit parent configuration."""
        manager = get_logging_manager()
        config = manager.config

        # Set backend layer to keys_only
        backend_config = LoggerConfig(
            name='rhosocial.activerecord.backend',
            log_data_mode='keys_only',
        )
        config.add_logger_config(backend_config)

        test_data = {'username': 'john', 'bio': 'test'}

        # backend.sqlite inherits from backend
        result = config.summarize_data(test_data, logger_name='rhosocial.activerecord.backend.sqlite')
        assert '<str>' in str(result)
        assert 'john' not in str(result)

        # backend.mysql also inherits
        result = config.summarize_data(test_data, logger_name='rhosocial.activerecord.backend.mysql')
        assert '<str>' in str(result)

    def test_exact_match_takes_precedence_over_parent(self):
        """Test that exact logger name match takes precedence over parent config."""
        manager = get_logging_manager()
        config = manager.config

        # Parent: backend uses keys_only
        backend_config = LoggerConfig(
            name='rhosocial.activerecord.backend',
            log_data_mode='keys_only',
        )
        config.add_logger_config(backend_config)

        # Child: backend.sqlite uses full
        sqlite_config = LoggerConfig(
            name='rhosocial.activerecord.backend.sqlite',
            log_data_mode='full',
        )
        config.add_logger_config(sqlite_config)

        test_data = {'username': 'john', 'password': 'secret'}

        # backend.mysql inherits keys_only from parent
        mysql_result = config.summarize_data(test_data, logger_name='rhosocial.activerecord.backend.mysql')
        assert '<str>' in str(mysql_result)

        # backend.sqlite uses its own full mode
        sqlite_result = config.summarize_data(test_data, logger_name='rhosocial.activerecord.backend.sqlite')
        assert 'john' in str(sqlite_result)
        assert 'secret' in str(sqlite_result)

    def test_logger_specific_summarizer_config(self):
        """Test logger-specific summarizer configuration."""
        manager = get_logging_manager()
        config = manager.config

        # Global: max_string_length=100 (default)
        # Custom for model.User: max_string_length=20
        custom_summarizer = SummarizerConfig(
            max_string_length=20,
            sensitive_fields={'password'}
        )
        model_config = LoggerConfig(
            name='rhosocial.activerecord.model.User',
            log_data_mode='summary',
            summarizer_config=custom_summarizer,
        )
        config.add_logger_config(model_config)

        # String longer than both 20 and 100
        test_data = {'bio': 'A' * 150, 'password': 'secret'}

        # Global summarizer: truncates at 100
        global_result = config.summarize_data(test_data)
        assert '...[truncated, 150 chars total]' in str(global_result)

        # model.User summarizer: truncates at 20
        user_result = config.summarize_data(test_data, logger_name='rhosocial.activerecord.model.User')
        assert '...[truncated, 150 chars total]' in str(user_result)
        # Check that it shows only first 20 chars before truncation marker
        bio_str = str(user_result)
        # The bio should show "AAAAAAAAAAAAAAAAAAAA" (20 A's) before truncation
        assert 'AAAAAAAAAAAAAAAAAAAA' in bio_str

    def test_mode_parameter_overrides_logger_config(self):
        """Test that explicit mode parameter overrides logger config."""
        manager = get_logging_manager()
        config = manager.config

        # Set backend to keys_only
        backend_config = LoggerConfig(
            name='rhosocial.activerecord.backend',
            log_data_mode='keys_only',
        )
        config.add_logger_config(backend_config)

        test_data = {'username': 'john', 'password': 'secret'}

        # Explicit mode='full' overrides keys_only
        result = config.summarize_data(test_data, mode='full', logger_name='rhosocial.activerecord.backend')
        assert 'john' in str(result)
        assert 'secret' in str(result)

    def test_get_log_data_mode_method(self):
        """Test get_log_data_mode returns correct mode."""
        manager = get_logging_manager()
        config = manager.config

        config.log_data_mode = 'summary'

        backend_config = LoggerConfig(
            name='rhosocial.activerecord.backend',
            log_data_mode='keys_only',
        )
        config.add_logger_config(backend_config)

        # Global mode
        assert config.get_log_data_mode() == 'summary'

        # Backend mode
        assert config.get_log_data_mode('rhosocial.activerecord.backend') == 'keys_only'

        # Child inherits
        assert config.get_log_data_mode('rhosocial.activerecord.backend.sqlite') == 'keys_only'

        # Unconfigured logger uses global
        assert config.get_log_data_mode('rhosocial.activerecord.model.User') == 'summary'

    def test_complex_hierarchy_scenario(self):
        """Test a complex scenario with multiple levels of configuration."""
        manager = get_logging_manager()
        config = manager.config

        # Global: summary
        config.log_data_mode = 'summary'

        # Backend layer: keys_only (strict for production safety)
        backend_config = LoggerConfig(
            name='rhosocial.activerecord.backend',
            log_data_mode='keys_only',
        )
        config.add_logger_config(backend_config)

        # Query layer: full (for debugging)
        query_config = LoggerConfig(
            name='rhosocial.activerecord.query',
            log_data_mode='full',
        )
        config.add_logger_config(query_config)

        # Model layer: summary with custom summarizer
        model_summarizer = SummarizerConfig(
            max_string_length=50,
            sensitive_fields={'password', 'token', 'secret'}
        )
        model_config = LoggerConfig(
            name='rhosocial.activerecord.model',
            log_data_mode='summary',
            summarizer_config=model_summarizer,
        )
        config.add_logger_config(model_config)

        test_data = {'username': 'john', 'password': 'secret', 'bio': 'A' * 100}

        # Backend: keys_only
        backend_result = config.summarize_data(test_data, logger_name='rhosocial.activerecord.backend.sqlite')
        assert '<str>' in str(backend_result)

        # Query: full
        query_result = config.summarize_data(test_data, logger_name='rhosocial.activerecord.query.ActiveQuery')
        assert 'john' in str(query_result)
        assert 'secret' in str(query_result)

        # Model: summary with custom truncation
        model_result = config.summarize_data(test_data, logger_name='rhosocial.activerecord.model.User')
        assert '***MASKED***' in str(model_result)

        # Transaction: uses global summary
        tx_result = config.summarize_data(test_data, logger_name='rhosocial.activerecord.transaction')
        assert '***MASKED***' in str(tx_result)
