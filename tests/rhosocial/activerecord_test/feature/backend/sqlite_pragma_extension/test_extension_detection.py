# tests/rhosocial/activerecord_test/feature/backend/sqlite_pragma_extension/test_extension_detection.py
"""
Tests for SQLite extension detection framework.
"""
import pytest

from rhosocial.activerecord.backend.impl.sqlite.extension import (
    ExtensionType,
    SQLiteExtensionRegistry,
    get_registry,
    reset_registry,
    KNOWN_EXTENSIONS,
)
from rhosocial.activerecord.backend.impl.sqlite.extension.extensions import (
    FTS5Extension,
    get_fts5_extension,
    JSON1Extension,
    get_json1_extension,
    RTreeExtension,
    get_rtree_extension,
    GeopolyExtension,
    get_geopoly_extension,
)


class TestExtensionType:
    """Test ExtensionType enum."""

    def test_extension_types_exist(self):
        """Test that all extension types are defined."""
        assert hasattr(ExtensionType, 'BUILTIN')
        assert hasattr(ExtensionType, 'LOADABLE')
        assert hasattr(ExtensionType, 'VTABLE')

    def test_extension_type_values(self):
        """Test extension type values."""
        assert ExtensionType.BUILTIN.value == "builtin"
        assert ExtensionType.LOADABLE.value == "loadable"
        assert ExtensionType.VTABLE.value == "vtable"


class TestKnownExtensions:
    """Test known extensions configuration."""

    def test_fts5_in_known_extensions(self):
        """Test FTS5 is in known extensions."""
        assert 'fts5' in KNOWN_EXTENSIONS
        assert KNOWN_EXTENSIONS['fts5']['type'] == ExtensionType.BUILTIN

    def test_fts4_in_known_extensions(self):
        """Test FTS4 is in known extensions and marked deprecated."""
        assert 'fts4' in KNOWN_EXTENSIONS
        assert KNOWN_EXTENSIONS['fts4']['deprecated'] is True
        assert KNOWN_EXTENSIONS['fts4']['successor'] == 'fts5'

    def test_json1_in_known_extensions(self):
        """Test JSON1 is in known extensions."""
        assert 'json1' in KNOWN_EXTENSIONS
        assert KNOWN_EXTENSIONS['json1']['type'] == ExtensionType.BUILTIN

    def test_rtree_in_known_extensions(self):
        """Test R-Tree is in known extensions."""
        assert 'rtree' in KNOWN_EXTENSIONS
        assert KNOWN_EXTENSIONS['rtree']['type'] == ExtensionType.VTABLE

    def test_geopoly_in_known_extensions(self):
        """Test Geopoly is in known extensions."""
        assert 'geopoly' in KNOWN_EXTENSIONS


class TestFTS5Extension:
    """Test FTS5 extension implementation."""

    def test_fts5_extension_creation(self):
        """Test FTS5 extension can be created."""
        ext = FTS5Extension()
        assert ext.name == 'fts5'
        assert ext.extension_type == ExtensionType.BUILTIN
        assert ext.deprecated is False

    def test_fts5_availability(self):
        """Test FTS5 availability check."""
        ext = get_fts5_extension()
        
        # FTS5 is available since 3.9.0
        assert ext.is_available((3, 9, 0)) is True
        assert ext.is_available((3, 35, 0)) is True
        assert ext.is_available((4, 0, 0)) is True
        
        # Not available before 3.9.0
        assert ext.is_available((3, 8, 0)) is False

    def test_fts5_feature_check(self):
        """Test FTS5 feature checking."""
        ext = get_fts5_extension()
        
        # Basic features available since 3.9.0
        assert ext.check_feature('full_text_search', (3, 9, 0)) is True
        assert ext.check_feature('bm25_ranking', (3, 9, 0)) is True
        
        # Trigram tokenizer available since 3.34.0
        assert ext.check_feature('trigram_tokenizer', (3, 33, 0)) is False
        assert ext.check_feature('trigram_tokenizer', (3, 34, 0)) is True

    def test_fts5_get_info(self):
        """Test FTS5 get_info method."""
        ext = get_fts5_extension()
        info = ext.get_info((3, 35, 0))
        
        assert info.name == 'fts5'
        assert info.extension_type == ExtensionType.BUILTIN
        assert info.installed is True
        assert info.deprecated is False

    def test_fts5_supported_tokenizers(self):
        """Test FTS5 supported tokenizers."""
        ext = get_fts5_extension()
        
        # Basic tokenizers available since 3.9.0
        tokenizers = ext.get_supported_tokenizers((3, 9, 0))
        assert 'unicode61' in tokenizers
        assert 'ascii' in tokenizers
        assert 'porter' in tokenizers
        assert 'trigram' not in tokenizers
        
        # Trigram available since 3.34.0
        tokenizers = ext.get_supported_tokenizers((3, 34, 0))
        assert 'trigram' in tokenizers


