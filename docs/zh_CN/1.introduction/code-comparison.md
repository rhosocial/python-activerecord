# 代码比较

让我们比较一下这些 ORM 中常见的数据库操作：

## 定义模型

**rhosocial ActiveRecord**:
```python
from activerecord import ActiveRecord
from typing import Optional
from datetime import datetime
from pydantic import EmailStr, field_validator

class User(ActiveRecord):
    __table_name__ = 'users'
    
    id: Optional[int] = None
    name: str
    email: EmailStr
    is_active: bool = True
    created_at: datetime = None
    
    @field_validator('email')
    def validate_email_domain(cls, v):
        if '@example.com' in v:
            raise ValueError("Example domains not allowed")
        return v
```

**SQLAlchemy**:
```python
from sqlalchemy import Column, Integer, String, Boolean, DateTime, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=func.now())
    
    @validates('email')
    def validate_email(self, key, email):
        if '@example.com' in email:
            raise ValueError("Example domains not allowed")
        return email
```

**Django ORM**:
```python
from django.db import models
from django.core.exceptions import ValidationError

def validate_email(value):
    if '@example.com' in value:
        raise ValidationError("Example domains not allowed")

class User(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True, validators=[validate_email])
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'users'
```

**Peewee**:
```python
from peewee import *
from datetime import datetime

db = SqliteDatabase('my_app.db')

class User(Model):
    name = CharField(max_length=100)
    email = CharField(unique=True)
    is_active = BooleanField(default=True)
    created_at = DateTimeField(default=datetime.now)
    
    def save(self, *args, **kwargs):
        if '@example.com' in self.email:
            raise ValueError("Example domains not allowed")
        return super(User, self).save(*args, **kwargs)
    
    class Meta:
        database = db
        table_name = 'users'
```

## CRUD 操作

**rhosocial ActiveRecord**:
```python
# 创建
user = User(name="John Doe", email="john@domain.com")
user.save()  # 返回受影响的行数

# 读取
user = User.find_one(1)  # 通过主键
active_users = User.query().where('is_active = ?', (True,)).all()

# 更新
user.name = "Jane Doe"
user.save()

# 删除
user.delete()  # 返回受影响的行数
```

**SQLAlchemy**:
```python
from sqlalchemy.orm import Session

# 创建
session = Session(engine)
user = User(name="John Doe", email="john@domain.com")
session.add(user)
session.commit()

# 读取
user = session.query(User).get(1)  # 通过主键
active_users = session.query(User).filter(User.is_active == True).all()

# 更新
user.name = "Jane Doe"
session.commit()

# 删除
session.delete(user)
session.commit()
```

**Django ORM**:
```python
# 创建
user = User.objects.create(name="John Doe", email="john@domain.com")

# 读取
user = User.objects.get(id=1)  # 通过主键
active_users = User.objects.filter(is_active=True)

# 更新
user.name = "Jane Doe"
user.save()

# 删除
user.delete()
```

**Peewee**:
```python
# 创建
user = User.create(name="John Doe", email="john@domain.com")

# 读取
user = User.get_by_id(1)  # 通过主键
active_users = User.select().where(User.is_active == True)

# 更新
user.name = "Jane Doe"
user.save()

# 删除
user.delete_instance()
```

## 异步操作

**rhosocial ActiveRecord**:
```python
# 创建
user = AsyncUser(name="John Doe", email="john@domain.com")
await user.save()

# 读取
user = await AsyncUser.find_one(1)
active_users = await AsyncUser.query().where('is_active = ?', (True,)).all()

# 更新
user.name = "Jane Doe"
await user.save()

# 删除
await user.delete()

# 事务
async with AsyncUser.transaction():
    user = await AsyncUser.find_one(1)
    user.status = 'inactive'
    await user.save()
```

**SQLAlchemy**:
```python
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

# 创建
async with AsyncSession(engine) as session:
    user = User(name="John Doe", email="john@domain.com")
    session.add(user)
    await session.commit()

# 读取
async with AsyncSession(engine) as session:
    user = await session.get(User, 1)
    query = select(User).where(User.is_active == True)
    result = await session.execute(query)
    active_users = result.scalars().all()

# 更新
async with AsyncSession(engine) as session:
    user = await session.get(User, 1)
    user.name = "Jane Doe"
    await session.commit()

# 删除
async with AsyncSession(engine) as session:
    user = await session.get(User, 1)
    await session.delete(user)
    await session.commit()

# 事务
async with AsyncSession(engine) as session:
    async with session.begin():
        user = await session.get(User, 1)
        user.status = 'inactive'
```

**Django ORM**:
```python
# 读取
user = await User.objects.aget(id=1)
active_users = [user async for user in User.objects.filter(is_active=True)]

# 注意：Django ORM 有限的异步支持 - 许多操作
# 仍然需要同步代码或 sync_to_async 包装器
```

**Peewee with peewee-async**:
```python
import asyncio
import peewee_async

database = peewee_async.PostgresqlDatabase('test')
objects = peewee_async.Manager(database)

# 创建
user = User(name="John Doe", email="john@domain.com")
await objects.create(user)

# 读取
user = await objects.get(User, id=1)
active_users = await objects.execute(User.select().where(User.is_active == True))

# 更新
user = await objects.get(User, id=1)
user.name = "Jane Doe"
await objects.update(user)

# 删除
user = await objects.get(User, id=1)
await objects.delete(user)
```