# tests/rhosocial/activerecord_test/feature/backend/sqlite/introspection/test_intro_state.py
"""The neutral object-state API as SQLite answers it.

The state shapes are core dataclasses; what this file pins is the mapping
SQLite makes into them. Three answers are easy to get wrong and invisible in
a listing that only says "something was returned":

* ``get_partition_state`` must say "no scheme" (``scheme is None``) rather
  than manufacture an empty scheme or a list of bounds;
* ``STRICT`` and ``WITHOUT ROWID`` are table traits, not table kinds, and
  both can be set at once;
* ``sqlite_sequence`` is an object the engine created for an AUTOINCREMENT
  declaration, so it must appear as a derived object and as a sequence row
  without being reported for a table that never asked for one.
"""

import pytest

from rhosocial.activerecord.backend.introspection.errors import (
    ObjectNotFoundError,
)
from rhosocial.activerecord.backend.introspection.types import (
    ConstraintState,
    DerivedObjectState,
    IndexState,
    ItemKind,
    PartitionState,
    SequenceState,
    TableState,
)

# Checking the temp schema by name makes the dialect warn that ``temp`` is a
# reserved word; the statement it builds is correct, so the warning is noise.
pytestmark = pytest.mark.filterwarnings("ignore:Identifier 'temp' is a reserved word")

DDL = """
CREATE TABLE accounts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    nickname TEXT CHECK (nickname <> ''),
    status TEXT DEFAULT 'CHECK(nope)',
    note TEXT DEFAULT 'a,b'
);
CREATE INDEX idx_accounts_nickname ON accounts(nickname);
CREATE UNIQUE INDEX idx_accounts_email_active ON accounts(email)
    WHERE status = 'active';
CREATE TABLE ledger (
    id INTEGER PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES accounts(id),
    memo TEXT,
    CONSTRAINT uq_memo UNIQUE(account_id, memo),
    CONSTRAINT ck_memo CHECK (length(memo) <= 20)
);
CREATE TABLE strict_table (a INTEGER PRIMARY KEY, b TEXT) STRICT;
CREATE TABLE strict_wr (a TEXT PRIMARY KEY, b TEXT) STRICT, WITHOUT ROWID;
CREATE TEMP TABLE temp_notes (body TEXT);
"""


@pytest.fixture()
def state_backend(sqlite_backend):
    sqlite_backend.executescript(DDL)
    sqlite_backend.execute("INSERT INTO accounts(email, nickname) VALUES ('a@example.com', 'a')")
    return sqlite_backend


class TestTableState:
    def test_regular_table_has_no_traits(self, state_backend):
        state = state_backend.introspector.get_table_state("accounts")

        assert isinstance(state, TableState)
        assert state.schema == "main"
        assert state.kind == "regular"
        assert state.traits == ()
        assert state.comment is None
        assert state.partitioning is None

    def test_strict_is_a_trait(self, state_backend):
        state = state_backend.introspector.get_table_state("strict_table")

        assert state.kind == "regular"
        assert state.traits == ("strict",)

    def test_strict_and_without_rowid_are_both_traits(self, state_backend):
        state = state_backend.introspector.get_table_state("strict_wr")

        assert state.kind == "regular"
        assert set(state.traits) == {"strict", "without_rowid"}

    def test_a_temp_table_is_temporary_without_an_explicit_schema(self, state_backend):
        state = state_backend.introspector.get_table_state("temp_notes")

        assert state.schema == "temp"
        assert state.kind == "temporary"

    def test_a_missing_table_is_reported_not_invented(self, state_backend):
        with pytest.raises(ObjectNotFoundError) as caught:
            state_backend.introspector.get_table_state("missing")

        assert caught.value.object_name == "missing"


class TestPartitionState:
    def test_unpartitioned_is_none_not_empty_bounds(self, state_backend):
        state = state_backend.introspector.get_partition_state("accounts")

        assert isinstance(state, PartitionState)
        assert state.scheme is None
        assert state.bounds == ()
        assert state.key_columns == ()

    def test_stats_do_not_change_the_answer(self, state_backend):
        plain = state_backend.introspector.get_partition_state("accounts")
        with_stats = state_backend.introspector.get_partition_state("accounts", include_stats=True)

        assert with_stats.scheme is None
        assert with_stats.bounds == plain.bounds

    def test_a_missing_table_is_reported(self, state_backend):
        with pytest.raises(ObjectNotFoundError):
            state_backend.introspector.get_partition_state("missing")


