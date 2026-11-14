# src/rhosocial/activerecord/backend/adapters/range.py
"""Neutral Range/Multirange types and their family adapter base.

``Range`` and ``Multirange`` are driver-independent, immutable value objects
mirroring PostgreSQL range semantics.  They depend only on the standard
library; backends derive :class:`RangeAdapterBase` to encode them into and
decode them from their native representations.

The JSON representation is lossless: a non-empty range records its
``element_type`` so that values such as ``"2024-01-01"`` can be restored as a
``date`` rather than a ``datetime``.
"""

from __future__ import annotations

from collections.abc import Mapping as MappingABC
from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal, InvalidOperation
from typing import (
    Any,
    ClassVar,
    Dict,
    List,
    Mapping,
    Optional,
    Sequence,
    Tuple,
    Type,
    Union,
)

from ..errors import TypeConversionError
from ..type_adapter import BaseSQLTypeAdapter

VALID_BOUNDS = ("()", "[)", "(]", "[]")
"""The four valid bound combinations, as ``(lower, upper)`` symbols."""

ELEMENT_TYPE_LABELS = ("int", "float", "decimal", "datetime", "date", "time", "str")
"""Element type labels accepted by the JSON representation."""

_TYPE_TO_LABEL: Dict[type, str] = {
    int: "int",
    float: "float",
    Decimal: "decimal",
    datetime: "datetime",
    date: "date",
    time: "time",
    str: "str",
}

_ISO_ELEMENT_LABELS = ("datetime", "date", "time")


def _label_for_value(value: Any) -> str:
    """Return the registry label for a concrete endpoint value."""
    try:
        return _TYPE_TO_LABEL[type(value)]
    except KeyError:
        raise ValueError(f"Unsupported range element type: {type(value).__name__}") from None


def _ensure_element(value: Any, label: str) -> None:
    """Raise ``ValueError`` unless ``value`` belongs to ``label``'s type."""
    if label == "int":
        acceptable = isinstance(value, int) and not isinstance(value, bool)
    elif label == "float":
        acceptable = isinstance(value, float)
    elif label == "decimal":
        acceptable = isinstance(value, Decimal)
    elif label == "datetime":
        acceptable = isinstance(value, datetime)
    elif label == "date":
        acceptable = isinstance(value, date) and not isinstance(value, datetime)
    elif label == "time":
        acceptable = isinstance(value, time)
    elif label == "str":
        acceptable = isinstance(value, str)
    else:
        raise ValueError(f"Unknown range element type label: {label!r}")

    if not acceptable:
        raise ValueError(f"Range element_type {label!r} cannot hold {type(value).__name__}")


def _encode_element(value: Any, label: str) -> Any:
    """Encode one endpoint as a JSON-compatible scalar."""
    _ensure_element(value, label)
    if label in _ISO_ELEMENT_LABELS:
        return value.isoformat()
    if label == "decimal":
        return str(value)
    return value


def _decode_element(value: Any, label: str) -> Any:
    """Decode one JSON scalar back into an endpoint value."""
    if label == "int":
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError(f"Range element_type 'int' requires int, got {type(value).__name__}")
        return value
    if label == "float":
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(
                f"Range element_type 'float' requires a number, got {type(value).__name__}"
            )
        return float(value)
    if label == "decimal":
        if not isinstance(value, str):
            raise ValueError(
                "Range element_type 'decimal' requires a string, " f"got {type(value).__name__}"
            )
        try:
            return Decimal(value)
        except (InvalidOperation, ValueError) as exc:
            raise ValueError(f"Invalid Decimal range endpoint {value!r}: {exc}") from exc
    if label in _ISO_ELEMENT_LABELS:
        if not isinstance(value, str):
            raise ValueError(
                f"Range element_type {label!r} requires a string, " f"got {type(value).__name__}"
            )
        parser = {
            "datetime": datetime.fromisoformat,
            "date": date.fromisoformat,
            "time": time.fromisoformat,
        }[label]
        try:
            return parser(value)
        except ValueError as exc:
            raise ValueError(f"Invalid {label} range endpoint {value!r}: {exc}") from exc
    if label == "str":
        if not isinstance(value, str):
            raise ValueError(f"Range element_type 'str' requires str, got {type(value).__name__}")
        return value
    raise ValueError(f"Unknown range element type label: {label!r}")


