# tests/rhosocial/activerecord_test/logging_module/test_sensitive_value.py
"""SensitiveValue wrapping and unwrapping."""

from rhosocial.activerecord.logging import (
    MASKERS,
    SensitiveValue,
    default_mask,
    register_masker,
    unwrap_sensitive,
)


def test_sensitive_value_masks_representation_but_keeps_value():
    value = SensitiveValue("secret")
    assert value.unwrap() == "secret"
    assert value.masked() == "***MASKED***"
    assert "secret" not in repr(value)


def test_unwrap_sensitive_handles_nested_containers():
    value = {
        "password": SensitiveValue("secret"),
        "items": (SensitiveValue("one"), "two"),
    }
    assert unwrap_sensitive(value) == {"password": "secret", "items": ("one", "two")}


def test_named_masker_is_resolved():
    register_masker("test-masker", lambda value: f"<{len(str(value))} chars>")
    value = SensitiveValue("secret", masker="test-masker")
    assert value.masked() == "<6 chars>"


def test_unknown_masker_falls_back_to_default():
    value = SensitiveValue("secret", masker="does-not-exist")
    assert value.masked() == "***MASKED***"
    assert MASKERS["default"] is default_mask
