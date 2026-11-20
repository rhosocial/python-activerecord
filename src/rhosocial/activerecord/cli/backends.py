# src/rhosocial/activerecord/cli/backends.py
"""Backend and connection resolution for the model CLI.

The CLI is part of the core package and therefore knows nothing about the
packages that happen to ship a backend. A caller names the backend class and
the connection config class by their fully qualified Python names, and passes
connection configuration values as ``KEY=VALUE`` pairs.
"""

import dataclasses
import importlib
import inspect
import json
import types
import typing
from typing import Any, Dict, List, Optional, Tuple

from ..backend.base import AsyncStorageBackend, StorageBackend
from ..backend.config import ConnectionConfig
from ..backend.named_connection import NamedConnectionResolver
from .errors import EXIT_USAGE, BackendUnavailableError, CLIError

#: Annotation wrapper used by ``typing.Annotated``; absent on Python 3.8.
_ANNOTATED = getattr(typing, "Annotated", None)

#: Union origins understood by the config value coercion helper.
_UNION_ORIGINS = {typing.Union}
if getattr(types, "UnionType", None) is not None:  # Python 3.10+
    _UNION_ORIGINS.add(types.UnionType)


def _load_attribute(module_path: str, attribute: str, reference: str, label: str) -> Any:
    """Import a module and walk a dotted attribute path inside it."""
    try:
        module = importlib.import_module(module_path)
    except ImportError as exc:
        raise BackendUnavailableError(
            f'Cannot import the {label} "{reference}": {exc}',
            hint="Install the package that provides it and check the module path.",
        ) from None

    target = module
    try:
        for part in attribute.split("."):
            target = getattr(target, part)
    except AttributeError:
        raise BackendUnavailableError(
            f'The {label} module "{module_path}" has no attribute "{attribute}".'
        ) from None
    except ImportError as exc:
        raise BackendUnavailableError(
            f'Cannot import the {label} "{reference}": {exc}',
            hint="Install the optional package that provides it.",
        ) from None
    return target


def import_symbol(reference: str, label: str = "class") -> Any:
    """Import a class named as ``module:Class`` or as a dotted name.

    Both spellings are accepted: ``mypkg.backend:MyBackend`` (the same shape
    used by ``--model`` and ``--connection``) and ``mypkg.backend.MyBackend``.
    The dotted form is resolved by trying progressively shorter module paths,
    so a class may be nested several packages deep without the caller having
    to know where the module ends and the attribute begins.

    Args:
        reference: Fully qualified class name.
        label: What the value names, used in error messages.

    Returns:
        The imported object.

    Raises:
        BackendUnavailableError: When the module or attribute cannot be found.
    """
    reference = (reference or "").strip()
    if not reference:
        raise CLIError(f"The {label} reference is empty")

    if ":" in reference:
        module_path, attribute = reference.rsplit(":", 1)
        if not module_path or not attribute:
            raise CLIError(f'Invalid {label} "{reference}": expected the form module:Class')
        return _load_attribute(module_path, attribute, reference, label)

    parts = reference.split(".")
    if len(parts) < 2:
        raise CLIError(f'Invalid {label} "{reference}": expected the form module:Class')

    # A dotted name has no delimiter between the module and the attribute,
    # so try the longest importable module prefix first.
    for index in range(len(parts) - 1, 0, -1):
        module_path = ".".join(parts[:index])
        attribute = ".".join(parts[index:])
        try:
            target = importlib.import_module(module_path)
        except ImportError:
            continue

        try:
            for part in attribute.split("."):
                target = getattr(target, part)
        except AttributeError:
            raise BackendUnavailableError(
                f'The {label} module "{module_path}" has no attribute "{attribute}".'
            ) from None
        except ImportError as exc:
            raise BackendUnavailableError(
                f'Cannot import the {label} "{reference}": {exc}',
                hint="Install the optional package that provides it.",
            ) from None
        return target

    raise BackendUnavailableError(
        f'Cannot import the {label} "{reference}".',
        hint="Install the package that provides it and check the class path.",
    )


def load_backend_class(reference: str, is_async: bool):
    """Import and validate a backend class.

    Args:
        reference: Fully qualified backend class name.
        is_async: Whether the model uses the asynchronous API. The caller is
            expected to name the class that matches this mode.

    Returns:
        The backend class.

    Raises:
        CLIError: When the reference does not name a backend of the right kind.
        BackendUnavailableError: When the reference cannot be imported.
    """
    backend_class = import_symbol(reference, "backend class")
    if not isinstance(backend_class, type):
        raise CLIError(f'The backend reference "{reference}" does not name a class')

    expected = AsyncStorageBackend if is_async else StorageBackend
    if not issubclass(backend_class, expected):
        article = "an" if is_async else "a"
        kind = "asynchronous" if is_async else "synchronous"
        raise CLIError(f'The backend class "{reference}" is not {article} {kind} backend')
    return backend_class


