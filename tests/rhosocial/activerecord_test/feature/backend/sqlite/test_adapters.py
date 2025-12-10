# tests/rhosocial/activerecord_test/feature/backend/sqlite/test_adapters.py
import datetime
import decimal
import json
import uuid

import pytest

from rhosocial.activerecord.backend.errors import TypeConversionError
from rhosocial.activerecord.backend.impl.sqlite.adapters import (
    SQLiteBlobAdapter,
    SQLiteJSONAdapter,
    SQLiteUUIDAdapter,
)

# --- Start of new imports ---
from enum import Enum as PyEnum
from typing import Optional, Union

# Import the generic adapters from the core library
from rhosocial.activerecord.backend.type_adapter import (
    DateTimeAdapter,
    EnumAdapter,
    DecimalAdapter,
    BooleanAdapter,
    ArrayAdapter,
    BaseSQLTypeAdapter,
    UUIDAdapter as GenericUUIDAdapter,
)
# --- End of new imports ---


class TestSQLiteBlobAdapter:
    @pytest.fixture
    def adapter(self):
        return SQLiteBlobAdapter()

    def test_to_database_bytes(self, adapter):
        """Test converting bytes to a database-compatible format."""
        test_bytes = b'\x01\x02\x03'
        assert adapter.to_database(test_bytes, bytes) == test_bytes

    def test_to_database_str(self, adapter):
        """Test converting a string to a database-compatible format."""
        test_str = "hello"
        assert adapter.to_database(test_str, bytes) == b'hello'

    def test_to_database_invalid_type_raises_error(self, adapter):
        """Test that converting an unsupported type raises TypeConversionError."""
        with pytest.raises(TypeConversionError, match="Cannot convert int to BLOB"):
            adapter.to_database(123, bytes)

    def test_from_database_bytes(self, adapter):
        """Test converting bytes from the database to a Python object."""
        test_bytes = b'\x01\x02\x03'
        assert adapter.from_database(test_bytes, bytes) == test_bytes

    def test_from_database_str(self, adapter):
        """Test converting a string from the database to a Python object."""
        test_str = "world"
        assert adapter.from_database(test_str, bytes) == b'world'

    def test_from_database_invalid_type_raises_error(self, adapter):
        """Test that converting an unsupported type from the database raises TypeConversionError."""
        with pytest.raises(TypeConversionError, match="Cannot convert database value of type int to bytes"):
            adapter.from_database(456, bytes)


class TestSQLiteJSONAdapter:
    @pytest.fixture
    def adapter(self):
        return SQLiteJSONAdapter()

    def test_to_database_with_extended_types(self, adapter):
        """Test serializing a complex dictionary with various types."""
        now = datetime.datetime.now()
        test_uuid = uuid.uuid4()
        data = {
            "datetime": now,
            "date": now.date(),
            "time": now.time(),
            "uuid": test_uuid,
            "decimal": decimal.Decimal("123.45"),
            "set": {1, 2, 3}
        }
        
        result_str = adapter.to_database(data, str)
        result_dict = json.loads(result_str)

        assert result_dict["datetime"] == now.isoformat()
        assert result_dict["uuid"] == str(test_uuid)
        assert result_dict["decimal"] == 123.45  # Converted to float
        assert sorted(result_dict["set"]) == [1, 2, 3]

    def test_to_database_unserializable_raises_error(self, adapter):
        """Test that an object that cannot be serialized raises TypeConversionError."""
        data = {"unserializable": object()}
        with pytest.raises(TypeConversionError, match="Failed to serialize object to JSON"):
            adapter.to_database(data, str)

    def test_from_database_valid_json(self, adapter):
        """Test deserializing a valid JSON string."""
        json_str = '{"key": "value", "number": 123}'
        expected_dict = {"key": "value", "number": 123}
        assert adapter.from_database(json_str, dict) == expected_dict

    def test_from_database_malformed_json_raises_error(self, adapter):
        """Test that a malformed JSON string raises TypeConversionError."""
        malformed_str = '{"key": "value",,}'
        with pytest.raises(TypeConversionError, match="Failed to decode JSON string"):
            adapter.from_database(malformed_str, dict)

    def test_from_database_non_string_raises_error(self, adapter):
        """Test that a non-string input raises TypeConversionError."""
        with pytest.raises(TypeConversionError, match="Cannot decode JSON from non-string type: int"):
            adapter.from_database(123, dict)


