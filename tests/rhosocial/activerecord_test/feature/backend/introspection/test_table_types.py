# tests/rhosocial/activerecord_test/feature/backend/introspection/test_table_types.py
"""The table kinds the introspection vocabulary can name.

A catalog reports more than "table" and "view", and the introspector is the
only layer that sees the difference: once a materialized view has been folded
into ``BASE_TABLE`` no later layer can tell it from one. These tests hold the
vocabulary open for the kinds a catalog actually reports.
"""

import pytest

from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
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


class TestSQLiteTableKinds:
    """`PRAGMA table_list` reports four kinds; the parser must keep them apart.

    Rows are handed to the parser directly: this is about the mapping, and a
    database would only add a fixture between the four words and the answer.
    """

    @staticmethod
    def _types(rows):
        backend = SQLiteBackend(database=":memory:")
        parsed = backend.introspector.parse_tables(rows, "main")
        return {table.name: table.table_type for table in parsed}

    def test_ordinary_table_and_view(self):
        kinds = self._types(
            [{"name": "t", "type": "table"}, {"name": "v", "type": "view"}]
        )
        assert kinds == {"t": TableType.BASE_TABLE, "v": TableType.VIEW}

    def test_shadow_tables_are_system_owned_not_external(self):
        # fts_data / fts_idx and friends are created and maintained by the
        # virtual-table module. Reporting them as EXTERNAL would put them in
        # the same bucket as the FTS5 table the user actually created.
        kinds = self._types([{"name": "fts_data", "type": "shadow"}])
        assert kinds == {"fts_data": TableType.SYSTEM_TABLE}

    def test_virtual_tables_are_external(self):
        kinds = self._types([{"name": "fts", "type": "virtual"}])
        assert kinds == {"fts": TableType.EXTERNAL}

    def test_all_four_kinds_in_one_answer(self):
        kinds = self._types(
            [
                {"name": "t", "type": "table"},
                {"name": "v", "type": "view"},
                {"name": "fts", "type": "virtual"},
                {"name": "fts_data", "type": "shadow"},
            ]
        )
        assert kinds == {
            "t": TableType.BASE_TABLE,
            "v": TableType.VIEW,
            "fts": TableType.EXTERNAL,
            "fts_data": TableType.SYSTEM_TABLE,
        }

    def test_unknown_kind_does_not_become_a_base_table(self):
        kinds = self._types([{"name": "x", "type": "something-new"}])
        assert kinds == {"x": TableType.EXTERNAL}