def load_config_class(reference: str):
    """Import and validate a connection config class."""
    config_class = import_symbol(reference, "connection config class")
    if not isinstance(config_class, type):
        raise CLIError(f'The connection config reference "{reference}" does not name a class')
    if not issubclass(config_class, ConnectionConfig):
        raise CLIError(
            f'The connection config class "{reference}" is not a ConnectionConfig subclass'
        )
    return config_class


def _parse_options(option_values: Optional[List[str]]) -> List[Tuple[str, str]]:
    parsed = []
    for item in option_values or []:
        if "=" not in item:
            raise CLIError(f'Invalid --config "{item}": expected KEY=VALUE')
        key, value = item.split("=", 1)
        if not key:
            raise CLIError(f'Invalid --config "{item}": key is empty')
        parsed.append((key, value))
    return parsed


def _scalar_type(annotation) -> type:
    """Reduce an annotation such as ``Optional[int]`` to a scalar type."""
    origin = typing.get_origin(annotation)
    args = typing.get_args(annotation)
    if _ANNOTATED is not None and origin is _ANNOTATED and args:
        return _scalar_type(args[0])
    if origin in _UNION_ORIGINS:
        candidates = [arg for arg in args if arg is not type(None)]
        return _scalar_type(candidates[0]) if candidates else str
    if origin is not None:
        return str
    return annotation if isinstance(annotation, type) else str


def _coerce(value: str, annotation) -> Any:
    scalar = _scalar_type(annotation)
    if scalar is bool:
        return value.lower() in ("true", "yes", "1", "on")
    if scalar is int:
        try:
            return int(value)
        except ValueError:
            raise CLIError(f'Invalid integer value "{value}"') from None
    if scalar is float:
        try:
            return float(value)
        except ValueError:
            raise CLIError(f'Invalid number value "{value}"') from None
    return value


def _field_types(config_class) -> Dict[str, Any]:
    """Return the constructor's field names and their annotations."""
    try:
        dataclass_fields = dataclasses.fields(config_class)
    except TypeError:
        dataclass_fields = None

    if dataclass_fields is not None:
        try:
            hints = typing.get_type_hints(config_class)
        except (NameError, TypeError):
            hints = {}
        return {field.name: hints.get(field.name, field.type) for field in dataclass_fields}

    try:
        signature = inspect.signature(config_class)
        hints = typing.get_type_hints(config_class.__init__)
    except (TypeError, ValueError, NameError):
        return {}

    fields: Dict[str, Any] = {}
    for name, parameter in signature.parameters.items():
        if name == "self" or parameter.kind in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        ):
            continue
        fields[name] = hints.get(name, parameter.annotation)
    return fields


def _collect_config_updates(args, config_class) -> Dict[str, Any]:
    """Turn repeated ``--config KEY=VALUE`` options into constructor kwargs.

    A key that names a constructor field is coerced to that field's type.
    ``options.KEY=value`` and unknown keys are collected into ``config.options``,
    so a backend may accept driver-specific values without the CLI knowing them.
    """
    fields = _field_types(config_class)
    updates: Dict[str, Any] = {}
    extra_options: Dict[str, Any] = {}

    for key, value in _parse_options(getattr(args, "config", None)):
        if key == "options":
            try:
                parsed = json.loads(value)
            except json.JSONDecodeError:
                raise CLIError(
                    "--config options must be a JSON object; "
                    "use options.KEY=VALUE for individual entries"
                ) from None
            if not isinstance(parsed, dict):
                raise CLIError("--config options must be a JSON object")
            extra_options.update(parsed)
        elif key.startswith("options."):
            extra_options[key[len("options.") :]] = value
        elif key in fields and key != "options":
            updates[key] = _coerce(value, fields[key])
        else:
            extra_options[key] = value

    if extra_options:
        updates["options"] = extra_options
    return updates


def _build_config(args, config_class) -> ConnectionConfig:
    values = _collect_config_updates(args, config_class)
    try:
        config = config_class(**values)
    except TypeError as exc:
        raise CLIError(f"Cannot build connection config: {exc}") from None
    if not isinstance(config, ConnectionConfig):
        raise CLIError(
            f'"{config_class.__name__}" produced {type(config).__name__}, ' "not a ConnectionConfig"
        )
    return config


def _apply_overrides(config: ConnectionConfig, args) -> ConnectionConfig:
    updates = _collect_config_updates(args, type(config))
    if not updates:
        return config
    if "options" in updates:
        merged = dict(getattr(config, "options", {}) or {})
        merged.update(updates["options"])
        updates["options"] = merged

    clone = getattr(config, "clone", None)
    if callable(clone):
        return clone(**updates)

    try:
        base = config.to_dict()
    except (AttributeError, TypeError):
        base = {}
    base.update(updates)
    try:
        return type(config)(**base)
    except TypeError as exc:
        raise CLIError(f"Cannot override connection config: {exc}") from None


