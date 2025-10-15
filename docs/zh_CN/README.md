# rhosocial ActiveRecord 文档大纲（中文版）

> **⚠️ 开发阶段声明：** 当前项目尚处于开发阶段，特性随时可能增减，且可能存在缺陷，甚至与实际实现不对应。因此文档内容存在随时调整的可能性，目前仅供参考。
>
> **📝 文档标注说明：** 在文档中，您可能会看到如"目前暂未实现"、"部分实现"、"存在调整可能"等标签。这些标签表示相关功能尚未完全实现或可能与实际实现不符，请以实际代码为准。

> **🔄 实现状态：** 截至最新审查，核心ActiveRecord功能稳定，基本CRUD操作、关系管理和查询构建已实现。异步操作、跨数据库查询和批量操作等功能处于不同开发阶段。有关特定功能的实现状态，请参见各个文档部分。

## [1. 介绍](1.introduction/README.md)
- [概述](1.introduction/introduction.md)
- [特点](1.introduction/features.md)
- [系统需求](1.introduction/README.md#requirements)
- [设计理念](1.introduction/philosophy.md)
- [Pydantic集成](1.introduction/pydantic-integration.md)
- [异步支持](1.introduction/async-support.md)
- [关系管理](1.introduction/relationships.md)
- [聚合功能](1.introduction/aggregation.md)
- [性能表现](1.introduction/performance.md)
- [学习曲线](1.introduction/learning-curve.md)
- [社区生态](1.introduction/community.md)
- [何时选择](1.introduction/when-to-choose.md)
- [代码对比](1.introduction/code-comparison.md)
- [总结](1.introduction/conclusion.md)

## [2. 快速入门（SQLite示例）](2.quick_start/README.md)
- [安装指南](2.quick_start/installation.md)
- [基本配置](2.quick_start/basic_configuration.md)
- [第一个模型示例](2.quick_start/first_model_example.md)
- [常见问题解答](2.quick_start/faq.md)

## [3. ActiveRecord 与 ActiveQuery](3.active_record_and_active_query/README.md)
### [3.1 定义模型](3.active_record_and_active_query/3.1.defining_models/README.md)
- [表结构定义](3.active_record_and_active_query/3.1.defining_models/table_schema_definition.md)
- [字段验证规则](3.active_record_and_active_query/3.1.defining_models/field_validation_rules.md)
- [生命周期钩子](3.active_record_and_active_query/3.1.defining_models/lifecycle_hooks.md)
- [继承与多态](3.active_record_and_active_query/3.1.defining_models/inheritance_and_polymorphism.md)
- [组合模式与混入](3.active_record_and_active_query/3.1.defining_models/composition_patterns_and_mixins.md)

### [3.2 CRUD操作](3.active_record_and_active_query/3.2.crud_operations/README.md)
- [创建/读取/更新/删除](3.active_record_and_active_query/3.2.crud_operations/create_read_update_delete.md)
- [批量操作](3.active_record_and_active_query/3.2.crud_operations/batch_operations.md)
- [事务处理基础](3.active_record_and_active_query/3.2.crud_operations/transaction_basics.md)

### [3.3 预定义字段与特性](3.active_record_and_active_query/3.3.predefined_fields_and_features/README.md)
- [主键配置](3.active_record_and_active_query/3.3.predefined_fields_and_features/primary_key_configuration.md)
- [时间戳字段（创建/更新）](3.active_record_and_active_query/3.3.predefined_fields_and_features/timestamp_fields.md)
- [软删除机制](3.active_record_and_active_query/3.3.predefined_fields_and_features/soft_delete_mechanism.md)
- [版本控制与乐观锁](3.active_record_and_active_query/3.3.predefined_fields_and_features/version_control_and_optimistic_locking.md)
- [悲观锁策略](3.active_record_and_active_query/3.3.predefined_fields_and_features/pessimistic_locking_strategies.md)
- [自定义字段](3.active_record_and_active_query/3.3.predefined_fields_and_features/custom_fields.md)

### [3.4 关系管理](3.active_record_and_active_query/3.4.relationships/README.md)
- [一对一关系](3.active_record_and_active_query/3.4.relationships/one_to_one_relationships.md)
- [一对多关系](3.active_record_and_active_query/3.4.relationships/one_to_many_relationships.md)
- [多对多关系](3.active_record_and_active_query/3.4.relationships/many_to_many_relationships.md)
- [多态关系](3.active_record_and_active_query/3.4.relationships/polymorphic_relationships.md)
- [自引用关系](3.active_record_and_active_query/3.4.relationships/self_referential_relationships.md)
- [关系加载策略](3.active_record_and_active_query/3.4.relationships/relationship_loading_strategies.md)
- [预加载与懒加载](3.active_record_and_active_query/3.4.relationships/eager_and_lazy_loading.md)
- [跨数据库关系](3.active_record_and_active_query/3.4.relationships/cross_database_relationships.md)

### [3.5 事务与隔离级别](3.active_record_and_active_query/3.5.transactions_and_isolation_levels/README.md)
- [事务管理](3.active_record_and_active_query/3.5.transactions_and_isolation_levels/transaction_management.md)
- [隔离级别配置](3.active_record_and_active_query/3.5.transactions_and_isolation_levels/isolation_level_configuration.md)
- [嵌套事务](3.active_record_and_active_query/3.5.transactions_and_isolation_levels/nested_transactions.md)
- [保存点](3.active_record_and_active_query/3.5.transactions_and_isolation_levels/savepoints.md)
- [事务中的错误处理](3.active_record_and_active_query/3.5.transactions_and_isolation_levels/error_handling_in_transactions.md)

### [3.6 聚合查询](3.active_record_and_active_query/3.6.aggregate_queries/README.md)
- [计数、求和、平均值、最小值、最大值](3.active_record_and_active_query/3.6.aggregate_queries/basic_aggregate_functions.md)
- [分组操作](3.active_record_and_active_query/3.6.aggregate_queries/group_by_operations.md)
- [Having子句](3.active_record_and_active_query/3.6.aggregate_queries/having_clauses.md)
- [复杂聚合](3.active_record_and_active_query/3.6.aggregate_queries/complex_aggregations.md)
- [窗口函数](3.active_record_and_active_query/3.6.aggregate_queries/window_functions.md)
- [统计查询](3.active_record_and_active_query/3.6.aggregate_queries/statistical_queries.md)
- [JSON操作](3.active_record_and_active_query/3.6.aggregate_queries/json_operations.md)
  - JSON提取（EXTRACT）
  - JSON文本提取（EXTRACT_TEXT）
  - JSON包含检查（CONTAINS）
  - JSON路径存在检查（EXISTS）
  - JSON类型获取（TYPE）
  - JSON元素操作（REMOVE/INSERT/REPLACE/SET）
- [自定义表达式](3.active_record_and_active_query/3.6.aggregate_queries/custom_expressions.md)
  - 算术表达式
  - 函数表达式
  - CASE表达式
  - 条件表达式（COALESCE, NULLIF等）
  - 子查询表达式
  - 分组集合表达式（CUBE, ROLLUP, GROUPING SETS）

### [3.7 高级查询特性](3.active_record_and_active_query/3.7.advanced_query_features/README.md)
- [自定义ActiveQuery类](3.active_record_and_active_query/3.7.advanced_query_features/custom_activequery_classes.md)
- [查询作用域](3.active_record_and_active_query/3.7.advanced_query_features/query_scopes.md)
- [动态查询构建](3.active_record_and_active_query/3.7.advanced_query_features/dynamic_query_building.md)
- [原生SQL集成](3.active_record_and_active_query/3.7.advanced_query_features/raw_sql_integration.md)
- [异步访问](3.active_record_and_active_query/3.7.advanced_query_features/async_access.md)

## [4. 性能优化](4.performance_optimization/README.md)
- [查询优化技巧](4.performance_optimization/query_optimization_techniques.md)
- [缓存策略](4.performance_optimization/caching_strategies.md)
  - [模型级缓存](4.performance_optimization/caching_strategies/model_level_caching.md)
  - [查询结果缓存](4.performance_optimization/caching_strategies/query_result_caching.md)
  - [关系缓存](4.performance_optimization/caching_strategies/relationship_caching.md)
- [大数据集处理](4.performance_optimization/large_dataset_handling.md)
- [批量操作最佳实践](4.performance_optimization/batch_operation_best_practices.md)
- [性能分析与监控](4.performance_optimization/performance_analysis_and_monitoring.md)

## [5. 后端配置](5.backend_configuration/README.md)
### 5.1 支持的数据库
> **注意：** SQLite是唯一内置的后端，其他数据库后端需要额外的依赖项。

- [MySQL](5.backend_configuration/5.1.supported_databases/mysql.md)
- [MariaDB](5.backend_configuration/5.1.supported_databases/mariadb.md)
- [PostgreSQL](5.backend_configuration/5.1.supported_databases/postgresql.md)
- [Oracle](5.backend_configuration/5.1.supported_databases/oracle.md)
- [SQL Server](5.backend_configuration/5.1.supported_databases/sql_server.md)
- [SQLite](5.backend_configuration/5.1.supported_databases/sqlite.md)

### 5.2 跨数据库查询
- [跨数据库连接配置](5.backend_configuration/5.2.cross_database_queries/connection_configuration.md)
- [异构数据源集成](5.backend_configuration/5.2.cross_database_queries/heterogeneous_data_source_integration.md)
- [数据同步策略](5.backend_configuration/5.2.cross_database_queries/data_synchronization_strategies.md)
- [跨数据库事务处理](5.backend_configuration/5.2.cross_database_queries/cross_database_transaction_handling.md)

### 5.3 数据库特定差异
- [数据类型映射](5.backend_configuration/5.3.database_specific_differences/data_type_mapping.md)
- [SQL方言差异](5.backend_configuration/5.3.database_specific_differences/sql_dialect_differences.md)
- [性能考量](5.backend_configuration/5.3.database_specific_differences/performance_considerations.md)

### 5.4 自定义后端
- [实现自定义数据库后端](5.backend_configuration/5.4.custom_backends/implementing_custom_backends.md)
- [扩展现有后端](5.backend_configuration/5.4.custom_backends/extending_existing_backends.md)

## [6. 测试与调试](6.testing_and_debugging/README.md)
- [单元测试编写指南](6.testing_and_debugging/unit_testing_guide/README.md)
  - [模型测试](6.testing_and_debugging/unit_testing_guide/model_testing.md)
  - [关系测试](6.testing_and_debugging/unit_testing_guide/relationship_testing.md)
  - [事务测试](6.testing_and_debugging/unit_testing_guide/transaction_testing.md)
- [调试技巧](6.testing_and_debugging/debugging_techniques.md)
- [日志记录和分析](6.testing_and_debugging/logging_and_analysis.md)
- [性能分析工具](6.testing_and_debugging/performance_profiling_tools.md)

## [7. 版本迁移与升级](7.version_migration_and_upgrades/README.md)
- [模式变更管理](7.version_migration_and_upgrades/schema_change_management.md)
- [数据迁移策略](7.version_migration_and_upgrades/data_migration_strategies.md)
- [从其他ORM迁移至ActiveRecord](7.version_migration_and_upgrades/migrating_from_other_orms.md)

## [8. 安全性考虑](8.security_considerations/README.md)
- [SQL注入防护](8.security_considerations/sql_injection_protection.md)
- [敏感数据处理](8.security_considerations/sensitive_data_handling.md)
- [访问控制与权限](8.security_considerations/access_control_and_permissions.md)

## [9. 应用场景](9.application_scenarios/README.md)
### 9.1 Web应用开发
- [Web API后端开发](9.application_scenarios/9.1.web_application_development/web_api_backend_development.md)
- [与各种Web框架集成](9.application_scenarios/9.1.web_application_development/integration_with_web_frameworks.md)

### 9.2 数据分析应用
- [报表生成](9.application_scenarios/9.2.data_analysis_applications/report_generation.md)
- [数据转换处理](9.application_scenarios/9.2.data_analysis_applications/data_transformation_processing.md)

### 9.3 企业应用开发
- [微服务架构中的应用](9.application_scenarios/9.3.enterprise_application_development/applications_in_microservice_architecture.md)
- [企业级数据库集成](9.application_scenarios/9.3.enterprise_application_development/enterprise_database_integration.md)

### 9.4 命令行工具开发
- [数据处理脚本](9.application_scenarios/9.4.command_line_tool_development/data_processing_scripts.md)
- [ETL流程实现](9.application_scenarios/9.4.command_line_tool_development/etl_process_implementation.md)

## [10. 完整使用示例](10.complete_examples/README.md)
- Web应用示例
- 数据分析示例
- 微服务示例
- 命令行工具示例

## [11. 贡献指南](11.contributing/README.md)
- [想法与功能请求](11.contributing/ideas_and_feature_requests.md)
- [开发流程](11.contributing/development_process.md)
- [Bug修复](11.contributing/bug_fixes.md)
- [文档贡献](11.contributing/documentation_contributions.md)
- [赞助支持](11.contributing/sponsorship.md)

## [12. API参考](12.api_reference/README.md)
- 完整类/方法文档
