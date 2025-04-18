# 从其他ORM迁移至ActiveRecord

## 介绍

从一个ORM框架迁移到另一个可能是一项重大工作。本指南提供了从流行的Python ORM（如SQLAlchemy、Django ORM和Peewee）迁移到rhosocial ActiveRecord的策略和最佳实践。我们将涵盖代码转换、数据迁移和测试方法，以确保平稳过渡。

## 通用迁移策略

### 1. 评估和规划

在开始迁移之前，进行彻底的评估：

- **清点现有模型**：记录所有模型、关系和自定义行为
- **识别ORM特定功能**：注意当前ORM中可能需要特殊处理的任何独特功能
- **分析查询模式**：审查应用程序如何与数据库交互
- **建立测试覆盖**：确保您有验证当前数据库功能的测试

### 2. 增量迁移与完全迁移

选择最适合您项目的迁移方法：

- **增量迁移**：一次转换一个模型和功能
  - 风险较低，允许逐步过渡
  - 需要ORM之间的临时兼容层
  - 更适合大型、复杂的应用程序

- **完全迁移**：一次性转换所有模型和功能
  - 概念上更简单，无需维护两个系统
  - 风险较高，需要更彻底的测试
  - 更适合较小的应用程序

## 从SQLAlchemy迁移

### 概念差异

| SQLAlchemy | rhosocial ActiveRecord |
|------------|---------------------|
| 显式会话管理 | 隐式连接管理 |
| 声明式模型定义 | 活动记录模式 |
| 通过Session API构建查询 | 模型类上的查询方法 |
| 在模型类中定义关系 | 模型类中的关系方法 |

### 模型转换示例

**SQLAlchemy模型：**

```python
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import datetime

Base = declarative_base()

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    username = Column(String(64), unique=True, nullable=False)
    email = Column(String(120), unique=True, nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    posts = relationship('Post', back_populates='author')
    
    def __repr__(self):
        return f'<User {self.username}>'

class Post(Base):
    __tablename__ = 'posts'
    
    id = Column(Integer, primary_key=True)
    title = Column(String(100), nullable=False)
    content = Column(String(10000), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    
    author = relationship('User', back_populates='posts')
    
    def __repr__(self):
        return f'<Post {self.title}>'
```

**等效的rhosocial ActiveRecord模型：**

```python
from rhosocial.activerecord import ActiveRecord
from typing import Optional
from datetime import datetime

class User(ActiveRecord):
    __table_name__ = 'users'
    
    id: int  # 主键，自动递增
    username: str  # 用户名，唯一，不允许为空
    email: str  # 电子邮件，唯一，不允许为空
    created_at: datetime  # 创建时间，自动设置为当前时间
    
    def __repr__(self):
        return f'<User {self.username}>'
    
    def posts(self):
        return self.has_many(Post, foreign_key='user_id')

class Post(ActiveRecord):
    __table_name__ = 'posts'
    
    id: int  # 主键，自动递增
    title: str  # 标题，不允许为空
    content: str  # 内容，不允许为空
    user_id: int  # 外键，关联到users表的id字段
    created_at: datetime  # 创建时间，自动设置为当前时间
    
    def __repr__(self):
        return f'<Post {self.title}>'
    
    def author(self):
        return self.belongs_to(User, foreign_key='user_id')
```

### 查询转换示例

**SQLAlchemy查询：**

```python
# 创建新用户
user = User(username='johndoe', email='john@example.com')
session.add(user)
session.commit()

# 通过主键查找用户
user = session.query(User).get(1)

# 按条件查找用户
user = session.query(User).filter(User.username == 'johndoe').first()

# 查找用户的所有帖子
posts = session.query(Post).filter(Post.user_id == user.id).all()

# 预加载关系
user_with_posts = session.query(User).options(joinedload(User.posts)).filter(User.id == 1).first()

# 更新用户
user.email = 'newemail@example.com'
session.commit()

# 删除用户
session.delete(user)
session.commit()
```

**等效的rhosocial ActiveRecord查询：**

