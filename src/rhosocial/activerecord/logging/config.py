# src/rhosocial/activerecord/logging/config.py
"""Logging configuration for ActiveRecord.

This module provides configuration classes for managing logging
settings across ActiveRecord components.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, List, Any
import logging
import threading

from .formatter import ActiveRecordFormatter
from .redaction import LogPayload, redact_payload
from .summarizer import SummarizerConfig, DataSummarizer


class LogDataMode(str, Enum):
    HIDDEN = "hidden"
    KEYS_ONLY = "keys_only"
    SUMMARY = "summary"
    FULL = "full"


def normalize_log_data_mode(mode: Optional[object]) -> Optional[LogDataMode]:
    if mode is None:
        return None
    if isinstance(mode, LogDataMode):
        return mode
    allowed = [item.value for item in LogDataMode]
    raise ValueError(f"log_data_mode must be a LogDataMode value: {allowed}")


#: Marks a level the library itself assigned, so an application override is
#: distinguishable from the library's own earlier decision.
_LIBRARY_LEVEL_ATTR = "_rhosocial_activerecord_level"

#: The documented quiet default.  It is enforced by inheritance rather than by
#: writing WARNING onto every logger, so an application that configures the
#: root logger (or any logger on the way to the model) still wins.  This covers
#: user-defined model loggers too, not only the framework's own namespace.
_QUIET_DEFAULT_LEVEL = logging.WARNING


def _library_owns_level(logger: logging.Logger) -> bool:
    """Return True when the logger's current level is the one the library set."""
    return getattr(logger, _LIBRARY_LEVEL_ATTR, None) == logger.level


def _set_level(logger: logging.Logger, level: int) -> None:
    """Set a level and remember it as the library's decision."""
    logger.setLevel(level)
    setattr(logger, _LIBRARY_LEVEL_ATTR, level)


