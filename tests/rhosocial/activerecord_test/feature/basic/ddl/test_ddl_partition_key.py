# tests/rhosocial/activerecord_test/feature/basic/ddl/test_ddl_partition_key.py
"""Partition key declaration on the field-level annotation surface.

``UsePartitionKey`` marks a field as a partition-key member; the extraction
lands on ``__partition_key__`` in field-declaration order, UseColumn-aware.
Exactly one of the two faces (annotations, direct dunder) may declare the
key; the query layer warns when a lookup skips every partition column, and
the CLI says the same out loud at filter time.
"""
from rhosocial.activerecord.backend.expression import (
    Column,
    ComparisonPredicate,
    Literal,
)
from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.base import UseColumn, UsePartitionKey
from rhosocial.activerecord.query.active_query import _warn_partial_key_scope
from rhosocial.activerecord.cli.runtime import apply_filters

import logging
import warnings
from types import SimpleNamespace

try:
    from typing import Annotated
except ImportError:
    from typing_extensions import Annotated

import pytest


class PartitionedLog(ActiveRecord):
    """Annotated partition key; the primary key contains every member."""

    @classmethod
    def table_name(cls):
        return "partitioned_logs"

    @classmethod
    def primary_key(cls):
        return ("id", "bucket")

    id: int
    bucket: Annotated[str, UsePartitionKey()]
    created_at: Annotated[str, UseColumn("created_day"), UsePartitionKey()]


class DirectPartitioned(ActiveRecord):
    """Direct-write partition key, as an introspection-generated model emits."""

    @classmethod
    def table_name(cls):
        return "direct_partitioned"

    @classmethod
    def primary_key(cls):
        return ("id", "day")

    __partition_key__ = ("day",)

    id: int
    day: str


class Unpartitioned(ActiveRecord):
    @classmethod
    def table_name(cls):
        return "unpartitioned"

    id: int
    name: str


class TestDeclarationSurface:
    """The four cases of §4: annotations, dunder, both, neither."""

    def test_annotated_only_extracts_in_field_order(self):
        # Declaration order, UseColumn-aware: the renamed field contributes
        # its column name, not the Python field name.
        assert PartitionedLog.__partition_key__ == ("bucket", "created_day")

    def test_annotated_only_accessor_mirrors_pk_accessor(self):
        assert PartitionedLog.partition_key_columns() == ("bucket", "created_day")

    def test_direct_declaration_adopted_as_written(self):
        assert DirectPartitioned.partition_key_columns() == ("day",)

    def test_both_declared_is_rejected(self):
        with pytest.raises(TypeError, match="twice"):
            class Both(ActiveRecord):
                @classmethod
                def table_name(cls):
                    return "both_declared"

                __partition_key__ = ("bucket",)

                id: int
                bucket: Annotated[str, UsePartitionKey()]

    def test_neither_declared_is_not_partitioned(self):
        assert Unpartitioned.partition_key_columns() == ()
        # The extraction writes nothing: the dunder stays the interface default.
        assert Unpartitioned.__dict__.get("__partition_key__") is None


class TestPartitionKeyValidation:
    """Direct declarations are validated; containment gaps are announced."""

    def test_bare_string_is_rejected_tuple_required(self):
        with pytest.raises(TypeError, match="must be a tuple"):
            class BareString(ActiveRecord):
                @classmethod
                def table_name(cls):
                    return "bare_string"

                __partition_key__ = "day"

                id: int
                day: str

    def test_expression_key_entries_are_rejected(self):
        # The first round accepts plain column tuples only: a non-string
        # entry (an expression key would arrive this way) is refused.
        with pytest.raises(TypeError, match="non-empty column-name strings"):
            class ExpressionKey(ActiveRecord):
                @classmethod
                def table_name(cls):
                    return "expression_key"

                __partition_key__ = ("day", lambda dialect: dialect)

                id: int
                day: str

    def test_unknown_column_is_rejected(self):
        with pytest.raises(TypeError, match="does not define"):
            class UnknownColumn(ActiveRecord):
                @classmethod
                def table_name(cls):
                    return "unknown_partition_column"

                __partition_key__ = ("nope",)

                id: int
                day: str

    def test_partition_key_outside_pk_warns(self):
        with pytest.warns(UserWarning, match="partition key"):
            class LoosePartition(ActiveRecord):
                @classmethod
                def table_name(cls):
                    return "loose_partition"

                @classmethod
                def primary_key(cls):
                    return "id"

                id: int
                region: Annotated[str, UsePartitionKey()]

    def test_direct_declaration_outside_pk_also_warns(self):
        with pytest.warns(UserWarning, match="partition key"):
            class LooseDirect(ActiveRecord):
                @classmethod
                def table_name(cls):
                    return "loose_direct"

                @classmethod
                def primary_key(cls):
                    return "id"

                __partition_key__ = ("day",)

                id: int
                day: str

    def test_partition_key_inside_pk_is_silent(self):
        with warnings.catch_warnings(record=True):
            warnings.simplefilter("error", UserWarning)
            class CoveredPartition(ActiveRecord):
                @classmethod
                def table_name(cls):
                    return "covered_partition"

                @classmethod
                def primary_key(cls):
                    return ("id", "region")

                id: int
                region: Annotated[str, UsePartitionKey()]

        assert CoveredPartition.partition_key_columns() == ("region",)


