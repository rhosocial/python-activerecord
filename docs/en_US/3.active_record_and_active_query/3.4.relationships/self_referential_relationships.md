# Self-referential Relationships

Self-referential relationships are associations where a model is related to itself. In rhosocial ActiveRecord, self-referential relationships allow you to model hierarchical structures, networks, and other complex relationships within a single model.

## Overview

Self-referential relationships are useful for modeling various types of data structures, including:

- Hierarchical structures (e.g., employees and managers, categories and subcategories)
- Network structures (e.g., friends in a social network, followers and following)
- Tree structures (e.g., organizational charts, file systems)
- Recursive structures (e.g., bill of materials, nested comments)

In rhosocial ActiveRecord, self-referential relationships are implemented using the same relationship descriptors as other relationships (`HasOne`, `HasMany`, `BelongsTo`), but with the model referencing itself.

## Types of Self-referential Relationships

### One-to-Many Self-referential Relationship

A one-to-many self-referential relationship is common for hierarchical structures where each record can have multiple children but only one parent.

#### Example: Categories and Subcategories

```python
from typing import ClassVar, Optional, List
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.field import IntegerPKMixin
from rhosocial.activerecord.relation import HasMany, BelongsTo

class Category(IntegerPKMixin, ActiveRecord):
    __table_name__ = "categories"
    
    id: Optional[int] = None
    name: str
    parent_id: Optional[int] = None  # Foreign key to parent category
    
    # Define relationship with parent category
    parent: ClassVar[BelongsTo['Category']] = BelongsTo(
        foreign_key='parent_id',
        inverse_of='children'
    )
    
    # Define relationship with child categories
    children: ClassVar[HasMany['Category']] = HasMany(
        foreign_key='parent_id',
        inverse_of='parent'
    )
    
    # Helper method to get all ancestors
    def ancestors(self):
        ancestors = []
        current = self.parent()
        while current:
            ancestors.append(current)
            current = current.parent()
        return ancestors
    
    # Helper method to get all descendants
    def descendants(self):
        result = []
        for child in self.children():
            result.append(child)
            result.extend(child.descendants())
        return result
```

### Many-to-Many Self-referential Relationship

A many-to-many self-referential relationship is useful for modeling networks where each record can be related to multiple other records of the same type.

#### Example: Friends in a Social Network

```python
from typing import ClassVar, Optional, List
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.field import IntegerPKMixin
from rhosocial.activerecord.relation import HasMany, BelongsTo

class User(IntegerPKMixin, ActiveRecord):
    __table_name__ = "users"
    
    id: Optional[int] = None
    username: str
    email: str
    
    # Define relationship with Friendship model for friendships initiated by this user
    friendships_initiated: ClassVar[HasMany['Friendship']] = HasMany(
        foreign_key='user_id',
        inverse_of='user'
    )
    
    # Define relationship with Friendship model for friendships received by this user
    friendships_received: ClassVar[HasMany['Friendship']] = HasMany(
        foreign_key='friend_id',
        inverse_of='friend'
    )
    
    # Helper method to get all friends
    def friends(self):
        # Get friends where this user initiated the friendship
        initiated = self.friendships_initiated()
        friend_ids_initiated = [friendship.friend_id for friendship in initiated]
        
        # Get friends where this user received the friendship
        received = self.friendships_received()
        friend_ids_received = [friendship.user_id for friendship in received]
        
        # Combine all friend IDs
        all_friend_ids = friend_ids_initiated + friend_ids_received
        
        # Return all friends
        return User.find_all().where(id__in=all_friend_ids).all()

class Friendship(IntegerPKMixin, ActiveRecord):
    __table_name__ = "friendships"
    
    id: Optional[int] = None
    user_id: int      # User who initiated the friendship
    friend_id: int    # User who received the friendship request
    status: str       # e.g., 'pending', 'accepted', 'rejected'
    created_at: datetime
    
    # Define relationships with User model
    user: ClassVar[BelongsTo['User']] = BelongsTo(
        foreign_key='user_id',
        inverse_of='friendships_initiated'
    )
    
    friend: ClassVar[BelongsTo['User']] = BelongsTo(
        foreign_key='friend_id',
        inverse_of='friendships_received'
    )
```

## Using Self-referential Relationships

### Creating Hierarchical Structures

