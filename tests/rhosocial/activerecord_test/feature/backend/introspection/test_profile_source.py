# tests/rhosocial/activerecord_test/feature/backend/introspection/test_profile_source.py
"""The closed set ``ColumnDataProfile.source`` is typed with.

``ProfileSource`` sat in core for a whole branch with nothing constructing a
member: the engines wrote ``source="estimate"`` and ``"aggregate"`` by hand,
and the closed set was a comment. Typing the slot with the Enum is only safe
because the Enum is a ``str`` -- a consumer writing the engine's own word
still gets a value that compares equal to the member that names it, and the
JSON artifact still carries the word rather than a class name. These tests are
what keeps that true. Dropping the ``str`` base, or renaming a member's value,
is a change to every consumer, not a tidy-up.

Being typed is only half of it. The shared parser writes what the engine
projected into the slot, and a word written into a slot typed with an Enum is
still a word: ``ProfileSource.AGGREGATE == "aggregate"`` is True, so an
assertion written with ``==`` cannot tell a member from the string that spells
it. The tests below therefore assert *identity* where the parser is concerned
-- ``is``, which a plain string never satisfies.
"""

import ast
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

import rhosocial.activerecord.backend.introspection as introspection_package
from rhosocial.activerecord.backend.introspection.base import IntrospectorBase
from rhosocial.activerecord.backend.introspection.types import (
    ColumnDataProfile,
    ProfileSource,
)

pytestmark = [pytest.mark.feature, pytest.mark.backend]

#: This repository's source tree: the test file sits at
#: ``tests/rhosocial/activerecord_test/feature/backend/introspection/``.
_SOURCE = Path(__file__).resolve().parents[6] / "src"


def _profile(source):
    """One profile whose only interesting slot is its provenance."""
    return ColumnDataProfile(
        schema="public",
        table_name="orders",
        column_name="status",
        null_fraction=0.1,
        source=source,
    )


class _Parser(IntrospectorBase):
    """An introspector with no database behind it, which is all a parser needs.

    ``parse_column_data_profiles`` reads the rows it is handed and nothing
    else: no executor, no cache, no dialect. The eight stubs are what the
    abstract base asks for, and they are stubs because this test never calls
    them -- which is the point of the parser being a pure function of its
    rows.
    """

    def parse_columns(self, rows, schema: Optional[str]) -> List[Dict[str, Any]]:
        raise NotImplementedError

    def parse_database_info(self, rows) -> Dict[str, Any]:
        raise NotImplementedError

    def parse_foreign_keys(self, rows, schema: Optional[str]):
        raise NotImplementedError

    def parse_indexes(self, rows, schema: Optional[str]):
        raise NotImplementedError

    def parse_tables(self, rows, schema: Optional[str]):
        raise NotImplementedError

    def parse_triggers(self, rows, schema: Optional[str]):
        raise NotImplementedError

    def parse_view_info(self, rows, schema: Optional[str]):
        raise NotImplementedError

    def parse_views(self, rows, schema: Optional[str]):
        raise NotImplementedError


@pytest.fixture
def parser():
    """The shared parser, reachable without a connection."""
    return _Parser(backend=None, executor=None)


class TestTheClosedSet:
    """The four words are the wire format, not decoration."""

    def test_each_member_spells_the_word_a_consumer_writes(self):
        assert ProfileSource.ESTIMATE.value == "estimate"
        assert ProfileSource.AGGREGATE.value == "aggregate"
        assert ProfileSource.SAMPLE.value == "sample"
        assert ProfileSource.UNKNOWN.value == "unknown"

    def test_the_enum_is_a_str(self):
        # The whole reason the slot could be tightened without a second round
        # of changes in nine repositories.
        assert issubclass(ProfileSource, str)

    def test_nothing_in_this_repository_produces_a_sample_yet(self):
        """``SAMPLE`` is declared and has no producer, and that is a fact.

        An engine that measures a subset of rows will name the member; until
        one does, a profile claiming a sample would be a claim nothing made.
        The test walks the source tree rather than a list of modules so a new
        producer has to be announced here.
        """
        producers = []
        for path in _SOURCE.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            for node in ast.walk(tree):
                if isinstance(node, ast.Attribute) and node.attr == "SAMPLE":
                    if isinstance(node.value, ast.Name) and node.value.id == "ProfileSource":
                        producers.append(f"{path.relative_to(_SOURCE.parent.parent)}:{node.lineno}")
        assert not producers, f"a producer of ProfileSource.SAMPLE appeared: {producers}"


