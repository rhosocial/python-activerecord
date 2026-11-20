# src/rhosocial/activerecord/backend/adapters/vector.py
"""Neutral dense-vector type and its adapter base.

This module provides a driver-independent representation of a dense numeric
vector (for example ``pgvector``, MySQL ``VECTOR``, or a JSON array column)
plus a base adapter that backend adapters derive from. It depends only on the
standard library; no array or database driver type is involved.
"""

import math
from abc import abstractmethod
from dataclasses import dataclass, field
from typing import Any, ClassVar, Dict, List, Optional, Sequence, Tuple, Type

from ..errors import TypeConversionError
from ..type_adapter import BaseSQLTypeAdapter

#: JSON spellings for non-finite floats in the canonical representation.
_NON_FINITE_VALUES = {
    "NaN": float("nan"),
    "Infinity": float("inf"),
    "-Infinity": float("-inf"),
}


def _to_json_scalar(value: Any) -> Any:
    """Return a JSON-safe scalar for one vector component."""
    if isinstance(value, float) and not math.isfinite(value):
        if math.isnan(value):
            return "NaN"
        return "Infinity" if value > 0 else "-Infinity"
    return value


@dataclass(frozen=True)
class Vector:
    """An immutable dense vector of numbers.

    ``values`` must be a non-empty sequence of ``int``/``float`` values. Non-
    finite components (NaN and infinities) are rejected unless the vector is
    built with ``allow_non_finite=True``; that flag is a construction
    permission only, so it does not participate in equality or hashing. The
    sequence container itself is normalized to a tuple, which keeps the value
    canonical and hashable.

    The vector's dimension is not constrained here: a column's DDL decides it.
    """

    #: Stable tag used by ``AdapterJSONCodec`` for tagged envelopes.
    json_type_tag: ClassVar[str] = "vector"

    values: Tuple[float, ...]
    allow_non_finite: bool = field(default=False, compare=False)

    def __post_init__(self) -> None:
        if not isinstance(self.allow_non_finite, bool):
            raise TypeError(
                "allow_non_finite must be bool, " f"got {type(self.allow_non_finite).__name__}"
            )
        if not isinstance(self.values, (tuple, list)):
            raise TypeError(
                "values must be a tuple or list of numbers, " f"got {type(self.values).__name__}"
            )
        if not self.values:
            raise ValueError("values must contain at least one number")

        checked: List[Any] = []
        for index, item in enumerate(self.values):
            if isinstance(item, bool) or not isinstance(item, (int, float)):
                raise TypeError(
                    f"values[{index}] must be int or float, " f"got {type(item).__name__}"
                )
            if not self.allow_non_finite and not math.isfinite(item):
                raise ValueError(
                    f"values[{index}] is not finite; " "pass allow_non_finite=True to accept it"
                )
            checked.append(item)
        object.__setattr__(self, "values", tuple(checked))

    @property
    def dimension(self) -> int:
        """Number of components in this vector."""
        return len(self.values)

    def to_json_value(self) -> List[Any]:
        """Return the canonical JSON representation of this vector.

        The result is a list of numbers, with non-finite components spelled
        ``"NaN"``, ``"Infinity"``, or ``"-Infinity"``.
        """
        return [_to_json_scalar(value) for value in self.values]

    @classmethod
    def from_json_value(cls, value: Sequence[Any]) -> "Vector":
        """Rebuild a :class:`Vector` from its JSON representation.

        Accepts a list/tuple of numbers or non-finite names. A vector that
        contains a non-finite component is rebuilt with
        ``allow_non_finite=True`` so the round-trip succeeds.
        """
        if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, (list, tuple)):
            raise TypeError(
                "vector JSON value must be a list of numbers, " f"got {type(value).__name__}"
            )

        numbers: List[Any] = []
        allow_non_finite = False
        for index, item in enumerate(value):
            if isinstance(item, str):
                if item not in _NON_FINITE_VALUES:
                    raise ValueError(
                        f"values[{index}] is not a recognized non-finite name: {item!r}"
                    )
                numbers.append(_NON_FINITE_VALUES[item])
                allow_non_finite = True
            elif isinstance(item, bool) or not isinstance(item, (int, float)):
                raise TypeError(
                    f"values[{index}] must be int, float, or a non-finite name, "
                    f"got {type(item).__name__}"
                )
            else:
                if isinstance(item, float) and not math.isfinite(item):
                    allow_non_finite = True
                numbers.append(item)
        return cls(tuple(numbers), allow_non_finite=allow_non_finite)


class VectorAdapterBase(BaseSQLTypeAdapter):
    """Base adapter for backends exposing dense vectors.

    Backends derive from this class and implement :meth:`_encode` and
    :meth:`_decode`. Conversion failures raised by those hooks are wrapped in
    :class:`TypeConversionError` by the base class.
    """

    neutral_type = Vector

    def _do_to_database(
        self, value: Any, target_type: Type, options: Optional[Dict[str, Any]]
    ) -> Any:
        vector = self._coerce_vector(value)
        try:
            return self._encode(vector, target_type, options)
        except TypeConversionError:
            raise
        except (TypeError, ValueError, OverflowError) as exc:
            self._conversion_error(value, str(exc))

    def _do_from_database(
        self, value: Any, target_type: Type, options: Optional[Dict[str, Any]]
    ) -> Any:
        try:
            vector = self._decode(value, options)
        except TypeConversionError:
            raise
        except (TypeError, ValueError, OverflowError) as exc:
            self._conversion_error(value, str(exc))

        if not isinstance(vector, Vector):
            self._conversion_error(
                value,
                "decoder must return Vector, " f"got {type(vector).__name__}",
            )
        return vector

    def _coerce_vector(self, value: Any) -> Vector:
        """Convert a supported Python value into a :class:`Vector`."""
        if isinstance(value, Vector):
            return value
        if isinstance(value, (list, tuple)):
            try:
                return Vector.from_json_value(value)
            except (TypeError, ValueError) as exc:
                self._conversion_error(value, str(exc))
        self._conversion_error(
            value,
            "expected Vector or a sequence of numbers",
        )

    @abstractmethod
    def _encode(
        self,
        vector: Vector,
        target_type: Type,
        options: Optional[Dict[str, Any]],
    ) -> Any:
        """Encode a neutral vector into the backend/driver value."""
        raise NotImplementedError

    @abstractmethod
    def _decode(self, value: Any, options: Optional[Dict[str, Any]]) -> Vector:
        """Decode a backend/driver value into a neutral vector."""
        raise NotImplementedError
