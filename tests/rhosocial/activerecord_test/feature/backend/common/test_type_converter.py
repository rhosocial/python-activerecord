# tests/rhosocial/activerecord_test/feature/backend/common/test_type_converter.py
import datetime
import json
import uuid
from decimal import Decimal
from enum import Enum

import pytest

from rhosocial.activerecord.backend.basic_type_converter import (
    BasicTypeConverter, DateTimeConverter, BooleanConverter, UUIDConverter,
    JSONConverter, DecimalConverter, ArrayConverter, EnumConverter
)
from rhosocial.activerecord.backend.errors import TypeConversionError
from rhosocial.activerecord.backend.type_converters import TypeRegistry, BaseTypeConverter
from rhosocial.activerecord.backend.typing import DatabaseType


class TestTypeRegistry:
    """Tests for the TypeRegistry class which manages type converters"""

    def test_register_and_find_converter(self):
        """Test registering converters and finding them by value and type"""
        registry = TypeRegistry()

        # Register a basic converter
        basic_converter = BasicTypeConverter()
        registry.register(basic_converter)

        # Test finding converter for int value
        found_converter = registry.find_converter(42)
        assert found_converter is basic_converter

        # Test finding converter for str value
        found_converter = registry.find_converter("test")
        assert found_converter is basic_converter

    def test_register_by_name(self):
        """Test registering and retrieving converters by type name"""
        registry = TypeRegistry()

        # Register a converter with type names
        converter = DateTimeConverter()
        registry.register(converter, names=["DATE", "TIME", "DATETIME"])

        # Test finding by name (case-insensitive)
        found_converter = registry.find_converter_by_name("date")
        assert found_converter is converter

        found_converter = registry.find_converter_by_name("DATETIME")
        assert found_converter is converter

        # Test non-existent name
        found_converter = registry.find_converter_by_name("NONEXISTENT")
        assert found_converter is None

    def test_register_by_type(self):
        """Test registering and retrieving converters by DatabaseType"""
        registry = TypeRegistry()

        # Register a converter with DatabaseType values
        converter = DateTimeConverter()
        registry.register(
            converter,
            types=[DatabaseType.DATE, DatabaseType.TIME, DatabaseType.DATETIME]
        )

        # Test finding converter with target type
        found_converter = registry.find_converter("2023-01-01", DatabaseType.DATE)
        assert found_converter is converter

        # Test finding with non-registered type
        found_converter = registry.find_converter("value", DatabaseType.INTEGER)
        assert found_converter is not converter

    def test_converter_priority(self):
        """Test that converters are checked in priority order"""
        registry = TypeRegistry()

        # Create converters with different priorities
        class LowPriorityConverter(BaseTypeConverter):
            @property
            def priority(self) -> int:
                return 10

            def can_handle(self, value, target_type=None):
                return isinstance(value, int)

        class HighPriorityConverter(BaseTypeConverter):
            @property
            def priority(self) -> int:
                return 100

            def can_handle(self, value, target_type=None):
                return isinstance(value, int)

        low_converter = LowPriorityConverter()
        high_converter = HighPriorityConverter()

        # Register converters in any order
        registry.register(low_converter)
        registry.register(high_converter)

        # High priority converter should be found first
        found_converter = registry.find_converter(42)
        assert found_converter is high_converter

    def test_unregister(self):
        """Test unregistering converters by class"""
        registry = TypeRegistry()

        # Register multiple converters
        basic_converter = BasicTypeConverter()
        datetime_converter = DateTimeConverter()

        registry.register(basic_converter, names=["INTEGER", "VARCHAR"])
        registry.register(datetime_converter, types=[DatabaseType.DATETIME])

        # Before unregistering, verify DateTimeConverter is found for DATETIME type
        assert registry.find_converter("2023-01-01", DatabaseType.DATETIME) is datetime_converter

        # Unregister DateTimeConverter
        registry.unregister(DateTimeConverter)

        # Basic converter should still be registered
        assert registry.find_converter(42) is basic_converter
        assert registry.find_converter_by_name("INTEGER") is basic_converter

        # When requesting a converter for DatabaseType.DATETIME, none should be found
        # since the specific mapping was removed when unregistering DateTimeConverter
        assert registry.find_converter("2023-01-01", DatabaseType.DATETIME) is None

    def test_find_converter_logic(self):
        """Test the detailed logic of how TypeRegistry finds converters"""

        # Create our test converters
        basic_converter = BasicTypeConverter()
        datetime_converter = DateTimeConverter()

        # CASE 1: Register only by converter list (no type mapping)
        registry = TypeRegistry()  # Fresh registry
        registry.register(basic_converter)
        registry.register(datetime_converter)

        # With no type mapping, converters are found purely by their can_handle method
        found = registry.find_converter("2023-01-01", DatabaseType.DATETIME)
        assert found is datetime_converter  # DateTimeConverter has higher priority

        found = registry.find_converter("hello", DatabaseType.TEXT)
        assert found is basic_converter  # BasicConverter handles strings

        # CASE 2: Register with explicit type mapping
        registry = TypeRegistry()  # Fresh registry
        registry.register(basic_converter, types=[DatabaseType.TEXT])
        registry.register(datetime_converter, types=[DatabaseType.DATETIME])

        # When type mapping exists, it's used first
        found = registry.find_converter("2023-01-01", DatabaseType.DATETIME)
        assert found is datetime_converter

        found = registry.find_converter("2023-01-01", DatabaseType.TEXT)
        assert found is basic_converter  # Type mapping overrides DateTimeConverter's can_handle

        # Unregistered types fall back to can_handle method
        found = registry.find_converter("hello", DatabaseType.VARCHAR)
        assert found is basic_converter  # No mapping for VARCHAR, but BasicConverter can handle strings

        # CASE 3: After unregistering, type mappings are removed
        registry.unregister(DateTimeConverter)

        # No more mapping for DATETIME
        found = registry.find_converter("2023-01-01", DatabaseType.DATETIME)
        assert found is None

        # But general string handling still works
        found = registry.find_converter("2023-01-01")  # No type specified
        assert found is basic_converter

    def test_to_and_from_database(self):
        """Test high-level conversion functions"""
        registry = TypeRegistry()
        bool_converter = BooleanConverter()
        registry.register(bool_converter, types=[DatabaseType.BOOLEAN])

        # Convert to database
        db_value = registry.to_database(True, DatabaseType.BOOLEAN)
        assert db_value == 1

        # Convert from database
        py_value = registry.from_database(1, DatabaseType.BOOLEAN)
        assert py_value is True

        # None values should pass through unchanged
        assert registry.to_database(None) is None
        assert registry.from_database(None) is None

        # Unhandled values should pass through unchanged
        obj = object()
        assert registry.to_database(obj) is obj

    def test_cache_mechanism(self):
        """Test that the type registry uses caching for better performance"""
        registry = TypeRegistry()

        # Create a converter with a mock can_handle function
        converter = BasicTypeConverter()
        original_can_handle = converter.can_handle

        # Replace with mock to track calls
        call_count = 0

        def mock_can_handle(value, target_type=None):
            nonlocal call_count
            call_count += 1
            return original_can_handle(value, target_type)

        converter.can_handle = mock_can_handle

        registry.register(converter)

        # First call - should check the converter
        registry.find_converter(42)
        assert call_count == 1

        # Second call - should use cache
        registry.find_converter(42)
        assert call_count == 1  # Still 1, not 2

        # Clear cache and call again
        registry.clear_cache()
        registry.find_converter(42)
        assert call_count == 2

    def test_get_registered_types_and_names(self):
        """Test methods to get registered types and names"""
        registry = TypeRegistry()
        registry.register(
            DateTimeConverter(),
            names=["DATE", "TIME"],
            types=[DatabaseType.DATE, DatabaseType.TIME]
        )

        # Check registered types
        types = registry.get_registered_types()
        assert DatabaseType.DATE in types
        assert DatabaseType.TIME in types

        # Check registered names
        names = registry.get_registered_names()
        assert "date" in names  # Should be lowercase
        assert "time" in names


