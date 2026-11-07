# tests/rhosocial/activerecord_test/feature/rules/test_catalogues_that_earn_their_name.py
"""The class-level catalogues that earn their capital name because a test walks them.

``.claude/rules/constants.md`` decides a read-once constant by asking what the
reading is: inline it, and take a capital name out of it. It grants exactly two
exemptions, and the second is the one this file exists for. A catalogue whose
every entry the tests assert is a set of facts somebody guarantees -- the same
shape as ``_TYPE_CAPABILITIES``, which the CLIs read to resolve the switch
behind a type and which the suite walks entry by entry, and as PostgreSQL's
``_RELKIND_LABELS``, read in the one CASE that names a relation's kind and
pinned because "the five pairs it holds are what the parsing matrix asserts".

The first check in ``test_constant_discipline.py`` was extended to collect
class-level assignments as well, because a module-level walk alone saw 135 of
the 541 all-caps assignments under ``src/`` and every name a class declares for
itself was invisible -- which is where the capitals accumulate. Once a reader
written as an attribute (``self.TABLE``, ``expr.TABLE``) is counted as well, it
reports nine catalogues with exactly one reader and no assertion naming them.
Each of the nine is pinned here rather than inlined, and the reason is the same
for all of them: the table is the one place the engine's own vocabulary is
written down, the reading that uses it is a single branch, and a spelling that
drifted inside it would be a value nothing validates.

The nine, and what each one is the answer to:

``SQLDialectBase.ISOLATION_LEVEL_NAMES``
    the SQL words for the four standard isolation levels;
``GraphTableMixin._ALTER_ACTIONS`` and ``._ALTER_TARGETS``
    the two vocabularies ``ALTER PROPERTY GRAPH`` accepts;
``TemporalArithmeticMixin._OPERATOR_WORDS``
    the Python symbols the temporal dunders hand down, as operation words;
``ArithmeticOperation.OPERATOR_SYMBOLS``
    the character each operation word writes, which the artifact never sees;
``SQLiteIntrospector._TRIGGER_TIMING`` and ``._TRIGGER_EVENTS``
    the words a trigger's header can be read with;
``SQLiteDateTimeMixin._DATETIME_EXTRACT_FORMATS``
    the strftime code each extractable field renders as.

Each test walks its table rather than spot-checking one entry, because the
defect the rule is about is a spelling nobody asserted -- and a test that
asserts one entry of nine leaves the other eight free to drift.
"""

import logging

import pytest

from rhosocial.activerecord.backend.dialect.base import SQLDialectBase
from rhosocial.activerecord.backend.dialect.mixins.graph import GraphTableMixin
from rhosocial.activerecord.backend.expression.core import Column, Literal
from rhosocial.activerecord.backend.expression.datetime import (
    DateTimeField,
    ExtractExpression,
)
from rhosocial.activerecord.backend.expression.mixins import TemporalArithmeticMixin
from rhosocial.activerecord.backend.expression.operators import (
    ArithmeticOperation,
    ArithmeticOperator,
)
from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.introspection.introspector import (
    SQLiteIntrospector,
)
from rhosocial.activerecord.backend.impl.sqlite.mixins.datetime import (
    SQLiteDateTimeMixin,
)
from rhosocial.activerecord.logging.formatter import ActiveRecordFormatter

pytestmark = [pytest.mark.feature]


@pytest.fixture
def dialect():
    """A SQLite dialect, which is how these catalogues are read for real."""
    backend = SQLiteBackend(database=":memory:")
    backend.connect()
    backend.introspect_and_adapt()
    try:
        yield backend.dialect
    finally:
        backend.disconnect()


