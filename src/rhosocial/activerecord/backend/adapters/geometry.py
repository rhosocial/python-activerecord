# src/rhosocial/activerecord/backend/adapters/geometry.py
"""Neutral 2D geometry types and the adapter base every backend derives.

The types in this module are deliberately independent of any database driver:

- all coordinates are 2D ``(x, y)``; 3D/4D input raises ``ValueError`` instead
  of being silently flattened;
- an :class:`~rhosocial.activerecord.backend.errors.TypeConversionError` never
  leaks driver-private objects: adapters decode to these neutral types;
- ``SRID`` is an optional attribute *outside* the shape. WKT output is plain
  WKT (not EWKT); GeoJSON output carries it as the non-standard ``"srid"``
  member, and ``from_wkt`` accepts an optional ``SRID=...;`` prefix.

The WKT parser is intentionally minimal: the seven standard types below, 2D
only, and no ``EMPTY``/curve/TIN/polyhedral-surface forms. Anything outside
that range raises ``ValueError``.
"""

import math
import re
from abc import abstractmethod
from collections.abc import Mapping as MappingABC
from dataclasses import dataclass, field
from typing import Any, ClassVar, Dict, List, Optional, Tuple, Type

from ..errors import TypeConversionError
from ..type_adapter import BaseSQLTypeAdapter

Coordinate = Tuple[float, float]
Ring = Tuple[Coordinate, ...]
PolygonRings = Tuple[Ring, ...]

_WKT_TYPE_NAMES = (
    "POINT",
    "LINESTRING",
    "POLYGON",
    "MULTIPOINT",
    "MULTILINESTRING",
    "MULTIPOLYGON",
    "GEOMETRYCOLLECTION",
)
_DIMENSION_WORDS = frozenset(("Z", "M", "ZM"))


# --- Validation helpers ----------------------------------------------------


def _validate_srid(srid: Any) -> Optional[int]:
    """Return a usable SRID or raise ``TypeError``/``ValueError``."""
    if srid is None:
        return None
    if isinstance(srid, bool) or not isinstance(srid, int):
        raise TypeError(f"srid must be int or None, got {type(srid).__name__}")
    if srid < 0:
        raise ValueError(f"srid must be non-negative, got {srid}")
    return srid


def _finite_float(value: Any, field_name: str) -> float:
    """Return ``value`` as a finite ``float``."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TypeError(f"{field_name} must be int or float, got {type(value).__name__}")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{field_name} must be finite, got {result!r}")
    return result


def _sequence_of(value: Any, field_name: str) -> tuple:
    """Return ``value`` as a tuple when it is a plain list/tuple."""
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, (list, tuple)):
        raise TypeError(f"{field_name} must be a list or tuple, got {type(value).__name__}")
    return tuple(value)


def _point_pair(value: Any, field_name: str) -> Coordinate:
    """Validate one 2D coordinate pair."""
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, (list, tuple)):
        raise TypeError(f"{field_name} must be a (x, y) pair, got {type(value).__name__}")
    if len(value) != 2:
        raise ValueError(f"{field_name} must be 2D (x, y), got {len(value)} ordinates")
    return (
        _finite_float(value[0], f"{field_name}[0]"),
        _finite_float(value[1], f"{field_name}[1]"),
    )


def _point_sequence(value: Any, field_name: str, min_points: int) -> Tuple[Coordinate, ...]:
    """Validate a non-empty coordinate sequence."""
    points = tuple(
        _point_pair(item, f"{field_name}[{index}]")
        for index, item in enumerate(_sequence_of(value, field_name))
    )
    if len(points) < min_points:
        raise ValueError(f"{field_name} requires at least {min_points} points, got {len(points)}")
    return points


def _linear_ring(value: Any, field_name: str) -> Ring:
    """Validate a closed polygon ring (``>= 4`` points including closure)."""
    ring = _point_sequence(value, field_name, 4)
    if ring[0] != ring[-1]:
        raise ValueError(f"{field_name} must be closed: first and last points must match")
    return ring


def _ring_sequence(value: Any, field_name: str) -> PolygonRings:
    """Validate a polygon's exterior + interior rings."""
    items = _sequence_of(value, field_name)
    rings = tuple(_linear_ring(item, f"{field_name}[{index}]") for index, item in enumerate(items))
    if not rings:
        raise ValueError(f"{field_name} requires at least one ring")
    return rings


