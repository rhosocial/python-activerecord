# tests/rhosocial/activerecord_test/feature/backend/schema/test_snapshot_data_type_serde.py
"""
Cover DataType serialization helpers and generic plain-tree conversion
in backend/schema/snapshot.py: _data_type_to_dict / _data_type_from_dict,
_to_plain / _from_plain round-trips for every supported leaf kind.
"""

from datetime import datetime, timezone
from decimal import Decimal
from enum import Enum
from typing import Optional

import pytest

from rhosocial.activerecord.backend.expression.types import (
    DecimalType,
    IntegerType,
    TextType,
    TimestampType,
    VarCharType,
)
from rhosocial.activerecord.backend.schema.snapshot import (
    _data_type_from_dict,
    _data_type_to_dict,
    _from_plain,
    _to_plain,
)
from rhosocial.activerecord.backend.introspection.types import ColumnNullable


class TestDataTypeSerde:
    @pytest.mark.parametrize(
        "dt",
        [
            IntegerType(),
            TextType(),
            VarCharType(length=128),
            DecimalType(precision=10, scale=2),
            TimestampType(),
        ],
    )
    def test_roundtrip(self, dt):
        d = _data_type_to_dict(dt)
        assert d["type"].endswith(type(dt).__name__)
        restored = _data_type_from_dict(d)
        assert type(restored) is type(dt)
        assert _data_type_to_dict(restored) == d

    def test_nested_params(self):
        # VarCharType.length is a plain int; DecimalType has two numeric params.
        d = _data_type_to_dict(DecimalType(precision=12, scale=4))
        assert d["params"]["precision"] == 12
        assert d["params"]["scale"] == 4
        restored = _data_type_from_dict(d)
        assert restored.precision == 12
        assert restored.scale == 4


class TestToPlain:
    def test_scalars(self):
        assert _to_plain(None) is None
        assert _to_plain("x") == "x"
        assert _to_plain(1) == 1
        assert _to_plain(1.5) == 1.5
        assert _to_plain(True) is True

    def test_datetime(self):
        dt = datetime(2026, 9, 2, tzinfo=timezone.utc)
        assert _to_plain(dt) == dt.isoformat()

    def test_enum(self):
        assert _to_plain(ColumnNullable.NOT_NULL) == "NOT_NULL"

    def test_tuple_list_dict(self):
        assert _to_plain((1, 2)) == [1, 2]
        assert _to_plain([1, "a"]) == [1, "a"]
        assert _to_plain({"k": 1}) == {"k": 1}

    def test_dataclass_and_datatype(self):
        p = _to_plain(IntegerType())
        assert p["type"].endswith("IntegerType")

    def test_decimal_passthrough(self):
        # Decimal is not JSON-native but has no special branch; ensure no crash
        _to_plain(Decimal("1.2"))


class TestFromPlain:
    def test_none(self):
        assert _from_plain(str, None) is None

    def test_scalar(self):
        assert _from_plain(str, "x") == "x"
        assert _from_plain(int, 3) == 3

    def test_list(self):
        assert _from_plain(list, [1, 2]) == [1, 2]

    def test_dict_plain(self):
        assert _from_plain(dict, {"a": 1}) == {"a": 1}

    def test_datatype_dict(self):
        d = _data_type_to_dict(VarCharType(length=8))
        restored = _from_plain(object, d)
        assert isinstance(restored, VarCharType)
        assert restored.length == 8
