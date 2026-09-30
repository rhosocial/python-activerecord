# tests/rhosocial/activerecord_test/feature/backend/dialect/test_view_support_invariants.py
"""Invariants over ``ViewSupport`` declarations.

Two contract mismatches motivated these:

* ``format_create_view_statement`` gates on ``supports_create_or_replace_view``
  and ``supports_if_not_exists_view``, neither of which the protocol declared.
  A capability scan of the protocol therefore saw a different contract than the
  generic renderer followed.
* Nothing connected "I support this" to "I render it". A backend can declare
  CREATE OR REPLACE VIEW and inherit the generic renderer, which ignores the
  flag and emits ``CREATE VIEW`` -- a silent downgrade at execution time rather
  than at capability-check time.
"""

import pytest

from rhosocial.activerecord.backend.dialect.mixins.ddl_view import ViewMixin
from rhosocial.activerecord.backend.dialect.protocols import ViewSupport
from rhosocial.activerecord.backend.expression import (
    Column,
    CreateViewExpression,
    QueryExpression,
    TableExpression,
)
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect

# Every real dialect in the tree mixes ViewMixin in, which is what supplies the
# probes below; a dialect that does not is not structurally a ViewSupport.
MIXIN_SUPPLIED_PROBES = (
    "supports_create_or_replace_view",
    "supports_if_not_exists_view",
    "supports_or_replace_view",
)


class TestProtocolMatchesTheRenderer:
    def test_probes_the_renderer_calls_are_declared(self):
        """A probe the renderer reads must be part of the declared contract."""
        for probe in MIXIN_SUPPLIED_PROBES:
            assert hasattr(ViewSupport, probe), (
                f"format_create_view_statement reads {probe}, "
                f"but ViewSupport does not declare it"
            )

    def test_protocol_declares_no_probe_the_renderer_ignores(self):
        """The reverse direction: nothing declared goes unread."""
        renderer_calls = {
            "supports_create_or_replace_view",
            "supports_if_not_exists_view",
        }
        declared = {m for m in dir(ViewSupport) if m.startswith("supports_")}
        # or_replace is the legacy spelling of one of the above; both are read.
        renderer_calls.add("supports_or_replace_view")
        assert renderer_calls <= declared, renderer_calls - declared


class TestProbeNamesAgree:
    """Both spellings answer the same question, on every dialect."""

    @pytest.mark.parametrize("answer", [True, False])
    def test_overriding_only_the_legacy_name_reaches_the_renderer(self, answer):
        """MariaDB / Firebird declare only supports_or_replace_view.

        The renderer gates on the other name, so the derivation has to run
        that direction. If it ran the other way these backends would be
        ignored and the core default would apply instead.
        """
        class LegacyOnly(ViewMixin):
            def supports_or_replace_view(self) -> bool:
                return answer

        assert LegacyOnly().supports_create_or_replace_view() is answer

    @pytest.mark.parametrize("answer", [True, False])
    def test_overriding_only_the_renderer_name_is_kept(self, answer):
        """Oracle / Snowflake / BigQuery / SQLServer declare only the new name."""
        class ModernOnly(ViewMixin):
            def supports_create_or_replace_view(self) -> bool:
                return answer

        assert ModernOnly().supports_create_or_replace_view() is answer

    def test_both_spellings_agree_by_default(self):
        class Bare(ViewMixin):
            pass

        assert Bare().supports_or_replace_view() is False
        assert Bare().supports_create_or_replace_view() is False


class TestSupportImpliesRendering:
    """Declaring a capability must not be silently ignored at render time."""

    def _view(self, dialect, **kwargs):
        query = QueryExpression(
            dialect, select=[Column(dialect, "id")], from_=TableExpression(dialect, "t")
        )
        return CreateViewExpression(dialect, view_name="v", query=query, **kwargs)

    def test_replace_requested_and_unsupported_raises(self):
        """The generic renderer refuses rather than dropping the flag.

        This is the shape SQLite needed: it has no CREATE OR REPLACE VIEW, and
        rendering the statement without it would hand the caller a definition
        that was never replaced.
        """
        from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError

        class NoReplace(DummyDialect):
            name = "NoReplace"

            def supports_create_or_replace_view(self) -> bool:
                return False

        with pytest.raises(UnsupportedFeatureError):
            self._view(NoReplace(), replace=True).to_sql()

    def test_if_not_exists_requested_and_unsupported_is_refused(self):
        """A silently dropped IF NOT EXISTS turns a conflict into a silent skip."""
        from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError

        class NoIfNotExists(DummyDialect):
            name = "NoIfNotExists"

            def supports_if_not_exists_view(self) -> bool:
                return False

        with pytest.raises(UnsupportedFeatureError):
            self._view(NoIfNotExists(), if_not_exists=True).to_sql()

    def test_supported_flags_reach_the_rendered_sql(self):
        class Everything(DummyDialect):
            name = "Everything"

        sql, _ = self._view(Everything(), replace=True).to_sql()
        assert "OR REPLACE" in sql
