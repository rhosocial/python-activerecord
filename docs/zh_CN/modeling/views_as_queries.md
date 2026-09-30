# 把视图写成查询

**视图就是一个查询。** `CREATE VIEW v AS SELECT ...` 除了查询本身什么都没存。
如果框架把视图建模成表，就得凭空发明名称、生命周期和内省机制，
去描述一个本来就能拿在变量里的表达式。

因此本框架不提供视图模型。用封装的 `ActiveQuery` 来表达视图。

> **物化视图**不同：它有实体、有名字、有存储成本、有刷新周期。那是真正值得建模的东西，
> 并且单独处理——只读的那一半见 [只读模型](readonly_models.md)。

---

## 1. 视图就是可复用的查询

从模型出发，把定义视图的部分预设好，返回查询：

```python
from rhosocial.activerecord.model import ActiveRecord

class Order(ActiveRecord):
    __table_name__ = "orders"
    id: int
    status: str
    total: float
    created_at: str

def open_orders():
    """“未完成订单”视图：只有状态过滤和排序。"""
    return Order.query().where(Order.c.status == "open").order_by(Order.c.created_at.desc())

rows = open_orders().limit(50).all()
total = open_orders().count()
```

这就是一个视图，而且是带参数的。同一个视图形状配上参数，是 SQL 视图做不到的：

```python
def orders_since(cutoff):
    return (
        Order.query()
        .where(Order.c.status == "open", Order.c.created_at >= cutoff)
        .order_by(Order.c.created_at.desc())
    )
```

一份定义，任意时间窗。而命名一个数据库视图 `open_orders_since` 意味着每个时间窗一个新对象。

---

## 2. 三种常见形状

### 过滤

```python
def paid_orders():
    return Order.query().where(Order.c.status == "paid")
```

### 聚合

两张表，一个分组。`aggregate()` 返回行而非模型实例：

```python
def revenue_by_customer(Customer, Order):
    return (
        Order.query()
        .join(Customer, on=Order.c.customer_id == Customer.c.id)
        .select(Customer.c.name, functions.sum(Order.c.total))
        .group_by(Customer.c.name)
        .aggregate()
    )

for row in revenue_by_customer(Customer, Order):
    print(row["name"], row[list(row)[1]])
```

### 投影

收窄列集合——注意显式别名，它保证结果可按键寻址：

```python
def order_summary():
    return Order.query().select(Order.c.id, Order.c.status.as_("state")).limit(20)
```

> **联结时慎用 `SELECT *`。** 两张表常常都有 `id`，裸的 `SELECT *` 会以同名输出两列，
> 而行映射会保留最后一个。联结时请用 `select()` 收窄投影。

---

## 3. 获得类型化实例

普通 `ActiveQuery` 返回的是它的 `model_class` 对应的实例。当想要的形状
*不是*表的形状时，为它声明一个模型，让查询提供数据行：

```python
class OrderSummary(ActiveRecord):
    __table_name__ = "orders"
    __primary_key__ = None                 # 不可按主键寻址
    id: int
    state: str
    total: float

def open_order_summaries():
    return OrderSummary.query().select(
        OrderSummary.c.id,
        OrderSummary.c.status.as_("state"),
        OrderSummary.c.total,
    ).where(OrderSummary.c.status == "open")
```

模型提供字段名与类型，查询提供投影。映射到已存储结果集（物化视图、外部表）的模型
正是这个形状，只是 `__table_name__` 指向存储对象而不是表。

---

## 4. 何时仍应创建数据库视图

Python 查询并非总是正确答案。以下情况应使用 `CREATE VIEW`：

| 需求 | 数据库视图更合适的原因 |
| --- | --- |
| **跨进程共享** | 多个服务需要同一份定义 |
| **权限边界** | 只授予视图的 `SELECT`，而不是基表的 |
| **需要查询优化器介入** | 带索引或过滤的视图可在服务端优化 |
| **遗留消费方** | 无法改造为发出该查询的工具 |

创建视图可通过 DDL 层完成——见 [DDL 视图](ddl_views.md)。此后你有两种读取方式：
继续使用封装的查询（通常更好，因为它带参数），或让模型指向该存储对象。

---

## 5. 为什么不写成 `__table_name__ = "the_view"`

把 `__table_name__` 指向已存在的视图确实可行，对物化视图也正是预期用法。
但对普通视图则更差：

- 框架无法知道该视图是否可更新，因此无法判断写入是否合法——那需要内省，
  而内省会破坏模型元数据所依赖的"导入时零 IO"性质
- 模型暗示了一个稳定形状，而视图定义可以在其下被改动
- 同一份定义无法以不同参数复用

这并不是说它对物化视图错了——那里对象**确实**是一个存储关系。
它是说对普通视图错了：普通视图只是一个起了名字的查询。

---

## 相关文档

- [只读模型](readonly_models.md) —— 拒绝写入，以及只读模型
- [无主键模型](keyless_models.md) —— 没有主键的模型
- [DDL 视图](ddl_views.md) —— 通过 DDL 层创建视图
- [推导字段](derived_fields.md) —— SELECT 列表中的计算值
