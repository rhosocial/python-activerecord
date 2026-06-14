# tests/rhosocial/activerecord_test/feature/backend/sqlite_pragma_extension/test_extension_detection.py
"""
Tests for SQLite extension detection via dialect.
"""


from rhosocial.activerecord.backend.impl.sqlite import SQLiteDialect, SQLiteExtensionInfo
from rhosocial.activerecord.backend.impl.sqlite.mixins.extension import ExtensionType


class TestExtensionType:
    """Test ExtensionType enum."""

    def test_extension_types_exist(self):
        """Test that all extension types are defined."""
        assert hasattr(ExtensionType, "BUILTIN")
        assert hasattr(ExtensionType, "LOADABLE")
        assert hasattr(ExtensionType, "VTABLE")

    def test_extension_type_values(self):
        """Test extension type values."""
        assert ExtensionType.BUILTIN.value == "builtin"
        assert ExtensionType.LOADABLE.value == "loadable"
        assert ExtensionType.VTABLE.value == "vtable"


class TestDialectExtensionDetection:
    """Test extension detection through the dialect."""

    def test_detect_extensions_returns_dict(self):
        d = SQLiteDialect(version=(3, 35, 0))
        exts = d.detect_extensions()
        assert isinstance(exts, dict)
        assert "fts5" in exts
        assert "rtree" in exts
        assert "geopoly" in exts
        assert "json1" in exts

    def test_detect_extensions_info_type(self):
        d = SQLiteDialect(version=(3, 35, 0))
        ext = d.detect_extensions()["fts5"]
        assert isinstance(ext, SQLiteExtensionInfo)
        assert ext.name == "fts5"
        assert ext.extension_type == ExtensionType.BUILTIN
        assert ext.installed is True

    def test_is_extension_available_fts5(self):
        d = SQLiteDialect(version=(3, 35, 0))
        assert d.is_extension_available("fts5") is True

    def test_is_extension_available_fts5_old_version(self):
        d = SQLiteDialect(version=(3, 8, 0))
        assert d.is_extension_available("fts5") is False

    def test_is_extension_available_rtree(self):
        d = SQLiteDialect(version=(3, 35, 0))
        assert d.is_extension_available("rtree") is True

    def test_is_extension_available_geopoly(self):
        d = SQLiteDialect(version=(3, 35, 0))
        assert d.is_extension_available("geopoly") is True

    def test_is_extension_available_geopoly_old_version(self):
        d = SQLiteDialect(version=(3, 25, 0))
        assert d.is_extension_available("geopoly") is False

    def test_is_extension_available_json1(self):
        d = SQLiteDialect(version=(3, 38, 0))
        assert d.is_extension_available("json1") is True

    def test_is_extension_available_json1_old_version(self):
        d = SQLiteDialect(version=(3, 37, 0))
        assert d.is_extension_available("json1") is False

    def test_get_extension_info(self):
        d = SQLiteDialect(version=(3, 35, 0))
        info = d.get_extension_info("fts5")
        assert info is not None
        assert info.name == "fts5"
        assert info.installed is True

    def test_get_extension_info_not_found(self):
        d = SQLiteDialect(version=(3, 35, 0))
        assert d.get_extension_info("nonexistent") is None

    def test_check_extension_feature(self):
        d = SQLiteDialect(version=(3, 35, 0))
        assert d.check_extension_feature("fts5", "full_text_search") is True
        assert d.check_extension_feature("fts5", "bm25_ranking") is True

    def test_check_extension_feature_trigram(self):
        d_old = SQLiteDialect(version=(3, 33, 0))
        assert d_old.check_extension_feature("fts5", "trigram_tokenizer") is False
        d_new = SQLiteDialect(version=(3, 34, 0))
        assert d_new.check_extension_feature("fts5", "trigram_tokenizer") is True

    def test_get_supported_features(self):
        d = SQLiteDialect(version=(3, 35, 0))
        features = d.get_supported_extension_features("fts5")
        assert "full_text_search" in features
        assert "bm25_ranking" in features
        assert "trigram_tokenizer" in features

    def test_get_supported_features_trigram_boundary(self):
        d = SQLiteDialect(version=(3, 33, 0))
        features = d.get_supported_extension_features("fts5")
        assert "trigram_tokenizer" not in features

    def test_detect_unknown_extension(self):
        d = SQLiteDialect(version=(3, 35, 0))
        assert d.is_extension_available("unknown") is False
        assert d.get_extension_info("unknown") is None
        assert d.check_extension_feature("unknown", "anything") is False
