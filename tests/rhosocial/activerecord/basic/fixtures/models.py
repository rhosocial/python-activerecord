import re
from datetime import date, time, datetime, timedelta
from decimal import Decimal
from typing import Optional, Type, Literal

import pytest
from pydantic import EmailStr, Field, field_validator

from src.rhosocial.activerecord import ActiveRecord
from src.rhosocial.activerecord.backend.errors import ValidationError
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
    timestamp_val: Optional[datetime]
    blob_val: Optional[bytes]
    json_val: Optional[dict]
    array_val: Optional[list]
    is_active: bool = True

class User(IntegerPKMixin, TimestampMixin, ActiveRecord):
    __table_name__ = "users"

    id: Optional[int] = None  # Primary key, empty for new records
    username: str            # Required field
    email: EmailStr          # Required field
    age: Optional[int] = Field(..., ge=0, le=100)  # Optional field
    balance: float = 0.0      # Field with default value
    is_active: bool = True    # Field with default value
    # created_at: Optional[str] = None  # Optional field, typically set automatically by database
    # updated_at: Optional[str] = None  # Optional field, typically set automatically by database

class ValidatedFieldUser(IntegerPKMixin, ActiveRecord):
    __table_name__ = "validated_field_users"

    id: Optional[int] = None  # Primary key, empty for new records
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
    """Model class for testing various field types"""
    __table_name__ = "type_tests"

    # UUID primary key provided by UUIDMixin
    string_field: str = Field(default="test string")
    int_field: int = Field(default=42)
    float_field: float = Field(default=3.14)
    decimal_field: Decimal = Field(default=Decimal("10.99"))
    bool_field: bool = Field(default=True)
    datetime_field: datetime = Field(default_factory=datetime.now)
    json_field: Optional[dict] = None
    nullable_field: Optional[str] = Field(default=None)

class ValidatedUser(IntegerPKMixin, ActiveRecord):
    """User model for validation testing"""
    __table_name__ = "validated_users"

    id: Optional[int] = None
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    age: Optional[int] = Field(None, ge=0, le=150)

    @field_validator('username')
    def validate_username(cls, v: str) -> str:
        # Custom username validation rules
        if len(v.strip()) != len(v):
            raise ValidationError("Username cannot have leading or trailing spaces")
        if not v.isalnum():
            raise ValidationError("Username must be alphanumeric")
        return v

    @classmethod
    def validate_record(cls, instance: 'ValidatedUser') -> None:
        """Business rule validation"""
        if instance.age is not None and instance.age < 13:
            raise ValidationError("User must be at least 13 years old")

@pytest.fixture(params=[Type[TypeCase], Type[User], Type[ValidatedFieldUser]])
def active_record_class(request) -> Type[ActiveRecord]:
    """Provide ActiveRecord model class"""
    return request.param

# Create fixtures for each ActiveRecord class for test_curd.py
user_class = create_active_record_fixture(User)
type_case_class = create_active_record_fixture(TypeCase)
validated_user_class = create_active_record_fixture(ValidatedFieldUser)

# Create fixtures for each ActiveRecord class for test_fields.py
type_test_model = create_active_record_fixture(TypeTestModel)

# Create fixtures for each ActiveRecord class for test_validation.py
validated_user = create_active_record_fixture(ValidatedUser)