# src/rhosocial/activerecord/backend/impl/sqlite/functions/geopoly.py
"""
SQLite Geopoly function factories.

SQLite 3.26+ includes the geopoly extension for 2D polygon geometry operations.
These functions provide a consistent API for working with polygon data in SQLite.

Functions: geopoly_contains, geopoly_within, geopoly_overlap,
geopoly_area, geopoly_x, geopoly_y, geopoly_centerpoint,
geopoly_json, geopoly_blob, geopoly_debug, geopoly_svg, geopoly_bbox,
geopoly_xform, geopoly_regular, geopoly_ccw, geopoly_cw

Reference: https://www.sqlite.org/geopoly.html
"""

from typing import Union, Optional, TYPE_CHECKING

from rhosocial.activerecord.backend.expression import bases, core

if TYPE_CHECKING:  # pragma: no cover
    from rhosocial.activerecord.backend.dialect import SQLDialectBase
    from .dialect import SQLiteDialect


def _convert_to_expression(
    dialect: "SQLDialectBase",
    expr: Union[str, "bases.BaseExpression"],
    handle_numeric_literals: bool = True,
) -> "bases.BaseExpression":
    """Convert an input value to an appropriate BaseExpression."""
    if isinstance(expr, bases.BaseExpression):
        return expr
    elif isinstance(expr, (int, float)):
        if handle_numeric_literals:
            return core.Literal(dialect, expr)
        return core.Column(dialect, str(expr))
    elif isinstance(expr, str):
        return core.Literal(dialect, expr)
    else:
        return core.Column(dialect, expr)


def geopoly_contains(
    dialect: "SQLiteDialect",
    polygon: Union[str, "bases.BaseExpression"],
    x: Union[float, "bases.BaseExpression"],
    y: Union[float, "bases.BaseExpression"],
) -> "core.FunctionCall":
    """Check if a point is inside a polygon.

    Returns 1 if the point (x, y) is contained within the polygon,
    0 if outside, or NULL if the polygon is NULL.

    Usage:
        geopoly_contains(dialect, polygon_json, -122.4194, 37.7749)

    Args:
        dialect: The SQLite dialect instance
        polygon: Polygon JSON definition or column
        x: X coordinate (longitude)
        y: Y coordinate (latitude)

    Returns:
        A FunctionCall instance representing geopoly_contains

    Version: SQLite 3.26.0+
    """
    poly_expr = _convert_to_expression(dialect, polygon)
    x_expr = _convert_to_expression(dialect, x)
    y_expr = _convert_to_expression(dialect, y)
    return core.FunctionCall(dialect, "geopoly_contains", poly_expr, x_expr, y_expr)


def geopoly_within(
    dialect: "SQLiteDialect",
    polygon: Union[str, "bases.BaseExpression"],
) -> "core.FunctionCall":
    """Check if a polygon is entirely within another polygon.

    Returns 1 if the polygon is completely within the _shape value,
    0 if not completely within.

    Usage:
        geopoly_within(dialect, polygon)

    Args:
        dialect: The SQLite dialect instance
        polygon: Polygon to check

    Returns:
        A FunctionCall instance representing geopoly_within

    Version: SQLite 3.26.0+
    """
    poly_expr = _convert_to_expression(dialect, polygon)
    return core.FunctionCall(dialect, "geopoly_within", poly_expr)


def geopoly_overlap(
    dialect: "SQLiteDialect",
    polygon1: Union[str, "bases.BaseExpression"],
    polygon2: Union[str, "bases.BaseExpression"],
) -> "core.FunctionCall":
    """Check if two polygons overlap.

    Returns 1 if the two polygons overlap, 0 if they do not overlap.

    Usage:
        geopoly_overlap(dialect, polygon1, polygon2)

    Args:
        dialect: The SQLite dialect instance
        polygon1: First polygon
        polygon2: Second polygon

    Returns:
        A FunctionCall instance representing geopoly_overlap

    Version: SQLite 3.26.0+
    """
    poly1_expr = _convert_to_expression(dialect, polygon1)
    poly2_expr = _convert_to_expression(dialect, polygon2)
    return core.FunctionCall(dialect, "geopoly_overlap", poly1_expr, poly2_expr)