def _polygon_sequence(value: Any, field_name: str) -> Tuple[PolygonRings, ...]:
    """Validate the polygon list of a multipolygon."""
    items = _sequence_of(value, field_name)
    polygons = tuple(
        _ring_sequence(item, f"{field_name}[{index}]") for index, item in enumerate(items)
    )
    if not polygons:
        raise ValueError(f"{field_name} requires at least one polygon")
    return polygons


def _geometry_sequence(value: Any, field_name: str) -> Tuple["Geometry", ...]:
    """Validate the children of a geometry collection."""
    items = _sequence_of(value, field_name)
    geometries = tuple(items)
    if not geometries:
        raise ValueError(f"{field_name} requires at least one geometry")
    for index, geometry in enumerate(geometries):
        if not isinstance(geometry, Geometry) or type(geometry) is Geometry:
            raise TypeError(
                f"{field_name}[{index}] must be a concrete Geometry, got {type(geometry).__name__}"
            )
    return geometries


# --- Neutral geometry types ------------------------------------------------


@dataclass(frozen=True, init=False)
class Geometry:
    """Base class for the neutral 2D geometry shapes.

    ``srid`` is declared ``init=False`` on the base so subclasses can keep
    required payload fields while still accepting ``srid`` keyword last in
    their own constructors (dataclasses have no keyword-only fields on
    Python 3.8). Equality and hashing include ``srid``.
    """

    #: Stable tag used by ``AdapterJSONCodec`` for tagged JSON envelopes.
    json_type_tag: ClassVar[str] = "geometry"

    srid: Optional[int] = field(default=None, init=False)

    def __init__(self, srid: Optional[int] = None) -> None:
        object.__setattr__(self, "srid", _validate_srid(srid))

    def to_wkt(self) -> str:
        """Return plain 2D WKT (never EWKT)."""
        if isinstance(self, Point):
            return "POINT ({})".format(_format_coordinate((self.x, self.y)))
        if isinstance(self, LineString):
            return "LINESTRING ({})".format(_format_coordinate_list(self.points))
        if isinstance(self, Polygon):
            return "POLYGON ({})".format(_format_ring_list(self.rings))
        if isinstance(self, MultiPoint):
            return "MULTIPOINT ({})".format(_format_coordinate_list(self.points))
        if isinstance(self, MultiLineString):
            return "MULTILINESTRING ({})".format(
                ", ".join("({})".format(_format_coordinate_list(line)) for line in self.lines)
            )
        if isinstance(self, MultiPolygon):
            return "MULTIPOLYGON ({})".format(
                ", ".join("({})".format(_format_ring_list(polygon)) for polygon in self.polygons)
            )
        if isinstance(self, GeometryCollection):
            return "GEOMETRYCOLLECTION ({})".format(
                ", ".join(child.to_wkt() for child in self.geometries)
            )
        raise TypeError("Cannot build WKT from the abstract Geometry base")

    @classmethod
    def from_wkt(cls, text: str, srid: Optional[int] = None) -> "Geometry":
        """Parse plain 2D WKT with an optional ``SRID=...;`` prefix.

        A prefix in ``text`` wins over the ``srid`` argument. Unsupported
        dimensions, curve/TIN forms, ``EMPTY`` shapes and malformed text all
        raise ``ValueError``.
        """
        if not isinstance(text, str):
            raise TypeError(f"text must be str, got {type(text).__name__}")
        srid = _validate_srid(srid)
        parsed = _parse_wkt(text, srid)
        if cls is Geometry:
            return parsed
        if type(parsed) is not cls:
            raise ValueError(f"WKT type {type(parsed).__name__} does not match {cls.__name__}")
        return parsed

    def to_json_value(self) -> Dict[str, Any]:
        """Return a GeoJSON object with an optional non-standard ``"srid"``."""
        if isinstance(self, Point):
            return _json_geometry(self, [self.x, self.y])
        if isinstance(self, LineString):
            return _json_geometry(self, _json_coordinates(self.points))
        if isinstance(self, Polygon):
            return _json_geometry(self, _json_coordinates(self.rings))
        if isinstance(self, MultiPoint):
            return _json_geometry(self, _json_coordinates(self.points))
        if isinstance(self, MultiLineString):
            return _json_geometry(self, _json_coordinates(self.lines))
        if isinstance(self, MultiPolygon):
            return _json_geometry(self, _json_coordinates(self.polygons))
        if isinstance(self, GeometryCollection):
            result: Dict[str, Any] = {
                "type": "GeometryCollection",
                "geometries": [child.to_json_value() for child in self.geometries],
            }
            if self.srid is not None:
                result["srid"] = self.srid
            return result
        raise TypeError("Cannot build GeoJSON from the abstract Geometry base")

    @classmethod
    def from_json_value(cls, value: MappingABC) -> "Geometry":
        """Rebuild a geometry from a GeoJSON object.

        ``Geometry.from_json_value`` dispatches on ``"type"``. A concrete
        subclass may omit ``"type"``; when present it must match the class.
        """
        if not isinstance(value, MappingABC):
            raise TypeError(f"value must be a mapping, got {type(value).__name__}")

        declared = value.get("type")
        if cls is Geometry:
            if not isinstance(declared, str):
                raise ValueError("GeoJSON geometry requires a 'type' string")
            target = _GEOJSON_TYPES.get(declared.lower())
            if target is None:
                raise ValueError(f"unsupported GeoJSON geometry type: {declared!r}")
        else:
            target = cls
            if declared is not None:
                if not isinstance(declared, str):
                    raise ValueError("GeoJSON 'type' must be a string")
                if declared.lower() != cls._json_type.lower():
                    raise ValueError(f"GeoJSON type {declared!r} does not match {cls.__name__}")

        srid = _validate_srid(value.get("srid"))

        if target is GeometryCollection:
            geometries = value.get("geometries")
            if not isinstance(geometries, (list, tuple)):
                raise ValueError("GeoJSON GeometryCollection requires a 'geometries' list")
            try:
                children = tuple(Geometry.from_json_value(child) for child in geometries)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"invalid GeoJSON GeometryCollection: {exc}") from exc
            return GeometryCollection(children, srid=srid)

        coordinates = value.get("coordinates")
        if coordinates is None:
            raise ValueError("GeoJSON geometry requires 'coordinates'")
        try:
            return _build_from_coordinates(target, coordinates, srid)
        except (TypeError, IndexError) as exc:
            raise ValueError(f"invalid GeoJSON coordinates for {target.__name__}: {exc}") from exc


