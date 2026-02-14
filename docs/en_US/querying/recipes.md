# Query Recipes

This document provides query solutions for common business scenarios, demonstrating rhosocial-activerecord best practices.

> 💡 **Core Principles:**
> 1. **Use the expression system**: rhosocial-activerecord's expression system covers the complete SQL standard, eliminating the need for handwritten SQL
> 2. **Custom query classes**: For frequently used queries, inherit from `ActiveQuery` to create dedicated query classes, specified in the model via `__query_class__`
> 3. **CTEQuery for complex queries**: When you need CTEs (Common Table Expressions), use the `CTEQuery` class to build queries independently

---

## Best Practice: Custom Query Classes

When a query pattern is frequently used in your application, the best approach is to create a custom query class:

```python
from typing import ClassVar, Optional, List
from datetime import datetime, timedelta
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.query import ActiveQuery
from rhosocial.activerecord.base import FieldProxy
from pydantic import Field

class UserQuery(ActiveQuery):
    """Custom query class for User model, encapsulating common query logic."""
    
    def recent(self, days: int = 7) -> 'UserQuery':
        """Query users registered in the last N days."""
        cutoff_date = datetime.now() - timedelta(days=days)
        return self.where(self.model_class.c.created_at >= cutoff_date)
    
    def active(self) -> 'UserQuery':
        """Query active users (verified email and not banned)."""
        return self.where(
            (self.model_class.c.email_verified == True) & 
            (self.model_class.c.is_banned == False)
        )


class User(ActiveRecord):
    """User model with custom query class."""
    
    # Specify custom query class
    __query_class__ = UserQuery
    
    c: ClassVar[FieldProxy] = FieldProxy()
    
    id: Optional[int] = None
    username: str
    email: str
    email_verified: bool = False
    is_banned: bool = False
    created_at: datetime
    
    @classmethod
    def table_name(cls) -> str:
        return 'users'


# Use custom query methods
recent_active_users = User.query().recent(days=7).active().all()
```

**Key Points:**
- Inherit from `ActiveQuery` to create custom query classes
- Set `__query_class__ = YourCustomQuery` in the model
- Access current model via `self.model_class`, fields via `self.model_class.c`
- Return `self` to support method chaining

> 💡 **AI Prompt:** "How do I create custom query classes for rhosocial-activerecord models?"

---

## Recipe 1: Users Registered in the Last 7 Days

**Business Need**: Get the list of users who registered in the past week.

### Method 1: Using Expressions (Simple Scenarios)

```python
from datetime import datetime, timedelta
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.base import FieldProxy
from typing import ClassVar, Optional
from pydantic import Field

class User(ActiveRecord):
    c: ClassVar[FieldProxy] = FieldProxy()
    
    id: Optional[int] = None
    username: str
    email: str
    created_at: datetime
    
    @classmethod
    def table_name(cls) -> str:
        return 'users'


# Query users registered in last 7 days
seven_days_ago = datetime.now() - timedelta(days=7)

recent_users = User.query() \
    .where(User.c.created_at >= seven_days_ago) \
    .order_by((User.c.created_at, "DESC")) \
    .all()

print(f"Users registered in last 7 days: {len(recent_users)}")
for user in recent_users:
    print(f"- {user.username} ({user.created_at.strftime('%Y-%m-%d')})")
```

### Method 2: Using Custom Query Class (Recommended)

```python
class UserQuery(ActiveQuery):
    """User-specific query class."""
    
    def recent(self, days: int = 7) -> 'UserQuery':
        """Query users registered in the last N days."""
        cutoff = datetime.now() - timedelta(days=days)
        return self.where(self.model_class.c.created_at >= cutoff)
    
    def newest_first(self) -> 'UserQuery':
        """Order by registration time descending."""
        return self.order_by((self.model_class.c.created_at, "DESC"))


class User(ActiveRecord):
    __query_class__ = UserQuery
    # ... field definitions


# Usage
recent_users = User.query().recent(days=7).newest_first().all()
```

> 💡 **AI Prompt:** "How do I use expressions for date range queries in rhosocial-activerecord?"

---

## Recipe 2: Top 10 Customers by Order Count

**Business Need**: Count orders per customer and find the 10 most active customers.

Using **CTEQuery** for complex aggregation:

