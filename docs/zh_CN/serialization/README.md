# 11. 序列化 (Serialization)

rhosocial-activerecord 充分利用了 Pydantic V2 的序列化能力，使得模型与 JSON、字典等格式之间的转换变得异常简单且类型安全。

## 目录

*   [JSON 序列化 (JSON Serialization)](json.md): 介绍如何将模型转换为 JSON 和字典，以及如何处理字段过滤和关联数据。

## 核心特性

*   **Pydantic Native**: 直接继承 `BaseModel`，享受完整的 Pydantic 生态支持。
*   **Flexible Control**: 支持 `include`、`exclude` 等参数精确控制输出。
*   **Type Safe**: 序列化过程遵循严格的类型定义。

## 示例代码

本章的完整示例代码位于 `docs/examples/chapter_11_serialization/` 目录：

| 文件 | 说明 |
|------|------|
| [01_basic_serialization.py](../../examples/chapter_11_serialization/01_basic_serialization.py) | 基本序列化：model_dump()、model_dump_json()、字段类型处理 |
| [02_field_filtering.py](../../examples/chapter_11_serialization/02_field_filtering.py) | 字段过滤：exclude、include、嵌套过滤、上下文感知 |
| [03_related_data.py](../../examples/chapter_11_serialization/03_related_data.py) | 关联数据：序列化关系、computed_field、嵌套模式
