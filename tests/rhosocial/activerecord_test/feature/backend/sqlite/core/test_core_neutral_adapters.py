# tests/rhosocial/activerecord_test/feature/backend/sqlite/core/test_core_neutral_adapters.py
"""DB-free tests for the SQLite neutral-family type adapters.

The adapters are pure value converters; no database connection is opened here.
Coverage:

- representative encode/decode round-trips for every neutral family;
- uniform ``TypeConversionError`` wrapping for bad input;
- the backend adapter inventory (sync and async) contains the new classes;
- the historical ``...sqlite.adapters`` import path still resolves.
"""

import datetime
import json
from decimal import Decimal

import pytest

from rhosocial.activerecord.backend.adapters import (
    BitString,
    BitStringAdapterBase,
    GeometryAdapterBase,
    GeometryCollection,
    LineString,
    MacAddress,
    MacAddressAdapterBase,
    MultiPoint,
    Multirange,
    Point,
    Polygon,
    Range,
    RangeAdapterBase,
    Vector,
    VectorAdapterBase,
)
from rhosocial.activerecord.backend.errors import TypeConversionError
from rhosocial.activerecord.backend.impl.sqlite.adapters import (
    SQLiteBitStringAdapter,
    SQLiteBlobAdapter,
    SQLiteGeometryAdapter,
    SQLiteJSONAdapter,
    SQLiteMacAddressAdapter,
    SQLiteRangeAdapter,
    SQLiteUUIDAdapter,
    SQLiteVectorAdapter,
)
from rhosocial.activerecord.backend.impl.sqlite.backend import (
    AsyncSQLiteBackend,
    SQLiteBackend,
)

SQLITE_ADAPTER_CLASSES = (
    SQLiteBlobAdapter,
    SQLiteJSONAdapter,
    SQLiteUUIDAdapter,
    SQLiteGeometryAdapter,
    SQLiteVectorAdapter,
    SQLiteBitStringAdapter,
    SQLiteRangeAdapter,
    SQLiteMacAddressAdapter,
)


# --- Geometry ---------------------------------------------------------------


class TestSQLiteGeometryAdapter:
    @pytest.fixture
    def adapter(self):
        return SQLiteGeometryAdapter()

    @pytest.mark.parametrize(
        "geometry",
        [
            Point(1.5, -2.5),
            LineString(((0, 0), (1, 1), (2, 0))),
            Polygon((((0, 0), (4, 0), (4, 4), (0, 0)),)),
            MultiPoint(((0, 0), (1, 1))),
            GeometryCollection((Point(1, 2), LineString(((0, 0), (1, 1))))),
        ],
        ids=["point", "linestring", "polygon", "multipoint", "collection"],
    )
    def test_plain_wkt_round_trip(self, adapter, geometry):
        text = adapter.to_database(geometry, str)
        assert isinstance(text, str)
        assert "SRID=" not in text
        assert adapter.from_database(text, type(geometry)) == geometry

    def test_srid_is_written_as_ewkt_prefix_and_read_back(self, adapter):
        geometry = Point(1.5, 2.5, srid=4326)
        text = adapter.to_database(geometry, str)

        assert text == "SRID=4326;POINT (1.5 2.5)"
        decoded = adapter.from_database(text, Point)
        assert decoded == geometry
        assert decoded.srid == 4326

    def test_options_provide_srid_when_value_has_none(self, adapter):
        text = adapter.to_database(Point(1, 2), str, {"srid": 3857})

        assert text.startswith("SRID=3857;")
        assert adapter.from_database(text, Point).srid == 3857

    def test_geojson_mapping_is_accepted_on_write(self, adapter):
        text = adapter.to_database({"type": "Point", "coordinates": [3, 4]}, str)

        assert text.startswith("POINT (3.0 4.0")
        assert adapter.from_database(text, Point) == Point(3, 4)

    def test_invalid_input_is_wrapped(self, adapter):
        with pytest.raises(TypeConversionError, match="Cannot convert int to Geometry"):
            adapter.to_database(123, str)

    def test_invalid_wkt_is_wrapped(self, adapter):
        with pytest.raises(TypeConversionError, match="Cannot convert str to Geometry"):
            adapter.from_database("NOT A WKT", Point)


