# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_auto_increment_protocol.py
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
from rhosocial.activerecord.backend.dialect.protocols import AutoIncrementSupport
from rhosocial.activerecord.backend.dialect.mixins import AutoIncrementMixin


class TestAutoIncrementProtocol:
    """Tests for AutoIncrementSupport protocol and its generic mixin."""

    def test_dummy_dialect_implements_protocol(self, dummy_dialect: DummyDialect):
        """Test that DummyDialect implements AutoIncrementSupport protocol."""
        assert isinstance(dummy_dialect, AutoIncrementSupport)

    def test_sqlite_dialect_implements_protocol(self):
        """Test that SQLiteDialect implements AutoIncrementSupport protocol."""
        assert isinstance(SQLiteDialect(), AutoIncrementSupport)

    def test_generic_mixin_default_is_true(self):
        """The generic implementation covers the common case: supported.

        Backends inherit ``True`` unchanged; only backends whose real
        capability differs (e.g. no server-side key generation) override.
        """

        class GenericDialect(AutoIncrementMixin):
            pass

        assert GenericDialect().supports_auto_increment() is True

    def test_concrete_dialects_inherit_without_override(self):
        """Override discipline: dialects matching the generic behaviour must
        NOT re-declare the method — overrides are reserved for deviations."""
        for dialect_cls in (DummyDialect, SQLiteDialect):
            assert "supports_auto_increment" not in dialect_cls.__dict__, (
                f"{dialect_cls.__name__} re-declares supports_auto_increment; "
                "identical behaviour must be inherited from AutoIncrementMixin"
            )
            assert dialect_cls().supports_auto_increment() is True