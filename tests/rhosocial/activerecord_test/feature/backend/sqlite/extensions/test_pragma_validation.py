# tests/rhosocial/activerecord_test/feature/backend/sqlite/extensions/test_pragma_validation.py
"""Unit tests for the whitelist-only PRAGMA validation module."""

import pytest

from rhosocial.activerecord.backend.impl.sqlite.backend.pragma_validation import (
    PragmaValidationError,
    apply_pragma_statement,
    validate_config_pragmas,
    validate_pragma_value,
)


class TestValidatePragmaValue:
    """Whitelist validation branches."""

    def test_unknown_pragma_rejected(self):
        with pytest.raises(PragmaValidationError, match="Unknown PRAGMA"):
            validate_pragma_value("not_a_pragma", 1)

    def test_read_only_pragma_rejected(self):
        # integrity_check is an information pragma
        with pytest.raises(PragmaValidationError, match="read-only"):
            validate_pragma_value("integrity_check", 1)

    def test_enum_accepts_registered_spelling(self):
        name, value = validate_pragma_value("journal_mode", "WAL")
        assert name == "journal_mode"
        assert value == "WAL"

    def test_enum_accepts_case_insensitive_spelling(self):
        name, value = validate_pragma_value("journal_mode", "wal")
        assert value == "WAL"

    def test_enum_rejects_non_member(self):
        with pytest.raises(PragmaValidationError, match="Allowed values"):
            validate_pragma_value("journal_mode", "BOGUS")

    def test_enum_bool_spelling_canonicalizes(self):
        _, value = validate_pragma_value("foreign_keys", "ON")
        assert value == "1"
        _, value = validate_pragma_value("foreign_keys", "OFF")
        assert value == "0"
        _, value = validate_pragma_value("foreign_keys", "false")
        assert value == "0"

    def test_enum_bool_rejects_other_words(self):
        with pytest.raises(PragmaValidationError, match="Allowed values"):
            validate_pragma_value("foreign_keys", "MAYBE")

    def test_int_accepts_literal(self):
        _, value = validate_pragma_value("cache_size", "-2000")
        assert value == "-2000"
        _, value = validate_pragma_value("cache_size", 5000)
        assert value == "5000"

    def test_int_accepts_whitespace_padding(self):
        _, value = validate_pragma_value("cache_size", " 5000 ")
        assert value == "5000"

    def test_int_rejects_identifier(self):
        with pytest.raises(PragmaValidationError, match="decimal integer"):
            validate_pragma_value("cache_size", "abc")

    def test_int_rejects_injection(self):
        with pytest.raises(PragmaValidationError, match="decimal integer"):
            validate_pragma_value("cache_size", "1; DROP TABLE users")

    def test_int_rejects_scientific_notation(self):
        with pytest.raises(PragmaValidationError, match="decimal integer"):
            validate_pragma_value("cache_size", "1e9")

    def test_statement_pragma_enum(self):
        # wal_checkpoint is a statement-like PRAGMA with an enum whitelist
        _, value = validate_pragma_value("wal_checkpoint", "passive")
        assert value == "PASSIVE"

    def test_read_uncommitted_registry_member(self):
        _, value = validate_pragma_value("read_uncommitted", 1)
        assert value == "1"

    def test_query_only_registry_member(self):
        _, value = validate_pragma_value("query_only", "ON")
        assert value == "1"


class TestApplyPragmaStatement:
    """Statement building."""

    def test_builds_statement(self):
        stmt, value = apply_pragma_statement("journal_mode", "WAL")
        assert stmt == "PRAGMA journal_mode = WAL"
        assert value == "WAL"

    def test_boolean_canonicalized_in_statement(self):
        stmt, value = apply_pragma_statement("foreign_keys", "ON")
        assert stmt == "PRAGMA foreign_keys = 1"
        assert value == "1"

    def test_invalid_value_propagates(self):
        with pytest.raises(PragmaValidationError):
            apply_pragma_statement("synchronous", "SOMETIMES")


