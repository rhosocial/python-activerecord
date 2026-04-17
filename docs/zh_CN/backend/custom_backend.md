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

`DummyDialect` (`src/rhosocial/activerecord/backend/impl/dummy/dialect.py`) 是一个极好的学习资源，因为它支持 **除内省协议以外的所有协议**（内省协议需要真实数据库连接，而 Dummy 不对应真实数据库）。

> **注意**："Dummy" 是指用于测试的逻辑数据库，而非 MySQL 或 PostgreSQL 这样的具体数据库产品。因此，内省协议（用于查询实际数据库元数据）不适用于 Dummy。

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

### 协议命名原则

在为您自己的自定义后端实现协议时，请遵循以下原则：

#### 1. 通用协议不使用后端前缀

通用协议（如 `WindowFunctionSupport`、`TableSupport`、`IndexSupport`）定义在 `rhosocial.activerecord.backend.dialect.protocols` 中，**不应包含任何后端特定前缀**。

```python
# ✅ 正确：通用协议
class WindowFunctionSupport(Protocol):
    def supports_window_functions(self) -> bool: ...

# ❌ 错误：包含后端前缀
class MySQLWindowFunctionSupport(Protocol): ...
```

#### 2. 后端特定协议必须有前缀

后端特定协议必须包含后端名称作为前缀（例如 `PostgresPartitionSupport`、`MySQLFullTextSearchSupport`）。

```python
# ✅ 正确：后端特定协议有前缀
class PostgresPartitionSupport(Protocol): ...

# ❌ 错误：缺少前缀
class PartitionSupport(Protocol): ...
```

#### 3. 优先使用通用协议，其次后端特定协议

**如果通用协议已经定义了满足您需要的接口，请使用通用协议。** 仅在通用协议无法覆盖您数据库的特定语法时，才定义后端特定的接口。

```python
# 示例：MySQL 全文搜索
# 通用 IndexSupport 协议已经定义了 supports_fulltext_index
# ✅ 使用通用协议并设置版本检查
class MySQLDialect(
    IndexSupport,  # 已经包含 supports_fulltext_index
    ...
):
    def supports_fulltext_index(self) -> bool:
        return self.version >= (5, 6, 0)

# 仅在需要 MySQL 特定接口时创建 MySQLFullTextSearchSupport：
# - format_match_against() - MySQL MATCH...AGAINST 语法
# - format_fulltext_index_options() - WITH PARSER 等
class MySQLFullTextSearchSupport(Protocol):
    def format_match_against(...): ...  # MySQL 特定
    def format_fulltext_index_options(...): ...  # MySQL 特定
```

这一原则确保：
- **无接口重复**：每个接口只定义一次
- **职责清晰**：通用协议覆盖标准 SQL，后端特定协议覆盖差异
- **可维护性**：标准 SQL 的变更只需在一处进行

#### 4. 通过 dialect_options 传递后端特定选项

当通用协议的格式化接口有后端特定参数时，使用 `dialect_options` 参数：

```python
# 通用协议定义带 dialect_options 的接口
class JSONSupport(Protocol):
    def supports_json_table(
        self, dialect_options: Optional[Dict[str, Any]] = None
    ) -> bool:
        """检查是否支持 JSON_TABLE。

        Args:
            dialect_options: 后端特定选项
        """
        ...

    def format_json_table_expression(
        self,
        expr,
        dialect_options: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, tuple]:
        """格式化 JSON_TABLE 表达式。

        Args:
            expr: JSONTableExpression 实例
            dialect_options: 后端特定选项，例如：
                - MySQL: {'on_error': 'IGNORE'}
                - PostgreSQL: {...}
        """
        ...
```

**在表达式中的用法：**

```python
# 创建表达式时传入 dialect_options
JSONTableExpression(
    dialect,
    json_column=User.json_data,
    path='$.addresses[*]',
    columns=[...],
    dialect_options={'on_error': 'IGNORE'}  # MySQL 特定
)
```

**优势：**
- **一致的接口**：通用协议定义签名
- **可扩展**：每个后端可以文档化自己的选项
- **类型安全**：类型检查器可以验证接口签名
- **向后兼容**：添加选项不会破坏现有实现

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

## 约束能力检测

rhosocial-activerecord 提供了 `ConstraintSupport` 协议，用于检测数据库对 SQL 标准约束功能的支持能力。

### 支持的约束类型

| 类别 | 特性 | SQL 标准 |
|------|------|----------|
| 基础约束 | PRIMARY KEY, UNIQUE, NOT NULL, CHECK, FOREIGN KEY | SQL-86/SQL-92 |
| 外键动作 | ON DELETE, ON UPDATE | SQL-92 |
| 匹配模式 | MATCH {SIMPLE\|PARTIAL\|FULL} | SQL:1999 |
| 延迟约束 | DEFERRABLE / INITIALLY DEFERRED/IMMEDIATE | SQL:1999 |
| 约束控制 | ENFORCED / NOT ENFORCED | SQL:2016 |
| ALTER TABLE | ADD CONSTRAINT, DROP CONSTRAINT | SQL-92 |

