# 使用 `python-activerecord-testsuite` 模式进行模型测试

测试您的 `ActiveRecord` 模型是构建健壮和可靠应用程序的基础。本指南演示了如何有效测试模型，利用官方 `python-activerecord-testsuite` 建立的模式，实现全面和标准化的方法。

`testsuite` 旨在提供一种通用方法来定义可以针对各种数据库后端运行的测试。这是通过提供后端特定实现和配置的“提供者”（Providers）来实现的。这种方法促进了隔离、可重复和彻底的测试。

## 理解测试设置（基于提供者）

`python-activerecord-testsuite` 使用 `ProviderRegistry` 来管理不同的后端实现。例如，SQLite 后端注册了多个提供者（例如 `BasicProvider`、`EventsProvider`、`QueryProvider`），每个提供者负责设置特定测试场景和模型，以用于其各自的功能组。

此设置的核心组件是提供者中的 `_setup_model` 方法（或类似的辅助函数），它动态配置 `ActiveRecord` 模型进行测试。这包括：
1.  获取给定测试场景的正确 `ConnectionConfig` 和 `StorageBackend` 类。
2.  调用 `model_class.configure(config, backend_class)` 将模型链接到实时数据库连接。
3.  准备数据库模式（例如，删除现有表并从 SQL 文件创建新表）。

以下是配置模型进行测试的简化表示：

```python
# 提供者（例如 python-activerecord 中的 BasicProvider）的简化辅助函数
import os
import tempfile
from typing import Type
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig

def _setup_model_for_testing(model_class: Type[ActiveRecord], scenario_name: str, schema_sql: str) -> Type[ActiveRecord]:
    """
    为给定测试场景配置 ActiveRecord 模型，
    设置临时数据库并创建模式。
    """
    # 为简单起见，这里我们始终使用内存中的 SQLite 数据库。
    # 实际提供者使用 scenario_name 来选择不同的配置。
    config = SQLiteConnectionConfig(database=":memory:")
    
    # 使用我们特定的后端和配置来配置模型类。
    model_class.configure(config, SQLiteBackend)
    
    # 准备数据库模式。
    model_class.__backend__.execute(f"DROP TABLE IF EXISTS {model_class.__table_name__}")
    model_class.__backend__.execute(schema_sql)
    
    return model_class
```

在您的实际测试中，您将使用 `testsuite` 提供的 `pytest` fixture（或您自己的提供者）来获取正确配置的模型实例。

## 基本模型测试（CRUD 操作）

我们将使用 `User` 模型示例，类似于 `testsuite` 的基本功能 fixture 中找到的 `User` 模型 (`rhosocial.activerecord.testsuite.feature.basic.fixtures.models`)。

```python
# 假设此 User 模型定义在 your_app/models.py 中
# 或为了清晰起见，定义在您的测试 fixture 中。
from rhosocial.activerecord.model import ActiveRecord
from pydantic import Field, EmailStr
from typing import Optional

class User(ActiveRecord):
    __table_name__ = "users" # 明确定义表名用于模式创建
    id: Optional[int] = Field(None, primary_key=True)
    username: str
    email: EmailStr
    age: Optional[int] = Field(None, ge=0, le=100)
    balance: float = 0.0
    is_active: bool = True
```

现在，让我们编写基本 CRUD 操作的测试。我们将使用 `pytest` fixture 来提供一个配置好的 `User` 模型。