def geopoly_area(
    dialect: "SQLiteDialect",
    polygon: Union[str, "bases.BaseExpression"],
) -> "core.FunctionCall":
    """Calculate the area of a polygon.

    Returns the area of the polygon as a real number.

    Usage:
        geopoly_area(dialect, polygon)

    Args:
        dialect: The SQLite dialect instance
        polygon: Polygon definition or column

    Returns:
        A FunctionCall instance representing geopoly_area

    Version: SQLite 3.26.0+
    """
    poly_expr = _convert_to_expression(dialect, polygon)
    return core.FunctionCall(dialect, "geopoly_area", poly_expr)


def geopoly_x(
    dialect: "SQLiteDialect",
    polygon: Union[str, "bases.BaseExpression"],
) -> "core.FunctionCall":
    """Get the X coordinate of a vertex of the polygon.

    Args:
        dialect: The SQLite dialect instance
        polygon: Polygon definition

    Returns:
        A FunctionCall instance representing geopoly_x

    Version: SQLite 3.26.0+
    """
    poly_expr = _convert_to_expression(dialect, polygon)
    return core.FunctionCall(dialect, "geopoly_x", poly_expr)


def geopoly_y(
    dialect: "SQLiteDialect",
    polygon: Union[str, "bases.BaseExpression"],
) -> "core.FunctionCall":
    """Get the Y coordinate of a vertex of the polygon.

    Args:
        dialect: The SQLite dialect instance
        polygon: Polygon definition

    Returns:
        A FunctionCall instance representing geopoly_y

    Version: SQLite 3.26.0+
    """
    poly_expr = _convert_to_expression(dialect, polygon)
    return core.FunctionCall(dialect, "geopoly_y", poly_expr)


def geopoly_centerpoint(
    dialect: "SQLiteDialect",
    polygon: Union[str, "bases.BaseExpression"],
) -> "core.FunctionCall":
    """Calculate the center point of a polygon.

    Returns a JSON array [x, y] containing the approximate
    center point of the polygon.

    Usage:
        geopoly_centerpoint(dialect, polygon)

    Args:
        dialect: The SQLite dialect instance
        polygon: Polygon definition

    Returns:
        A FunctionCall instance representing geopoly_centerpoint

    Version: SQLite 3.26.0+
    """
    poly_expr = _convert_to_expression(dialect, polygon)
    return core.FunctionCall(dialect, "geopoly_centerpoint", poly_expr)


def geopoly_json(
    dialect: "SQLiteDialect",
    polygon: Union[str, "bases.BaseExpression"],
) -> "core.FunctionCall":
    """Convert a BLOB to a JSON polygon definition.

    Returns a JSON array of [x, y] coordinates representing
    the polygon.

    Usage:
        geopoly_json(dialect, blob_column)

    Args:
        dialect: The SQLite dialect instance
        polygon: Polygon BLOB

    Returns:
        A FunctionCall instance representing geopoly_json

    Version: SQLite 3.26.0+
    """
    poly_expr = _convert_to_expression(dialect, polygon)
    return core.FunctionCall(dialect, "geopoly_json", poly_expr)


def geopoly_blob(
    dialect: "SQLiteDialect",
    polygon: Union[str, "bases.BaseExpression"],
) -> "core.FunctionCall":
    """Convert a JSON polygon definition to BLOB.

    Returns a BLOB containing the polygon definition.

    Usage:
        geopoly_blob(dialect, polygon_json)

    Args:
        dialect: The SQLite dialect instance
        polygon: Polygon JSON definition

    Returns:
        A FunctionCall instance representing geopoly_blob

    Version: SQLite 3.26.0+
    """
    poly_expr = _convert_to_expression(dialect, polygon)
    return core.FunctionCall(dialect, "geopoly_blob", poly_expr)


def geopoly_debug(
    dialect: "SQLiteDialect",
    polygon: Union[str, "bases.BaseExpression"],
) -> "core.FunctionCall":
    """Return text rendering of a polygon for debugging.

    Returns a text description of the polygon for debugging.

    Usage:
        geopoly_debug(dialect, polygon)

    Args:
        dialect: The SQLite dialect instance
        polygon: Polygon definition

    Returns:
        A FunctionCall instance representing geopoly_debug

    Version: SQLite 3.26.0+
    """
    poly_expr = _convert_to_expression(dialect, polygon)
    return core.FunctionCall(dialect, "geopoly_debug", poly_expr)


