# src/rhosocial/activerecord/testsuite/feature/basic/fixtures/models_py312.py
"""
Python 3.12+ fixture model definitions.

This file contains model classes using Python 3.12+ syntax features:
- Type parameter syntax (PEP 695): `class Model[T]:` instead of `Generic[T]`
- `@override` decorator for inheritance safety
- Enhanced f-string expressions

Note: This file should only be imported and used in Python 3.12+ environments.
"""
from __future__ import annotations

import copy
import re
from datetime import date, time, datetime
from decimal import Decimal
from typing import Optional, Type, Literal, Union, Any, Dict, List, Self, Set, override
import json

from pydantic import EmailStr, Field, field_validator, model_validator

from rhosocial.activerecord.backend.type_adapter import BaseSQLTypeAdapter
from rhosocial.activerecord.base.fields import UseAdapter, UseColumn
from rhosocial.activerecord.model import ActiveRecord, AsyncActiveRecord
from rhosocial.activerecord.base.field_proxy import FieldProxy
from rhosocial.activerecord.backend.errors import ValidationError
from rhosocial.activerecord.field import CompositePKMixin, TimestampMixin, UUIDMixin, IntegerPKMixin
from typing import Annotated, ClassVar


# Declare that this module requires Python 3.12+
__requires_python__ = (3, 12)


class TypeCase(UUIDMixin, ActiveRecord):
    """A model with a wide variety of data types to test database type handling.

    Python 3.12+ version using | syntax, Self type, and @override.
    """
    __table_name__ = "type_cases"

    username: str
    email: str
    tiny_int: int | None
    small_int: int | None
    big_int: int | None
    float_val: float | None
    double_val: float | None
    decimal_val: Decimal | None
    char_val: str | None
    varchar_val: str | None
    text_val: str | None
    date_val: date | None
    time_val: time | None
    timestamp_val: datetime | None
    blob_val: bytes | None
    json_val: dict | None
    array_val: list | None
    is_active: bool = True

    def clone(self) -> Self:
        """Create a deep copy of this instance."""
        return copy.deepcopy(self)


class AsyncTypeCase(UUIDMixin, AsyncActiveRecord):
    """A model with a wide variety of data types to test database type handling.

    Python 3.12+ version using | syntax, Self type, and @override.
    """
    __table_name__ = "type_cases"
    c: ClassVar[FieldProxy] = FieldProxy()

    username: str
    email: str
    tiny_int: int | None
    small_int: int | None
    big_int: int | None
    float_val: float | None
    double_val: float | None
    decimal_val: Decimal | None
    char_val: str | None
    varchar_val: str | None
    text_val: str | None
    date_val: date | None
    time_val: time | None
    timestamp_val: datetime | None
    blob_val: bytes | None
    json_val: dict | None
    array_val: list | None
    is_active: bool = True

    def clone(self) -> Self:
        """Create a deep copy of this instance."""
        return copy.deepcopy(self)


class TypeTestModel(UUIDMixin, ActiveRecord):
    """Model class for testing various field types.

    Python 3.12+ version using | syntax, Self type, and @override.
    """
    __table_name__ = "type_tests"

    # UUID primary key provided by UUIDMixin
    string_field: str = Field(default="test string")
    int_field: int = Field(default=42)
    float_field: float = Field(default=3.14)
    decimal_field: Decimal = Field(default=Decimal("10.99"))
    bool_field: bool = Field(default=True)
    datetime_field: datetime = Field(default_factory=datetime.now)
    json_field: dict | None = None
    nullable_field: str | None = Field(default=None)


class AsyncTypeTestModel(UUIDMixin, AsyncActiveRecord):
    """Model class for testing various field types.

    Python 3.12+ version using | syntax, Self type, and @override.
    """
    __table_name__ = "type_tests"
    c: ClassVar[FieldProxy] = FieldProxy()

    # UUID primary key provided by UUIDMixin
    string_field: str = Field(default="test string")
    int_field: int = Field(default=42)
    float_field: float = Field(default=3.14)
    decimal_field: Decimal = Field(default=Decimal("10.99"))
    bool_field: bool = Field(default=True)
    datetime_field: datetime = Field(default_factory=datetime.now)
    json_field: dict | None = None
    nullable_field: str | None = Field(default=None)


