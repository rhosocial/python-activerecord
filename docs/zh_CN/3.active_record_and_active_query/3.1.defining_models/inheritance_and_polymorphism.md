# 继承和多态性

本文档解释了如何在ActiveRecord模型中使用继承和多态性。这些面向对象的概念允许您创建模型层次结构、共享行为和实现基础模型的专用版本。

## 概述

rhosocial ActiveRecord支持模型继承，允许您创建相关模型的层次结构。这使您能够：

- 在相关模型之间共享通用字段和行为
- 实现基础模型的专用版本
- 创建模型之间的多态关系
- 以逻辑的、面向对象的结构组织您的模型

## 单表继承

单表继承（STI）是一种多个模型类共享单个数据库表的模式。该表包括任何子类所需的所有字段，并且一个类型列指示一行代表哪个特定模型。

### 基本实现

```python
from rhosocial.activerecord import ActiveRecord
from typing import Optional

class Vehicle(ActiveRecord):
    __table_name__ = 'vehicles'
    __type_field__ = 'vehicle_type'  # 存储模型类型的列
    
    id: int
    make: str
    model: str
    year: int
    color: str
    vehicle_type: str  # 存储类名或类型标识符
    
    def __init__(self, **data):
        if self.__class__ == Vehicle:
            data['vehicle_type'] = 'Vehicle'
        super().__init__(**data)

class Car(Vehicle):
    doors: int
    trunk_capacity: Optional[float] = None
    
    def __init__(self, **data):
        data['vehicle_type'] = 'Car'
        super().__init__(**data)

class Motorcycle(Vehicle):
    engine_displacement: Optional[int] = None
    has_sidecar: bool = False
    
    def __init__(self, **data):
        data['vehicle_type'] = 'Motorcycle'
        super().__init__(**data)
```

### 使用STI进行查询

使用单表继承进行查询时，您可以：

1. 查询基类以获取所有类型：

```python
# 获取所有车辆，不论类型
vehicles = Vehicle.query().all()
```

2. 查询特定子类以仅获取该类型：

```python
# 仅获取汽车
cars = Car.query().all()

# 仅获取摩托车
motorcycles = Motorcycle.query().all()
```

ActiveRecord框架在从子类查询时自动添加适当的类型条件。

## 类表继承

类表继承（CTI）为继承层次结构中的每个类使用单独的表，它们之间有外键关系。这种方法更规范化，但需要连接才能完整检索对象。

### 基本实现

```python
from rhosocial.activerecord import ActiveRecord
from typing import Optional

class Person(ActiveRecord):
    __table_name__ = 'people'
    
    id: int
    name: str
    email: str
    birth_date: Optional[date] = None

class Employee(Person):
    __table_name__ = 'employees'
    __primary_key__ = 'person_id'  # 指向people表的外键
    
    person_id: int  # 引用Person.id
    hire_date: date
    department: str
    salary: float
    
    def __init__(self, **data):
        # 单独处理person数据
        person_data = {}
        for field in Person.model_fields():
            if field in data:
                person_data[field] = data.pop(field)
        
        # 创建或更新person记录
        if 'id' in person_data:
            person = Person.find_one(person_data['id'])
            for key, value in person_data.items():
                setattr(person, key, value)
            person.save()
        else:
            person = Person(**person_data)
            person.save()
        
        # 为employee设置person_id
        data['person_id'] = person.id
        
        super().__init__(**data)
```

### 使用CTI进行查询

使用类表继承进行查询需要显式连接：

```python
# 获取带有person数据的employees
employees = Employee.query()\
    .inner_join('people', 'person_id', 'people.id')\
    .select('employees.*', 'people.name', 'people.email')\
    .all()
```

## 多态关联

多态关联允许模型通过单个关联属于多种类型的模型。这是通过外键和类型标识符的组合实现的。

### 基本实现

