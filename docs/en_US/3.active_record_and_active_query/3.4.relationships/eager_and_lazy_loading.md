# Eager Loading and Lazy Loading

Efficient data loading is crucial for application performance, especially when working with related records. rhosocial ActiveRecord provides two primary approaches for loading related data: eager loading and lazy loading. This document explores these loading strategies in depth, providing practical examples and best practices.

## Understanding Loading Strategies

Before diving into the specifics of each loading strategy, it's important to understand the fundamental difference between them:

- **Lazy Loading**: Loads related data only when it's explicitly requested
- **Eager Loading**: Loads related data in advance, typically when the parent record is loaded

The choice between these strategies can significantly impact your application's performance and resource usage.

## Lazy Loading

Lazy loading is the default behavior in rhosocial ActiveRecord. When you access a relationship, the framework executes a separate database query to retrieve the related data.

### How Lazy Loading Works

When you define a relationship in your model, rhosocial ActiveRecord creates a method that, when called, executes a query to fetch the related records:

```python
from typing import ClassVar, Optional
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.field import IntegerPKMixin
from rhosocial.activerecord.relation import HasMany, BelongsTo

class Author(IntegerPKMixin, ActiveRecord):
    __table_name__ = "authors"
    
    id: Optional[int] = None
    name: str
    
    books: ClassVar[HasMany['Book']] = HasMany(
        foreign_key='author_id',
        inverse_of='author'
    )

class Book(IntegerPKMixin, ActiveRecord):
    __table_name__ = "books"
    
    id: Optional[int] = None
    title: str
    author_id: int
    
    author: ClassVar[BelongsTo['Author']] = BelongsTo(
        foreign_key='author_id',
        inverse_of='books'
    )
```

With lazy loading, related data is loaded only when you call the relationship method:

```python
# Load an author
author = Author.find_by(name="Jane Austen")

# No books are loaded yet

# Now the books are loaded when we call the books() method
books = author.books()

for book in books:
    print(f"Book: {book.title}")
    
    # This triggers another query to load the author
    book_author = book.author()
    print(f"Author: {book_author.name}")
```

### When to Use Lazy Loading

Lazy loading is appropriate in the following scenarios:

1. **When you don't always need related data**: If you only occasionally need to access related records, lazy loading prevents unnecessary data retrieval

2. **For deeply nested relationships**: When you have complex relationship chains and only need specific branches

3. **For large related datasets**: When related collections might contain many records and you want to avoid loading them all

4. **During development and exploration**: When you're not yet sure which relationships you'll need

### The N+1 Query Problem

The main drawback of lazy loading is the N+1 query problem. This occurs when you load a collection of N records and then access a relationship for each one, resulting in N additional queries:

```python
# Load all authors (1 query)
authors = Author.find_all().all()

# For each author, load their books (N additional queries)
for author in authors:
    books = author.books()  # This executes a query for each author
    print(f"Author: {author.name}, Books: {len(books)}")
```

This pattern can lead to performance issues as the number of records increases.

## Eager Loading

Eager loading addresses the N+1 query problem by loading related data in advance. rhosocial ActiveRecord provides the `with_` method to specify which relationships should be eager loaded.

### Basic Eager Loading

To eager load a relationship, use the `with_` method in your query:

```python
# Eager load books when fetching authors
authors = Author.find_all().with_("books").all()

# Now you can access books without additional queries
for author in authors:
    books = author.books()  # No additional query is executed
    print(f"Author: {author.name}, Books: {len(books)}")
```

Behind the scenes, rhosocial ActiveRecord executes two queries:
1. One query to fetch all authors
2. Another query to fetch all books for those authors

It then associates the books with their respective authors in memory, so no additional queries are needed when you access the relationship.

### Nested Eager Loading

You can eager load nested relationships using dot notation:

```python
# Eager load books and each book's reviews
authors = Author.find_all().with_("books.reviews").all()

# Now you can access books and reviews without additional queries
for author in authors:
    for book in author.books():
        print(f"Book: {book.title}")
        for review in book.reviews():
            print(f"  Review: {review.content}")
```

### Multiple Relationship Eager Loading

You can eager load multiple relationships by passing a list to the `with_` method:

```python
# Eager load both books and publisher information
authors = Author.find_all().with_(["books", "publisher"]).all()

# Now you can access both relationships without additional queries
for author in authors:
    books = author.books()
    publisher = author.publisher()
    print(f"Author: {author.name}, Publisher: {publisher.name}")
    print(f"Number of books: {len(books)}")
```

### Conditional Eager Loading

You can combine eager loading with query conditions to limit the related records that are loaded:

```python
# Eager load only published books
authors = Author.find_all().with_("books", lambda q: q.where(published=True)).all()

# Now you can access only published books without additional queries
for author in authors:
    published_books = author.books()  # Contains only published books
    print(f"Author: {author.name}, Published books: {len(published_books)}")
```

### When to Use Eager Loading

Eager loading is beneficial in the following scenarios:

1. **When you know you'll need related data**: If you're certain you'll access related records, eager loading reduces the number of database queries

2. **For collections**: When working with multiple parent records and their relationships

3. **For displaying related data**: When building views or reports that show parent records along with their related data

