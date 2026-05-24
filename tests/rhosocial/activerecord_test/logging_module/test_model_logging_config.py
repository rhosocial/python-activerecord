"""Tests for ActiveRecord class-level logging configuration."""

import io
import logging
from typing import Optional

import pytest

from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend, SQLiteConnectionConfig
from rhosocial.activerecord.backend.impl.sqlite.backend.async_backend import AsyncSQLiteBackend
from rhosocial.activerecord.connection.group import BackendGroup, AsyncBackendGroup
from rhosocial.activerecord.logging import LoggingConfig, LogDataMode
from rhosocial.activerecord.logging.mixin import BackendLoggingMixin
from rhosocial.activerecord.model import ActiveRecord, AsyncActiveRecord


class TestModelLoggingConfig:
    """Test class-level LoggingConfig behavior."""

    @pytest.fixture(autouse=True)
    def reset_logging_state(self):
        original_model_config = ActiveRecord.__logging_config__
        original_async_model_config = AsyncActiveRecord.__logging_config__
        original_backend_config = BackendLoggingMixin.__logging_config__
        ActiveRecord.__logging_config__ = LoggingConfig()
        AsyncActiveRecord.__logging_config__ = LoggingConfig()
        BackendLoggingMixin.__logging_config__ = LoggingConfig()
        yield
        ActiveRecord.__logging_config__ = original_model_config
        AsyncActiveRecord.__logging_config__ = original_async_model_config
        BackendLoggingMixin.__logging_config__ = original_backend_config

    def test_model_logging_config_overrides_global_default_for_log_data(self):
        class LocalModel(ActiveRecord):
            __table_name__ = "local_model"
            id: Optional[int] = None

        stream = io.StringIO()
        logger = logging.getLogger("test.model_logging_config.hidden")
        logger.handlers.clear()
        logger.setLevel(logging.DEBUG)
        logger.propagate = False
        handler = logging.StreamHandler(stream)
        logger.addHandler(handler)

        original_logger = LocalModel.__logger__
        original_config = LocalModel.__logging_config__
        try:
            ActiveRecord.__logging_config__ = LoggingConfig(log_data_mode=LogDataMode.FULL)
            LocalModel.__logging_config__ = LoggingConfig(log_data_mode=LogDataMode.HIDDEN)
            LocalModel.set_logger(logger)

            LocalModel.log_data(logging.DEBUG, "Payload", {"secret": "visible"})

            output = stream.getvalue()
            assert "<hidden>" in output
            assert "visible" not in output
        finally:
            LocalModel.__logger__ = original_logger
            LocalModel.__logging_config__ = original_config
            logger.handlers.clear()

    def test_different_models_use_different_logging_configs(self):
        class HiddenModel(ActiveRecord):
            __table_name__ = "hidden_model"
            id: Optional[int] = None

        class FullModel(ActiveRecord):
            __table_name__ = "full_model"
            id: Optional[int] = None

        hidden_original = HiddenModel.__logging_config__
        full_original = FullModel.__logging_config__
        try:
            HiddenModel.__logging_config__ = LoggingConfig(log_data_mode=LogDataMode.HIDDEN)
            FullModel.__logging_config__ = LoggingConfig(log_data_mode=LogDataMode.FULL)

            data = {"name": "alice"}

            assert HiddenModel.get_logging_config().summarize_data(data) == "<hidden>"
            assert FullModel.get_logging_config().summarize_data(data) == data
        finally:
            HiddenModel.__logging_config__ = hidden_original
            FullModel.__logging_config__ = full_original

    def test_configure_binds_logging_config_to_model_and_backend(self):
        class ConfiguredModel(ActiveRecord):
            __table_name__ = "configured_model"
            id: Optional[int] = None

        logging_config = LoggingConfig(log_data_mode=LogDataMode.KEYS_ONLY)

        ConfiguredModel.configure(
            SQLiteConnectionConfig(database=":memory:"),
            SQLiteBackend,
            logging_config=logging_config,
        )

        try:
            assert ConfiguredModel.__logging_config__ is logging_config
            assert ConfiguredModel.__backend__._logging_config is logging_config
            assert ConfiguredModel.get_logging_config() is logging_config
        finally:
            ConfiguredModel.__backend__.disconnect()
            ConfiguredModel.__backend__ = None
            ConfiguredModel.__logging_config__ = ActiveRecord.__logging_config__

    @pytest.mark.asyncio
    async def test_async_configure_binds_logging_config_to_model_and_backend(self):
        class AsyncConfiguredModel(AsyncActiveRecord):
            __table_name__ = "async_configured_model"
            id: Optional[int] = None

        logging_config = LoggingConfig(log_data_mode=LogDataMode.KEYS_ONLY)

        await AsyncConfiguredModel.configure(
            SQLiteConnectionConfig(database=":memory:"),
            AsyncSQLiteBackend,
            logging_config=logging_config,
        )

        try:
            assert AsyncConfiguredModel.__logging_config__ is logging_config
            assert AsyncConfiguredModel.__backend__._logging_config is logging_config
            assert AsyncConfiguredModel.get_logging_config() is logging_config
        finally:
            await AsyncConfiguredModel.__backend__.disconnect()
            AsyncConfiguredModel.__backend__ = None
            AsyncConfiguredModel.__logging_config__ = AsyncActiveRecord.__logging_config__

    def test_backend_group_binds_logging_config_to_models_and_backend(self):
        class GroupUser(ActiveRecord):
            __table_name__ = "group_users"
            id: Optional[int] = None

        class GroupPost(ActiveRecord):
            __table_name__ = "group_posts"
            id: Optional[int] = None

        logging_config = LoggingConfig(log_data_mode=LogDataMode.HIDDEN)
        group = BackendGroup(
            name="logging",
            models=[GroupUser, GroupPost],
            config=SQLiteConnectionConfig(database=":memory:"),
            backend_class=SQLiteBackend,
            logging_config=logging_config,
        )

        group.configure()

        try:
            assert GroupUser.__logging_config__ is logging_config
            assert GroupPost.__logging_config__ is logging_config
            assert group.get_backend()._logging_config is logging_config
        finally:
            group.disconnect()
            GroupUser.__logging_config__ = ActiveRecord.__logging_config__
            GroupPost.__logging_config__ = ActiveRecord.__logging_config__

    def test_backend_group_without_logging_config_keeps_model_config(self):
        class GroupKeepModel(ActiveRecord):
            __table_name__ = "group_keep_model"
            id: Optional[int] = None

        model_config = LoggingConfig(log_data_mode=LogDataMode.FULL)
        GroupKeepModel.__logging_config__ = model_config
        group = BackendGroup(
            name="logging-default",
            models=[GroupKeepModel],
            config=SQLiteConnectionConfig(database=":memory:"),
            backend_class=SQLiteBackend,
        )

        group.configure()

        try:
            assert GroupKeepModel.__logging_config__ is model_config
            assert group.get_backend()._logging_config is None
        finally:
            group.disconnect()
            GroupKeepModel.__logging_config__ = ActiveRecord.__logging_config__

    @pytest.mark.asyncio
    async def test_async_backend_group_binds_logging_config_to_models_and_backend(self):
        class AsyncGroupUser(AsyncActiveRecord):
            __table_name__ = "async_group_users"
            id: Optional[int] = None

        logging_config = LoggingConfig(log_data_mode=LogDataMode.HIDDEN)
        group = AsyncBackendGroup(
            name="async-logging",
            models=[AsyncGroupUser],
            config=SQLiteConnectionConfig(database=":memory:"),
            backend_class=AsyncSQLiteBackend,
            logging_config=logging_config,
        )

        await group.configure()

        try:
            assert AsyncGroupUser.__logging_config__ is logging_config
            assert group.get_backend()._logging_config is logging_config
        finally:
            await group.disconnect()
            AsyncGroupUser.__logging_config__ = AsyncActiveRecord.__logging_config__
