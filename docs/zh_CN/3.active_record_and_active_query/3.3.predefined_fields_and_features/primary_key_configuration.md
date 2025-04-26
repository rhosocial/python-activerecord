# 主键配置

主键对于唯一标识数据库中的记录至关重要。rhosocial ActiveRecord为您的模型提供了灵活的主键配置选项。

## 默认主键

默认情况下，ActiveRecord假定您的模型有一个名为`id`的主键字段。这会自动为您处理，除非您想自定义其行为，否则不需要显式定义它。

```python
from rhosocial.activerecord import ActiveRecord

class Product(ActiveRecord):
    __tablename__ = 'products'
    
    name: str
    price: float
    # 'id'被隐式用作主键
```

## 自定义主键名称

如果您的表为主键使用不同的列名，您可以使用`__primary_key__`类属性指定它：

```python
from rhosocial.activerecord import ActiveRecord

class Product(ActiveRecord):
    __tablename__ = 'products'
    __primary_key__ = 'product_id'  # 使用'product_id'作为主键
    
    product_id: int
    name: str
    price: float
```

## 整数主键

对于具有整数主键的表，rhosocial ActiveRecord提供了`IntegerPKMixin`来简化处理：

```python
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.field import IntegerPKMixin

class Product(IntegerPKMixin, ActiveRecord):
    __tablename__ = 'products'
    
    name: str
    price: float
```

`IntegerPKMixin`自动将新记录的主键设置为`None`，允许数据库在保存记录时分配自动递增的值。

## UUID主键

对于需要全局唯一标识符的应用程序，rhosocial ActiveRecord提供了`UUIDMixin`用于基于UUID的主键：

```python
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.field import UUIDMixin

class Product(UUIDMixin, ActiveRecord):
    __tablename__ = 'products'
    
    name: str
    price: float
```

`UUIDMixin`在创建新记录时自动为主键生成新的UUID。这对于分布式系统或需要在将记录插入数据库之前生成ID特别有用。

## 复合主键

虽然不直接通过混入支持，但您可以通过重写`primary_key()`方法并在模型中自定义查询条件来实现复合主键：

```python
from rhosocial.activerecord import ActiveRecord

class OrderItem(ActiveRecord):
    __tablename__ = 'order_items'
    
    order_id: int
    item_id: int
    quantity: int
    price: float
    
    @classmethod
    def primary_key(cls):
        return ['order_id', 'item_id']
    
    # 您需要重写其他方法以正确处理复合键
```

## 通过主键查找记录

无论您如何配置主键，ActiveRecord都提供了一致的API来查找记录：

```python
# 通过主键查找
product = Product.find(1)  # 返回id=1的产品

# 通过主键查找多条记录
products = Product.find_all([1, 2, 3])  # 返回id为1、2和3的产品
```

## 数据库特定考虑因素

不同的数据库后端对主键的处理方式不同：

- **SQLite**：当定义为`INTEGER PRIMARY KEY`时，整数主键自动自增
- **MySQL/MariaDB**：使用`AUTO_INCREMENT`实现自增主键
- **PostgreSQL**：通常使用`SERIAL`或`BIGSERIAL`类型实现自增键

rhosocial ActiveRecord为您处理这些差异，但在设计架构时了解这些差异是有好处的。

## 最佳实践

1. **使用整数主键**用于大多数表，除非您有特定理由不这样做
2. **使用UUID主键**当您需要全局唯一标识符或在插入前生成ID时
3. **保持一致性**在整个应用程序中使用一致的主键命名约定
4. **考虑性能**影响，特别是UUID键可能影响索引和连接性能

## 下一步

现在您了解了如何配置主键，您可能想探索：

- [时间戳字段](timestamp_fields.md) - 用于自动创建和更新时间跟踪
- [关系](../relationships/README.md) - 用于定义模型之间的关联