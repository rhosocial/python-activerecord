# 推导字段 (Derived Fields)

推导字段是一种**只读计算字段**，其值在查询时由数据库 SQL 表达式动态生成。它不存储在数据库表中，不会被 Pydantic 验证，也不会被脏字段跟踪。

典型用途：
- 价格计算（折扣价、含税价）
- 全名拼接（`first_name || ' ' || last_name`）
- 数据格式转换（JSON 提取、类型转换）
- 聚合结果的直接引用

## 声明方式

### 方式 A：直接赋值

```python
from typing import ClassVar
from decimal import Decimal
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.base.fields import DerivedField

class Product(ActiveRecord):
    __table_name__ = "products"
    id: int
    name: str
    price: Decimal

    discount_price: ClassVar[DerivedField] = DerivedField(
        lambda d: d.c.price * Decimal('0.9')
    )
```

`DerivedField` 接受一个回调函数，参数 `d` 是当前模型的 `FieldProxy` 对象，支持类型安全的表达式构建。

### 方式 B：使用 `Annotated`（推荐）

```python
from typing import ClassVar, Annotated
from decimal import Decimal
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.base.fields import DerivedField

class Product(ActiveRecord):
    __table_name__ = "products"
    id: int
    name: str
    price: Decimal

    discount_price: ClassVar[Annotated[Decimal, DerivedField(
        lambda d: d.c.price * Decimal('0.9')
    )]]
```

`Annotated` 方式更清楚地表达了字段类型，便于工具推断。

## 进阶用法

### 使用 `UseColumn` 指定 SQL 别名

```python
from rhosocial.activerecord.base.fields import UseColumn

total_price: ClassVar[Annotated[Decimal, DerivedField(
    lambda d: d.c.price * d.c.quantity
), UseColumn("total_price")]]
```

### 使用 `UseAdapter` 进行类型适配

```python
from rhosocial.activerecord.base.fields import UseAdapter

class JsonStringAdapter:
    @staticmethod
    def from_db(value, info):
        import json
        return json.dumps(value, ensure_ascii=False) if value else "{}"

    @staticmethod
    def to_db(value, info):
        import json
        return json.loads(value) if value else {}

metadata: ClassVar[Annotated[str, DerivedField(
    lambda d: d.c.raw_data,
), UseAdapter(JsonStringAdapter)]]
```

## 在查询中使用

使用 `derived` 参数控制是否加载推导字段：

```python
# 加载所有推导字段
products = Product.find_all(derived=True).all()
for p in products:
    print(f"{p.name}: ¥{p.price} -> ¥{p.discount_price}")

# 加载指定的推导字段
products = Product.find_all(derived=["discount_price"]).all()

# 使用自定义别名和表达式
products = Product.find_all(derived={
    "total": lambda d: d.c.price * d.c.quantity
}).all()
```

在 `ActiveQuery` 中也支持：

```python
products = Product.query().where(Product.c.price > 100).all(derived=True)
```

## 注意事项

1. **只读**：推导字段不可赋值，尝试赋值会被忽略。
2. **不验证**：推导字段不经过 Pydantic 验证器。
3. **不跟踪**：推导字段不会出现在脏字段跟踪中。
4. **列名冲突**：推导字段名不能与数据库列名冲突，否则会抛出 `ValueError`。
5. **性能**：推导字段在每次查询时都会生成 SQL 表达式，频繁使用需注意数据库端计算开销。
