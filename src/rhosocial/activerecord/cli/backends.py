# src/rhosocial/activerecord/cli/backends.py
"""Built-in backend registry and connection resolution for the model CLI."""

import dataclasses
import importlib
import importlib.util
import typing
from typing import Any, Dict, List, Optional, Tuple

from ..backend.base import AsyncStorageBackend, StorageBackend
from ..backend.config import ConnectionConfig
from ..backend.named_connection import NamedConnectionResolver
from .errors import CLIError, BackendUnavailableError


class BackendSpec:
    """Everything needed to import and construct one built-in backend.

    Attributes:
        name: The value accepted by ``--backend``.
        package: Distribution that provides the backend, or None when it ships
            inside the core package.
        module: Import path for the sync and async backend classes.
        sync_class: Class name of the synchronous backend.
        async_class: Class name of the asynchronous backend, if one exists.
        config_module: Import path for the connection config class.
        config_class: Class name of the connection config.
    """

    def __init__(
        self,
        name: str,
        package: Optional[str],
        module: str,
        sync_class: str,
        async_class: Optional[str],
        config_module: str,
        config_class: str,
    ):
        self.name = name
        self.package = package
        self.module = module
        self.sync_class = sync_class
        self.async_class = async_class
        self.config_module = config_module
        self.config_class = config_class


_IMPL = "rhosocial.activerecord.backend.impl."

#: The v1 registry. It is explicit on purpose: scanning the package layout
#: would turn the directory structure into an undocumented plugin protocol.
BACKENDS: Dict[str, BackendSpec] = {
    "sqlite": BackendSpec(
        "sqlite",
        None,
        _IMPL + "sqlite.backend",
        "SQLiteBackend",
        "AsyncSQLiteBackend",
        _IMPL + "sqlite.config",
        "SQLiteConnectionConfig",
    ),
    "mysql": BackendSpec(
        "mysql",
        "rhosocial-activerecord-mysql",
        _IMPL + "mysql.backend",
        "MySQLBackend",
        "AsyncMySQLBackend",
        _IMPL + "mysql.config",
        "MySQLConnectionConfig",
    ),
    "mariadb": BackendSpec(
        "mariadb",
        "rhosocial-activerecord-mariadb",
        _IMPL + "mariadb.backend",
        "MariaDBBackend",
        "AsyncMariaDBBackend",
        _IMPL + "mariadb.config",
        "MariaDBConnectionConfig",
    ),
    "postgres": BackendSpec(
        "postgres",
        "rhosocial-activerecord-postgres",
        _IMPL + "postgres.backend",
        "PostgresBackend",
        "AsyncPostgresBackend",
        _IMPL + "postgres.config",
        "PostgresConnectionConfig",
    ),
    "sqlserver": BackendSpec(
        "sqlserver",
        "rhosocial-activerecord-sqlserver",
        _IMPL + "sqlserver.backend",
        "SQLServerBackend",
        "AsyncSQLServerBackend",
        _IMPL + "sqlserver.config",
        "SQLServerConnectionConfig",
    ),
    "oracle": BackendSpec(
        "oracle",
        "rhosocial-activerecord-oracle",
        _IMPL + "oracle.backend",
        "OracleBackend",
        "AsyncOracleBackend",
        _IMPL + "oracle.config",
        "OracleConnectionConfig",
    ),
    "firebird": BackendSpec(
        "firebird",
        "rhosocial-activerecord-firebird",
        _IMPL + "firebird.backend",
        "FirebirdBackend",
        "AsyncFirebirdBackend",
        _IMPL + "firebird.config",
        "FirebirdConnectionConfig",
    ),
    "snowflake": BackendSpec(
        "snowflake",
        "rhosocial-activerecord-snowflake",
        _IMPL + "snowflake.backend",
        "SnowflakeBackend",
        "AsyncSnowflakeBackend",
        _IMPL + "snowflake.config",
        "SnowflakeConnectionConfig",
    ),
    "clickhouse": BackendSpec(
        "clickhouse",
        "rhosocial-activerecord-clickhouse",
        _IMPL + "clickhouse.backend",
        "ClickHouseBackend",
        "AsyncClickHouseBackend",
        _IMPL + "clickhouse.config",
        "ClickHouseConnectionConfig",
    ),
    "bigquery": BackendSpec(
        "bigquery",
        "rhosocial-activerecord-bigquery",
        _IMPL + "bigquery.backend",
        "BigQueryBackend",
        "AsyncBigQueryBackend",
        _IMPL + "bigquery.config",
        "BigQueryConnectionConfig",
    ),
}

_CONFIG_TO_BACKEND = {
    spec.config_class: name for name, spec in BACKENDS.items()
}

_CONNECTION_FLAGS = ("database", "host", "port", "user", "password")

