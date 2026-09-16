# 场景实战 (Scenarios)

将 `rhosocial-activerecord` 集成到现代 Web 框架中，以及在复杂并发场景下的正确用法。

## 目录

*   **[FastAPI 集成](fastapi.md)**: 异步、连接池隔离、推导 DDL、日志与 Prometheus 指标。
*   **[GraphQL 集成](graphql.md)**: 解决 N+1 问题，构建高效 API。

## 示例代码

本章的完整示例代码位于 `docs/examples/chapter_14_scenarios/`。

| 目录               | 内容                                       |
|--------------------|--------------------------------------------|
| `fastapi_blog/`    | FastAPI 博客 REST API（连接池 + 日志 + 指标） |
| `graphql_fastapi/` | GraphQL + FastAPI 集成示例                 |
