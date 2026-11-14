# tests/rhosocial/activerecord_test/feature/backend/sqlite/extensions/test_ext_extension_surface.py
"""The SQLite extension registry: detection, availability and feature gates.

Each dialect instance owns its own runtime parameters, so a fresh dialect per
test is already isolated from the others.
"""

from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
from rhosocial.activerecord.backend.impl.sqlite.mixins.extension import ExtensionType

LOW = (3, 8, 0)
HIGH = (3, 53, 0)


def test_compile_options_map_known_and_unknown_extensions():
    dialect = SQLiteDialect(version=LOW)
    # No compile options: the version check is the only evidence there is.
    assert dialect._is_extension_enabled_in_build("fts5") is True

    dialect.set_runtime_param("compile_options", {"ENABLE_FTS5": True})
    assert dialect._is_extension_enabled_in_build("fts5") is True
    assert dialect._is_extension_enabled_in_build("rtree") is False

    # An extension the map has no option for cannot be ruled out by the build.
    assert dialect._is_extension_enabled_in_build("mystery") is True


def test_detect_extensions_reports_version_and_build():
    low = SQLiteDialect(version=LOW).detect_extensions()
    assert low["fts5"].installed is False
    assert low["fts5"].features == []
    assert low["fts4"].deprecated is True
    assert low["fts4"].successor == "fts5"
    assert low["fts5"].extension_type is ExtensionType.BUILTIN
    assert low["rtree"].extension_type is ExtensionType.VTABLE

    high = SQLiteDialect(version=HIGH).detect_extensions()
    assert high["fts5"].installed is True
    assert high["fts5"].min_version == (3, 9, 0)
    assert "trigram_tokenizer" in high["fts5"].features


def test_is_extension_available_gates_name_build_and_version():
    low = SQLiteDialect(version=LOW)
    assert low.is_extension_available("mystery") is False
    assert low.is_extension_available("fts5") is False  # 3.8.0 < 3.9.0

    high = SQLiteDialect(version=HIGH)
    assert high.is_extension_available("fts5") is True

    high.set_runtime_param("compile_options", {"ENABLE_OTHER": True})
    assert high.is_extension_available("fts5") is False


def test_get_extension_info_reports_deprecation():
    assert SQLiteDialect(version=HIGH).get_extension_info("mystery") is None

    fts4 = SQLiteDialect(version=HIGH).get_extension_info("fts4")
    assert fts4.name == "fts4"
    assert fts4.deprecated is True
    assert fts4.successor == "fts5"
    assert "full_text_search" in fts4.features


def test_check_extension_feature_gates_name_build_and_feature():
    low = SQLiteDialect(version=LOW)
    assert low.check_extension_feature("mystery", "anything") is False
    assert low.check_extension_feature("fts5", "full_text_search") is False

    high = SQLiteDialect(version=HIGH)
    assert high.check_extension_feature("fts5", "full_text_search") is True
    assert high.check_extension_feature("fts5", "not_a_feature") is False

    blocked = SQLiteDialect(version=HIGH)
    blocked.set_runtime_param("compile_options", {"ENABLE_OTHER": True})
    assert blocked.check_extension_feature("fts5", "full_text_search") is False


def test_supported_extension_features_listing():
    assert SQLiteDialect(version=HIGH).get_supported_extension_features("mystery") == []

    assert SQLiteDialect(version=LOW).get_supported_extension_features("fts5") == []

    high = SQLiteDialect(version=HIGH).get_supported_extension_features("fts5")
    assert "full_text_search" in high
    assert "trigram_tokenizer" in high
