# tests/rhosocial/activerecord_test/feature/backend/adapters/test_geometry.py
"""DB-free tests for the neutral 2D geometry types and GeometryAdapterBase."""

import json
from dataclasses import FrozenInstanceError

import pytest

from rhosocial.activerecord.backend.adapters.geometry import (
    Geometry,
    GeometryAdapterBase,
    GeometryCollection,
    LineString,
    MultiLineString,
    MultiPoint,
    MultiPolygon,
    Point,
    Polygon,
)
from rhosocial.activerecord.backend.adapters.json_codec import AdapterJSONCodec
from rhosocial.activerecord.backend.errors import TypeConversionError

OUTER_RING = [
    (0.0, 0.0),
    (4.0, 0.0),
    (4.0, 4.0),
    (0.0, 4.0),
    (0.0, 0.0),
]
SECOND_RING = [
    (2.0, 2.0),
    (3.0, 2.0),
    (3.0, 3.0),
    (2.0, 2.0),
]

SAMPLE_POINT = Point(1.0, -2.0)
SAMPLE_LINESTRING = LineString([(0.0, 0.0), (1.0, 1.0), (2.0, 0.0)])
SAMPLE_POLYGON = Polygon([OUTER_RING])
SAMPLE_MULTIPOINT = MultiPoint([(0.0, 0.0), (1.0, 1.0)])
SAMPLE_MULTILINESTRING = MultiLineString([[(0.0, 0.0), (1.0, 1.0)], [(2.0, 2.0), (3.0, 3.0)]])
SAMPLE_MULTIPOLYGON = MultiPolygon(
    [[OUTER_RING], [[(2.0, 2.0), (3.0, 2.0), (3.0, 3.0), (2.0, 2.0)]]]
)
SAMPLE_COLLECTION = GeometryCollection([Point(1.0, 2.0), LineString([(0.0, 0.0), (1.0, 1.0)])])

SAMPLE_GEOMETRIES = [
    SAMPLE_POINT,
    SAMPLE_LINESTRING,
    SAMPLE_POLYGON,
    SAMPLE_MULTIPOINT,
    SAMPLE_MULTILINESTRING,
    SAMPLE_MULTIPOLYGON,
    SAMPLE_COLLECTION,
]

WKT_CASES = [
    ("POINT (1.0 -2.0)", SAMPLE_POINT),
    ("LINESTRING (0.0 0.0, 1.0 1.0, 2.0 0.0)", SAMPLE_LINESTRING),
    (
        "POLYGON ((0.0 0.0, 4.0 0.0, 4.0 4.0, 0.0 4.0, 0.0 0.0))",
        SAMPLE_POLYGON,
    ),
    ("MULTIPOINT (0.0 0.0, 1.0 1.0)", SAMPLE_MULTIPOINT),
    (
        "MULTILINESTRING ((0.0 0.0, 1.0 1.0), (2.0 2.0, 3.0 3.0))",
        SAMPLE_MULTILINESTRING,
    ),
    (
        "MULTIPOLYGON ("
        "((0.0 0.0, 4.0 0.0, 4.0 4.0, 0.0 4.0, 0.0 0.0)), "
        "((2.0 2.0, 3.0 2.0, 3.0 3.0, 2.0 2.0)))",
        SAMPLE_MULTIPOLYGON,
    ),
    (
        "GEOMETRYCOLLECTION (POINT (1.0 2.0), LINESTRING (0.0 0.0, 1.0 1.0))",
        SAMPLE_COLLECTION,
    ),
]

UNSUPPORTED_WKT = [
    "POINT Z (1 2 3)",
    "POINT M (1 2 3)",
    "POINT ZM (1 2 3 4)",
    "POINT (1 2 3)",
    "LINESTRING Z (0 0 0, 1 1 1)",
    "CIRCULARSTRING (0 0, 1 1, 2 0)",
    "COMPOUNDCURVE ((0 0, 1 1), (2 2, 3 3))",
    "CURVEPOLYGON (CIRCULARSTRING (0 0, 1 1, 2 0))",
    "TIN (((0 0, 1 0, 0 1, 0 0)))",
    "POLYHEDRALSURFACE (((0 0, 1 0, 0 1, 0 0)))",
    "TRIANGLE ((0 0, 1 0, 0 1, 0 0))",
    "POINT EMPTY",
    "GEOMETRYCOLLECTION EMPTY",
]

