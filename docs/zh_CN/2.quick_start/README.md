# 快速入门（SQLite示例）

本指南将帮助您使用SQLite作为数据库后端，快速上手rhosocial ActiveRecord。SQLite已包含在Python中，这使其成为快速原型设计和学习框架的理想选择。

## 目录

- [安装指南](installation.md) - 如何安装rhosocial ActiveRecord
- [基本配置](basic_configuration.md) - 设置您的第一个连接
- [第一个模型示例](first_model_example.md) - 创建和使用您的第一个模型
- [常见问题解答](faq.md) - 常见问题和故障排除

## 概述

rhosocial ActiveRecord是一个现代化的ORM（对象关系映射）框架，它遵循ActiveRecord模式，为数据库操作提供直观的接口。它将ActiveRecord模式的简洁性与Pydantic的类型安全性相结合。

该框架允许您：

- 定义映射到数据库表的模型
- 使用最少的代码执行CRUD操作
- 使用流畅的接口构建复杂查询
- 管理模型之间的关系
- 处理具有适当隔离级别的事务

本快速入门指南将使用SQLite引导您了解基础知识，SQLite已包含在Python中，无需额外设置。一旦您熟悉了基础知识，您可以探索更高级的功能或切换到其他数据库后端。