```python
# tests/test_basic_user.py
import pytest
from your_app.models import User
from rhosocial.activerecord.backend.errors import NotFoundError # 示例异常

# User 模型的示例模式
USER_SCHEMA = """
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    age INTEGER,
    balance REAL DEFAULT 0.0,
    is_active BOOLEAN DEFAULT TRUE
);
"""

@pytest.fixture
def configured_user_model() -> Type[User]:
    """
    为每个测试提供一个配置好的 User 模型和干净的数据库表。
    """
    # 使用我们的助手函数设置模型。
    # 在实际的 testsuite 中，这将来自提供者的 setup_user_model。
    return _setup_model_for_testing(User, "memory", USER_SCHEMA)

def test_create_and_read_user(configured_user_model: Type[User]):
    """测试创建用户并随后检索它。"""
    # 创建
    user = configured_user_model.create(username='testuser', email='test@example.com', age=30)
    assert user.id is not None
    assert user.username == 'testuser'
    assert user.email == 'test@example.com'
    assert user.age == 30
    assert user.is_active is True

    # 读取
    retrieved_user = configured_user_model.find(user.id)
    assert retrieved_user.username == 'testuser'
    assert retrieved_user.email == 'test@example.com'
    assert retrieved_user.age == 30

def test_update_user(configured_user_model: Type[User]):
    """测试更新现有用户的属性。"""
    user = configured_user_model.create(username='testuser', email='test@example.com')
    
    # 更新
    user.update(email='new_email@example.com', is_active=False)
    
    # 验证更新
    updated_user = configured_user_model.find(user.id)
    assert updated_user.email == 'new_email@example.com'
    assert updated_user.is_active is False

def test_delete_user(configured_user_model: Type[User]):
    """测试从数据库中删除用户。"""
    user = configured_user_model.create(username='testuser', email='test@example.com')
    user_id = user.id
    
    # 删除
    user.destroy()
    
    # 验证删除
    with pytest.raises(NotFoundError): # 使用特定的 NotFoundError
        configured_user_model.find(user_id)
```

## 测试验证

`ActiveRecord` 模型利用 `Pydantic` 进行强大的数据验证。您可以直接测试这些验证。我们将使用 `ValidatedUser` 模型，它也受到 `testsuite` fixture 的启发。

```python
# 假设此 ValidatedUser 模型定义在 your_app/models.py 中
# 或在您的测试 fixture 中。
import re
from rhosocial.activerecord.backend.errors import ValidationError as ActiveRecordValidationError # 别名以避免冲突

class ValidatedUser(ActiveRecord):
    __table_name__ = "validated_users"
    id: Optional[int] = Field(None, primary_key=True)
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    age: Optional[int] = Field(None, ge=0, le=150)

    @field_validator('username')
    @classmethod
    def validate_username_no_spaces(cls, v: str) -> str:
        if len(v.strip()) != len(v):
            raise ActiveRecordValidationError("用户名不能包含前导或尾随空格")
        if not v.isalnum():
            raise ActiveRecordValidationError("用户名必须是字母数字")
        return v

    @classmethod
    def validate_record(cls, instance: 'ValidatedUser') -> None:
        """保存前应用的业务规则验证。"""
        if instance.age is not None and instance.age < 13:
            raise ActiveRecordValidationError("用户必须至少 13 岁")
```

现在，让我们测试这些验证：

```python
# tests/test_user_validations.py
import pytest
from pydantic import ValidationError as PydanticValidationError # Pydantic 的 ValidationError 别名
from your_app.models import ValidatedUser
from rhosocial.activerecord.backend.errors import ValidationError as ActiveRecordValidationError

# ValidatedUser 模型的示例模式
VALIDATED_USER_SCHEMA = """
CREATE TABLE validated_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    age INTEGER
);
"""

@pytest.fixture
def configured_validated_user_model() -> Type[ValidatedUser]:
    """
    为每个测试提供一个配置好的 ValidatedUser 模型和干净的表。
    """
    return _setup_model_for_testing(ValidatedUser, "memory", VALIDATED_USER_SCHEMA)

def test_username_length_validation(configured_validated_user_model: Type[ValidatedUser]):
    """测试 Pydantic 的 min_length/max_length 用户名验证。"""
    with pytest.raises(PydanticValidationError, match="username"):
        configured_validated_user_model.create(username='ab', email='test@example.com')
    with pytest.raises(PydanticValidationError, match="username"):
        configured_validated_user_model.create(username='a_very_long_username_that_exceeds_fifty_characters_limit', email='test@example.com')

def test_username_custom_validation(configured_validated_user_model: Type[ValidatedUser]):
    """测试自定义 @field_validator 的用户名验证。"""
    with pytest.raises(ActiveRecordValidationError, match="用户名不能包含前导或尾随空格"):
        configured_validated_user_model.create(username='  testuser', email='test@example.com')
    with pytest.raises(ActiveRecordValidationError, match="用户名必须是字母数字"):
        configured_validated_user_model.create(username='test-user', email='test@example.com')

def test_email_format_validation(configured_validated_user_model: Type[ValidatedUser]):
    """测试 Pydantic 的 EmailStr 电子邮件验证。"""
    with pytest.raises(PydanticValidationError, match="email"):
        configured_validated_user_model.create(username='testuser', email='not-an-email')

def test_age_business_rule_validation(configured_validated_user_model: Type[ValidatedUser]):
    """测试年龄的自定义业务逻辑验证。"""
    with pytest.raises(ActiveRecordValidationError, match="用户必须至少 13 岁"):
        configured_validated_user_model.create(username='childuser', email='child@example.com', age=10)
```

