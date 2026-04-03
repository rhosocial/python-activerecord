# src/rhosocial/activerecord/logging/config.py
"""Logging configuration for ActiveRecord.

This module provides configuration classes for managing logging
settings across ActiveRecord components.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, List, Any
import logging

from .formatter import ActiveRecordFormatter
from .summarizer import SummarizerConfig, DataSummarizer


@dataclass
class LoggerConfig:
    """Configuration for a single logger.

    This class defines the settings for an individual logger instance.

    Attributes:
        name: The name of the logger (e.g., 'rhosocial.activerecord.model').
        level: The logging level (default: DEBUG).
        propagate: Whether to propagate logs to parent loggers (default: False).
        handlers: List of handlers to attach to the logger.
        log_data_mode: Data summarization mode for this logger.
            - 'summary': Truncate large values, mask sensitive fields
            - 'keys_only': Only show field names, no values
            - 'full': Show complete data
            If None, uses the global LoggingConfig.log_data_mode.
        summarizer_config: Custom SummarizerConfig for this logger.
            If None, uses the global LoggingConfig.summarizer_config.
    """

    name: str
    level: int = logging.DEBUG
    propagate: bool = False
    handlers: List[logging.Handler] = field(default_factory=list)
    log_data_mode: Optional[str] = None
    summarizer_config: Optional[SummarizerConfig] = None

    def create_logger(self) -> logging.Logger:
        """Create and configure a logger instance.

        Returns:
            Configured logging.Logger instance.
        """
        logger = logging.getLogger(self.name)
        logger.setLevel(self.level)
        logger.propagate = self.propagate

        for handler in self.handlers:
            if handler not in logger.handlers:
                logger.addHandler(handler)

        return logger


@dataclass
class LoggingConfig:
    """Global logging configuration for ActiveRecord.

    This configuration controls how ActiveRecord creates and manages loggers.
    Users can customize logging behavior through this class.

    Key principle: This configuration does NOT modify the root logger.
    All loggers created through this config have propagate=False by default,
    preventing logs from bubbling up to the root logger.

    Attributes:
        default_level: Default log level for all ActiveRecord loggers.
        propagate: Whether to propagate logs to parent loggers (default: False).
        formatter: Default formatter for handlers.
        loggers: Logger configurations by category.
        auto_setup: Whether to auto-setup handlers when first log is written.
        summarizer_config: Configuration for data summarization in logs.
        log_data_mode: Default mode for data logging ('summary', 'keys_only', 'full').

    Example:
        >>> config = LoggingConfig(
        ...     default_level=logging.INFO,
        ...     propagate=False,
        ...     auto_setup=True
        ... )
        >>> logger = config.get_logger('activerecord')
    """

    # Default log level for all ActiveRecord loggers
    default_level: int = logging.DEBUG

    # Whether to propagate logs to parent loggers (including root)
    # Default False to avoid polluting user's root logger
    propagate: bool = False

    # Default formatter class or instance
    formatter: logging.Formatter = field(default_factory=ActiveRecordFormatter)

    # Logger configurations by category
    loggers: Dict[str, LoggerConfig] = field(default_factory=dict)

    # Whether to auto-setup handlers when first log is written
    auto_setup: bool = True

    # Data summarization configuration
    summarizer_config: SummarizerConfig = field(default_factory=SummarizerConfig)

    # Default mode for data logging: 'summary', 'keys_only', or 'full'
    # - 'summary': Truncate large values, mask sensitive fields
    # - 'keys_only': Only show field names, no values
    # - 'full': Show complete data (not recommended for production)
    log_data_mode: str = 'summary'

    # Cached summarizer instance
    _summarizer: Optional[DataSummarizer] = field(default=None, repr=False, compare=False)

    # Cached summarizers for specific loggers (by logger name)
    _logger_summarizers: Dict[str, DataSummarizer] = field(default_factory=dict, repr=False, compare=False)

    def __setattr__(self, name: str, value: Any) -> None:
        """Override setattr to invalidate cached summarizers when config changes."""
        if name == 'summarizer_config':
            # Clear cached summarizers when summarizer_config is updated
            object.__setattr__(self, '_summarizer', None)
            object.__setattr__(self, '_logger_summarizers', {})
        object.__setattr__(self, name, value)

    def get_summarizer(self, logger_name: Optional[str] = None) -> DataSummarizer:
        """Get or create the DataSummarizer instance.

        Args:
            logger_name: Optional logger name to get a specific summarizer.
                If provided and the logger has a custom summarizer_config,
                returns a summarizer configured for that logger.
                If None, returns the global summarizer.

        Returns:
            DataSummarizer instance configured with appropriate config.
        """
        if logger_name is None:
            if self._summarizer is None:
                self._summarizer = DataSummarizer(self.summarizer_config)
            return self._summarizer

        # Find matching logger config (supports hierarchical matching)
        logger_config = self._find_logger_config(logger_name)

        if logger_config is not None and logger_config.summarizer_config is not None:
            # Use logger-specific summarizer config
            if logger_name not in self._logger_summarizers:
                self._logger_summarizers[logger_name] = DataSummarizer(logger_config.summarizer_config)
            return self._logger_summarizers[logger_name]
        else:
            # Use global summarizer
            return self.get_summarizer()

    def _find_logger_config(self, logger_name: str) -> Optional['LoggerConfig']:
        """Find the most specific LoggerConfig for a given logger name.

        Performs hierarchical matching: for logger 'rhosocial.activerecord.model.User',
        checks in order:
        1. 'rhosocial.activerecord.model.User' (exact match)
        2. 'rhosocial.activerecord.model' (parent)
        3. 'rhosocial.activerecord' (grandparent)
        ... and so on until a match is found.

        Args:
            logger_name: The full logger name to find config for.

        Returns:
            LoggerConfig if found, None otherwise.
        """
        # Check exact match first
        if logger_name in self.loggers:
            return self.loggers[logger_name]

        # Check parent loggers (hierarchical matching)
        parts = logger_name.split('.')
        for i in range(len(parts) - 1, 0, -1):
            parent_name = '.'.join(parts[:i])
            if parent_name in self.loggers:
                return self.loggers[parent_name]

        return None

    def get_log_data_mode(self, logger_name: Optional[str] = None) -> str:
        """Get the effective log data mode for a logger.

        Args:
            logger_name: Optional logger name to get specific mode.
                If provided and the logger has a custom log_data_mode,
                returns that mode. Otherwise returns the global mode.

        Returns:
            The effective log data mode ('summary', 'keys_only', or 'full').
        """
        if logger_name is None:
            return self.log_data_mode

        logger_config = self._find_logger_config(logger_name)
        if logger_config is not None and logger_config.log_data_mode is not None:
            return logger_config.log_data_mode

        return self.log_data_mode

    def summarize_data(
        self,
        data: Any,
        mode: Optional[str] = None,
        logger_name: Optional[str] = None
    ) -> Any:
        """Summarize data according to the configured mode.

        Args:
            data: The data to summarize.
            mode: Override mode ('summary', 'keys_only', 'full').
                If None, uses the effective log_data_mode for the logger.
            logger_name: Optional logger name to get logger-specific configuration.
                If provided, uses the summarizer and mode configured for that logger.

        Returns:
            Summarized data according to the mode.
        """
        effective_mode = mode or self.get_log_data_mode(logger_name)

        if effective_mode == 'full':
            return data
        elif effective_mode == 'keys_only':
            return self.get_summarizer(logger_name).summarize_keys_only(data)
        else:  # 'summary' (default)
            return self.get_summarizer(logger_name).summarize(data)

    def get_logger(self, name: str) -> logging.Logger:
        """Get or create a logger with the configured settings.

        This method creates a logger that is isolated from the root logger
        by default (propagate=False), preventing ActiveRecord logs from
        appearing in user's root logger handlers unless explicitly configured.

        Args:
            name: The name of the logger to create/get.

        Returns:
            Configured logging.Logger instance.
        """
        logger = logging.getLogger(name)
        logger.setLevel(self.default_level)
        logger.propagate = self.propagate

        # Check if there's a specific config for this logger
        if name in self.loggers:
            config = self.loggers[name]
            logger.setLevel(config.level)
            logger.propagate = config.propagate
            for handler in config.handlers:
                if handler not in logger.handlers:
                    logger.addHandler(handler)

        # Auto-setup handler if enabled and no handlers exist
        if self.auto_setup and not logger.handlers:
            handler = logging.StreamHandler()
            handler.setFormatter(self.formatter)
            logger.addHandler(handler)

        return logger

    def add_logger_config(self, config: LoggerConfig) -> None:
        """Add a specific logger configuration.

        Args:
            config: LoggerConfig instance to add.
        """
        self.loggers[config.name] = config
