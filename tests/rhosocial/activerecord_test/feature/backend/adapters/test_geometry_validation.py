# tests/rhosocial/activerecord_test/feature/backend/adapters/test_geometry_validation.py
"""What the neutral geometry classes refuse.

``test_geometry.py`` covers the shapes the classes build; this file covers the
inputs they **reject**, because a geometry column is written by application
code that gets coordinates wrong -- and the message it gets back is the whole
of the diagnosis. Three doors are checked:

* the constructors (``LineString`` / ``Polygon`` take sequences of pairs);
* the WKT parser (a closed ring, enough points, finite ordinates);
* the GeoJSON loader (a ``type``, ``coordinates``, a geometry list).
"""

import pytest

from rhosocial.activerecord.backend.adapters import (
    Geometry,
    GeometryCollection,
    LineString,
    Point,
    Polygon,
)


def test_a_constructor_takes_a_sequence_not_text():
    with pytest.raises(TypeError, match="points must be a list or tuple"):
        LineString("abc")
    with pytest.raises(TypeError, match="rings must be a list or tuple"):
        Polygon("abc")


def test_a_coordinate_must_be_a_pair():
    with pytest.raises(TypeError, match=r"points\[0\] must be a \(x, y\) pair"):
        LineString([1, 2])


def test_a_coordinate_must_be_numeric():
    with pytest.raises(TypeError, match=r"points\[0\]\[0\] must be int or float"):
        LineString([("x", 1)])


def test_the_abstract_base_has_no_spelling_of_its_own():
    """``Geometry`` is a family root, not a shape: asking it for WKT or GeoJSON
    would have to invent a type name."""
    with pytest.raises(TypeError, match="abstract Geometry base"):
        Geometry().to_wkt()
    with pytest.raises(TypeError, match="abstract Geometry base"):
        Geometry().to_json_value()


# ---------------------------------------------------------------------------
# GeoJSON
# ---------------------------------------------------------------------------


def test_a_geojson_document_must_declare_its_type_as_text():
    with pytest.raises(ValueError, match="requires a 'type' string"):
        Geometry.from_json_value({"type": 1, "coordinates": [1, 1]})


def test_geojson_coordinates_are_required():
    with pytest.raises(ValueError, match="requires 'coordinates'"):
        Geometry.from_json_value({"type": "Point"})


def test_geojson_coordinates_are_validated_by_the_shape():
    with pytest.raises(ValueError, match="two-element array"):
        Geometry.from_json_value({"type": "Point", "coordinates": [1]})


def test_a_geojson_collection_requires_a_geometry_list():
    with pytest.raises(ValueError, match="requires a 'geometries' list"):
        Geometry.from_json_value({"type": "GeometryCollection"})


def test_a_geojson_collection_child_must_be_a_geometry():
    with pytest.raises(ValueError, match="invalid GeoJSON GeometryCollection"):
        Geometry.from_json_value({"type": "GeometryCollection", "geometries": [42]})


def test_a_concrete_class_refuses_a_document_of_another_shape():
    with pytest.raises(ValueError, match="does not match Point"):
        Point.from_json_value({"type": "LineString", "coordinates": [[0, 0], [1, 1]]})


# ---------------------------------------------------------------------------
# WKT
# ---------------------------------------------------------------------------


def test_a_coordinate_list_needs_enough_points():
    with pytest.raises(ValueError, match="at least 2 points"):
        Geometry.from_wkt("LINESTRING (1 1)")


def test_a_ring_must_be_closed():
    """Four points is the minimum, but the first must equal the last: a ring
    that is not closed is not a ring."""
    with pytest.raises(ValueError, match="rings must be closed"):
        Geometry.from_wkt("POLYGON ((0 0, 1 0, 1 1, 0 1))")


def test_a_polygon_may_carry_more_than_one_ring():
    polygon = Geometry.from_wkt("POLYGON ((0 0, 1 0, 1 1, 0 0), (2 2, 3 2, 3 3, 2 2))")

    assert isinstance(polygon, Polygon)
    assert len(polygon.rings) == 2


def test_a_multipoint_needs_at_least_one_point():
    with pytest.raises(ValueError, match="MULTIPOINT requires at least one point"):
        Geometry.from_wkt("MULTIPOINT ()")


def test_a_collection_needs_at_least_one_geometry():
    with pytest.raises(ValueError, match="GEOMETRYCOLLECTION requires at least one geometry"):
        Geometry.from_wkt("GEOMETRYCOLLECTION ()")


def test_an_ordinate_must_be_finite():
    """``1e400`` parses as ``inf``; a coordinate that is not finite is refused
    rather than stored."""
    with pytest.raises(ValueError, match="not finite"):
        Geometry.from_wkt("POINT (1e400 0)")


def test_a_collection_really_builds_from_wkt():
    collection = Geometry.from_wkt("GEOMETRYCOLLECTION (POINT (1 1), LINESTRING (0 0, 1 1))")

    assert isinstance(collection, GeometryCollection)
    assert len(collection.geometries) == 2