try:
    _ANNOTATED = typing.Annotated
except AttributeError:  # Python 3.8
    _ANNOTATED = None


def install_hint(spec: BackendSpec) -> str:
    """Return the pip command that installs a backend package."""
    if spec.package is None:
        return "The SQLite backend ships with rhosocial-activerecord."
    return f"pip install {spec.package}"


def find_backend(name: str) -> BackendSpec:
    """Look up a backend by ``--backend`` name.

    Args:
        name: Backend name, case-insensitive.

    Returns:
        The matching registry entry.

    Raises:
        BackendUnavailableError: When the name is not in the registry.
    """
    spec = BACKENDS.get((name or "").lower())
    if spec is None:
        known = ", ".join(sorted(BACKENDS))
        raise BackendUnavailableError(
            f'Unsupported backend "{name}". Known backends: {known}'
        )
    return spec


def _module_available(module_path: str) -> bool:
    try:
        return importlib.util.find_spec(module_path) is not None
    except (ImportError, AttributeError, ValueError):
        return False


def ensure_backend_available(spec: BackendSpec) -> None:
    """Check that a backend package is installed before importing it."""
    if spec.package is not None and not _module_available(spec.module):
        raise BackendUnavailableError(
            f'Backend "{spec.name}" needs the {spec.package} package.',
            hint=install_hint(spec),
        )


def load_backend_class(spec: BackendSpec, is_async: bool):
    """Import the sync or async backend class from the registry."""
    ensure_backend_available(spec)
    class_name = spec.async_class if is_async else spec.sync_class
    if is_async and not class_name:
        raise BackendUnavailableError(
            f'Backend "{spec.name}" does not provide an asynchronous backend.'
        )
    try:
        module = importlib.import_module(spec.module)
        backend_class = getattr(module, class_name)
    except ImportError as exc:
        raise BackendUnavailableError(
            f'Cannot import backend "{spec.name}" ({class_name}): {exc}',
            hint=install_hint(spec),
        ) from None
    except AttributeError:
        raise BackendUnavailableError(
            f'Backend module "{spec.module}" has no class "{class_name}".'
        ) from None
    return backend_class


def load_config_class(spec: BackendSpec):
    """Import the connection config class from the registry."""
    ensure_backend_available(spec)
    try:
        module = importlib.import_module(spec.config_module)
        return getattr(module, spec.config_class)
    except ImportError as exc:
        raise BackendUnavailableError(
            f'Cannot import connection config for "{spec.name}": {exc}',
            hint=install_hint(spec),
        ) from None
    except AttributeError:
        raise BackendUnavailableError(
            f'Backend module "{spec.config_module}" has no class "{spec.config_class}".'
        ) from None


def infer_backend_name(config: ConnectionConfig) -> Optional[str]:
    """Infer the backend from a named connection's config type."""
    return _CONFIG_TO_BACKEND.get(type(config).__name__)


def _parse_options(option_values: Optional[List[str]]) -> List[Tuple[str, str]]:
    parsed = []
    for item in option_values or []:
        if "=" not in item:
            raise CLIError(f'Invalid --option "{item}": expected KEY=VALUE')
        key, value = item.split("=", 1)
        if not key:
            raise CLIError(f'Invalid --option "{item}": key is empty')
        parsed.append((key, value))
    return parsed


def _scalar_type(annotation) -> type:
    """Reduce an annotation such as ``Optional[int]`` to a scalar type."""
    origin = typing.get_origin(annotation)
    args = typing.get_args(annotation)
    if _ANNOTATED is not None and origin is _ANNOTATED and args:
        return _scalar_type(args[0])
    if origin is typing.Union:
        candidates = [arg for arg in args if arg is not type(None)]
        return candidates[0] if candidates and isinstance(candidates[0], type) else str
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


def _field_names(config_class) -> Dict[str, Any]:
    try:
        fields = dataclasses.fields(config_class)
    except TypeError:
        return {}
    try:
        hints = typing.get_type_hints(config_class)
    except (NameError, TypeError):
        hints = {}
    return {field.name: hints.get(field.name, field.type) for field in fields}


def _collect_overrides(args, config_class) -> Dict[str, Any]:
    fields = _field_names(config_class)
    updates: Dict[str, Any] = {}
    mapping = {
        "database": getattr(args, "database", None),
        "host": getattr(args, "host", None),
        "port": getattr(args, "port", None),
        "username": getattr(args, "user", None),
        "password": getattr(args, "password", None),
    }
    for field_name, value in mapping.items():
        if value is not None and field_name in fields:
            updates[field_name] = _coerce(value, fields[field_name])

    extra_options = {}
    for key, value in _parse_options(getattr(args, "option", None)):
        if key in fields and key != "options":
            updates[key] = _coerce(value, fields[key])
        else:
            extra_options[key] = value
    if extra_options:
        updates["options"] = extra_options
    return updates