def geopoly_svg(
    dialect: "SQLiteDialect",
    polygon: Union[str, "bases.BaseExpression"],
    *,
    xscale: Optional[Union[float, "bases.BaseExpression"]] = None,
    yscale: Optional[Union[float, "bases.BaseExpression"]] = None,
    xoff: Optional[Union[float, "bases.BaseExpression"]] = None,
    yoff: Optional[Union[float, "bases.BaseExpression"]] = None,
) -> "core.FunctionCall":
    """Convert a polygon to SVG format.

    Returns a text string which is a Scalable Vector Graphics (SVG) representation
    of the polygon.

    Usage:
        geopoly_svg(dialect, polygon)
        geopoly_svg(dialect, polygon, xscale=1.0, yscale=-1.0, xoff=0, yoff=400)

    Args:
        dialect: The SQLite dialect instance
        polygon: Polygon definition
        xscale: X scale factor (default 1.0)
        yscale: Y scale factor (default -1.0)
        xoff: X offset (default 0)
        yoff: Y offset (default 0)

    Returns:
        A FunctionCall instance representing geopoly_svg

    Version: SQLite 3.26.0+
    """
    poly_expr = _convert_to_expression(dialect, polygon)
    args = [poly_expr]
    if xscale is not None:
        args.append(_convert_to_expression(dialect, xscale))
    if yscale is not None:
        args.append(_convert_to_expression(dialect, yscale))
    if xoff is not None:
        args.append(_convert_to_expression(dialect, xoff))
    if yoff is not None:
        args.append(_convert_to_expression(dialect, yoff))
    return core.FunctionCall(dialect, "geopoly_svg", *args)


def geopoly_bbox(
    dialect: "SQLiteDialect",
    polygon: Union[str, "bases.BaseExpression"],
) -> "core.FunctionCall":
    """Calculate the bounding box of a polygon.

    Returns a new polygon that is the smallest (axis-aligned) rectangle
    completely containing the input polygon.

    Usage:
        geopoly_bbox(dialect, polygon)

    Args:
        dialect: The SQLite dialect instance
        polygon: Polygon definition

    Returns:
        A FunctionCall instance representing geopoly_bbox

    Version: SQLite 3.26.0+
    """
    poly_expr = _convert_to_expression(dialect, polygon)
    return core.FunctionCall(dialect, "geopoly_bbox", poly_expr)


def geopoly_group_bbox(
    dialect: "SQLiteDialect",
    polygon: Union[str, "bases.BaseExpression"],
) -> "core.FunctionCall":
    """Calculate the bounding box of a group of polygons (aggregate).

    Returns a new polygon that is the smallest (axis-aligned) rectangle
    completely containing all input polygons.

    Note: This is an aggregate function.

    Usage:
        geopoly_group_bbox(dialect, polygon)

    Args:
        dialect: The SQLite dialect instance
        polygon: Polygon definition

    Returns:
        A FunctionCall instance representing geopoly_group_bbox

    Version: SQLite 3.26.0+
    """
    poly_expr = _convert_to_expression(dialect, polygon)
    return core.FunctionCall(dialect, "geopoly_group_bbox", poly_expr)


def geopoly_contains_point(
    dialect: "SQLiteDialect",
    polygon: Union[str, "bases.BaseExpression"],
    x: Union[float, "bases.BaseExpression"],
    y: Union[float, "bases.BaseExpression"],
) -> "core.FunctionCall":
    """Check if a point is inside a polygon.

    This is an alias for geopoly_contains().

    Usage:
        geopoly_contains_point(dialect, polygon, x, y)

    Args:
        dialect: The SQLite dialect instance
        polygon: Polygon JSON definition or column
        x: X coordinate
        y: Y coordinate

    Returns:
        A FunctionCall instance representing geopoly_contains_point

    Version: SQLite 3.26.0+
    """
    poly_expr = _convert_to_expression(dialect, polygon)
    x_expr = _convert_to_expression(dialect, x)
    y_expr = _convert_to_expression(dialect, y)
    return core.FunctionCall(dialect, "geopoly_contains_point", poly_expr, x_expr, y_expr)