MALFORMED_WKT = [
    "",
    "POINT",
    "POINT (1)",
    "POINT (1 2",
    "NOPE (1 2)",
    "POINT (1 2) EXTRA",
    "SRID=abc;POINT (1 2)",
    "SRID=-1;POINT (1 2)",
    "POINT (1 2))",
]


# --- construction validation ----------------------------------------------


def test_point_accepts_int_and_float_coordinates():
    assert Point(1, 2) == Point(1.0, 2.0)
    assert isinstance(Point(1, 2).x, float)


def test_point_rejects_non_numeric_coordinates():
    with pytest.raises(TypeError):
        Point("1", 2)
    with pytest.raises(TypeError):
        Point((1, 2), 3)


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf")])
def test_point_rejects_non_finite_coordinates(bad):
    with pytest.raises(ValueError):
        Point(bad, 0.0)
    with pytest.raises(ValueError):
        Point(0.0, bad)


def test_coordinates_must_be_2d():
    with pytest.raises(ValueError):
        LineString([(0, 0, 0), (1, 1, 1)])
    with pytest.raises(ValueError):
        Polygon([[(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 0, 0)]])


def test_linestring_requires_two_points():
    with pytest.raises(ValueError):
        LineString([(0.0, 0.0)])
    assert LineString([(0.0, 0.0), (0.0, 0.0)]) == LineString(((0.0, 0.0), (0.0, 0.0)))


def test_polygon_rings_must_be_closed():
    with pytest.raises(ValueError):
        Polygon([[(0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)]])
    with pytest.raises(ValueError):
        Polygon([])


def test_polygon_ring_requires_four_points():
    with pytest.raises(ValueError):
        Polygon([[(0.0, 0.0), (1.0, 1.0), (0.0, 0.0)]])


@pytest.mark.parametrize(
    "factory",
    [MultiPoint, MultiLineString, MultiPolygon, GeometryCollection],
    ids=["multipoint", "multilinestring", "multipolygon", "collection"],
)
def test_multi_types_reject_empty_input(factory):
    with pytest.raises(ValueError):
        factory([])


def test_geometry_collection_rejects_bare_base_geometry():
    with pytest.raises(TypeError):
        GeometryCollection([Geometry()])


def test_srid_validation():
    assert Point(1.0, 2.0, srid=0).srid == 0
    with pytest.raises(ValueError):
        Point(1.0, 2.0, srid=-1)
    with pytest.raises(TypeError):
        Point(1.0, 2.0, srid="4326")
    with pytest.raises(TypeError):
        Point(1.0, 2.0, srid=True)


def test_geometry_is_immutable():
    point = Point(1.0, 2.0)
    with pytest.raises(FrozenInstanceError):
        point.x = 3.0  # type: ignore[misc]


# --- WKT ------------------------------------------------------------------


@pytest.mark.parametrize(
    "text, expected", WKT_CASES, ids=[case[1]._json_type for case in WKT_CASES]
)
def test_wkt_round_trip(text, expected):
    parsed = Geometry.from_wkt(text)
    assert parsed == expected
    assert parsed.to_wkt() == text
    assert Geometry.from_wkt(parsed.to_wkt()) == expected


def test_multipoint_accepts_parenthesized_coordinates():
    assert Geometry.from_wkt("MULTIPOINT ((0 0), (1 1))") == MultiPoint([(0.0, 0.0), (1.0, 1.0)])


def test_wkt_accepts_srid_prefix():
    parsed = Geometry.from_wkt("SRID=4326;POINT (1.0 2.0)")
    assert parsed == Point(1.0, 2.0, srid=4326)
    assert parsed.srid == 4326


def test_srid_prefix_wins_over_argument():
    parsed = Geometry.from_wkt("SRID=3857;POINT (1.0 2.0)", srid=4326)
    assert parsed.srid == 3857


def test_from_wkt_srid_argument_without_prefix():
    parsed = Geometry.from_wkt("LINESTRING (0.0 0.0, 1.0 1.0)", srid=4326)
    assert parsed.srid == 4326


