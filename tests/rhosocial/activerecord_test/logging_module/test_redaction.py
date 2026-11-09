# tests/rhosocial/activerecord_test/logging_module/test_redaction.py
"""Query-parameter redaction semantics."""

from rhosocial.activerecord.logging import (
    LoggingConfig,
    LogDataKind,
    LogDataMode,
    LogPayload,
)


def test_dict_query_params_mask_default_sensitive_fields():
    config = LoggingConfig()
    payload = LogPayload(
        {"password": "secret", "name": "alice"},
        LogDataKind.QUERY_PARAMS,
    )
    redacted = config.redact(payload)
    assert redacted["password"] == "***MASKED***"
    assert redacted["name"] == "alice"


def test_positional_params_without_names_only_reveal_shape():
    config = LoggingConfig()
    payload = LogPayload(("alice", "secret"), LogDataKind.QUERY_PARAMS)
    redacted = config.redact(payload)
    assert redacted == "<2 params: str, str>"


def test_named_params_mask_explicit_sensitive_names():
    config = LoggingConfig()
    payload = LogPayload(
        ("alice", "secret"),
        LogDataKind.QUERY_PARAMS,
        param_names=("name", "password"),
        sensitive_names=("password",),
    )
    redacted = config.redact(payload)
    assert redacted["name"] == "alice"
    assert redacted["password"] == "***MASKED***"


def test_hidden_mode_never_exposes_values():
    config = LoggingConfig()
    payload = LogPayload(
        ("alice", "secret"),
        LogDataKind.QUERY_PARAMS,
        mode=LogDataMode.HIDDEN,
    )
    assert config.redact(payload) == "<hidden>"


def test_keys_only_mode_shows_types():
    config = LoggingConfig()
    payload = LogPayload(
        ("alice", "secret"),
        LogDataKind.QUERY_PARAMS,
        param_names=("name", "password"),
        mode=LogDataMode.KEYS_ONLY,
    )
    redacted = config.redact(payload)
    assert redacted["name"] == "<str>"
    assert redacted["password"] == "<str>"


def test_error_payload_names_the_type_and_truncates_message():
    config = LoggingConfig()
    payload = LogPayload(
        ValueError("bad value " + "x" * 200),
        LogDataKind.ERROR,
    )
    redacted = config.redact(payload)
    assert redacted["error_type"] == "ValueError"
    assert "truncated" in redacted["error_message"]
