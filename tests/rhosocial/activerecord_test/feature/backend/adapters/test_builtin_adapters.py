# tests/rhosocial/activerecord_test/feature/backend/adapters/test_builtin_adapters.py
"""The seven built-in adapters, and the base contract they all inherit.

These are the framework's own conversions, not a backend's: a backend that
registers nothing still inherits this layer through ``TypeAdaptionMixin``
(``base/type_adaption.py``). The tests here are therefore backend-free -- each
adapter is exercised directly, and the subject is the conversion contract
itself: **which target types each adapter claims, and what it produces for
them.**

Two shapes recur and are asserted once, in the base-class section, rather than
repeated per adapter:

* ``None`` never reaches a subclass: both directions answer it in the base
  (write as ``None``, read as ``_on_none_from_database``).
* an ``Optional[T]`` annotation is unwrapped to ``T`` before conversion, while
  a genuine multi-member ``Union`` is not -- guessing which member a stored
  value belongs to is not a conversion the adapter can justify.
"""

import datetime
import uuid
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, Optional, Type, Union

import pytest

from rhosocial.activerecord.backend.errors import TypeConversionError
from rhosocial.activerecord.backend.type_adapter import (
    ArrayAdapter,
    BaseSQLTypeAdapter,
    BooleanAdapter,
    DateTimeAdapter,
    DecimalAdapter,
    EnumAdapter,
    JSONAdapter,
    UUIDAdapter,
)


class Colour(Enum):
    """One string-valued member and one int-valued member, so ``.value`` is
    observable in both of the shapes the adapter must handle."""

    RED = "red"
    ONE = 1


class _Neutral(BaseSQLTypeAdapter):
    """A concrete adapter with a declared neutral type, for the error message."""

    neutral_type = Colour

    def _do_to_database(
        self, value: Any, target_type: Type, options: Optional[Dict[str, Any]]
    ) -> Any:
        raise NotImplementedError

    def _do_from_database(
        self, value: Any, target_type: Type, options: Optional[Dict[str, Any]]
    ) -> Any:
        raise NotImplementedError


class _Nameless(_Neutral):
    """The same adapter without a neutral type: the message falls back to the
    value's own class."""

    neutral_type = None


class _EmptyAnswering(_Neutral):
    """Overrides the None answer, the way a backend can for a non-optional
    column whose store spells absence as ``''``."""

    def _on_none_from_database(self, target_type: Type, **kwargs) -> Any:
        return ""


# ---------------------------------------------------------------------------
# 1. The base contract
# ---------------------------------------------------------------------------


def test_the_base_is_abstract():
    with pytest.raises(TypeError):
        BaseSQLTypeAdapter()


def test_none_is_answered_by_the_base_in_both_directions():
    """A subclass never sees ``None``: write returns it untouched, and read
    routes it to ``_on_none_from_database``."""
    assert _Neutral().to_database(None, str) is None
    assert _Neutral().from_database(None, str) is None


def test_a_subclass_can_give_absence_its_own_answer():
    assert _EmptyAnswering().from_database(None, str) == ""
    # The write direction stays the base's: absence is written as absence.
    assert _EmptyAnswering().to_database(None, str) is None


def test_an_optional_annotation_is_unwrapped_before_conversion():
    """``Optional[datetime]`` converts exactly as ``datetime`` does."""
    adapter = DateTimeAdapter()
    assert adapter.from_database("2024-01-01T00:00:00", Optional[datetime.datetime]) == (
        datetime.datetime(2024, 1, 1, 0, 0)
    )


def test_a_multi_member_union_is_not_unwrapped():
    """Two real candidates are not a choice the adapter may make silently:
    the target stays the ``Union`` and the conversion refuses it."""
    stored = str(uuid.uuid4())
    with pytest.raises(TypeError):
        UUIDAdapter().from_database(stored, Union[uuid.UUID, str])


def test_register_type_accumulates_pairs():
    adapter = _Neutral()
    assert adapter.supported_types == {}

    adapter.register_type(Colour, str)
    adapter.register_type(Colour, int)

    assert adapter.supported_types == {Colour: {str, int}}