class TestIsolationLevelNames:
    """The SQL words for the four standard isolation levels."""

    def test_every_level_names_the_sql_word_it_renders(self):
        assert set(SQLDialectBase.ISOLATION_LEVEL_NAMES) == {
            "READ_UNCOMMITTED",
            "READ_COMMITTED",
            "REPEATABLE_READ",
            "SERIALIZABLE",
        }

    def test_the_word_is_the_spaced_name_of_the_level(self, dialect):
        for level, word in SQLDialectBase.ISOLATION_LEVEL_NAMES.items():
            assert dialect.get_isolation_level_name(level) == word

    def test_a_level_the_table_does_not_hold_still_reads(self, dialect):
        """The fallback is the spaced name, not a raise and not a silence."""
        assert dialect.get_isolation_level_name("READ_UNCOMMITTED_X") == (
            "READ UNCOMMITTED X"
        )


class TestAlterGraphVocabularies:
    """The two vocabularies ``ALTER PROPERTY GRAPH`` accepts."""

    def test_the_actions_are_the_two_the_statement_declares(self):
        assert set(GraphTableMixin._ALTER_ACTIONS) == {"add", "drop"}

    def test_the_targets_are_the_three_the_statement_declares(self):
        assert set(GraphTableMixin._ALTER_TARGETS) == {
            "edge tables",
            "tables",
            "vertex tables",
        }

    def test_every_key_normalises_to_the_word_after_the_arrow(self):
        normalize = GraphTableMixin._normalize_alter_keyword
        for action, word in GraphTableMixin._ALTER_ACTIONS.items():
            assert normalize(action, GraphTableMixin._ALTER_ACTIONS, "action") == word
            assert normalize(action.upper(), GraphTableMixin._ALTER_ACTIONS, "action") == word
        for target, word in GraphTableMixin._ALTER_TARGETS.items():
            assert normalize(target, GraphTableMixin._ALTER_TARGETS, "target") == word

    def test_a_word_the_vocabulary_does_not_hold_is_refused(self):
        normalize = GraphTableMixin._normalize_alter_keyword
        with pytest.raises(ValueError):
            normalize("rename", GraphTableMixin._ALTER_ACTIONS, "action")
        with pytest.raises(ValueError):
            normalize("databases", GraphTableMixin._ALTER_TARGETS, "target")


class TestOperatorWords:
    """The Python symbols the temporal dunders hand down, as operation words."""

    def test_the_symbols_are_the_three_arithmetic_dunders_declare(self):
        assert set(TemporalArithmeticMixin._OPERATOR_WORDS) == {"+", "-", "*"}

    def test_every_word_is_an_operation_and_the_symbol_is_its_own(self):
        for symbol, word in TemporalArithmeticMixin._OPERATOR_WORDS.items():
            member = ArithmeticOperator(word)
            assert member.symbol == symbol, (
                f"{symbol!r} would build {word!r}, which writes {member.symbol!r}"
            )


class TestOperatorSymbols:
    """The character each operation word writes, and the artifact never sees it."""

    def test_every_member_has_a_symbol_keyed_by_itself(self):
        assert set(ArithmeticOperation.OPERATOR_SYMBOLS) == set(ArithmeticOperator)

    def test_the_symbol_is_the_member_s_own(self):
        for op, symbol in ArithmeticOperation.OPERATOR_SYMBOLS.items():
            assert symbol is op.symbol

    def test_the_formatter_writes_the_symbol_and_nothing_else(self, dialect):
        sql, params = ArithmeticOperation(
            dialect, ArithmeticOperator.MOD, Column(dialect, "a"), Literal(dialect, 7)
        ).to_sql()

        assert sql == '"a" % ?'
        assert params == (7,)
        assert ArithmeticOperator.MOD.value not in sql


