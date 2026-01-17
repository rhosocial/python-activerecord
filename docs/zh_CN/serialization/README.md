# 第八章：序列化 (Serialization)

rhosocial-activerecord 充分利用了 Pydantic V2 的序列化能力，使得模型与 JSON、字典等格式之间的转换变得异常简单且类型安全。

## 目录

*   [JSON 序列化 (JSON Serialization)](json.md): 介绍如何将模型转换为 JSON 和字典，以及如何处理字段过滤和关联数据。

## 核心特性

*   **Pydantic Native**: 直接继承 `BaseModel`，享受完整的 Pydantic 生态支持。
*   **Flexible Control**: 支持 `include`、`exclude` 等参数精确控制输出。
*   **Type Safe**: 序列化过程遵循严格的类型定义。