def test_require_text_and_require_bytes_are_the_shared_guards():
    assert BaseSQLTypeAdapter._require_text("ok") == "ok"
    assert BaseSQLTypeAdapter._require_bytes(b"ab") == b"ab"
    # ``bytearray`` is accepted and normalised, because drivers differ on it.
    assert BaseSQLTypeAdapter._require_bytes(bytearray(b"ab")) == b"ab"

    with pytest.raises(TypeError, match="value must be str"):
        BaseSQLTypeAdapter._require_text(1)
    with pytest.raises(TypeError, match="value must be bytes"):
        BaseSQLTypeAdapter._require_bytes("ab")


def test_a_conversion_error_names_the_target_and_the_reason():
    with pytest.raises(TypeConversionError) as caught:
        _Neutral()._conversion_error("bad", "not a colour")
    message = str(caught.value)
    assert "Colour" in message  # the adapter's neutral type
    assert "not a colour" in message

    # An explicit target wins over the neutral type.
    with pytest.raises(TypeConversionError) as caught:
        _Neutral()._conversion_error("bad", "wrong shape", target=int)
    assert "int" in str(caught.value)

    # With neither, the value's own class is named rather than left blank.
    with pytest.raises(TypeConversionError) as caught:
        _Nameless()._conversion_error("bad", "no target")
    assert "str" in str(caught.value)


# ---------------------------------------------------------------------------
# 2. DateTimeAdapter: three Python temporals onto three driver targets
# ---------------------------------------------------------------------------


def test_a_datetime_is_written_as_iso_text_a_timestamp_or_itself():
    adapter = DateTimeAdapter()
    aware = datetime.datetime(2024, 1, 1, tzinfo=datetime.timezone.utc)

    assert adapter.to_database(aware, str) == "2024-01-01T00:00:00+00:00"
    assert adapter.to_database(aware, int) == 1704067200
    assert adapter.to_database(aware, float) == 1704067200.0
    assert adapter.to_database(aware, datetime.datetime) is aware

    with pytest.raises(TypeError, match="Cannot convert datetime"):
        adapter.to_database(aware, bool)


def test_a_date_is_written_as_iso_text_an_epoch_second_or_itself():
    """A ``date`` has no clock, so ``int`` means midnight: the adapter combines
    it with ``time.min`` rather than inventing a time of day."""
    adapter = DateTimeAdapter()
    value = datetime.date(2024, 1, 1)

    assert adapter.to_database(value, str) == "2024-01-01"
    assert adapter.to_database(value, int) == int(
        datetime.datetime.combine(value, datetime.time.min).timestamp()
    )
    assert adapter.to_database(value, datetime.date) is value

    # Only ``int`` is claimed for a date; ``float`` was never registered.
    with pytest.raises(TypeError, match="Cannot convert date"):
        adapter.to_database(value, float)


def test_a_time_is_written_as_iso_text_or_itself():
    adapter = DateTimeAdapter()
    value = datetime.time(12, 0)

    assert adapter.to_database(value, str) == "12:00:00"
    assert adapter.to_database(value, datetime.time) is value

    with pytest.raises(TypeError, match="Cannot convert time"):
        adapter.to_database(value, int)


def test_a_datetime_is_read_back_from_all_three_stores():
    adapter = DateTimeAdapter()

    identity = datetime.datetime(2024, 1, 1, 12, 0)
    assert adapter.from_database(identity, datetime.datetime) is identity
    assert adapter.from_database("2024-01-01T12:00:00", datetime.datetime) == identity
    epoch = 1704110400  # 2024-01-01T12:00:00Z
    assert adapter.from_database(epoch, datetime.datetime) == datetime.datetime.fromtimestamp(epoch)

    with pytest.raises(TypeError, match="Cannot convert dict"):
        adapter.from_database({"year": 2024}, datetime.datetime)


def test_a_date_and_a_time_are_read_back_the_same_way():
    adapter = DateTimeAdapter()

    day = datetime.date(2024, 1, 1)
    assert adapter.from_database(day, datetime.date) is day
    assert adapter.from_database("2024-01-01", datetime.date) == day

    clock = datetime.time(12, 0)
    assert adapter.from_database(clock, datetime.time) is clock
    assert adapter.from_database("12:00:00", datetime.time) == clock


# ---------------------------------------------------------------------------
# 3. JSONAdapter: a document onto text, and back
# ---------------------------------------------------------------------------


def test_a_document_is_written_as_json_text():
    adapter = JSONAdapter()

    assert adapter.to_database({"a": 1}, str) == '{"a": 1}'
    assert adapter.to_database([1, 2], str) == "[1, 2]"

    with pytest.raises(TypeError, match="Cannot convert dict"):
        adapter.to_database({"a": 1}, int)