class TestJSON1Extension:
    """Test JSON1 extension implementation."""

    def test_json1_extension_creation(self):
        """Test JSON1 extension can be created."""
        ext = JSON1Extension()
        assert ext.name == 'json1'
        assert ext.extension_type == ExtensionType.BUILTIN

    def test_json1_availability(self):
        """Test JSON1 availability check."""
        ext = get_json1_extension()
        
        # JSON1 is built-in since 3.38.0
        assert ext.is_available((3, 38, 0)) is True
        assert ext.is_available((3, 40, 0)) is True
        
        # Not available before 3.38.0
        assert ext.is_available((3, 37, 0)) is False

    def test_json1_feature_check(self):
        """Test JSON1 feature checking."""
        ext = get_json1_extension()
        
        assert ext.check_feature('json_functions', (3, 38, 0)) is True
        assert ext.check_feature('json_array', (3, 38, 0)) is True
        assert ext.check_feature('json_arrow_operators', (3, 38, 0)) is True


class TestRTreeExtension:
    """Test R-Tree extension implementation."""

    def test_rtree_extension_creation(self):
        """Test R-Tree extension can be created."""
        ext = RTreeExtension()
        assert ext.name == 'rtree'
        assert ext.extension_type == ExtensionType.VTABLE

    def test_rtree_availability(self):
        """Test R-Tree availability check."""
        ext = get_rtree_extension()
        
        # R-Tree is available since 3.6.0
        assert ext.is_available((3, 6, 0)) is True
        assert ext.is_available((3, 35, 0)) is True

    def test_rtree_feature_check(self):
        """Test R-Tree feature checking."""
        ext = get_rtree_extension()
        
        assert ext.check_feature('rtree_index', (3, 6, 0)) is True
        assert ext.check_feature('rtree_query', (3, 8, 5)) is True


class TestGeopolyExtension:
    """Test Geopoly extension implementation."""

    def test_geopoly_extension_creation(self):
        """Test Geopoly extension can be created."""
        ext = GeopolyExtension()
        assert ext.name == 'geopoly'
        assert ext.extension_type == ExtensionType.VTABLE

    def test_geopoly_availability(self):
        """Test Geopoly availability check."""
        ext = get_geopoly_extension()
        
        # Geopoly is available since 3.26.0
        assert ext.is_available((3, 26, 0)) is True
        assert ext.is_available((3, 35, 0)) is True
        
        # Not available before 3.26.0
        assert ext.is_available((3, 25, 0)) is False


class TestExtensionRegistry:
    """Test extension registry."""

    def setup_method(self):
        """Reset registry before each test."""
        reset_registry()

    def test_get_registry(self):
        """Test getting the registry."""
        registry = get_registry()
        assert registry is not None
        assert isinstance(registry, SQLiteExtensionRegistry)

    def test_registry_singleton(self):
        """Test registry is a singleton."""
        registry1 = get_registry()
        registry2 = get_registry()
        assert registry1 is registry2

    def test_register_extension(self):
        """Test registering an extension."""
        registry = get_registry()
        ext = FTS5Extension()
        registry.register(ext)
        
        retrieved = registry.get_extension('fts5')
        assert retrieved is not None
        assert retrieved.name == 'fts5'

    def test_detect_extensions(self):
        """Test detecting extensions."""
        registry = get_registry()
        registry.register(get_fts5_extension())
        
        detected = registry.detect_extensions((3, 35, 0))
        assert 'fts5' in detected
        assert detected['fts5'].installed is True

    def test_is_extension_available(self):
        """Test checking extension availability."""
        registry = get_registry()
        
        # Check from known extensions
        assert registry.is_extension_available('fts5', (3, 9, 0)) is True
        assert registry.is_extension_available('json1', (3, 38, 0)) is True

    def test_check_extension_feature(self):
        """Test checking extension feature."""
        registry = get_registry()
        
        assert registry.check_extension_feature('fts5', 'full_text_search', (3, 9, 0)) is True
        assert registry.check_extension_feature('fts5', 'trigram_tokenizer', (3, 34, 0)) is True