class TestValidateConfigPragmas:
    """Whole-dict validation."""

    def test_valid_dict_passes(self):
        validate_config_pragmas(
            {
                "foreign_keys": "ON",
                "journal_mode": "WAL",
                "synchronous": "FULL",
                "wal_autocheckpoint": "1000",
                "wal_checkpoint": "FULL",
            }
        )

    def test_invalid_entry_raises(self):
        with pytest.raises(PragmaValidationError, match="Unknown PRAGMA"):
            validate_config_pragmas({"foreign_keys": "ON", "bogus_pragma": 1})

    def test_invalid_value_raises(self):
        with pytest.raises(PragmaValidationError, match="Allowed values"):
            validate_config_pragmas({"synchronous": "WHENEVER"})


class TestEdgeBranches:
    """Cover remaining validation branches."""

    def test_empty_int_string_rejected(self):
        with pytest.raises(PragmaValidationError, match="decimal integer"):
            validate_pragma_value("cache_size", "+")

    def test_bool_without_enum_rejected(self):
        # No registry pragma is bool-typed without allowed_values today; force
        # the branch through a fake info lookup.
        from unittest.mock import patch
        from rhosocial.activerecord.backend.impl.sqlite.pragma.base import PragmaInfo, PragmaCategory
        fake = PragmaInfo(
            name="fake_bool", category=PragmaCategory.CONFIGURATION, description="x",
            read_only=False, value_type=bool, allowed_values=None,
        )
        with patch(
            "rhosocial.activerecord.backend.impl.sqlite.backend.pragma_validation.get_pragma_info",
            return_value=fake,
        ):
            with pytest.raises(PragmaValidationError, match="Allowed boolean spellings"):
                validate_pragma_value("fake_bool", "MAYBE")

    def test_str_type_without_whitelist_refused(self):
        from unittest.mock import patch
        from rhosocial.activerecord.backend.impl.sqlite.pragma.base import PragmaInfo, PragmaCategory
        fake = PragmaInfo(
            name="fake_str", category=PragmaCategory.CONFIGURATION, description="x",
            read_only=False, value_type=str, allowed_values=None,
        )
        with patch(
            "rhosocial.activerecord.backend.impl.sqlite.backend.pragma_validation.get_pragma_info",
            return_value=fake,
        ):
            with pytest.raises(PragmaValidationError, match="no value whitelist"):
                validate_pragma_value("fake_str", "anything")

    def test_unsafe_characters_guard(self):
        from unittest.mock import patch
        from rhosocial.activerecord.backend.impl.sqlite.pragma.base import PragmaInfo, PragmaCategory
        # Enum entry whose registered spelling contains a character outside
        # the safe set triggers the final guard.
        fake = PragmaInfo(
            name="fake_guard", category=PragmaCategory.CONFIGURATION, description="x",
            read_only=False, value_type=str, allowed_values=["A'B"],
        )
        with patch(
            "rhosocial.activerecord.backend.impl.sqlite.backend.pragma_validation.get_pragma_info",
            return_value=fake,
        ):
            with pytest.raises(PragmaValidationError, match="Unsafe characters"):
                validate_pragma_value("fake_guard", "A'B")

    def test_enum_int_entry_matched(self):
        # page_size has int-typed enum entries
        _, value = validate_pragma_value("page_size", 4096)
        assert value == "4096"

    def test_enum_bool_false_entry_via_loop(self):
        # Registry with bool entries hits the loop path (not the fast path).
        from unittest.mock import patch
        from rhosocial.activerecord.backend.impl.sqlite.pragma.base import PragmaInfo, PragmaCategory
        fake = PragmaInfo(
            name="fake_bool2", category=PragmaCategory.CONFIGURATION, description="x",
            read_only=False, value_type=bool, allowed_values=[False, True],
        )
        with patch(
            "rhosocial.activerecord.backend.impl.sqlite.backend.pragma_validation.get_pragma_info",
            return_value=fake,
        ):
            assert validate_pragma_value("fake_bool2", "off")[1] == "0"
            assert validate_pragma_value("fake_bool2", "YES")[1] == "1"
