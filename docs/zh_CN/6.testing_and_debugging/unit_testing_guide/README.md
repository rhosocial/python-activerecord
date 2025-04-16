# 单元测试指南

单元测试是开发可靠的ActiveRecord应用程序的关键部分。本指南涵盖了测试ActiveRecord模型、关系和事务的最佳实践和策略。

## 概述

有效的ActiveRecord应用程序单元测试包括：

- 测试模型验证和业务逻辑
- 验证关系行为
- 确保事务完整性
- 在适当时模拟数据库连接

## 测试框架

Python ActiveRecord设计为与标准Python测试框架无缝协作，如：

- `unittest` - Python的内置测试框架
- `pytest` - 一个功能更丰富的测试框架，具有出色的fixture支持

## 测试数据库配置

测试ActiveRecord模型时，建议：

1. 使用单独的测试数据库配置
2. 在测试之间重置数据库状态
3. 使用事务隔离测试用例
4. 在适当时考虑使用内存SQLite以加快测试速度

## 目录

- [模型测试](model_testing.md) - 测试ActiveRecord模型的策略
- [关系测试](relationship_testing.md) - 测试模型关系的技术
- [事务测试](transaction_testing.md) - 测试数据库事务的方法

## 最佳实践

- 保持测试隔离和独立
- 使用fixtures或工厂创建测试数据
- 测试有效和无效的场景
- 在必要时模拟外部依赖
- 使用数据库事务加速测试并确保隔离