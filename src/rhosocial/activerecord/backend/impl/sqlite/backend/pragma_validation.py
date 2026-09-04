# src/rhosocial/activerecord/backend/impl/sqlite/backend/pragma_validation.py
"""
Whitelist-only PRAGMA name and value validation.

PRAGMA statements cannot be parameterized, so every name and value that is
concatenated into a PRAGMA statement MUST pass through this module. There
are no regular expressions here by policy: values are validated against
explicit enumerations and character-by-character membership in literal
character sets.

Validation layers (in order):
1. Name must exist in the PRAGMA registry (get_pragma_info).
2. The PRAGMA must not be read-only.
3. Value must satisfy the PRAGMA's declared whitelist:
   - enumerated values (allowed_values): member check, case-insensitive for
     string entries, canonical spelling of the registry entry is emitted;
   - bool pragmas: standard spellings ("1"/"ON"/"TRUE"/"YES" etc.) mapped to
     canonical "1"/"0";
   - int pragmas: decimal integer literal, checked character-by-character.
4. Final guard: the canonical value string may only contain characters from
    a literal safe set before it is inlined into the statement.
"""

from typing import Any, Optional, Tuple

from ..pragma import get_pragma_info

# Canonical spellings for boolean PRAGMAs. Anything else is rejected.
_TRUE_SPELLINGS = frozenset({"1", "ON", "TRUE", "YES"})
_FALSE_SPELLINGS = frozenset({"0", "OFF", "FALSE", "NO"})

# Characters permitted in a PRAGMA value after canonicalization. This is a
# literal set, not a pattern: each character of the value is checked for
# membership.
_SAFE_VALUE_CHARS = frozenset(
    "abcdefghijklmnopqrstuvwxyz"
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    "0123456789"
    "_+-. "
)

_DECIMAL_DIGITS = frozenset("0123456789")


class PragmaValidationError(ValueError):
    """Raised when a PRAGMA name or value fails whitelist validation."""


def _is_int_literal(text: str) -> bool:
    """Check whether text is a decimal integer literal, char by char."""
    body = text[1:] if text[:1] in ("+", "-") else text
    if not body:
        return False
    return all(ch in _DECIMAL_DIGITS for ch in body)


def _canonical_from_enum(info, raw: str) -> Optional[str]:
    """Match raw against info.allowed_values, returning the registered spelling.

    String entries compare case-insensitively; int entries compare as decimal
    literals; bool entries accept the standard spellings and canonicalize to
    "1"/"0".
    """
    allowed = info.allowed_values
    if not allowed:
        return None
    bool_typed = info.value_type is bool or any(
        isinstance(v, bool) for v in allowed
    )
    if bool_typed:
        if raw.upper() in _TRUE_SPELLINGS:
            return "1"
        if raw.upper() in _FALSE_SPELLINGS:
            return "0"
    for entry in allowed:
        if isinstance(entry, int):
            if raw == str(entry):
                return str(entry)
        elif raw.upper() == str(entry).upper():
            return str(entry)
    return None


def validate_pragma_value(pragma_key: str, pragma_value: Any) -> Tuple[str, str]:
    """Validate a PRAGMA name/value pair against the registry whitelist.

    Args:
        pragma_key: PRAGMA name (must be a registry member).
        pragma_value: Value to set. Accepted forms depend on the PRAGMA's
            declared whitelist: bool spellings, int literals, or enum
            members (compared case-insensitively in string form).

    Returns:
        Tuple of (canonical_name, canonical_value_string) safe to inline
        into a PRAGMA statement.

    Raises:
        PragmaValidationError: If the name is unknown, the PRAGMA is
            read-only, or the value is not permitted.
    """
    info = get_pragma_info(pragma_key)
    if info is None:
        raise PragmaValidationError(f"Unknown PRAGMA: {pragma_key}")
    if info.read_only:
        raise PragmaValidationError(f"PRAGMA {pragma_key} is read-only and cannot be set")

    raw = str(pragma_value).strip()

    # Enumerated whitelist takes precedence when declared.
    canonical = _canonical_from_enum(info, raw)
    if canonical is None:
        if info.allowed_values:
            raise PragmaValidationError(
                f"Invalid value {pragma_value!r} for PRAGMA {pragma_key}. "
                f"Allowed values: {info.allowed_values}"
            )
        if info.value_type is bool:
            raise PragmaValidationError(
                f"Invalid value {pragma_value!r} for PRAGMA {pragma_key}. "
                f"Allowed boolean spellings: {sorted(_TRUE_SPELLINGS | _FALSE_SPELLINGS)}"
            )
        if info.value_type is int:
            if not _is_int_literal(raw):
                raise PragmaValidationError(
                    f"Invalid value {pragma_value!r} for PRAGMA {pragma_key}. "
                    f"Expected a decimal integer literal."
                )
            canonical = raw
        else:
            raise PragmaValidationError(
                f"PRAGMA {pragma_key} has no value whitelist; refusing to set {pragma_value!r}"
            )

    # Final guard: every character of the canonical value must be in the
    # literal safe set. Names come from the registry itself, so they are
    # trusted, but this keeps the concatenated statement inert even if a
    # registry entry were ever edited unsafely.
    if any(ch not in _SAFE_VALUE_CHARS for ch in canonical):
        raise PragmaValidationError(
            f"Unsafe characters in value {canonical!r} for PRAGMA {pragma_key}"
        )

    return info.name, canonical


def apply_pragma_statement(pragma_key: str, pragma_value: Any) -> Tuple[str, str]:
    """Build a safe 'PRAGMA name = value' statement from a validated pair.

    Returns:
        Tuple of (statement, canonical_value_string).

    Raises:
        PragmaValidationError: See validate_pragma_value.
    """
    name, canonical = validate_pragma_value(pragma_key, pragma_value)
    return f"PRAGMA {name} = {canonical}", canonical


def validate_config_pragmas(pragmas: dict) -> None:
    """Validate a whole config pragmas dict (same rules as set_pragma).

    Raises:
        PragmaValidationError: On the first invalid entry.
    """
    for key, value in pragmas.items():
        validate_pragma_value(key, value)


__all__ = [
    "PragmaValidationError",
    "validate_pragma_value",
    "apply_pragma_statement",
    "validate_config_pragmas",
]
