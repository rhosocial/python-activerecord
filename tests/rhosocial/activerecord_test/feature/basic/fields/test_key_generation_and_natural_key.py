# tests/rhosocial/activerecord_test/feature/basic/fields/test_key_generation_and_natural_key.py
"""UUID version selection and the declared natural key.

Both are declaration-surface facts (A1 / A2 of the governance plan): the
UUID variant is chosen by overriding ``uuid_version()`` and the natural
key by overriding ``natural_key()``.
"""
import uuid
from typing import ClassVar, Optional

from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.base import FieldProxy
from rhosocial.activerecord.field import UUIDMixin
from rhosocial.activerecord.model import ActiveRecord, AsyncActiveRecord

import pytest

HAS_UUID7 = getattr(uuid, "uuid7", None) is not None


class Uuid4Record(UUIDMixin, ActiveRecord):
    @classmethod
    def table_name(cls):
        return "a1_uuid4"

    c: ClassVar[FieldProxy] = FieldProxy()

    label: str = ""


class Uuid7Record(UUIDMixin, ActiveRecord):
    @classmethod
    def table_name(cls):
        return "a1_uuid7"

    @classmethod
    def uuid_version(cls):
        return "uuid7"

    c: ClassVar[FieldProxy] = FieldProxy()

    label: str = ""


class TestUuidVersionSelection:
    def test_default_generates_v4(self):
        assert Uuid4Record.uuid_version() == "uuid4"
        record = Uuid4Record()
        assert record.id.version == 4

    def test_override_selects_v7(self):
        assert Uuid7Record.uuid_version() == "uuid7"

    @pytest.mark.skipif(not HAS_UUID7, reason="uuid.uuid7 needs Python 3.14+")
    def test_v7_is_generated_with_its_version(self):
        record = Uuid7Record()
        assert record.id.version == 7

    @pytest.mark.skipif(HAS_UUID7, reason="uuid.uuid7 is available here")
    def test_v7_without_stdlib_support_says_what_is_missing(self):
        # The probe, not an import: the message must name the declaration
        # and the interpreter requirement, because that is what the reader
        # needs to fix it.
        with pytest.raises(RuntimeError, match="Python 3.14"):
            Uuid7Record()

    def test_unknown_variant_is_rejected(self):
        class WrongVariant(UUIDMixin, ActiveRecord):
            @classmethod
            def table_name(cls):
                return "a1_uuid_bad"

            @classmethod
            def uuid_version(cls):
                return "uuid9"

            c: ClassVar[FieldProxy] = FieldProxy()

        with pytest.raises(ValueError, match="uuid4"):
            WrongVariant()

    def test_declared_key_value_still_wins(self):
        given = uuid.uuid4()
        record = Uuid4Record(id=given)
        assert record.id == given


class NamedAccount(ActiveRecord):
    @classmethod
    def table_name(cls):
        return "a2_named_accounts"

    @classmethod
    def natural_key(cls):
        return ("tenant", "external_id")

    c: ClassVar[FieldProxy] = FieldProxy()

    id: Optional[int] = None
    tenant: str
    external_id: str
    note: str = ""


class UnnamedAccount(ActiveRecord):
    @classmethod
    def table_name(cls):
        return "a2_unnamed_accounts"

    c: ClassVar[FieldProxy] = FieldProxy()

    id: Optional[int] = None
    tenant: str
    external_id: str