class TestIndexStates:
    def test_autoindex_is_flagged(self, state_backend):
        indexes = state_backend.introspector.list_index_states("accounts")

        auto = next(i for i in indexes if i.name.startswith("sqlite_autoindex_"))
        assert isinstance(auto, IndexState)
        assert auto.table == "accounts"
        assert auto.schema == "main"
        assert auto.unique is True
        assert auto.raw["autoindex"] is True
        assert auto.raw["origin"] == "u"

    def test_partial_index_carries_its_predicate(self, state_backend):
        indexes = state_backend.introspector.list_index_states("accounts")

        partial = next(i for i in indexes if i.name == "idx_accounts_email_active")
        assert partial.unique is True
        assert partial.predicate == "status = 'active'"
        assert partial.raw["partial"] is True

    def test_sqlite_indexes_are_btree_usable_and_visible(self, state_backend):
        indexes = state_backend.introspector.list_index_states("accounts")

        assert indexes
        for index in indexes:
            assert index.method == "btree"
            assert index.usable is True
            assert index.visible is True

    def test_a_missing_table_has_no_indexes(self, state_backend):
        assert state_backend.introspector.list_index_states("missing") == []


class TestConstraintStates:
    def test_all_four_kinds_are_reported(self, state_backend):
        states = state_backend.introspector.list_constraint_states("ledger")

        kinds = {state.kind for state in states}
        assert {"primary_key", "unique", "check", "foreign_key"} <= kinds
        for state in states:
            assert isinstance(state, ConstraintState)
            assert state.table == "ledger"

    def test_a_unique_constraint_names_its_backing_autoindex(self, state_backend):
        states = state_backend.introspector.list_constraint_states("ledger")

        unique = next(state for state in states if state.kind == "unique")
        assert unique.backing_index.startswith("sqlite_autoindex_")
        assert unique.raw["columns"] == ["account_id", "memo"]

    def test_a_named_check_keeps_its_name_and_expression(self, state_backend):
        states = state_backend.introspector.list_constraint_states("ledger")

        check = next(state for state in states if state.kind == "check")
        assert check.name == "ck_memo"
        assert check.raw["named"] is True
        assert check.raw["table_constraint"] is True
        assert check.raw["expression"] == "length(memo) <= 20"

    def test_an_unnamed_check_gets_a_label_that_says_so(self, state_backend):
        states = state_backend.introspector.list_constraint_states("accounts")

        checks = [state for state in states if state.kind == "check"]
        assert len(checks) == 1
        check = checks[0]
        assert check.raw["named"] is False
        assert "nickname" in check.raw["expression"]

    def test_foreign_key_reports_the_connection_switch(self, state_backend):
        states = state_backend.introspector.list_constraint_states("ledger")

        fk = next(state for state in states if state.kind == "foreign_key")
        assert fk.raw["referenced_table"] == "accounts"
        assert fk.raw["columns"] == ["account_id"]
        assert fk.enforced is True
        assert fk.raw["foreign_keys_pragma"] is True


class TestDerivedObjects:
    def test_autoincrement_derives_sqlite_sequence(self, state_backend):
        derived = state_backend.introspector.list_derived_objects("accounts")

        sequence = next(obj for obj in derived if obj.kind == "identity_sequence")
        assert isinstance(sequence, DerivedObjectState)
        assert sequence.name == "sqlite_sequence"
        assert sequence.owned_by == "accounts"

    def test_unique_clause_derives_an_autoindex(self, state_backend):
        derived = state_backend.introspector.list_derived_objects("accounts")

        autoindexes = [obj for obj in derived if obj.kind == "autoindex"]
        assert autoindexes
        assert all(obj.name.startswith("sqlite_autoindex_") for obj in autoindexes)

    def test_a_plain_table_derives_nothing(self, state_backend):
        assert state_backend.introspector.list_derived_objects("strict_table") == []


