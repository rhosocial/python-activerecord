# 哲学和设计方法

## rhosocial ActiveRecord

rhosocial ActiveRecord 遵循活动记录模式，其中：
- 每个模型类对应一个数据库表
- 每个实例对应该表中的一行
- 模型对象通过其方法直接管理数据库操作

该库采用"约定优于配置"的方法，使用 Pydantic 进行强类型验证，并优先考虑在 Python 代码中感觉自然的直观、以模型为中心的 API。
这种 Pydantic 集成是一个核心区别特性，使其能够与其他基于 Pydantic 的系统无缝交互。

rhosocial ActiveRecord 还采用了渐进式异步编程方法，允许开发者根据应用需求选择同步和异步接口。

## SQLAlchemy

SQLAlchemy 遵循更复杂的架构，具有两个不同的层：
- 核心层：提供直接 SQL 构建的 SQL 表达式语言
- ORM 层：实现数据映射器模式的可选层

SQLAlchemy 强调显式配置和灵活性，允许对 SQL 生成和执行进行精细控制。它将数据库操作与模型对象分离，使其更适合复杂的数据库模式和操作。

虽然 SQLAlchemy 在 1.4 及更高版本中提供了异步支持，但与同步代码相比，它需要一种不同的方法，导致应用程序设计上可能存在不一致。

## Django ORM

作为 Django Web 框架的一部分，Django ORM 的设计目标是：
- 与 Django 的其他组件紧密集成
- 使用最少的配置，易于使用
- 针对 Web 应用程序开发模式进行优化

Django ORM 遵循活动记录模式，但做出了特定的设计选择，以补充 Django 的"内置电池"理念。

Django 在最新版本中添加了有限的异步支持，但它不如从基础开始构建异步能力的框架那样全面。

## Peewee

Peewee 被设计为一种轻量级替代方案，专注于：
- 简单性和小占用空间
- 最小依赖
- 易于理解的实现

它遵循类似于 rhosocial ActiveRecord 的活动记录模式，但较少关注高级功能或广泛的类型验证。

Peewee 的异步支持通过单独的扩展 peewee-async 提供，在同步和异步模式之间切换时需要不同的模式。