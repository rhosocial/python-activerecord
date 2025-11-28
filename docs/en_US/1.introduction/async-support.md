# Asynchronous Support

**YET NOT IMPLEMENTED** - Async functionality is currently only implemented at the backend level, not at the ActiveRecord/ActiveQuery level.

rhosocial ActiveRecord provides a well-designed asynchronous interface, distinguishing it from many competing ORMs.
The approach to async support prioritizes usability, flexibility, and backward compatibility.

## Dual API Architecture

The framework offers both synchronous and asynchronous interfaces through a thoughtful design:

- **Complete API Parity**: The async API mirrors the sync API, making it easy to switch between modes
- **Minimal Cognitive Overhead**: Similar patterns in both sync and async code
- **Progressive Adoption**: Existing synchronous code can coexist with new asynchronous code

## Flexible Implementation Options

Developers can choose from multiple implementation strategies based on their needs:

### 1. Separate Definitions

This approach provides full backward compatibility and clear separation:

```python
# Synchronous model
class User(BaseActiveRecord):
    __table_name__ = 'users'
    id: Optional[int] = None
    name: str
    email: str
    
    def get_full_info(self):
        return f"{self.name} <{self.email}>"

# Asynchronous model
class AsyncUser(AsyncBaseActiveRecord):
    __table_name__ = 'users'
    id: Optional[int] = None
    name: str
    email: str
    
    def get_full_info(self):
        return f"{self.name} <{self.email}>"
```

### 2. Mixin Inheritance

This approach reduces code duplication by combining sync and async capabilities:

```python
# Combined model with both sync and async capabilities
class User(BaseActiveRecord, AsyncBaseActiveRecord):
    __table_name__ = 'users'
    id: Optional[int] = None
    name: str
    email: str
    
    def get_full_info(self):
        return f"{self.name} <{self.email}>"
```

## Database Backend Compatibility

The library's architecture for asynchronous operations is designed to use native asynchronous database drivers to achieve true non-blocking I/O.

- **Native Async Drivers**: For databases that operate over a network (like PostgreSQL and MySQL), the asynchronous backend is built to leverage native async drivers. This approach is ideal for high-concurrency applications. The currently supported synchronous drivers are `psycopg` for PostgreSQL and `mysql-connector-python` for MySQL.
- **A Note on SQLite**: An asynchronous backend for SQLite is intentionally not provided. The standard `sqlite3` library in Python does not offer a native asynchronous API. While it is possible to simulate async behavior (e.g., using a thread pool), this approach was avoided. SQLite, as an embedded, in-process database, has I/O operations that are typically file-system-bound and extremely fast. Simulating async would introduce overhead and complexity without the true non-blocking network I/O benefits that `asyncio` is designed for, and could even degrade performance.

## Async Usage Examples

### Basic CRUD Operations

```python
# Create
user = AsyncUser(name="John Doe", email="john@example.com")
await user.save()

# Read
user = await AsyncUser.find_one(1)  # By primary key
active_users = await AsyncUser.query().where('is_active = ?', (True,)).all()

# Update
user.name = "Jane Doe"
await user.save()

# Delete
await user.delete()
```

### Transactions

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

### Complex Queries

```python
async def get_department_statistics():
    return await AsyncEmployee.query()
        .group_by('department')
        .count('id', 'employee_count')
        .avg('salary', 'avg_salary')
        .min('hire_date', 'earliest_hire')
        .aggregate()
```

## Comparison with Other ORMs

- **vs SQLAlchemy**: More intuitive async API with better sync/async parity compared to SQLAlchemy 1.4+'s approach
- **vs Django ORM**: More comprehensive async support compared to Django's limited async capabilities
- **vs Peewee**: Integrated async support versus Peewee's separate peewee-async extension

The asynchronous capabilities of rhosocial ActiveRecord make it particularly well-suited for modern Python applications
that require high performance and scalability, especially when combined with async web frameworks like FastAPI.