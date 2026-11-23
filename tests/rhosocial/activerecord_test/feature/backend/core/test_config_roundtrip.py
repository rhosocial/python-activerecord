# tests/rhosocial/activerecord_test/feature/backend/core/test_config_roundtrip.py
"""DB-free contract tests for BaseConfig to_dict/clone options round-trip."""

from rhosocial.activerecord.backend.config import BaseConfig


def test_options_are_nested_in_to_dict():
    cfg = BaseConfig(options={"timezone": "UTC", "sslmode": "require"})
    data = cfg.to_dict()
    assert isinstance(data.get("options"), dict)
    assert data["options"] == {"timezone": "UTC", "sslmode": "require"}
    # options keys are NOT flattened to top level
    assert "timezone" not in data
    assert "sslmode" not in data


def test_empty_options_omitted():
    assert "options" not in BaseConfig().to_dict()


def test_clone_preserves_options():
    cfg = BaseConfig(options={"timezone": "UTC", "sslmode": "require"})
    cloned = cfg.clone()
    assert cloned.options == cfg.options
    assert cloned is not cfg


def test_clone_merges_option_updates():
    cfg = BaseConfig(options={"timezone": "UTC", "sslmode": "require"})
    cloned = cfg.clone(options={"timezone": "Asia/Shanghai"})
    assert cloned.options == {"timezone": "Asia/Shanghai", "sslmode": "require"}
    assert cfg.options == {"timezone": "UTC", "sslmode": "require"}  # original untouched


def test_nested_roundtrip_survives_two_hops():
    cfg = BaseConfig(options={"timezone": "UTC"})
    twice = cfg.clone().clone()
    assert twice.options == {"timezone": "UTC"}


def test_option_key_colliding_with_field_is_not_lost():
    # A bare field named 'timezone' must not swallow an option of the same name.
    # BaseConfig has no 'timezone' field, so the nested form keeps it in options.
    cfg = BaseConfig(options={"timezone": "UTC"})
    assert cfg.clone().options["timezone"] == "UTC"