def _apply_overrides(config: ConnectionConfig, args) -> ConnectionConfig:
    updates = _collect_overrides(args, type(config))
    if not updates:
        return config
    if "options" in updates:
        merged = dict(getattr(config, "options", {}) or {})
        merged.update(updates["options"])
        updates["options"] = merged
    return config.clone(**updates)


def _build_config(args, config_class) -> ConnectionConfig:
    fields = _field_names(config_class)
    values: Dict[str, Any] = {}
    mapping = {
        "database": getattr(args, "database", None),
        "host": getattr(args, "host", None),
        "port": getattr(args, "port", None),
        "username": getattr(args, "user", None),
        "password": getattr(args, "password", None),
    }
    for field_name, value in mapping.items():
        if value is not None and field_name in fields:
            values[field_name] = _coerce(value, fields[field_name])

    extra_options = {}
    for key, value in _parse_options(getattr(args, "option", None)):
        if key in fields and key != "options":
            values[key] = _coerce(value, fields[key])
        else:
            extra_options[key] = value
    if extra_options:
        values["options"] = extra_options

    try:
        return config_class(**values)
    except TypeError as exc:
        raise CLIError(f"Cannot build connection config: {exc}") from None


def _load_named_connection(qualified_name: str) -> ConnectionConfig:
    if ":" not in qualified_name:
        raise CLIError(
            f'Invalid --connection "{qualified_name}": expected module:callable'
        )
    module_path, attr_name = qualified_name.rsplit(":", 1)
    resolver_name = f"{module_path}.{attr_name}"
    try:
        resolver = NamedConnectionResolver(resolver_name).load()
        config = resolver.resolve()
    except Exception as exc:
        raise CLIError(f'Cannot resolve --connection "{qualified_name}": {exc}') from None
    if not isinstance(config, ConnectionConfig):
        raise CLIError(
            f'--connection "{qualified_name}" returned {type(config).__name__}, '
            "not a ConnectionConfig"
        )
    return config


def _has_new_connection(args) -> bool:
    if getattr(args, "backend", None) or getattr(args, "connection", None):
        return True
    return any(getattr(args, flag, None) is not None for flag in _CONNECTION_FLAGS)


def _validate_backend_class(backend_class, is_async: bool, source: str) -> None:
    expected = AsyncStorageBackend if is_async else StorageBackend
    if not issubclass(backend_class, expected):
        kind = "asynchronous" if is_async else "synchronous"
        raise CLIError(
            f"{source} selected {backend_class.__name__}, which is not a {kind} backend"
        )


def resolve_connection(model, is_async: bool, args):
    """Resolve the connection config and backend class for one command.

    Priority: explicit ``--connection``, explicit ``--backend`` or connection
    flags, then the model module's own configuration.

    Returns:
        Tuple of (config, backend_class, spec) where ``spec`` is None when the
        model's existing configuration is reused.
    """
    if getattr(args, "connection", None):
        config = _load_named_connection(args.connection)
        inferred = infer_backend_name(config)
        explicit = getattr(args, "backend", None)
        if explicit and inferred and explicit.lower() != inferred:
            raise CLIError(
                f'--backend "{explicit}" conflicts with the config returned by '
                f'--connection, which belongs to "{inferred}"'
            )
        name = explicit.lower() if explicit else inferred
        if not name:
            raise BackendUnavailableError(
                "Cannot infer the backend from --connection; add --backend"
            )
        spec = find_backend(name)
        backend_class = load_backend_class(spec, is_async)
        _validate_backend_class(backend_class, is_async, f'Backend "{name}"')
        return _apply_overrides(config, args), backend_class, spec

    if _has_new_connection(args):
        name = (getattr(args, "backend", None) or "sqlite").lower()
        spec = find_backend(name)
        config_class = load_config_class(spec)
        if name == "sqlite" and getattr(args, "database", None) is None:
            raise CLIError(
                "The sqlite backend needs --database (a file path or :memory:)"
            )
        backend_class = load_backend_class(spec, is_async)
        _validate_backend_class(backend_class, is_async, f'Backend "{name}"')
        return _build_config(args, config_class), backend_class, spec

    config = getattr(model, "__connection_config__", None)
    backend_class = getattr(model, "__backend_class__", None)
    if config is None or backend_class is None:
        raise CLIError(
            f'{model.__name__} has no database configuration. Pass --backend and '
            "connection flags, or --connection, or call configure() in the model module."
        )
    if not isinstance(config, ConnectionConfig):
        raise CLIError(f"{model.__name__} has an invalid connection configuration")
    _validate_backend_class(backend_class, is_async, f"{model.__name__}'s configuration")
    return _apply_overrides(config, args), backend_class, None