```python
from typing import ClassVar, Optional
from datetime import datetime
from pydantic import Field
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.base import FieldProxy
from rhosocial.activerecord.query import CTEQuery

class User(ActiveRecord):
    c: ClassVar[FieldProxy] = FieldProxy()
    
    id: Optional[int] = None
    username: str
    email: str
    
    @classmethod
    def table_name(cls) -> str:
        return 'users'

class Order(ActiveRecord):
    c: ClassVar[FieldProxy] = FieldProxy()
    
    id: Optional[int] = None
    user_id: int
    total_amount: float
    created_at: datetime
    
    @classmethod
    def table_name(cls) -> str:
        return 'orders'


# Use CTEQuery for Top 10 customer statistics
# Step 1: Get backend
backend = Order.backend()

# Step 2: Create CTEQuery instance
cte_query = CTEQuery(backend)

# Step 3: Create subquery (count orders per user)
order_stats = Order.query() \
    .select('user_id') \
    .group_by('user_id')

# Step 4: Add CTE
cte_query.with_cte('order_stats', order_stats)

# Step 5: Build main query and execute
# Note: CTEQuery needs from_cte() to specify which CTE to read from
top_customers = cte_query \
    .from_cte('order_stats') \
    .select('user_id') \
    .aggregate()  # Returns list of dictionaries

print("Customer order statistics:")
for row in top_customers:
    print(f"- User {row['user_id']}")
```

**Key Points:**
- `CTEQuery(backend)` creates an instance, requires backend parameter
- `.with_cte('name', query)` adds a CTE, query can be an ActiveQuery
- `.from_cte('name')` specifies which CTE to read data from
- `.aggregate()` executes the query and returns a list of dictionaries

> 💡 **AI Prompt:** "How do I implement GROUP BY aggregation queries using CTEQuery?"

---

## Recipe 3: Users with More Than 5 Pending Tasks

**Business Need**: Find users with too many backlogged tasks for reminders or performance analysis.

```python
from typing import ClassVar, Optional
from pydantic import Field
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.base import FieldProxy
from rhosocial.activerecord.query import CTEQuery

class User(ActiveRecord):
    c: ClassVar[FieldProxy] = FieldProxy()
    
    id: Optional[int] = None
    username: str
    email: str
    
    @classmethod
    def table_name(cls) -> str:
        return 'users'

class Task(ActiveRecord):
    c: ClassVar[FieldProxy] = FieldProxy()
    
    id: Optional[int] = None
    user_id: int
    title: str
    status: str
    
    @classmethod
    def table_name(cls) -> str:
        return 'tasks'


# Query users with more than 5 pending tasks
backend = Task.backend()

# Create CTEQuery
cte_query = CTEQuery(backend)

# Create subquery: count pending tasks per user
pending_counts = Task.query() \
    .select('user_id') \
    .where("status = 'pending'") \
    .group_by('user_id')

# Add CTE
cte_query.with_cte('pending_counts', pending_counts)

# Execute main query
overloaded_users = cte_query \
    .from_cte('pending_counts') \
    .select('user_id') \
    .aggregate()

print("Pending task statistics:")
for row in overloaded_users:
    print(f"⚠️ User {row['user_id']}")
```

**Key Points:**
- Use `.where()` in subquery to filter pending tasks
- Use `.group_by()` to group by user
- Main query reads statistics from CTE

> 💡 **AI Prompt:** "How do I filter and group data in rhosocial-activerecord?"

---

## Recipe 4: Monthly Order Statistics

**Business Need**: Generate monthly sales reports, counting order volume per month.

Using **CTEQuery** with date functions:

```python
from typing import ClassVar, Optional
from datetime import datetime
from pydantic import Field
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.base import FieldProxy
from rhosocial.activerecord.query import CTEQuery

class Order(ActiveRecord):
    c: ClassVar[FieldProxy] = FieldProxy()
    
    id: Optional[int] = None
    order_no: str
    total_amount: float
    created_at: datetime
    
    @classmethod
    def table_name(cls) -> str:
        return 'orders'


# Group orders by month
backend = Order.backend()

# Create CTEQuery
cte_query = CTEQuery(backend)

# Create subquery: group by month
# Note: Date functions are database-specific, here we use string form where condition
monthly_stats = Order.query() \
    .select('id', 'total_amount', 'created_at') \
    .where("created_at >= date('now', '-12 months')") \
    .group_by("strftime('%Y-%m', created_at)")

# Add CTE
cte_query.with_cte('monthly_stats', monthly_stats)

# Execute query
result = cte_query \
    .from_cte('monthly_stats') \
    .select('id', 'total_amount', 'created_at') \
    .aggregate()

print("Monthly order statistics (last 12 months):")
for row in result:
    print(f"Order {row['id']}: ${row['total_amount']} ({row['created_at']})")
```

**Date functions for different databases:**

