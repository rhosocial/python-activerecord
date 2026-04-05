# 并发控制 (Concurrency)

在 Web 应用中，两个用户同时编辑同一篇文章是很常见的。如果没有锁，后提交的修改会覆盖先提交的。

## 乐观锁 (Optimistic Locking)

`OptimisticLockMixin` 通过增加一个 `version` 字段来解决此问题。

```python
from rhosocial.activerecord.field import OptimisticLockMixin

class Post(OptimisticLockMixin, ActiveRecord):
    title: str
```

**工作原理**:
1.  读取数据时，获取当前 `version` (如 1)。
2.  更新时，SQL 附加条件 `WHERE id = ... AND version = 1`。
3.  如果更新行数为 0，说明期间 `version` 已变（被别人改了），抛出 `StaleObjectError`。

```python
try:
    post.title = "New Title"
    post.save()
except StaleObjectError:
    print("数据已被修改，请刷新重试")
```

## 悲观锁 (Pessimistic Locking)

悲观锁通过在查询时锁定行来防止并发修改。`rhosocial-activerecord` 提供 `for_update()` 方法实现悲观锁。

### 基本用法

```python
# 转账场景：锁定用户行防止并发修改
def transfer(from_id: int, to_id: int, amount: float):
    with Account.transaction():
        # 按固定顺序锁定，避免死锁
        first_id, second_id = min(from_id, to_id), max(from_id, to_id)

        first = Account.query().where(Account.c.id == first_id).for_update().one()
        second = Account.query().where(Account.c.id == second_id).for_update().one()

        debit, credit = (first, second) if from_id < to_id else (second, first)
        debit.balance -= amount
        credit.balance += amount

        debit.save()
        credit.save()
```

### 后端支持情况

| 后端 | 支持级别 | 说明 |
|------|----------|------|
| MySQL | ✅ 完整支持 | InnoDB 行级锁 |
| PostgreSQL | ✅ 完整支持 | MVCC + 行级锁 |
| SQLite | ❌ 不支持 | 使用文件级锁 |

### 能力检测

编写跨数据库兼容代码时，使用 `supports_for_update()` 检测后端能力：

```python
dialect = Account.backend().dialect

if dialect.supports_for_update():
    # MySQL/PostgreSQL：使用 FOR UPDATE
    account = Account.query().where(Account.c.id == 1).for_update().one()
else:
    # SQLite：依赖文件锁或使用数据分区策略
    account = Account.find_one(1)
```

### 设计原则

`rhosocial-activerecord` 在 `FOR UPDATE` 支持上遵循「不替用户做选择」原则：

1. **默认拒绝**：`SQLDialectBase.supports_for_update()` 默认返回 `False`
2. **显式启用**：只有明确支持的后端（MySQL、PostgreSQL）才返回 `True`
3. **双层防御**：
   - ActiveQuery 层：调用 `for_update()` 时检测，不支持则抛错
   - Dialect 层：生成 SQL 时再次检测，作为安全网
4. **用户自主适配**：用户通过 `supports_for_update()` 判断后选择替代方案

### 死锁预防

使用悲观锁时需注意死锁预防：

1. **固定锁顺序**：始终按主键升序锁定资源
2. **短事务**：事务内只做必要操作
3. **数据分区**：将数据按 ID 范围分配给不同 Worker

```python
# ✅ 正确：按主键升序锁定
first_id, second_id = min(from_id, to_id), max(from_id, to_id)
first = Account.query().where(Account.c.id == first_id).for_update().one()
second = Account.query().where(Account.c.id == second_id).for_update().one()

# ❌ 错误：不同 Worker 可能以相反顺序锁定
account1 = Account.query().where(Account.c.id == from_id).for_update().one()
account2 = Account.query().where(Account.c.id == to_id).for_update().one()
```

### 乐观锁 vs 悲观锁选择

| 场景 | 推荐方案 | 原因 |
|------|----------|------|
| 冲突较少 | 乐观锁 | 无锁开销，吞吐量高 |
| 冲突频繁 | 悲观锁 | 避免频繁重试 |
| 需要强一致性 | 悲观锁 | 锁定期间保证数据不变 |
| 跨数据库兼容 | 乐观锁 | 所有后端都支持 |