@dataclass(frozen=True, init=False)
class Point(Geometry):
    """A single 2D point."""

    _json_type: ClassVar[str] = "Point"

    x: float
    y: float

    def __init__(self, x: float, y: float, srid: Optional[int] = None) -> None:
        super().__init__(srid)
        object.__setattr__(self, "x", _finite_float(x, "x"))
        object.__setattr__(self, "y", _finite_float(y, "y"))


@dataclass(frozen=True, init=False)
class LineString(Geometry):
    """An ordered sequence of two or more 2D points."""

    _json_type: ClassVar[str] = "LineString"

    points: Tuple[Coordinate, ...]

    def __init__(self, points: Any, srid: Optional[int] = None) -> None:
        super().__init__(srid)
        object.__setattr__(self, "points", _point_sequence(points, "points", 2))


@dataclass(frozen=True, init=False)
class Polygon(Geometry):
    """An exterior ring plus optional interior rings; every ring is closed."""

    _json_type: ClassVar[str] = "Polygon"

    rings: PolygonRings

    def __init__(self, rings: Any, srid: Optional[int] = None) -> None:
        super().__init__(srid)
        object.__setattr__(self, "rings", _ring_sequence(rings, "rings"))


@dataclass(frozen=True, init=False)
class MultiPoint(Geometry):
    """A non-empty set of 2D points."""

    _json_type: ClassVar[str] = "MultiPoint"

    points: Tuple[Coordinate, ...]

    def __init__(self, points: Any, srid: Optional[int] = None) -> None:
        super().__init__(srid)
        object.__setattr__(self, "points", _point_sequence(points, "points", 1))


@dataclass(frozen=True, init=False)
class MultiLineString(Geometry):
    """A non-empty set of line strings."""

    _json_type: ClassVar[str] = "MultiLineString"

    lines: Tuple[Tuple[Coordinate, ...], ...]

    def __init__(self, lines: Any, srid: Optional[int] = None) -> None:
        super().__init__(srid)
        items = _sequence_of(lines, "lines")
        parsed = tuple(
            _point_sequence(item, f"lines[{index}]", 2) for index, item in enumerate(items)
        )
        if not parsed:
            raise ValueError("lines requires at least one line string")
        object.__setattr__(self, "lines", parsed)


@dataclass(frozen=True, init=False)
class MultiPolygon(Geometry):
    """A non-empty set of polygons."""

    _json_type: ClassVar[str] = "MultiPolygon"

    polygons: Tuple[PolygonRings, ...]

    def __init__(self, polygons: Any, srid: Optional[int] = None) -> None:
        super().__init__(srid)
        object.__setattr__(self, "polygons", _polygon_sequence(polygons, "polygons"))


