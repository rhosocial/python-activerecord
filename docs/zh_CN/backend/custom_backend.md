# 自定义后端 (Custom Backend)

要支持新的数据库（如 PostgreSQL, MySQL），你需要：

1.  **继承 `SQLDialectBase`**: 定义该数据库特定的 SQL 语法（引号风格、类型映射）。
2.  **继承 `StorageBackend`**: 实现 `connect`, `execute`, `fetch`, `introspect_and_adapt` 等底层 I/O 操作。

## 后端自适配 (introspect_and_adapt)

`introspect_and_adapt()` 方法是后端实现 sync/async 对称性的关键。它在模型配置时自动调用，确保后端能够根据实际数据库服务器版本调整其行为：

1. **连接数据库**（如尚未连接）
2. **查询实际服务器版本**
3. **重新初始化方言和类型适配器**以匹配实际版本

例如，MySQL 5.6 不支持 JSON 类型，而 MySQL 8.0 支持。通过 `introspect_and_adapt()`，后端可以查询实际版本并相应调整其功能支持。

对于不需要版本特定适配的后端（如 SQLite、Dummy），可以实现为空操作（no-op）。

### 版本检测行为

`get_server_version()` 方法负责获取数据库服务器版本。**重要变更**：当版本检测失败时，该方法会抛出 `OperationalError` 异常，而非返回默认值。

```python
from rhosocial.activerecord.backend.errors import OperationalError

try:
    version = backend.get_server_version()
except OperationalError as e:
    # 版本检测失败，需要处理错误
    print(f"无法获取数据库版本: {e}")
```

这种设计确保了问题能够被及早发现，而非被掩盖。返回默认版本号可能导致：
- 后续操作在不受支持的数据库版本上执行
- 难以追踪的隐蔽错误
- 用户体验下降

在实现自定义后端时，请确保：
1. 版本检测逻辑足够健壮
2. 提供有意义的错误信息
3. 考虑连接状态对版本检测的影响

## 参考实现

我们推荐参考 `src/rhosocial/activerecord/backend/impl/` 下现有的实现：

*   **`dummy`**: 一个全功能的后端，用于测试 SQL 生成而无需真实数据库。它展示了如何使用标准混入 (Mixins) 实现 **所有** 支持的协议。
*   **`sqlite`**: 一个真实世界的实现，处理了版本特定的特性支持（例如，检查 SQLite 版本以支持 CTE）。

## 基于协议的方言系统

方言系统严重依赖于 `src/rhosocial/activerecord/backend/dialect/protocols.py` 中定义的 **协议 (Protocols)**。这些协议（如 `WindowFunctionSupport`, `CTESupport`）定义了数据库的能力。

### Dummy 方言：一个完整的范例

`DummyDialect` (`src/rhosocial/activerecord/backend/impl/dummy/dialect.py`) 是一个极好的学习资源，因为它支持 **所有特性**。

注意它是如何简单地混入标准实现的：

```python
class DummyDialect(
    SQLDialectBase,
    # 通过 Mixins 引入标准实现
    WindowFunctionMixin, CTEMixin, AdvancedGroupingMixin, ...
    # 协议定义用于类型检查
    WindowFunctionSupport, CTESupport, AdvancedGroupingSupport, ...
):
    # 特性标志
    def supports_window_functions(self) -> bool: return True
    # ...
```

### 实现策略

在实现自定义方言时（例如为 MySQL 或 PostgreSQL），请遵循以下策略：

1.  **检查基类协议**: 查看 `src/rhosocial/activerecord/backend/dialect/protocols.py` 以了解特性需要哪些方法。
2.  **评估默认实现**: 检查 `src/rhosocial/activerecord/backend/dialect/mixins.py`（或基类）。基类实现通常足以应对标准 SQL。
3.  **如果兼容则混入**: 如果标准 SQL 行为适用于您的数据库，只需继承相应的 `Mixin`（例如 `WindowFunctionMixin`）并将特性标志设置为 `True`。
4.  **仅在必要时自定义实现**: 如果您的数据库使用非标准语法，**只有在那时** 您才应该手动实现协议方法。

### 关注格式化函数

混入协议后，请验证相应的格式化方法。例如，如果您混入了 `WindowFunctionMixin`，请检查 Mixin/基类中的 `format_window_function_call`。

*   如果您的数据库遵循标准 SQL（例如 `OVER (...)`），默认实现即可工作。
*   如果有差异，请覆盖该特定方法。

## RETURNING 子句支持（重要）

当保存新记录（INSERT）时，框架需要获取数据库生成的主键值。这通过以下两种方式实现：

### 主键获取策略

| 优先级 | 方式 | 要求 |
|--------|------|------|
| 1 | RETURNING 子句 | 后端实现 `supports_returning_clause()` 返回 `True` |
| 2 | last_insert_id | 后端从 `cursor.lastrowid` 提供整型主键 |

### 后端实现要求

**如果数据库支持 RETURNING 子句**（如 PostgreSQL、SQLite 3.35+、MySQL 8.0+）：

```python
from rhosocial.activerecord.backend.dialect.mixins import ReturningMixin
from rhosocial.activerecord.backend.dialect.protocols import ReturningSupport

class MyDialect(ReturningMixin, ReturningSupport):
    def supports_returning_clause(self) -> bool:
        """根据数据库版本判断是否支持 RETURNING"""
        return self.version >= (x, y, z)  # 替换为实际版本号
```

**如果数据库不支持 RETURNING 子句**：

- 必须确保 `cursor.lastrowid` 可用（大多数 Python 数据库驱动都支持）
- 仅支持整型自增主键（`IntegerPKMixin`）
- 不支持 RETURNING 的后端，使用非整型主键（如 UUID）的新记录保存会失败

### 兼容性矩阵

| 数据库 | RETURNING 支持 | 最低版本 |
|--------|---------------|----------|
| SQLite | ✅ | 3.35.0 |
| PostgreSQL | ✅ | 所有版本 |
| MySQL | ❌ | - (使用 last_insert_id) |
| MariaDB | ❌ | - (使用 last_insert_id) |

> 💡 **AI提示词示例**: "如何在自定义后端中实现 RETURNING 子句支持？如果不支持 RETURNING，有什么限制？"

## 测试与协议支持

Rhosocial ActiveRecord 的测试套件被设计为能够感知协议。这意味着它会自动适应您的后端能力：

*   **自动测试选择**: 测试运行器会检查您方言的特性标志（例如 `supports_window_functions()`）。
*   **跳过不支持的特性**: 如果您的方言对特定特性返回 `False`，相应的测试将被自动跳过。
*   **验证**: 如果您的方言返回 `True` 但未能为该特性生成有效的 SQL，测试将会失败。

因此，准确实现方言中的 `supports_*` 方法至关重要。切勿对您尚未完全实现或验证的特性返回 `True`。

## 后端命令行 (CLI) 支持

后端还可以通过实现 `__main__.py` 模块作为命令行工具使用。这对于调试、快速访问数据库或测试您的实现非常有用。

例如，**SQLite** 后端 (`src/rhosocial/activerecord/backend/impl/sqlite/__main__.py`) 可以直接执行：

```bash
# 针对数据库文件运行 SQL 查询
python -m rhosocial.activerecord.backend.impl.sqlite --db-file my.db "SELECT * FROM users"

# 执行 SQL 脚本文件
python -m rhosocial.activerecord.backend.impl.sqlite --db-file my.db -f schema.sql --executescript
```

这是通过标准 Python 模块执行实现的。在构建您自己的后端时，考虑添加 CLI 接口可以极大地提升开发体验。
