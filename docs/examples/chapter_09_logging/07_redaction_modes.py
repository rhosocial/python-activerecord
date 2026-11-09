"""
Logging Chapter: Example 7 - Query parameter redaction

This example shows how LogPayload and ParamMeta semantics keep query values
out of INFO logs, and how SensitiveValue is unwrapped before execution.
"""

from rhosocial.activerecord.logging import (
    LogDataKind,
    LogDataMode,
    LoggingConfig,
    LogPayload,
    SensitiveValue,
    register_masker,
    unwrap_sensitive,
)


def show(label: str, value: object) -> None:
    print(f"{label}: {value}")


def main() -> None:
    print("=" * 60)
    print("Example 7: Query parameter redaction")
    print("=" * 60)

    config = LoggingConfig()

    show(
        "dict params",
        config.redact(
            LogPayload(
                {"id": 1, "password": "secret", "name": "alice"},
                LogDataKind.QUERY_PARAMS,
            )
        ),
    )
    show(
        "positional, no names",
        config.redact(LogPayload(("alice", "secret"), LogDataKind.QUERY_PARAMS)),
    )
    show(
        "positional, named",
        config.redact(
            LogPayload(
                ("alice", "secret"),
                LogDataKind.QUERY_PARAMS,
                param_names=("name", "password"),
                sensitive_names=("password",),
            )
        ),
    )
    show(
        "hidden mode",
        config.redact(
            LogPayload(
                ("alice", "secret"),
                LogDataKind.QUERY_PARAMS,
                mode=LogDataMode.HIDDEN,
            )
        ),
    )
    show(
        "keys-only mode",
        config.redact(
            LogPayload(
                ("alice", "secret"),
                LogDataKind.QUERY_PARAMS,
                param_names=("name", "password"),
                mode=LogDataMode.KEYS_ONLY,
            )
        ),
    )

    register_masker("phone", lambda value: value[:3] + "****" + value[-2:])
    phone = SensitiveValue("13800138000", masker="phone")
    show("SensitiveValue repr", repr(phone))
    show("SensitiveValue unwrap", unwrap_sensitive(phone))

    nested = {
        "name": "alice",
        "contact": {"phone": SensitiveValue("13800138000", masker="phone")},
        "items": (SensitiveValue("secret"), "plain"),
    }
    show("nested unwrap", unwrap_sensitive(nested))

    print("\nLogDataMode.FULL intentionally disables masking; use it only for controlled debugging.")


if __name__ == "__main__":
    main()