### 实现示例

```python
from rhosocial.activerecord.backend.dialect.mixins import ConstraintMixin
from rhosocial.activerecord.backend.dialect.protocols import ConstraintSupport

class MyDialect(ConstraintMixin, ConstraintSupport):
    def supports_check_constraint(self) -> bool:
        """根据数据库版本判断是否支持 CHECK 约束"""
        return self.version >= (8, 0, 0)

    def supports_fk_match(self) -> bool:
        """SQLite 不支持 MATCH 子句"""
        return False
```

### 使用示例

```python
if dialect.supports_check_constraint():
    # 可以使用 CHECK 约束
    pass

if dialect.supports_add_constraint():
    # 可以使用 ALTER TABLE ADD CONSTRAINT
    pass
```

### SQLite 特殊说明

SQLite 不支持 `ALTER TABLE ADD/DROP CONSTRAINT`，也不支持 `MATCH` 子句、`DEFERRABLE` 表约束和 `ENFORCED/NOT ENFORCED` 控制。在实现 SQLite 方言时，这些方法应返回 `False`。

> 💡 **AI提示词示例**: "如何在自定义后端中实现约束能力检测？不同数据库对约束的支持有哪些差异？"

## 后端命令行 (CLI) 支持

后端还可以通过实现 `__main__.py` 模块作为命令行工具使用。这对于调试、快速访问数据库或测试您的实现非常有用。

例如，**SQLite** 后端 (`src/rhosocial/activerecord/backend/impl/sqlite/__main__.py`) 可以直接执行：

```bash
# 针对数据库文件运行 SQL 查询
python -m rhosocial.activerecord.backend.impl.sqlite --db-file my.db "SELECT * FROM users"

# 执行 SQL 脚本文件
python -m rhosocial.activerecord.backend.impl.sqlite --db-file my.db -f schema.sql --executescript
```

## 后端特定表达式与协议

在实现数据库后端时，您可能需要添加对非 SQL 标准特性的支持。本节介绍添加新表达式及其对应协议的流程。

### 表达式与协议的关系

rhosocial-activerecord 中的表达式分为两类：

1. **通用表达式 (Generic Expressions)**：定义在 `src/rhosocial/activerecord/backend/expression/`，可在所有数据库中使用，基于标准 SQL 或方言抽象。

2. **后端特定表达式 (Backend-Specific Expressions)**：定义在后端特定的 `expression/` 子目录（如 `mysql/expression/`），实现特定数据库的功能。

### 协议-表达式-格式化模式

每个后端特定特性通常遵循以下模式：

```
协议 (supports_* + format_*) 
    ↓
表达式 (收集参数，调用 dialect.format_*)
    ↓
Dialect 格式化实现
```

#### 示例：MySQL MATCH...AGAINST

**步骤 1: 定义协议** (`mysql/protocols.py`，Protocol: 协议)

```python
@runtime_checkable
class FullTextSearchSupport(Protocol):
    def supports_fulltext_index(self) -> bool:  # supports_* 方法
        """是否支持 FULLTEXT 索引"""
        ...

    def format_match_against(  # format_* 方法
        self,
        columns: List[str],
        search_string: str,
        mode: Optional[str] = None
    ) -> Tuple[str, tuple]:
        """格式化 MATCH...AGAINST 表达式"""
        ...
```

**步骤 2: 定义表达式** (`mysql/expression/match_against.py`，Expression: 表达式)

```python
class MatchAgainstExpression(AliasableMixin, ComparisonMixin, SQLValueExpression):
    def __init__(
        self,
        dialect: MySQLDialect,
        columns: List[str],
        search_string: str,
        mode: Optional[str] = None,
    ):
        super().__init__(dialect)
        self.columns = columns
        self.search_string = search_string
        self.mode = mode

    def to_sql(self) -> Tuple[str, tuple]:
        # 委托给方言的格式化方法
        return self.dialect.format_match_against(
            self.columns,
            self.search_string,
            self.mode,
        )

    def as_(self, alias: str) -> AliasColumn:
        return AliasColumn(self, alias)
```

**步骤 3: 在方言中实现协议** (`mysql/dialect.py`，Dialect: 方言)

```python
class MySQLDialect(
    MySQLBaseMixin,
    FullTextSearchSupport,  # 添加协议
    ...
):
    def supports_fulltext_index(self) -> bool:
        return self.version >= (5, 6, 0)

    def format_match_against(
        self,
        columns: List[str],
        search_string: str,
        mode: Optional[str] = None
    ) -> Tuple[str, tuple]:
        cols_sql = ", ".join(self.format_identifier(c) for c in columns)
        placeholder = self.get_parameter_placeholder()
        
        # 模式映射 (mode mapping)
        mode_map = {
            "NATURAL_LANGUAGE": "IN NATURAL LANGUAGE MODE",
            "BOOLEAN": "IN BOOLEAN MODE",
            "QUERY_EXPANSION": "IN NATURAL LANGUAGE MODE WITH QUERY EXPANSION",
        }
        mode_str = mode_map.get(mode, "IN NATURAL LANGUAGE MODE")
        
        sql = f"MATCH({cols_sql}) AGAINST({placeholder} {mode_str})"
        return sql, (search_string,)
```

