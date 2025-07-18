# tests/rhosocial/activerecord_test/basic/test_fields.py
"""Basic Fields Test Module

This module tests the basic field processing functionality of the ActiveRecord class.
"""
import json
from datetime import datetime
from decimal import Decimal
from uuid import UUID

import tzlocal

from .fixtures.models import type_test_model  # needed as fixture, do not remove.


def test_string_field(type_test_model):
    """Test string field processing"""
    # Basic string test
    model = type_test_model(string_field="test string")
    model.save()

    saved_model = type_test_model.find_one(model.id)
    assert saved_model.string_field == "test string"

    # Special characters test
    special_string = "Special chars: !@#$%^&*()"
    model.string_field = special_string
    model.save()

    saved_model.refresh()
    assert saved_model.string_field == special_string

    # Unicode test
    unicode_string = "Unicode: 你好世界 🌍"
    model.string_field = unicode_string
    model.save()

    saved_model.refresh()
    assert saved_model.string_field == unicode_string


def test_numeric_fields(type_test_model):
    """Test numeric type fields"""
    model = type_test_model(
        int_field=42,
        float_field=3.14159,
        decimal_field=Decimal("10.99")
    )
    model.save()

    saved_model = type_test_model.find_one(model.id)

    # Integer test
    assert saved_model.int_field == 42
    assert isinstance(saved_model.int_field, int)

    # Float test
    assert abs(saved_model.float_field - 3.14159) < 1e-6
    assert isinstance(saved_model.float_field, float)

    # Decimal test
    assert saved_model.decimal_field == Decimal("10.99")
    assert isinstance(saved_model.decimal_field, Decimal)

    # Large number test
    model.int_field = 2 ** 31 - 1
    model.float_field = 1.23456789
    model.decimal_field = Decimal("9999999.99")
    model.save()

    saved_model.refresh()
    assert saved_model.int_field == 2 ** 31 - 1
    assert abs(saved_model.float_field - 1.23456789) < 1e-5
    assert saved_model.decimal_field == Decimal("9999999.99")


def test_boolean_field(type_test_model):
    """Test boolean field processing"""
    model = type_test_model(bool_field=True)
    model.save()

    saved_model = type_test_model.find_one(model.id)
    assert saved_model.bool_field is True
    assert isinstance(saved_model.bool_field, bool)

    # Toggle value test
    model.bool_field = False
    model.save()

    saved_model.refresh()
    assert saved_model.bool_field is False


def test_datetime_field(type_test_model):
    """Test datetime field processing"""
    test_datetime = datetime(2024, 1, 1, 12, 30, 45, 123456, tzinfo=tzlocal.get_localzone())
    model = type_test_model(datetime_field=test_datetime)
    model.save()

    saved_model = type_test_model.find_one(model.id)
    assert saved_model.datetime_field == test_datetime
    assert isinstance(saved_model.datetime_field, datetime)


def test_json_field(type_test_model):
    """Test JSON field processing"""
    test_json = {
        "string": "value",
        "number": 42,
        "array": [1, 2, 3],
        "nested": {
            "key": "value"
        }
    }
    model = type_test_model(json_field=test_json)
    model.save()

    saved_model = type_test_model.find_one(model.id)
    assert saved_model.json_field == test_json

    # JSON serialization/deserialization test
    json_str = json.dumps(saved_model.json_field)
    parsed_json = json.loads(json_str)
    assert parsed_json == test_json


def test_nullable_field(type_test_model):
    """Test nullable field processing"""
    model = type_test_model()  # Use default value None
    assert model.nullable_field is None
    model.save()

    saved_model = type_test_model.find_one(model.id)
    assert saved_model.nullable_field is None

    # Set and clear value test
    model.nullable_field = "some value"
    model.save()

    saved_model.refresh()
    assert saved_model.nullable_field == "some value"

    model.nullable_field = None
    model.save()

    saved_model.refresh()
    assert saved_model.nullable_field is None


def test_uuid_primary_key(type_test_model):
    """Test UUID primary key processing"""
    model = type_test_model()
    model.save()

    assert isinstance(model.id, UUID)

    # UUID lookup test
    found_model = type_test_model.find_one(model.id)
    assert found_model is not None
    assert found_model.id == model.id

    # UUID generation uniqueness test
    another_model = type_test_model()
    another_model.save()
    assert another_model.id != model.id
