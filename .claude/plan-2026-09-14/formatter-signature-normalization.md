# 格式化函数签名规范化改造计划

> 目标：所有 `format_*` 格式化函数统一为 `(self, expr: SomeExpression) -> Tuple[str, tuple]`，消除 isinstance 判断，补齐类型提示。

## 一、返回类型不是 Tuple[str, tuple] 的方法

### 1.1 返回 `str` 的方法

| 方法 | 文件 | 当前签名 | 改造方案 |
|------|------|---------|---------|
| `format_pk_constraint` | `mixins/ddl_column.py:231` | `(self, t_const: "TableConstraint") -> str` | 改返回类型为 `Tuple[str, tuple]`，返回 `(sql, ())` |
| `format_unique_constraint` | `mixins/ddl_column.py:248` | `(self, t_const: "TableConstraint") -> str` | 同上 |
| `format_xml_name` | `mixins/xml.py:164` | `(self, name: str) -> str` | 这是内部辅助函数，非表达式格式化，可保留。但需确认是否可改为接收 expr |

### 1.2 返回类型大小写不一致

所有使用 `-> Tuple[str, Tuple]` 的方法统一改为 `-> Tuple[str, tuple]`（小写 tuple）。

涉及文件：`mixins/expression.py`、`mixins/function.py`、`mixins/predicate.py` 中约 52 个方法。

## 二、参数不是 expr 的方法

### 2.1 `format_storage_options`

- **当前签名**: `(self, storage_options: Dict[str, Any]) -> Tuple[str, Tuple]`
- **改造方案**:
  1. 在 `expression/statements/ddl_table.py` 中，`CreateTableExpression` 已有 `storage_options: Dict[str, Any]` 字段
  2. 新建 `StorageOptionsExpression` 表达式类（或直接让 `format_storage_options` 接收 `expr: "CreateTableExpression"`，从 `expr.storage_options` 取值）
  3. **推荐方案**: 创建 `StorageOptionsExpression` 表达式类，持有 `options: Dict[str, Any]`，调用方改为 `self.format_storage_options(StorageOptionsExpression(dialect, expr.storage_options))`
  4. 去掉 isinstance 判断，值直接用 `inline_sql_literal` 渲染

### 2.2 `format_alias`

- **当前签名**: `(self, expression_sql: str, alias: str, expression_params: tuple) -> Tuple[str, Tuple]`
- **改造方案**: 这是内部辅助方法，接收已格式化的 SQL 片段，非表达式格式化。可保留但改为 `-> Tuple[str, tuple]`

### 2.3 `format_limit_offset`

- **当前签名**: `(self, limit=None, offset=None) -> Tuple[str, List]`
- **改造方案**: 此方法是低级辅助，`format_limit_offset_clause` 才是接收 clause 的版本。保留此方法但返回类型改为 `Tuple[str, tuple]`

### 2.4 `format_data_type`

- **当前签名**: `(self, data_type: DataType) -> SQLQueryAndParams`
- **改造方案**: `SQLQueryAndParams` 等价于 `Tuple[str, tuple]`，可保留。参数名 `data_type` 是合理的（不是表达式格式化，是类型格式化）

## 三、参数缺少类型提示的方法

### 3.1 `expression.py` — 缺少类型提示的方法

| 方法 | 当前 | 补齐为 |
|------|------|--------|
| `format_identifier_expression` | `(self, expr)` | `(self, expr: "IdentifierExpression")` |
| `format_wildcard` | `(self, expr)` | `(self, expr: "WildcardExpression")` |
| `format_qualified_identifier` | `(self, expr)` | `(self, expr: "QualifiedIdentifierExpression")` |
| `format_cast_expression` | `(self, expr)` | `(self, expr: "CastExpression")` |
| `format_sql_operation` | `(self, expr)` | `(self, expr: "SQLOperation")` |
| `format_binary_operator` | `(self, expr)` | `(self, expr: "BinaryExpression")` |
| `format_unary_operator` | `(self, expr)` | `(self, expr: "UnaryExpression")` |
| `format_binary_arithmetic_expression` | `(self, expr)` | `(self, expr: "BinaryArithmeticExpression")` |
| `format_raw_sql` | `(self, expr)` | `(self, expr: "RawSQLExpression")` |
| `format_subquery` | `(self, expr)` | `(self, expr: "Subquery")` |

### 3.2 `predicate.py` — 全部 10 个方法缺少类型提示

