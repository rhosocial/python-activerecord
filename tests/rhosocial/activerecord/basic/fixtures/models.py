import re
from datetime import date, time, datetime
from decimal import Decimal
from typing import Optional, Type, Literal, Any, Dict

import pytest
from pydantic import EmailStr, Field, field_validator

from src.rhosocial.activerecord.backend.errors import ValidationError
from src.rhosocial.activerecord import ActiveRecord
from src.rhosocial.activerecord.field import TimestampMixin, UUIDMixin, IntegerPKMixin
from tests.rhosocial.activerecord.utils import create_active_record_fixture


class TypeCase(UUIDMixin, ActiveRecord):
    __table_name__ = "type_cases"

    # id: str
    username: str
    email: str
    tiny_int: Optional[int]
    small_int: Optional[int]
    big_int: Optional[int]
    float_val: Optional[float]
    double_val: Optional[float]
    decimal_val: Optional[Decimal]
    char_val: Optional[str]
    varchar_val: Optional[str]
    text_val: Optional[str]
    date_val: Optional[date]
    time_val: Optional[time]
    timestamp_val: Optional[float]
    blob_val: Optional[bytes]
    json_val: Optional[dict]
    array_val: Optional[list]
    is_active: bool = True

class User(IntegerPKMixin, TimestampMixin, ActiveRecord):
    __table_name__ = "users"

    id: Optional[int] = None  # 主键，新记录时为空
    username: str            # 必需字段
    email: EmailStr              # 必需字段
    age: Optional[int] = Field(..., ge=0, le=100)  # 可选字段
    balance: float = 0.0      # 有默认值的字段
    is_active: bool = True    # 有默认值的字段
    # created_at: Optional[str] = None  # 可选字段，通常由数据库自动设置
    # updated_at: Optional[str] = None  # 可选字段，通常由数据库自动设置

class ValidatedFieldUser(IntegerPKMixin, ActiveRecord):
    __table_name__ = "validated_field_users"

    id: Optional[int] = None  # 主键，新记录时为空
    username: str
    email: EmailStr
    age: Optional[int] = None
    balance: Optional[float] = 0.0
    credit_score: int
    status: Literal['active', 'inactive', 'banned', 'pending', 'suspended'] = 'active'
    is_active: Optional[bool] = True

    @field_validator('username')
    def validate_username(cls, value):
        if re.search(r'123', value):
            raise ValidationError("Username must not contain any digits.")
        return value

    @field_validator('credit_score')
    def validate_credit_score(cls, value):
        if not (0 <= value <= 800):
            raise ValidationError("Credit score must be a float between 0 and 800.")
        return value

class TypeTestModel(UUIDMixin, ActiveRecord):
    """用于测试各种字段类型的模型类"""
    __table_name__ = "type_tests"

    # UUID主键由UUIDMixin提供
    string_field: str = Field(default="test string")
    int_field: int = Field(default=42)
    float_field: float = Field(default=3.14)
    decimal_field: Decimal = Field(default=Decimal("10.99"))
    bool_field: bool = Field(default=True)
    datetime_field: datetime = Field(default_factory=datetime.now)
    json_field: Optional[dict] = None
    nullable_field: Optional[str] = Field(default=None)

class ValidatedUser(IntegerPKMixin, ActiveRecord):
    """用于验证测试的用户模型"""
    __table_name__ = "validated_users"

    id: Optional[int] = None
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    age: Optional[int] = Field(None, ge=0, le=150)

    @field_validator('username')
    def validate_username(cls, v: str) -> str:
        # 自定义用户名验证规则
        if len(v.strip()) != len(v):
            raise ValidationError("Username cannot have leading or trailing spaces")
        if not v.isalnum():
            raise ValidationError("Username must be alphanumeric")
        return v

    @classmethod
    def validate_record(cls, instance: 'ValidatedUser') -> None:
        """业务规则验证"""
        if instance.age is not None and instance.age < 13:
            raise ValidationError("User must be at least 13 years old")

@pytest.fixture(params=[Type[TypeCase], Type[User], Type[ValidatedFieldUser]])
def active_record_class(request) -> Type[ActiveRecord]:
    """提供 ActiveRecord 模型类"""
    return request.param

# 为test_curd.py每个 ActiveRecord 类创建对应的夹具
user_class = create_active_record_fixture(User)
type_case_class = create_active_record_fixture(TypeCase)
validated_user_class = create_active_record_fixture(ValidatedFieldUser)

# test_fields.py每个 ActiveRecord 类创建对应的夹具
type_test_model = create_active_record_fixture(TypeTestModel)

# test_validation.py每个 ActiveRecord 类创建对应的夹具
validated_user = create_active_record_fixture(ValidatedUser)
