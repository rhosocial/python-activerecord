# Expression System

`rhosocial-activerecord` features an independent, stateless SQL expression building layer.

## Core Components

*   **Column**: Represents a database column.
*   **Literal**: Represents a raw value (automatically parameterized to prevent injection).
*   **Function**: Represents a SQL function (e.g., `COUNT`, `UPPER`).
*   **BinaryExpression**: Represents an operation (e.g., `a == b`, `a + b`).

## ToSQL Protocol

Any object that implements the `ToSQL` protocol can be compiled into SQL.

```python
class MyCustomExpr:
    def to_sql(self, dialect, param_collector):
        return "MY_FUNCTION()"
```