```python
# Choose date function dynamically based on backend type
from rhosocial.activerecord.backend.impl.sqlite import SQLiteDialect
from rhosocial.activerecord.backend.impl.postgres import PostgresDialect

backend = Order.backend()

if isinstance(backend.dialect, SQLiteDialect):
    # SQLite: strftime('%Y-%m', created_at)
    date_expr = "strftime('%Y-%m', created_at)"
elif isinstance(backend.dialect, PostgresDialect):
    # PostgreSQL: to_char(created_at, 'YYYY-MM')
    date_expr = "to_char(created_at, 'YYYY-MM')"
else:  # MySQL
    # MySQL: DATE_FORMAT(created_at, '%Y-%m')
    date_expr = "DATE_FORMAT(created_at, '%Y-%m')"
```

**Key Points:**
- Date functions are database-specific and need to be chosen based on your database
- Can use string form date comparisons in WHERE clauses
- GROUP BY can use string form expressions

> 💡 **AI Prompt:** "How do I use date functions from different databases in rhosocial-activerecord?"

---

## Recipe 5: Find Duplicate Emails

**Business Need**: During data cleaning, discovered multiple users with the same email address, need to find these duplicate records.

```python
from typing import ClassVar, Optional
from datetime import datetime
from pydantic import Field
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.base import FieldProxy
from rhosocial.activerecord.query import CTEQuery

class User(ActiveRecord):
    c: ClassVar[FieldProxy] = FieldProxy()
    
    id: Optional[int] = None
    username: str
    email: str
    created_at: Optional[datetime] = None
    
    @classmethod
    def table_name(cls) -> str:
        return 'users'


# Find duplicate emails
backend = User.backend()

# Create CTEQuery
cte_query = CTEQuery(backend)

# Create subquery: group by email
duplicate_query = User.query() \
    .select('email', 'id', 'username') \
    .group_by('email')

# Add CTE
cte_query.with_cte('duplicate_emails', duplicate_query)

# Execute main query
result = cte_query \
    .from_cte('duplicate_emails') \
    .select('email', 'id', 'username') \
    .aggregate()

print("User email list:")
for row in result:
    print(f"📧 {row['email']}: {row['username']} (ID: {row['id']})")
```

**Cleaning duplicate data:**

```python
# Keep earliest registered account, delete other duplicates
# Note: This is example logic, actual deletion should be done with caution

def deduplicate_emails():
    backend = User.backend()
    
    # Find earliest ID in each group
    sql = """
    SELECT MIN(id) as min_id
    FROM users
    GROUP BY email
    """
    
    result = backend.execute(sql, options=ExecutionOptions(stmt_type=StatementType.SELECT))
    ids_to_keep = [row['min_id'] for row in result]
    
    # Delete records not in keep list
    if ids_to_keep:
        placeholders = ','.join(['?' for _ in ids_to_keep])
        delete_sql = f"DELETE FROM users WHERE id NOT IN ({placeholders})"
        backend.execute(delete_sql, tuple(ids_to_keep), options=ExecutionOptions(stmt_type=StatementType.DELETE))
        print("Duplicate email accounts cleaned up")
```

> 💡 **AI Prompt:** "How do I find and clean up duplicate data with rhosocial-activerecord?"

---

## Recipe 6: Pagination Implementation

**Business Need**: Implement classic pagination with support for jumping to specific page numbers.

### Method 1: Implement in Custom Query Class

```python
from typing import ClassVar, Optional, List, Tuple, Dict, Any
from pydantic import Field
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.query import ActiveQuery
from rhosocial.activerecord.base import FieldProxy

class ProductQuery(ActiveQuery):
    """Product-specific query class with pagination logic."""
    
    def by_category(self, category: str) -> 'ProductQuery':
        """Filter by category."""
        return self.where(self.model_class.c.category == category)
    
    def paginate(
        self, 
        page: int = 1, 
        per_page: int = 20
    ) -> Tuple[List, int]:
        """
        Execute paginated query.
        
        Returns:
            (Current page data, Total record count)
        """
        # Query total count
        total = self.count()
        
        # Calculate offset
        offset = (page - 1) * per_page
        
        # Execute paginated query
        items = self \
            .order_by((self.model_class.c.created_at, "DESC")) \
            .limit(per_page) \
            .offset(offset) \
            .all()
        
        return items, total
    
    def paginated_response(
        self, 
        page: int = 1, 
        per_page: int = 20
    ) -> Dict[str, Any]:
        """Return standard paginated response format (suitable for APIs)."""
        items, total = self.paginate(page, per_page)
        total_pages = (total + per_page - 1) // per_page
        
        return {
            "data": [item.model_dump() for item in items],
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total,
                "total_pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1
            }
        }


class Product(ActiveRecord):
    __query_class__ = ProductQuery
    
    c: ClassVar[FieldProxy] = FieldProxy()
    
    id: Optional[int] = None
    name: str
    price: float
    category: str
    created_at: Optional[datetime] = None
    
    @classmethod
    def table_name(cls) -> str:
        return 'products'


# Usage example
page = 1
products, total = Product.query().by_category("electronics").paginate(page=page, per_page=10)

# API response format
response = Product.query().by_category("electronics").paginated_response(page=1, per_page=10)
```