class TestNaturalKeyDeclaration:
    def test_default_is_empty(self):
        assert UnnamedAccount.natural_key() == ()

    def test_override_is_reported(self):
        assert NamedAccount.natural_key() == ("tenant", "external_id")

    def test_unknown_field_is_rejected_at_class_creation(self):
        with pytest.raises(TypeError, match="does not define"):
            class BadKey(ActiveRecord):
                @classmethod
                def table_name(cls):
                    return "a2_bad_key"

                @classmethod
                def natural_key(cls):
                    return ("nope",)

                c: ClassVar[FieldProxy] = FieldProxy()

                id: Optional[int] = None

    def test_repeated_field_is_rejected_at_class_creation(self):
        with pytest.raises(TypeError, match="repeats"):
            class RepeatedKey(ActiveRecord):
                @classmethod
                def table_name(cls):
                    return "a2_repeated_key"

                @classmethod
                def natural_key(cls):
                    return ("tenant", "tenant")

                c: ClassVar[FieldProxy] = FieldProxy()

                id: Optional[int] = None
                tenant: str


class AsyncNamedAccount(AsyncActiveRecord):
    @classmethod
    def table_name(cls):
        return "a2_named_accounts_async"

    @classmethod
    def natural_key(cls):
        return ("tenant", "external_id")

    c: ClassVar[FieldProxy] = FieldProxy()

    id: Optional[int] = None
    tenant: str
    external_id: str
    note: str = ""


NAMED_DDL = (
    'CREATE TABLE "{table}" ('
    '"id" INTEGER PRIMARY KEY AUTOINCREMENT, '
    '"tenant" TEXT NOT NULL, '
    '"external_id" TEXT NOT NULL, '
    '"note" TEXT NOT NULL DEFAULT \'\')'
)


class TestNaturalKeyConsumption:
    @pytest.fixture
    def configured(self, tmp_path):
        NamedAccount.configure(
            SQLiteConnectionConfig(database=str(tmp_path / "natural.db")), SQLiteBackend
        )
        NamedAccount.backend().execute(NAMED_DDL.format(table="a2_named_accounts"))
        return NamedAccount

    def test_empty_lookup_uses_the_declared_key(self, configured):
        row, created = configured.find_one_or_create(
            defaults={"tenant": "acme", "external_id": "X-1", "note": "first"}
        )
        assert created is True
        assert row.tenant == "acme" and row.external_id == "X-1"

        again, created_again = configured.find_one_or_create(
            defaults={"tenant": "acme", "external_id": "X-1", "note": "ignored"}
        )
        assert created_again is False
        assert again.id == row.id
        assert again.note == "first"

    def test_explicit_lookup_still_wins(self, configured):
        first, _ = configured.find_one_or_create(
            defaults={"tenant": "acme", "external_id": "X-2"}
        )
        row, created = configured.find_one_or_create(
            tenant="acme", external_id="X-2", defaults={"note": "second"}
        )
        assert created is False
        assert row.id == first.id

    def test_missing_key_member_names_what_is_absent(self, configured):
        with pytest.raises(ValueError, match="external_id"):
            configured.find_one_or_create(defaults={"tenant": "acme"})

    def test_undeclared_model_keeps_requiring_a_lookup(self, tmp_path):
        UnnamedAccount.configure(
            SQLiteConnectionConfig(database=str(tmp_path / "unnamed.db")), SQLiteBackend
        )
        with pytest.raises(ValueError, match="at least one lookup field"):
            UnnamedAccount.find_one_or_create(defaults={"tenant": "acme"})

    @pytest.mark.asyncio
    async def test_async_twin_uses_the_declared_key(self, async_user_class):
        # Same fixture-based backend as the rest of the async tests: a
        # freshly configured async backend would open its own loop-bound
        # connection, while this one is already wired to the test loop.
        backend = async_user_class.backend()
        AsyncNamedAccount.__backend__ = backend
        await backend.execute('DROP TABLE IF EXISTS "a2_named_accounts_async"')
        await backend.executescript(NAMED_DDL.format(table="a2_named_accounts_async"))

        row, created = await AsyncNamedAccount.find_one_or_create(
            defaults={"tenant": "acme", "external_id": "X-9"}
        )
        assert created is True
        again, created_again = await AsyncNamedAccount.find_one_or_create(
            defaults={"tenant": "acme", "external_id": "X-9"}
        )
        assert created_again is False
        assert again.id == row.id