```python
# 创建新用户
user = User(username='johndoe', email='john@example.com')
user.save()

# 通过主键查找用户
user = User.find_one(1)

# 按条件查找用户
user = User.find().where(User.username == 'johndoe').one()

# 查找用户的所有帖子
posts = Post.find().where(Post.user_id == user.id).all()

# 预加载关系
user_with_posts = User.find().with_('posts').where(User.id == 1).one()

# 更新用户
user.email = 'newemail@example.com'
user.save()

# 删除用户
user.delete()
```

## 从Django ORM迁移

### 概念差异

| Django ORM | rhosocial ActiveRecord |
|------------|---------------------|
| 与Django紧密集成 | 独立的ORM |
| 模型定义在应用特定的models.py中 | 模型可以在任何地方定义 |
| 迁移系统与Django绑定 | 独立的迁移系统 |
| QuerySet API | ActiveQuery API |

### 模型转换示例

**Django模型：**

```python
from django.db import models

class Category(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    
    class Meta:
        verbose_name_plural = 'Categories'
    
    def __str__(self):
        return self.name

class Product(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='products')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name
```

**等效的rhosocial ActiveRecord模型：**

```python
from rhosocial.activerecord import ActiveRecord
from typing import Optional
from datetime import datetime
from decimal import Decimal

class Category(ActiveRecord):
    name: str  # 名称
    description: Optional[str] = ''  # 描述，可为空，默认为空字符串
    
    def __str__(self):
        return self.name
    
    def products(self):
        return self.has_many(Product, foreign_key='category_id')

class Product(ActiveRecord):
    name: str  # 名称
    description: str  # 描述
    price: Decimal  # 价格，精度为10位，小数点后2位
    category_id: int  # 外键，关联到category表的id字段
    created_at: datetime  # 创建时间，自动设置为当前时间
    updated_at: datetime  # 更新时间，自动更新为当前时间
    is_active: bool = True  # 是否激活，默认为True
    
    def __str__(self):
        return self.name
    
    def category(self):
        return self.belongs_to(Category, foreign_key='category_id')
```

### 查询转换示例

**Django查询：**

```python
# 创建新分类
category = Category.objects.create(name='Electronics', description='Electronic devices')

# 创建产品
product = Product.objects.create(
    name='Smartphone',
    description='Latest model',
    price=599.99,
    category=category
)

# 获取所有产品
all_products = Product.objects.all()

# 过滤产品
active_products = Product.objects.filter(is_active=True)

# 复杂过滤
expensive_electronics = Product.objects.filter(
    category__name='Electronics',
    price__gt=500,
    is_active=True
)

# 排序
products_by_price = Product.objects.order_by('price')

# 限制结果
top_5_products = Product.objects.order_by('-created_at')[:5]

# 更新产品
product.price = 499.99
product.save()

# 删除产品
product.delete()
```

**等效的rhosocial ActiveRecord查询：**

```python
# 创建新分类
category = Category(name='Electronics', description='Electronic devices')
category.save()

# 创建产品
product = Product(
    name='Smartphone',
    description='Latest model',
    price=599.99,
    category_id=category.id
)
product.save()

# 获取所有产品
all_products = Product.find().all()

# 过滤产品
active_products = Product.find().where(Product.is_active == True).all()

# 复杂过滤
expensive_electronics = Product.find()\
    .join(Category, Product.category_id == Category.id)\
    .where(Category.name == 'Electronics')\
    .where(Product.price > 500)\
    .where(Product.is_active == True)\
    .all()

# 排序
products_by_price = Product.find().order_by(Product.price.asc()).all()

# 限制结果
top_5_products = Product.find().order_by(Product.created_at.desc()).limit(5).all()

# 更新产品
product.price = 499.99
product.save()

# 删除产品
product.delete()
```

## 从Peewee迁移

### 概念差异

| Peewee | rhosocial ActiveRecord |
|--------|---------------------|
| 轻量级，简单的API | 具有活动记录模式的全功能ORM |
| 以模型为中心的设计 | 以模型为中心的设计 |
| 通过模型Meta进行连接管理 | 通过配置进行连接管理 |
| 基于字段的查询构建 | 方法链接进行查询 |

