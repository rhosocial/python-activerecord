# 表达式系统 (Expression System)

`rhosocial-activerecord` 拥有一个独立的、无状态的 SQL 表达式构建层。

## 核心组件

*   **Column**: 代表数据库列。
*   **Literal**: 代表原始值（自动参数化以防注入）。
*   **Function**: 代表 SQL 函数（如 `COUNT`, `UPPER`）。
*   **BinaryExpression**: 代表运算（如 `a == b`, `a + b`）。

## ToSQL 协议

任何实现了 `ToSQL` 协议的对象都可以被编译成 SQL。

```python
class MyCustomExpr:
    def to_sql(self, dialect, param_collector):
        return "MY_FUNCTION()"
```
