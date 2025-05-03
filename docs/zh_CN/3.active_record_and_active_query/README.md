# ActiveRecord 与 ActiveQuery

本节涵盖了rhosocial ActiveRecord框架的核心组件：ActiveRecord模型和ActiveQuery功能。

## 概述

ActiveRecord模式是一种将数据库表映射到类、将行映射到对象的架构模式。它封装了数据库访问并为数据添加了领域逻辑。rhosocial ActiveRecord使用现代Python特性实现了这种模式，利用Pydantic进行数据验证和类型安全。

ActiveQuery是查询构建器组件，它提供了一个流畅的接口来构建数据库查询。它允许您以可读和可维护的方式构建复杂查询，在大多数情况下无需编写原始SQL。

## 目录

- [定义模型](3.1.defining_models/README.md) - 学习如何定义数据模型
  - 表结构定义
  - 字段验证规则
  - 生命周期钩子
  - 继承和多态性
  - 组合模式和混入

- [CRUD操作](3.2.crud_operations/README.md)
  - [创建/读取/更新/删除](3.2.crud_operations/create_read_update_delete.md)
  - [批量操作](3.2.crud_operations/batch_operations.md)
  - [事务基础](3.2.crud_operations/transaction_basics.md)

- [预定义字段和功能](3.3.predefined_fields_and_features/README.md)
  - [主键配置](3.3.predefined_fields_and_features/primary_key_configuration.md)
  - [时间戳字段（创建/更新）](3.3.predefined_fields_and_features/timestamp_fields.md)
  - [软删除机制](3.3.predefined_fields_and_features/soft_delete_mechanism.md)
  - [版本控制和乐观锁](3.3.predefined_fields_and_features/version_control_and_optimistic_locking.md)
  - [悲观锁策略](3.3.predefined_fields_and_features/pessimistic_locking_strategies.md)
  - [自定义字段](3.3.predefined_fields_and_features/custom_fields.md)

- [关系](3.4.relationships/README.md)
  - [一对一关系](3.4.relationships/one_to_one_relationships.md)
  - [一对多关系](3.4.relationships/one_to_many_relationships.md)
  - [多对多关系](3.4.relationships/many_to_many_relationships.md)
  - [多态关系](3.4.relationships/polymorphic_relationships.md)
  - [自引用关系](3.4.relationships/self_referential_relationships.md)
  - [关系加载策略](3.4.relationships/relationship_loading_strategies.md)
  - [预加载与懒加载](3.4.relationships/eager_and_lazy_loading.md)
  - [跨数据库关系](3.4.relationships/cross_database_relationships.md)

- [事务与隔离级别](3.5.transactions_and_isolation_levels/README.md)
  - [事务管理](3.5.transactions_and_isolation_levels/transaction_management.md)
  - [隔离级别配置](3.5.transactions_and_isolation_levels/isolation_level_configuration.md)
  - [嵌套事务](3.5.transactions_and_isolation_levels/nested_transactions.md)
  - [保存点](3.5.transactions_and_isolation_levels/savepoints.md)
  - [事务中的错误处理](3.5.transactions_and_isolation_levels/error_handling_in_transactions.md)

- [聚合查询](3.6.aggregate_queries/README.md)
  - [计数、求和、平均值、最小值、最大值](3.6.aggregate_queries/basic_aggregate_functions.md)
  - [分组操作](3.6.aggregate_queries/group_by_operations.md)
  - [Having子句](3.6.aggregate_queries/having_clauses.md)
  - [复杂聚合](3.6.aggregate_queries/complex_aggregations.md)
  - [窗口函数](3.6.aggregate_queries/window_functions.md)
  - [统计查询](3.6.aggregate_queries/statistical_queries.md)
  - [JSON操作](3.6.aggregate_queries/json_operations.md)
  - [自定义表达式](3.6.aggregate_queries/custom_expressions.md)

- [高级查询功能](3.7.advanced_query_features/README.md)
  - [自定义ActiveQuery类](3.7.advanced_query_features/custom_activequery_classes.md)
  - [查询作用域](3.7.advanced_query_features/query_scopes.md)
  - [动态查询构建](3.7.advanced_query_features/dynamic_query_building.md)
  - [原始SQL集成](3.7.advanced_query_features/raw_sql_integration.md)
  - [公共表表达式](3.7.advanced_query_features/common_table_expressions.md)
  - [异步访问](3.7.advanced_query_features/async_access.md)

## 关键概念

- **模型即类**：每个数据库表由继承自ActiveRecord的模型类表示
- **记录即对象**：数据库中的每一行由模型类的实例表示
- **验证**：使用Pydantic的验证系统进行数据验证
- **查询构建**：通过ActiveQuery对象上的方法链构建查询
- **关系**：模型可以定义与其他模型的关系
- **事件**：模型支持生命周期事件以实现自定义行为

本节将指导您了解ActiveRecord模型和查询的所有方面，从基本的CRUD操作到高级功能，如自定义查询作用域和关系管理。