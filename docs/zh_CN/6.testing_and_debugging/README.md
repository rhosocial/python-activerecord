# 测试和调试

有效的测试和调试对于开发可靠的ActiveRecord应用程序至关重要。本章涵盖了测试模型、关系和事务的综合策略和工具，以及调试和性能分析技术。

## 目录

- [单元测试指南](unit_testing_guide/README.md)
  - [模型测试](unit_testing_guide/model_testing.md) - 学习如何测试ActiveRecord模型
  - [关系测试](unit_testing_guide/relationship_testing.md) - 测试模型关系的策略
  - [事务测试](unit_testing_guide/transaction_testing.md) - 测试数据库事务的方法

- [调试技术](debugging_techniques.md) - ActiveRecord应用程序的常见调试策略
  - 使用日志进行调试
  - 检查查询执行
  - 排查常见问题

- [日志记录和分析](logging_and_analysis.md) - 有效配置和使用日志
  - 设置日志记录
  - 日志分析技术
  - 通过日志识别性能瓶颈

- [性能分析工具](performance_profiling_tools.md) - 分析ActiveRecord性能的工具和技术
  - 查询分析
  - 内存使用分析
  - 与Python分析器集成