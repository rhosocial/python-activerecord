# Loading Strategies

Choosing the appropriate loading strategy is crucial for application performance when using relationships. Different loading strategies are suitable for different usage scenarios.

> 💡 **AI Prompt Example**: "What are the relationship loading strategies in ActiveRecord? What are their respective advantages and disadvantages?"

## The N+1 Query Problem

When iterating through an object list and accessing its relationships, it may trigger a massive amount of database queries, which is the famous N+1 problem.

```python
# Import necessary modules
from typing import List
from rhosocial.activerecord.model import ActiveRecord

# Assume we have User and Profile models with a one-to-one relationship
# User.has_one(Profile) and Profile.belongs_to(User)

# N+1 Query Problem Example
print("=== N+1 Query Problem Example ===")

# First query: get all users
users = User.query().all()  # Execute 1 query
print(f"Got {len(users)} users")

# Iterate through users and access related profiles
for user in users:
    # Each call to profile() executes 1 database query
    # If there are 100 users, 100 queries will be executed
    profile = user.profile()  # Execute N queries (N = number of users)
    if profile:
        print(f"User {user.username}'s bio: {profile.bio}")
    else:
        print(f"User {user.username} has no profile")

# Total queries = 1 + N = 101 queries (assuming 100 users)
print(f"Total database queries executed: {1 + len(users)}")

# Impact of N+1 problem:
# 1. Increased database pressure
# 2. Accumulated network latency
# 3. Longer application response time
# 4. Increased database connection resource consumption
```

> 💡 **AI Prompt Example**: "What is the N+1 query problem? What impact will it have on application performance?"

## Eager Loading

Using the `with_()` method allows you to load related data alongside the main query, effectively solving the N+1 problem.

```python
# Eager Loading Example
print("=== Eager Loading Example ===")

# Use eager loading to get users and their profiles in one go
# with_('profile') tells the ORM to load related profile data along with user data
users_with_profiles = User.query().with_('profile').all()  # Only execute 1 query (or few queries)

print(f"Got {len(users_with_profiles)} users and their profiles through eager loading")

# Iterate through users and access related profiles
for user in users_with_profiles:
    # No more DB query triggered here, reading directly from cache
    # Because profile data was already fetched during eager loading
    profile = user.profile()  # Get from cache, no query execution
    if profile:
        print(f"User {user.username}'s bio: {profile.bio}")
    else:
        print(f"User {user.username} has no profile")

# Total queries = 1 (or through JOIN to get all data)
print(f"Total database queries executed: 1")

# Advantages of eager loading:
# 1. Significantly reduces database query count
# 2. Reduces network latency
# 3. Improves application response speed
# 4. Reduces database connection resource consumption

# Eager loading multiple relationships
print("\n=== Eager Loading Multiple Relationships ===")

# Assume User also has posts relationship (one-to-many)
# Can eager load multiple relationships simultaneously
users_with_relations = User.query().with_('profile').with_('posts').all()

for user in users_with_relations:
    # Access eagerly loaded profile
    profile = user.profile()  # Get from cache
    
    # Access eagerly loaded posts
    posts = user.posts()  # Get from cache
    
    print(f"User {user.username} has {len(posts)} posts")
    if profile:
        print(f"  Bio: {profile.bio}")
```

> 💡 **AI Prompt Example**: "How to use the with_() method for eager loading? What performance improvements can eager loading bring?"

## Lazy Loading

By default, relationships are lazily loaded. SQL is executed only when you call the relationship method.

```python
# Lazy Loading Example
print("=== Lazy Loading Example ===")

# Get user without loading relationships
user = User.find_one({'username': 'John'})  # Execute 1 query to get user

# At this point, user object is loaded, but related profile is not loaded
print(f"Got user: {user.username}")

# Execute query only when really need to access related data
if user:
    # Only execute database query when calling profile()
    profile = user.profile()  # Execute 1 query to get profile
    
    if profile:
        print(f"User profile: {profile.bio}")
    else:
        print("User has no profile")
    
    # Accessing the same relationship again won't execute query
    # Because data has been cached
    profile_again = user.profile()  # Get from cache, no query execution
    print("Second access to profile (from cache)")

# Suitable scenarios for lazy loading:
# 1. Uncertain whether related data will be accessed
# 2. Only need to access related data for some objects
# 3. Memory usage sensitive scenarios
# 4. Cases with large related data

# Considerations for lazy loading:
# 1. May cause N+1 query problem
# 2. Need to pay attention to database connection lifecycle
# 3. Consider performance impact when accessing relationships in loops
```

> 💡 **AI Prompt Example**: "In what situations is lazy loading more suitable? What issues should be considered when using it?"

## Batch Loading

Even without `with_()`, some advanced loaders support automatically batch loading relationships for all other elements in the list when accessing the relationship of the first element.

```python
# Batch Loading Concept Example (current library mainly relies on with_, but understanding concept helps)
print("=== Batch Loading Concept Example ===")

# Assume there's a batch loading implementation
users = User.query().all()  # Get all users

# When accessing related data of the first user
first_user_profile = users[0].profile()  # Access first user's profile

# Ideally, the system would automatically batch load profiles for all users
# Instead of just the first user's profile
# This can avoid multiple queries when accessing other users' profiles later

print("Advantages of batch loading:")
print("1. Intelligent demand prediction when first accessing related data")
print("2. Automatic query strategy optimization")
print("3. Balances advantages of eager loading and lazy loading")

# Current recommended approach is still explicit with_()
print("\nCurrent recommended approach:")
users_with_profiles = User.query().with_('profile').all()
print("Explicit eager loading remains best practice")
```

> 💡 **AI Prompt Example**: "What's the difference between batch loading and eager loading? Which approach is more suitable for my application scenario?"

## Performance Comparison and Recommendations

```python
# Performance Comparison Summary
print("=== Relationship Loading Strategy Comparison ===")

print("""
1. Eager Loading - with_()
   Suitable scenarios:
   - Need to access related data for most objects
   - Performance-critical scenarios
   - Need to avoid N+1 problem
   
   Advantages:
   - Minimum query count
   - Best performance
   - Predictable database load
   
   Disadvantages:
   - May load unnecessary data
   - Higher memory usage

2. Lazy Loading - Default behavior
   Suitable scenarios:
   - Uncertain whether related data will be accessed
   - Only need to access related data for few objects
   - Memory usage sensitive scenarios
   
   Advantages:
   - Load on demand, saves memory
   - High flexibility
   
   Disadvantages:
   - May cause N+1 problem
   - Unpredictable performance

3. Recommendations:
   - Certain need for related data → Use eager loading
   - Uncertain need → Use lazy loading
   - Loop accessing related data → Must use eager loading
   - Performance critical path → Prioritize eager loading
""")
```

> 💡 **AI Prompt Example**: "How to choose the appropriate relationship loading strategy in real projects? What are the best practices?"