class TestTheSlot:
    """Both spellings a consumer can write land in the same slot."""

    def test_the_member_assigns(self):
        profile = _profile(ProfileSource.ESTIMATE)

        assert profile.source is ProfileSource.ESTIMATE

    def test_the_engines_own_word_still_assigns(self):
        profile = _profile("estimate")

        assert profile.source == ProfileSource.ESTIMATE

    def test_the_two_spellings_are_the_same_fact(self):
        from_member = _profile(ProfileSource.AGGREGATE)
        from_word = _profile("aggregate")

        assert from_member.source == from_word.source
        assert asdict(from_member) == asdict(from_word)

    def test_an_absent_source_is_still_none(self):
        profile = ColumnDataProfile(table_name="orders", column_name="status")

        assert profile.source is None


class TestTheParser:
    """What the shared parser writes into a slot typed with a member.

    The parser is the boundary an engine's word crosses, and it used to cross
    it unchanged: ``source=_first(row, "source")`` wrote the bare string into
    the slot, and ``== ProfileSource.AGGREGATE`` was True while ``is`` was
    False. Identity is what is asserted here, because equality cannot tell a
    member from the word that spells it -- which is exactly how the defect
    survived a whole branch with a typed slot and a test that read it.
    """

    def test_the_engine_s_word_becomes_the_member(self, parser):
        found = parser.parse_column_data_profiles(
            [{"column_name": "status", "source": "aggregate", "row_count": 10}],
            "main",
            "orders",
        )

        assert len(found) == 1
        assert found[0].source is ProfileSource.AGGREGATE

    def test_the_member_a_caller_wrote_is_returned_unchanged(self, parser):
        """The Enum's own lookup, so a member is not re-resolved into another."""
        found = parser.parse_column_data_profiles(
            [{"column_name": "status", "source": ProfileSource.ESTIMATE}],
            "main",
            "orders",
        )

        assert found[0].source is ProfileSource.ESTIMATE

    def test_a_row_the_engine_said_nothing_about_stays_none(self, parser):
        """``None`` means "not measured", and ``_first`` already decides that."""
        found = parser.parse_column_data_profiles(
            [{"column_name": "note", "row_count": 10}],
            "main",
            "orders",
        )

        assert found[0].source is None

    def test_a_word_the_set_does_not_name_is_refused(self, parser):
        """A typo is not a fact, and ``UNKNOWN`` would have made it one.

        ``UNKNOWN`` is the engine declining to say how it measured. A word no
        member spells is a spelling nobody validated, and the parser is where
        it is caught -- which is what stops a misspelling reaching a consumer
        as a legitimate "the engine would not say".
        """
        with pytest.raises(ValueError) as raised:
            parser.parse_column_data_profiles(
                [{"column_name": "status", "source": "agregate"}],
                "main",
                "orders",
            )

        assert "agregate" in str(raised.value)
        assert "ProfileSource" in str(raised.value)


class TestSerialisation:
    """The artifact carries the word, whichever spelling was written."""

    def test_the_word_is_what_reaches_json(self):
        artifact = json.dumps(asdict(_profile(ProfileSource.ESTIMATE)))

        assert '"source": "estimate"' in artifact
        assert "ProfileSource" not in artifact

    def test_the_artifact_is_byte_identical_for_both_spellings(self):
        from_member = json.dumps(asdict(_profile(ProfileSource.ESTIMATE)))
        from_word = json.dumps(asdict(_profile("estimate")))

        assert from_member == from_word

    def test_the_cli_output_path_maps_a_member_to_its_word(self):
        """The serialisation helper the CLIs share unwraps the Enum."""
        from rhosocial.activerecord.backend.impl.sqlite.cli.introspect import (
            _serialize_for_output,
        )

        assert _serialize_for_output(_profile(ProfileSource.ESTIMATE))["source"] == "estimate"
        assert _serialize_for_output(_profile("estimate"))["source"] == "estimate"

    def test_the_introspection_package_the_parser_reads_from(self):
        # The slot is part of the public contract of this package, which is
        # what the annotation now says out loud.
        assert introspection_package.types.ProfileSource is ProfileSource