class TestTriggerHeaderVocabulary:
    """The words a trigger's header can be read with."""

    def test_the_timing_words_are_the_three_the_grammar_allows(self):
        assert SQLiteIntrospector._TRIGGER_TIMING == (
            "BEFORE", "AFTER", "INSTEAD OF"
        )

    def test_the_event_words_are_the_three_the_grammar_allows(self):
        assert SQLiteIntrospector._TRIGGER_EVENTS == ("DELETE", "INSERT", "UPDATE")

    def test_every_timing_word_is_read_back_out_of_a_header(self):
        for word in SQLiteIntrospector._TRIGGER_TIMING:
            ddl = f"CREATE TRIGGER t {word} ON users BEGIN SELECT 1; END"
            timing, events = SQLiteIntrospector.parse_trigger_header(ddl)

            assert timing == word.upper()
            assert events == []

    def test_every_event_word_is_read_back_out_of_a_header(self):
        for word in SQLiteIntrospector._TRIGGER_EVENTS:
            ddl = f"CREATE TRIGGER t AFTER {word} ON users BEGIN SELECT 1; END"
            timing, events = SQLiteIntrospector.parse_trigger_header(ddl)

            assert timing == "AFTER"
            assert events == [word]

    def test_a_header_naming_several_events_lists_them_all(self):
        ddl = "CREATE TRIGGER t AFTER INSERT OR UPDATE ON users BEGIN SELECT 1; END"

        timing, events = SQLiteIntrospector.parse_trigger_header(ddl)

        assert timing == "AFTER"
        assert sorted(events) == ["INSERT", "UPDATE"]

    def test_a_header_with_no_timing_reads_as_not_stated(self):
        timing, events = SQLiteIntrospector.parse_trigger_header("CREATE TRIGGER t")

        assert timing == ""
        assert events == []


class TestExtractFormats:
    """The strftime code each extractable field renders as."""

    def test_every_field_the_enum_declares_has_a_code(self):
        assert set(SQLiteDateTimeMixin._DATETIME_EXTRACT_FORMATS) == {
            field.value for field in DateTimeField
        }

    def test_every_code_is_a_strftime_conversion(self):
        for field, code in SQLiteDateTimeMixin._DATETIME_EXTRACT_FORMATS.items():
            assert code.startswith("%"), f"{field} renders {code!r}, not a strftime code"

    def test_the_formatter_reads_the_table_for_the_field_it_was_asked(self, dialect):
        source = Literal(dialect, "2024-01-02 03:04:05")
        for field, code in SQLiteDateTimeMixin._DATETIME_EXTRACT_FORMATS.items():
            sql, _ = ExtractExpression(dialect, field, source).to_sql()

            assert f"strftime('{code}'" in sql, (
                f"EXTRACT({field}) no longer renders the code the table holds"
            )


class TestTheFormatterDefaultFormat:
    """The format a formatter starts from, and a subclass can change."""

    @staticmethod
    def _record(message="hello"):
        return logging.LogRecord(
            "rhosocial.activerecord", logging.INFO, __file__, 1, message, None, None
        )

    def test_the_default_is_the_class_attribute_s_own(self):
        """The signature reads the attribute, not a second copy of the sentence.

        The two are compared by *rendering one record* through each: a fresh
        record would carry a different ``asctime`` and the comparison would
        be about the clock. ``__init__`` is what writes ``self`` from ``fmt or
        self.DEFAULT_FORMAT``, so a formatter built with no argument and one
        built with the attribute hold the same sentence, and one built with
        another does not.
        """
        record = self._record()

        assert ActiveRecordFormatter().format(record) == ActiveRecordFormatter(
            fmt=ActiveRecordFormatter.DEFAULT_FORMAT
        ).format(record)

    def test_the_rendered_record_carries_the_sentence_the_attribute_names(self):
        rendered = ActiveRecordFormatter().format(self._record())

        assert " - INFO - [" in rendered
        assert rendered.endswith("] - hello")

    def test_a_subclass_overriding_the_attribute_changes_the_default(self):
        class Terse(ActiveRecordFormatter):
            DEFAULT_FORMAT = "%(message)s"

        assert Terse().format(self._record()) == "hello"
        assert Terse().format(self._record()) != ActiveRecordFormatter().format(
            self._record()
        )