def geopoly_xform(
    dialect: "SQLiteDialect",
    polygon: Union[str, "bases.BaseExpression"],
    a: Union[float, "bases.BaseExpression"],
    b: Union[float, "bases.BaseExpression"],
    c: Union[float, "bases.BaseExpression"],
    d: Union[float, "bases.BaseExpression"],
    e: Union[float, "bases.BaseExpression"],
    f: Union[float, "bases.BaseExpression"],
) -> "core.FunctionCall":
    """Transform a polygon using an affine transformation.

    Applies an affine transformation to the polygon using the formula:
    new_x = a*x + c*y + e
    new_y = b*x + d*y + f

    Usage:
        geopoly_xform(dialect, polygon, 1.0, 0.0, 0.0, 1.0, 0.0, 0.0)

    Args:
        dialect: The SQLite dialect instance
        polygon: Polygon definition
        a: Transform coefficient for new x from old x
        b: Transform coefficient for new y from old x
        c: Transform coefficient for new x from old y
        d: Transform coefficient for new y from old y
        e: X offset
        f: Y offset

    Returns:
        A FunctionCall instance representing geopoly_xform

    Version: SQLite 3.26.0+
    """
    poly_expr = _convert_to_expression(dialect, polygon)
    return core.FunctionCall(
        dialect, "geopoly_xform", poly_expr,
        _convert_to_expression(dialect, a),
        _convert_to_expression(dialect, b),
        _convert_to_expression(dialect, c),
        _convert_to_expression(dialect, d),
        _convert_to_expression(dialect, e),
        _convert_to_expression(dialect, f),
    )


def geopoly_regular(
    dialect: "SQLiteDialect",
    x: Union[float, "bases.BaseExpression"],
    y: Union[float, "bases.BaseExpression"],
    radius: Union[float, "bases.BaseExpression"],
    n: Union[int, "bases.BaseExpression"],
) -> "core.FunctionCall":
    """Create a regular polygon.

    Returns a regular polygon with N vertices centered at (x, y)
    with circumradius R.

    Usage:
        geopoly_regular(dialect, 0.0, 0.0, 10.0, 6)  # hexagon

    Args:
        dialect: The SQLite dialect instance
        x: Center X coordinate
        y: Center Y coordinate
        radius: Circumradius
        n: Number of vertices

    Returns:
        A FunctionCall instance representing geopoly_regular

    Version: SQLite 3.26.0+
    """
    x_expr = _convert_to_expression(dialect, x)
    y_expr = _convert_to_expression(dialect, y)
    r_expr = _convert_to_expression(dialect, radius)
    n_expr = _convert_to_expression(dialect, n)
    return core.FunctionCall(dialect, "geopoly_regular", x_expr, y_expr, r_expr, n_expr)


def geopoly_ccw(
    dialect: "SQLiteDialect",
    polygon: Union[str, "bases.BaseExpression"],
) -> "core.FunctionCall":
    """Reorder polygon vertices to counter-clockwise order.

    Returns a new polygon with vertices reordered to be in counter-clockwise order.

    Usage:
        geopoly_ccw(dialect, polygon)

    Args:
        dialect: The SQLite dialect instance
        polygon: Polygon definition

    Returns:
        A FunctionCall instance representing geopoly_ccw

    Version: SQLite 3.26.0+
    """
    poly_expr = _convert_to_expression(dialect, polygon)
    return core.FunctionCall(dialect, "geopoly_ccw", poly_expr)


def geopoly_cw(
    dialect: "SQLiteDialect",
    polygon: Union[str, "bases.BaseExpression"],
) -> "core.FunctionCall":
    """Reorder polygon vertices to clockwise order.

    Returns a new polygon with vertices reordered to be in clockwise order.

    Usage:
        geopoly_cw(dialect, polygon)

    Args:
        dialect: The SQLite dialect instance
        polygon: Polygon definition

    Returns:
        A FunctionCall instance representing geopoly_cw

    Version: SQLite 3.26.0+
    """
    poly_expr = _convert_to_expression(dialect, polygon)
    return core.FunctionCall(dialect, "geopoly_cw", poly_expr)