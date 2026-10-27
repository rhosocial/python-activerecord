# tests/rhosocial/activerecord_test/feature/backend/introspection/test_table_types.py
"""The table kinds the introspection vocabulary can name.

A catalog reports more than "table" and "view", and the introspector is the
only layer that sees the difference: once a materialized view has been folded
into ``BASE_TABLE`` no later layer can tell it from one. These tests hold the
vocabulary open for the kinds a catalog actually reports.
"""

import pytest

from rhosocial.activerecord.backend.introspection.types import TableType

pytestmark = [pytest.mark.feature, pytest.mark.backend]


class TestTableTypeSpellings:
    def test_materialized_view_is_distinct_from_a_base_table(self):
        assert TableType.MATERIALIZED_VIEW.value == "MATERIALIZED_VIEW"
        assert TableType.MATERIALIZED_VIEW is not TableType.BASE_TABLE

    def test_materialized_view_is_distinct_from_a_view(self):
        # A view is recomputed on every read; a materialized view holds rows
        # and is refreshed. Sharing VIEW would erase the refresh semantics.
        assert TableType.MATERIALIZED_VIEW is not TableType.VIEW

    def test_partitioned_table_is_distinct_from_a_base_table(self):
        assert TableType.PARTITIONED_TABLE.value == "PARTITIONED_TABLE"
        assert TableType.PARTITIONED_TABLE is not TableType.BASE_TABLE

    def test_foreign_table_is_distinct_from_an_external_table(self):
        assert TableType.FOREIGN_TABLE.value == "FOREIGN_TABLE"
        assert TableType.FOREIGN_TABLE is not TableType.EXTERNAL

    def test_every_member_has_its_own_spelling(self):
        spellings = [member.value for member in TableType]
        assert len(spellings) == len(set(spellings))
