import json
from datetime import datetime

import pytest

from src.rhosocial.activerecord.backend.dialect import DatabaseType
from src.rhosocial.activerecord.backend.errors import TypeConversionError


def test_boolean_conversion(db):
    """测试布尔值转换"""
    mapper = db.value_mapper
    assert mapper.to_database(True, DatabaseType.BOOLEAN) == 1
    assert mapper.to_database(False, DatabaseType.BOOLEAN) == 0


def test_datetime_conversion(db):
    """测试日期时间转换"""
    mapper = db.value_mapper
    now = datetime.now()
    converted = mapper.to_database(now, DatabaseType.DATETIME)
    assert isinstance(converted, str)


def test_array_conversion(db):
    """测试数组转换"""
    mapper = db.value_mapper
    data = [1, 2, 3]
    converted = mapper.to_database(data, DatabaseType.ARRAY)
    assert isinstance(converted, str)
    assert json.loads(converted) == data


def test_invalid_array_conversion(db):
    """测试无效数组转换"""
    mapper = db.value_mapper
    with pytest.raises(TypeConversionError):
        mapper.to_database(123, DatabaseType.ARRAY)