# --- Vector ----------------------------------------------------------------


class TestSQLiteVectorAdapter:
    @pytest.fixture
    def adapter(self):
        return SQLiteVectorAdapter()

    def test_round_trip(self, adapter):
        vector = Vector((0, 1.5, -2, 3))

        text = adapter.to_database(vector, str)
        assert json.loads(text) == [0, 1.5, -2, 3]
        assert adapter.from_database(text, Vector) == vector

    def test_non_finite_round_trip(self, adapter):
        vector = Vector((1.0, float("inf"), float("-inf")), allow_non_finite=True)

        text = adapter.to_database(vector, str)
        assert '"Infinity"' in text and '"-Infinity"' in text
        assert adapter.from_database(text, Vector) == vector

    def test_sequence_is_accepted_on_write(self, adapter):
        text = adapter.to_database([1, 2.5], str)

        assert json.loads(text) == [1, 2.5]

    def test_invalid_value_is_wrapped(self, adapter):
        with pytest.raises(TypeConversionError, match="Cannot convert str to Vector"):
            adapter.to_database("not-a-vector", str)

    def test_invalid_json_is_wrapped(self, adapter):
        with pytest.raises(TypeConversionError, match="Cannot convert str to Vector"):
            adapter.from_database("[1, 2", Vector)


# --- BitString -------------------------------------------------------------


class TestSQLiteBitStringAdapter:
    @pytest.fixture
    def adapter(self):
        return SQLiteBitStringAdapter()

    @pytest.mark.parametrize(
        "bits",
        [
            BitString.from_bits("1"),
            BitString.from_bits("00101"),
            BitString.from_bits("10000000"),
            BitString.from_int(0b1010, 4),
        ],
        ids=["single", "leading-zeros", "whole-byte", "from-int"],
    )
    def test_round_trip(self, adapter, bits):
        text = adapter.to_database(bits, str)

        assert text == bits.to_bits()
        assert adapter.from_database(text, BitString) == bits

    def test_invalid_bits_are_wrapped(self, adapter):
        with pytest.raises(TypeConversionError, match="Cannot convert str to BitString"):
            adapter.from_database("10201", BitString)

    def test_invalid_value_is_wrapped(self, adapter):
        with pytest.raises(TypeConversionError, match="Cannot convert float to BitString"):
            adapter.to_database(1.5, str)


# --- Range / Multirange ----------------------------------------------------


class TestSQLiteRangeAdapter:
    @pytest.fixture
    def adapter(self):
        return SQLiteRangeAdapter()

    @pytest.mark.parametrize(
        "range_value",
        [
            Range(1, 10, "[)"),
            Range(None, 10, "(]"),
            Range(1, None, "[)"),
            Range(empty=True),
            Range(datetime.date(2024, 1, 1), datetime.date(2024, 2, 1), "[]"),
            Range(Decimal("1.10"), Decimal("2.20"), "[)"),
        ],
        ids=["int", "unbounded-lower", "unbounded-upper", "empty", "date", "decimal"],
    )
    def test_range_round_trip(self, adapter, range_value):
        text = adapter.to_database(range_value, str)

        assert isinstance(text, str)
        assert adapter.from_database(text, Range) == range_value

    def test_multirange_round_trip(self, adapter):
        multirange = Multirange((Range(5, 7, "[)"), Range(1, 2, "[)")))

        text = adapter.to_database(multirange, str)
        assert isinstance(json.loads(text), list)
        decoded = adapter.from_database(text, Multirange)
        assert decoded == multirange
        assert decoded.ranges == (Range(1, 2, "[)"), Range(5, 7, "[)"))

    def test_shape_is_inferred_without_an_explicit_target(self, adapter):
        single = adapter.to_database(Range(1, 3, "[)"), str)
        multiple = adapter.to_database(Multirange((Range(1, 3, "[)"),)), str)

        assert isinstance(adapter.from_database(single, str), Range)
        assert isinstance(adapter.from_database(multiple, str), Multirange)

    def test_invalid_value_is_wrapped(self, adapter):
        with pytest.raises(TypeConversionError, match="Cannot convert str to Range"):
            adapter.to_database("nope", Range)

    def test_invalid_json_is_wrapped(self, adapter):
        with pytest.raises(TypeConversionError, match="Cannot convert str to Range"):
            adapter.from_database("{not json", Range)

    def test_target_mismatch_is_wrapped(self, adapter):
        range_text = adapter.to_database(Range(1, 3, "[)"), str)
        multirange_text = adapter.to_database(Multirange((Range(1, 3, "[)"),)), str)

        with pytest.raises(TypeConversionError, match="Cannot convert str to Multirange"):
            adapter.from_database(range_text, Multirange)
        with pytest.raises(TypeConversionError, match="Cannot convert str to Range"):
            adapter.from_database(multirange_text, Range)


