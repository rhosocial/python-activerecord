# tests/rhosocial/activerecord_test/feature/backend/sqlite2/test_type_adaption.py
import json
from datetime import datetime
import uuid # Needed for UUID adapter test, though not directly used in these specific tests
from decimal import Decimal # Needed for Decimal adapter test

import pytest

from rhosocial.activerecord.backend.errors import TypeConversionError
from rhosocial.activerecord.backend.type_adapter import (
    BooleanAdapter,
    DateTimeAdapter,
    ArrayAdapter, # Directly instantiate as it's not default registered
    JSONAdapter,
    UUIDAdapter,
    DecimalAdapter
)


def test_boolean_adaption(db):
    """Test boolean value adaptation from Python bool to database int."""
    bool_adapter = db.adapter_registry.get_adapter(bool, int)
    assert bool_adapter.to_database(True, int) == 1
    assert bool_adapter.to_database(False, int) == 0

    # Test from database
    assert bool_adapter.from_database(1, bool) is True
    assert bool_adapter.from_database(0, bool) is False


def test_datetime_adaption(db):
    """Test datetime adaptation from Python datetime to database string."""
    datetime_adapter = db.adapter_registry.get_adapter(datetime, str)
    
    now = datetime.now().replace(microsecond=0) # SQLite often doesn't store microseconds reliably in TEXT
    converted_to_db = datetime_adapter.to_database(now, str)
    
    assert isinstance(converted_to_db, str)
    
    # Test from database (assuming ISO format for TEXT)
    converted_from_db = datetime_adapter.from_database(converted_to_db, datetime)
    assert isinstance(converted_from_db, datetime)
    assert converted_from_db == now


def test_array_adaption(db):
    """Test array adaptation from Python list to database JSON string."""
    # ArrayAdapter is not registered by default, so instantiate directly
    array_adapter = ArrayAdapter() 
    data = [1, 2, "hello", {"key": "value"}]
    converted_to_db = array_adapter.to_database(data, str)
    assert isinstance(converted_to_db, str)
    assert json.loads(converted_to_db) == data

    # Test from database
    converted_from_db = array_adapter.from_database(converted_to_db, list)
    assert isinstance(converted_from_db, list)
    assert converted_from_db == data


def test_invalid_array_adaption(db):
    """Test invalid array adaptation with ArrayAdapter."""
    array_adapter = ArrayAdapter()
    with pytest.raises(TypeError): # Changed from TypeConversionError to TypeError
        array_adapter.to_database(123, str) # ArrayAdapter expects list, tuple, etc.


def test_json_adaption(db):
    """Test JSON adaptation from Python dict/list to database JSON string."""
    # JSONAdapter is registered by default
    json_adapter = db.adapter_registry.get_adapter(dict, str)
    data = {"name": "test", "value": 123, "list": [1,2]}
    converted_to_db = json_adapter.to_database(data, str)
    assert isinstance(converted_to_db, str)
    assert json.loads(converted_to_db) == data

    # Test from database
    converted_from_db = json_adapter.from_database(converted_to_db, dict)
    assert isinstance(converted_from_db, dict)
    assert converted_from_db == data


def test_uuid_adaption(db):
    """Test UUID adaptation from Python UUID to database string."""
    # Standard UUIDAdapter is registered by default
    uuid_adapter = db.adapter_registry.get_adapter(uuid.UUID, str)
    test_uuid = uuid.uuid4()
    converted_to_db = uuid_adapter.to_database(test_uuid, str)
    assert isinstance(converted_to_db, str)
    assert converted_to_db == str(test_uuid)

    # Test from database
    converted_from_db = uuid_adapter.from_database(converted_to_db, uuid.UUID)
    assert isinstance(converted_from_db, uuid.UUID)
    assert converted_from_db == test_uuid


def test_decimal_adaption(db):
    """Test Decimal adaptation from Python Decimal to database string."""
    # DecimalAdapter is registered by default
    decimal_adapter = db.adapter_registry.get_adapter(Decimal, str)
    test_decimal = Decimal("123.456")
    converted_to_db = decimal_adapter.to_database(test_decimal, str)
    assert isinstance(converted_to_db, str)
    assert converted_to_db == str(test_decimal)

    # Test from database
    converted_from_db = decimal_adapter.from_database(converted_to_db, Decimal)
    assert isinstance(converted_from_db, Decimal)
    assert converted_from_db == test_decimal