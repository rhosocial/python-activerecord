# tests/rhosocial/activerecord_test/feature/backend/sqlite/native/test_native_affinity.py
"""SQLite column affinity as the backend-specific part of the type behaviour.

SQLite has no native column types, so there is no ``BIT``/``JSON``/``GEOMETRY``
to test here.  What is SQLite-specific is *affinity*: a declared type selects
one of five rules that may rewrite the value on the way in
(https://www.sqlite.org/datatype3.html#determination_of_column_affinity).

Every test writes the same Python values through the same adapters into the
five affinity tables and then checks:

* the stored form (``typeof()`` and the value), i.e. what affinity actually did;
* S1 -- the value read back (where the rewrite leaves the value representable);
* S2 -- rewriting the read value stores the identical form again;
* S3 -- text written by native SQL (not through an adapter) reads back.

The value set is deliberately the one that separates the affinities: geometry
WKT and JSON text are not numeric, a bit string of digits *is*, and a Decimal is
bound as ``float`` by the core suggestion table.
"""

import json
from decimal import Decimal

import pytest

from rhosocial.activerecord.backend.adapters.bitstring import BitString
from rhosocial.activerecord.backend.adapters.geometry import Point
from rhosocial.activerecord.backend.errors import TypeConversionError

AFFINITIES = ("text", "integer", "real", "numeric", "blob")

SHAPE = Point(1.5, 2.5)
SHAPE_TEXT = "POINT (1.5 2.5)"
FLAGS = BitString.from_bits("00101")
PAYLOAD = {"a": 1, "b": [1, None, "x"]}
PAYLOAD_TEXT = '{"a": 1, "b": [1, null, "x"]}'
AMOUNT = Decimal("12.50")
RAW_BYTES = b"\x00\x01\xff"

#: (typeof, value) the server keeps per affinity.  Measured, not derived.
EXPECTED_STORED = {
    "text": {
        "shape": ("text", SHAPE_TEXT),
        "flags": ("text", "00101"),
        "amount": ("text", "12.5"),
        "payload": ("text", PAYLOAD_TEXT),
        "raw_bytes": ("blob", RAW_BYTES),
        "counter": ("text", "42"),
        "ratio": ("text", "2.5"),
    },
    "integer": {
        "shape": ("text", SHAPE_TEXT),
        "flags": ("integer", 101),
        "amount": ("real", 12.5),
        "payload": ("text", PAYLOAD_TEXT),
        "raw_bytes": ("blob", RAW_BYTES),
        "counter": ("integer", 42),
        "ratio": ("real", 2.5),
    },
    "real": {
        "shape": ("text", SHAPE_TEXT),
        "flags": ("real", 101.0),
        "amount": ("real", 12.5),
        "payload": ("text", PAYLOAD_TEXT),
        "raw_bytes": ("blob", RAW_BYTES),
        "counter": ("real", 42.0),
        "ratio": ("real", 2.5),
    },
    "numeric": {
        "shape": ("text", SHAPE_TEXT),
        "flags": ("integer", 101),
        "amount": ("real", 12.5),
        "payload": ("text", PAYLOAD_TEXT),
        "raw_bytes": ("blob", RAW_BYTES),
        "counter": ("integer", 42),
        "ratio": ("real", 2.5),
    },
    "blob": {
        "shape": ("text", SHAPE_TEXT),
        "flags": ("text", "00101"),
        "amount": ("real", 12.5),
        "payload": ("text", PAYLOAD_TEXT),
        "raw_bytes": ("blob", RAW_BYTES),
        "counter": ("integer", 42),
        "ratio": ("real", 2.5),
    },
}


def _values() -> dict:
    return dict(
        shape=SHAPE,
        flags=FLAGS,
        amount=AMOUNT,
        payload=PAYLOAD,
        raw_bytes=RAW_BYTES,
        counter=42,
        ratio=2.5,
    )


def _stored(model, column: str, row_id: int):
    """Read the stored ``(typeof, value)`` pair without any adapter."""
    row = model.backend().fetch_one(
        f"SELECT typeof({column}) AS t, {column} AS v "
        f"FROM {model.table_name()} WHERE id = ?",
        (row_id,),
    )
    return row["t"], row["v"]


def _native_insert(model, row_id: int, **columns) -> None:
    """Insert a row through native SQL, bypassing the adapters."""
    names = ", ".join(["id"] + list(columns))
    placeholders = ", ".join("?" for _ in range(len(columns) + 1))
    model.backend().execute(
        f"INSERT INTO {model.table_name()} ({names}) VALUES ({placeholders})",
        (row_id,) + tuple(columns.values()),
    )


def _mark_for_write(instance, *fields: str) -> None:
    """Mark fields as modified without changing their value.

    ``save()`` only writes tracked (dirty) fields, and change tracking compares
    values, so assigning an equal value does not schedule an update.  Setting a
    field to ``None`` and back marks it dirty while leaving the value intact --
    which is what S2 needs: the *same* value must be written back.
    """
    for field in fields:
        original = getattr(instance, field)
        setattr(instance, field, None)
        setattr(instance, field, original)
    assert instance.is_dirty, "the row must actually be rewritten"


@pytest.mark.parametrize("affinity", AFFINITIES)
def test_stored_form_matches_the_declared_affinity(affinity_models, affinity):
    """What affinity does to the bound value, with no adapter involved on read."""
    model = affinity_models[affinity]
    instance = model(**_values())
    instance.save()

    for column, (sqlite_type, value) in EXPECTED_STORED[affinity].items():
        stored = _stored(model, column, instance.id)
        assert stored[0] == sqlite_type, f"{affinity}/{column} affinity changed"
        assert stored[1] == value, f"{affinity}/{column} stored value"


