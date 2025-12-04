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