```python
# Create parent category
electronics = Category(name="Electronics")
electronics.save()

# Create child categories
phones = Category(name="Phones", parent_id=electronics.id)
phones.save()

laptops = Category(name="Laptops", parent_id=electronics.id)
laptops.save()

# Create a subcategory
smartphones = Category(name="Smartphones", parent_id=phones.id)
smartphones.save()
```

### Navigating Hierarchical Structures

```python
# Get a category
smartphones = Category.find_by(name="Smartphones")

# Get the parent category
parent = smartphones.parent()
print(f"Parent category: {parent.name}")  # Output: Parent category: Phones

# Get all ancestors
ancestors = smartphones.ancestors()
for ancestor in ancestors:
    print(f"Ancestor: {ancestor.name}")  # Output: Ancestor: Phones, Ancestor: Electronics

# Get all children of a category
electronics = Category.find_by(name="Electronics")
children = electronics.children()
for child in children:
    print(f"Child category: {child.name}")  # Output: Child category: Phones, Child category: Laptops

# Get all descendants
descendants = electronics.descendants()
for descendant in descendants:
    print(f"Descendant: {descendant.name}")  # Output: Descendant: Phones, Descendant: Laptops, Descendant: Smartphones
```

### Managing Friend Relationships

```python
# Create users
alice = User(username="alice", email="alice@example.com")
alice.save()

bob = User(username="bob", email="bob@example.com")
bob.save()

charlie = User(username="charlie", email="charlie@example.com")
charlie.save()

# Create friendships
alice_bob_friendship = Friendship(
    user_id=alice.id,
    friend_id=bob.id,
    status="accepted",
    created_at=datetime.now()
)
alice_bob_friendship.save()

alice_charlie_friendship = Friendship(
    user_id=alice.id,
    friend_id=charlie.id,
    status="accepted",
    created_at=datetime.now()
)
alice_charlie_friendship.save()

# Get all friends of a user
alice = User.find_by(username="alice")
friends = alice.friends()

for friend in friends:
    print(f"Friend: {friend.username}")  # Output: Friend: bob, Friend: charlie
```

## Advanced Techniques

### Recursive Queries

For complex hierarchical structures, you might need to perform recursive queries to efficiently retrieve all ancestors or descendants. This can be done using recursive Common Table Expressions (CTEs) in SQL, which you can implement using raw SQL queries:

```python
# Get all descendants of a category using a recursive CTE
def get_all_descendants(category_id):
    sql = """
    WITH RECURSIVE descendants AS (
        SELECT id, name, parent_id
        FROM categories
        WHERE id = %s
        UNION ALL
        SELECT c.id, c.name, c.parent_id
        FROM categories c
        JOIN descendants d ON c.parent_id = d.id
    )
    SELECT * FROM descendants WHERE id != %s;
    """
    
    # Execute the raw SQL query
    return Category.find_by_sql(sql, [category_id, category_id])

# Usage
electronics = Category.find_by(name="Electronics")
descendants = get_all_descendants(electronics.id)
```

### Preventing Circular References

When working with hierarchical structures, it's important to prevent circular references (e.g., a category being its own ancestor). You can implement validation logic to check for this:

```python
class Category(IntegerPKMixin, ActiveRecord):
    # ... existing code ...
    
    def validate(self):
        super().validate()
        
        # Check for circular references
        if self.parent_id and self.id:
            # Check if this category is being set as a descendant of itself
            current = Category.find_by(id=self.parent_id)
            while current:
                if current.id == self.id:
                    self.add_error("parent_id", "Cannot set a category as a descendant of itself")
                    break
                current = current.parent()
```

## Best Practices

1. **Use clear naming conventions**: When defining self-referential relationships, use clear and descriptive names for the relationships (e.g., `parent`, `children`, `friends`).

2. **Implement helper methods**: Add helper methods to your models to make working with self-referential relationships more intuitive, as shown in the examples above.

3. **Be careful with deep hierarchies**: Deep hierarchical structures can lead to performance issues. Consider using techniques like materialized paths or nested sets for very deep hierarchies.

4. **Prevent circular references**: Implement validation logic to prevent circular references in hierarchical structures.

5. **Use eager loading**: When retrieving multiple records with their related records, use eager loading to avoid N+1 query problems.

## Conclusion

Self-referential relationships in rhosocial ActiveRecord provide a powerful way to model complex structures within a single model. By using the same relationship descriptors as other relationships but with the model referencing itself, you can create hierarchical structures, networks, and other complex relationships. With the addition of helper methods and validation logic, you can create intuitive and robust models for your application.