@pytest.mark.parametrize("affinity", AFFINITIES)
def test_round_trip_under_affinity(affinity_models, affinity):
    """S1: the value survives the affinity, except where affinity rewrites it."""
    model = affinity_models[affinity]
    instance = model(**_values())
    instance.save()

    if EXPECTED_STORED[affinity]["flags"][0] != "text":
        # Affinity turned the bit *text* into a number (00101 -> 101); the
        # numeric value is no longer a bit string and the adapter says so
        # instead of inventing digits back.
        with pytest.raises(TypeConversionError, match="value must be str"):
            model.find_one(instance.id)
        return

    found = model.find_one(instance.id)
    assert found.shape == SHAPE
    assert found.flags == FLAGS
    assert found.amount == AMOUNT
    assert found.payload == PAYLOAD
    assert found.raw_bytes == RAW_BYTES
    assert found.counter == 42
    assert found.ratio == 2.5


@pytest.mark.parametrize("affinity", ("text", "blob"))
def test_bit_string_carriers_keep_the_bit_length(affinity_models, affinity):
    """TEXT and BLOB affinity keep the text, so the leading zeros survive."""
    model = affinity_models[affinity]
    instance = model(flags=FLAGS)
    instance.save()

    found = model.find_one(instance.id)
    assert found.flags == FLAGS
    assert found.flags.bit_length == 5, "the leading zero must survive the carrier"


@pytest.mark.parametrize("affinity", AFFINITIES)
def test_blob_bytes_are_stored_byte_for_byte(affinity_models, affinity):
    """No affinity converts a BLOB value, so bytes are never mangled."""
    model = affinity_models[affinity]
    instance = model(raw_bytes=RAW_BYTES)
    instance.save()

    assert _stored(model, "raw_bytes", instance.id) == ("blob", RAW_BYTES)
    assert model.find_one(instance.id).raw_bytes == RAW_BYTES


def test_numeric_affinity_decimal_is_quantised_by_the_column(affinity_models):
    """NUMERIC affinity keeps the numeric value, not the Decimal's scale.

    ``Decimal("12.50")`` is bound as a ``float`` by the core suggestion table,
    so NUMERIC affinity stores ``12.5`` (REAL); the adapter restores a Decimal
    numerically equal to the input.  An integral Decimal becomes an INTEGER.
    """
    model = affinity_models["numeric"]
    instance = model(amount=Decimal("12.50"), counter=42, ratio=2.5)
    instance.save()

    assert _stored(model, "amount", instance.id) == ("real", 12.5)
    found = model.find_one(instance.id)
    assert found.amount == Decimal("12.50")
    assert isinstance(found.amount, Decimal)

    integral = model(amount=Decimal("42.00"))
    integral.save()
    assert _stored(model, "amount", integral.id) == ("integer", 42)
    assert model.find_one(integral.id).amount == Decimal("42.00")


@pytest.mark.parametrize("affinity", ("text", "blob"))
def test_text_carriers_are_not_rewritten(affinity_models, affinity):
    """TEXT-affinity (and BLOB-affinity) columns keep geometry/JSON/bit text."""
    model = affinity_models[affinity]
    instance = model(shape=SHAPE, payload=PAYLOAD, flags=FLAGS)
    instance.save()

    assert _stored(model, "shape", instance.id)[1] == SHAPE_TEXT
    assert _stored(model, "payload", instance.id)[1] == PAYLOAD_TEXT
    assert _stored(model, "flags", instance.id)[1] == "00101"

    found = model.find_one(instance.id)
    assert found.shape == SHAPE
    assert found.payload == PAYLOAD
    assert found.flags == FLAGS


def test_rewriting_the_text_affinity_row_is_stable(affinity_models):
    """S2: writing the value read back stores exactly the same text."""
    model = affinity_models["text"]
    instance = model(**_values())
    instance.save()

    before = {
        column: _stored(model, column, instance.id)
        for column in ("shape", "flags", "amount", "payload", "raw_bytes")
    }

    found = model.find_one(instance.id)
    _mark_for_write(found, "shape", "flags", "amount", "payload", "raw_bytes")
    found.save()

    for column, stored in before.items():
        assert _stored(model, column, instance.id) == stored, (
            f"{column} must not be re-encoded on rewrite"
        )


def test_foreign_text_is_read_and_canonicalised(affinity_models):
    """S3: text written by native SQL (no adapter) is decoded and canonicalised."""
    model = affinity_models["text"]
    row_id = 9001
    _native_insert(
        model,
        row_id,
        shape="POINT(3 4)",
        flags="1011",
        amount=7.25,
        payload='{"k": "v"}',
        raw_bytes=b"\x00\xff",
    )

    found = model.find_one(row_id)
    assert found.shape == Point(3, 4)
    assert found.flags == BitString.from_bits("1011")
    assert found.amount == Decimal("7.25")
    assert found.payload == {"k": "v"}
    assert found.raw_bytes == b"\x00\xff"

    # Rewriting produces the canonical form of each value, not the foreign text.
    _mark_for_write(found, "shape", "flags", "amount", "payload", "raw_bytes")
    found.save()
    assert _stored(model, "shape", row_id)[1] == Point(3, 4).to_wkt()
    assert _stored(model, "flags", row_id)[1] == "1011"
    assert _stored(model, "amount", row_id)[1] == "7.25"
    assert json.loads(_stored(model, "payload", row_id)[1]) == {"k": "v"}