@dataclass(frozen=True, init=False)
class GeometryCollection(Geometry):
    """A non-empty heterogeneous collection of concrete geometry shapes."""

    _json_type: ClassVar[str] = "GeometryCollection"

    geometries: Tuple[Geometry, ...]

    def __init__(self, geometries: Any, srid: Optional[int] = None) -> None:
        super().__init__(srid)
        object.__setattr__(self, "geometries", _geometry_sequence(geometries, "geometries"))


_GEOJSON_TYPES: Dict[str, Type[Geometry]] = {
    "point": Point,
    "linestring": LineString,
    "polygon": Polygon,
    "multipoint": MultiPoint,
    "multilinestring": MultiLineString,
    "multipolygon": MultiPolygon,
    "geometrycollection": GeometryCollection,
}


def _build_from_coordinates(
    target: Type[Geometry], coordinates: Any, srid: Optional[int]
) -> Geometry:
    """Construct ``target`` from its GeoJSON ``coordinates`` payload."""
    if target is Point:
        if not isinstance(coordinates, (list, tuple)) or len(coordinates) != 2:
            raise ValueError("Point coordinates must be a two-element array")
        return Point(coordinates[0], coordinates[1], srid=srid)
    if target is LineString:
        return LineString(coordinates, srid=srid)
    if target is Polygon:
        return Polygon(coordinates, srid=srid)
    if target is MultiPoint:
        return MultiPoint(coordinates, srid=srid)
    if target is MultiLineString:
        return MultiLineString(coordinates, srid=srid)
    if target is MultiPolygon:
        return MultiPolygon(coordinates, srid=srid)
    raise ValueError(f"cannot build {target.__name__} from coordinates")


# --- WKT formatting --------------------------------------------------------


def _format_number(value: float) -> str:
    return repr(float(value))


def _format_coordinate(coordinate: Coordinate) -> str:
    return "{} {}".format(_format_number(coordinate[0]), _format_number(coordinate[1]))


def _format_coordinate_list(points: Tuple[Coordinate, ...]) -> str:
    return ", ".join(_format_coordinate(point) for point in points)


def _format_ring_list(rings: PolygonRings) -> str:
    return ", ".join("({})".format(_format_coordinate_list(ring)) for ring in rings)


def _json_coordinates(value: Any) -> Any:
    """Turn tuples into JSON arrays recursively."""
    if isinstance(value, tuple):
        return [_json_coordinates(item) for item in value]
    return value


def _json_geometry(geometry: Geometry, coordinates: Any) -> Dict[str, Any]:
    result: Dict[str, Any] = {"type": geometry._json_type, "coordinates": coordinates}
    if geometry.srid is not None:
        result["srid"] = geometry.srid
    return result


# --- Minimal 2D WKT parser -------------------------------------------------

_SRID_PREFIX_RE = re.compile(r"^\s*SRID\s*=\s*([^;]+)\s*;\s*", re.IGNORECASE)

_WKT_TOKEN_RE = re.compile(
    r"(?P<word>[A-Za-z_][A-Za-z0-9_]*)"
    r"|(?P<number>[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[eE][-+]?\d+)?)"
    r"|(?P<lparen>\()"
    r"|(?P<rparen>\))"
    r"|(?P<comma>,)"
)


def _tokenize_wkt(text: str) -> List[Tuple[str, Any]]:
    tokens: List[Tuple[str, Any]] = []
    index = 0
    length = len(text)
    while index < length:
        char = text[index]
        if char.isspace():
            index += 1
            continue
        match = _WKT_TOKEN_RE.match(text, index)
        if match is None:
            raise ValueError(f"unexpected character {char!r} in WKT text at position {index}")
        kind = match.lastgroup
        raw = match.group(kind)
        if kind == "number":
            number = float(raw)
            if not math.isfinite(number):
                raise ValueError(f"coordinate {raw!r} is not finite")
            tokens.append((kind, number))
        else:
            tokens.append((kind, raw))
        index = match.end()
    return tokens


def _parse_wkt(text: str, srid: Optional[int]) -> Geometry:
    match = _SRID_PREFIX_RE.match(text)
    if match is not None:
        raw_srid = match.group(1).strip()
        try:
            prefix_srid = int(raw_srid)
        except ValueError:
            raise ValueError(f"invalid SRID prefix: {raw_srid!r}") from None
        if prefix_srid < 0:
            raise ValueError(f"SRID must be non-negative, got {prefix_srid}")
        srid = prefix_srid
        text = text[match.end() :]

    tokens = _tokenize_wkt(text)
    if not tokens:
        raise ValueError("empty WKT text")
    return _WKTParser(tokens, srid).parse()


