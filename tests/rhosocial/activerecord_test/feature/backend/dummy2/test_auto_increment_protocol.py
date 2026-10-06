# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_auto_increment_protocol.py
"""Protocols for the two auto-increment mechanisms, and their mixin defaults.

The former single ``AutoIncrementSupport`` protocol answered three questions at
once (``AUTO_INCREMENT``, SQL-standard identity, ``AUTOINCREMENT``) and its
probe was called by no formatter. It is split into one protocol per mechanism:
``AutoIncrementColumnSupport`` for the parameterless marker and
``IdentityColumnSupport`` for the parameterised SQL-standard clause. Both
mixins fail closed (probe defaults ``False``); DummyDialect, the reference
switchboard, declares them ``True`` explicitly.
"""

from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
from rhosocial.activerecord.backend.dialect.protocols import (
    AutoIncrementColumnSupport,
    IdentityColumnSupport,
)
from rhosocial.activerecord.backend.dialect.mixins import (
    AutoIncrementMixin,
    IdentityColumnMixin,
)


class TestAutoIncrementColumnProtocol:
    """The parameterless ``AUTO_INCREMENT`` marker protocol and its mixin."""

    def test_dummy_dialect_implements_protocol(self, dummy_dialect: DummyDialect):
        """Test that DummyDialect implements AutoIncrementColumnSupport."""
        assert isinstance(dummy_dialect, AutoIncrementColumnSupport)

    def test_sqlite_dialect_implements_protocol(self):
        """Test that SQLiteDialect implements AutoIncrementColumnSupport.

        Structurally: the mixin supplies both methods. Its probe answers
        ``False`` (SQLite's ``AUTOINCREMENT`` is a constraint keyword, not this
        standalone clause), which is a declaration, not a missing method.
        """
        assert isinstance(SQLiteDialect(), AutoIncrementColumnSupport)

    def test_generic_mixin_default_is_false(self):
        """The generic default fails closed.

        A probe answering True by default would let the formatter emit
        ``AUTO_INCREMENT`` on a server that rejects it.
        """

        class GenericDialect(AutoIncrementMixin):
            pass

        assert GenericDialect().supports_auto_increment_column() is False

    def test_dummy_declares_the_marker(self, dummy_dialect: DummyDialect):
        """DummyDialect is the switchboard: it declares the marker True."""
        assert dummy_dialect.supports_auto_increment_column() is True

    def test_sqlite_inherits_the_false_default(self):
        """SQLite must not re-declare the probe: the mixin default is right.

        SQLite's ``AUTOINCREMENT`` only exists inside an ``INTEGER PRIMARY
        KEY`` constraint, so a standalone marker clause is refused rather than
        rendered as ``AUTO_INCREMENT``.
        """
        assert "supports_auto_increment_column" not in SQLiteDialect.__dict__
        assert SQLiteDialect().supports_auto_increment_column() is False


class TestIdentityColumnProtocol:
    """The parameterised SQL-standard identity protocol and its mixin."""

    def test_dummy_dialect_implements_protocol(self, dummy_dialect: DummyDialect):
        """Test that DummyDialect implements IdentityColumnSupport."""
        assert isinstance(dummy_dialect, IdentityColumnSupport)

    def test_sqlite_dialect_implements_protocol(self):
        """SQLiteDialect carries the methods and declines the capability."""
        assert isinstance(SQLiteDialect(), IdentityColumnSupport)

    def test_mixin_defaults_all_probes_to_false(self):
        """Every identity probe fails closed until a dialect declares it."""

        class GenericDialect(IdentityColumnMixin):
            pass

        dialect = GenericDialect()
        assert dialect.supports_identity_column() is False
        assert dialect.supports_identity_generation_always() is False
        assert dialect.supports_identity_start() is False
        assert dialect.supports_identity_increment() is False
        assert dialect.supports_identity_minvalue() is False
        assert dialect.supports_identity_maxvalue() is False
        assert dialect.supports_identity_cycle() is False

    def test_dummy_declares_every_probe(self, dummy_dialect: DummyDialect):
        """DummyDialect turns the whole switchboard on, option by option."""
        assert dummy_dialect.supports_identity_column() is True
        assert dummy_dialect.supports_identity_generation_always() is True
        assert dummy_dialect.supports_identity_start() is True
        assert dummy_dialect.supports_identity_increment() is True
        assert dummy_dialect.supports_identity_minvalue() is True
        assert dummy_dialect.supports_identity_maxvalue() is True
        assert dummy_dialect.supports_identity_cycle() is True

    def test_sqlite_inherits_the_false_defaults(self):
        """SQLite has no identity grammar, so every probe stays False."""
        for probe in (
            "supports_identity_column",
            "supports_identity_generation_always",
            "supports_identity_start",
            "supports_identity_increment",
            "supports_identity_minvalue",
            "supports_identity_maxvalue",
            "supports_identity_cycle",
        ):
            assert probe not in SQLiteDialect.__dict__, (
                f"SQLiteDialect re-declares {probe}; the mixin default is right"
            )
            assert getattr(SQLiteDialect(), probe)() is False