class User(IntegerPKMixin, TimestampMixin, ActiveRecord):
    """A standard User model for general CRUD operation testing.

    Python 3.12+ version using | syntax, Self type, and @override.
    """
    __table_name__ = "users"
    c: ClassVar[FieldProxy] = FieldProxy()

    id: int | None = None
    username: str
    email: EmailStr
    age: int | None = Field(..., ge=0, le=100)
    balance: float = 0.0
    is_active: bool = True

    def with_balance(self, new_balance: float) -> Self:
        """Return a new instance with updated balance."""
        new_user = self.clone()
        new_user.balance = new_balance
        return new_user

    def activate(self) -> Self:
        """Activate the user and return self for chaining."""
        self.is_active = True
        return self

    def deactivate(self) -> Self:
        """Deactivate the user and return self for chaining."""
        self.is_active = False
        return self


class AsyncUser(IntegerPKMixin, TimestampMixin, AsyncActiveRecord):
    """A standard User model for general CRUD operation testing.

    Python 3.12+ version using | syntax, Self type, and @override.
    """
    __table_name__ = "users"
    c: ClassVar[FieldProxy] = FieldProxy()

    id: int | None = None
    username: str
    email: EmailStr
    age: int | None = Field(..., ge=0, le=100)
    balance: float = 0.0
    is_active: bool = True

    def with_balance(self, new_balance: float) -> Self:
        """Return a new instance with updated balance."""
        new_user = copy.deepcopy(self)
        new_user.balance = new_balance
        return new_user


class ValidatedFieldUser(IntegerPKMixin, ActiveRecord):
    """A User model with specific, custom field validators to test the framework's
    validation handling.

    Python 3.12+ version using | syntax, Self type, and @override.
    """
    __table_name__ = "validated_field_users"
    c: ClassVar[FieldProxy] = FieldProxy()

    id: int | None = None
    username: str
    email: EmailStr
    age: int | None = None
    balance: float | None = 0.0
    credit_score: int
    status: Literal['active', 'inactive', 'banned', 'pending', 'suspended'] = 'active'
    is_active: bool | None = True

    @field_validator('username')
    def validate_username(cls, value):
        """A custom validator that rejects usernames containing '123'."""
        if re.search(r'123', value):
            raise ValidationError("Username must not contain '123'.")
        return value

    @field_validator('credit_score')
    def validate_credit_score(cls, value):
        """A custom validator that ensures credit_score is within a specific range."""
        if not (0 <= value <= 800):
            raise ValidationError("Credit score must be between 0 and 800.")
        return value


class AsyncValidatedFieldUser(IntegerPKMixin, AsyncActiveRecord):
    """A User model with specific, custom field validators to test the framework's
    validation handling.

    Python 3.12+ version using | syntax, Self type, and @override.
    """
    __table_name__ = "validated_field_users"
    c: ClassVar[FieldProxy] = FieldProxy()

    id: int | None = None
    username: str
    email: EmailStr
    age: int | None = None
    balance: float | None = 0.0
    credit_score: int
    status: Literal['active', 'inactive', 'banned', 'pending', 'suspended'] = 'active'
    is_active: bool | None = True

    @field_validator('username')
    def validate_username(cls, value):
        """A custom validator that rejects usernames containing '123'."""
        if re.search(r'123', value):
            raise ValidationError("Username must not contain '123'.")
        return value

    @field_validator('credit_score')
    def validate_credit_score(cls, value):
        """A custom validator that ensures credit_score is within a specific range."""
        if not (0 <= value <= 800):
            raise ValidationError("Credit score must be between 0 and 800.")
        return value


class ValidatedUser(IntegerPKMixin, ActiveRecord):
    """User model for validation testing.

    Python 3.12+ version using | syntax, Self type, and @override.
    """
    __table_name__ = "validated_users"

    id: int | None = None
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    age: int | None = Field(None, ge=0, le=150)

    @field_validator('username')
    @override
    def validate_username(cls, v: str) -> str:
        if len(v.strip()) != len(v):
            raise ValidationError("Username cannot have leading or trailing spaces")
        if not v.isalnum():
            raise ValidationError("Username must be alphanumeric")
        return v

    @classmethod
    def validate_record(cls, instance: Self) -> None:
        """Business rule validation using Self type."""
        if instance.age is not None and instance.age < 13:
            raise ValidationError("User must be at least 13 years old")


