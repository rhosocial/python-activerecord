# tests/rhosocial/activerecord_test/feature/backend/dialect/test_version_predicates.py
"""The version a capability check reads, and the answer it gets before adaptation.

A capability predicate decides whether SQL may use a feature, so it has to
answer ``no`` rather than raise when the version is unknown: the caller is
asking because it cannot assume the feature is there. These tests pin that
contract down at the two layers that shape it -- the dialect, which resolves
the version, and an introspector, which reports it without connecting.
"""

import sqlite3

import pytest

from rhosocial.activerecord.backend.dialect.base import SQLDialectBase
from rhosocial.activerecord.backend.dialect.exceptions import DialectNotAdaptedException
from rhosocial.activerecord.backend.dialect.mixins.dql import DQLMixin
from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect

pytestmark = [pytest.mark.feature, pytest.mark.backend]

SQLITE_LIBRARY_VERSION = tuple(sqlite3.sqlite_version_info[:3])


class BareDialect(DQLMixin, SQLDialectBase):
    """A dialect that cannot name a version and knows nothing without a server."""


class TestVersionWithoutAdaptation:
    """The strict property keeps its contract; the predicates stay answerable."""

    def test_strict_version_still_raises(self):
        with pytest.raises(DialectNotAdaptedException):
            _ = BareDialect().version

    def test_version_or_none_reports_nothing(self):
        assert BareDialect().version_or_none is None

    def test_version_at_least_answers_no(self):
        assert BareDialect().version_at_least((0, 0, 1)) is False

    def test_capability_predicate_answers_instead_of_raising(self):
        # The DQL default mirrors PostgreSQL's 13+ gate; a bare dialect has no
        # version, so the honest answer is "not confirmed" rather than an
        # exception the caller would have to catch to learn the same thing.
        assert BareDialect().supports_fetch_with_ties() is False

    def test_adapted_version_wins(self):
        dialect = BareDialect()
        dialect.version = (15, 2, 0)
        assert dialect.version_or_none == (15, 2, 0)
        assert dialect.version_at_least((13, 0, 0)) is True
        assert dialect.supports_fetch_with_ties() is True


class TestSQLiteNamesItsVersionWithoutAdaptation:
    """SQLite's engine is the driver's library, so the version is already known."""

    def test_declared_version_is_the_library(self):
        assert SQLiteDialect().version_or_none == SQLITE_LIBRARY_VERSION

    def test_strict_version_still_waits_for_adaptation(self):
        # Capability checks may use the library version; the strict property
        # must still refuse, because an unconfigured dialect has not been told
        # which version the caller targets.
        with pytest.raises(DialectNotAdaptedException):
            _ = SQLiteDialect().version

    def test_foreign_key_predicate_answers_before_adaptation(self):
        assert SQLiteDialect().supports_foreign_key_introspection() is True

    def test_declared_version_feeds_every_version_gated_predicate(self):
        dialect = SQLiteDialect()
        assert dialect.supports_basic_cte() is True
        assert dialect.supports_window_functions() is True
        assert dialect.supports_table_list_pragma() is True

    def test_adapted_version_overrides_the_library(self):
        dialect = SQLiteDialect()
        dialect.version = (3, 20, 0)
        assert dialect.version_or_none == (3, 20, 0)
        assert dialect.supports_returning_insert() is False
        assert dialect.supports_window_functions() is False


class TestIntrospectorReportsVersionWithoutIO:
    """`server_version` is the parser-facing answer: no raise, no connection."""

    def test_backend_caches_nothing_before_it_probes(self):
        backend = SQLiteBackend(database=":memory:")
        assert backend.get_cached_server_version() is None

    def test_introspector_reads_the_dialects_declared_version(self):
        backend = SQLiteBackend(database=":memory:")
        assert backend.introspector.server_version == SQLITE_LIBRARY_VERSION

    def test_introspector_falls_back_to_the_backends_cache(self):
        backend = SQLiteBackend(database=":memory:")
        backend._dialect = BareDialect()
        backend._server_version_cache = (8, 4, 1)
        assert backend.introspector.server_version == (8, 4, 1)

    def test_introspector_reports_nothing_rather_than_raising(self):
        backend = SQLiteBackend(database=":memory:")
        backend._dialect = BareDialect()
        assert backend.introspector.server_version is None
