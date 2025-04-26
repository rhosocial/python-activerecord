# 自定义后端

本节介绍如何在rhosocial ActiveRecord中实现自定义数据库后端和扩展现有后端。

## 概述

rhosocial ActiveRecord设计时考虑了可扩展性，允许开发者创建超出内置后端（SQLite、MySQL/MariaDB、PostgreSQL等）范围的自定义数据库后端。这一功能在以下情况下特别有用：

- 需要支持标准发行版中未包含的数据库系统
- 想要为现有后端添加专门功能
- 正在集成应与ActiveRecord模型一起工作的自定义数据存储解决方案

以下页面提供了关于实现和扩展数据库后端的详细指导：

- [实现自定义数据库后端](implementing_custom_backends.md)：从头创建新数据库后端的分步指南
- [扩展现有后端](extending_existing_backends.md)：如何扩展或修改现有数据库后端的行为

## 架构

rhosocial ActiveRecord中的后端系统遵循模块化架构，具有明确的关注点分离：

1. **抽象基类**：`StorageBackend`抽象基类定义了所有后端必须实现的接口
2. **方言系统**：SQL方言差异通过方言系统处理
3. **实现目录**：每个后端实现都存储在`rhosocial.activerecord.backend.impl`下的自己的子目录中

```
backend/
  base.py                # 抽象基类和接口
  dialect.py             # SQL方言系统
  impl/                  # 实现目录
    sqlite/              # SQLite实现
      __init__.py
      backend.py         # SQLiteBackend类
      dialect.py         # SQLite方言实现
    mysql/               # MySQL实现
      ...
    pgsql/               # PostgreSQL实现
      ...
    your_custom_backend/ # 您的自定义实现
      ...
```

这种架构使添加新后端变得简单明了，同时确保它们与框架的其余部分正确集成。

## 实现位置

在实现自定义后端或扩展现有后端时，您可以灵活选择代码放置位置：

1. **在ActiveRecord包内**：如果您正在修改核心包，可以直接将实现放在`rhosocial.activerecord.backend.impl`目录中。
2. **在单独的包中**：您可以在核心ActiveRecord包外创建自己的包结构，如果您计划单独分发后端，这是推荐的方法。

这两种方法都是有效的，单独的包提供了更好的隔离和更容易的分发。

## 测试您的后端

彻底测试您的后端实现对确保可靠性至关重要。您应该：

1. **参考现有测试**：研究并参考现有后端的测试结构（例如，在`tests/rhosocial/activerecord/backend`目录中）
2. **确保分支覆盖**：编写覆盖所有代码分支和边缘情况的测试
3. **模拟真实场景**：创建模拟您的后端将遇到的各种使用场景的测试
4. **测试集成**：验证您的后端与ActiveRecord框架的其余部分正确协作