class AsyncValidatedUser(IntegerPKMixin, AsyncActiveRecord):
    """User model for validation testing.

    Python 3.12+ version using | syntax, Self type, and @override.
    """
    __table_name__ = "validated_users"
    c: ClassVar[FieldProxy] = FieldProxy()

    id: int | None = None
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    age: int | None = Field(None, ge=0, le=150)

    @field_validator('username')
    @override
    def validate_username(cls, v: str) -> str:
        if len(v.strip()) != len(v):
            raise ValidationError("Username cannot have leading or trailing spaces")
        if not v.isalnum():
            raise ValidationError("Username must be alphanumeric")
        return v

    @classmethod
    def validate_record(cls, instance: Self) -> None:
        """Business rule validation using Self type."""
        if instance.age is not None and instance.age < 13:
            raise ValidationError("User must be at least 13 years old")


# Keep this mixin I/O-free: fields, validators, and the FieldProxy descriptor are shared by sync/async models.
# FieldProxy builds expressions from configured model metadata; concrete models still own table metadata and I/O bases.
class PydanticValidatedFieldsMixin:
    """Shared Pydantic fields and validators for sync/async contract tests."""

    c: ClassVar[FieldProxy] = FieldProxy()
    code: str = Field(
        ...,
        pattern=r"^[A-Z]{3}-\d{3}$",
        title="Validation code",
        description="Business code used by Pydantic compatibility tests.",
        json_schema_extra={"active_record_test": "pydantic-native"},
    )
    quantity: int = Field(..., ge=1, le=999)
    step_count: int = Field(..., gt=0, lt=100, multiple_of=5)
    price: Decimal = Field(..., ge=Decimal("0.01"))
    start_at: datetime
    end_at: datetime
    status: Literal["draft", "active", "archived"] = "draft"
    normalized_name: str = Field(..., min_length=1, max_length=50)
    created_token: str = Field(default_factory=lambda: "generated-token")

    @field_validator("normalized_name")
    def normalize_name(cls, value: str) -> str:
        return value.strip().lower()

    @model_validator(mode="after")
    def validate_period(self):
        if self.end_at <= self.start_at:
            raise ValueError("end_at must be after start_at")
        return self


class PydanticValidatedModel(PydanticValidatedFieldsMixin, IntegerPKMixin, ActiveRecord):
    """Model for Pydantic native validation contract tests."""
    __table_name__ = "pydantic_validated_models"

    id: int | None = None


class AsyncPydanticValidatedModel(PydanticValidatedFieldsMixin, IntegerPKMixin, AsyncActiveRecord):
    """Async model for Pydantic native validation contract tests."""
    __table_name__ = "pydantic_validated_models"

    id: int | None = None


class YesOrNoBooleanAdapter(BaseSQLTypeAdapter):
    """Converts Python's True/False to 'yes'/'no' strings."""
    def _do_to_database(self, value: bool, target_type: Type, options: Dict[str, Any] | None = None) -> str:
        return "yes" if value else "no"

    def _do_from_database(self, value: str, target_type: Type, options: Dict[str, Any] | None = None) -> bool:
        return value == "yes"


class TypeAdapterTest(ActiveRecord):
    """Model for testing various type adapter scenarios.

    Python 3.12+ version using | syntax.
    """
    __table_name__ = 'type_adapter_tests'
    __primary_key__ = 'id'

    id: int | None = None
    name: str
    optional_name: str | None = None
    optional_age: int | None = None
    last_login: datetime | None = None
    is_premium: bool | None = None
    unsupported_union: str | int = 0
    custom_bool: Annotated[bool, UseAdapter(YesOrNoBooleanAdapter(), str)] = None
    optional_custom_bool: Annotated[bool | None, UseAdapter(YesOrNoBooleanAdapter(), str)] = None


class AsyncTypeAdapterTest(AsyncActiveRecord):
    """Model for testing various type adapter scenarios.

    Python 3.12+ version using | syntax.
    """
    __table_name__ = 'type_adapter_tests'
    __primary_key__ = 'id'
    c: ClassVar[FieldProxy] = FieldProxy()

    id: int | None = None
    name: str
    optional_name: str | None = None
    optional_age: int | None = None
    last_login: datetime | None = None
    is_premium: bool | None = None
    unsupported_union: str | int = 0
    custom_bool: Annotated[bool, UseAdapter(YesOrNoBooleanAdapter(), str)] = None
    optional_custom_bool: Annotated[bool | None, UseAdapter(YesOrNoBooleanAdapter(), str)] = None


class MappedUser(IntegerPKMixin, TimestampMixin, ActiveRecord):
    """User model with custom column name mappings.

    Python 3.12+ version using | syntax, Self type, and @override.
    """
    __table_name__ = "users"
    __primary_key__ = "id"

    user_id: Annotated[int | None, UseColumn("id")] = None
    user_name: Annotated[str, UseColumn("username")]
    email_address: Annotated[str, UseColumn("email")]
    creation_date: Annotated[datetime | None, UseColumn("created_at")] = None

    def update_email(self, new_email: str) -> Self:
        """Update email and return self for chaining."""
        self.email_address = new_email
        return self