| 方法 | 补齐为 |
|------|--------|
| `format_comparison_predicate` | `(self, expr: "ComparisonPredicate")` |
| `format_logical_predicate` | `(self, expr: "LogicalPredicate")` |
| `format_in_predicate` | `(self, expr: "InPredicate")` |
| `format_between_predicate` | `(self, expr: "BetweenPredicate")` |
| `format_is_null_predicate` | `(self, expr: "IsNullPredicate")` |
| `format_is_boolean_predicate` | `(self, expr: "IsBooleanPredicate")` |
| `format_exists_expression` | `(self, expr: "ExistsExpression")` |
| `format_any_expression` | `(self, expr: "AnyExpression")` |
| `format_all_expression` | `(self, expr: "AllExpression")` |
| `format_like_predicate` | `(self, expr: "LikePredicate")` |

### 3.3 `dql.py` — 4 个方法缺少类型提示

| 方法 | 补齐为 |
|------|--------|
| `format_limit_offset_clause` | `(self, clause: "LimitOffsetClause")` |
| `format_where_clause` | `(self, clause: "WhereClause")` |
| `format_order_by_clause` | `(self, clause: "OrderByClause")` |
| `format_group_by_having_clause` | `(self, clause: "GroupByHavingClause")` |

### 3.4 `ddl_table.py`

| 方法 | 补齐为 |
|------|--------|
| `format_table` | `(self, expr: "TableExpression")` |

### 3.5 `join.py`

| 方法 | 补齐为 |
|------|--------|
| `format_lateral_expression` | `(self, expr: "LateralExpression")` |

## 四、消除 isinstance 判断

### 4.1 `format_binary_arithmetic_expression` — `_needs_parens`

- **isinstance**: `isinstance(operand, BinaryArithmeticExpression)`
- **改造**: 让 `BinaryArithmeticExpression` 实现 `precedence` 属性，通过 duck-typing 或 Protocol 检查 `hasattr(operand, 'OPERATOR_PRECEDENCE')`

### 4.2 `format_comparison_predicate`

- **isinstance**: `isinstance(expr.right, QueryExpression)`
- **改造**: 让所有表达式实现统一的 `needs_parenthesization()` 方法，或在 `ComparisonPredicate` 的 `right` 字段上通过 `to_sql()` 返回的 SQL 自动判断（子查询的 `to_sql()` 已自带括号）

### 4.3 `format_in_predicate`

- **isinstance**: `isinstance(expr.values, Literal) and isinstance(expr.values.value, (list, tuple, set))`
- **改造**: `InPredicate` 应在构造时区分 `values_list` 和 `subquery` 两种模式，格式化函数只调用 `expr.values.to_sql()` 或 `expr.values_list`，不做 isinstance

### 4.4 `format_any_expression` / `format_all_expression`

- **isinstance**: `isinstance(array_expr.value, (list, tuple))`
- **改造**: `AnyExpression`/`AllExpression` 应在构造时将集合值封装为表达式对象，格式化时统一调用 `to_sql()`

### 4.5 `format_limit_offset_clause`

- **isinstance**: `isinstance(clause.limit, ToSQLProtocol)` / `isinstance(clause.offset, ToSQLProtocol)`
- **改造**: `LimitOffsetClause` 的 `limit`/`offset` 字段应统一为表达式对象（构造时将原始值包装为 `Literal`）

### 4.6 `format_order_by_clause`

- **isinstance**: `isinstance(item, tuple)`
- **改造**: `OrderByClause` 的 items 应统一为 `OrderByItem` 表达式对象（包含 `expression` 和 `direction` 属性）

### 4.7 `format_query_statement` — FROM 子句

- **isinstance**: `isinstance(expr.from_, str)` / `isinstance(expr.from_, list)` / `isinstance(source, str)`
- **改造**: `QueryExpression.from_` 应统一为表达式对象列表（构造时将字符串包装为 `TableExpression`）

### 4.8 `format_insert_statement` — 数据源

- **isinstance**: `isinstance(expr.source, DefaultValuesSource/ValuesSource/SelectSource)`
- **改造**: 保留。这三种 Source 类型是 **不同的表达式类型**，各自的 `to_sql()` 逻辑完全不同。isinstance 分发是合理的（多态分发），不是在判断"同一字段的多种原始类型"

### 4.9 `format_update_statement` / `format_delete_statement` — FROM/USING

- **isinstance**: `isinstance(source, str)` / `isinstance(source, QueryExpression)` / `isinstance(source, BaseExpression)`
- **改造**: FROM/USING 的 source 列表应统一为表达式对象（构造时将字符串包装为 `TableExpression`）

### 4.10 `format_function_call` — COUNT(*)

