# src/rhosocial/activerecord/logging/redaction.py
"""Log payload redaction helpers.

Query parameters are often positional tuples without field names.  The
summarizer can mask dictionary keys, but it cannot infer that the third item in
a tuple is a password.  This module keeps that distinction explicit through
``LogPayload`` and ``ParamMeta``.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable, Dict, Mapping, Optional, Sequence

from .summarizer import DataSummarizer


class LogDataKind(str, Enum):
    """Kinds of data a log call may carry."""

    QUERY_PARAMS = "query_params"
    ROW_DATA = "row_data"
    CONFIG = "config"
    ERROR = "error"


@dataclass(frozen=True)
class ParamMeta:
    """Metadata for one query parameter.

    Attributes:
        index: Position in the parameter sequence.
        field: Model field or column name, when known.
        sensitive: Whether the value must be masked.
        masker: Optional field-specific masker.
    """

    index: int
    field: Optional[str] = None
    sensitive: bool = False
    masker: Optional[Callable[[Any], Any]] = None


@dataclass
class LogPayload:
    """Data plus the semantics needed to redact it."""

    data: Any
    kind: LogDataKind
    param_names: Optional[Sequence[str]] = None
    sensitive_names: Optional[Sequence[str]] = None
    mode: Optional[Any] = None
    param_meta: Optional[Sequence["ParamMeta"]] = None



def default_mask(value: Any) -> str:
    """Return the default masked value."""
    return "***MASKED***"


@dataclass(frozen=True)
class SensitiveValue:
    """A query value whose log representation is masked.

    The wrapped value is still sent to the database; callers must use
    :func:`unwrap_sensitive` before building SQL or binding parameters.
    """

    value: Any
    masker: Any = "default"

    def unwrap(self) -> Any:
        """Return the original value."""
        return self.value

    def masked(self) -> Any:
        """Return the masked value."""
        masker = get_masker(self.masker) or default_mask
        return masker(self.value)

    def __repr__(self) -> str:
        return repr(self.masked())

    def __str__(self) -> str:
        return str(self.masked())


def unwrap_sensitive(value: Any) -> Any:
    """Recursively unwrap ``SensitiveValue`` instances.

    Lists, tuples and dictionaries are rebuilt with unwrapped contents so a
    query builder can use the result for SQL assembly and parameter binding.
    """
    if isinstance(value, SensitiveValue):
        return value.unwrap()
    if isinstance(value, Mapping):
        return {key: unwrap_sensitive(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return tuple(unwrap_sensitive(item) for item in value)
    if isinstance(value, list):
        return [unwrap_sensitive(item) for item in value]
    if isinstance(value, set):
        return {unwrap_sensitive(item) for item in value}
    return value


#: Name -> masker registry.  ``Sensitive`` declarations and
#: ``SensitiveValue`` instances refer to these names.
MASKERS: Dict[str, Callable[[Any], Any]] = {
    "default": default_mask,
}


def register_masker(name: str, masker: Callable[[Any], Any]) -> None:
    """Register a named masker used by model fields and query values."""
    if not name:
        raise ValueError("masker name must be non-empty")
    if not callable(masker):
        raise TypeError("masker must be callable")
    MASKERS[name] = masker


def get_masker(masker: Any) -> Optional[Callable[[Any], Any]]:
    """Return a callable masker from a name, callable, or ``None``."""
    if masker is None:
        return None
    if callable(masker):
        return masker
    if isinstance(masker, str):
        return MASKERS.get(masker)
    raise TypeError(f"masker must be a name or callable, got {type(masker).__name__}")


def _mode_value(mode: Any) -> Optional[str]:
    if mode is None:
        return None
    return getattr(mode, "value", mode)


def _type_summary(values: Sequence[Any]) -> str:
    types = ", ".join(type(value).__name__ for value in values)
    return f"<{len(values)} params: {types}>"


def _meta_parameter_names(payload: LogPayload) -> tuple:
    """Return names, sensitive names and explicit maskers from param metadata."""
    names = []
    sensitive_names = []
    maskers = {}
    for index, meta in enumerate(payload.param_meta or ()):
        name = meta.field or f"param{index}"
        names.append(name)
        if meta.sensitive or meta.masker is not None:
            sensitive_names.append(name)
            if meta.masker is not None:
                maskers[name] = meta.masker
    return names, sensitive_names, maskers


def _redact_query_params(
    config: Any,
    payload: LogPayload,
    mode: Any,
    logger_name: Optional[str],
) -> Any:
    data = payload.data
    mode_value = _mode_value(mode)

    if mode_value == "hidden":
        return "<hidden>"
    if mode_value == "full":
        return data

    if payload.param_meta is not None and isinstance(data, (list, tuple)):
        names, sensitive_names, maskers = _meta_parameter_names(payload)
        named = {name: value for name, value in zip(names, data)}
        summarizer: DataSummarizer = config.get_summarizer(logger_name)
        for name in sensitive_names:
            masker = get_masker(maskers.get(name))
            value = named[name]
            named[name] = (
                masker(value) if masker is not None
                else summarizer.mask_value(name, value)
            )
        if mode_value == "keys_only":
            return {name: f"<{type(value).__name__}>" for name, value in named.items()}
        return config.summarize_data(named, logger_name)

    if payload.param_names is not None and isinstance(data, (list, tuple)):
        named = {
            name: value for name, value in zip(payload.param_names, data)
        }
        summarizer: DataSummarizer = config.get_summarizer(logger_name)
        for name in payload.sensitive_names or ():
            if name in named:
                named[name] = summarizer.mask_value(name, named[name])
        if mode_value == "keys_only":
            return {name: f"<{type(value).__name__}>" for name, value in named.items()}
        return config.summarize_data(named, logger_name)

    if isinstance(data, Mapping):
        return config.summarize_data(data, logger_name)

    if mode_value == "keys_only":
        return _type_summary(data)

    # Positional sequence without names: never print values by default.
    return _type_summary(data)


def redact_payload(
    config: Any,
    payload: LogPayload,
    mode: Any = None,
    logger_name: Optional[str] = None,
) -> Any:
    """Redact a payload according to its kind and the effective log mode."""
    if payload.kind is LogDataKind.QUERY_PARAMS:
        return _redact_query_params(config, payload, mode, logger_name)

    if payload.kind is LogDataKind.ROW_DATA:
        return config.summarize_data(payload.data, logger_name)

    if payload.kind is LogDataKind.CONFIG:
        mode_value = _mode_value(mode)
        if mode_value == "hidden":
            return "<hidden>"
        if mode_value == "keys_only":
            if isinstance(payload.data, Mapping):
                return {
                    key: f"<{type(value).__name__}>"
                    for key, value in payload.data.items()
                }
            return config.get_summarizer(logger_name).summarize_keys_only(
                payload.data
            )
        return config.summarize_data(payload.data, logger_name)

    if payload.kind is LogDataKind.ERROR:
        data = payload.data
        summarizer = config.get_summarizer(logger_name)
        if isinstance(data, BaseException):
            return {
                "error_type": type(data).__name__,
                "error_message": summarizer.summarize(str(data)),
            }
        return summarizer.summarize(str(data))

    return config.summarize_data(payload.data, logger_name)
