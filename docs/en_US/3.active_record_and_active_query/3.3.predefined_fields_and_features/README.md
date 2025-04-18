# Predefined Fields and Features

rhosocial ActiveRecord provides several predefined fields and features that you can easily incorporate into your models. These features are implemented as mixins that can be added to your model classes to provide common functionality without having to reimplement it yourself.

## Overview

Predefined fields and features in rhosocial ActiveRecord include:

- Primary key configuration
- Timestamp fields for tracking creation and update times
- Soft delete mechanism for logical deletion
- Version control and optimistic locking for concurrency management
- Pessimistic locking strategies for transaction isolation
- Custom fields for extending model capabilities

These features are designed to be composable, allowing you to mix and match them according to your application's needs.

## Contents

- [Primary Key Configuration](primary_key_configuration.md)
- [Timestamp Fields](timestamp_fields.md)
- [Soft Delete Mechanism](soft_delete_mechanism.md)
- [Version Control and Optimistic Locking](version_control_and_optimistic_locking.md)
- [Pessimistic Locking Strategies](pessimistic_locking_strategies.md)
- [Custom Fields](custom_fields.md)

## Using Predefined Features

To use these predefined features, simply include the appropriate mixin in your model class definition:

```python
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.field import TimestampMixin, SoftDeleteMixin, IntegerPKMixin

class User(IntegerPKMixin, TimestampMixin, SoftDeleteMixin, ActiveRecord):
    __tablename__ = 'users'
    
    name: str
    email: str
```

In this example, the `User` model includes:
- Integer primary key support via `IntegerPKMixin`
- Automatic timestamp management via `TimestampMixin`
- Soft delete functionality via `SoftDeleteMixin`

## Mixin Order

When using multiple mixins, the order of inheritance can be important. As a general rule:

1. Place more specific mixins before more general ones
2. If two mixins modify the same method, the one listed first will take precedence
3. Always place `ActiveRecord` as the last base class

For example, if you have a custom timestamp mixin that extends the standard `TimestampMixin`, you would place it before `TimestampMixin` in the inheritance list:

```python
class CustomTimestampMixin(TimestampMixin):
    # Custom timestamp behavior
    pass

class Article(CustomTimestampMixin, TimestampMixin, ActiveRecord):
    # Article model definition
    pass
```

## Next Steps

Explore each predefined feature in detail by following the links in the Contents section above.