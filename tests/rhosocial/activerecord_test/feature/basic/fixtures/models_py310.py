# src/rhosocial/activerecord/testsuite/feature/basic/fixtures/models_py310.py
"""
Python 3.10+ fixture model definitions.

This file contains model classes using Python 3.10+ syntax features:
- `X | Y` syntax instead of `Optional[X]` or `Union[X, Y]`
- `Type | None` instead of `Optional[Type]`

Note: This file should only be imported and used in Python 3.10+ environments.
"""
import re
from datetime import date, time, datetime
from decimal import Decimal
from typing import Optional, Type, Literal, Union, Any, Dict, List, Set
import json

from pydantic import EmailStr, Field, field_validator, model_validator

from rhosocial.activerecord.backend.type_adapter import BaseSQLTypeAdapter
from rhosocial.activerecord.base.fields import UseAdapter, UseColumn
from rhosocial.activerecord.model import ActiveRecord, AsyncActiveRecord
from rhosocial.activerecord.base.field_proxy import FieldProxy
from rhosocial.activerecord.backend.errors import ValidationError
from rhosocial.activerecord.field import CompositePKMixin, TimestampMixin, UUIDMixin, IntegerPKMixin
from typing import Annotated, ClassVar


# Declare that this module requires Python 3.10+
__requires_python__ = (3, 10)


class TypeCase(UUIDMixin, ActiveRecord):
    """A model with a wide variety of data types to test database type handling.

    Python 3.10+ version using | syntax instead of Optional.
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


class AsyncTypeCase(UUIDMixin, AsyncActiveRecord):
    """A model with a wide variety of data types to test database type handling.

    Python 3.10+ version using | syntax instead of Optional.
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


class TypeTestModel(UUIDMixin, ActiveRecord):
    """Model class for testing various field types.

    Python 3.10+ version using | syntax instead of Optional.
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

    Python 3.10+ version using | syntax instead of Optional.
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

    Python 3.10+ version using | syntax instead of Optional.
    """
    __table_name__ = "users"
    c: ClassVar[FieldProxy] = FieldProxy()

    # The IntegerPKMixin is expected to handle the `id` field.
    id: int | None = None
    username: str
    email: EmailStr
    age: int | None = Field(..., ge=0, le=100)
    balance: float = 0.0
    is_active: bool = True


class AsyncUser(IntegerPKMixin, TimestampMixin, AsyncActiveRecord):
    """A standard User model for general CRUD operation testing.

    Python 3.10+ version using | syntax instead of Optional.
    """
    __table_name__ = "users"
    c: ClassVar[FieldProxy] = FieldProxy()

    # The IntegerPKMixin is expected to handle the `id` field.
    id: int | None = None
    username: str
    email: EmailStr
    age: int | None = Field(..., ge=0, le=100)
    balance: float = 0.0
    is_active: bool = True


class ValidatedFieldUser(IntegerPKMixin, ActiveRecord):
    """A User model with specific, custom field validators to test the framework's
    validation handling.

    Python 3.10+ version using | syntax instead of Optional.
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

    Python 3.10+ version using | syntax instead of Optional.
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

    Python 3.10+ version using | syntax instead of Optional.
    """
    __table_name__ = "validated_users"

    id: int | None = None
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    age: int | None = Field(None, ge=0, le=150)

    @field_validator('username')
    def validate_username(cls, v: str) -> str:
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