**步骤 4: 添加测试**

```python
def test_match_against_expression(self):
    dialect = MySQLDialect(version=(8, 0, 0))
    expr = MatchAgainstExpression(
        dialect,
        columns=['title', 'content'],
        search_string='database',
    )
    sql, params = expr.to_sql()
    assert 'MATCH' in sql
    assert 'AGAINST' in sql
    assert params == ('database',)
```

### 使用此模式的场景

在以下情况下使用此模式：

1. 特性是后端特定的（非 SQL 标准）
2. 特性需要版本检测
3. 需要多种格式化方法（如创建索引 + 查询）
4. 表达式需要与查询构建器集成

### 将协议实现分离到 Mixin

为了更好的组织，协议实现可以分离到单独的 mixin 类中，避免方言类过于臃肿。这正是 MySQL 使用的模式：

**`mysql/mixins.py`** (协议实现)

```python
class MySQLFullTextMixin:
    def supports_fulltext_index(self) -> bool:
        return self.version >= (5, 6, 0)

    def supports_fulltext_parser(self) -> bool:
        return self.version >= (5, 1, 0)

    def format_match_against(
        self,
        columns: List[str],
        search_string: str,
        mode: Optional[str] = None
    ) -> Tuple[str, tuple]:
        # 实现...
```

**`mysql/dialect.py`** (组合 Mixin)

```python
class MySQLDialect(
    MySQLBaseMixin,
    MySQLFullTextMixin,  # 分离的 mixin 用于组织
    FullTextSearchSupport,
    ...
):
    pass
```

优势：
- **代码组织**：相关方法分组在一起
- **可维护性**：更容易定位和修改特定特性
- **可重用性**：可以根据需要混合到不同的方言中

### 协议方法说明

| 方法类型 | 用途 |
|----------|------|
| `supports_*` | 检查特性是否支持（基于版本） |
| `format_*` | 生成特性的 SQL |
| `format_create_*` | 生成 CREATE 语句（如适用） |

### 强制流程：新增方言方法必须经过 Protocol → Mixin → Dialect

**严禁直接在方言类中添加 `format_*` 或 `supports_*` 方法。** 每个新的方言方法必须按以下三步流程完成：

1. **Protocol**：在对应的 Protocol 类中声明接口签名（`supports_*` + `format_*`）
2. **Mixin**：在对应的 Mixin 类中提供默认实现（不支持的抛 `UnsupportedFeatureError`，`supports_*` 默认返回 `False`）
3. **Dialect**：在具体方言类中混入 Protocol + Mixin，覆写需要的方法

**原因**：探查工具（`devtools/inspect`）依赖 Protocol 和 Mixin 来发现能力声明和方法签名。跳过任何一步会导致探查工具遗漏该方法，使得后端能力无法被正确检测。

**通用 vs 后端特定**：
- **通用特性**（SQL 标准或多数数据库支持）：Protocol 和 Mixin 定义在核心包 `dialect/protocols.py` 和 `dialect/mixins.py` 中
- **后端特定特性**（仅某个数据库支持）：Protocol 和 Mixin 定义在后端包自己的 `protocols.py` 和 `mixins.py` 中，但命名必须带后端前缀（如 `MySQLModifyColumnSupport`、`MySQLModifyColumnMixin`）

**示例**：为 MySQL 添加 `MODIFY COLUMN` 支持

```python
# 步骤 1: MySQL 专属 Protocol (mysql/protocols.py)
@runtime_checkable
class MySQLModifyColumnSupport(Protocol):
    def supports_modify_column(self) -> bool: ...
    def format_modify_column_action(self, action) -> Tuple[str, tuple]: ...

# 步骤 2: MySQL 专属 Mixin (mysql/mixins.py)
class MySQLModifyColumnMixin:
    def supports_modify_column(self) -> bool:
        return self.version >= (5, 0, 0)  # 所有 MySQL 5.x+ 支持

    def format_modify_column_action(self, action) -> Tuple[str, tuple]:
        col_sql, col_params = self.format_column_definition(action.column)
        sql = f"MODIFY COLUMN {col_sql}"
        if action.after_column:
            sql += f" AFTER {self.format_identifier(action.after_column)}"
        elif action.first:
            sql += " FIRST"
        return sql, col_params

# 步骤 3: MySQL 方言混入 Protocol + Mixin (mysql/dialect.py)
class MySQLDialect(
    MySQLModifyColumnMixin,
    MySQLModifyColumnSupport,
    ...
):
    pass  # Mixin 中已有实现，无需额外覆写
```

> **注意**：核心包的 `SQLDialectBase`（`base.py`）中可以提供抛 `UnsupportedFeatureError` 的默认实现，确保 `AlterTableAction.to_sql()` 等调用路径不会因方法缺失而崩溃。但这**不替代** Protocol/Mixin 步骤——默认实现只是安全兜底，真正的接口声明和能力检测仍需通过 Protocol/Mixin 完成。
