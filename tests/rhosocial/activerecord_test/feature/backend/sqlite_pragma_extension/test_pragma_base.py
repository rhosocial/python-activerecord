# tests/rhosocial/activerecord_test/feature/backend/sqlite_pragma_extension/test_pragma_base.py
"""
Tests for SQLite PRAGMA base framework.
"""
import pytest

from rhosocial.activerecord.backend.impl.sqlite.pragma import (
    PragmaCategory,
    PragmaInfo,
    get_pragma_info,
    get_all_pragma_infos,
    get_pragma_names,
    get_pragmas_by_category,
)


class TestPragmaCategory:
    """Test PragmaCategory enum."""

    def test_pragma_categories_exist(self):
        """Test that all pragma categories are defined."""
        assert hasattr(PragmaCategory, 'CONFIGURATION')
        assert hasattr(PragmaCategory, 'INFORMATION')
        assert hasattr(PragmaCategory, 'DEBUG')
        assert hasattr(PragmaCategory, 'PERFORMANCE')
        assert hasattr(PragmaCategory, 'WAL')
        assert hasattr(PragmaCategory, 'COMPILE_TIME')

    def test_pragma_category_values(self):
        """Test pragma category values."""
        assert PragmaCategory.CONFIGURATION.value == "configuration"
        assert PragmaCategory.INFORMATION.value == "information"
        assert PragmaCategory.DEBUG.value == "debug"
        assert PragmaCategory.PERFORMANCE.value == "performance"
        assert PragmaCategory.WAL.value == "wal"
        assert PragmaCategory.COMPILE_TIME.value == "compile_time"


class TestPragmaInfo:
    """Test PragmaInfo dataclass."""

    def test_pragma_info_creation(self):
        """Test creating a PragmaInfo instance."""
        info = PragmaInfo(
            name='test_pragma',
            category=PragmaCategory.CONFIGURATION,
            description='Test pragma',
            read_only=False,
            min_version=(3, 0, 0),
            value_type=str,
        )
        
        assert info.name == 'test_pragma'
        assert info.category == PragmaCategory.CONFIGURATION
        assert info.description == 'Test pragma'
        assert info.read_only is False
        assert info.min_version == (3, 0, 0)
        assert info.value_type == str

    def test_pragma_info_get_sql(self):
        """Test PragmaInfo get_sql method."""
        info = PragmaInfo(
            name='foreign_keys',
            category=PragmaCategory.CONFIGURATION,
            description='Test pragma',
        )
        
        sql = info.get_sql()
        assert sql == "PRAGMA foreign_keys"

    def test_pragma_info_get_set_sql(self):
        """Test PragmaInfo get_set_sql method."""
        info = PragmaInfo(
            name='foreign_keys',
            category=PragmaCategory.CONFIGURATION,
            description='Test pragma',
            read_only=False,
        )
        
        sql = info.get_set_sql(value=1)
        assert sql == "PRAGMA foreign_keys = 1"

    def test_pragma_info_get_set_sql_with_argument(self):
        """Test PragmaInfo get_set_sql with argument."""
        info = PragmaInfo(
            name='table_info',
            category=PragmaCategory.INFORMATION,
            description='Test pragma',
            requires_argument=True,
        )
        
        sql = info.get_set_sql(argument='users')
        assert "table_info(users)" in sql


class TestPragmaQueries:
    """Test pragma query functions."""

    def test_get_pragma_info_existing(self):
        """Test getting existing pragma info."""
        info = get_pragma_info('foreign_keys')
        assert info is not None
        assert info.name == 'foreign_keys'
        assert info.category == PragmaCategory.CONFIGURATION

    def test_get_pragma_info_non_existing(self):
        """Test getting non-existing pragma info."""
        info = get_pragma_info('non_existing_pragma')
        assert info is None

    def test_get_all_pragma_infos(self):
        """Test getting all pragma infos."""
        all_pragmas = get_all_pragma_infos()
        assert isinstance(all_pragmas, dict)
        assert len(all_pragmas) > 0
        assert 'foreign_keys' in all_pragmas

    def test_get_pragma_names(self):
        """Test getting pragma names."""
        names = get_pragma_names()
        assert isinstance(names, list)
        assert len(names) > 0
        assert 'foreign_keys' in names

    def test_get_pragmas_by_category(self):
        """Test getting pragmas by category."""
        config_pragmas = get_pragmas_by_category(PragmaCategory.CONFIGURATION)
        assert isinstance(config_pragmas, list)
        assert len(config_pragmas) > 0
        
        # Check all are configuration pragmas
        for pragma in config_pragmas:
            assert pragma.category == PragmaCategory.CONFIGURATION


