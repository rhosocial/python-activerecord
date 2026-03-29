# src/rhosocial/activerecord/logging/formatter.py
"""Custom formatters for ActiveRecord logging.

This module provides custom logging formatters that enhance log records
with additional context information specific to ActiveRecord operations.
"""

import logging
import os
from typing import Optional


class ModuleFormatter(logging.Formatter):
    """Formatter that includes module context in log records.

    This formatter adds a 'subpackage_module' attribute to each log record,
    showing the directory and filename where the log message originated.
    This provides more precise location information for debugging.

    Attributes:
        subpackage_module: Added to each record, format: "{dirname}-{filename}"

    Example:
        >>> formatter = ModuleFormatter(
        ...     "%(asctime)s - %(levelname)s - [%(subpackage_module)s:%(lineno)d] - %(message)s"
        ... )
        >>> handler.setFormatter(formatter)
    """

    def format(self, record: logging.LogRecord) -> str:
        """Format the log record with module context.

        Args:
            record: The log record to format.

        Returns:
            Formatted log message string.
        """
        module_dir = os.path.basename(os.path.dirname(record.pathname))
        record.subpackage_module = f"{module_dir}-{record.filename}"
        return super().format(record)


class ActiveRecordFormatter(ModuleFormatter):
    """Default formatter for ActiveRecord logs.

    This is the standard formatter used by ActiveRecord for all internal
    logging. It extends ModuleFormatter with a predefined format string.

    Default Format:
        "%(asctime)s - %(levelname)s - [%(subpackage_module)s:%(lineno)d] - %(message)s"

    Example Output:
        2024-01-15 10:30:45,123 - DEBUG - [base-base.py:42] - Executing query: SELECT * FROM users

    Usage:
        >>> from rhosocial.activerecord.logging import ActiveRecordFormatter
        >>> formatter = ActiveRecordFormatter()
        >>> handler.setFormatter(formatter)

        # Or with custom format:
        >>> formatter = ActiveRecordFormatter(
        ...     "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        ... )
    """

    DEFAULT_FORMAT = "%(asctime)s - %(levelname)s - [%(subpackage_module)s:%(lineno)d] - %(message)s"

    def __init__(self, fmt: Optional[str] = None, datefmt: Optional[str] = None):
        """Initialize the formatter.

        Args:
            fmt: Custom format string. If None, uses DEFAULT_FORMAT.
            datefmt: Custom date format string. If None, uses default.
        """
        super().__init__(fmt or self.DEFAULT_FORMAT, datefmt)