### Method 2: Cursor Pagination (Large Dataset Optimization)

```python
class ProductQuery(ActiveQuery):
    """Query class supporting cursor pagination."""
    
    def cursor_paginate(
        self,
        last_id: Optional[int] = None,
        per_page: int = 20
    ) -> Tuple[List, Optional[int]]:
        """
        Cursor pagination (suitable for large datasets).
        
        Args:
            last_id: ID of the last product from the previous page
            per_page: Number of items per page
        
        Returns:
            (List of products, Next page cursor)
        """
        query = self.order_by((self.model_class.c.id, "ASC"))
        
        if last_id:
            query = query.where(self.model_class.c.id > last_id)
        
        # Query one extra to determine if there's a next page
        products = query.limit(per_page + 1).all()
        
        if len(products) > per_page:
            next_cursor = products[-1].id
            products = products[:-1]  # Remove the extra queried item
        else:
            next_cursor = None
        
        return products, next_cursor


# Use cursor pagination
first_page, next_cursor = Product.query().cursor_paginate(per_page=10)
if next_cursor:
    second_page, next_cursor = Product.query().cursor_paginate(last_id=next_cursor, per_page=10)
```

**Comparison of Two Pagination Methods:**

| Feature | OFFSET Pagination | Cursor Pagination |
|---------|-------------------|-------------------|
| Suitable for | Small datasets, need to jump pages | Large datasets, only need prev/next |
| Performance | Slows down with large OFFSET | Always efficient |
| Data Consistency | Data may change during pagination | Better data stability |
| Implementation Complexity | Simple | Slightly more complex |

> 💡 **AI Prompt:** "What is the difference between OFFSET pagination and cursor pagination in rhosocial-activerecord, and how do I choose?"

---

## More Query Patterns

### Fuzzy Search (LIKE)

```python
# Users with username containing "admin"
admins = User.query() \
    .where(User.c.username.like("%admin%")) \
    .all()

# Emails starting with "test"
test_users = User.query() \
    .where(User.c.email.like("test%")) \
    .all()
```

### IN Query

```python
user_ids = [1, 2, 3, 4, 5]
users = User.query() \
    .where(User.c.id.in_(user_ids)) \
    .all()
```

### Range Query (BETWEEN)

```python
from datetime import date

orders = Order.query() \
    .where(Order.c.created_at.between(date(2024, 1, 1), date(2024, 12, 31))) \
    .all()
```

### Complex Conditions (AND/OR)

```python
from rhosocial.activerecord.backend.expression import and_, or_

# VIP or registered in last 30 days
vip_or_recent = User.query() \
    .where(or_(
        User.c.is_vip == True,
        User.c.created_at >= thirty_days_ago
    )) \
    .all()

# VIP AND registered in last 30 days
vip_and_recent = User.query() \
    .where(and_(
        User.c.is_vip == True,
        User.c.created_at >= thirty_days_ago
    )) \
    .all()
```

> 💡 **AI Prompt:** "Usage of AND and OR condition combinations in rhosocial-activerecord"

---

## CTEQuery vs ActiveQuery Comparison

| Feature | ActiveQuery | CTEQuery |
|---------|------------|---------|
| Use Case | Simple to medium complexity queries | Complex queries requiring CTE/WITH clauses |
| Creation | `Model.query()` | `CTEQuery(backend)` |
| Associate CTE | Not supported | `.with_cte(name, query)` |
| Specify Data Source | Automatically uses model table | `.from_cte(name)` |
| Return Results | List of model instances | List of dictionaries (`.aggregate()`) |
| Requires backend | No (obtained from model) | Yes (must be passed) |

---

## See Also

- [ActiveQuery](active_query.md) — Complete query API documentation
- [CTEQuery](cte_query.md) — Common Table Expressions detailed documentation
- [Cheatsheet](cheatsheet.md) — Quick reference for common query patterns
