# 数据摘要

> 💡 **AI 提示**: "ActiveRecord 的数据摘要功能如何防止敏感数据出现在日志中？"

当日志数据（如 INSERT/UPDATE 参数）时，`DataSummarizer` 会自动：

1. **截断长字符串**：防止大文本字段导致日志膨胀
2. **屏蔽敏感字段**：隐藏密码、令牌、API 密钥等
3. **限制集合大小**：只显示列表/字典的前 N 项
4. **控制嵌套深度**：防止无限递归

## 默认敏感字段

以下字段名会被自动屏蔽（不区分大小写）：

```text
password, passwd, pwd
token, access_token, refresh_token, auth_token
secret, secret_key, api_key, apikey
credential, credentials
private_key, privatekey
```

## 自定义敏感字段

```python
from rhosocial.activerecord.logging import (
    SummarizerConfig,
    get_logging_manager,
)

# 定义自定义敏感字段
config = SummarizerConfig(
    sensitive_fields={
        'password', 'token', 'api_key',
        'credit_card', 'ssn', 'phone'  # 添加您的自定义字段
    }
)

manager = get_logging_manager()
manager._config.summarizer_config = config
```

### 追加到默认字段

```python
from rhosocial.activerecord.logging import get_logging_manager, SummarizerConfig

manager = get_logging_manager()
current_fields = manager._config.summarizer_config.sensitive_fields

# 在保留默认字段的同时添加新字段
new_config = SummarizerConfig(
    sensitive_fields=current_fields | {'credit_card', 'ssn'}
)
manager._config.summarizer_config = new_config
```

### 禁用敏感字段屏蔽

如果您不需要敏感字段屏蔽功能（例如在受控的开发环境中），可以通过以下方式禁用：

```python
from rhosocial.activerecord.logging import (
    SummarizerConfig,
    get_logging_manager,
)

# 设置空的敏感字段集合，禁用屏蔽功能
config = SummarizerConfig(
    sensitive_fields=set()  # 空集合 = 不屏蔽任何字段
)

manager = get_logging_manager()
manager._config.summarizer_config = config
```

> ⚠️ **警告**：禁用敏感字段屏蔽可能导致密码、令牌等敏感信息出现在日志中。请确保仅在安全可控的环境中使用此配置。

## 日志模式

三种模式控制数据的日志记录方式：

### 1. 摘要模式（默认）

截断长值并屏蔽敏感字段：

```python
manager._config.log_data_mode = 'summary'

# 日志中的结果：
# {'title': 'Short', 'content': 'Lorem ipsum...[truncated, 1000 chars total]', 'password': '***MASKED***'}
```

### 2. 仅键模式

只显示字段名和类型提示，不显示实际值：

```python
manager._config.log_data_mode = 'keys_only'

# 日志中的结果：
# {'title': '<str>', 'content': '<str>', 'password': '***MASKED***'}
```

此模式非常适合生产环境和需要 GDPR/PCI 合规的场景。

### 3. 完整模式

显示完整数据，不进行摘要（请谨慎使用）：

```python
manager._config.log_data_mode = 'full'

# 日志中的结果（完整数据）：
# {'title': 'Short', 'content': 'Lorem ipsum dolor...', 'password': 'secret123'}
```

> ⚠️ **警告**：`full` 模式可能会记录敏感数据。不建议在生产环境中使用。

## 配置选项

所有可用的 `SummarizerConfig` 选项：

| 选项 | 默认值 | 描述 |
|------|--------|------|
| `max_string_length` | 100 | 截断前的最大字符串长度 |
| `max_bytes_length` | 64 | 截断前的最大字节长度 |
| `max_dict_items` | 10 | 字典/列表中显示的最大项数 |
| `max_depth` | 5 | 递归数据的最大嵌套深度 |
| `sensitive_fields` | 见上文 | 要屏蔽的字段名集合 |
| `mask_placeholder` | `***MASKED***` | 被屏蔽字段的占位符 |
| `string_placeholder` | `...[truncated, {length} chars total]` | 截断字符串的占位符 |
| `show_type_hint` | True | 在截断消息中显示类型提示 |

### 完整配置示例

```python
import logging
from rhosocial.activerecord.logging import (
    SummarizerConfig,
    LoggingConfig,
    get_logging_manager,
)

# 创建自定义配置
summarizer_config = SummarizerConfig(
    max_string_length=200,
    max_dict_items=5,
    sensitive_fields={
        'password', 'token', 'api_key',
        'credit_card', 'ssn'
    },
    mask_placeholder='[REDACTED]',
)

manager = get_logging_manager()
manager._config.summarizer_config = summarizer_config
manager._config.log_data_mode = 'summary'
manager._config.default_level = logging.DEBUG
```

## 使用 log_data 方法

`LoggingMixin` 提供了便捷的方法来记录带有摘要的数据：

```python
from rhosocial.activerecord.model import ActiveRecord
import logging

class User(ActiveRecord):
    __table_name__ = "users"
    # ... 字段 ...

# 记录数据并自动摘要
User.log_data(logging.INFO, "Creating user", {
    'username': 'john',
    'password': 'secret123',
    'bio': 'A' * 1000
})

# 仅记录键（不记录值）
User.log_data_keys_only(logging.INFO, "User data", user_dict)

# 记录完整数据（绕过摘要）
User.log_data_full(logging.DEBUG, "Debug user data", user_dict)
```

## 与后端集成

后端在记录查询日志时自动使用数据摘要：

```python
# SQLite 后端使用摘要记录 INSERT
user = User(username="john", password="secret", bio="Long bio...")
user.save()

# 日志显示为：
# DEBUG - Raw data for insert: {'username': 'john', 'password': '***MASKED***', 'bio': 'Long bio...[truncated, 1000 chars total]'}
```