def _quote_bound(text: str) -> str:
    """Quote a PostgreSQL range bound, escaping ``"`` and ``\\`` with a backslash.

    Range bounds use double quotes, not SQL string literals: PostgreSQL's
    range input parser treats a single quote as part of the bound value.
    """
    return '"' + text.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _render_literal_endpoint(value: Any) -> str:
    """Render one endpoint for a PostgreSQL range literal.

    Numeric endpoints stay bare; text and temporal endpoints are quoted with
    PostgreSQL's range-bound syntax so the literal is accepted verbatim by
    the range input parser.
    """
    if isinstance(value, bool):
        raise ValueError("bool is not a supported range endpoint")
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return repr(value)
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, (datetime, date, time)):
        return _quote_bound(value.isoformat())
    if isinstance(value, str):
        return _quote_bound(value)
    raise ValueError(f"Unsupported range endpoint type: {type(value).__name__}")


@dataclass(frozen=True)
class Range:
    """An immutable interval over a comparable scalar domain.

    ``bounds`` holds the lower and upper bracket symbols in that order.
    ``empty`` marks the empty range, which carries no endpoints.
    """

    lower: Any = None
    upper: Any = None
    bounds: str = "[)"
    empty: bool = False

    #: Stable tag used by ``AdapterJSONCodec`` in tagged mode.
    json_type_tag: ClassVar[str] = "range"

    def __post_init__(self) -> None:
        if not isinstance(self.bounds, str) or self.bounds not in VALID_BOUNDS:
            raise ValueError(f"bounds must be one of {VALID_BOUNDS}, got {self.bounds!r}")
        if self.empty:
            if self.lower is not None or self.upper is not None:
                raise ValueError("An empty range must not define lower or upper bounds")
            return
        if self.lower is not None and self.upper is not None:
            try:
                if self.lower > self.upper:
                    raise ValueError(
                        f"Range lower bound {self.lower!r} is greater than "
                        f"upper bound {self.upper!r}"
                    )
            except TypeError as exc:
                raise ValueError(
                    "Range bounds are not comparable: "
                    f"{type(self.lower).__name__} and {type(self.upper).__name__}"
                ) from exc

    def _element_type_label(self) -> str:
        """Infer the JSON element type from whichever endpoint is present."""
        if self.lower is not None:
            return _label_for_value(self.lower)
        if self.upper is not None:
            return _label_for_value(self.upper)
        raise ValueError("element_type is required for a non-empty range without explicit bounds")

    def contains(self, value: Any) -> bool:
        """Return whether ``value`` falls inside this range."""
        if self.empty:
            return False
        try:
            if self.lower is not None:
                if self.bounds[0] == "[":
                    if value < self.lower:
                        return False
                elif value <= self.lower:
                    return False
            if self.upper is not None:
                if self.bounds[1] == "]":
                    if value > self.upper:
                        return False
                elif value >= self.upper:
                    return False
        except TypeError as exc:
            raise ValueError(
                "Cannot compare range value of type " f"{type(value).__name__} with its bounds"
            ) from exc
        return True

    def to_postgres_literal(self) -> str:
        """Render the canonical PostgreSQL range literal."""
        if self.empty:
            return "empty"
        lower = "" if self.lower is None else _render_literal_endpoint(self.lower)
        upper = "" if self.upper is None else _render_literal_endpoint(self.upper)
        lower_bracket = "(" if self.lower is None else self.bounds[0]
        upper_bracket = ")" if self.upper is None else self.bounds[1]
        return f"{lower_bracket}{lower},{upper}{upper_bracket}"

    def to_json_value(self) -> Dict[str, Any]:
        """Return the lossless JSON-compatible representation."""
        if self.empty:
            return {
                "lower": None,
                "upper": None,
                "bounds": self.bounds,
                "empty": True,
                "element_type": None,
            }

        label = self._element_type_label()
        lower = None if self.lower is None else _encode_element(self.lower, label)
        upper = None if self.upper is None else _encode_element(self.upper, label)
        return {
            "lower": lower,
            "upper": upper,
            "bounds": self.bounds,
            "empty": False,
            "element_type": label,
        }

    @classmethod
    def from_json_value(cls, value: Mapping[str, Any]) -> "Range":
        """Rebuild a range from its JSON-compatible representation."""
        if not isinstance(value, MappingABC):
            raise ValueError(f"Range JSON value must be a mapping, got {type(value).__name__}")

        missing = [key for key in ("lower", "upper", "bounds", "empty") if key not in value]
        if missing:
            raise ValueError(f"Range JSON value is missing fields: {', '.join(missing)}")

        bounds = value["bounds"]
        if not isinstance(bounds, str) or bounds not in VALID_BOUNDS:
            raise ValueError(f"bounds must be one of {VALID_BOUNDS}, got {bounds!r}")

        empty = value["empty"]
        if not isinstance(empty, bool):
            raise ValueError(f"empty must be a bool, got {type(empty).__name__}")
        if empty:
            return cls(None, None, bounds, True)

        label = value.get("element_type")
        if label is None:
            raise ValueError("element_type is required for a non-empty range")
        if label not in ELEMENT_TYPE_LABELS:
            raise ValueError(f"Unknown range element_type: {label!r}")

        lower = None if value["lower"] is None else _decode_element(value["lower"], label)
        upper = None if value["upper"] is None else _decode_element(value["upper"], label)
        return cls(lower, upper, bounds, False)