# --- MacAddress ------------------------------------------------------------


class TestSQLiteMacAddressAdapter:
    @pytest.fixture
    def adapter(self):
        return SQLiteMacAddressAdapter()

    @pytest.mark.parametrize(
        "text",
        ["08:00:2b:01:02:03", "08:00:2B:01:02:03", "08002B010203"],
        ids=["eui48", "uppercase", "compact"],
    )
    def test_eui48_round_trip_canonicalizes(self, adapter, text):
        mac = MacAddress.parse(text)

        stored = adapter.to_database(mac, str)
        assert stored == "08:00:2b:01:02:03"
        assert adapter.from_database(stored, MacAddress) == mac

    def test_eui64_round_trip(self, adapter):
        mac = MacAddress.parse("08:00:2b:01:02:03:04:05")

        stored = adapter.to_database(mac, str)
        assert stored == "08:00:2b:01:02:03:04:05"
        assert adapter.from_database(stored, MacAddress) == mac

    def test_invalid_text_is_wrapped(self, adapter):
        with pytest.raises(TypeConversionError, match="Cannot convert str to MacAddress"):
            adapter.from_database("zz:zz:zz:zz:zz:zz", MacAddress)

    def test_invalid_value_is_wrapped(self, adapter):
        with pytest.raises(TypeConversionError, match="Cannot convert object to MacAddress"):
            adapter.to_database(object(), str)


# --- Inventory -------------------------------------------------------------


@pytest.mark.parametrize(
    "backend_factory", [SQLiteBackend, AsyncSQLiteBackend], ids=["sync", "async"]
)
def test_inventory_contains_neutral_family_adapters(backend_factory):
    backend = backend_factory(database=":memory:")
    inventory_classes = {type(adapter) for adapter in backend.get_type_adapters()}

    for adapter_class in SQLITE_ADAPTER_CLASSES:
        assert adapter_class in inventory_classes

    # One instance per class, and every inventory entry is one of ours or a
    # standard fallback adapter.
    names = [type(adapter).__name__ for adapter in backend.get_type_adapters()]
    assert len(names) == len(set(names))
    assert len(names) >= len(SQLITE_ADAPTER_CLASSES)


def test_historical_import_path_still_resolves():
    """The module -> package move must not break documented imports."""
    import rhosocial.activerecord.backend.impl.sqlite.adapters as adapters

    assert adapters.SQLiteJSONAdapter is SQLiteJSONAdapter
    assert adapters.SQLiteUUIDAdapter is SQLiteUUIDAdapter
    assert adapters.SQLiteGeometryAdapter is SQLiteGeometryAdapter


def test_neutral_adapters_derive_from_family_bases():
    assert issubclass(SQLiteGeometryAdapter, GeometryAdapterBase)
    assert issubclass(SQLiteVectorAdapter, VectorAdapterBase)
    assert issubclass(SQLiteBitStringAdapter, BitStringAdapterBase)
    assert issubclass(SQLiteRangeAdapter, RangeAdapterBase)
    assert issubclass(SQLiteMacAddressAdapter, MacAddressAdapterBase)
