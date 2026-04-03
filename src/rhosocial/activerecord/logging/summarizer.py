# src/rhosocial/activerecord/logging/summarizer.py
"""Data summarizer for logging large data structures.

This module provides the DataSummarizer class that intelligently truncates
and summarizes data structures for logging purposes, preventing overly long
log messages while preserving useful information.
"""

from dataclasses import dataclass, field
from typing import Any, Set, Optional, Dict, List, Union, Callable


MaskPlaceholderType = Union[str, Callable[[Any], Any]]
"""Type for mask_placeholder: either a string or a callable that transforms the value."""


@dataclass
class SummarizerConfig:
    """Configuration for DataSummarizer.

    Attributes:
        max_string_length: Maximum length for string values before truncation.
        max_bytes_length: Maximum length for bytes values before truncation.
        max_dict_items: Maximum number of dict/list items to display.
        max_depth: Maximum nesting depth for recursive summarization.
        sensitive_fields: Set of field names to mask (case-insensitive).
        string_placeholder: Placeholder for truncated strings.
        bytes_placeholder: Placeholder for truncated bytes.
        dict_placeholder: Placeholder for truncated collections.
        mask_placeholder: Placeholder for masked sensitive fields. Can be a string
            or a callable that takes the original value and returns the masked result.
        field_maskers: Dictionary mapping field names to custom masker functions.
            Each masker is a callable that takes the original value and returns
            the masked result. Field names are case-insensitive.
        show_type_hint: Whether to show type hints in truncation messages.
    """

    max_string_length: int = 100
    max_bytes_length: int = 64
    max_dict_items: int = 10
    max_depth: int = 5
    sensitive_fields: Set[str] = field(
        default_factory=lambda: {
            'password', 'passwd', 'pwd',
            'token', 'access_token', 'refresh_token', 'auth_token',
            'secret', 'secret_key', 'api_key', 'apikey',
            'credential', 'credentials',
            'private_key', 'privatekey',
        }
    )
    string_placeholder: str = "...[truncated, {length} chars total]"
    bytes_placeholder: str = "...[{length} bytes total]"
    dict_placeholder: str = "...[{count} more items]"
    mask_placeholder: MaskPlaceholderType = "***MASKED***"
    field_maskers: Dict[str, Callable[[Any], Any]] = field(default_factory=dict)
    show_type_hint: bool = True