## 测试类型映射

为了测试 `ActiveRecord` 如何处理各种数据类型，我们可以使用类似于 `testsuite` fixture 中的 `TypeCase` 模型，它包含各种常见类型。

```python
# 假设此 TypeCase 模型定义在 your_app/models.py 中
from datetime import date, time, datetime
from decimal import Decimal
from typing import Optional
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.field import UUIDMixin # 提供 uuid 主键

class TypeCase(UUIDMixin, ActiveRecord):
    __table_name__ = "type_cases"
    # id: UUID 字段由 UUIDMixin 提供
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
```

现在，让我们测试其中一些类型。请记住，`ActiveRecord` 使用 `TypeRegistry` 和 `SQLTypeAdapter` 进行这些转换，如 [数据类型映射指南](./data_type_mapping.md) 中所述。

```python
# tests/test_type_case.py
import pytest
import uuid
from datetime import date, time, datetime
from decimal import Decimal
from your_app.models import TypeCase

# TypeCase 模型的示例模式 (简化)
TYPE_CASE_SCHEMA = """
CREATE TABLE type_cases (
    id VARCHAR(36) PRIMARY KEY, -- UUID
    username VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    tiny_int INTEGER,
    small_int INTEGER,
    big_int INTEGER,
    float_val REAL,
    double_val REAL,
    decimal_val TEXT, -- 在 SQLite 中以 TEXT 存储以实现 Decimal 精度
    char_val VARCHAR(1),
    varchar_val VARCHAR(255),
    text_val TEXT,
    date_val TEXT,     -- 以 TEXT 存储 (ISO 格式)
    time_val TEXT,     -- 以 TEXT 存储 (ISO 格式)
    timestamp_val TEXT, -- 以 TEXT 存储 (ISO 格式)
    blob_val BLOB,
    json_val TEXT,     -- 以 TEXT 存储 (JSON 字符串)
    array_val TEXT,    -- 以 TEXT 存储 (JSON 字符串)
    is_active BOOLEAN
);
"""

@pytest.fixture
def configured_type_case_model() -> Type[TypeCase]:
    """
    为每个测试提供一个配置好的 TypeCase 模型和干净的数据库表。
    """
    return _setup_model_for_testing(TypeCase, "memory", TYPE_CASE_SCHEMA)

def test_type_case_all_types(configured_type_case_model: Type[TypeCase]):
    """测试写入和读取所有支持的数据类型。"""
    test_uuid = uuid.uuid4()
    test_date = date(2023, 1, 15)
    test_time = time(14, 30, 45)
    test_datetime = datetime(2023, 1, 15, 14, 30, 45, 123456)
    test_decimal = Decimal("12345.6789")
    test_blob = b"binary_data"
    test_json = {"key": "value", "list": [1, 2, {"nested": True}]}
    test_array = ["item1", 123, {"obj_item": "data"}]

    tc_instance = configured_type_case_model.create(
        id=test_uuid,
        username="typetest",
        email="type@example.com",
        tiny_int=1,
        small_int=100,
        big_int=10000000000,
        float_val=1.23,
        double_val=1.23456789,
        decimal_val=test_decimal,
        char_val="A",
        varchar_val="short string",
        text_val="a very long string that needs to be stored as text",
        date_val=test_date,
        time_val=test_time,
        timestamp_val=test_datetime,
        blob_val=test_blob,
        json_val=test_json,
        array_val=test_array,
        is_active=False
    )

    retrieved_tc = configured_type_case_model.find(tc_instance.id)

    assert retrieved_tc.id == test_uuid
    assert retrieved_tc.username == "typetest"
    assert retrieved_tc.email == "type@example.com"
    assert retrieved_tc.tiny_int == 1
    assert retrieved_tc.small_int == 100
    assert retrieved_tc.big_int == 10000000000
    assert retrieved_tc.float_val == pytest.approx(1.23)
    assert retrieved_tc.double_val == pytest.approx(1.23456789)
    assert retrieved_tc.decimal_val == test_decimal
    assert retrieved_tc.char_val == "A"
    assert retrieved_tc.varchar_val == "short string"
    assert retrieved_tc.text_val == "a very long string that needs to be stored as text"
    assert retrieved_tc.date_val == test_date
    assert retrieved_tc.time_val == test_time
    # SQLite datetime 精度可能不同，如果需要，比较到秒/微秒
    assert retrieved_tc.timestamp_val.isoformat(timespec='microseconds') == test_datetime.isoformat(timespec='microseconds')
    assert retrieved_tc.blob_val == test_blob
    assert retrieved_tc.json_val == test_json
    assert retrieved_tc.array_val == test_array
    assert retrieved_tc.is_active is False
```

