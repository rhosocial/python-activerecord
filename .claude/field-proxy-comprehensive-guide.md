# ActiveRecord FieldProxy Complete Implementation Guide

## 1. Overview

FieldProxy is a powerful feature that lets users access model fields via the
`Model.proxy_name.field_name` syntax and generate corresponding SQL expression objects. It
supports:

- Plain field access
- `UseColumn`-annotated fields
- Dynamic table aliases
- Preset table aliases
- Column aliases
- Self-join queries

## 2. Implementation

### 2.1 Core Implementation

FieldProxy is implemented through Python's descriptor protocol:

```python
# The alias capability comes from AliasableMixin (backend/expression/mixins.py)
# Column and other expression classes inherit this mixin to gain as_() (NOT via monkey-patch):

class FieldProxy:
    def __get__(self, instance, owner):
        ...
        # returns a dynamic field accessor

        def __getattr__(self, field_name):
            ...
            self._table_alias = static_table_alias  # possibly set at initialization

            # Use Pydantic's model_fields to get field information
            # Use ColumnNameMixin methods to get the correct column name
            # This correctly handles the UseColumn annotation: if the field has UseColumn,
            # return the custom column name; otherwise return the field name

            # Use the table alias (if set) as the table name

            # Create the column expression object using the real dialect
```

### 2.2 Usage

```python
class User(ActiveRecord):
    __table_name__ = "users"
    __primary_key__: ClassVar[str] = "id"  # explicitly specify the primary key column name

    # Plain fields - field name and column name are the same

    # UseColumn-annotated fields - field name and column name differ

    # Plain field proxy - uses the default table name

    # Field proxy with preset table alias - for self-join queries
    u1: ClassVar[FieldProxy] = FieldProxy(table_alias='u1')  # first table alias
    u2: ClassVar[FieldProxy] = FieldProxy(table_alias='u2')  # second table alias
    referrer: ClassVar[FieldProxy] = FieldProxy(table_alias='r')  # referrer table alias
    referred: ClassVar[FieldProxy] = FieldProxy(table_alias='ref')  # referred table alias
```

## 3. Features

### 3.1 Basic Field Access

```python
# Plain field access
User.query().where(User.c.age > 25)
User.query().where((User.fields.status == 'active') & (User.fields.age > 18))
User.query().select(User.cols.id, User.cols.name, User.cols.email)
```

### 3.2 UseColumn-Annotated Field Access

```python
# UseColumn-annotated field access
User.query().where(User.c.user_age > 30)  # maps to the 'age' column
```

### 3.3 Column Aliases

```python
# Column aliases
User.query().select(User.c.name.as_('user_name'))
```

### 3.4 Dynamic Table Aliases (Self-Join Queries)

```python
# Dynamic table aliases (self-join queries)
user1 = User.c.with_table_alias('u1')
user2 = User.c.with_table_alias('u2')
User.query().where((user1.age == user2.age) & (user1.id != user2.id))
```

### 3.5 Preset Table Aliases (Self-Join Queries)

```python
# Preset table aliases (self-join queries)
User.query().where((User.u1.age == User.u2.age) & (User.u1.id != User.u2.id))
```

### 3.6 Mixed Usage

```python
# Mixed usage
User.query().select(
    User.u1.name.as_('user1_name'),
    User.u2.name.as_('user2_name')
).where(User.u1.age > User.u2.age)
```

## 4. Advanced Usage

### 4.1 Advanced Query Building

```python
# Complex condition building
User.query().where(
    (User.c.age > 18) &
    (User.c.status == 'active') &
    (User.c.created_at > datetime.now() - timedelta(days=30))
)

# Aggregate function support
User.query().select(
    User.c.department,
    User.c.salary.avg().as_('avg_salary'),
    User.c.id.count().as_('employee_count')
).group_by(User.c.department)
```

### 4.2 Relationship Query Enhancement

```python
# Joined queries
User.query().join(Order).where(Order.c.total > User.c.salary)

# Nested relationship queries
User.query().join(Order).join(Product).where(
    (User.c.age > 25) &
    (Product.c.category == 'electronics')
)
```

### 4.3 Data Validation and Type Safety

```python
# Since field proxies are directly tied to model fields, the IDE provides full type hints
# Wrong field names are caught at development time
User.query().where(User.c.non_existent_field == 'value')  # IDE flags an error
```

### 4.4 Dynamic Query Building

```python
# Conditional query building
def build_user_query(filters):
    query = User.query()
    if 'min_age' in filters:
        query = query.where(User.c.age >= filters['min_age'])
    if 'status' in filters:
        query = query.where(User.c.status == filters['status'])
    return query

# Dynamic field selection
def select_fields(model, field_names):
    fields = [getattr(model.c, name) for name in field_names]
    return model.query().select(*fields)
```

### 4.5 Advanced SQL Feature Support

```python
# Window functions
User.query().select(
    User.c.name,
    User.c.salary.rank().over(
        partition_by=[User.c.department],
        order_by=[User.c.salary.desc()]
    ).as_('salary_rank')
)

# CTE (Common Table Expression)
with_recursive_users = User.query().where(User.c.manager_id.is_null()).union_all(
    User.query().join(with_recursive_users).where(
        User.c.manager_id == with_recursive_users.c.id
    )
)
```

### 4.6 Data Transformation and Computation

```python
# Field computation
User.query().select(
    User.c.name,
    (User.c.salary * 12).as_('annual_salary'),
    (User.c.age > 18).as_('is_adult')
)

# String operations
User.query().select(
    User.c.name.upper().as_('uppercase_name'),
    User.c.email.contains('@gmail.com').as_('is_gmail_user')
)
```

## 5. Security and Performance

### 5.1 SQL Injection Protection

```python
# FieldProxy ensures all query parameters are properly parameterized
User.query().where(User.c.name == user_input)  # automatically parameterized, prevents SQL injection
```

### 5.2 Field-Level Access Control

```python
# FieldProxy can integrate with permission control
if user.has_permission('view_salary'):
    query = User.query().select(User.c.salary)
else:
    query = User.query().select(User.c.name, User.c.email)  # excludes sensitive fields
```

## 6. Summary

FieldProxy provides powerful and flexible query-building capability for the ActiveRecord
pattern. With simple syntax, users can:

- Access model fields and generate SQL expressions
- Use column and table aliases
- Build complex self-join queries
- Gain type safety and IDE support
- Implement advanced SQL features

The implementation is fully integrated into the existing activerecord architecture and is
fully compatible with the expression-dialect system, offering an intuitive, safe, and
feature-rich query-building experience.