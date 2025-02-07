import json
from decimal import Decimal
from typing import Any, Dict, Optional, Union

try:
    from zoneinfo import ZoneInfo
except ImportError:
    from backports.zoneinfo import ZoneInfo  # compatible for Python 3.8

from datetime import datetime, date, time as timed
import time
from pytz import timezone as pytz_timezone
from dateutil.parser import parse

from .errors import TypeConversionError
from .typing import QueryResult


def format_with_length(base_type: str, params: Dict[str, Any]) -> str:
    """Process type with length parameter

    Args:
        base_type: Base type name
        params: Type parameters

    Returns:
        str: Formatted type string with length if specified
    """
    length = params.get('length')
    return f"{base_type}({length})" if length else base_type


def format_decimal(base_type: str, params: Dict[str, Any]) -> str:
    """Format decimal type

    Args:
        base_type: Base type name
        params: Type parameters containing precision and scale

    Returns:
        str: Formatted decimal type string
    """
    precision = params.get('precision')
    scale = params.get('scale')
    if precision is not None and scale is not None:
        return f"{base_type}({precision},{scale})"
    return base_type


def convert_datetime(
        value: Union[str, datetime, date, timed],
        format: Optional[str] = None,
        timezone: Optional[str] = None
) -> str:
    """
    Convert a datetime value to a string in the specified format.

    Args:
        value: The datetime value to convert
        format: The output format. Default is ISO 8601
        timezone: The timezone to use. Default is UTC

    Returns:
        str: A string representation of the datetime value

    Raises:
        ValueError: If the datetime string cannot be parsed
        TypeError: If the value type is not supported
    """
    if isinstance(value, str):
        try:
            dt = parse(value)
        except ValueError:
            if '-' in value:
                dt = datetime.strptime(value, '%Y-%m-%d')
            elif ':' in value:
                if '.' in value:
                    dt = datetime.strptime(value, '%H:%M:%S.%f')
                else:
                    dt = datetime.strptime(value, '%H:%M:%S')
            else:
                raise ValueError(f"Cannot parse value '{value}'")
    elif isinstance(value, (datetime, date, timed)):
        dt = value
    else:
        raise TypeError(f"Invalid value type: {type(value)}")

    if timezone:
        dt = dt.astimezone(pytz_timezone(timezone))

    if format:
        return dt.strftime(format)
    else:
        return dt.isoformat()


def parse_datetime(
        value: str,
        format: Optional[str] = None,
        timezone: Optional[str] = None
) -> Union[datetime, date]:
    """Parse datetime string, uses system timezone if not provided

    Args:
        value: Datetime string
        format: Date format string
        timezone: Timezone string (e.g. 'UTC', 'Asia/Shanghai')

    Returns:
        Union[datetime, date]: Parsed datetime or date object

    Raises:
        TypeConversionError: If the datetime string cannot be parsed
    """
    try:
        if format:
            dt = datetime.strptime(value, format)
        else:
            if 'T' in value:
                dt = datetime.fromisoformat(value)
            elif '.' in value:
                dt = datetime.strptime(value, '%Y-%m-%d %H:%M:%S.%f')
            elif ' ' in value:
                dt = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
            else:
                return datetime.strptime(value, '%Y-%m-%d').date()

        if timezone:
            tz = ZoneInfo(timezone)
            dt = dt.replace(tzinfo=tz)
        else:
            dt = dt.astimezone()

        return dt

    except ValueError as e:
        raise TypeConversionError(f"Invalid datetime format: {value}. Error: {str(e)}") from e


def safe_json_dumps(value: Any) -> str:
    """Safe JSON serialization

    Handles special types (like Decimal, datetime)

    Args:
        value: The value to serialize

    Returns:
        str: JSON string representation

    Raises:
        TypeConversionError: If serialization fails
    """
    def default(obj):
        if isinstance(obj, Decimal):
            return str(obj)
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

    try:
        return json.dumps(value, default=default)
    except Exception as e:
        raise TypeConversionError(f"JSON serialization failed: {value}") from e


def safe_json_loads(value: str) -> Any:
    """Safe JSON parsing

    Args:
        value: JSON string

    Returns:
        Any: Parsed Python object

    Raises:
        TypeConversionError: If JSON parsing fails
    """
    try:
        if not isinstance(value, str):
            return value

        return json.loads(value)
    except Exception as e:
        raise TypeConversionError(f"Failed to parse JSON: {str(e)}") from e


def array_converter(v):
    """Convert Python sequence to array representation

    Args:
        v: Value to convert (should be list or tuple)

    Returns:
        str: JSON string representation of the array

    Raises:
        TypeConversionError: If value cannot be converted to array
    """
    if isinstance(v, (list, tuple)):
        return safe_json_dumps(v)
    raise TypeConversionError(f"Cannot convert {type(v)} to array")


def measure_time(func):
    """Decorator for measuring function execution time

    Args:
        func: Function to measure

    Returns:
        wrapper: Decorated function that tracks execution time
    """
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        duration = time.perf_counter() - start
        if isinstance(result, QueryResult):
            result.duration = duration
        return result
    return wrapper