# A Tour of Key Features

Don't let technical jargon scare you. Let's look at how `rhosocial-activerecord` helps you write better code through a real-world scenario: building a simple blog system.

## 1. Defining Your Data: What You See Is What You Get
It all starts with defining your model. In `rhosocial-activerecord`, your model **is essentially** a Pydantic model. This means you don't need to learn a new set of validation rules—just use your familiar Pydantic knowledge.

```python
from typing import ClassVar
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.base import FieldProxy
from pydantic import Field

class User(ActiveRecord):
    # Use Pydantic directly for powerful data validation
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., pattern=r"^[\w\.-]+@[\w\.-]+\.\w+$")
    age: int = Field(..., ge=18)

    # Enable Field Proxy to provide type support for subsequent queries
    c: ClassVar[FieldProxy] = FieldProxy()

# Try to create an invalid user
# user = User(username="al", email="not-an-email", age=10) 
# ^ This raises a Pydantic ValidationError immediately, without even connecting to the DB!
```

**What does this solve?**
You no longer have to worry about "garbage data" entering your database. Validation happens at the Python level and is instant.

## 2. Don't Repeat Yourself: Composing Features Like Lego
Soon you'll realize that not just `User`, but also your `Post` and `Comment` models need unique IDs, and need to track creation time (`created_at`) and update time (`updated_at`).

Do you have to repeat these fields in every class? No. We prefer **Composition over Inheritance**.

```python
from rhosocial.activerecord.field import UUIDMixin, TimestampMixin

# Get common capabilities in one line by inheriting Mixins
class Post(UUIDMixin, TimestampMixin, ActiveRecord):
    title: str
    content: str
    
    c: ClassVar[FieldProxy] = FieldProxy()

# Now Post automatically has:
# - id (UUID type, auto-generated)
# - created_at (auto-recorded creation time)
# - updated_at (auto-updated modification time)
```

**What does this solve?**
Your model code stays clean and focused on business logic, while common functionality is reused via Mixins.

## 3. Query Like You Code: Goodbye Typos
Now that we have data, we need to query it. In traditional ORMs, you often have to carefully spell out string field names. If you make a typo, you won't know until the program runs and crashes.

`rhosocial-activerecord` provides the `FieldProxy` system (the `c` attribute above), giving your query code intelligent completion just like normal Python code.

```python
# ❌ The Bad Way (Traditional)
# If you typo 'username' as 'usrname', you only find out at runtime
# User.query().where("usrname == 'alice'")

# ✅ Our Way
# IDE autocompletes .username. If you typo, the IDE flags it in red immediately.
users = User.query().where(User.c.username == "alice").all()
```

**What does this solve?**
It moves runtime errors to compile/write time, leveraging your IDE to significantly reduce silly bugs.

## 4. Safety AND Speed: Flexible Data Access
Your blog is a hit, and now you need to export a million logs for analysis.
*   Using full objects one by one is too slow because creating a million Python objects is expensive.
*   Writing raw SQL is error-prone and hard to maintain.

`rhosocial-activerecord` allows you to switch seamlessly within the same library:

```python
# Scenario A: Handling User Registration (Need Full Validation)
# Use ActiveRecord objects, enjoy full Pydantic validation and lifecycle hooks
user = User(username="bob", email="bob@example.com", age=20)
user.save()

# Scenario B: Generating Big Data Reports (Need Max Performance)
# Use aggregate() to get a list of dicts directly, skipping object creation/validation
# Speed is comparable to raw SQL. We still use User.c.active for type hints.
raw_data = User.query().where(User.c.age > 20).limit(100000).aggregate()
```

**What does this solve?**
You don't have to abandon your ORM for performance reasons, nor do you have to sacrifice critical business safety for speed.

## 5. Burden-Free Testing: Test SQL Without a DB
Finally, you're ready to deploy. You wrote some complex query logic and want to write a unit test.
Usually, this means: Install Docker -> Start MySQL -> Create Tables -> Insert Data -> Run Test -> Cleanup... What a hassle!

We can directly test "Is the generated SQL correct?":

```python
# Check the generated SQL directly, no DB connection needed
sql, params = User.query().where(User.c.username == "alice").to_sql()

# Assert the SQL is what you expect
assert "SELECT * FROM users WHERE username = ?" in sql
assert params == ("alice",)
```

**What does this solve?**
Your unit tests run instantly with no external environmental dependencies.
