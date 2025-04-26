# ActiveRecord中的关系

本节介绍rhosocial ActiveRecord支持的各种关系类型，以及如何在应用程序中有效地使用它们。

## 目录

- [一对一关系](one_to_one_relationships.md) - 定义和使用一对一关系
- [一对多关系](one_to_many_relationships.md) - 定义和使用一对多关系
- [多对多关系](many_to_many_relationships.md) - 定义和使用多对多关系
- [多态关系](polymorphic_relationships.md) - 定义和使用多态关系
- [自引用关系](self_referential_relationships.md) - 定义和使用自引用关系
- [关系加载策略](relationship_loading_strategies.md) - 理解预加载和延迟加载
- [预加载和延迟加载](eager_and_lazy_loading.md) - 使用不同的加载策略优化性能
- [跨数据库关系](cross_database_relationships.md) - 处理跨不同数据库的关系

## 概述

ActiveRecord中的关系表示数据库表之间的关联，允许您以面向对象的方式处理相关数据。rhosocial ActiveRecord提供了丰富的关系类型和加载策略，帮助您高效地建模复杂的数据关系。

rhosocial ActiveRecord中的关系系统设计为：

- **类型安全**：利用Python的类型提示提供更好的IDE支持和运行时验证
- **直观**：使用描述性类属性定义关系
- **高效**：支持各种加载策略以优化性能
- **灵活**：支持复杂的关系类型，包括多态和自引用关系

## 核心概念

### 关系类型

rhosocial ActiveRecord支持几种关系类型：

- **BelongsTo**：表示多对一关系，当前模型包含引用另一个模型的外键
- **HasOne**：表示一对一关系，另一个模型包含引用当前模型的外键
- **HasMany**：表示一对多关系，另一个模型中的多条记录包含引用当前模型的外键
- **多对多**：通过中间连接表表示，允许一个模型中的多条记录与另一个模型中的多条记录相关联

### 关系加载

rhosocial ActiveRecord支持不同的相关数据加载策略：

- **延迟加载**：仅在明确访问时才加载相关数据
- **预加载**：在单个查询或最少数量的查询中预先加载相关数据

正确使用这些加载策略对应用程序性能至关重要，特别是在处理大型数据集或复杂关系链时。