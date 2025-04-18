# 定义模型

本节介绍如何在应用程序中定义ActiveRecord模型。模型是应用程序数据层的基础，代表数据库表并提供数据操作方法。

## 概述

在rhosocial ActiveRecord中，模型被定义为继承自`ActiveRecord`基类的类。每个模型对应一个数据库表，模型的每个实例对应表中的一行。模型利用Pydantic进行数据验证和类型安全。

## 目录

- [表结构定义](table_schema_definition.md) - 如何定义表结构
- [模型关系定义](model_relationships.md) - 如何定义和使用模型关系
- [字段验证规则](field_validation_rules.md) - 为模型字段添加验证
- [生命周期钩子](lifecycle_hooks.md) - 使用事件自定义模型行为
- [继承和多态性](inheritance_and_polymorphism.md) - 创建模型层次结构
- [组合模式和混入](composition_patterns_and_mixins.md) - 跨模型重用功能

## 基本模型定义

以下是一个简单的模型定义示例：

```python
from rhosocial.activerecord import ActiveRecord
from datetime import datetime
from typing import Optional

class User(ActiveRecord):
    __table_name__ = 'users'  # 可选：默认为类名的蛇形命名法
    
    id: int  # 主键（默认字段名为'id'）
    username: str
    email: str
    created_at: datetime
    updated_at: datetime
    is_active: bool = True  # 带默认值的字段
    bio: Optional[str] = None  # 可选字段
```

## 关键组件

### 表名

默认情况下，表名从类名的蛇形命名法派生（例如，`UserProfile`变为`user_profile`）。您可以通过设置`__table_name__`类属性来覆盖此行为。

### 主键

默认情况下，主键字段名为`id`。您可以通过设置`__primary_key__`类属性来自定义：

```python
class CustomModel(ActiveRecord):
    __primary_key__ = 'custom_id'
    
    custom_id: int
    # 其他字段...
```

### 字段类型

rhosocial ActiveRecord利用Pydantic的类型系统，支持所有标准Python类型和Pydantic的专用类型。常见字段类型包括：

- 基本类型：`int`、`float`、`str`、`bool`
- 日期/时间类型：`datetime`、`date`、`time`
- 复杂类型：`dict`、`list`
- 可选字段：`Optional[Type]`
- 自定义类型：任何与Pydantic兼容的类型

### 字段约束

您可以使用Pydantic的字段函数为字段添加约束：

```python
from pydantic import Field

class Product(ActiveRecord):
    id: int
    name: str = Field(..., min_length=3, max_length=100)
    price: float = Field(..., gt=0)
    description: Optional[str] = Field(None, max_length=1000)
```

## 下一步

探索每个模型定义方面的详细文档，了解如何为应用程序创建健壮、类型安全的模型。