```python
from rhosocial.activerecord import ActiveRecord
from datetime import datetime

class Comment(ActiveRecord):
    __table_name__ = 'comments'
    
    id: int
    content: str
    commentable_id: int      # 关联对象的外键
    commentable_type: str    # 关联对象的类型（例如，'Post'，'Photo'）
    created_at: datetime
    
    def commentable(self):
        """获取关联对象（帖子、照片等）"""
        if self.commentable_type == 'Post':
            from .post import Post
            return Post.find_one(self.commentable_id)
        elif self.commentable_type == 'Photo':
            from .photo import Photo
            return Photo.find_one(self.commentable_id)
        return None

class Post(ActiveRecord):
    __table_name__ = 'posts'
    
    id: int
    title: str
    content: str
    
    def comments(self):
        """获取与此帖子关联的评论"""
        return Comment.query()\
            .where(commentable_id=self.id, commentable_type='Post')\
            .all()
    
    def add_comment(self, content: str):
        """向此帖子添加评论"""
        comment = Comment(
            content=content,
            commentable_id=self.id,
            commentable_type='Post',
            created_at=datetime.now()
        )
        comment.save()
        return comment

class Photo(ActiveRecord):
    __table_name__ = 'photos'
    
    id: int
    title: str
    url: str
    
    def comments(self):
        """获取与此照片关联的评论"""
        return Comment.query()\
            .where(commentable_id=self.id, commentable_type='Photo')\
            .all()
    
    def add_comment(self, content: str):
        """向此照片添加评论"""
        comment = Comment(
            content=content,
            commentable_id=self.id,
            commentable_type='Photo',
            created_at=datetime.now()
        )
        comment.save()
        return comment
```

### 使用多态关联

```python
# 创建帖子并添加评论
post = Post(title="我的第一篇帖子", content="你好，世界！")
post.save()
post.add_comment("好帖子！")

# 创建照片并添加评论
photo = Photo(title="日落", url="/images/sunset.jpg")
photo.save()
photo.add_comment("美丽的色彩！")

# 获取帖子的所有评论
post_comments = post.comments()

# 从评论获取可评论对象
comment = Comment.find_one(1)
commentable = comment.commentable()  # 返回Post或Photo实例
```

## 抽象基类

抽象基类提供通用功能，而无需直接实例化。它们对于在模型之间共享代码而不为基类创建数据库表很有用。

### 基本实现

```python
from abc import ABC
from rhosocial.activerecord import ActiveRecord

class Auditable(ActiveRecord, ABC):
    """可审计模型的抽象基类。"""
    __abstract__ = True  # 将其标记为抽象类（无表）
    
    created_at: datetime
    updated_at: datetime
    created_by: Optional[int] = None
    updated_by: Optional[int] = None
    
    def __init__(self, **data):
        super().__init__(**data)
        self.on(ModelEvent.BEFORE_CREATE, self._set_audit_timestamps)
        self.on(ModelEvent.BEFORE_UPDATE, self._update_audit_timestamps)
    
    def _set_audit_timestamps(self, event):
        now = datetime.now()
        self.created_at = now
        self.updated_at = now
        # 如果可用，可以从当前用户设置created_by/updated_by
    
    def _update_audit_timestamps(self, event):
        self.updated_at = datetime.now()
        # 如果可用，可以从当前用户设置updated_by

class User(Auditable):
    __table_name__ = 'users'
    
    id: int
    username: str
    email: str
    # 继承created_at、updated_at、created_by、updated_by

class Product(Auditable):
    __table_name__ = 'products'
    
    id: int
    name: str
    price: float
    # 继承created_at、updated_at、created_by、updated_by
```

## 方法重写

您可以重写父类的方法以在子类中自定义行为：

```python
class Animal(ActiveRecord):
    id: int
    name: str
    species: str
    
    def make_sound(self):
        return "一些通用动物声音"

class Dog(Animal):
    breed: str
    
    def __init__(self, **data):
        data['species'] = '犬科'
        super().__init__(**data)
    
    def make_sound(self):
        # 重写父方法
        return "汪汪！"

class Cat(Animal):
    fur_color: str
    
    def __init__(self, **data):
        data['species'] = '猫科'
        super().__init__(**data)
    
    def make_sound(self):
        # 重写父方法
        return "喵喵！"
```

## 最佳实践

1. **选择正确的继承类型**：为差异较少的密切相关模型选择单表继承，为差异显著的模型选择类表继承。

2. **使用抽象基类**：对于不需要数据库表的共享行为，使用抽象基类。

3. **小心深层次结构**：深层继承层次结构可能变得复杂且难以维护。尽可能保持浅层。

4. **记录类型字段**：在单表继承和多态关联中清楚地记录类型字段的含义。

5. **考虑组合**：有时组合（使用混入或has-a关系）比继承更合适。

6. **彻底测试继承**：编写验证基类和子类行为的测试。

## 结论

继承和多态性是强大的面向对象概念，可以帮助您组织和构建ActiveRecord模型。通过适当地使用这些技术，您可以创建更易于维护、符合DRY（不要重复自己）原则的代码，同时准确地模拟领域中的关系。