### 模型转换示例

**Peewee模型：**

```python
from peewee import *

db = SqliteDatabase('my_app.db')

class BaseModel(Model):
    class Meta:
        database = db

class Person(BaseModel):
    name = CharField()
    birthday = DateField()
    is_relative = BooleanField(default=False)
    
    def __str__(self):
        return self.name

class Pet(BaseModel):
    owner = ForeignKeyField(Person, backref='pets')
    name = CharField()
    animal_type = CharField()
    
    def __str__(self):
        return f'{self.name} ({self.animal_type})'
```

**等效的rhosocial ActiveRecord模型：**

```python
from rhosocial.activerecord import ActiveRecord
from typing import Optional
from datetime import date

class Person(ActiveRecord):
    name: str  # 姓名
    birthday: date  # 生日
    is_relative: bool = False  # 是否亲戚，默认为False
    
    def __str__(self):
        return self.name
    
    def pets(self):
        return self.has_many(Pet, foreign_key='owner_id')

class Pet(ActiveRecord):
    owner_id: int  # 外键，关联到person表的id字段
    name: str  # 名称
    animal_type: str  # 动物类型
    
    def __str__(self):
        return f'{self.name} ({self.animal_type})'
    
    def owner(self):
        return self.belongs_to(Person, foreign_key='owner_id')
```

### 查询转换示例

**Peewee查询：**

```python
# 创建人员
person = Person.create(name='John', birthday=date(1990, 1, 1), is_relative=True)

# 创建具有关系的宠物
pet = Pet.create(owner=person, name='Fido', animal_type='dog')

# 获取属于某人的所有宠物
pets = Pet.select().where(Pet.owner == person)

# 连接查询
query = (Pet
         .select(Pet, Person)
         .join(Person)
         .where(Person.name == 'John'))

# 排序
pets_by_name = Pet.select().order_by(Pet.name)

# 限制
first_3_pets = Pet.select().limit(3)

# 更新记录
person.name = 'John Smith'
person.save()

# 删除记录
pet.delete_instance()
```

**等效的rhosocial ActiveRecord查询：**

```python
# 创建人员
person = Person(name='John', birthday=date(1990, 1, 1), is_relative=True)
person.save()

# 创建具有关系的宠物
pet = Pet(owner_id=person.id, name='Fido', animal_type='dog')
pet.save()

# 获取属于某人的所有宠物
pets = Pet.find().where(Pet.owner_id == person.id).all()

# 连接查询
pets = Pet.find()\
    .join(Person, Pet.owner_id == Person.id)\
    .where(Person.name == 'John')\
    .all()

# 排序
pets_by_name = Pet.find().order_by(Pet.name.asc()).all()

# 限制
first_3_pets = Pet.find().limit(3).all()

# 更新记录
person.name = 'John Smith'
person.save()

# 删除记录
pet.delete()
```

## 数据迁移策略

### 1. 使用数据库级迁移

对于模式基本保持不变的简单迁移：

```python
from rhosocial.activerecord.migration import Migration

class MigrateFromDjangoORM(Migration):
    def up(self):
        # 如需要，重命名表
        self.execute("ALTER TABLE django_app_product RENAME TO product")
        
        # 如需要，重命名列
        self.execute("ALTER TABLE product RENAME COLUMN product_name TO name")
        
        # 如需要，更新外键约束
        self.execute("ALTER TABLE product DROP CONSTRAINT django_app_product_category_id_fkey")
        self.execute("ALTER TABLE product ADD CONSTRAINT product_category_id_fkey "
                    "FOREIGN KEY (category_id) REFERENCES category(id)")
```

### 2. 使用ETL过程

对于具有重大模式变更的复杂迁移：