class TestSequenceStates:
    def test_sqlite_sequence_rows_become_sequence_states(self, state_backend):
        states = state_backend.introspector.list_sequence_states()

        assert len(states) == 1
        state = states[0]
        assert isinstance(state, SequenceState)
        assert state.name == "accounts"
        assert state.owned_by == "accounts"
        assert state.schema == "main"
        assert state.start is None
        assert state.increment is None
        assert state.raw["last_value"] == 1

    def test_a_database_without_autoincrement_has_no_sequences(self, state_backend):
        assert state_backend.introspector.list_sequence_states(schema="temp") == []


class TestSchemas:
    def test_main_and_temp_are_always_named(self, state_backend):
        names = state_backend.introspector.list_schemas()

        assert names[:2] == ["main", "temp"]

    def test_an_attached_database_is_named(self, state_backend):
        state_backend.executescript("ATTACH DATABASE ':memory:' AS aux;")

        assert "aux" in state_backend.introspector.list_schemas()


class TestItemExists:
    def test_tables_indexes_and_sequences_exist(self, state_backend):
        introspector = state_backend.introspector

        assert introspector.item_exists(ItemKind.TABLE, "accounts") is True
        assert introspector.item_exists(ItemKind.TABLE, "temp_notes") is True
        assert introspector.item_exists(ItemKind.INDEX, "idx_accounts_nickname") is True
        assert introspector.item_exists(ItemKind.INDEX, "sqlite_autoindex_accounts_1") is True
        assert introspector.item_exists(ItemKind.SEQUENCE, "sqlite_sequence") is True
        assert introspector.item_exists(ItemKind.SEQUENCE, "accounts") is True

    def test_absent_objects_do_not_exist(self, state_backend):
        introspector = state_backend.introspector

        assert introspector.item_exists(ItemKind.TABLE, "missing") is False
        assert introspector.item_exists(ItemKind.INDEX, "missing") is False
        assert introspector.item_exists(ItemKind.SEQUENCE, "missing") is False
        assert introspector.item_exists(ItemKind.SCHEMA, "missing") is False

    def test_sqlite_has_no_type_objects_to_find(self, state_backend):
        assert state_backend.introspector.item_exists(ItemKind.TYPE, "accounts") is False


class TestAsyncStateApi:
    @pytest.mark.asyncio
    async def test_the_async_twin_answers_the_same_facts(self, async_sqlite_memory_backend):
        backend = async_sqlite_memory_backend
        await backend.executescript(DDL)
        await backend.execute("INSERT INTO accounts(email, nickname) VALUES ('a@example.com', 'a')")
        introspector = backend.introspector

        regular = await introspector.get_table_state("accounts")
        strict_wr = await introspector.get_table_state("strict_wr")
        temporary = await introspector.get_table_state("temp_notes")
        partition = await introspector.get_partition_state("accounts")
        indexes = await introspector.list_index_states("accounts")
        constraints = await introspector.list_constraint_states("ledger")
        derived = await introspector.list_derived_objects("accounts")
        sequences = await introspector.list_sequence_states()
        schemas = await introspector.list_schemas()

        assert regular.kind == "regular"
        assert strict_wr.traits and set(strict_wr.traits) == {
            "strict",
            "without_rowid",
        }
        assert temporary.kind == "temporary"
        assert partition.scheme is None
        autoindex = next(index for index in indexes if index.name.startswith("sqlite_autoindex_"))
        assert autoindex.raw["autoindex"] is True
        partial = next(index for index in indexes if index.name == "idx_accounts_email_active")
        assert partial.predicate == "status = 'active'"
        assert {state.kind for state in constraints} >= {
            "primary_key",
            "unique",
            "check",
            "foreign_key",
        }
        assert any(obj.kind == "identity_sequence" for obj in derived)
        assert [state.name for state in sequences] == ["accounts"]
        assert schemas[:2] == ["main", "temp"]
        assert await introspector.item_exists(ItemKind.TABLE, "accounts") is True
        assert await introspector.item_exists(ItemKind.INDEX, "idx_accounts_nickname") is True
        assert await introspector.item_exists(ItemKind.SEQUENCE, "sqlite_sequence") is True