def test_a_document_is_read_back_in_the_shape_the_driver_gave():
    """A driver that already parsed the document (PostgreSQL ``jsonb``) hands
    over a dict/list; one that stored text hands over a string. Both are
    legitimate, and neither is re-parsed into a second object."""
    adapter = JSONAdapter()
    document = {"a": 1}

    assert adapter.from_database(document, dict) is document
    assert adapter.from_database([1, 2], list) == [1, 2]
    assert adapter.from_database('{"a": 1}', dict) == document

    with pytest.raises(TypeError, match="Cannot convert int"):
        adapter.from_database(7, dict)


def test_the_json_codec_hooks_are_forwarded():
    """``default`` / ``object_hook`` are the seam neutral-type codecs plug into
    (``adapters/json_codec.py``), so they have to reach ``json`` itself."""
    calls = []

    def default(value):
        calls.append(value)
        return "encoded"

    def object_hook(mapping):
        return {key: "seen" for key in mapping}

    adapter = JSONAdapter(default=default, object_hook=object_hook)

    assert adapter.to_database({"when": datetime.date(2024, 1, 1)}, str) == ('{"when": "encoded"}')
    assert calls and isinstance(calls[0], datetime.date)

    assert adapter.from_database('{"a": 1}', dict) == {"a": "seen"}


# ---------------------------------------------------------------------------
# 4. UUIDAdapter
# ---------------------------------------------------------------------------


def test_a_uuid_is_written_as_text_or_kept():
    adapter = UUIDAdapter()
    value = uuid.uuid4()

    assert adapter.to_database(value, str) == str(value)
    assert adapter.to_database(value, uuid.UUID) is value

    with pytest.raises(TypeError, match="Cannot convert UUID"):
        adapter.to_database(value, int)


def test_a_uuid_is_read_back_from_text_bytes_or_itself():
    adapter = UUIDAdapter()
    value = uuid.uuid4()

    assert adapter.from_database(value, uuid.UUID) is value
    assert adapter.from_database(str(value), uuid.UUID) == value
    # A BLOB store hands over bytes; they must go through ``UUID(bytes=...)``
    # rather than the positional hex form, which takes a string.
    assert adapter.from_database(value.bytes, uuid.UUID) == value

    with pytest.raises(TypeError, match="Cannot convert str to UUID"):
        adapter.from_database("not-a-uuid", uuid.UUID)
    with pytest.raises(TypeError, match="Cannot convert bytes to UUID"):
        adapter.from_database(b"short", uuid.UUID)
    with pytest.raises(TypeError, match="Cannot convert int"):
        adapter.from_database(7, uuid.UUID)


# ---------------------------------------------------------------------------
# 5. EnumAdapter
# ---------------------------------------------------------------------------


def test_the_enum_adapter_registers_the_two_framework_pairs():
    """``CORE_DEFAULT_TYPE_MAPPINGS`` declares ``(Enum, str)``, so the generic
    adapter claims it (and the ``int`` spelling beside it). A backend whose
    server spells enums differently registers its own adapter over these pairs
    -- PostgreSQL, MySQL, MariaDB, Oracle and ClickHouse all do -- so the
    generic claim costs them nothing.
    """
    adapter = EnumAdapter()

    assert adapter.supported_types == {Enum: {str, int}}


def test_the_stored_label_is_the_member_value_not_its_name():
    adapter = EnumAdapter()

    assert adapter.to_database(Colour.RED, str) == "red"
    assert adapter.to_database(Colour.ONE, str) == "1"
    assert adapter.to_database(Colour.ONE, int) == 1

    with pytest.raises(TypeError, match="Cannot convert Colour"):
        adapter.to_database(Colour.RED, float)


def test_a_member_is_read_back_from_value_numeric_text_or_legacy_name():
    """Three stores have to keep working: the value (the rule since the
    ``.value`` decision), the numeric text a ``TEXT`` column may hold, and the
    member *name* written before that rule."""
    adapter = EnumAdapter()

    assert adapter.from_database("red", Colour) is Colour.RED
    assert adapter.from_database("1", Colour) is Colour.ONE
    assert adapter.from_database("RED", Colour) is Colour.RED
    assert adapter.from_database(1, Colour) is Colour.ONE

    # A bool is an int subclass; reading it as a member would be a guess.
    with pytest.raises(TypeError):
        adapter.from_database(True, Colour)
    with pytest.raises(TypeError, match="Cannot convert float"):
        adapter.from_database(1.5, Colour)