class AsyncMappedUser(IntegerPKMixin, TimestampMixin, AsyncActiveRecord):
    """User model with custom column name mappings.

    Python 3.12+ version using | syntax.
    """
    __table_name__ = "users"
    __primary_key__ = "id"
    c: ClassVar[FieldProxy] = FieldProxy()

    user_id: Annotated[int | None, UseColumn("id")] = None
    user_name: Annotated[str, UseColumn("username")]
    email_address: Annotated[str, UseColumn("email")]
    creation_date: Annotated[datetime | None, UseColumn("created_at")] = None


class MappedPost(IntegerPKMixin, TimestampMixin, ActiveRecord):
    """Post model with custom column name mappings.

    Python 3.12+ version using | syntax.
    """
    __table_name__ = "posts"
    __primary_key__ = "id"

    post_id: Annotated[int | None, UseColumn("id")] = None
    author_id: Annotated[int, UseColumn("author")]
    post_title: Annotated[str, UseColumn("title")]
    post_content: Annotated[str, UseColumn("content")]
    publication_time: Annotated[datetime | None, UseColumn("published_at")] = None
    is_published: Annotated[bool, UseColumn("published")]


class AsyncMappedPost(IntegerPKMixin, TimestampMixin, AsyncActiveRecord):
    """Post model with custom column name mappings.

    Python 3.12+ version using | syntax.
    """
    __table_name__ = "posts"
    __primary_key__ = "id"
    c: ClassVar[FieldProxy] = FieldProxy()

    post_id: Annotated[int | None, UseColumn("id")] = None
    author_id: Annotated[int, UseColumn("author")]
    post_title: Annotated[str, UseColumn("title")]
    post_content: Annotated[str, UseColumn("content")]
    publication_time: Annotated[datetime | None, UseColumn("published_at")] = None
    is_published: Annotated[bool, UseColumn("published")]


class MappedComment(IntegerPKMixin, TimestampMixin, ActiveRecord):
    """Comment model with custom column name mappings.

    Python 3.12+ version using | syntax.
    """
    __table_name__ = "comments"
    __primary_key__ = "id"

    comment_id: Annotated[int | None, UseColumn("id")] = None
    post_id: Annotated[int, UseColumn("post_ref")]
    author_id: Annotated[int, UseColumn("author")]
    comment_text: Annotated[str, UseColumn("text")]
    comment_creation_date: Annotated[datetime | None, UseColumn("created_at")] = None
    is_approved: Annotated[bool, UseColumn("approved")]


class AsyncMappedComment(IntegerPKMixin, TimestampMixin, AsyncActiveRecord):
    """Comment model with custom column name mappings.

    Python 3.12+ version using | syntax.
    """
    __table_name__ = "comments"
    __primary_key__ = "id"
    c: ClassVar[FieldProxy] = FieldProxy()

    comment_id: Annotated[int | None, UseColumn("id")] = None
    post_id: Annotated[int, UseColumn("post_ref")]
    author_id: Annotated[int, UseColumn("author")]
    comment_text: Annotated[str, UseColumn("text")]
    comment_creation_date: Annotated[datetime | None, UseColumn("created_at")] = None
    is_approved: Annotated[bool, UseColumn("approved")]


class IntToStringAdapter(BaseSQLTypeAdapter):
    """A simple type adapter that converts an integer for the DB to a string for Python."""

    def __init__(self):
        super().__init__()
        self._register_type(str, int)

    def _do_to_database(self, value: Any, target_type: Type, options: Dict[str, Any] | None = None) -> Any:
        return int(value)

    def _do_from_database(self, value: Any, target_type: Type, options: Dict[str, Any] | None = None) -> Any:
        return str(value)


class ColumnMappingModel(ActiveRecord):
    """A model demonstrating various valid uses of UseColumn and UseAdapter.

    Python 3.12+ version using | syntax.
    """
    __table_name__ = 'column_mapping_items'
    __primary_key__ = 'id'

    item_id: Annotated[int | None, UseColumn("id")] = Field(default=None)
    name: str
    item_count: Annotated[int, UseColumn("item_total")]
    notes: Annotated[str, UseAdapter(IntToStringAdapter(), target_db_type=int), UseColumn("remarks")]