class _WKTParser:
    """Recursive-descent parser for the supported 2D WKT subset."""

    def __init__(self, tokens: List[Tuple[str, Any]], srid: Optional[int]) -> None:
        self._tokens = tokens
        self._index = 0
        self._srid = srid

    def parse(self) -> Geometry:
        geometry = self._parse_geometry(top_level=True)
        if self._index != len(self._tokens):
            raise ValueError("unexpected trailing content in WKT text")
        return geometry

    # -- token helpers ------------------------------------------------------

    def _peek(self) -> Optional[Tuple[str, Any]]:
        if self._index < len(self._tokens):
            return self._tokens[self._index]
        return None

    def _advance(self) -> Tuple[str, Any]:
        token = self._peek()
        if token is None:
            raise ValueError("unexpected end of WKT text")
        self._index += 1
        return token

    def _expect(self, kind: str) -> Any:
        token = self._advance()
        if token[0] != kind:
            raise ValueError(f"expected {kind} in WKT text, got {token[1]!r}")
        return token[1]

    def _expect_number(self) -> float:
        return float(self._expect("number"))

    def _accept_comma(self) -> bool:
        token = self._peek()
        if token is not None and token[0] == "comma":
            self._advance()
            return True
        return False

    def _at_rparen(self) -> bool:
        token = self._peek()
        return token is not None and token[0] == "rparen"

    def _at_lparen(self) -> bool:
        token = self._peek()
        return token is not None and token[0] == "lparen"

    # -- shape helpers ------------------------------------------------------

    def _parse_xy(self) -> Coordinate:
        x = self._expect_number()
        y = self._expect_number()
        self._reject_third_ordinate()
        return (x, y)

    def _reject_third_ordinate(self) -> None:
        token = self._peek()
        if token is not None and token[0] == "number":
            raise ValueError("only 2D coordinates are supported; extra ordinate found")

    def _parse_coordinate(self) -> Coordinate:
        self._expect("lparen")
        coordinate = self._parse_xy()
        self._expect("rparen")
        return coordinate

    def _parse_xy_list(self, min_points: int) -> Tuple[Coordinate, ...]:
        self._expect("lparen")
        points = [self._parse_xy()]
        while self._accept_comma():
            points.append(self._parse_xy())
        self._expect("rparen")
        if len(points) < min_points:
            raise ValueError(
                f"coordinate list requires at least {min_points} points, got {len(points)}"
            )
        return tuple(points)

    def _parse_ring(self) -> Ring:
        ring = self._parse_xy_list(4)
        if ring[0] != ring[-1]:
            raise ValueError("polygon rings must be closed: first and last points must match")
        return ring

    def _parse_ring_list(self) -> PolygonRings:
        self._expect("lparen")
        rings = [self._parse_ring()]
        while self._accept_comma():
            rings.append(self._parse_ring())
        self._expect("rparen")
        return tuple(rings)

    # -- geometry dispatch --------------------------------------------------

    def _parse_geometry(self, top_level: bool) -> Geometry:
        keyword = str(self._expect("word")).upper()
        following = self._peek()

        if (
            following is not None
            and following[0] == "word"
            and str(following[1]).upper() in _DIMENSION_WORDS
        ):
            raise ValueError(f"{keyword} {following[1]} is not supported: only 2D WKT is supported")
        if keyword not in _WKT_TYPE_NAMES:
            raise ValueError(f"unsupported WKT geometry type: {keyword!r}")
        if (
            following is not None
            and following[0] == "word"
            and str(following[1]).upper() == "EMPTY"
        ):
            raise ValueError("EMPTY geometries are not supported")

        # Only the outermost geometry carries the parsed SRID; children inside
        # a collection keep their own (None) SRID.
        srid = self._srid if top_level else None

        if keyword == "POINT":
            self._expect("lparen")
            coordinate = self._parse_xy()
            self._expect("rparen")
            return Point(coordinate[0], coordinate[1], srid=srid)

        if keyword == "LINESTRING":
            return LineString(self._parse_xy_list(2), srid=srid)

        if keyword == "POLYGON":
            return Polygon(self._parse_ring_list(), srid=srid)

        if keyword == "MULTIPOINT":
            return MultiPoint(self._parse_multipoint_body(), srid=srid)

        if keyword == "MULTILINESTRING":
            return MultiLineString(self._parse_multilinestring_body(), srid=srid)

        if keyword == "MULTIPOLYGON":
            return MultiPolygon(self._parse_multipolygon_body(), srid=srid)

        return GeometryCollection(self._parse_collection_body(), srid=srid)

    def _parse_multipoint_body(self) -> Tuple[Coordinate, ...]:
        self._expect("lparen")
        if self._at_rparen():
            raise ValueError("MULTIPOINT requires at least one point")
        points = [self._parse_coordinate() if self._at_lparen() else self._parse_xy()]
        while self._accept_comma():
            points.append(self._parse_coordinate() if self._at_lparen() else self._parse_xy())
        self._expect("rparen")
        return tuple(points)

    def _parse_multilinestring_body(self) -> Tuple[Tuple[Coordinate, ...], ...]:
        self._expect("lparen")
        lines = [self._parse_xy_list(2)]
        while self._accept_comma():
            lines.append(self._parse_xy_list(2))
        self._expect("rparen")
        return tuple(lines)

    def _parse_multipolygon_body(self) -> Tuple[PolygonRings, ...]:
        self._expect("lparen")
        polygons = [self._parse_ring_list()]
        while self._accept_comma():
            polygons.append(self._parse_ring_list())
        self._expect("rparen")
        return tuple(polygons)

    def _parse_collection_body(self) -> Tuple[Geometry, ...]:
        self._expect("lparen")
        if self._at_rparen():
            raise ValueError("GEOMETRYCOLLECTION requires at least one geometry")
        geometries = [self._parse_geometry(top_level=False)]
        while self._accept_comma():
            geometries.append(self._parse_geometry(top_level=False))
        self._expect("rparen")
        return tuple(geometries)