# ---------------------------------------------------------------------------
# 6. BooleanAdapter
# ---------------------------------------------------------------------------


def test_a_truth_value_is_written_as_one_text_or_itself():
    adapter = BooleanAdapter()

    assert adapter.to_database(True, int) == 1
    assert adapter.to_database(False, int) == 0
    assert adapter.to_database(True, str) == "true"
    assert adapter.to_database(False, str) == "false"
    assert adapter.to_database(True, bool) is True

    with pytest.raises(TypeError, match="Cannot convert bool"):
        adapter.to_database(True, float)


def test_a_truth_value_is_read_back_from_an_integer_or_text():
    adapter = BooleanAdapter()

    assert adapter.from_database(1, bool) is True
    assert adapter.from_database(0, bool) is False
    assert adapter.from_database("TRUE", bool) is True
    assert adapter.from_database("false", bool) is False
    # The other spelling a store may hold is not a truth value: only the word
    # ``true`` (any case) is true, so everything else reads as false.
    assert adapter.from_database("yes", bool) is False

    with pytest.raises(TypeError, match="Cannot convert float"):
        adapter.from_database(1.0, bool)


# ---------------------------------------------------------------------------
# 7. DecimalAdapter
# ---------------------------------------------------------------------------


def test_a_decimal_is_written_as_text_a_float_or_kept():
    adapter = DecimalAdapter()
    value = Decimal("1.50")

    assert adapter.to_database(value, str) == "1.50"
    assert adapter.to_database(value, float) == 1.5
    assert adapter.to_database(value, Decimal) is value

    with pytest.raises(TypeError, match="Cannot convert Decimal"):
        adapter.to_database(value, int)


def test_a_decimal_is_read_back_without_a_float_in_the_path():
    """``Decimal(str(value))`` for every driver shape: a float in the path would
    reintroduce the precision loss the adapter exists to prevent."""
    adapter = DecimalAdapter()

    assert adapter.from_database(Decimal("1.50"), Decimal) == Decimal("1.50")
    assert adapter.from_database("1.50", Decimal) == Decimal("1.50")
    assert adapter.from_database(1.5, Decimal) == Decimal("1.5")
    assert adapter.from_database(2, Decimal) == Decimal("2")

    with pytest.raises(TypeError, match="Cannot convert list"):
        adapter.from_database([1], Decimal)


def test_a_declared_precision_quantises_on_the_way_in():
    """``precision`` is a column declaration, and it is applied by the adapter
    rather than left to the driver's rounding."""
    adapter = DecimalAdapter()
    options = {"precision": "0.01"}

    assert adapter.from_database("1.005", Decimal, options) == Decimal("1.01")
    assert adapter.from_database(Decimal("1.004"), Decimal, options) == Decimal("1.00")
    # With no precision declared, the value is carried exactly.
    assert adapter.from_database("1.005", Decimal) == Decimal("1.005")


# ---------------------------------------------------------------------------
# 8. ArrayAdapter
# ---------------------------------------------------------------------------


def test_the_array_adapter_claims_no_type_pairs_of_its_own():
    """Explicitly so: registering ``(list, str)`` here would collide with
    ``JSONAdapter``, which claims the same pair. The adapter is for callers
    that want array semantics and register it themselves."""
    assert ArrayAdapter().supported_types == {}


def test_an_array_is_written_as_json_text():
    adapter = ArrayAdapter()

    assert adapter.to_database([1, 2], str) == "[1, 2]"
    assert adapter.to_database((1, 2), str) == "[1, 2]"
    assert adapter.to_database({1}, str) == "[1]"

    with pytest.raises(TypeError, match="JSON array string"):
        adapter.to_database({"a": 1}, str)
    with pytest.raises(TypeError, match="Cannot convert list"):
        adapter.to_database([1, 2], int)


def test_an_array_is_read_back_as_a_list():
    adapter = ArrayAdapter()

    assert adapter.from_database("[1, 2]", list) == [1, 2]

    with pytest.raises(TypeError, match="Cannot convert str"):
        adapter.from_database("[1, 2]", dict)