class TestSQLiteUUIDAdapter:
    @pytest.fixture
    def adapter(self):
        return SQLiteUUIDAdapter()

    @pytest.fixture
    def sample_uuid(self):
        return uuid.uuid4()

    def test_to_database_as_str(self, adapter, sample_uuid):
        """Test converting a UUID to a string."""
        assert adapter.to_database(sample_uuid, str) == str(sample_uuid)

    def test_to_database_as_bytes(self, adapter, sample_uuid):
        """Test converting a UUID to bytes."""
        assert adapter.to_database(sample_uuid, bytes) == sample_uuid.bytes

    def test_to_database_invalid_target_raises_error(self, adapter, sample_uuid):
        """Test converting a UUID to an unsupported type raises TypeConversionError."""
        with pytest.raises(TypeConversionError, match="Cannot convert UUID to unsupported target type: int"):
            adapter.to_database(sample_uuid, int)

    def test_from_database_str(self, adapter, sample_uuid):
        """Test converting a UUID string from the database."""
        uuid_str = str(sample_uuid)
        assert adapter.from_database(uuid_str, uuid.UUID) == sample_uuid

    def test_from_database_bytes(self, adapter, sample_uuid):
        """Test converting UUID bytes from the database."""
        uuid_bytes = sample_uuid.bytes
        assert adapter.from_database(uuid_bytes, uuid.UUID) == sample_uuid

    def test_from_database_invalid_str_raises_error(self, adapter):
        """Test that an invalid UUID string raises TypeConversionError."""
        with pytest.raises(TypeConversionError, match="Could not convert value of type str to UUID"):
            adapter.from_database("not-a-uuid", uuid.UUID)

    def test_from_database_invalid_type_raises_error(self, adapter):
        """Test that an unsupported type from the database raises TypeConversionError."""
        with pytest.raises(TypeConversionError, match="Cannot convert int to UUID"):
            adapter.from_database(123, uuid.UUID)


# --- Tests for Generic Adapters ---

class TestGenericUUIDAdapter:
    @pytest.fixture
    def adapter(self):
        return GenericUUIDAdapter()

    @pytest.fixture
    def sample_uuid(self):
        return uuid.uuid4()
        
    def test_from_database_with_uuid_object(self, adapter, sample_uuid):
        """Tests that the adapter is idempotent and handles existing UUID objects."""
        assert adapter.from_database(sample_uuid, uuid.UUID) == sample_uuid
        
    def test_unsupported_to_database_conversion_raises_error(self, adapter, sample_uuid):
        """Test that converting to an unsupported type raises TypeError."""
        with pytest.raises(TypeError, match="Cannot convert UUID to int"):
            adapter.to_database(sample_uuid, int)
            
    def test_unsupported_from_database_conversion_raises_error(self, adapter):
        """Test that converting from an unsupported type raises TypeError."""
        with pytest.raises(TypeError, match="Cannot convert int to UUID"):
            adapter.from_database(123, uuid.UUID)


class TestDateTimeAdapter:
    @pytest.fixture
    def adapter(self):
        return DateTimeAdapter()

    def test_date_to_int(self, adapter):
        """Test converting date to int timestamp."""
        d = datetime.date(2024, 1, 1)
        # Midnight UTC timestamp for that date
        expected_ts = int(datetime.datetime(2024, 1, 1, 0, 0).timestamp())
        assert adapter.to_database(d, int) == expected_ts

    def test_time_to_str(self, adapter):
        """Test converting time to ISO format string."""
        t = datetime.time(14, 30, 5)
        assert adapter.to_database(t, str) == "14:30:05"

    def test_unsupported_time_conversion(self, adapter):
        """Test that converting time to int raises TypeError."""
        t = datetime.time(14, 30, 5)
        with pytest.raises(TypeError):
            adapter.to_database(t, int)
            
    def test_from_database_unsupported(self, adapter):
        """Test that from_database raises TypeError for unsupported conversions."""
        with pytest.raises(ValueError):
            adapter.from_database("test", datetime.time) # Note: fromisoformat is strict
        with pytest.raises(TypeError):
            adapter.from_database(b"test", datetime.datetime)