- **isinstance**: `isinstance(expr, aggregates.AggregateFunctionCall)` + `isinstance(expr.args[0], operators.RawSQLExpression)` + `isinstance(expr.args[0], core.WildcardExpression)`
- **改造**: 保留对 `AggregateFunctionCall` 的判断（这是多态分发）。但 COUNT(*) 的特殊化应由 `WildcardExpression` 的 `to_sql()` 自然产生 `*`，不需要在 format_function_call 中特殊判断。确认 `WildcardExpression.to_sql()` 返回 `("*", ())` 即可

### 4.11 `format_function_call` — FILTER 子句协议探测

- **isinstance**: `isinstance(self, FilterClauseSupport) and isinstance(self, FilterClauseMixin)`
- **改造**: 保留。这是 dialect 的能力探测，判断当前 dialect 是否支持 FILTER 子句

### 4.12 `format_cte_expression`

- **isinstance**: `isinstance(query, BaseExpression)` / `isinstance(query, tuple)` / `isinstance(params_input, list)`
- **改造**: CTE 的 query 应统一为表达式对象（构造时将 tuple/string 包装为表达式）

### 4.13 `format_window_function_call`

- **isinstance**: `isinstance(arg, bases.BaseExpression)` / `isinstance(call.window_spec, str)`
- **改造**:
  - 参数应统一为表达式对象（构造时将字面值包装为 `Literal`）
  - `window_spec` 应统一为表达式对象（字符串包装为 `WindowSpecification` 或 `NamedWindowReference`）

### 4.14 `format_window_specification`

- **isinstance**: `isinstance(part, bases.BaseExpression)`
- **改造**: PARTITION BY 项应统一为表达式对象

### 4.15 `format_join_clause`

- **isinstance**: `isinstance(join_expr.left_table, (QueryExpression, JoinClause))` / 同 right_table
- **改造**: 保留。JOIN 的左右表可以是表名（`TableExpression`）、子查询或嵌套 JOIN，这是合法的多态

### 4.16 `format_on_conflict_clause`

- **isinstance**: `isinstance(target, str)` / `isinstance(target, ToSQLProtocol)`
- **改造**: ON CONFLICT 目标应统一为表达式对象（构造时将字符串包装为 `ColumnExpression`）

### 4.17 `format_ilike_expression`

- **isinstance**: `isinstance(column, str)` / `isinstance(column, ToSQLProtocol)`
- **改造**: 列应统一为表达式对象

### 4.18 `format_json_*`

- **isinstance**: `isinstance(expr.column, bases.BaseExpression)`
- **改造**: JSON 表达式的 `column` 字段应统一为表达式对象

### 4.19 `format_default_constraint`

- **isinstance**: `isinstance(constraint.default_value, BaseExpression/Literal/str)`
- **改造**: DEFAULT 值在 DDL 上下文中必须内联。保留 isinstance 但简化：统一用 `inline_sql_literal` 渲染，让 `Literal` 的 `inline_literals=True` 模式自然产生内联值

### 4.20 `format_foreign_key_constraint`

- **isinstance**: `isinstance(t_const, ForeignKeyConstraint)`
- **改造**: 保留。`ForeignKeyConstraint` 是 `TableConstraint` 的子类，需要额外属性

### 4.21 `format_alter_column_action`

- **isinstance**: `isinstance(action.new_value, str/ToSQLProtocol/Literal)`
- **改造**: `new_value` 应统一为表达式对象

### 4.22 `format_for_update_clause`

- **isinstance**: `isinstance(col, str)` / `isinstance(col, ToSQLProtocol)`
- **改造**: FOR UPDATE OF 列应统一为表达式对象

### 4.23 `format_create_index_statement`

- **isinstance**: `isinstance(col, ToSQLProtocol)`
- **改造**: 索引列应统一为表达式对象

### 4.24 `format_add_table_constraint_action`

- **isinstance**: `isinstance(action.constraint, ForeignKeyConstraint)`
- **改造**: 保留（同 4.20）

## 五、优先级排序

### P0 — 返回类型修复（阻塞性）
1. `format_pk_constraint` → `Tuple[str, tuple]`
2. `format_unique_constraint` → `Tuple[str, tuple]`

### P1 — 参数签名统一
3. `format_storage_options` → 接收 expr
4. `format_alias` → 返回类型统一
5. `format_limit_offset` → 返回类型统一

### P2 — 类型提示补齐
6. `expression.py` 10 个方法
7. `predicate.py` 10 个方法
8. `dql.py` 4 个方法
9. `ddl_table.py` 1 个方法
10. `join.py` 1 个方法

### P3 — isinstance 消除
11. 各方法按上述方案逐一改造

### P4 — 返回类型大小写统一
12. `Tuple[str, Tuple]` → `Tuple[str, tuple]` 全局替换