def _sort_key(range_value: Range) -> Tuple[Tuple[int, Any], Tuple[int, Any], str]:
    """Sort unbounded lower endpoints first and unbounded upper ones last."""
    lower_key = (0, None) if range_value.lower is None else (1, range_value.lower)
    upper_key = (1, None) if range_value.upper is None else (0, range_value.upper)
    return (lower_key, upper_key, range_value.bounds)


def _sort_ranges(ranges: Sequence[Range]) -> List[Range]:
    try:
        return sorted(ranges, key=_sort_key)
    except TypeError as exc:
        raise ValueError(f"Cannot sort multirange with incomparable bounds: {exc}") from exc


def _can_merge(left: Range, right: Range) -> bool:
    """Return whether two ranges overlap or touch without leaving a gap."""
    if left.upper is None:
        return True
    if right.lower is None:
        return True
    try:
        if right.lower < left.upper:
            return True
        if right.lower > left.upper:
            return False
    except TypeError as exc:
        raise ValueError(
            "Cannot compare multirange bounds: "
            f"{type(left.upper).__name__} and {type(right.lower).__name__}"
        ) from exc
    # Equal endpoints merge when at least one side includes the shared point.
    return left.bounds[1] == "]" or right.bounds[0] == "["


def _merge_two(left: Range, right: Range) -> Range:
    """Merge two overlapping/touching ranges, taking the wider endpoints."""
    if left.lower is None or right.lower is None:
        lower = None
        lower_inclusive = False
    else:
        try:
            if left.lower < right.lower:
                lower = left.lower
                lower_inclusive = left.bounds[0] == "["
            elif right.lower < left.lower:
                lower = right.lower
                lower_inclusive = right.bounds[0] == "["
            else:
                lower = left.lower
                lower_inclusive = left.bounds[0] == "[" or right.bounds[0] == "["
        except TypeError as exc:
            raise ValueError(
                "Cannot compare multirange lower bounds: "
                f"{type(left.lower).__name__} and {type(right.lower).__name__}"
            ) from exc

    if left.upper is None or right.upper is None:
        upper = None
        upper_inclusive = False
    else:
        try:
            if left.upper > right.upper:
                upper = left.upper
                upper_inclusive = left.bounds[1] == "]"
            elif right.upper > left.upper:
                upper = right.upper
                upper_inclusive = right.bounds[1] == "]"
            else:
                upper = left.upper
                upper_inclusive = left.bounds[1] == "]" or right.bounds[1] == "]"
        except TypeError as exc:
            raise ValueError(
                "Cannot compare multirange upper bounds: "
                f"{type(left.upper).__name__} and {type(right.upper).__name__}"
            ) from exc

    bounds = ("[" if lower_inclusive else "(") + ("]" if upper_inclusive else ")")
    return Range(lower, upper, bounds, False)


def _merge_ranges(ranges: Sequence[Range]) -> List[Range]:
    merged: List[Range] = []
    for current in ranges:
        if not merged:
            merged.append(current)
            continue
        if _can_merge(merged[-1], current):
            merged[-1] = _merge_two(merged[-1], current)
        else:
            merged.append(current)
    return merged


