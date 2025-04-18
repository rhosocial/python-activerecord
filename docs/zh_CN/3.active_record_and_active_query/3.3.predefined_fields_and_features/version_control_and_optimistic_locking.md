# 版本控制和乐观锁

乐观锁是一种并发控制方法，它允许多个用户访问同一条记录进行编辑，同时防止意外覆盖更改。rhosocial ActiveRecord提供了`OptimisticLockMixin`来在您的模型中实现这种模式。

## 概述

`OptimisticLockMixin`为您的模型添加了一个`version`字段。每次记录更新时，此版本号都会递增。在保存更改之前，系统会验证数据库中的版本号与记录加载时的版本号是否匹配。如果它们不匹配，则表示在此期间有其他人修改了记录，并会引发错误。

这种方法被称为"乐观"锁定，因为它假设冲突很少见，只在保存时检查冲突，而不是预先锁定记录。

## 基本用法

要向模型添加乐观锁，请在类定义中包含`OptimisticLockMixin`：

```python
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.field import OptimisticLockMixin

class Account(OptimisticLockMixin, ActiveRecord):
    __table_name__ = 'accounts'
    
    name: str
    balance: float
```

使用此设置，`version`字段将被自动管理：

```python
# 创建一个新账户
account = Account(name="张三", balance=1000.0)
account.save()

# 新记录的版本设置为1
print(account.version)  # 1

# 更新账户
account.balance = 1500.0
account.save()

# 版本会自动递增
print(account.version)  # 2

# 如果另一个进程在您保存更改之前更新了同一条记录
# 将引发错误
```

## 处理并发更新

当检测到并发更新时，会引发`DatabaseError`。您可以捕获此异常并适当处理：

```python
from rhosocial.activerecord.backend import DatabaseError

try:
    account.balance += 100.0
    account.save()
except DatabaseError as e:
    if "Record was updated by another process" in str(e):
        # 处理冲突
        # 例如，重新加载记录并重新应用更改
        fresh_account = Account.find(account.id)
        fresh_account.balance += 100.0
        fresh_account.save()
    else:
        # 处理其他数据库错误
        raise
```

## 工作原理

`OptimisticLockMixin`通过以下方式工作：

1. 向您的模型添加一个`version`字段（存储为私有属性`_version`）
2. 为`AFTER_SAVE`事件注册处理程序以更新版本
3. 向更新查询添加版本检查条件
4. 在成功更新后递增版本号

以下是实现的简化视图：

```python
class OptimisticLockMixin(IUpdateBehavior, IActiveRecord):
    _version: Version = Version(value=1, increment_by=1)

    def __init__(self, **data):
        super().__init__(**data)
        version_value = data.get('version', 1)
        self._version = Version(value=version_value, increment_by=1)
        self.on(ModelEvent.AFTER_SAVE, self._handle_version_after_save)

    @property
    def version(self) -> int:
        return self._version.value

    def get_update_conditions(self):
        # 向更新条件添加版本检查
        condition, params = self._version.get_update_condition()
        return [(condition, params)]

    def get_update_expressions(self):
        # 向更新表达式添加版本递增
        return {
            self._version.db_column: self._version.get_update_expression(self.backend())
        }

    def _handle_version_after_save(self, instance, is_new=False, result=None, **kwargs):
        if not is_new:
            if result.affected_rows == 0:
                raise DatabaseError("Record was updated by another process")
            self._version.increment()
```

## 数据库考虑因素

要使用乐观锁，您的数据库表必须包含一个用于版本号的列。默认情况下，此列名为`version`，应为整数类型。您可以通过修改`_version`属性的`db_column`属性来自定义列名。

创建支持版本的表的示例SQL：

```sql
CREATE TABLE accounts (
    id INTEGER PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    balance DECIMAL(10, 2) NOT NULL,
    version INTEGER NOT NULL DEFAULT 1
);
```

## 与其他混入结合

`OptimisticLockMixin`与其他混入（如`TimestampMixin`和`SoftDeleteMixin`）配合良好：

```python
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.field import TimestampMixin, OptimisticLockMixin, SoftDeleteMixin

class Account(TimestampMixin, OptimisticLockMixin, SoftDeleteMixin, ActiveRecord):
    __table_name__ = 'accounts'
    
    name: str
    balance: float
```

使用此设置，您将拥有：
- `created_at`：记录创建时间
- `updated_at`：记录最后更新时间
- `version`：用于乐观锁的当前版本号
- `deleted_at`：记录软删除时间（如果未删除，则为`None`）

## 最佳实践

1. **与时间戳字段一起使用**：将乐观锁与时间戳字段结合使用，提供版本控制和时间信息。

2. **优雅处理冲突**：当冲突发生时，提供用户友好的方式来解决冲突。

3. **考虑性能**：乐观锁会向每个更新查询添加额外条件，这可能会影响高容量系统的性能。

4. **自定义递增值**：对于频繁更新的记录，考虑使用更大的递增值以避免达到整数限制。

## 下一步

现在您了解了乐观锁，您可能想要探索：

- [悲观锁策略](pessimistic_locking_strategies.md) - 用于更强的并发控制
- [软删除机制](soft_delete_mechanism.md) - 用于记录的逻辑删除
- [自定义字段](custom_fields.md) - 用于扩展模型功能