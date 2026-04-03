# 7. 日志系统

> 💡 **AI 提示**: "ActiveRecord 的日志系统如何防止敏感数据出现在日志中？"

`rhosocial-activerecord` 日志系统提供了智能数据摘要功能，可自动截断大值并屏蔽日志消息中的敏感字段。

## 概述

日志系统的核心原则：

1. **与根日志器隔离**：不修改应用程序的根日志器配置
2. **数据摘要**：自动截断长字符串并屏蔽敏感字段
3. **可配置模式**：在摘要模式、仅键模式或完整日志模式之间选择
4. **零配置**：开箱即用，提供合理的默认设置
5. **层次化命名**：采用语义化的层次日志命名空间，便于统一控制和精细调节

## 章节目录

* **[日志命名空间](namespace.md)**: 层次化日志命名规则、用户自定义类处理、层次继承优势
* **[数据摘要](data_summarization.md)**: 敏感字段屏蔽、三种日志模式、配置选项
* **[按层级配置](per_logger_config.md)**: 为不同组件设置不同摘要模式、层次继承规则

## 快速开始

### 基本用法

使用 ActiveRecord 时会自动配置日志系统：

```python
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend

# 日志系统自动配置
class User(ActiveRecord):
    __table_name__ = "users"
    id: Optional[int] = None
    username: str
    password: str  # 将在日志中被屏蔽

# 保存时，password 自动在日志中被屏蔽
user = User(username="john", password="secret123")
user.save()
# 日志显示: {'username': 'john', 'password': '***MASKED***'}
```

### 自定义日志级别

```python
import logging
from rhosocial.activerecord.logging import configure_logging

# 设置日志级别为 INFO
configure_logging(level=logging.INFO)
```

### 快速配置数据摘要

```python
from rhosocial.activerecord.logging import (
    SummarizerConfig,
    get_logging_manager,
)

# 定义自定义敏感字段
config = SummarizerConfig(
    sensitive_fields={
        'password', 'token', 'api_key',
        'credit_card', 'ssn'
    },
    mask_placeholder='[REDACTED]',
)

manager = get_logging_manager()
manager.config.summarizer_config = config
```

## 示例代码

完整的示例代码位于 `docs/examples/chapter_07_logging/` 目录：

| 文件 | 说明 |
|------|------|
| [01_basic_configuration.py](../../examples/chapter_07_logging/01_basic_configuration.py) | 基本配置：日志级别设置、命名空间层次、运行时级别调整 |
| [02_data_summarization.py](../../examples/chapter_07_logging/02_data_summarization.py) | 数据摘要：敏感字段屏蔽、字符串截断、三种日志模式 |
| [03_per_logger_config.py](../../examples/chapter_07_logging/03_per_logger_config.py) | 按层级配置：不同组件使用不同摘要模式、层次继承 |
| [04_advanced_scenarios.py](../../examples/chapter_07_logging/04_advanced_scenarios.py) | 高级场景：生产/开发环境配置、自定义日志器名称、与应用集成 |

运行示例：

```bash
cd python-activerecord
source .venv3.8/bin/activate
python docs/examples/chapter_07_logging/01_basic_configuration.py
```

## 最佳实践

1. **生产环境**：使用 `summary` 或 `keys_only` 模式
2. **开发环境**：使用 `summary` 模式和 `DEBUG` 级别
3. **调试时**：临时使用 `full` 模式，但永远不要提交到生产环境
4. **自定义字段**：始终将应用程序特定的敏感字段添加到配置中
5. **合规性**：尽可能使用 `keys_only` 模式以满足 GDPR/PCI 合规要求

## 另见

- [故障排除](../getting_started/troubleshooting.md) - 常见日志问题
- [性能](../performance/README.md) - 日志开销注意事项