@dataclass(frozen=True)
class Multirange:
    """An immutable, canonical collection of disjoint ranges.

    Construction always normalizes the input: empty ranges are dropped,
    members are sorted, and overlapping or touching ranges are merged.  The
    canonical form makes equality and hashing stable.
    """

    ranges: Tuple[Range, ...] = ()

    #: Stable tag used by ``AdapterJSONCodec`` in tagged mode.
    json_type_tag: ClassVar[str] = "multirange"

    def __post_init__(self) -> None:
        if not isinstance(self.ranges, (tuple, list)):
            raise TypeError(f"ranges must be a tuple or list, got {type(self.ranges).__name__}")
        materialized: List[Range] = []
        for item in self.ranges:
            if not isinstance(item, Range):
                raise TypeError(
                    "Multirange members must be Range instances, " f"got {type(item).__name__}"
                )
            if not item.empty:
                materialized.append(item)

        ordered = _sort_ranges(materialized)
        merged = _merge_ranges(ordered)
        object.__setattr__(self, "ranges", tuple(_sort_ranges(merged)))

    def to_postgres_literal(self) -> str:
        """Render the canonical PostgreSQL multirange literal."""
        if not self.ranges:
            return "{}"
        inner = ",".join(item.to_postgres_literal() for item in self.ranges)
        # ``inner`` already contains the per-range brackets.
        return "{" + inner + "}"

    def to_json_value(self) -> List[Any]:
        """Return a JSON-compatible array of range representations."""
        return [r.to_json_value() for r in self.ranges]

    @classmethod
    def from_json_value(cls, value: Sequence[Any]) -> "Multirange":
        """Rebuild a multirange from an array of range JSON values."""
        if isinstance(value, (str, bytes)) or not isinstance(value, (list, tuple)):
            raise ValueError(f"Multirange JSON value must be an array, got {type(value).__name__}")
        ranges = [Range.from_json_value(item) for item in value]
        labels = {item._element_type_label() for item in ranges if not item.empty}
        if len(labels) > 1:
            raise ValueError(
                "Multirange members must share one element_type, " f"got {sorted(labels)}"
            )
        return cls(tuple(ranges))


class RangeAdapterBase(BaseSQLTypeAdapter):
    """Base adapter for neutral :class:`Range` and :class:`Multirange` values.

    The base class dispatches encoding by value type and validates decoding
    results against the requested neutral type.  Backends derive from it and
    implement :meth:`_encode` and :meth:`_decode`; failures raised by those
    hooks are wrapped in :class:`TypeConversionError`.
    """

    neutral_type: ClassVar[Optional[type]] = Range

    def _do_to_database(
        self, value: Any, target_type: Type, options: Optional[Dict[str, Any]]
    ) -> Any:
        if not isinstance(value, (Range, Multirange)):
            self._conversion_error(value, "expected Range or Multirange", target=Range)
        neutral: Union[Range, Multirange] = value
        neutral_type: type = Multirange if isinstance(value, Multirange) else Range
        try:
            return self._encode(neutral, target_type, options)
        except TypeConversionError:
            raise
        except (TypeError, ValueError) as exc:
            self._conversion_error(value, str(exc), target=neutral_type)

    def _do_from_database(
        self, value: Any, target_type: Type, options: Optional[Dict[str, Any]]
    ) -> Any:
        if isinstance(value, Range):
            if target_type is Multirange:
                self._conversion_error(value, "expected Multirange, got Range", target=Multirange)
            return value
        if isinstance(value, Multirange):
            if target_type is Range:
                self._conversion_error(value, "expected Range, got Multirange", target=Range)
            return value

        expected = target_type if target_type in (Range, Multirange) else None
        try:
            result = self._decode(value, target_type, options)
        except TypeConversionError:
            raise
        except (TypeError, ValueError) as exc:
            self._conversion_error(value, str(exc), target=expected)

        if not isinstance(result, (Range, Multirange)):
            self._conversion_error(
                value,
                "decoder must return Range or Multirange, " f"got {type(result).__name__}",
                target=expected,
            )
        if expected is Range and not isinstance(result, Range):
            self._conversion_error(value, "expected Range, got Multirange", target=Range)
        if expected is Multirange and not isinstance(result, Multirange):
            self._conversion_error(value, "expected Multirange, got Range", target=Multirange)
        return result

    def _encode(
        self,
        value: Union[Range, Multirange],
        target_type: Type,
        options: Optional[Dict[str, Any]],
    ) -> Any:
        """Encode a neutral range value into the backend/driver value."""
        raise NotImplementedError

    def _decode(
        self, value: Any, target_type: Type, options: Optional[Dict[str, Any]]
    ) -> Union[Range, Multirange]:
        """Decode a backend/driver value into a neutral range value."""
        raise NotImplementedError