class AsyncColumnMappingModel(AsyncActiveRecord):
    """A model demonstrating various valid uses of UseColumn and UseAdapter.

    Python 3.12+ version using | syntax.
    """
    __table_name__ = 'column_mapping_items'
    __primary_key__ = 'id'
    c: ClassVar[FieldProxy] = FieldProxy()

    item_id: Annotated[int | None, UseColumn("id")] = Field(default=None)
    name: str
    item_count: Annotated[int, UseColumn("item_total")]
    notes: Annotated[str, UseAdapter(IntToStringAdapter(), target_db_type=int), UseColumn("remarks")]


class ListToStringAdapter(BaseSQLTypeAdapter):
    """Converts a Python list of strings to a single comma-separated string for the DB."""

    def __init__(self):
        super().__init__()
        self._register_type(list, str)

    def _do_to_database(self, value: List[str], target_type: Type, options: Dict[str, Any] | None = None) -> str | None:
        if value is None:
            return None
        return ",".join(value)

    def _do_from_database(self, value: str, target_type: Type, options: Dict[str, Any] | None = None) -> list[str] | None:
        if value is None:
            return None

        if isinstance(value, str):
            if value.startswith('[') and value.endswith(']'):
                import ast
                try:
                    parsed_value = ast.literal_eval(value)
                    if isinstance(parsed_value, list):
                        return parsed_value
                    else:
                        return [parsed_value] if parsed_value is not None else []
                except (ValueError, SyntaxError):
                    pass

            stripped_value = value.strip().strip('"\'')
            if stripped_value.startswith('[') and stripped_value.endswith(']'):
                import ast
                try:
                    parsed_value = ast.literal_eval(stripped_value)
                    if isinstance(parsed_value, list):
                        return parsed_value
                except (ValueError, SyntaxError):
                    pass

            if value:
                return [item.strip().strip('"\'') for item in value.split(',')]
            else:
                return []

        return [value] if value is not None else []


class JsonToStringAdapter(BaseSQLTypeAdapter):
    """Converts a Python dictionary to a JSON string for the DB."""

    def __init__(self):
        super().__init__()
        self._register_type(dict, str)

    def _do_to_database(self, value: Dict, target_type: Type, options: Dict[str, Any] | None = None) -> str | None:
        if value is None:
            return None
        return json.dumps(value)

    def _do_from_database(self, value: str, target_type: Type, options: Dict[str, Any] | None = None) -> dict | None:
        if value is None:
            return None
        return json.loads(value)


class MixedAnnotationModel(ActiveRecord):
    """A model with various combinations of annotations to test field mapping and adapters.

    Python 3.12+ version using | syntax, Self type, and @override.
    """
    __table_name__ = "mixed_annotation_items"
    __primary_key__ = "id"

    name: str
    item_id: Annotated[int, UseColumn("id")]
    tags: Annotated[list[str], UseAdapter(ListToStringAdapter(), str)]
    metadata: Annotated[dict | None, UseColumn("meta"), UseAdapter(JsonToStringAdapter(), str)] = None
    description: str | None = None
    status: str = "active"

    def with_status(self, new_status: str) -> Self:
        """Return a new instance with updated status."""
        new_instance = copy.deepcopy(self)
        new_instance.status = new_status
        return new_instance


class AsyncMixedAnnotationModel(AsyncActiveRecord):
    """A model with various combinations of annotations to test field mapping and adapters.

    Python 3.12+ version using | syntax.
    """
    __table_name__ = "mixed_annotation_items"
    __primary_key__ = "id"
    c: ClassVar[FieldProxy] = FieldProxy()

    name: str
    item_id: Annotated[int, UseColumn("id")]
    tags: Annotated[list[str], UseAdapter(ListToStringAdapter(), str)]
    metadata: Annotated[dict | None, UseColumn("meta"), UseAdapter(JsonToStringAdapter(), str)] = None
    description: str | None = None
    status: str = "active"


# Python 3.12+ Type Parameter Syntax Examples (PEP 695)
# These demonstrate the new generic syntax, though they may not be directly
# usable with ActiveRecord due to Pydantic model constraints.

class GenericContainer[T]:
    """Example of Python 3.12+ type parameter syntax.

    Note: This is a demonstration class, not an ActiveRecord model.
    The new syntax allows cleaner generic definitions:

    Before (Python 3.8+):
        class GenericContainer(Generic[T]):
            ...

    After (Python 3.12+):
        class GenericContainer[T]:
            ...
    """
    def __init__(self, value: T):
        self._value = value

    def get_value(self) -> T:
        return self._value

    def map[U](self, func: callable[[T], U]) -> "GenericContainer[U]":
        """Transform the contained value using the provided function.

        Uses Python 3.12+ type parameter syntax for methods.
        """
        return GenericContainer(func(self._value))