def test_wkt_is_plain_not_ewkt():
    assert Point(1.0, 2.0, srid=4326).to_wkt() == "POINT (1.0 2.0)"


def test_subclass_from_wkt_enforces_shape():
    assert Point.from_wkt("POINT (1.0 2.0)") == Point(1.0, 2.0)
    with pytest.raises(ValueError):
        Point.from_wkt("LINESTRING (0.0 0.0, 1.0 1.0)")


@pytest.mark.parametrize("text", UNSUPPORTED_WKT)
def test_unsupported_wkt_raises_value_error(text):
    with pytest.raises(ValueError):
        Geometry.from_wkt(text)


@pytest.mark.parametrize("text", MALFORMED_WKT)
def test_malformed_wkt_raises_value_error(text):
    with pytest.raises(ValueError):
        Geometry.from_wkt(text)


def test_from_wkt_requires_text():
    with pytest.raises(TypeError):
        Geometry.from_wkt(123)  # type: ignore[arg-type]


# --- GeoJSON --------------------------------------------------------------


@pytest.mark.parametrize(
    "geometry", SAMPLE_GEOMETRIES, ids=[g._json_type for g in SAMPLE_GEOMETRIES]
)
def test_geojson_round_trip(geometry):
    value = geometry.to_json_value()
    assert json.loads(json.dumps(value)) == value
    assert Geometry.from_json_value(value) == geometry


def test_geojson_round_trip_preserves_srid():
    geometry = Point(1.0, 2.0, srid=4326)
    value = geometry.to_json_value()
    assert value == {"type": "Point", "coordinates": [1.0, 2.0], "srid": 4326}
    assert Geometry.from_json_value(value) == geometry


def test_geometry_collection_geojson_uses_geometries():
    value = SAMPLE_COLLECTION.to_json_value()
    assert value["type"] == "GeometryCollection"
    assert "coordinates" not in value
    assert [child["type"] for child in value["geometries"]] == ["Point", "LineString"]


def test_geojson_from_json_value_dispatch_is_case_insensitive():
    assert Geometry.from_json_value({"type": "point", "coordinates": [1, 2]}) == Point(1.0, 2.0)


def test_subclass_geojson_without_type_is_accepted():
    assert Point.from_json_value({"coordinates": [1, 2]}) == Point(1.0, 2.0)


def test_subclass_geojson_rejects_type_mismatch():
    with pytest.raises(ValueError):
        Point.from_json_value({"type": "LineString", "coordinates": [[0, 0], [1, 1]]})


@pytest.mark.parametrize(
    "value",
    [
        {"coordinates": [1, 2]},
        {"type": "Nope", "coordinates": [1, 2]},
        {"type": "Point"},
        {"type": "Point", "coordinates": [1]},
        {"type": "GeometryCollection"},
        {"type": "Point", "coordinates": [1, 2], "srid": -1},
    ],
)
def test_invalid_geojson_raises_value_error(value):
    with pytest.raises(ValueError):
        Geometry.from_json_value(value)


def test_from_json_value_requires_mapping():
    with pytest.raises(TypeError):
        Geometry.from_json_value([1, 2])  # type: ignore[arg-type]


# --- equality / hashing ---------------------------------------------------


def test_equal_values_ignore_list_vs_tuple_and_int_vs_float():
    assert Point(1, 2) == Point(1.0, 2.0)
    assert Polygon([OUTER_RING]) == Polygon([tuple(OUTER_RING)])  # type: ignore[arg-type]
    assert MultiPoint([(0, 0), (1, 1)]) == MultiPoint([(0.0, 0.0), (1.0, 1.0)])


def test_srid_participates_in_equality():
    assert Point(1.0, 2.0) != Point(1.0, 2.0, srid=4326)


def test_different_shapes_are_not_equal():
    assert Point(0.0, 0.0) != MultiPoint([(0.0, 0.0)])
    assert LineString([(0.0, 0.0), (1.0, 1.0)]) != MultiLineString([[(0.0, 0.0), (1.0, 1.0)]])


def test_geometries_are_hashable_and_dedupe_in_sets():
    assert len({Point(1, 2), Point(1.0, 2.0)}) == 1
    assert len({SAMPLE_POINT, SAMPLE_LINESTRING, SAMPLE_POINT}) == 2