class TestBasicTypeConverter:
    """Tests for the BasicTypeConverter which handles primitive types"""

    def test_can_handle(self):
        """Test type checking for basic converter"""
        converter = BasicTypeConverter()

        # BasicTypeConverter handles primitive types
        assert converter.can_handle(42)
        assert converter.can_handle(3.14)
        assert converter.can_handle("test")
        assert converter.can_handle(True)

        # But not complex types
        assert not converter.can_handle(datetime.datetime.now())
        assert not converter.can_handle([1, 2, 3])

    def test_to_database(self):
        """Test conversion to database format"""
        converter = BasicTypeConverter()

        # Basic types should remain unchanged except booleans
        assert converter.to_database(42) == 42
        assert converter.to_database(3.14) == 3.14
        assert converter.to_database("test") == "test"

        # Booleans are converted to 0/1 integers
        assert converter.to_database(True) == 1
        assert converter.to_database(False) == 0

        # None passes through
        assert converter.to_database(None) is None

    def test_from_database(self):
        """Test conversion from database format"""
        converter = BasicTypeConverter()

        # Basic types remain unchanged
        assert converter.from_database(42) == 42
        assert converter.from_database(3.14) == 3.14
        assert converter.from_database("test") == "test"

        # Boolean conversion happens only with explicit source_type
        assert converter.from_database(1, DatabaseType.BOOLEAN) is True
        assert converter.from_database(0, DatabaseType.BOOLEAN) is False

        # Without type hint, integers stay as integers
        assert converter.from_database(1) == 1


