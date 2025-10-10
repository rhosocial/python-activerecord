# 测试和调试

rhosocial ActiveRecord 中的测试和调试当前专注于基本功能。实际实现提供了开发和调试的基本工具，更高级的功能计划在未来的版本中发布。

## 当前测试功能

- 基本CRUD操作测试
- 简单模型验证测试
- 直接数据库交互验证
- 查询执行调试

## 目录

- [基本测试指南](unit_testing_guide/README.md)
  - [模型测试](unit_testing_guide/model_testing.md) - 测试基本模型功能
  - [查询测试](unit_testing_guide/relationship_testing.md) - 查询执行的测试方法
  - [数据库测试](unit_testing_guide/transaction_testing.md) - 测试数据库操作

- [调试技术](debugging_techniques.md) - 当前ActiveRecord应用程序的调试方法
  - 使用日志进行调试
  - 检查查询执行
  - 排查常见问题

- [日志记录和分析](logging_and_analysis.md) - 有效配置和使用日志
  - 设置日志记录
  - 日志分析技术

## 局限性

当前的测试框架是基础的，缺少对关系、事务和高级功能的全面测试工具。这些将在未来版本中添加。