def test_json_type_tag_is_inherited_by_all_shapes():
    assert Geometry.json_type_tag == "geometry"
    for geometry in SAMPLE_GEOMETRIES:
        assert geometry.json_type_tag == "geometry"


# --- GeometryAdapterBase --------------------------------------------------


class FakeGeometryAdapter(GeometryAdapterBase):
    """WKT/bytes adapter used to exercise the hooks without a database."""

    def _encode(self, geometry, target_type, options):
        if options.get("fail"):
            raise RuntimeError("boom")
        if target_type is bytes:
            return geometry.to_wkt().encode("utf-8")
        return geometry.to_wkt()

    def _decode(self, value, options):
        if options.get("fail"):
            raise RuntimeError("boom")
        if options.get("return_raw"):
            return value
        if isinstance(value, bytes):
            value = value.decode("utf-8")
        return Geometry.from_wkt(value)


@pytest.fixture
def adapter():
    return FakeGeometryAdapter()


def test_adapter_base_is_abstract():
    with pytest.raises(TypeError):
        GeometryAdapterBase()  # type: ignore[abstract]
    assert GeometryAdapterBase.neutral_type is Geometry


def test_adapter_encodes_neutral_geometry(adapter):
    assert adapter.to_database(SAMPLE_POINT, str) == "POINT (1.0 -2.0)"


def test_adapter_encodes_wkt_text_and_geojson_mapping(adapter):
    assert adapter.to_database("POINT (1.0 2.0)", str) == "POINT (1.0 2.0)"
    assert adapter.to_database({"type": "Point", "coordinates": [1, 2]}, str) == ("POINT (1.0 2.0)")


def test_adapter_passes_options_to_encode_hook(adapter):
    assert adapter.to_database(SAMPLE_POINT, bytes) == b"POINT (1.0 -2.0)"


def test_adapter_decodes_to_neutral_geometry(adapter):
    assert adapter.from_database("POINT (1.0 2.0)", Geometry) == Point(1.0, 2.0)
    assert adapter.from_database(b"LINESTRING (0.0 0.0, 1.0 1.0)", Geometry) == (
        LineString([(0.0, 0.0), (1.0, 1.0)])
    )


def test_adapter_passes_none_through(adapter):
    assert adapter.to_database(None, str) is None
    assert adapter.from_database(None, Geometry) is None


def test_adapter_wraps_encode_errors(adapter):
    with pytest.raises(TypeConversionError) as excinfo:
        adapter.to_database(SAMPLE_POINT, str, {"fail": True})
    assert "Cannot convert Point to Geometry: RuntimeError: boom" in str(excinfo.value)


def test_adapter_wraps_decode_errors(adapter):
    with pytest.raises(TypeConversionError) as excinfo:
        adapter.from_database("POINT (1 2)", Geometry, {"fail": True})
    assert "Cannot convert str to Geometry: RuntimeError: boom" in str(excinfo.value)


def test_adapter_rejects_non_geometry_input(adapter):
    with pytest.raises(TypeConversionError):
        adapter.to_database(42, str)


def test_adapter_reports_invalid_wkt(adapter):
    with pytest.raises(TypeConversionError) as excinfo:
        adapter.to_database("POINT (1 2 3)", str)
    assert "invalid WKT" in str(excinfo.value)


def test_adapter_rejects_non_geometry_decode_result(adapter):
    with pytest.raises(TypeConversionError) as excinfo:
        adapter.from_database("POINT (1 2)", Geometry, {"return_raw": True})
    assert "expected a concrete Geometry" in str(excinfo.value)


# --- AdapterJSONCodec tagged mode ----------------------------------------


@pytest.mark.parametrize(
    "geometry",
    [
        Point(1.0, 2.0, srid=4326),
        GeometryCollection(
            [Point(1.0, 2.0, srid=4326), LineString([(0.0, 0.0), (1.0, 1.0)])],
            srid=4326,
        ),
    ],
    ids=["point", "geometrycollection"],
)
def test_tagged_codec_round_trip(geometry):
    codec = AdapterJSONCodec(tagged=True)
    text = codec.dumps(geometry)
    payload = json.loads(text)
    assert payload["__type__"] == "geometry"

    restored = codec.loads(text)
    assert isinstance(restored, type(geometry))
    assert restored == geometry