class TestDateTimeConverter:
    """Tests for the DateTimeConverter handling date and time types"""

    def test_can_handle(self):
        """Test type checking for datetime converter"""
        converter = DateTimeConverter()

        # DateTimeConverter handles date/time objects
        assert converter.can_handle(datetime.datetime.now())
        assert converter.can_handle(datetime.date.today())
        assert converter.can_handle(datetime.time())

        # It also handles when target type is specified
        assert converter.can_handle("2023-01-01", DatabaseType.DATE)

        # But not other types
        assert not converter.can_handle(42)
        assert not converter.can_handle([])

    def test_to_database(self):
        """Test conversion of date/time objects to database format"""
        converter = DateTimeConverter()

        # Test datetime conversion
        dt = datetime.datetime(2023, 1, 15, 14, 30, 45)
        assert converter.to_database(dt) == "2023-01-15 14:30:45"

        # Test date conversion
        d = datetime.date(2023, 1, 15)
        assert converter.to_database(d) == "2023-01-15"

        # Test time conversion
        t = datetime.time(14, 30, 45)
        assert converter.to_database(t) == "14:30:45"

        # Test with specific target types
        assert converter.to_database(dt, DatabaseType.DATE) == "2023-01-15"
        assert converter.to_database(dt, DatabaseType.TIME) == "14:30:45"

    def test_from_database(self):
        """Test conversion from database format to date/time objects"""
        converter = DateTimeConverter()

        # Test datetime strings
        dt_str = "2023-01-15 14:30:45"
        result = converter.from_database(dt_str, DatabaseType.DATETIME)
        assert isinstance(result, datetime.datetime)
        assert result.year == 2023
        assert result.month == 1
        assert result.day == 15
        assert result.hour == 14
        assert result.minute == 30
        assert result.second == 45

        # Test date strings
        date_str = "2023-01-15"
        result = converter.from_database(date_str, DatabaseType.DATE)
        assert isinstance(result, datetime.date)
        assert result.year == 2023
        assert result.month == 1
        assert result.day == 15

        # Test time strings
        time_str = "14:30:45"
        result = converter.from_database(time_str, DatabaseType.TIME)
        assert isinstance(result, datetime.time)
        assert result.hour == 14
        assert result.minute == 30
        assert result.second == 45

        # Test that objects pass through unchanged
        dt = datetime.datetime.now()
        assert converter.from_database(dt) is dt