# --- Adapter base ----------------------------------------------------------


class GeometryAdapterBase(BaseSQLTypeAdapter):
    """Base class for backend geometry adapters.

    The neutral type accepted by :meth:`to_database` is a
    :class:`Geometry` instance, WKT text, or a GeoJSON mapping; the hook
    :meth:`_encode` receives a validated :class:`Geometry` and decides the
    backend representation (WKT string, EWKB bytes, a driver object, ...).
    :meth:`_decode` must return a neutral :class:`Geometry`; anything else is
    reported as a ``TypeConversionError`` so driver-private objects never
    escape.
    """

    neutral_type = Geometry

    def _do_to_database(
        self, value: Any, target_type: Type, options: Optional[Dict[str, Any]]
    ) -> Any:
        geometry = self._coerce_geometry(value)
        options_dict = options if options is not None else {}
        try:
            return self._encode(geometry, target_type, options_dict)
        except TypeConversionError:
            raise
        except Exception as exc:  # pragma: no cover - defensive wrapping
            self._conversion_error(value, f"{type(exc).__name__}: {exc}")

    def _do_from_database(
        self, value: Any, target_type: Type, options: Optional[Dict[str, Any]]
    ) -> Any:
        options_dict = options if options is not None else {}
        try:
            geometry = self._decode(value, options_dict)
        except TypeConversionError:
            raise
        except Exception as exc:
            self._conversion_error(value, f"{type(exc).__name__}: {exc}")

        if not isinstance(geometry, Geometry) or type(geometry) is Geometry:
            self._conversion_error(
                value,
                f"decoder returned {type(geometry).__name__}, expected a concrete Geometry",
            )
        return geometry

    def _coerce_geometry(self, value: Any) -> Geometry:
        """Accept a neutral geometry, WKT text, or a GeoJSON mapping."""
        if isinstance(value, Geometry) and type(value) is not Geometry:
            return value
        if isinstance(value, str):
            try:
                return Geometry.from_wkt(value)
            except (TypeError, ValueError) as exc:
                self._conversion_error(value, f"invalid WKT: {exc}")
        if isinstance(value, MappingABC):
            try:
                return Geometry.from_json_value(value)
            except (TypeError, ValueError) as exc:
                self._conversion_error(value, f"invalid GeoJSON: {exc}")
        self._conversion_error(value, "expected a Geometry, WKT text, or GeoJSON mapping")

    @abstractmethod
    def _encode(self, geometry: Geometry, target_type: Type, options: Dict[str, Any]) -> Any:
        """Encode a validated neutral geometry into the backend representation."""

    @abstractmethod
    def _decode(self, value: Any, options: Dict[str, Any]) -> Geometry:
        """Decode a backend value into a concrete neutral geometry."""
