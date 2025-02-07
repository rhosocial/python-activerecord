import json
from datetime import datetime
from decimal import Decimal
from uuid import UUID

import tzlocal

from .fixtures.models import type_test_model  # needed as fixture, do not remove.


def test_string_field(type_test_model):
    """测试字符串字段处理"""
    # 基础字符串测试
    model = type_test_model(string_field="test string")
    model.save()

    saved_model = type_test_model.find_one(model.id)
    assert saved_model.string_field == "test string"

    # 特殊字符测试
    special_string = "Special chars: !@#$%^&*()"
    model.string_field = special_string
    model.save()

    saved_model.refresh()
    assert saved_model.string_field == special_string

    # Unicode测试
    unicode_string = "Unicode: 你好世界 🌍"
    model.string_field = unicode_string
    model.save()

    saved_model.refresh()
    assert saved_model.string_field == unicode_string

def test_numeric_fields(type_test_model):
    """测试数值类型字段"""
    model = type_test_model(
        int_field=42,
        float_field=3.14159,
        decimal_field=Decimal("10.99")
    )
    model.save()

    saved_model = type_test_model.find_one(model.id)

    # 整数测试
    assert saved_model.int_field == 42
    assert isinstance(saved_model.int_field, int)

    # 浮点数测试
    assert abs(saved_model.float_field - 3.14159) < 1e-6
    assert isinstance(saved_model.float_field, float)

    # 定点数测试
    assert saved_model.decimal_field == Decimal("10.99")
    assert isinstance(saved_model.decimal_field, Decimal)

    # 大数测试
    model.int_field = 2 ** 31 - 1
    model.float_field = 1.23456789
    model.decimal_field = Decimal("9999999.99")
    model.save()

    saved_model.refresh()
    assert saved_model.int_field == 2 ** 31 - 1
    assert abs(saved_model.float_field - 1.23456789) < 1e-6
    assert saved_model.decimal_field == Decimal("9999999.99")

def test_boolean_field(type_test_model):
    """测试布尔字段处理"""
    model = type_test_model(bool_field=True)
    model.save()

    saved_model = type_test_model.find_one(model.id)
    assert saved_model.bool_field is True
    assert isinstance(saved_model.bool_field, bool)

    # 切换值测试
    model.bool_field = False
    model.save()

    saved_model.refresh()
    assert saved_model.bool_field is False

def test_datetime_field(type_test_model):
    """测试日期时间字段处理"""
    test_datetime = datetime(2024, 1, 1, 12, 30, 45, 123456, tzinfo=tzlocal.get_localzone())
    model = type_test_model(datetime_field=test_datetime)
    model.save()

    saved_model = type_test_model.find_one(model.id)
    assert saved_model.datetime_field == test_datetime
    assert isinstance(saved_model.datetime_field, datetime)

def test_json_field(type_test_model):
    """测试JSON字段处理"""
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

    # JSON序列化/反序列化测试
    json_str = json.dumps(saved_model.json_field)
    parsed_json = json.loads(json_str)
    assert parsed_json == test_json

def test_nullable_field(type_test_model):
    """测试可空字段处理"""
    model = type_test_model()  # 使用默认值None
    assert model.nullable_field is None
    model.save()

    saved_model = type_test_model.find_one(model.id)
    assert saved_model.nullable_field is None

    # 设置和清除值测试
    model.nullable_field = "some value"
    model.save()

    saved_model.refresh()
    assert saved_model.nullable_field == "some value"

    model.nullable_field = None
    model.save()

    saved_model.refresh()
    assert saved_model.nullable_field is None

def test_uuid_primary_key(type_test_model):
    """测试UUID主键处理"""
    model = type_test_model()
    model.save()

    assert isinstance(model.id, UUID)

    # UUID查找测试
    found_model = type_test_model.find_one(model.id)
    assert found_model is not None
    assert found_model.id == model.id

    # UUID生成唯一性测试
    another_model = type_test_model()
    another_model.save()
    assert another_model.id != model.id