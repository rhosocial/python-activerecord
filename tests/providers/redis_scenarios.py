# tests/providers/redis_scenarios.py
"""Redis cache scenario loader from YAML configuration.

Provides a clean, file-based approach to configure Redis connections
for testing and benchmarking.  Users can add their own scenarios
to ``redis_scenarios.yaml`` or create a separate YAML file following
the same format.

Usage::

    from providers.redis_scenarios import get_redis_scenario

    # Get a pre-defined scenario
    config = get_redis_scenario("default")

    # List all available scenarios
    scenarios = get_enabled_redis_scenarios()

The returned *config* is a :class:`RedisConfig` instance that can be
passed directly to ``RedisCache(config=...)`` or used to create a
raw ``redis.Redis`` client.
"""

import os
import re
from typing import Dict

import yaml

from rhosocial.activerecord.relation.cache_backends import RedisConfig

_FILE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "redis_scenarios.yaml")

# Cache for loaded scenarios (module-level singleton)
_SCENARIOS: Dict[str, dict] = {}


def _interpolate_env(value) -> str:
    """Replace ``${VAR_NAME}`` / ``${VAR_NAME:-default}`` with env var values."""
    if not isinstance(value, str):
        return value

    def _replace(match):
        var_name = match.group(1)
        default = match.group(2)
        return os.environ.get(var_name, default or "")

    return re.sub(r"\$\{(\w+)(?::-([^}]*))?\}", _replace, value)


def _load_scenarios() -> Dict[str, dict]:
    """Load and interpolate all scenarios from the YAML file.

    Returns empty dict when the file does not exist (it is optional and
    lives in ``tests/config/``, which is git-excluded).
    """
    if not os.path.exists(_FILE_PATH):
        return {}

    with open(_FILE_PATH, "r") as f:
        raw = yaml.safe_load(f)

    if not raw:
        return {}

    return {name: {k: _interpolate_env(v) for k, v in conf.items()} for name, conf in raw.items()}


def register_redis_scenario(name: str, config: dict):
    """Register (or override) a Redis scenario at runtime."""
    _SCENARIOS[name] = {k: _interpolate_env(v) for k, v in config.items()}


def _to_int(value) -> int:
    """Convert a value to int, handling strings from YAML/env."""
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip():
        return int(value)
    return 0


def get_redis_scenario(name: str) -> "RedisConfig":
    """Return a :class:`RedisConfig` for the named scenario.

    Falls back to ``"default"`` if *name* is not found.
    String values that should be integers (port, db, socket_connect_timeout)
    are automatically converted.
    """
    if not _SCENARIOS:
        _SCENARIOS.update(_load_scenarios())

    if not _SCENARIOS:
        raise FileNotFoundError(
            f"No Redis scenarios loaded. Create {_FILE_PATH} with a "
            f"'default' entry, or call register_redis_scenario() first."
        )
    raw = _SCENARIOS.get(name)
    if raw is None:
        raw = _SCENARIOS.get("default")
    if raw is None:
        raise KeyError(f"No Redis scenario named '{name}' and no 'default' scenario found")

    # Strip None-valued keys so RedisConfig defaults apply, convert types
    cleaned = {}
    for k, v in raw.items():
        if v is None:
            continue
        # Convert known integer fields (handles string values from YAML/env)
        if k in ("port", "db", "socket_connect_timeout"):
            v = _to_int(v)
        cleaned[k] = v

    return RedisConfig(**cleaned)


def get_enabled_redis_scenarios() -> Dict[str, dict]:
    """Return the raw dict of all loaded scenario names → config dicts."""
    if not _SCENARIOS:
        _SCENARIOS.update(_load_scenarios())
    return dict(_SCENARIOS)


# Load scenarios at import time (one-time cost)
_SCENARIOS.update(_load_scenarios())