4. **For consistent performance**: To avoid unpredictable query patterns and ensure consistent response times

## Advanced Loading Techniques

### Selective Loading

Sometimes you may want to load only specific columns of related records. You can achieve this by combining eager loading with select clauses:

```python
# Eager load only book titles
authors = Author.find_all().with_("books", lambda q: q.select("id", "title")).all()

# Now you can access book titles without loading all book data
for author in authors:
    books = author.books()
    for book in books:
        print(f"Book title: {book.title}")
        # Other book attributes might not be available
```

### Counting Related Records

If you only need to know the count of related records without loading them all, you can use the `with_count` method:

```python
# Load authors with book counts
authors = Author.find_all().with_count("books").all()

# Access the count without loading the actual books
for author in authors:
    book_count = author.books_count  # This is a property, not a method call
    print(f"Author: {author.name}, Number of books: {book_count}")
```

### Preloading Specific Records

In some cases, you might want to manually preload related records for better control:

```python
# Load all authors
authors = Author.find_all().all()

# Get all author IDs
author_ids = [author.id for author in authors]

# Preload all books for these authors in a single query
all_books = Book.find_all().where(author_id__in=author_ids).all()

# Group books by author ID
books_by_author = {}
for book in all_books:
    if book.author_id not in books_by_author:
        books_by_author[book.author_id] = []
    books_by_author[book.author_id].append(book)

# Now you can access books without additional queries
for author in authors:
    author_books = books_by_author.get(author.id, [])
    print(f"Author: {author.name}, Books: {len(author_books)}")
```

## Performance Considerations

### Memory Usage

Eager loading loads all related data into memory at once, which can be a concern for large datasets. Consider the following factors:

- **Dataset size**: For very large related collections, eager loading might consume significant memory
- **Application context**: Server environments with limited memory might benefit from more selective loading strategies
- **User experience**: The memory cost might be worth it if it significantly improves response times

### Query Complexity

Eager loading can generate complex SQL queries, especially with nested relationships. Monitor your database performance to ensure these queries are efficient:

- Use database indexes on foreign keys
- Consider the depth of eager loaded relationships
- Watch for query timeouts with very complex relationship chains

### Benchmarking

It's often helpful to benchmark different loading strategies for your specific use case:

```python
import time

# Benchmark lazy loading
start_time = time.time()
authors = Author.find_all().all()
for author in authors:
    books = author.books()
    for book in books:
        _ = book.title
end_time = time.time()
print(f"Lazy loading time: {end_time - start_time} seconds")

# Benchmark eager loading
start_time = time.time()
authors = Author.find_all().with_("books").all()
for author in authors:
    books = author.books()
    for book in books:
        _ = book.title
end_time = time.time()
print(f"Eager loading time: {end_time - start_time} seconds")
```

## Best Practices

### 1. Profile Your Application

Use database query logging and profiling tools to identify N+1 query problems and other performance issues:

```python
# Enable query logging during development
from rhosocial.activerecord import set_query_logging
set_query_logging(True)

# Your code here
```

### 2. Be Strategic with Eager Loading

Only eager load relationships that you know you'll need. Eager loading relationships that aren't used can waste memory and database resources.

### 3. Consider Batch Processing

For very large datasets, consider processing records in batches to balance memory usage and query efficiency:

```python
# Process authors in batches of 100
batch_size = 100
offset = 0

while True:
    authors_batch = Author.find_all().limit(batch_size).offset(offset).with_("books").all()
    
    if not authors_batch:
        break
        
    for author in authors_batch:
        # Process author and books
        pass
        
    offset += batch_size
```

### 4. Use Relationship Caching

Configure appropriate caching for frequently accessed relationships to reduce database load:

```python
from rhosocial.activerecord.relation import HasMany, CacheConfig

class Author(IntegerPKMixin, ActiveRecord):
    # ...
    
    books: ClassVar[HasMany['Book']] = HasMany(
        foreign_key='author_id',
        inverse_of='author',
        cache_config=CacheConfig(enabled=True, ttl=300)  # Cache for 5 minutes
    )
```

### 5. Optimize Queries

Use query scopes and conditions to limit the amount of data loaded:

```python
# Define a scope for recent books
class Book(IntegerPKMixin, ActiveRecord):
    # ...
    
    @classmethod
    def recent(cls, query=None):
        query = query or cls.find_all()
        return query.where(published_at__gte=datetime.now() - timedelta(days=30))

# Use the scope with eager loading
authors = Author.find_all().with_("books", Book.recent).all()
```

### 6. Consider Denormalization

For read-heavy applications, consider denormalizing some data to reduce the need for relationship loading:

```python
class Author(IntegerPKMixin, ActiveRecord):
    __table_name__ = "authors"
    
    id: Optional[int] = None
    name: str
    book_count: int = 0  # Denormalized count of books
    
    # ...
```

## Conclusion

Choosing between eager loading and lazy loading is a critical decision that affects your application's performance and resource usage. By understanding the trade-offs and applying the appropriate strategy for each situation, you can optimize your database interactions and provide a better experience for your users.

Remember that there's no one-size-fits-all approach—the best loading strategy depends on your specific use case, data volume, and application requirements. Regular profiling and benchmarking will help you make informed decisions and continuously improve your application's performance.