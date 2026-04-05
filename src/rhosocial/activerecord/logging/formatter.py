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
    showing the fully qualified module name and line number where the log
    message originated. This provides precise location information for debugging.

    Attributes:
        subpackage_module: Added to each record, format: "{module_name}:{lineno}"

    Example:
        >>> formatter = ModuleFormatter(
        ...     "%(asctime)s - %(levelname)s - [%(subpackage_module)s] - %(message)s"
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
        # Extract fully qualified module name from pathname
        module_name = self._extract_module_name(record.pathname, record.filename)
        record.subpackage_module = f"{module_name}:{record.lineno}"
        return super().format(record)

    def _extract_module_name(self, pathname: str, filename: str) -> str:
        """Extract fully qualified module name from file path.

        Args:
            pathname: Full path to the source file.
            filename: The filename portion (with extension).

        Returns:
            Fully qualified module name (e.g., 'rhosocial.activerecord.backend.base').
        """
        # Normalize the path
        path_parts = pathname.replace('\\', '/').split('/')

        # Find 'rhosocial' in the path followed by 'activerecord'
        # This ensures we get the correct package root, not a project directory name
        for i in range(len(path_parts) - 1, -1, -1):
            if path_parts[i] == 'rhosocial':
                # Only accept if followed by 'activerecord'
                if i + 1 < len(path_parts) and path_parts[i + 1] == 'activerecord':
                    # Build module name: rhosocial.activerecord.xxx.filename (without .py)
                    base_name = os.path.splitext(filename)[0]
                    module_parts = path_parts[i:-1] + [base_name]
                    return '.'.join(module_parts)

        # Fallback: use filename without extension
        return os.path.splitext(filename)[0]


class ActiveRecordFormatter(ModuleFormatter):
    """Default formatter for ActiveRecord logs.

    This is the standard formatter used by ActiveRecord for all internal
    logging. It extends ModuleFormatter with a predefined format string.

    Default Format:
        "%(asctime)s - %(levelname)s - [%(subpackage_module)s] - %(message)s"

    Example Output:
        2024-01-15 10:30:45,123 - DEBUG - [rhosocial.activerecord.backend.base:42] - Executing query: SELECT * FROM users

    Usage:
        >>> from rhosocial.activerecord.logging import ActiveRecordFormatter
        >>> formatter = ActiveRecordFormatter()
        >>> handler.setFormatter(formatter)

        # Or with custom format:
        >>> formatter = ActiveRecordFormatter(
        ...     "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
        ... )
    """

    DEFAULT_FORMAT = "%(asctime)s - %(levelname)s - [%(subpackage_module)s] - %(message)s"

    def __init__(self, fmt: Optional[str] = None, datefmt: Optional[str] = None):
        """Initialize the formatter.

        Args:
            fmt: Custom format string. If None, uses DEFAULT_FORMAT.
            datefmt: Custom date format string. If None, uses default.
        """
        super().__init__(fmt or self.DEFAULT_FORMAT, datefmt)