class TestEnumAdapter:
    class Status(PyEnum):
        PENDING = 1
        COMPLETED = 2
        FAILED = 3

    @pytest.fixture
    def adapter(self):
        return EnumAdapter()

    def test_to_database(self, adapter):
        """Test converting Enum members to database values."""
        assert adapter.to_database(self.Status.COMPLETED, int) == 2
        assert adapter.to_database(self.Status.COMPLETED, str) == "COMPLETED"

    def test_from_database(self, adapter):
        """Test converting database values to Enum members."""
        assert adapter.from_database(2, self.Status) == self.Status.COMPLETED
        assert adapter.from_database("COMPLETED", self.Status) == self.Status.COMPLETED

    def test_invalid_conversions(self, adapter):
        """Test invalid conversions for EnumAdapter raise errors."""
        with pytest.raises(TypeError):
            adapter.to_database(self.Status.PENDING, float)
        with pytest.raises(KeyError): # Enum['invalid'] raises KeyError
            adapter.from_database("INVALID", self.Status)
        with pytest.raises(ValueError): # Enum(99) raises ValueError
            adapter.from_database(99, self.Status)
        with pytest.raises(TypeError):
            adapter.from_database(1.5, self.Status)


class TestDecimalAdapter:
    @pytest.fixture
    def adapter(self):
        return DecimalAdapter()

    def test_to_and_from_database(self, adapter):
        """Test basic to/from database conversions for Decimal."""
        val = decimal.Decimal("123.456")
        assert adapter.to_database(val, str) == "123.456"
        assert adapter.to_database(val, float) == 123.456
        assert adapter.from_database("123.456", decimal.Decimal) == val
        assert adapter.from_database(123.456, decimal.Decimal) == val

    def test_quantization(self, adapter):
        """Test precision and rounding options."""
        val = decimal.Decimal("123.456789")
        options = {"precision": "0.01", "rounding": decimal.ROUND_DOWN}
        expected = decimal.Decimal("123.45")
        assert adapter.from_database("123.456789", decimal.Decimal, options) == expected

    def test_invalid_conversions(self, adapter):
        """Test invalid conversions for DecimalAdapter."""
        with pytest.raises(TypeError):
            adapter.to_database(decimal.Decimal("1"), int)
        with pytest.raises(decimal.InvalidOperation):
            adapter.from_database("not-a-decimal", decimal.Decimal)


class TestBooleanAdapter:
    @pytest.fixture
    def adapter(self):
        return BooleanAdapter()
        
    def test_to_database_str(self, adapter):
        assert adapter.to_database(True, str) == "true"
        assert adapter.to_database(False, str) == "false"

    def test_from_database_str(self, adapter):
        assert adapter.from_database("true", bool) is True
        assert adapter.from_database("TRUE", bool) is True
        assert adapter.from_database("false", bool) is False
        # Note: any string other than 'true' (case-insensitive) becomes False
        assert adapter.from_database("anything_else", bool) is False

    def test_invalid_from_database(self, adapter):
        with pytest.raises(TypeError):
            adapter.from_database(b"true", bool)


class TestArrayAdapter:
    @pytest.fixture
    def adapter(self):
        return ArrayAdapter()

    def test_to_database(self, adapter):
        assert adapter.to_database([1, "a", True], str) == '[1, "a", true]'
        assert adapter.to_database((1, "a"), str) == '[1, "a"]'
        # Order is not guaranteed for sets, so we check content
        result_set = json.loads(adapter.to_database({1, "a"}, str))
        assert set(result_set) == {1, "a"}

    def test_to_database_invalid_type(self, adapter):
        with pytest.raises(TypeError, match="Cannot convert dict to JSON array string"):
            adapter.to_database({"a": 1}, str)
            
    def test_from_database(self, adapter):
        assert adapter.from_database('[1, "a", true]', list) == [1, "a", True]


class TestBaseSQLTypeAdapter:
    @pytest.fixture
    def adapter(self):
        # Use a concrete implementation for testing base class logic
        return DateTimeAdapter()

    def test_from_database_with_optional_type(self, adapter):
        """Test that from_database correctly handles Optional[T] by unwrapping it."""
        val = "2024-01-01T12:00:00"
        # The target type is Optional[datetime], which is Union[datetime, None]
        result = adapter.from_database(val, Optional[datetime.datetime])
        assert isinstance(result, datetime.datetime)
        assert result == datetime.datetime(2024, 1, 1, 12, 0, 0)
        
    def test_from_database_with_none(self, adapter):
        """Test that from_database returns None if the input value is None."""
        assert adapter.from_database(None, datetime.datetime) is None
        assert adapter.from_database(None, Optional[datetime.datetime]) is None

    def test_to_database_with_none(self, adapter):
        """Test that to_database returns None if the input value is None."""
        assert adapter.to_database(None, str) is None