## 测试自定义类型适配器

正如 [数据类型映射指南](./data_type_mapping.md) 中讨论的，自定义 `SQLTypeAdapter` 对于处理原生不支持或需要自定义序列化的特定数据类型至关重要。测试它们时，您需要确保它们已正确注册到模型的后端*之前*，模型与数据库交互。

让我们重新审视假设的 `Money` 类型和 `您的_MoneyAdapter` 示例。

```python
# your_app/types.py
from decimal import Decimal
from typing import Any, Dict, List, Optional, Type
from rhosocial.activerecord.backend.type_adapter import SQLTypeAdapter

class Money:
    def __init__(self, amount: Decimal, currency: str):
        self.amount = amount
        self.currency = currency
    
    def __eq__(self, other): # 对于测试相等性很重要
        if not isinstance(other, Money):
            return NotImplemented
        return self.amount == other.amount and self.currency == other.currency

class 您的_MoneyAdapter(SQLTypeAdapter):
    @property
    def supported_types(self) -> Dict[Type, List[Any]]:
        return {Money: ["TEXT"]}

    def to_database(self, value: Money, target_type: Type, options: Optional[Dict[str, Any]] = None) -> Any:
        # 简化：将 Money 对象转换为字符串，例如 "19.99,USD"
        return f"{value.amount},{value.currency}"
    
    def from_database(self, value: str, target_type: Type, options: Optional[Dict[str, Any]] = None) -> Any:
        # 简化：将 "19.99,USD" 字符串转换回 Money 对象
        amount, currency = value.split(',')
        return Money(Decimal(amount), currency)

# your_app/models.py
from rhosocial.activerecord.model import ActiveRecord
from pydantic import Field
from .types import Money

class Product(ActiveRecord):
    __table_name__ = "products_money"
    id: Optional[int] = Field(None, primary_key=True)
    name: str
    price: Money # 模型使用自定义 Money 类型
```

现在，测试此 `Product` 模型时，您需要一个 fixture 来配置模型并将其 `您的_MoneyAdapter` 注册到其后端。

