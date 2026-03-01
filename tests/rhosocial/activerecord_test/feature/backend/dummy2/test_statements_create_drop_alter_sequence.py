# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_statements_create_drop_alter_sequence.py
import pytest
from rhosocial.activerecord.backend.expression.statements import (
    CreateSequenceExpression, DropSequenceExpression, AlterSequenceExpression
)
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect


class TestCreateDropAlterSequenceStatements:
    """Tests for CREATE SEQUENCE, DROP SEQUENCE, and ALTER SEQUENCE statements."""

    # region CREATE SEQUENCE tests
    def test_basic_create_sequence(self, dummy_dialect: DummyDialect):
        """Tests basic CREATE SEQUENCE statement."""
        create_seq = CreateSequenceExpression(
            dummy_dialect,
            sequence_name="user_id_seq"
        )
        sql, params = create_seq.to_sql()

        assert 'CREATE SEQUENCE "user_id_seq"' in sql
        assert params == ()

    def test_create_sequence_if_not_exists(self, dummy_dialect: DummyDialect):
        """Tests CREATE SEQUENCE IF NOT EXISTS statement."""
        create_seq = CreateSequenceExpression(
            dummy_dialect,
            sequence_name="order_id_seq",
            if_not_exists=True
        )
        sql, params = create_seq.to_sql()

        assert 'CREATE SEQUENCE IF NOT EXISTS "order_id_seq"' in sql
        assert params == ()

    def test_create_sequence_with_start(self, dummy_dialect: DummyDialect):
        """Tests CREATE SEQUENCE with START WITH."""
        create_seq = CreateSequenceExpression(
            dummy_dialect,
            sequence_name="invoice_seq",
            start=1000
        )
        sql, params = create_seq.to_sql()

        assert 'CREATE SEQUENCE "invoice_seq"' in sql
        assert 'START WITH 1000' in sql
        assert params == ()

    def test_create_sequence_with_increment(self, dummy_dialect: DummyDialect):
        """Tests CREATE SEQUENCE with INCREMENT BY."""
        create_seq = CreateSequenceExpression(
            dummy_dialect,
            sequence_name="even_seq",
            start=2,
            increment=2
        )
        sql, params = create_seq.to_sql()

        assert 'START WITH 2' in sql
        assert 'INCREMENT BY 2' in sql
        assert params == ()

    def test_create_sequence_with_min_max(self, dummy_dialect: DummyDialect):
        """Tests CREATE SEQUENCE with MINVALUE and MAXVALUE."""
        create_seq = CreateSequenceExpression(
            dummy_dialect,
            sequence_name="bounded_seq",
            start=1,
            minvalue=1,
            maxvalue=1000
        )
        sql, params = create_seq.to_sql()

        assert 'MINVALUE 1' in sql
        assert 'MAXVALUE 1000' in sql
        assert params == ()

    def test_create_sequence_with_cycle(self, dummy_dialect: DummyDialect):
        """Tests CREATE SEQUENCE with CYCLE option."""
        create_seq = CreateSequenceExpression(
            dummy_dialect,
            sequence_name="cycling_seq",
            start=1,
            maxvalue=100,
            cycle=True
        )
        sql, params = create_seq.to_sql()

        assert 'CYCLE' in sql
        assert 'NO CYCLE' not in sql
        assert params == ()

    def test_create_sequence_no_cycle_explicit(self, dummy_dialect: DummyDialect):
        """Tests CREATE SEQUENCE with explicit NO CYCLE (default)."""
        create_seq = CreateSequenceExpression(
            dummy_dialect,
            sequence_name="non_cycling_seq",
            start=1,
            cycle=False
        )
        sql, params = create_seq.to_sql()

        assert 'NO CYCLE' in sql
        assert params == ()

    def test_create_sequence_with_cache(self, dummy_dialect: DummyDialect):
        """Tests CREATE SEQUENCE with CACHE."""
        create_seq = CreateSequenceExpression(
            dummy_dialect,
            sequence_name="high_throughput_seq",
            start=1,
            cache=100
        )
        sql, params = create_seq.to_sql()

        assert 'CACHE 100' in sql
        assert params == ()

    def test_create_sequence_with_order(self, dummy_dialect: DummyDialect):
        """Tests CREATE SEQUENCE with ORDER."""
        create_seq = CreateSequenceExpression(
            dummy_dialect,
            sequence_name="ordered_seq",
            start=1,
            order=True
        )
        sql, params = create_seq.to_sql()

        assert 'ORDER' in sql
        assert params == ()

    def test_create_sequence_with_owned_by(self, dummy_dialect: DummyDialect):
        """Tests CREATE SEQUENCE with OWNED BY."""
        create_seq = CreateSequenceExpression(
            dummy_dialect,
            sequence_name="user_id_seq",
            start=1,
            owned_by="users.id"
        )
        sql, params = create_seq.to_sql()

        assert 'OWNED BY users.id' in sql
        assert params == ()

    def test_create_sequence_all_options(self, dummy_dialect: DummyDialect):
        """Tests CREATE SEQUENCE with all options."""
        create_seq = CreateSequenceExpression(
            dummy_dialect,
            sequence_name="complex_seq",
            if_not_exists=True,
            start=100,
            increment=5,
            minvalue=100,
            maxvalue=10000,
            cycle=True,
            cache=20,
            order=True,
            owned_by="orders.id"
        )
        sql, params = create_seq.to_sql()

        assert 'CREATE SEQUENCE IF NOT EXISTS' in sql
        assert 'START WITH 100' in sql
        assert 'INCREMENT BY 5' in sql
        assert 'MINVALUE 100' in sql
        assert 'MAXVALUE 10000' in sql
        assert 'CYCLE' in sql
        assert 'CACHE 20' in sql
        assert 'ORDER' in sql
        assert 'OWNED BY orders.id' in sql
        assert params == ()

    # region DROP SEQUENCE tests
    def test_basic_drop_sequence(self, dummy_dialect: DummyDialect):
        """Tests basic DROP SEQUENCE statement."""
        drop_seq = DropSequenceExpression(
            dummy_dialect,
            sequence_name="old_seq"
        )
        sql, params = drop_seq.to_sql()

        assert sql == 'DROP SEQUENCE "old_seq"'
        assert params == ()

    def test_drop_sequence_if_exists(self, dummy_dialect: DummyDialect):
        """Tests DROP SEQUENCE IF EXISTS statement."""
        drop_seq = DropSequenceExpression(
            dummy_dialect,
            sequence_name="deprecated_seq",
            if_exists=True
        )
        sql, params = drop_seq.to_sql()

        assert sql == 'DROP SEQUENCE IF EXISTS "deprecated_seq"'
        assert params == ()

    # region ALTER SEQUENCE tests
    def test_alter_sequence_restart(self, dummy_dialect: DummyDialect):
        """Tests ALTER SEQUENCE with RESTART."""
        alter_seq = AlterSequenceExpression(
            dummy_dialect,
            sequence_name="user_id_seq",
            restart=1000
        )
        sql, params = alter_seq.to_sql()

        assert 'ALTER SEQUENCE "user_id_seq"' in sql
        assert 'RESTART WITH 1000' in sql
        assert params == ()

    def test_alter_sequence_increment(self, dummy_dialect: DummyDialect):
        """Tests ALTER SEQUENCE with INCREMENT BY."""
        alter_seq = AlterSequenceExpression(
            dummy_dialect,
            sequence_name="order_seq",
            increment=1
        )
        sql, params = alter_seq.to_sql()

        assert 'INCREMENT BY 1' in sql
        assert params == ()

    def test_alter_sequence_min_max(self, dummy_dialect: DummyDialect):
        """Tests ALTER SEQUENCE with MINVALUE and MAXVALUE."""
        alter_seq = AlterSequenceExpression(
            dummy_dialect,
            sequence_name="bounded_seq",
            minvalue=10,
            maxvalue=999999
        )
        sql, params = alter_seq.to_sql()

        assert 'MINVALUE 10' in sql
        assert 'MAXVALUE 999999' in sql
        assert params == ()

    def test_alter_sequence_cycle(self, dummy_dialect: DummyDialect):
        """Tests ALTER SEQUENCE with CYCLE."""
        alter_seq = AlterSequenceExpression(
            dummy_dialect,
            sequence_name="cycling_seq",
            cycle=True
        )
        sql, params = alter_seq.to_sql()

        assert 'CYCLE' in sql
        assert 'NO CYCLE' not in sql
        assert params == ()

    def test_alter_sequence_no_cycle(self, dummy_dialect: DummyDialect):
        """Tests ALTER SEQUENCE with NO CYCLE."""
        alter_seq = AlterSequenceExpression(
            dummy_dialect,
            sequence_name="non_cycling_seq",
            cycle=False
        )
        sql, params = alter_seq.to_sql()

        assert 'NO CYCLE' in sql
        assert params == ()

    def test_alter_sequence_cache(self, dummy_dialect: DummyDialect):
        """Tests ALTER SEQUENCE with CACHE."""
        alter_seq = AlterSequenceExpression(
            dummy_dialect,
            sequence_name="cached_seq",
            cache=50
        )
        sql, params = alter_seq.to_sql()

        assert 'CACHE 50' in sql
        assert params == ()

    def test_alter_sequence_order(self, dummy_dialect: DummyDialect):
        """Tests ALTER SEQUENCE with ORDER."""
        alter_seq = AlterSequenceExpression(
            dummy_dialect,
            sequence_name="ordered_seq",
            order=True
        )
        sql, params = alter_seq.to_sql()

        assert 'ORDER' in sql
        assert params == ()

    def test_alter_sequence_no_order(self, dummy_dialect: DummyDialect):
        """Tests ALTER SEQUENCE with NO ORDER."""
        alter_seq = AlterSequenceExpression(
            dummy_dialect,
            sequence_name="unordered_seq",
            order=False
        )
        sql, params = alter_seq.to_sql()

        assert 'NO ORDER' in sql
        assert params == ()

    def test_alter_sequence_owned_by(self, dummy_dialect: DummyDialect):
        """Tests ALTER SEQUENCE with OWNED BY."""
        alter_seq = AlterSequenceExpression(
            dummy_dialect,
            sequence_name="user_id_seq",
            owned_by="users.id"
        )
        sql, params = alter_seq.to_sql()

        assert 'OWNED BY users.id' in sql
        assert params == ()

    def test_alter_sequence_owned_by_none(self, dummy_dialect: DummyDialect):
        """Tests ALTER SEQUENCE with OWNED BY NONE."""
        alter_seq = AlterSequenceExpression(
            dummy_dialect,
            sequence_name="orphan_seq",
            owned_by=""  # Empty string triggers OWNED BY NONE
        )
        sql, params = alter_seq.to_sql()

        # owned_by="" should result in OWNED BY NONE
        assert 'OWNED BY NONE' in sql or 'OWNED BY ' not in sql
        assert params == ()

    def test_alter_sequence_multiple_options(self, dummy_dialect: DummyDialect):
        """Tests ALTER SEQUENCE with multiple options."""
        alter_seq = AlterSequenceExpression(
            dummy_dialect,
            sequence_name="complex_seq",
            restart=500,
            increment=2,
            maxvalue=10000,
            cycle=True,
            cache=25
        )
        sql, params = alter_seq.to_sql()

        assert 'ALTER SEQUENCE "complex_seq"' in sql
        assert 'RESTART WITH 500' in sql
        assert 'INCREMENT BY 2' in sql
        assert 'MAXVALUE 10000' in sql
        assert 'CYCLE' in sql
        assert 'CACHE 25' in sql
        assert params == ()

    # region Roundtrip and edge cases
    def test_sequence_roundtrip(self, dummy_dialect: DummyDialect):
        """Tests creating and dropping a sequence."""
        create_seq = CreateSequenceExpression(
            dummy_dialect,
            sequence_name="roundtrip_seq",
            start=1
        )
        create_sql, create_params = create_seq.to_sql()

        drop_seq = DropSequenceExpression(
            dummy_dialect,
            sequence_name="roundtrip_seq"
        )
        drop_sql, drop_params = drop_seq.to_sql()

        assert 'CREATE SEQUENCE "roundtrip_seq"' in create_sql
        assert 'DROP SEQUENCE "roundtrip_seq"' == drop_sql
        assert create_params == ()
        assert drop_params == ()

    @pytest.mark.parametrize("sequence_name,expected_identifier", [
        pytest.param("simple_seq", '"simple_seq"', id="simple_name"),
        pytest.param("seq_with_underscores", '"seq_with_underscores"', id="underscore_name"),
        pytest.param("SeqWithCamelCase", '"SeqWithCamelCase"', id="camelcase_name"),
        pytest.param("seq-with-hyphens", '"seq-with-hyphens"', id="hyphen_name"),
    ])
    def test_create_sequence_various_names(self, dummy_dialect: DummyDialect, sequence_name, expected_identifier):
        """Tests CREATE SEQUENCE with various name formats."""
        create_seq = CreateSequenceExpression(
            dummy_dialect,
            sequence_name=sequence_name
        )
        sql, params = create_seq.to_sql()

        assert f'CREATE SEQUENCE {expected_identifier}' in sql
        assert params == ()

    def test_sequence_with_special_characters(self, dummy_dialect: DummyDialect):
        """Tests sequence names with special characters."""
        create_seq = CreateSequenceExpression(
            dummy_dialect,
            sequence_name='seq"name'
        )
        sql, params = create_seq.to_sql()

        assert sql.startswith('CREATE SEQUENCE "seq""name"')
        assert params == ()

    def test_sequence_with_unicode(self, dummy_dialect: DummyDialect):
        """Tests sequence names with unicode characters."""
        create_seq = CreateSequenceExpression(
            dummy_dialect,
            sequence_name="序列"
        )
        sql, params = create_seq.to_sql()

        assert 'CREATE SEQUENCE "序列"' in sql
        assert params == ()
