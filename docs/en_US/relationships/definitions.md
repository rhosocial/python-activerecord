# Relationship Definitions (1:1, 1:N)

`rhosocial-activerecord` uses three core descriptors: `BelongsTo`, `HasOne`, `HasMany`. These descriptors provide type-safe relationship definition methods.

> 💡 **AI Prompt Example**: "What types of relationships are available in ActiveRecord? What are the differences between them?"

## One-to-One: User and Profile

Each user has one profile page. This relationship represents a one-to-one mapping between two entities.

```python
# Import necessary modules
from typing import ClassVar
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.relation import HasOne, BelongsTo

# User class represents users in the system
class User(ActiveRecord):
    # Username field
    username: str
    
    # User has one Profile (one-to-one relationship)
    # HasOne descriptor defines the ownership relationship
    # foreign_key='user_id' refers to the foreign key column name in the Profile table
    # inverse_of='user' specifies the name of the reverse relationship, i.e., the corresponding relationship name in the Profile class
    profile: ClassVar[HasOne['Profile']] = HasOne(foreign_key='user_id', inverse_of='user')

    # Return table name
    @classmethod
    def table_name(cls) -> str:
        return 'users'

# Profile class represents user's detailed information
class Profile(ActiveRecord):
    # Foreign key column linking to User table's id column
    # This column actually exists in the database
    user_id: str
    
    # User's biography
    bio: str
    # User's avatar URL
    avatar_url: str
    
    # Profile belongs to a User (one-to-one reverse relationship)
    # BelongsTo descriptor defines the subordinate relationship
    # foreign_key='user_id' refers to the foreign key column name in this table
    # inverse_of='profile' specifies the name of the reverse relationship, i.e., the corresponding relationship name in the User class
    user: ClassVar[BelongsTo['User']] = BelongsTo(foreign_key='user_id', inverse_of='profile')

    # Return table name
    @classmethod
    def table_name(cls) -> str:
        return 'profiles'
```

> 💡 **AI Prompt Example**: "In a one-to-one relationship, which table should contain the foreign key? What's the difference between HasOne and BelongsTo?"

## One-to-Many: User and Post

A user can publish multiple posts. This relationship represents that one entity can own multiple related entities.

```python
# Import necessary modules
from typing import ClassVar
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.relation import HasMany, BelongsTo

# User class represents users in the system
class User(ActiveRecord):
    # Username field
    username: str
    # Email field
    email: str
    
    # User has many Posts (one-to-many relationship)
    # HasMany descriptor defines the one-to-many ownership relationship
    # foreign_key='user_id' refers to the foreign key column name in the Post table
    # inverse_of='author' specifies the name of the reverse relationship, i.e., the corresponding relationship name in the Post class
    posts: ClassVar[HasMany['Post']] = HasMany(foreign_key='user_id', inverse_of='author')

    # Return table name
    @classmethod
    def table_name(cls) -> str:
        return 'users'

# Post class represents articles published by users
class Post(ActiveRecord):
    # Post title
    title: str
    # Post content
    content: str
    # Foreign key column linking to User table's id column
    # This column actually exists in the database
    user_id: str
    
    # Post belongs to a User (many-to-one relationship, the post's author)
    # BelongsTo descriptor defines the subordinate relationship
    # foreign_key='user_id' refers to the foreign key column name in this table
    # inverse_of='posts' specifies the name of the reverse relationship, i.e., the corresponding relationship name in the User class
    author: ClassVar[BelongsTo['User']] = BelongsTo(foreign_key='user_id', inverse_of='posts')

    # Return table name
    @classmethod
    def table_name(cls) -> str:
        return 'posts'
```

> 💡 **AI Prompt Example**: "How is a one-to-many relationship represented in the database? How to access related data through code?"

## Relationship Usage Examples

After defining relationships, you can use them as follows:

```python
# Create user
user = User(username="John Doe", email="john@example.com")
user.save()

# Create user's profile
profile = Profile(bio="I'm John, a programmer", avatar_url="http://example.com/avatar.jpg", user_id=user.id)
profile.save()

# Create user's posts
post1 = Post(title="My First Post", content="This is the post content...", user_id=user.id)
post1.save()
post2 = Post(title="My Second Post", content="This is another post content...", user_id=user.id)
post2.save()

# Access related data
# Get user's profile (one-to-one relationship)
user_profile = user.profile()  # This will execute one database query
print(f"User bio: {user_profile.bio}")

# Get user's all posts (one-to-many relationship)
user_posts = user.posts()  # This will execute one database query
print(f"User published {len(user_posts)} posts")

# Get post's author (many-to-one relationship)
post_author = post1.author()  # This will execute one database query
print(f"Post author: {post_author.username}")
```

> 💡 **AI Prompt Example**: "Does accessing relationships execute database queries? How to avoid the N+1 query problem?"

## Important Notes

**Note**: All relationship descriptors must be declared as `ClassVar` to avoid interfering with Pydantic's field validation.

If `ClassVar` is not used, Pydantic will treat these relationships as model fields, causing:
1. Errors during data validation
2. Unnecessary relationship data included during serialization
3. Increased memory usage

```python
# ❌ Incorrect approach - without ClassVar
class User(ActiveRecord):
    # This will be treated as a field by Pydantic, causing issues
    profile = HasOne(foreign_key='user_id', inverse_of='user')

# ✅ Correct approach - with ClassVar
class User(ActiveRecord):
    # This will not be treated as a field by Pydantic
    profile: ClassVar[HasOne['Profile']] = HasOne(foreign_key='user_id', inverse_of='user')
```

> 💡 **AI Prompt Example**: "Why must relationship descriptors be declared with ClassVar? What are the consequences of not doing so?"