# 自定义后端 (Custom Backend)

要支持新的数据库（如 PostgreSQL, MySQL），你需要：

1.  **继承 `SQLDialectBase`**: 定义该数据库特定的 SQL 语法（引号风格、类型映射）。
2.  **继承 `StorageBackend`**: 实现 `connect`, `execute`, `fetch` 等底层 I/O 操作。

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

## 测试与协议支持

Rhosocial ActiveRecord 的测试套件被设计为能够感知协议。这意味着它会自动适应您的后端能力：

*   **自动测试选择**: 测试运行器会检查您方言的特性标志（例如 `supports_window_functions()`）。
*   **跳过不支持的特性**: 如果您的方言对特定特性返回 `False`，相应的测试将被自动跳过。
*   **验证**: 如果您的方言返回 `True` 但未能为该特性生成有效的 SQL，测试将会失败。

因此，准确实现方言中的 `supports_*` 方法至关重要。切勿对您尚未完全实现或验证的特性返回 `True`。