```python
# 从旧ORM提取数据
from old_app.models import OldUser
from new_app.models import User

def migrate_users():
    # 从旧系统获取所有用户
    old_users = OldUser.objects.all()
    
    # 转换并加载到新系统
    for old_user in old_users:
        user = User(
            username=old_user.username,
            email=old_user.email,
            # 根据需要转换数据
            status='active' if old_user.is_active else 'inactive'
        )
        user.save()
        
        print(f"已迁移用户: {user.username}")
```

### 3. 增量迁移的双写策略

对于最小停机时间的渐进式迁移：

```python
# 在服务层，在过渡期间写入两个ORM
class UserService:
    def create_user(self, username, email, **kwargs):
        # 在旧ORM中创建
        old_user = OldUser.objects.create(
            username=username,
            email=email,
            is_active=kwargs.get('is_active', True)
        )
        
        # 在新ORM中创建
        new_user = User(
            username=username,
            email=email,
            status='active' if kwargs.get('is_active', True) else 'inactive'
        )
        new_user.save()
        
        return new_user
```

## 测试迁移

### 1. 功能等效性测试

验证新实现产生与旧实现相同的结果：

```python
import unittest

class MigrationTest(unittest.TestCase):
    def test_user_retrieval(self):
        # 使用旧ORM测试
        old_user = OldUser.objects.get(username='testuser')
        
        # 使用新ORM测试
        new_user = User.find().where(User.username == 'testuser').one()
        
        # 验证结果匹配
        self.assertEqual(old_user.email, new_user.email)
        self.assertEqual(old_user.is_active, new_user.status == 'active')
```

### 2. 性能测试

比较新旧实现之间的性能：

```python
import time

def benchmark_query():
    # 对旧ORM进行基准测试
    start = time.time()
    old_result = OldUser.objects.filter(is_active=True).count()
    old_time = time.time() - start
    
    # 对新ORM进行基准测试
    start = time.time()
    new_result = User.find().where(User.status == 'active').count()
    new_time = time.time() - start
    
    print(f"旧ORM: {old_time:.4f}秒, 新ORM: {new_time:.4f}秒")
    print(f"结果: 旧={old_result}, 新={new_result}")
```

## 常见挑战和解决方案

### 1. 自定义SQL和数据库特定功能

**挑战**：迁移自定义SQL或数据库特定功能。

**解决方案**：使用rhosocial ActiveRecord的原始SQL功能：

```python
# 旧SQLAlchemy原始查询
result = session.execute("SELECT * FROM users WHERE last_login > NOW() - INTERVAL '7 days'")

# 新ActiveRecord原始查询
result = User.find_by_sql("SELECT * FROM users WHERE last_login > NOW() - INTERVAL '7 days'")
```

### 2. 复杂关系

**挑战**：迁移复杂的关系模式。

**解决方案**：分解复杂关系并逐步实现：

```python
# 明确定义关系
class User(ActiveRecord):
    # 基本字段...
    
    def posts(self):
        return self.has_many(Post, foreign_key='user_id')
    
    def comments(self):
        return self.has_many(Comment, foreign_key='user_id')
    
    def commented_posts(self):
        # 实现多对多通过关系
        return self.has_many_through(Post, Comment, 'user_id', 'post_id')
```

### 3. 自定义模型方法

**挑战**：迁移自定义模型方法和行为。

**解决方案**：在新模型中实现等效方法：

```python
# 旧Django模型方法
class Order(models.Model):
    # 字段...
    
    def calculate_total(self):
        return sum(item.price * item.quantity for item in self.items.all())

# 新ActiveRecord模型方法
class Order(ActiveRecord):
    # 字段...
    
    def calculate_total(self):
        items = self.items().all()
        return sum(item.price * item.quantity for item in items)
```

## 结论

从一个ORM迁移到另一个需要仔细规划、系统转换和彻底测试。通过遵循本指南中的模式和示例，您可以成功地将应用程序从SQLAlchemy、Django ORM或Peewee迁移到rhosocial ActiveRecord，同时最小化中断并保持功能。

请记住，迁移是改进数据模型和查询模式的机会。在迁移过程中，利用rhosocial ActiveRecord的功能来增强应用程序的数据库交互。