class DataSummarizer:
    """Intelligent data summarizer for logging.

    This class provides methods to summarize complex data structures
    for logging purposes. It handles:
    - String truncation
    - Bytes representation
    - Collection size limiting
    - Sensitive field masking
    - Recursive depth limiting

    Example:
        >>> config = SummarizerConfig(max_string_length=50)
        >>> summarizer = DataSummarizer(config)
        >>> data = {"name": "John", "bio": "A" * 1000, "password": "secret123"}
        >>> print(summarizer.summarize(data))
        {"name": "John", "bio": "AAAAA...[truncated, 1000 chars total]", "password": "***MASKED***"}
    """

    def __init__(self, config: Optional[SummarizerConfig] = None):
        """Initialize the summarizer.

        Args:
            config: Optional configuration. Uses defaults if not provided.
        """
        self.config = config or SummarizerConfig()
        self._sensitive_fields_lower = {
            f.lower() for f in self.config.sensitive_fields
        }
        # Build lowercase mapping for field_maskers
        self._field_maskers_lower = {
            k.lower(): v for k, v in self.config.field_maskers.items()
        }

    def _is_sensitive_field(self, field_name: str) -> bool:
        """Check if a field name is sensitive.

        Args:
            field_name: The field name to check.

        Returns:
            True if the field is considered sensitive.
        """
        return field_name.lower() in self._sensitive_fields_lower

    def _mask_field(self, field_name: str, value: Any) -> Any:
        """Mask a sensitive field value.

        Uses field-specific masker if available, otherwise uses the global
        mask_placeholder (which can be a string or callable).

        Args:
            field_name: The field name (used to look up field-specific masker).
            value: The original value to mask.

        Returns:
            The masked value.
        """
        field_lower = field_name.lower()

        # Check for field-specific masker first
        if field_lower in self._field_maskers_lower:
            masker = self._field_maskers_lower[field_lower]
            try:
                return masker(value)
            except Exception:
                # If masker fails, fall back to default
                pass

        # Use global mask_placeholder
        if callable(self.config.mask_placeholder):
            try:
                return self.config.mask_placeholder(value)
            except Exception:
                return "***MASKED***"
        else:
            return self.config.mask_placeholder

    def _truncate_string(self, value: str) -> str:
        """Truncate a string if it exceeds max length.

        Args:
            value: The string to potentially truncate.

        Returns:
            Truncated string with placeholder if needed.
        """
        if len(value) <= self.config.max_string_length:
            return value

        truncated = value[:self.config.max_string_length]
        placeholder = self.config.string_placeholder.format(length=len(value))
        return truncated + placeholder

    def _truncate_bytes(self, value: bytes) -> str:
        """Represent bytes with truncation.

        Args:
            value: The bytes to represent.

        Returns:
            String representation with truncation if needed.
        """
        length = len(value)
        if length <= self.config.max_bytes_length:
            return repr(value)

        preview = value[:self.config.max_bytes_length]
        placeholder = self.config.bytes_placeholder.format(length=length)
        return f"{preview!r}{placeholder}"

    def summarize(
        self,
        data: Any,
        depth: int = 0,
        keys_only: bool = False
    ) -> Any:
        """Recursively summarize a data structure.

        Args:
            data: The data to summarize.
            depth: Current recursion depth.
            keys_only: If True, only show keys for dicts (no values).

        Returns:
            Summarized version of the data.
        """
        # Check depth limit
        if depth > self.config.max_depth:
            return f"<max depth exceeded, type: {type(data).__name__}>"

        # Handle None
        if data is None:
            return None

        # Handle strings (must check before sequences)
        if isinstance(data, str):
            return self._truncate_string(data)

        # Handle bytes
        if isinstance(data, bytes):
            return self._truncate_bytes(data)

        # Handle other primitives
        if isinstance(data, (int, float, bool)):
            return data

        # Handle dictionaries
        if isinstance(data, dict):
            return self._summarize_dict(data, depth, keys_only)

        # Handle lists, tuples, sets
        if isinstance(data, (list, tuple, set)):
            return self._summarize_sequence(data, depth, keys_only)

        # Handle other types with repr
        try:
            repr_str = repr(data)
            if len(repr_str) > self.config.max_string_length:
                type_hint = f"<{type(data).__name__}: " if self.config.show_type_hint else ""
                return f"{type_hint}{repr_str[:self.config.max_string_length]}...[truncated]>"
            return repr_str
        except Exception:
            return f"<{type(data).__name__}: repr failed>"

    def _summarize_dict(
        self,
        data: dict,
        depth: int,
        keys_only: bool
    ) -> dict:
        """Summarize a dictionary.

        Args:
            data: The dictionary to summarize.
            depth: Current recursion depth.
            keys_only: If True, values are replaced with type hints.

        Returns:
            Summarized dictionary.
        """
        result = {}
        items = list(data.items())

        for i, (key, value) in enumerate(items):
            # Check if we've exceeded max items
            if i >= self.config.max_dict_items:
                remaining = len(items) - i
                placeholder = self.config.dict_placeholder.format(count=remaining)
                result[self.config.dict_placeholder.split('{')[0].strip() or '...'] = f"{remaining} more items"
                break

            # Mask sensitive fields
            str_key = str(key)
            if self._is_sensitive_field(str_key):
                result[key] = self._mask_field(str_key, value)
            elif keys_only:
                # Only show key with value type hint
                result[key] = f"<{type(value).__name__}>"
            else:
                # Recursively summarize value
                result[key] = self.summarize(value, depth + 1, keys_only)

        return result

    def _summarize_sequence(
        self,
        data: Union[list, tuple, set],
        depth: int,
        keys_only: bool
    ) -> Union[list, str]:
        """Summarize a sequence (list, tuple, or set).

        Args:
            data: The sequence to summarize.
            depth: Current recursion depth.
            keys_only: If True, items are replaced with type hints.

        Returns:
            Summarized sequence as list (original type info preserved in hint).
        """
        result = []
        items = list(data)

        for i, item in enumerate(items):
            if i >= self.config.max_dict_items:
                remaining = len(items) - i
                result.append(f"...[{remaining} more items]")
                break

            if keys_only:
                result.append(f"<{type(item).__name__}>")
            else:
                result.append(self.summarize(item, depth + 1, keys_only))

        # Preserve type information
        if isinstance(data, tuple):
            return f"tuple({result})"
        elif isinstance(data, set):
            return f"set({result})"
        return result

    def summarize_keys_only(self, data: Any) -> Any:
        """Summarize data showing only keys/field names.

        This is useful for INFO level logging where you want to know
        what fields are present without their values.

        Args:
            data: The data to summarize.

        Returns:
            Summarized data with only keys visible.
        """
        return self.summarize(data, depth=0, keys_only=True)

    def mask_sensitive(self, data: Any) -> Any:
        """Mask sensitive fields in data without truncation.

        This preserves all data structure and sizes, only masking
        fields that match sensitive field names.

        Args:
            data: The data to process.

        Returns:
            Data with sensitive fields masked.
        """
        if isinstance(data, dict):
            result = {}
            for key, value in data.items():
                str_key = str(key)
                if self._is_sensitive_field(str_key):
                    result[key] = self._mask_field(str_key, value)
                else:
                    result[key] = self.mask_sensitive(value)
            return result
        elif isinstance(data, (list, tuple)):
            processed = [self.mask_sensitive(item) for item in data]
            return type(data)(processed) if isinstance(data, tuple) else processed
        elif isinstance(data, set):
            return {self.mask_sensitive(item) for item in data}
        return data


# Default global instance
_default_summarizer: Optional[DataSummarizer] = None


def get_default_summarizer() -> DataSummarizer:
    """Get the default global DataSummarizer instance.

    Returns:
        The default DataSummarizer instance.
    """
    global _default_summarizer
    if _default_summarizer is None:
        _default_summarizer = DataSummarizer()
    return _default_summarizer


def set_default_summarizer(summarizer: DataSummarizer) -> None:
    """Set the default global DataSummarizer instance.

    Args:
        summarizer: The DataSummarizer instance to use as default.
    """
    global _default_summarizer
    _default_summarizer = summarizer


def summarize_data(data: Any, keys_only: bool = False) -> Any:
    """Convenience function to summarize data using the default summarizer.

    Args:
        data: The data to summarize.
        keys_only: If True, only show keys without values.

    Returns:
        Summarized data.
    """
    summarizer = get_default_summarizer()
    if keys_only:
        return summarizer.summarize_keys_only(data)
    return summarizer.summarize(data)
