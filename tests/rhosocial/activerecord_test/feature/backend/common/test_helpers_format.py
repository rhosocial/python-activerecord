# tests/rhosocial/activerecord_test/feature/backend/common/test_helpers_format.py
from datetime import datetime, date

import pytest

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

from unittest.mock import patch

from rhosocial.activerecord.backend.helpers import (
    format_with_length,
    format_decimal,
    convert_datetime,
    parse_datetime
)
from rhosocial.activerecord.backend.errors import TypeConversionError


class TestFormatFunctions:
    def test_format_with_length_with_length(self):
        # Test format_with_length with length parameter
        result = format_with_length("VARCHAR", {"length": 255})
        assert result == "VARCHAR(255)"

    def test_format_with_length_without_length(self):
        # Test format_with_length without length parameter
        result = format_with_length("TEXT", {})
        assert result == "TEXT"

    def test_format_decimal_with_precision_scale(self):
        # Test format_decimal with precision and scale
        result = format_decimal("DECIMAL", {"precision": 10, "scale": 2})
        assert result == "DECIMAL(10,2)"

    def test_format_decimal_without_precision_scale(self):
        # Test format_decimal without precision and scale
        result = format_decimal("DECIMAL", {})
        assert result == "DECIMAL"

    def test_format_decimal_with_precision_only(self):
        # Test format_decimal with precision only
        result = format_decimal("DECIMAL", {"precision": 10})
        assert result == "DECIMAL"

    def test_format_decimal_with_scale_only(self):
        # Test format_decimal with scale only
        result = format_decimal("DECIMAL", {"scale": 2})
        assert result == "DECIMAL"


class TestConvertDateTime:
    def test_convert_datetime_str_parse_exception(self):
        # Test the parse exception handling in convert_datetime
        with patch('rhosocial.activerecord.backend.helpers.parse', side_effect=ValueError("Parse error")):
            # Test with a date string
            result = convert_datetime("2022-07-25")
            assert result == "2022-07-25T00:00:00"

    def test_convert_datetime_str_with_time_only(self):
        # Test converting a time string
        # Note: When parsing a time string, it combines with current date
        result = convert_datetime("14:30:00")
        # We can't assert the exact value as it will include today's date
        # So we just check that it ends with the expected time
        assert result.endswith("14:30:00")

    def test_convert_datetime_str_with_time_microseconds(self):
        # Test converting a time string with microseconds
        # Note: When parsing a time string, it combines with current date
        result = convert_datetime("14:30:00.123456")
        # We can't assert the exact value as it will include today's date
        # So we just check that it ends with the expected time
        assert result.endswith("14:30:00.123456")

    def test_convert_datetime_invalid_not_parseable(self):
        # Test with a string that can't be parsed at all
        with pytest.raises(ValueError):
            convert_datetime("not a date or time")

    def test_convert_datetime_invalid_time_format(self):
        # Test with a string that contains colon but isn't valid time format
        # This will trigger the elif ':' in value: branch but fail later
        with pytest.raises(ValueError):
            convert_datetime("14:invalid:00")


class TestParseDateTime:
    def test_parse_datetime_with_format(self):
        # Test parsing a datetime with format
        result = parse_datetime("2022-07-25 14:30:00", format="%Y-%m-%d %H:%M:%S")
        assert isinstance(result, datetime)
        assert result.year == 2022
        assert result.month == 7
        assert result.day == 25
        assert result.hour == 14
        assert result.minute == 30
        assert result.second == 0

    def test_parse_datetime_iso_format(self):
        # Test parsing an ISO format datetime
        result = parse_datetime("2022-07-25T14:30:00")
        assert isinstance(result, datetime)
        assert result.year == 2022
        assert result.month == 7
        assert result.day == 25
        assert result.hour == 14
        assert result.minute == 30
        assert result.second == 0

    def test_parse_datetime_with_microseconds(self):
        # Test parsing a datetime with microseconds
        result = parse_datetime("2022-07-25 14:30:00.123456")
        assert isinstance(result, datetime)
        assert result.year == 2022
        assert result.month == 7
        assert result.day == 25
        assert result.hour == 14
        assert result.minute == 30
        assert result.second == 0
        assert result.microsecond == 123456

    def test_parse_datetime_standard_format(self):
        # Test parsing a standard format datetime
        result = parse_datetime("2022-07-25 14:30:00")
        assert isinstance(result, datetime)
        assert result.year == 2022
        assert result.month == 7
        assert result.day == 25
        assert result.hour == 14
        assert result.minute == 30
        assert result.second == 0

    def test_parse_date_only(self):
        # Test parsing a date only
        result = parse_datetime("2022-07-25")
        assert isinstance(result, date)
        assert result.year == 2022
        assert result.month == 7
        assert result.day == 25

    def test_parse_datetime_with_timezone(self):
        # Test parsing a datetime with timezone
        result = parse_datetime("2022-07-25T14:30:00", timezone="UTC")
        assert isinstance(result, datetime)
        assert result.tzinfo is not None
        assert result.tzinfo.key == "UTC"

    def test_parse_datetime_invalid_format(self):
        # Test parsing an invalid datetime format
        with pytest.raises(TypeConversionError):
            parse_datetime("invalid datetime")

    def test_parse_datetime_invalid_format_with_format(self):
        # Test parsing with an invalid format string
        with pytest.raises(TypeConversionError):
            parse_datetime("2022-07-25", format="%d/%m/%Y")