class TestBooleanConverter:
    """Tests for the BooleanConverter handling boolean values"""

    def test_can_handle(self):
        """Test type checking for boolean converter"""
        converter = BooleanConverter()

        # BooleanConverter handles booleans
        assert converter.can_handle(True)
        assert converter.can_handle(False)

        # It also handles when target type is specified
        assert converter.can_handle("true", DatabaseType.BOOLEAN)
        assert converter.can_handle(1, DatabaseType.BOOLEAN)

        # But not other types without type hint
        assert not converter.can_handle(42)
        assert not converter.can_handle("string")

    def test_to_database(self):
        """Test conversion of boolean values to database format"""
        converter = BooleanConverter()

        # Test boolean values
        assert converter.to_database(True) == 1
        assert converter.to_database(False) == 0

        # Test string representations
        assert converter.to_database("true") == 1
        assert converter.to_database("yes") == 1
        assert converter.to_database("false") == 0
        assert converter.to_database("no") == 0

        # Test case insensitivity
        assert converter.to_database("TRUE") == 1
        assert converter.to_database("False") == 0

    def test_from_database(self):
        """Test conversion from database format to boolean values"""
        converter = BooleanConverter()

        # Test with explicit source type
        assert converter.from_database(1, DatabaseType.BOOLEAN) is True
        assert converter.from_database(0, DatabaseType.BOOLEAN) is False

        # Test string representations with source type
        assert converter.from_database("true", DatabaseType.BOOLEAN) is True
        assert converter.from_database("yes", DatabaseType.BOOLEAN) is True
        assert converter.from_database("false", DatabaseType.BOOLEAN) is False
        assert converter.from_database("no", DatabaseType.BOOLEAN) is False

        # Test case insensitivity
        assert converter.from_database("TRUE", DatabaseType.BOOLEAN) is True
        assert converter.from_database("False", DatabaseType.BOOLEAN) is False

        # Without source type, values pass through
        assert converter.from_database(1) == 1
        assert converter.from_database("true") == "true"


class TestUUIDConverter:
    """Tests for the UUIDConverter handling UUID values"""

    def test_can_handle(self):
        """Test type checking for UUID converter"""
        converter = UUIDConverter()

        # UUIDConverter handles UUID objects
        assert converter.can_handle(uuid.uuid4())

        # It also handles when target type is specified
        assert converter.can_handle("550e8400-e29b-41d4-a716-446655440000", DatabaseType.UUID)

        # But not other types without type hint
        assert not converter.can_handle(42)
        assert not converter.can_handle("string")

    def test_to_database(self):
        """Test conversion of UUID values to database format"""
        converter = UUIDConverter()

        # Test with UUID object
        test_uuid = uuid.UUID("550e8400-e29b-41d4-a716-446655440000")
        assert converter.to_database(test_uuid) == "550e8400-e29b-41d4-a716-446655440000"

        # Test with string representation
        assert converter.to_database("550e8400-e29b-41d4-a716-446655440000") == "550e8400-e29b-41d4-a716-446655440000"

        # Invalid UUID strings should pass through
        assert converter.to_database("not-a-uuid") == "not-a-uuid"

    def test_from_database(self):
        """Test conversion from database format to UUID values"""
        converter = UUIDConverter()

        # Test with correct source type
        result = converter.from_database("550e8400-e29b-41d4-a716-446655440000", DatabaseType.UUID)
        assert isinstance(result, uuid.UUID)
        assert str(result) == "550e8400-e29b-41d4-a716-446655440000"

        # Without source type, strings pass through
        assert converter.from_database("550e8400-e29b-41d4-a716-446655440000") == "550e8400-e29b-41d4-a716-446655440000"

        # UUID objects pass through unchanged
        test_uuid = uuid.uuid4()
        assert converter.from_database(test_uuid) is test_uuid