class TypedResult[T, E]:
    """Example of Python 3.12+ multiple type parameters.

    Note: This is a demonstration class, not an ActiveRecord model.
    """
    def __init__(self, value: T | None = None, error: E | None = None):
        self._value = value
        self._error = error

    def is_ok(self) -> bool:
        return self._error is None

    def unwrap(self) -> T:
        if self._error is not None:
            raise ValueError(f"Cannot unwrap error: {self._error}")
        return self._value  # type: ignore

# =============================================================================
# Composite Primary Key Models
# =============================================================================

class OrderItem(CompositePKMixin, ActiveRecord):
    """Composite PK (order_id, product_id), PK provided by application."""
    __table_name__ = "order_items"
    __primary_key__ = ("order_id", "product_id")
    c: ClassVar[FieldProxy] = FieldProxy()

    order_id: int
    product_id: int
    quantity: int = 1
    unit_price: Decimal = Decimal("0.00")


class AsyncOrderItem(CompositePKMixin, AsyncActiveRecord):
    """Async variant of OrderItem."""
    __table_name__ = "order_items"
    __primary_key__ = ("order_id", "product_id")
    c: ClassVar[FieldProxy] = FieldProxy()

    order_id: int
    product_id: int
    quantity: int = 1
    unit_price: Decimal = Decimal("0.00")


class StoreInventory(CompositePKMixin, ActiveRecord):
    """Triple-column composite PK."""
    __table_name__ = "store_inventory"
    __primary_key__ = ("store_id", "product_id", "batch_id")
    c: ClassVar[FieldProxy] = FieldProxy()

    store_id: int
    product_id: int
    batch_id: str
    stock: int = 0


class AsyncStoreInventory(CompositePKMixin, AsyncActiveRecord):
    """Async variant of StoreInventory."""
    __table_name__ = "store_inventory"
    __primary_key__ = ("store_id", "product_id", "batch_id")
    c: ClassVar[FieldProxy] = FieldProxy()

    store_id: int
    product_id: int
    batch_id: str
    stock: int = 0


class Order(IntegerPKMixin, TimestampMixin, ActiveRecord):
    """Single-column auto-increment PK -- backward compatibility control group."""
    __table_name__ = "orders"
    __primary_key__ = "id"
    c: ClassVar[FieldProxy] = FieldProxy()

    id: Optional[int] = None
    total: Decimal = Decimal("0.00")


class AsyncOrder(IntegerPKMixin, TimestampMixin, AsyncActiveRecord):
    """Async variant of Order."""
    __table_name__ = "orders"
    __primary_key__ = "id"
    c: ClassVar[FieldProxy] = FieldProxy()

    id: Optional[int] = None
    total: Decimal = Decimal("0.00")


class MappedOrderItem(CompositePKMixin, ActiveRecord):
    """Composite PK with UseColumn mapping -- Python field names differ from DB column names."""
    __table_name__ = "order_items"
    __primary_key__ = ("order_id", "product_id")

    order_ref: Annotated[int, UseColumn("order_id")]
    product_ref: Annotated[int, UseColumn("product_id")]
    quantity: int = 1
    unit_price: Decimal = Decimal("0.00")


class AsyncMappedOrderItem(CompositePKMixin, AsyncActiveRecord):
    """Async variant of MappedOrderItem."""
    __table_name__ = "order_items"
    __primary_key__ = ("order_id", "product_id")
    c: ClassVar[FieldProxy] = FieldProxy()

    order_ref: Annotated[int, UseColumn("order_id")]
    product_ref: Annotated[int, UseColumn("product_id")]
    quantity: int = 1
    unit_price: Decimal = Decimal("0.00")


class BulkUser(IntegerPKMixin, ActiveRecord):
    __table_name__ = "bulk_users"
    c: ClassVar[FieldProxy] = FieldProxy()

    id: int | None = None
    name: str
    age: int = 0
    email: str = ""


class AsyncBulkUser(IntegerPKMixin, AsyncActiveRecord):
    __table_name__ = "bulk_users"
    c: ClassVar[FieldProxy] = FieldProxy()

    id: int | None = None
    name: str
    age: int = 0
    email: str = ""
