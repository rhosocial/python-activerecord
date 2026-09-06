# Loading Strategies

Choosing the appropriate loading strategy is crucial for application performance when using relationships. Different loading strategies are suitable for different usage scenarios.

> 💡 **AI Prompt Example**: "What are the relationship loading strategies in ActiveRecord? What are their respective advantages and disadvantages?"

## Three Loading Strategies

The framework provides three ways to load relationships. They differ in **when** the query executes and **how much** data is loaded:

| Strategy | Trigger | Query count | Use case |
|----------|---------|-------------|----------|
| **Lazy loading** (default) | First access to the relation | 1 per object | Uncertain whether relation data is needed |
| **Eager loading** (`with_()`) | Alongside the main query | 1 per relation level | Certain most objects' relations are needed |
| **Batch loading** (concept) | Accessing the first object | 1 per relation level | Want a balance of both |

## The N+1 Query Problem

When iterating through an object list and accessing its relationships one by one, a huge number of database queries is triggered. This is the famous N+1 problem.

```python
users = User.query().all()  # 1 query

for user in users:
    profile = user.profile()  # 1 query per user (N queries total)
```

- With 100 users, total queries = 1 + 100 = 101
- Impact: increased database pressure, accumulated network latency, slower responses, higher connection resource consumption

**The N+1 problem most commonly appears when accessing relations inside loops**, and eager loading is its standard solution.

> 💡 **AI Prompt Example**: "What is the N+1 query problem? What impact will it have on application performance?"

## Lazy Loading

By default, relationships are **lazily loaded**: SQL is executed only when you call the relation method.

```python
user = User.find_one({'username': 'John'})  # Query the user only
profile = user.profile()                    # Query the profile only now
```

- Accessing the same relation again does not re-query — the result is cached
- **Pros**: load on demand, saves memory, high flexibility
- **Cons**: may cause N+1 in loops, unpredictable performance

**Suitable scenarios**:

- Uncertain whether related data will be accessed
- Only need related data for some objects
- Memory-sensitive cases or large related data

> 💡 **AI Prompt Example**: "In what situations is lazy loading more suitable? What issues should be considered when using it?"

## Eager Loading

Using the `with_()` method loads related data alongside the main query — the standard solution to the N+1 problem.

```python
users = User.query().with_('profile').all()  # main query + 1 batch relation query
for user in users:
    profile = user.profile()  # read from cache, no extra query
```

- After the main query runs, the framework batch-loads `profile` for all users in one query
- Accessing the relation reads from cache and does not trigger a query
- **Pros**: minimum query count, best performance, predictable database load
- **Cons**: may load unnecessary data, higher memory usage

`with_()` supports nested paths, query modifiers, path validation and more. See the [Eager Loading Deep Dive](eager_loading.md) for the full rules.

> 💡 **AI Prompt Example**: "How to use the with_() method for eager loading? What performance improvements can eager loading bring?"

## Batch Loading

**Concept**: even without `with_()`, when accessing the relation of the first element in a list, the framework automatically batch-loads the same relation for all other elements.

```python
users = User.query().all()
first_profile = users[0].profile()  # ideally: auto-load profiles for all users
```

> **Note**: the current framework does **not** provide implicit batch loading. Its batch-loading capability is triggered explicitly via `with_()` (see [Loading Mechanics](eager_loading.md#loading-mechanics)). This concept is listed only to help understand the trade-off between eager and lazy loading.

> 💡 **AI Prompt Example**: "What's the difference between batch loading and eager loading? Which approach is more suitable for my application scenario?"

## Choosing a Strategy

| Scenario | Strategy |
|----------|----------|
| Need relation data of most objects | Use `with_()` eager loading |
| Need relations of only a few objects | Use lazy loading (default) |
| Accessing relations in loops | Must use eager loading |
| Need to filter/sort relations | Eager loading + query modifier |
| Performance-critical path | Prefer eager loading |
| Memory-sensitive | Use lazy loading |

> 💡 **AI Prompt Example**: "How to choose the appropriate relationship loading strategy in real projects? What are the best practices?"