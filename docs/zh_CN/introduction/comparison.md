# 对比分析 (Comparison)

选择 ORM 是一个重大的决定。以下是 `rhosocial-activerecord` 与其他流行 Python ORM 的对比。

| 特性 | rhosocial-activerecord | SQLModel | SQLAlchemy | Django ORM |
| :--- | :--- | :--- | :--- | :--- |
| **设计模式** | Active Record | Data Mapper / 混合 | Data Mapper | Active Record |
| **数据验证** | Pydantic V2 (原生) | Pydantic V1/V2 | 可选 / 外部集成 | 内部系统 |
| **类型安全** | 高 (Field Proxies) | 高 | 高 (2.0+) | 中 |
| **零 IO 测试** | **支持 (原生)** | 不支持 | 不支持 | 不支持 |
| **性能表现** | 可调节 (严格 <-> 原始) | 中 | 高 | 低/中 |
| **上手难度** | 低 | 低 | 高 | 中 |

## vs SQLModel
**SQLModel** 是一个很棒的库，启发了许多现代 Python ORM。它试图统一 Pydantic 和 SQLAlchemy。
*   **区别**: SQLModel 同时继承自 Pydantic 和 SQLAlchemy 模型，这有时会导致“元类冲突”和复杂的 MRO (方法解析顺序) 问题。`rhosocial-activerecord` 保持简单：它 *就是* Pydantic，并且 *使用* 自定义的后端系统，避免了 SQLAlchemy 在简单任务中的复杂性。
*   **选择 rhosocial 如果**: 你想要纯粹的 Active Record 体验，而不需要 SQLAlchemy 的负担。

## vs SQLAlchemy
**SQLAlchemy** 是 Python 数据库访问的工业级标准。它遵循 Data Mapper 模式（数据库表映射到类，但解耦）。
*   **区别**: SQLAlchemy 极其强大，但学习曲线陡峭。你需要理解 Session, Engine, Metadata 和 Unit of Work 模式。`rhosocial-activerecord` 将这些抽象化了。你调用 `save()`，它就保存。
*   **选择 rhosocial 如果**: 你想要快速开发，不需要 Data Mapper 的极端灵活性。

## vs Django ORM
**Django ORM** 是 Python 中最著名的 Active Record 实现。
*   **区别**: Django ORM 与 Django 框架紧密耦合。你无法轻易在 FastAPI 或 Flask 中使用它，除非引入整个 Django。它也使用自己的验证系统，而不是 Pydantic。
*   **选择 rhosocial 如果**: 你正在构建现代异步应用（如 FastAPI）并想要 Pydantic 验证，或者你需要一个用于脚本和工具的独立 ORM。
