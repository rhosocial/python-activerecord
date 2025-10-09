# tests/rhosocial/activerecord_test/feature/backend/common/test_helpers_json.py
import pytest
import json
from datetime import datetime, date
from decimal import Decimal
from unittest.mock import patch

from rhosocial.activerecord.backend.helpers import (
    safe_json_dumps,
    safe_json_loads,
    array_converter
)
from rhosocial.activerecord.backend.errors import TypeConversionError


class TestSafeJsonDumps:
    def test_safe_json_dumps_basic(self):
        # Test basic value serialization
        result = safe_json_dumps({"name": "John", "age": 30})
        parsed = json.loads(result)
        assert parsed["name"] == "John"
        assert parsed["age"] == 30

    def test_safe_json_dumps_decimal(self):
        # Test Decimal serialization
        result = safe_json_dumps({"amount": Decimal("123.45")})
        parsed = json.loads(result)
        assert parsed["amount"] == "123.45"

    def test_safe_json_dumps_datetime(self):
        # Test datetime serialization
        dt = datetime(2022, 7, 25, 14, 30, 0)
        result = safe_json_dumps({"timestamp": dt})
        parsed = json.loads(result)
        assert parsed["timestamp"] == "2022-07-25T14:30:00"

    def test_safe_json_dumps_date(self):
        # Test date serialization
        d = date(2022, 7, 25)
        result = safe_json_dumps({"date": d})
        parsed = json.loads(result)
        assert parsed["date"] == "2022-07-25"

    def test_safe_json_dumps_complex_structure(self):
        # Test serialization of complex structure
        data = {
            "name": "John",
            "transactions": [
                {"amount": Decimal("123.45"), "date": date(2022, 7, 25)},
                {"amount": Decimal("67.89"), "date": date(2022, 7, 26)}
            ]
        }
        result = safe_json_dumps(data)
        parsed = json.loads(result)
        assert parsed["name"] == "John"
        assert parsed["transactions"][0]["amount"] == "123.45"
        assert parsed["transactions"][0]["date"] == "2022-07-25"
        assert parsed["transactions"][1]["amount"] == "67.89"
        assert parsed["transactions"][1]["date"] == "2022-07-26"

    def test_safe_json_dumps_non_serializable(self):
        # Test serialization of non-serializable object
        class NonSerializable:
            pass

        with pytest.raises(TypeConversionError):
            safe_json_dumps({"obj": NonSerializable()})

    def test_safe_json_dumps_error_handling(self):
        # Test error handling during serialization
        with patch('json.dumps', side_effect=Exception("JSON error")):
            with pytest.raises(TypeConversionError):
                safe_json_dumps({"name": "John"})


class TestSafeJsonLoads:
    def test_safe_json_loads_basic(self):
        # Test basic JSON parsing
        result = safe_json_loads('{"name": "John", "age": 30}')
        assert result["name"] == "John"
        assert result["age"] == 30

    def test_safe_json_loads_non_string(self):
        # Test passing a non-string value
        original = {"name": "John", "age": 30}
        result = safe_json_loads(original)
        assert result is original

    def test_safe_json_loads_invalid_json(self):
        # Test parsing invalid JSON
        with pytest.raises(TypeConversionError):
            safe_json_loads('{"name": "John", "age": }')

    def test_safe_json_loads_empty_string(self):
        # Test parsing an empty string
        with pytest.raises(TypeConversionError):
            safe_json_loads('')

    def test_safe_json_loads_list(self):
        # Test parsing JSON list
        result = safe_json_loads('[1, 2, 3]')
        assert result == [1, 2, 3]

    def test_safe_json_loads_error_handling(self):
        # Test error handling during parsing
        with patch('json.loads', side_effect=Exception("JSON error")):
            with pytest.raises(TypeConversionError):
                safe_json_loads('{"name": "John"}')


class TestArrayConverter:
    def test_array_converter_list(self):
        # Test converting a list
        result = array_converter([1, 2, 3])
        parsed = json.loads(result)
        assert parsed == [1, 2, 3]

    def test_array_converter_tuple(self):
        # Test converting a tuple
        result = array_converter((1, 2, 3))
        parsed = json.loads(result)
        assert parsed == [1, 2, 3]

    def test_array_converter_empty_list(self):
        # Test converting an empty list
        result = array_converter([])
        parsed = json.loads(result)
        assert parsed == []

    def test_array_converter_with_complex_types(self):
        # Test converting a list with complex types
        data = [
            {"amount": Decimal("123.45"), "date": date(2022, 7, 25)},
            {"amount": Decimal("67.89"), "date": date(2022, 7, 26)}
        ]
        result = array_converter(data)
        parsed = json.loads(result)
        assert parsed[0]["amount"] == "123.45"
        assert parsed[0]["date"] == "2022-07-25"
        assert parsed[1]["amount"] == "67.89"
        assert parsed[1]["date"] == "2022-07-26"

    def test_array_converter_non_array(self):
        # Test converting a non-array value
        with pytest.raises(TypeConversionError):
            array_converter("not an array")

    def test_array_converter_none(self):
        # Test converting None
        with pytest.raises(TypeConversionError):
            array_converter(None)
