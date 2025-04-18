# One-to-One Relationships

One-to-one relationships represent a connection between two models where each record in the first model is associated with exactly one record in the second model, and vice versa. In rhosocial ActiveRecord, one-to-one relationships can be implemented using either `HasOne` or `BelongsTo` descriptors, depending on which model holds the foreign key.

## Types of One-to-One Relationships

There are two ways to implement one-to-one relationships in rhosocial ActiveRecord:

1. **HasOne**: Used when the related model contains the foreign key
2. **BelongsTo**: Used when the current model contains the foreign key

## HasOne Relationship

A `HasOne` relationship indicates that another model contains a foreign key referencing the current model. For example, a user has one profile:

```python
from typing import ClassVar, Optional
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.field import IntegerPKMixin
from rhosocial.activerecord.relation import HasOne

class User(IntegerPKMixin, ActiveRecord):
    __table_name__ = "users"
    
    id: Optional[int] = None
    username: str
    email: str
    
    # Define relationship with Profile model
    profile: ClassVar[HasOne['Profile']] = HasOne(
        foreign_key='user_id',  # Foreign key field in Profile model
        inverse_of='user'       # Corresponding relationship name in Profile model
    )
```

## BelongsTo Relationship

A `BelongsTo` relationship indicates that the current model contains a foreign key referencing another model. For example, a profile belongs to a user:

```python
from typing import ClassVar, Optional
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.field import IntegerPKMixin
from rhosocial.activerecord.relation import BelongsTo

class Profile(IntegerPKMixin, ActiveRecord):
    __table_name__ = "profiles"
    
    id: Optional[int] = None
    user_id: int  # Foreign key
    bio: str
    avatar_url: str
    
    # Define relationship with User model
    user: ClassVar[BelongsTo['User']] = BelongsTo(
        foreign_key='user_id',  # Foreign key field in current model
        inverse_of='profile'    # Corresponding relationship name in User model
    )
```

## Using One-to-One Relationships

### Accessing Related Records

Once you've defined a one-to-one relationship, you can access the related record as if it were a property of the model instance:

```python
# Get a user
user = User.find_one(1)

# Access the user's profile
profile = user.profile()

# Access the profile's user
profile = Profile.find_one(1)
user = profile.user()
```

### Creating Related Records

To create a related record, you first need to create the parent record, then create the related record with the appropriate foreign key:

```python
# Create a user
user = User(username="john_doe", email="john@example.com")
user.save()

# Create a profile for the user
profile = Profile(user_id=user.id, bio="Python developer", avatar_url="/avatars/john.jpg")
profile.save()
```

## Eager Loading

To optimize performance when accessing related records, you can use eager loading to load the related record in the same query:

```python
# Eager load profile when querying for a user
user = User.query().with_("profile").find_one(1)

# Now accessing profile doesn't trigger an additional query
profile = user.profile()
```

## Inverse Relationships

Inverse relationships are automatically set up when you define the `inverse_of` parameter in your relationship definition. This ensures that the relationship is properly linked in both directions.

## Cascading Operations

By default, rhosocial ActiveRecord doesn't automatically cascade delete operations to related records. If you want to delete related records when the parent record is deleted, you need to implement this behavior manually:

```python
class User(IntegerPKMixin, ActiveRecord):
    # ... other code ...
    
    def before_delete(self) -> None:
        # Delete the user's profile when the user is deleted
        profile = self.profile()
        if profile:
            profile.delete()
        super().before_delete()
```

## Best Practices

1. **Always define inverse relationships**: This helps maintain data integrity and enables bidirectional navigation.
2. **Use meaningful relationship names**: Choose names that clearly indicate the relationship's purpose.
3. **Consider using transactions**: When creating or updating related records, use transactions to ensure data consistency.
4. **Use eager loading**: When you know you'll need related records, use eager loading to reduce the number of database queries.
5. **Validate foreign keys**: Ensure that foreign keys reference valid records to maintain data integrity.

## Common Issues and Solutions

### Circular Dependencies

When defining models with mutual relationships, you might encounter circular import dependencies. To resolve this, use string-based forward references:

```python
from typing import ClassVar, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from .profile import Profile

class User(IntegerPKMixin, ActiveRecord):
    # ... other code ...
    
    profile: ClassVar[HasOne['Profile']] = HasOne(
        foreign_key='user_id',
        inverse_of='user'
    )
```

### N+1 Query Problem

The N+1 query problem occurs when you load a list of records and then access a related record for each one, resulting in N+1 database queries. To avoid this, use eager loading:

```python
# Bad: N+1 queries
users = User.find_all()
for user in users:
    profile = user.profile()  # Triggers a separate query for each user

# Good: 2 queries
users = User.query().with_("profile").find_all()
for user in users:
    profile = user.profile()  # Uses already loaded data, no additional query
```

## Conclusion

One-to-one relationships in rhosocial ActiveRecord provide a powerful way to model connections between related entities. By understanding the difference between `HasOne` and `BelongsTo` relationships and following best practices for relationship definition and usage, you can build efficient and maintainable data models for your applications.