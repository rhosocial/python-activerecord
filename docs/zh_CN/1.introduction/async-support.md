# 异步支持

**尚未实现** - 异步功能目前只在后端实现，ActiveRecord/ActiveQuery 层面尚未实现。

未来，ActiveRecord/ActiveQuery 层面的同步或异步使用能力将取决于后端支持。目前，SQLite 后端不提供异步支持，而 MySQL 和 PostgreSQL 后端则同时提供同步和异步支持。

rhosocial ActiveRecord 提供了精心设计的异步接口，这使其与许多竞争对手的 ORM 有所不同。异步支持方法优先考虑可用性、灵活性和向后兼容性。

## 双 API 架构

该框架通过精心设计提供同步和异步接口：

- **完整的 API 对等性**：异步 API 镜像同步 API，使在两种模式之间切换变得容易
- **最小认知开销**：同步和异步代码中的类似模式
- **渐进式采用**：现有同步代码可以与新的异步代码共存

## 灵活的实现选项

开发者可以根据需求选择多种实现策略：

### 1. 独立定义

这种方法提供完全向后兼容性和清晰分离：

```python
# 同步模型
class User(BaseActiveRecord):
    __table_name__ = 'users'
    id: Optional[int] = None
    name: str
    email: str
    
    def get_full_info(self):
        return f"{self.name} <{self.email}>"

# 异步模型
class AsyncUser(AsyncBaseActiveRecord):
    __table_name__ = 'users'
    id: Optional[int] = None
    name: str
    email: str
    
    def get_full_info(self):
        return f"{self.name} <{self.email}>"
```

### 2. 混合继承

这种方法通过结合同步和异步功能减少代码重复：

```python
# 具有同步和异步功能的组合模型
class User(BaseActiveRecord, AsyncBaseActiveRecord):
    __table_name__ = 'users'
    id: Optional[int] = None
    name: str
    email: str
    
    def get_full_info(self):
        return f"{self.name} <{self.email}>"
```

## 数据库后端兼容性

该库的异步操作架构旨在通过原生异步数据库驱动实现真正的非阻塞I/O。

- **原生异步驱动**: 对于通过网络操作的数据库（如 PostgreSQL 和 MySQL），异步后端旨在利用原生异步驱动。这种方法非常适合高并发应用。目前支持的同步驱动是用于 PostgreSQL 的 `psycopg` 和用于 MySQL 的 `mysql-connector-python`。
- **关于 SQLite 的说明**: 我们特意没有提供针对 SQLite 的异步后端。Python 标准库中的 `sqlite3` 不提供原生异步 API。虽然可以通过线程池等方式模拟异步行为，但我们选择避免这种做法。SQLite 作为一个嵌入式的进程内数据库，其 I/O 操作通常是与文件系统绑定且速度极快。模拟异步会引入开销和复杂性，却无法带来 `asyncio` 旨在解决的真正的非阻塞网络 I/O 优势，甚至可能降低性能。

## 异步使用示例

### 基本 CRUD 操作

```python
# 创建
user = AsyncUser(name="John Doe", email="john@example.com")
await user.save()

# 读取
user = await AsyncUser.find_one(1)  # 通过主键
active_users = await AsyncUser.query().where('is_active = ?', (True,)).all()

# 更新
user.name = "Jane Doe"
await user.save()

# 删除
await user.delete()
```

### 事务

```python
async def transfer_funds(from_account_id, to_account_id, amount):
    async with AsyncAccount.transaction():
        from_account = await AsyncAccount.find_one(from_account_id)
        to_account = await AsyncAccount.find_one(to_account_id)
        
        from_account.balance -= amount
        to_account.balance += amount
        
        await from_account.save()
        await to_account.save()
```

### 复杂查询

```python
async def get_department_statistics():
    return await AsyncEmployee.query()
        .group_by('department')
        .count('id', 'employee_count')
        .avg('salary', 'avg_salary')
        .min('hire_date', 'earliest_hire')
        .aggregate()
```

## 与其他 ORM 的比较

- **vs SQLAlchemy**：与 SQLAlchemy 1.4+ 的方法相比，更直观的异步 API，同步/异步对等性更好
- **vs Django ORM**：与 Django 有限的异步功能相比，更全面的异步支持
- **vs Peewee**：集成的异步支持，而不是 Peewee 的单独 peewee-async 扩展

rhosocial ActiveRecord 的异步功能使其特别适合需要高性能和可扩展性的现代 Python 应用程序，尤其是与 FastAPI 等异步 Web 框架结合使用时。