@dataclass
class LoggerConfig:
    """Configuration for a single logger.

    This class defines the settings for an individual logger instance.

    Attributes:
        name: The name of the logger (e.g., 'rhosocial.activerecord.model').
        level: The logging level (default: WARNING).
        propagate: Whether to propagate logs to parent loggers (default: True,
            so the application's root configuration decides where they go).
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
    level: int = logging.WARNING
    propagate: bool = True
    handlers: List[logging.Handler] = field(default_factory=list)
    log_data_mode: Optional[LogDataMode] = None
    summarizer_config: Optional[SummarizerConfig] = None

    def __post_init__(self) -> None:
        self._validate_log_data_mode(self.log_data_mode)

    @staticmethod
    def _validate_log_data_mode(mode: Optional[LogDataMode]) -> None:
        normalize_log_data_mode(mode)

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

    Key principle: This configuration does NOT modify the root logger and
    does NOT install handlers on library loggers.  Loggers propagate to their
    parents by default, so the application's own root configuration decides
    where ActiveRecord records are written and at which level.

    Attributes:
        default_level: Default log level for all ActiveRecord loggers.
        propagate: Whether to propagate logs to parent loggers (default: True).
        formatter: Default formatter used when auto_setup installs a handler.
        loggers: Logger configurations by category.
        auto_setup: Whether to auto-setup handlers when first log is written.
        summarizer_config: Configuration for data summarization in logs.
        log_data_mode: Default mode for data logging ('summary', 'keys_only', 'full').

    Example:
        >>> config = LoggingConfig(
        ...     default_level=logging.DEBUG,
        ...     propagate=True,
        ...     auto_setup=False
        ... )
        >>> logger = config.get_logger('activerecord')
    """

    # Default log level for all ActiveRecord loggers.  WARNING keeps an
    # application's stderr quiet until it asks for more detail.
    default_level: int = logging.WARNING

    # Whether to propagate logs to parent loggers (including root).
    # Default True: the application owns the handlers and the level.
    propagate: bool = True

    # Default formatter class or instance
    formatter: logging.Formatter = field(default_factory=ActiveRecordFormatter)

    # Logger configurations by category
    loggers: Dict[str, LoggerConfig] = field(default_factory=dict)

    # Whether to auto-setup handlers when first log is written.
    # Default False: ActiveRecord never writes to the process's stderr on its own.
    auto_setup: bool = False

    # Data summarization configuration
    summarizer_config: SummarizerConfig = field(default_factory=SummarizerConfig)

    # Default mode for data logging: 'summary', 'keys_only', or 'full'
    # - 'summary': Truncate large values, mask sensitive fields
    # - 'keys_only': Only show field names, no values
    # - 'full': Show complete data (not recommended for production)
    log_data_mode: LogDataMode = LogDataMode.SUMMARY

    # Cached summarizer instance
    _summarizer: Optional[DataSummarizer] = field(default=None, repr=False, compare=False)

    # Cached summarizers for specific loggers (by logger name)
    _logger_summarizers: Dict[str, DataSummarizer] = field(default_factory=dict, repr=False, compare=False)

    # Track which loggers have been configured (for idempotent get_logger)
    _configured_loggers: set = field(default_factory=set, repr=False, compare=False)

    # Lock for thread-safe cache access (RLock for reentrant get_summarizer calls)
    _lock: Any = field(default=None, repr=False, compare=False, init=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "_lock", threading.RLock())

    def __setattr__(self, name: str, value: Any) -> None:
        """Override setattr to invalidate cached summarizers when config changes."""
        if name == "log_data_mode":
            value = normalize_log_data_mode(value)
        if name == "summarizer_config":
            lock = self.__dict__.get("_lock") if "__dict__" in dir(self) else None
            if lock is not None:
                with lock:
                    object.__setattr__(self, "_summarizer", None)
                    object.__setattr__(self, "_logger_summarizers", {})
            else:
                object.__setattr__(self, "_summarizer", None)
                object.__setattr__(self, "_logger_summarizers", {})
        if name in ("default_level", "propagate", "auto_setup", "formatter"):
            lock = self.__dict__.get("_lock") if "__dict__" in dir(self) else None
            if lock is not None:
                with lock:
                    object.__setattr__(self, "_configured_loggers", set())
            else:
                object.__setattr__(self, "_configured_loggers", set())
        object.__setattr__(self, name, value)

    @staticmethod
    def _validate_log_data_mode(mode: Optional[LogDataMode]) -> None:
        normalize_log_data_mode(mode)

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
        with self._lock:
            if logger_name is None:
                if self._summarizer is None:
                    object.__setattr__(self, "_summarizer", DataSummarizer(self.summarizer_config))
                return self._summarizer

            # Find matching logger config (supports hierarchical matching)
            logger_config = self._find_logger_config(logger_name)

            if logger_config is not None and logger_config.summarizer_config is not None:
                # Use logger-specific summarizer config
                if logger_name not in self._logger_summarizers:
                    new_dict = dict(self._logger_summarizers)
                    new_dict[logger_name] = DataSummarizer(logger_config.summarizer_config)
                    object.__setattr__(self, "_logger_summarizers", new_dict)
                return self._logger_summarizers[logger_name]
            else:
                # Use global summarizer
                return self.get_summarizer()

    def _find_logger_config(self, logger_name: str) -> Optional["LoggerConfig"]:
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
        parts = logger_name.split(".")
        for i in range(len(parts) - 1, 0, -1):
            parent_name = ".".join(parts[:i])
            if parent_name in self.loggers:
                return self.loggers[parent_name]

        return None

    def resolve_log_data_mode(self, logger_name: Optional[str] = None) -> LogDataMode:
        """Get the effective log data mode for a logger."""
        if logger_name is None:
            mode = self.log_data_mode
        else:
            logger_config = self._find_logger_config(logger_name)
            if logger_config is not None and logger_config.log_data_mode is not None:
                mode = logger_config.log_data_mode
            else:
                mode = self.log_data_mode
        resolved = normalize_log_data_mode(mode)
        if resolved is None:
            return LogDataMode.SUMMARY
        return resolved

    def get_log_data_mode(self, logger_name: Optional[str] = None) -> LogDataMode:
        """Get the effective log data mode for a logger."""
        return self.resolve_log_data_mode(logger_name)

    def summarize_data(self, data: Any, logger_name: Optional[str] = None) -> Any:
        """Summarize data according to the configured mode."""
        effective_mode = self.resolve_log_data_mode(logger_name)

        if effective_mode is LogDataMode.HIDDEN:
            return "<hidden>"
        if effective_mode is LogDataMode.FULL:
            return data
        if effective_mode is LogDataMode.KEYS_ONLY:
            return self.get_summarizer(logger_name).summarize_keys_only(data)
        return self.get_summarizer(logger_name).summarize(data)

    def redact(
        self,
        payload: LogPayload,
        logger_name: Optional[str] = None,
    ) -> Any:
        """Redact a structured log payload according to its kind and mode."""
        mode = payload.mode if payload.mode is not None else self.resolve_log_data_mode(
            logger_name
        )
        return redact_payload(self, payload, mode, logger_name)

    def get_logger(self, name: str) -> logging.Logger:
        """Get or create a logger with the configured settings.

        Loggers propagate to their parents by default (propagate=True), so
        the application's root handlers receive them without ActiveRecord
        installing one of its own.  A level the application has already set
        on the logger is left alone, and loggers stay unset while the default
        is ``WARNING`` so the application's root level (or any level set on a
        parent logger) is inherited: the library owns the default, not the
        final decision.  A non-default level, or a per-logger ``LoggerConfig``,
        is written explicitly.

        Configuration is applied only on the first call for a given name.
        Subsequent calls return the same logger without overwriting settings,
        preserving any user customizations made directly on the logger.

        Args:
            name: The name of the logger to create/get.

        Returns:
            Configured logging.Logger instance.
        """
        logger = logging.getLogger(name)
        if name not in self._configured_loggers:
            # Check if there's a specific config for this logger
            config = self.loggers.get(name)
            if config is not None:
                _set_level(logger, config.level)
                logger.propagate = config.propagate
                for handler in config.handlers:
                    if handler not in logger.handlers:
                        logger.addHandler(handler)
            else:
                # A level the application set is left alone.  A level the
                # library set earlier may be replaced, because that was only
                # ever a default and not the final word.
                if logger.level == logging.NOTSET or _library_owns_level(logger):
                    if self.default_level == _QUIET_DEFAULT_LEVEL:
                        # Stay unset so the application's root/parent level is
                        # inherited; Python's own root default is WARNING.
                        _set_level(logger, logging.NOTSET)
                    else:
                        _set_level(logger, self.default_level)
                logger.propagate = self.propagate

            # Auto-setup handler if enabled and no handlers exist
            if self.auto_setup and not logger.handlers:
                handler = logging.StreamHandler()
                handler.setFormatter(self.formatter)
                logger.addHandler(handler)

            self._configured_loggers.add(name)
        return logger

    def add_logger_config(self, config: LoggerConfig) -> None:
        """Add a specific logger configuration.

        Args:
            config: LoggerConfig instance to add.
        """
        config.log_data_mode = normalize_log_data_mode(config.log_data_mode)
        self.loggers[config.name] = config
        lock = self.__dict__.get("_lock") if "__dict__" in dir(self) else None
        if lock is not None:
            with lock:
                object.__setattr__(self, "_logger_summarizers", {})
        else:
            object.__setattr__(self, "_logger_summarizers", {})