class TestJSONConverter:
    """Tests for the JSONConverter handling JSON data"""

    def test_can_handle(self):
        """Test type checking for JSON converter"""
        converter = JSONConverter()

        # JSONConverter handles dicts and lists
        assert converter.can_handle({"key": "value"})
        assert converter.can_handle([1, 2, 3])

        # It also handles when target type is specified
        assert converter.can_handle("string", DatabaseType.JSON)
        assert converter.can_handle(42, DatabaseType.JSONB)

        # But not other types without type hint
        assert not converter.can_handle(42)
        assert not converter.can_handle(datetime.datetime.now())

    def test_to_database(self):
        """Test conversion of Python objects to JSON database format"""
        converter = JSONConverter()

        # Test with dictionary
        data = {"name": "Test", "numbers": [1, 2, 3]}
        result = converter.to_database(data)
        # Verify result is valid JSON string
        parsed = json.loads(result)
        assert parsed == data

        # Test with list
        data = [1, "two", {"three": 3}]
        result = converter.to_database(data)
        parsed = json.loads(result)
        assert parsed == data

        # Test with already serialized JSON
        json_str = '{"key": "value"}'
        assert converter.to_database(json_str) == json_str

        # Invalid JSON strings should pass through
        assert converter.to_database("not-json") == "not-json"

    def test_from_database(self):
        """Test conversion from JSON database format to Python objects"""
        converter = JSONConverter()

        # Test with JSON source type
        json_str = '{"name": "Test", "numbers": [1, 2, 3]}'
        result = converter.from_database(json_str, DatabaseType.JSON)
        assert isinstance(result, dict)
        assert result["name"] == "Test"
        assert result["numbers"] == [1, 2, 3]

        # Test with JSONB source type
        json_str = '[1, "two", {"three": 3}]'
        result = converter.from_database(json_str, DatabaseType.JSONB)
        assert isinstance(result, list)
        assert result[0] == 1
        assert result[1] == "two"
        assert result[2]["three"] == 3

        # Without source type, strings pass through
        assert converter.from_database('{"key": "value"}') == '{"key": "value"}'

        # Dictionary objects pass through unchanged
        data = {"key": "value"}
        assert converter.from_database(data) is data

    def test_json_serializer(self):
        """Test the custom JSON serializer for special types"""
        converter = JSONConverter()

        # Test serializing with datetime
        data = {
            "date": datetime.datetime(2023, 1, 15, 14, 30, 45),
            "id": uuid.UUID("550e8400-e29b-41d4-a716-446655440000"),
            "amount": Decimal("123.45")
        }

        # Should not raise TypeError
        result = converter.to_database(data)

        # Verify the serialized values
        parsed = json.loads(result)
        assert parsed["date"] == "2023-01-15T14:30:45"
        assert parsed["id"] == "550e8400-e29b-41d4-a716-446655440000"
        assert parsed["amount"] == 123.45


class TestDecimalConverter:
    """Tests for the DecimalConverter handling Decimal values"""

    def test_can_handle(self):
        """Test type checking for Decimal converter"""
        converter = DecimalConverter()

        # DecimalConverter handles Decimal objects
        assert converter.can_handle(Decimal("123.45"))

        # It also handles when target type is specified
        assert converter.can_handle("123.45", DatabaseType.DECIMAL)
        assert converter.can_handle(123.45, DatabaseType.NUMERIC)

        # But not other types without type hint
        assert not converter.can_handle(42)
        assert not converter.can_handle("string")

    def test_to_database(self):
        """Test conversion of Decimal values to database format"""
        converter = DecimalConverter()

        # Test with Decimal object
        decimal_val = Decimal("123.45")
        assert converter.to_database(decimal_val) == 123.45

        # Test with string representation and correct target type
        assert converter.to_database("123.45", DatabaseType.DECIMAL) == 123.45

        # Invalid decimal strings should pass through
        assert converter.to_database("not-a-decimal") == "not-a-decimal"

    def test_from_database(self):
        """Test conversion from database format to Decimal values"""
        converter = DecimalConverter()

        # Test with correct source type
        result = converter.from_database("123.45", DatabaseType.DECIMAL)
        assert isinstance(result, Decimal)
        assert result == Decimal("123.45")

        # Test with NUMERIC source type
        result = converter.from_database("123.45", DatabaseType.NUMERIC)
        assert isinstance(result, Decimal)
        assert result == Decimal("123.45")

        # Without source type, strings pass through
        assert converter.from_database("123.45") == "123.45"

        # Decimal objects pass through unchanged
        decimal_val = Decimal("123.45")
        assert converter.from_database(decimal_val) is decimal_val