class _QueryStub:
    """Minimal query surface ``_warn_partial_key_scope`` reads."""

    def __init__(self, model, where_clause=None):
        self.model_class = model
        self.where_clause = where_clause
        self.records = []

    def _log(self, level, msg, *args, **kwargs):
        self.records.append((level, msg))


_DIALECT = SQLiteDialect()


def _where(*pairs):
    """Predicates over column names, as a WHERE tree fragment."""
    return tuple(
        ComparisonPredicate(_DIALECT, "=", Column(_DIALECT, column), Literal(_DIALECT, value))
        for column, value in pairs
    )


class TestQueryPartitionScopeWarning:
    """The query layer warns when a lookup skips every partition column."""

    def test_partitioned_model_without_partition_column_warns(self):
        query = _QueryStub(PartitionedLog)
        _warn_partial_key_scope(query)
        assert any(
            level == logging.WARNING and "partition key" in msg
            for level, msg in query.records
        )

    def test_partition_column_constrained_is_silent(self):
        # ``bucket`` is a primary-key member too, so constraining it alone
        # still leaves ``id`` -- both warnings must be accounted for.
        query = _QueryStub(
            PartitionedLog,
            _where(("bucket", "x"), ("id", 1)),
        )
        _warn_partial_key_scope(query)
        assert query.records == []

    def test_pk_partial_warning_survives_next_to_partition_check(self):
        # Partition column constrained, primary key only half so: the PK
        # warning still fires (and the partition one stays silent). The key
        # is application-assigned here -- the PK check reads the caller's
        # key columns, which an auto-generated key would not report.
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", UserWarning)
            class NaturalKeyPartitioned(ActiveRecord):
                @classmethod
                def table_name(cls):
                    return "natural_key_partitioned"

                @classmethod
                def primary_key(cls):
                    return ("code", "bucket")

                @classmethod
                def pk_auto_generated(cls):
                    return False

                code: str
                bucket: Annotated[str, UsePartitionKey()]

        query = _QueryStub(NaturalKeyPartitioned, _where(("bucket", "x")))
        _warn_partial_key_scope(query)
        messages = [msg for _, msg in query.records]
        assert any("leaves key column(s) code" in msg for msg in messages)
        assert not any("partition key" in msg for msg in messages)

    def test_keyless_partitioned_model_still_warns(self):
        # The independence case: no primary key means the PK check
        # early-returns, and the partition check must not be swallowed.
        with pytest.warns(UserWarning, match="partition key"):
            class KeylessPartitioned(ActiveRecord):
                @classmethod
                def table_name(cls):
                    return "keyless_partitioned"

                @classmethod
                def primary_key(cls):
                    return None

                __partition_key__ = ("day",)

                id: int
                day: str

        query = _QueryStub(KeylessPartitioned)
        _warn_partial_key_scope(query)
        assert any(
            level == logging.WARNING and "partition key" in msg
            for level, msg in query.records
        )

    def test_non_partitioned_model_is_silent(self):
        query = _QueryStub(Unpartitioned)
        _warn_partial_key_scope(query)
        assert query.records == []


class _FilterQueryStub:
    """Records ``where`` calls; the other filter options stay untouched."""

    def __init__(self):
        self.predicates = []

    def where(self, predicate):
        self.predicates.append(predicate)
        return self


def _args(where=None, quiet=False):
    return SimpleNamespace(where=where, order_by=None, select=None, quiet=quiet)


class TestCliPartitionHint:
    """The CLI says the partition-scope difference out loud at filter time."""

    @pytest.fixture
    def cli_model(self, tmp_path):
        class CliPartitionedLog(ActiveRecord):
            @classmethod
            def table_name(cls):
                return "cli_partitioned_logs"

            @classmethod
            def primary_key(cls):
                return ("id", "bucket")

            id: int
            bucket: Annotated[str, UsePartitionKey()]

        CliPartitionedLog.configure(
            SQLiteConnectionConfig(database=str(tmp_path / "cli_pk.db")), SQLiteBackend
        )
        return CliPartitionedLog

    def test_hint_printed_when_where_skips_partition(self, cli_model, capsys):
        apply_filters(_FilterQueryStub(), cli_model, _args(["id=1"]))
        stderr = capsys.readouterr().err
        assert "partitioned by" in stderr
        assert "bucket" in stderr

    def test_no_hint_when_partition_column_constrained(self, cli_model, capsys):
        apply_filters(_FilterQueryStub(), cli_model, _args(["bucket=jobs"]))
        assert capsys.readouterr().err == ""

    def test_no_hint_without_where(self, cli_model, capsys):
        apply_filters(_FilterQueryStub(), cli_model, _args())
        assert capsys.readouterr().err == ""

    def test_quiet_suppresses_the_hint(self, cli_model, capsys):
        apply_filters(_FilterQueryStub(), cli_model, _args(["id=1"], quiet=True))
        assert capsys.readouterr().err == ""

    def test_no_hint_for_unpartitioned_model(self, tmp_path, capsys):
        class CliPlain(ActiveRecord):
            @classmethod
            def table_name(cls):
                return "cli_plain"

            id: int
            name: str

        CliPlain.configure(
            SQLiteConnectionConfig(database=str(tmp_path / "cli_plain.db")), SQLiteBackend
        )
        apply_filters(_FilterQueryStub(), CliPlain, _args(["id=1"]))
        assert capsys.readouterr().err == ""