class TestConfigurationPragmas:
    """Test configuration pragma definitions."""

    def test_foreign_keys_pragma(self):
        """Test foreign_keys pragma definition."""
        info = get_pragma_info('foreign_keys')
        assert info is not None
        assert info.category == PragmaCategory.CONFIGURATION
        assert info.read_only is False
        assert info.value_type == bool
        assert info.default_value is False

    def test_journal_mode_pragma(self):
        """Test journal_mode pragma definition."""
        info = get_pragma_info('journal_mode')
        assert info is not None
        assert info.category == PragmaCategory.CONFIGURATION
        assert 'WAL' in info.allowed_values

    def test_synchronous_pragma(self):
        """Test synchronous pragma definition."""
        info = get_pragma_info('synchronous')
        assert info is not None
        assert info.category == PragmaCategory.CONFIGURATION
        assert 'FULL' in info.allowed_values


class TestInformationPragmas:
    """Test information pragma definitions."""

    def test_table_info_pragma(self):
        """Test table_info pragma definition."""
        info = get_pragma_info('table_info')
        assert info is not None
        assert info.category == PragmaCategory.INFORMATION
        assert info.read_only is True
        assert info.requires_argument is True

    def test_index_list_pragma(self):
        """Test index_list pragma definition."""
        info = get_pragma_info('index_list')
        assert info is not None
        assert info.category == PragmaCategory.INFORMATION
        assert info.requires_argument is True

    def test_database_list_pragma(self):
        """Test database_list pragma definition."""
        info = get_pragma_info('database_list')
        assert info is not None
        assert info.category == PragmaCategory.INFORMATION
        assert info.requires_argument is False


class TestDebugPragmas:
    """Test debug pragma definitions."""

    def test_integrity_check_pragma(self):
        """Test integrity_check pragma definition."""
        info = get_pragma_info('integrity_check')
        assert info is not None
        assert info.category == PragmaCategory.DEBUG
        assert info.read_only is True

    def test_quick_check_pragma(self):
        """Test quick_check pragma definition."""
        info = get_pragma_info('quick_check')
        assert info is not None
        assert info.category == PragmaCategory.DEBUG


class TestPerformancePragmas:
    """Test performance pragma definitions."""

    def test_cache_size_pragma(self):
        """Test cache_size pragma definition."""
        info = get_pragma_info('cache_size')
        assert info is not None
        assert info.category == PragmaCategory.PERFORMANCE

    def test_mmap_size_pragma(self):
        """Test mmap_size pragma definition."""
        info = get_pragma_info('mmap_size')
        assert info is not None
        assert info.category == PragmaCategory.PERFORMANCE


class TestWALPragmas:
    """Test WAL pragma definitions."""

    def test_wal_checkpoint_pragma(self):
        """Test wal_checkpoint pragma definition."""
        info = get_pragma_info('wal_checkpoint')
        assert info is not None
        assert info.category == PragmaCategory.WAL

    def test_wal_autocheckpoint_pragma(self):
        """Test wal_autocheckpoint pragma definition."""
        info = get_pragma_info('wal_autocheckpoint')
        assert info is not None
        assert info.category == PragmaCategory.WAL


class TestCompileTimePragmas:
    """Test compile-time pragma definitions."""

    def test_compile_options_pragma(self):
        """Test compile_options pragma definition."""
        info = get_pragma_info('compile_options')
        assert info is not None
        assert info.category == PragmaCategory.COMPILE_TIME
        assert info.read_only is True

    def test_user_version_pragma(self):
        """Test user_version pragma definition."""
        info = get_pragma_info('user_version')
        assert info is not None
        assert info.category == PragmaCategory.COMPILE_TIME
        assert info.read_only is False  # user_version can be set