class AsyncValidatedUser(IntegerPKMixin, AsyncActiveRecord):
    """User model for validation testing.

    Python 3.10+ version using | syntax instead of Optional.
    """
    __table_name__ = "validated_users"
    c: ClassVar[FieldProxy] = FieldProxy()

    id: int | None = None
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    age: int | None = Field(None, ge=0, le=150)

    @field_validator('username')
    def validate_username(cls, v: str) -> str:
        if len(v.strip()) != len(v):
            raise ValidationError("Username cannot have leading or trailing spaces")
        if not v.isalnum():
            raise ValidationError("Username must be alphanumeric")
        return v

    @classmethod
    def validate_record(cls, instance) -> None:
        """Business rule validation"""
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

    Python 3.10+ version using | syntax instead of Optional and Union.
    """
    __table_name__ = 'type_adapter_tests'
    __primary_key__ = 'id'

    id: int | None = None
    name: str
    # Fields for testing implicit X | None handling
    optional_name: str | None = None
    optional_age: int | None = None
    last_login: datetime | None = None
    is_premium: bool | None = None
    # Field for testing unsupported Union (str | int syntax)
    unsupported_union: str | int = 0
    # Fields for testing explicit adapter annotation
    custom_bool: Annotated[bool, UseAdapter(YesOrNoBooleanAdapter(), str)] = None
    optional_custom_bool: Annotated[bool | None, UseAdapter(YesOrNoBooleanAdapter(), str)] = None


class AsyncTypeAdapterTest(AsyncActiveRecord):
    """Model for testing various type adapter scenarios.

    Python 3.10+ version using | syntax instead of Optional and Union.
    """
    __table_name__ = 'type_adapter_tests'
    __primary_key__ = 'id'
    c: ClassVar[FieldProxy] = FieldProxy()

    id: int | None = None
    name: str
    # Fields for testing implicit X | None handling
    optional_name: str | None = None
    optional_age: int | None = None
    last_login: datetime | None = None
    is_premium: bool | None = None
    # Field for testing unsupported Union (str | int syntax)
    unsupported_union: str | int = 0
    # Fields for testing explicit adapter annotation
    custom_bool: Annotated[bool, UseAdapter(YesOrNoBooleanAdapter(), str)] = None
    optional_custom_bool: Annotated[bool | None, UseAdapter(YesOrNoBooleanAdapter(), str)] = None


class MappedUser(IntegerPKMixin, TimestampMixin, ActiveRecord):
    """User model with custom column name mappings for testing in basic feature.

    Python 3.10+ version using | syntax instead of Optional.
    """
    __table_name__ = "users"
    __primary_key__ = "id"

    # Python field: user_id, Database column: id
    user_id: Annotated[int | None, UseColumn("id")] = None

    # Python field: user_name, Database column: username
    user_name: Annotated[str, UseColumn("username")]

    # Python field: email_address, Database column: email
    email_address: Annotated[str, UseColumn("email")]

    # Python field: creation_date, which maps to the 'created_at' column.
    creation_date: Annotated[datetime | None, UseColumn("created_at")] = None


class AsyncMappedUser(IntegerPKMixin, TimestampMixin, AsyncActiveRecord):
    """User model with custom column name mappings for testing in basic feature.

    Python 3.10+ version using | syntax instead of Optional.
    """
    __table_name__ = "users"
    __primary_key__ = "id"
    c: ClassVar[FieldProxy] = FieldProxy()

    # Python field: user_id, Database column: id
    user_id: Annotated[int | None, UseColumn("id")] = None

    # Python field: user_name, Database column: username
    user_name: Annotated[str, UseColumn("username")]

    # Python field: email_address, Database column: email
    email_address: Annotated[str, UseColumn("email")]

    # Python field: creation_date, which maps to the 'created_at' column.
    creation_date: Annotated[datetime | None, UseColumn("created_at")] = None


class MappedPost(IntegerPKMixin, TimestampMixin, ActiveRecord):
    """Post model with custom column name mappings for testing in basic feature.

    Python 3.10+ version using | syntax instead of Optional.
    """
    __table_name__ = "posts"
    __primary_key__ = "id"

    # Python field: post_id, Database column: id
    post_id: Annotated[int | None, UseColumn("id")] = None

    # Python field: author_id, Database column: author
    author_id: Annotated[int, UseColumn("author")]

    # Python field: post_title, Database column: title
    post_title: Annotated[str, UseColumn("title")]

    # Python field: post_content, Database column: content
    post_content: Annotated[str, UseColumn("content")]

    # Python field: publication_time, maps to 'published_at' column
    publication_time: Annotated[datetime | None, UseColumn("published_at")] = None

    # Python field: is_published, Database column: published
    is_published: Annotated[bool, UseColumn("published")]


class AsyncMappedPost(IntegerPKMixin, TimestampMixin, AsyncActiveRecord):
    """Post model with custom column name mappings for testing in basic feature.

    Python 3.10+ version using | syntax instead of Optional.
    """
    __table_name__ = "posts"
    __primary_key__ = "id"
    c: ClassVar[FieldProxy] = FieldProxy()

    # Python field: post_id, Database column: id
    post_id: Annotated[int | None, UseColumn("id")] = None

    # Python field: author_id, Database column: author
    author_id: Annotated[int, UseColumn("author")]

    # Python field: post_title, Database column: title
    post_title: Annotated[str, UseColumn("title")]

    # Python field: post_content, Database column: content
    post_content: Annotated[str, UseColumn("content")]

    # Python field: publication_time, maps to 'published_at' column
    publication_time: Annotated[datetime | None, UseColumn("published_at")] = None

    # Python field: is_published, Database column: published
    is_published: Annotated[bool, UseColumn("published")]


class MappedComment(IntegerPKMixin, TimestampMixin, ActiveRecord):
    """Comment model with custom column name mappings for testing in basic feature.

    Python 3.10+ version using | syntax instead of Optional.
    """
    __table_name__ = "comments"
    __primary_key__ = "id"

    # Python field: comment_id, Database column: id
    comment_id: Annotated[int | None, UseColumn("id")] = None

    # Python field: post_id, Database column: post_ref
    post_id: Annotated[int, UseColumn("post_ref")]

    # Python field: author_id, Database column: author
    author_id: Annotated[int, UseColumn("author")]

    # Python field: comment_text, Database column: text
    comment_text: Annotated[str, UseColumn("text")]

    # Python field: comment_creation_date, maps to 'created_at' column.
    comment_creation_date: Annotated[datetime | None, UseColumn("created_at")] = None

    # Python field: is_approved, Database column: approved
    is_approved: Annotated[bool, UseColumn("approved")]


class AsyncMappedComment(IntegerPKMixin, TimestampMixin, AsyncActiveRecord):
    """Comment model with custom column name mappings for testing in basic feature.

    Python 3.10+ version using | syntax instead of Optional.
    """
    __table_name__ = "comments"
    __primary_key__ = "id"
    c: ClassVar[FieldProxy] = FieldProxy()

    # Python field: comment_id, Database column: id
    comment_id: Annotated[int | None, UseColumn("id")] = None

    # Python field: post_id, Database column: post_ref
    post_id: Annotated[int, UseColumn("post_ref")]

    # Python field: author_id, Database column: author
    author_id: Annotated[int, UseColumn("author")]

    # Python field: comment_text, Database column: text
    comment_text: Annotated[str, UseColumn("text")]

    # Python field: comment_creation_date, maps to 'created_at' column.
    comment_creation_date: Annotated[datetime | None, UseColumn("created_at")] = None

    # Python field: is_approved, Database column: approved
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
    """A model demonstrating various valid uses of UseColumn and UseAdapter,
    including mapping the primary key attribute.

    Python 3.10+ version using | syntax instead of Optional.
    """
    __table_name__ = 'column_mapping_items'
    __primary_key__ = 'id'

    # Primary key defaults to 'id'. item_id attribute maps to this 'id' column.
    item_id: Annotated[int | None, UseColumn("id")] = Field(default=None)
    name: str  # Default mapping
    item_count: Annotated[int, UseColumn("item_total")]  # Mapped to 'item_total'
    notes: Annotated[str, UseAdapter(IntToStringAdapter(), target_db_type=int), UseColumn("remarks")]


class AsyncColumnMappingModel(AsyncActiveRecord):
    """A model demonstrating various valid uses of UseColumn and UseAdapter,
    including mapping the primary key attribute.

    Python 3.10+ version using | syntax instead of Optional.
    """
    __table_name__ = 'column_mapping_items'
    __primary_key__ = 'id'
    c: ClassVar[FieldProxy] = FieldProxy()

    # Primary key defaults to 'id'. item_id attribute maps to this 'id' column.
    item_id: Annotated[int | None, UseColumn("id")] = Field(default=None)
    name: str  # Default mapping
    item_count: Annotated[int, UseColumn("item_total")]  # Mapped to 'item_total'
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

    Python 3.10+ version using | syntax instead of Optional.
    """
    __table_name__ = "mixed_annotation_items"
    __primary_key__ = "id"

    # 1. Standard Python type
    name: str

    # 2. Field with a different column name
    item_id: Annotated[int, UseColumn("id")]

    # 3. Field using a type adapter
    tags: Annotated[list[str], UseAdapter(ListToStringAdapter(), str)]

    # 4. Field with both a different column name and a type adapter
    metadata: Annotated[dict | None, UseColumn("meta"), UseAdapter(JsonToStringAdapter(), str)] = None

    # 5. Field that is nullable
    description: str | None = None

    # 6. Field with a default value
    status: str = "active"


class AsyncMixedAnnotationModel(AsyncActiveRecord):
    """A model with various combinations of annotations to test field mapping and adapters.

    Python 3.10+ version using | syntax instead of Optional.
    """
    __table_name__ = "mixed_annotation_items"
    __primary_key__ = "id"
    c: ClassVar[FieldProxy] = FieldProxy()

    # 1. Standard Python type
    name: str

    # 2. Field with a different column name
    item_id: Annotated[int, UseColumn("id")]

    # 3. Field using a type adapter
    tags: Annotated[list[str], UseAdapter(ListToStringAdapter(), str)]

    # 4. Field with both a different column name and a type adapter
    metadata: Annotated[dict | None, UseColumn("meta"), UseAdapter(JsonToStringAdapter(), str)] = None

    # 5. Field that is nullable
    description: str | None = None

    # 6. Field with a default value
    status: str = "active"

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