```python
# tests/test_product_money_adapter.py
import pytest
from decimal import Decimal
from your_app.models import Product
from your_app.types import Money, 您的_MoneyAdapter
from rhosocial.activerecord.backend.errors import UnregisteredAdapterError # 用于注销

# Product 模型的示例模式
PRODUCT_MONEY_SCHEMA = """
CREATE TABLE products_money (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR(255) NOT NULL,
    price TEXT -- 价格以 TEXT 存储在 DB 中
);
"""

@pytest.fixture
def configured_product_model_with_money_adapter() -> Type[Product]:
    """
    设置 Product 模型进行测试，包括其模式和自定义适配器。
    """
    # 使用助手函数配置模型。
    configured_model = _setup_model_for_testing(Product, "memory", PRODUCT_MONEY_SCHEMA)

    # 将自定义 您的_MoneyAdapter 注册到模型的后端
    backend = configured_model.backend()
    adapter = 您的_MoneyAdapter()
    backend.adapter_registry.register(adapter, Money, "TEXT")

    yield configured_model

    # 清理：测试后注销适配器
    # 注意：在实际场景中，您可能需要更健壮的注册表清理
    # 或依赖于内存数据库提供的测试隔离。
    try:
        backend.adapter_registry.unregister(Money, "TEXT")
    except UnregisteredAdapterError:
        pass # 已注销或未找到
```

通过配置模型和注册适配器，您可以测试其行为：

```python
# tests/test_product_money_adapter.py (续)
def test_money_type_adapter_write_and_read(configured_product_model_with_money_adapter: Type[Product]):
    """
    测试 您的_MoneyAdapter 是否通过模型正确写入和读取自定义类型。
    """
    # 1. 使用 Money 对象创建产品
    initial_price = Money(Decimal("19.99"), "USD")
    product = configured_product_model_with_money_adapter.create(name="Test Product", price=initial_price)
    product_id = product.id

    # 2. 从数据库中检索产品
    retrieved_product = configured_product_model_with_money_adapter.find(product_id)

    # 3. 验证 `from_database` 转换是否成功
    assert isinstance(retrieved_product.price, Money)
    assert retrieved_product.price == initial_price # 使用 Money 类中的 __eq__

    # 4. 直接检查原始数据库值以确认 `to_database` 转换
    # 这需要直接使用模型的后端。
    raw_data = configured_product_model_with_money_adapter.backend().execute_and_fetch_one(
        f"SELECT price FROM {configured_product_model_with_money_adapter.__table_name__} WHERE id=?",
        params=[product_id]
    )
    assert raw_data['price'] == "19.99,USD"
```

## 测试套件的最佳实践

*   **隔离**: 每个测试都应在隔离的环境中运行。提供者（或您本地的测试辅助函数，如 `_setup_model_for_testing`）通过为每个测试配置新的数据库连接和模式来确保这一点，通常使用内存数据库（例如 SQLite `:memory:`）。
*   **基于场景的测试**: `testsuite` 使用不同的场景（例如内存中、基于文件的 SQLite、不同的 pragmas）在各种条件下测试模型。这确保了跨部署环境的鲁棒性。
*   **清晰的模式定义**: 保持您的测试数据库模式清晰和独立。在 `testsuite` 提供者中，这些通常从 `.sql` 文件加载，从而提高了清晰度和可维护性。
*   **参数化 Fixture**: 利用 `pytest` fixture，可能通过场景进行参数化，以避免代码重复并确保在不同后端配置下进行彻底测试。
*   **关注 `ActiveRecord` API**: 尽管提供者处理低级设置，但您的测试应主要与 `ActiveRecord` 模型的公共 API（`.create`、`.find`、`.update`、`.destroy`、`.query`）交互。后端直接执行方法（`.execute`、`.execute_and_fetch_one`）应谨慎使用，主要用于验证中间状态（例如用于适配器测试的原始数据库值）或非常低级的后端功能测试。
*   **别名化 Pydantic 错误**: 如果您的模型同时使用 Pydantic 的 `ValidationError` 和框架的 `ActiveRecordValidationError`（例如用于自定义业务逻辑），请考虑对其进行别名化以避免混淆，如验证示例所示。