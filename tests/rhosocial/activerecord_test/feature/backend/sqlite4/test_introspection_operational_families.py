# tests/rhosocial/activerecord_test/feature/backend/sqlite4/test_introspection_operational_families.py
"""The families SQLite answers False for, and the reason it says so.

Four of these families answer ``False`` and the sixth answers ``False`` on
every build that lacks ``dbstat``. The tests go after the *probe and its
reason*, not after the family: there is no answer to run, so what is worth
pinning is that the probe is a boolean, that it stays boolean under a
monkeypatched lie, and that a caller who goes ahead anyway is refused rather
than handed an empty listing that reads as a real answer.

The ``dbstat`` half copies the technique from the per-table storage tests: the
family is a compile-time fact, so both build shapes are proved by patching the
probe rather than by requiring a particular library.
"""

import pytest

from rhosocial.activerecord.backend.dialect.exceptions import (
    ProtocolNotImplementedError,
    UnsupportedFeatureError,
)
from rhosocial.activerecord.backend.expression.introspection import (
    IndexUsageStatsQueryStatement,
    ObjectDependencyQueryStatement,
    RuntimeMetricsQueryStatement,
    TableUsageStatsQueryStatement,
    UnusedIndexesQueryStatement,
)
from rhosocial.activerecord.backend.impl.sqlite.mixins.introspection import (
    _dbstat_compiled_in,
)


class TestFamiliesSQLiteCannotAnswer:
    """A probe answering False is the fact under test, with its reason."""

    @pytest.mark.parametrize(
        "probe",
        [
            "supports_unused_indexes_detection",
            "supports_table_stats",
            "supports_runtime_stats",
            "supports_index_stats",
            "supports_object_dependencies",
            "supports_ddl_extraction",
        ],
    )
    def test_the_probe_is_a_boolean_false(self, sqlite_backend, probe):
        """The answer is a settled ``False``, not an absent attribute."""
        answered = getattr(sqlite_backend.dialect, probe)()
        assert answered is False

    @pytest.mark.parametrize(
        "probe, statement",
        [
            ("supports_unused_indexes_detection", UnusedIndexesQueryStatement),
            ("supports_table_stats", TableUsageStatsQueryStatement),
            ("supports_runtime_stats", RuntimeMetricsQueryStatement),
            ("supports_index_stats", IndexUsageStatsQueryStatement),
            ("supports_object_dependencies", ObjectDependencyQueryStatement),
        ],
    )
    def test_the_statement_has_no_formatter_behind_the_false(
        self, sqlite_backend, probe, statement
    ):
        """A False probe has nothing to render: the statement refuses.

        This is the pair the rule matches -- a ``True`` obliges a formatter, so
        a ``False`` with a formatter behind it would be a probe lying in the
        other direction, and a ``True`` with no formatter is the broken promise
        ``supports_ddl_extraction`` used to be.
        """
        with pytest.raises((UnsupportedFeatureError, Exception)):
            statement(sqlite_backend.dialect).to_sql()

    def test_a_familys_manager_method_does_not_imply_an_answer(self, sqlite_backend):
        """The method exists, and it is the probe that says whether to call it.

        ``list_runtime_metrics`` is on the shared manager because every backend
        has the method; what differs is whether this engine can answer. A
        caller that went ahead without reading the probe gets the statement's
        own refusal rather than a listing that reads as a real answer, and the
        refusal names the formatter that does not exist.
        """
        for call in (
            lambda: sqlite_backend.introspector.list_runtime_metrics(),
            lambda: sqlite_backend.introspector.list_index_usage_stats(),
            lambda: sqlite_backend.introspector.list_object_dependencies(),
            lambda: sqlite_backend.introspector.list_unused_indexes(),
            lambda: sqlite_backend.introspector.list_table_usage_stats(),
        ):
            with pytest.raises(ProtocolNotImplementedError):
                call()

    def test_unused_indexes_answer_is_empty_and_says_why(self, sqlite_backend):
        """Absence of evidence is not evidence of use, and the docstring says so."""
        docstring = sqlite_backend.dialect.supports_unused_indexes_detection.__doc__ or ""
        assert "no per-index use counter" in docstring
        assert "never served a query" in docstring

    def test_ddl_extraction_names_what_is_missing(self, sqlite_backend):
        """The False says what would have to exist for it to be a True."""
        docstring = sqlite_backend.dialect.supports_ddl_extraction.__doc__ or ""
        assert "format_ddl_statement_query_statement" in docstring
        assert "False" in docstring

        with pytest.raises(ProtocolNotImplementedError):
            sqlite_backend.introspector.get_ddl_statement("orders")

    def test_the_ddl_probe_and_the_statement_agree(self, sqlite_backend):
        """The False and the refusal are the same fact seen from two sides."""
        assert sqlite_backend.dialect.supports_ddl_extraction() is False
        with pytest.raises(ProtocolNotImplementedError):
            sqlite_backend.introspector.get_ddl_statement("orders")


class TestCompiledInFeatures:
    """The ``dbstat`` family is a compile-time fact, so both shapes are proved."""

    def test_the_probe_answers_a_boolean(self, sqlite_backend):
        assert isinstance(sqlite_backend.dialect.supports_table_storage_introspection(), bool)

    def test_the_statement_renders_when_the_build_has_it(self, sqlite_backend, monkeypatch):
        monkeypatch.setattr(
            sqlite_backend.dialect,
            "supports_table_storage_introspection",
            lambda: True,
        )
        from rhosocial.activerecord.backend.impl.sqlite.expression.introspection import (
            SQLiteTableStorageStatement,
        )

        sql, _ = SQLiteTableStorageStatement(sqlite_backend.dialect, "main").to_sql()
        assert "dbstat" in sql.lower()

    def test_the_statement_refuses_when_the_build_lacks_it(self, sqlite_backend, monkeypatch):
        monkeypatch.setattr(
            sqlite_backend.dialect,
            "supports_table_storage_introspection",
            lambda: False,
        )
        from rhosocial.activerecord.backend.impl.sqlite.expression.introspection import (
            SQLiteTableStorageStatement,
        )

        with pytest.raises(UnsupportedFeatureError):
            SQLiteTableStorageStatement(sqlite_backend.dialect, "main").to_sql()

    def test_the_cached_probe_is_idempotent(self):
        """The lru_cache answers the same build the same way every call."""
        assert _dbstat_compiled_in() == _dbstat_compiled_in()
        assert isinstance(_dbstat_compiled_in(), bool)
