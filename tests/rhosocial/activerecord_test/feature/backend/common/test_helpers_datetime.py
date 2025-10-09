# tests/rhosocial/activerecord_test/feature/backend/common/test_helpers_datetime.py
from datetime import datetime, date, time

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo

import pytest
import pytz.exceptions

from rhosocial.activerecord.backend.helpers import convert_datetime


def test_convert_datetime_str():
    # Test converting a string to a datetime object
    value = "2022-07-25T14:30:00"
    result = convert_datetime(value)
    assert result == "2022-07-25T14:30:00"


def test_convert_datetime_datetime():
    # Test converting a datetime object to a string
    value = datetime(2022, 7, 25, 14, 30, 0)
    result = convert_datetime(value)
    assert result == "2022-07-25T14:30:00"


def test_convert_datetime_date():
    # Test converting a date object to a string
    value = date(2022, 7, 25)
    result = convert_datetime(value)
    assert result == "2022-07-25"


def test_convert_datetime_time():
    # Test converting a time object to a string
    value = time(14, 30, 0)
    result = convert_datetime(value)
    assert result == "14:30:00"


def test_convert_datetime_invalid_str():
    # Test parsing an invalid string
    value = "invalid date"
    with pytest.raises(ValueError):
        convert_datetime(value)


def test_convert_datetime_no_format():
    # Test converting a datetime object to a string without a format
    value = datetime(2022, 7, 25, 14, 30, 0)
    result = convert_datetime(value)
    assert result == "2022-07-25T14:30:00"


def test_convert_datetime_with_format():
    # Test converting a datetime object to a string with a format
    value = datetime(2022, 7, 25, 14, 30, 0)
    result = convert_datetime(value, format="%Y-%m-%d %H:%M:%S")
    assert result == "2022-07-25 14:30:00"


def test_convert_datetime_with_timezone():
    # Test converting a datetime object to a string with a timezone
    value = datetime(2022, 7, 25, 14, 30, 0, tzinfo=ZoneInfo("UTC"))
    result = convert_datetime(value, timezone="US/Eastern")
    assert result == "2022-07-25T10:30:00-04:00"


def test_convert_datetime_with_invalid_timezone():
    # Test converting a datetime object to a string with an invalid timezone
    value = datetime(2022, 7, 25, 14, 30, 0)
    with pytest.raises(pytz.exceptions.UnknownTimeZoneError):
        convert_datetime(value, timezone="invalid")


def test_convert_datetime_with_empty_string():
    # Test converting an empty string to a datetime object
    value = ""
    with pytest.raises(ValueError):
        convert_datetime(value)


def test_convert_datetime_with_none():
    # Test converting None to a datetime object
    value = None
    with pytest.raises(TypeError):
        convert_datetime(value)


def test_convert_datetime_with_floating_point_seconds():
    # Test converting a datetime object with floating point seconds to a string
    value = datetime(2022, 7, 25, 14, 30, 0, 123456)
    result = convert_datetime(value)
    assert result == "2022-07-25T14:30:00.123456"


def test_convert_datetime_with_microseconds():
    # Test converting a datetime object with microseconds to a string
    value = datetime(2022, 7, 25, 14, 30, 0, 123456)
    result = convert_datetime(value, format="%Y-%m-%d %H:%M:%S.%f")
    assert result == "2022-07-25 14:30:00.123456"