class TestArrayConverter:
    """Tests for the ArrayConverter handling array data"""

    def test_can_handle(self):
        """Test type checking for array converter"""
        converter = ArrayConverter()

        # ArrayConverter handles lists, tuples and sets
        assert converter.can_handle([1, 2, 3])
        assert converter.can_handle((1, 2, 3))
        assert converter.can_handle({1, 2, 3})

        # It also handles when target type is specified
        assert converter.can_handle("string", DatabaseType.ARRAY)

        # But not other types without type hint
        assert not converter.can_handle(42)
        assert not converter.can_handle({"key": "value"})

    def test_to_database(self):
        """Test conversion of sequence types to database array format"""
        converter = ArrayConverter()

        # Test with list
        data = [1, 2, 3]
        result = converter.to_database(data)
        assert json.loads(result) == data

        # Test with tuple
        data = (1, 2, 3)
        result = converter.to_database(data)
        assert json.loads(result) == [1, 2, 3]  # Tuples become lists in JSON

        # Test with set
        data = {1, 2, 3}
        result = converter.to_database(data)
        # Sets become lists in JSON and may be reordered
        assert sorted(json.loads(result)) == [1, 2, 3]

        # Test with non-sequence when target is ARRAY
        with pytest.raises(TypeConversionError):
            converter.to_database("not-an-array", DatabaseType.ARRAY)

    def test_from_database(self):
        """Test conversion from database array format to Python sequences"""
        converter = ArrayConverter()

        # Test with ARRAY source type
        array_str = '[1, 2, 3]'
        result = converter.from_database(array_str, DatabaseType.ARRAY)
        assert isinstance(result, list)
        assert result == [1, 2, 3]

        # Test complex array
        array_str = '[1, "two", {"three": 3}]'
        result = converter.from_database(array_str, DatabaseType.ARRAY)
        assert result[0] == 1
        assert result[1] == "two"
        assert result[2]["three"] == 3

        # Without source type, strings pass through
        assert converter.from_database('[1, 2, 3]') == '[1, 2, 3]'

        # List objects pass through unchanged
        data = [1, 2, 3]
        assert converter.from_database(data) is data

    def test_array_json_serializer(self):
        """Test the custom JSON serializer for special types in arrays"""
        converter = ArrayConverter()

        # Test serializing array with special types
        data = [
            datetime.datetime(2023, 1, 15, 14, 30, 45),
            uuid.UUID("550e8400-e29b-41d4-a716-446655440000"),
            Decimal("123.45"),
            {1, 2, 3}  # Set
        ]

        # Should not raise TypeError
        result = converter.to_database(data)

        # Verify the serialized values
        parsed = json.loads(result)
        assert parsed[0] == "2023-01-15T14:30:45"
        assert parsed[1] == "550e8400-e29b-41d4-a716-446655440000"
        assert parsed[2] == 123.45
        assert sorted(parsed[3]) == [1, 2, 3]


class TestEnumValues(Enum):
    """Sample enum for testing EnumConverter"""
    RED = "red"
    GREEN = "green"
    BLUE = "blue"


class TestEnumConverter:
    """Tests for the EnumConverter handling Enum values"""

    def test_can_handle(self):
        """Test type checking for Enum converter"""
        converter = EnumConverter()

        # EnumConverter handles Enum values
        assert converter.can_handle(TestEnumValues.RED)

        # But not other types
        assert not converter.can_handle("RED")
        assert not converter.can_handle(1)

    def test_to_database(self):
        """Test conversion of Enum values to database format"""
        converter = EnumConverter()

        # Test various enum values
        assert converter.to_database(TestEnumValues.RED) == "red"
        assert converter.to_database(TestEnumValues.GREEN) == "green"
        assert converter.to_database(TestEnumValues.BLUE) == "blue"

        # None passes through
        assert converter.to_database(None) is None

    def test_from_database(self):
        """Test conversion from database format to Enum values"""
        converter = EnumConverter()

        # Base implementation can't convert to Enum without knowing the Enum class
        # So it just passes through the value
        assert converter.from_database("red") == "red"
        assert converter.from_database("green") == "green"

        # Custom Enum converter would need additional context to convert back
        class CustomEnumConverter(EnumConverter):
            def __init__(self, enum_class):
                self.enum_class = enum_class

            def from_database(self, value, source_type=None):
                if value is None:
                    return None
                try:
                    # Try to match value to enum member
                    for member in self.enum_class:
                        if member.value == value:
                            return member
                except (TypeError, ValueError):
                    pass
                return value  # Fallback

        # Test custom converter
        custom_converter = CustomEnumConverter(TestEnumValues)
        assert custom_converter.from_database("red") is TestEnumValues.RED
        assert custom_converter.from_database("green") is TestEnumValues.GREEN

        # Value not in enum just passes through
        assert custom_converter.from_database("purple") == "purple"


if __name__ == "__main__":
    pytest.main()