def _load_named_connection(qualified_name: str) -> ConnectionConfig:
    if ":" not in qualified_name:
        raise CLIError(f'Invalid --connection "{qualified_name}": expected module:callable')
    module_path, attr_name = qualified_name.rsplit(":", 1)
    resolver_name = f"{module_path}.{attr_name}"
    try:
        resolver = NamedConnectionResolver(resolver_name).load()
        config = resolver.resolve()
    except Exception as exc:
        raise CLIError(f'Cannot resolve --connection "{qualified_name}": {exc}') from exc
    if not isinstance(config, ConnectionConfig):
        raise CLIError(
            f'--connection "{qualified_name}" returned {type(config).__name__}, '
            "not a ConnectionConfig"
        )
    return config


def _validate_backend_class(backend_class, is_async: bool, source: str) -> None:
    expected = AsyncStorageBackend if is_async else StorageBackend
    if not issubclass(backend_class, expected):
        article = "an" if is_async else "a"
        kind = "asynchronous" if is_async else "synchronous"
        raise CLIError(
            f"{source} selected {backend_class.__name__}, which is not " f"{article} {kind} backend"
        )


def resolve_connection(model, is_async: bool, args):
    """Resolve the connection config and backend class for one command.

    Each half is resolved independently:

    * backend class: ``--backend-class``, otherwise the model's own
      ``configure()``.
    * connection config: ``--connection``, ``--config-class`` with ``--config``
      values, otherwise the model's own ``configure()``.

    The two halves may come from different sources, so a named connection can
    supply credentials while the model supplies its backend class.

    Returns:
        Tuple of (config, backend_class).

    Raises:
        CLIError: When a required half is missing or the two inputs conflict.
    """
    backend_reference = getattr(args, "backend_class", None)
    if backend_reference:
        backend_class = load_backend_class(backend_reference, is_async)
    else:
        backend_class = model.backend_class()
        if backend_class is None:
            raise CLIError(
                f"{model.__name__} has no backend class. Pass --backend-class "
                "MODULE:CLASS, or call configure() in the model module."
            )
        _validate_backend_class(backend_class, is_async, f"{model.__name__}'s configuration")

    connection_reference = getattr(args, "connection", None)
    config_reference = getattr(args, "config_class", None)
    if connection_reference and config_reference:
        raise CLIError("Use --connection or --config-class, not both")

    if connection_reference:
        config = _apply_overrides(_load_named_connection(connection_reference), args)
    elif config_reference:
        config = _build_config(args, load_config_class(config_reference))
    else:
        config = model.connection_config()
        if config is None:
            raise CLIError(
                f"{model.__name__} has no connection config. Pass --config-class "
                "MODULE:CLASS with --config KEY=VALUE, pass --connection, or call "
                "configure() in the model module."
            )
        if not isinstance(config, ConnectionConfig):
            raise CLIError(f"{model.__name__} has an invalid connection configuration")
        config = _apply_overrides(config, args)

    return config, backend_class


def resolve_connection_without_model(is_async: bool, args):
    """Resolve a connection without a model to fall back on.

    Module-level migration functions never touch a model, so requiring
    ``--model`` just to obtain credentials is noise.  When there is no model,
    the backend class and one config source must be named explicitly.

    Returns:
        Tuple of (config, backend_class).

    Raises:
        CLIError: When ``--backend-class`` or a config source is missing, or
            both config sources are given.
    """
    backend_reference = getattr(args, "backend_class", None)
    if not backend_reference:
        raise CLIError(
            "No model supplies a connection. Pass --backend-class MODULE:CLASS, "
            "and either --connection MODULE:CALLABLE or --config-class "
            "MODULE:CLASS with --config KEY=VALUE.",
            exit_code=EXIT_USAGE,
        )
    backend_class = load_backend_class(backend_reference, is_async)
    _validate_backend_class(backend_class, is_async, "--backend-class")

    connection_reference = getattr(args, "connection", None)
    config_reference = getattr(args, "config_class", None)
    if connection_reference and config_reference:
        raise CLIError("Use --connection or --config-class, not both", exit_code=EXIT_USAGE)

    if connection_reference:
        return _apply_overrides(_load_named_connection(connection_reference), args), backend_class
    if config_reference:
        return _build_config(args, load_config_class(config_reference)), backend_class

    raise CLIError(
        "No model supplies a connection. Pass --connection MODULE:CALLABLE or "
        "--config-class MODULE:CLASS with --config KEY=VALUE.",
        exit_code=EXIT_USAGE,
    )
