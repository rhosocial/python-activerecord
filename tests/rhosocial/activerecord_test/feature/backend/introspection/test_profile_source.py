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
"""

import ast
import json
from dataclasses import asdict
from pathlib import Path

import pytest

import rhosocial.activerecord.backend.introspection as introspection_package
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
