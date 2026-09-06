# {database} Specific Features

This section covers {database}-specific features that differ from other backends. rhosocial-activerecord uses a two-layer architecture for many features: a **core layer** provides common interfaces and default implementations, while each backend's **dialect layer** overrides formatting and adds backend-specific capabilities.

When you encounter a feature in this section, check whether it is a backend-specific extension or a core feature with backend-specific formatting — the documentation will indicate which layer applies.

## Contents

- [Dialect Expressions](dialect.md): Two-layer expression system — common core and {database}-specific overrides
- [Field Types](field_types.md): Core DataType hierarchy and {database}-specific type extensions
- [Indexing](indexing.md): {database}-specific index types and optimization strategies
- [EXPLAIN](explain.md): Query execution plan analysis ({database}-specific syntax)
- [Introspection](introspection.md): Database metadata queries and schema inspection
- [Partitioning](partition.md): Table partitioning ({database}-specific, optional)

## Feature Highlights

| Feature | Common Layer | {database}-Specific Layer |
|---------|-------------|---------------------------|
| Expressions | Core expression classes (Column, Literal, FunctionCall, etc.) | Dialect overrides and {database}-specific expression classes |
| Type System | Core DataType hierarchy (IntegerType, VarCharType, etc.) | {database}-specific DataType subclasses and type adapters |
| EXPLAIN | ExplainExpression interface | {database}-specific EXPLAIN syntax and result parsing |
| Introspection | Introspector interface | {database}-specific metadata queries |

## Related Topics

- [Type Adapters](../type_adapters/README.md) — type mapping and custom adapters
- [DDL Operations](../ddl/README.md) — schema management
- [Core: Expression System](https://github.com/Rhosocial/python-activerecord/tree/main/docs/en_US/backend/expression)
- [Core: Backend System](https://github.com/Rhosocial/python-activerecord/tree/main/docs/en_US/backend)
