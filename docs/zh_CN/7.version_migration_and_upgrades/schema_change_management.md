# 模式变更管理

## 介绍

数据库模式变更是应用程序开发中不可避免的一部分。随着应用程序的发展，您需要添加新表、修改现有列或重构关系。rhosocial ActiveRecord提供了一种通过迁移脚本系统地管理这些变更的方法。

## 迁移基础

### 什么是迁移？

迁移是对数据库模式的版本化变更，可以根据需要应用或撤销。rhosocial ActiveRecord中的迁移是定义数据库结构转换的Python脚本。

### 迁移文件结构

一个典型的迁移文件包括：

```python
from rhosocial.activerecord.migration import Migration

class AddUserTable(Migration):
    """添加用户表的迁移。"""
    
    def up(self):
        """应用迁移。"""
        self.create_table('user', [
            self.column('id', 'integer', primary_key=True, auto_increment=True),
            self.column('username', 'string', length=64, null=False, unique=True),
            self.column('email', 'string', length=255, null=False),
            self.column('created_at', 'datetime'),
            self.column('updated_at', 'datetime')
        ])
        
        self.create_index('user', 'email')
    
    def down(self):
        """撤销迁移。"""
        self.drop_table('user')
```

## 管理迁移

### 创建新迁移

要创建新迁移，请使用迁移生成器命令：

```bash
python -m rhosocial.activerecord.migration create add_user_table
```

这将在您的迁移目录中创建一个带时间戳的迁移文件。

### 应用迁移

应用待处理的迁移：

```bash
python -m rhosocial.activerecord.migration up
```

应用特定数量的迁移：

```bash
python -m rhosocial.activerecord.migration up 3
```

### 撤销迁移

撤销最近的迁移：

```bash
python -m rhosocial.activerecord.migration down
```

撤销特定数量的迁移：

```bash
python -m rhosocial.activerecord.migration down 3
```

### 检查迁移状态

查看哪些迁移已应用，哪些待处理：

```bash
python -m rhosocial.activerecord.migration status
```

## 模式变更的最佳实践

### 1. 使迁移可逆

尽可能确保您的迁移可以通过实现`up()`和`down()`方法来撤销。

### 2. 保持迁移小而集中

每个迁移应处理对模式的单一逻辑变更。这使迁移更容易理解、测试和排除故障。

### 3. 使用数据库无关的操作

尽可能使用迁移API的数据库无关方法，而不是原始SQL。这确保您的迁移可以在不同的数据库后端工作。

### 4. 部署前测试迁移

在应用到生产环境之前，始终在开发或测试环境中测试迁移。

### 5. 版本控制您的迁移

迁移应与应用程序代码一起提交到版本控制系统。

## 常见模式变更操作

### 创建表

```python
def up(self):
    self.create_table('product', [
        self.column('id', 'integer', primary_key=True, auto_increment=True),
        self.column('name', 'string', length=128, null=False),
        self.column('price', 'decimal', precision=10, scale=2, null=False),
        self.column('description', 'text'),
        self.column('category_id', 'integer'),
        self.column('created_at', 'datetime'),
        self.column('updated_at', 'datetime')
    ])
```

### 添加列

```python
def up(self):
    self.add_column('user', 'last_login_at', 'datetime', null=True)
```

### 修改列

```python
def up(self):
    self.change_column('product', 'price', 'decimal', precision=12, scale=4)
```

### 创建索引

```python
def up(self):
    self.create_index('product', 'category_id')
    self.create_index('product', ['name', 'category_id'], unique=True)
```

### 添加外键

```python
def up(self):
    self.add_foreign_key('product', 'category_id', 'category', 'id', on_delete='CASCADE')
```

## 处理复杂模式变更

对于涉及数据转换的复杂模式变更，您可能需要将模式变更与数据迁移步骤结合起来：

```python
def up(self):
    # 1. 添加新列
    self.add_column('user', 'full_name', 'string', length=255, null=True)
    
    # 2. 迁移数据（使用原始SQL进行复杂转换）
    self.execute("UPDATE user SET full_name = CONCAT(first_name, ' ', last_name)")
    
    # 3. 数据迁移后使列不可为空
    self.change_column('user', 'full_name', 'string', length=255, null=False)
    
    # 4. 移除旧列
    self.remove_column('user', 'first_name')
    self.remove_column('user', 'last_name')
```

## 数据库特定考虑因素

虽然rhosocial ActiveRecord旨在提供数据库无关的迁移，但某些操作可能具有特定于数据库的行为。有关某些操作如何实现的详细信息，请参阅特定数据库后端的文档。

## 结论

有效的模式变更管理对于在允许应用程序发展的同时维护数据库完整性至关重要。通过遵循本指南中概述的模式和实践，您可以以受控、可逆的方式实施数据库变更，最大限度地降低风险和停机时间。