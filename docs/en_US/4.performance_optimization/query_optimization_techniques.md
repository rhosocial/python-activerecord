# Query Optimization Techniques

Efficient query construction is fundamental to database application performance. This document explores various techniques to optimize your queries in rhosocial ActiveRecord applications.

## Understanding Query Execution Plans

Query execution plans (or query plans) show how the database engine will execute your query. Understanding these plans is crucial for query optimization.

### Viewing Execution Plans

rhosocial ActiveRecord provides methods to view the execution plan for a query:

```python
from rhosocial.activerecord.models import User

# Get the execution plan without running the query
query = User.objects.filter(status='active').order_by('created_at')
execution_plan = query.explain()
print(execution_plan)

# Get the execution plan with analysis (actual execution statistics)
detailed_plan = query.explain(analyze=True)
print(detailed_plan)
```

### Interpreting Execution Plans

Key elements to look for in execution plans:

1. **Sequential Scans**: Full table scans that can be slow for large tables
2. **Index Scans**: Faster access using indexes
3. **Join Types**: Nested loops, hash joins, merge joins
4. **Sort Operations**: Can be expensive for large datasets
5. **Temporary Tables**: May indicate complex operations

## Index Optimization

Proper indexing is one of the most effective ways to improve query performance.

### Creating Effective Indexes

```python
from rhosocial.activerecord.models import Article
from rhosocial.activerecord.migration import Migration

class CreateArticlesTable(Migration):
    def up(self):
        self.create_table('articles', [
            self.column('id', 'integer', primary_key=True),
            self.column('title', 'string'),
            self.column('author_id', 'integer'),
            self.column('category_id', 'integer'),
            self.column('published_at', 'datetime'),
            self.column('status', 'string')
        ])
        
        # Create single-column indexes
        self.add_index('articles', 'author_id')
        self.add_index('articles', 'published_at')
        
        # Create composite index for common query patterns
        self.add_index('articles', ['category_id', 'status', 'published_at'])
```

### Index Selection Guidelines

1. **Index columns used in WHERE clauses**: Especially for high-cardinality columns
2. **Index columns used in JOIN conditions**: Improves join performance
3. **Index columns used in ORDER BY**: Eliminates sorting operations
4. **Consider composite indexes**: For queries that filter on multiple columns
5. **Index order matters**: Place more selective columns first in composite indexes
6. **Avoid over-indexing**: Indexes speed up reads but slow down writes

## Query Refactoring Strategies

### Optimizing SELECT Statements

```python
# Avoid selecting unnecessary columns
# Instead of:
all_users = User.objects.all()

# Select only needed columns:
user_names = User.objects.select('id', 'name', 'email')
```

### Using Query Scopes

Query scopes help encapsulate common query patterns and promote reuse:

```python
class Article(ActiveRecord):
    __tablename__ = 'articles'
    
    @classmethod
    def published(cls):
        return cls.objects.filter(status='published')
    
    @classmethod
    def by_category(cls, category_id):
        return cls.objects.filter(category_id=category_id)
    
    @classmethod
    def recent(cls, limit=10):
        return cls.objects.order_by('-published_at').limit(limit)

# Usage
recent_articles = Article.recent(5).published()
```

### Optimizing Joins

```python
# Use specific join types when appropriate
query = Article.objects.join('author').filter(author__status='active')

# Use left joins when you need all records from the left table
query = Article.objects.left_join('comments').select('articles.*', 'COUNT(comments.id) as comment_count')

# Avoid joining unnecessary tables
# Instead of joining and then filtering:
query = Article.objects.join('author').join('category').filter(category__name='Technology')

# Consider using subqueries:
tech_category_ids = Category.objects.filter(name='Technology').select('id')
query = Article.objects.filter(category_id__in=tech_category_ids)
```

## Subquery Optimization

Subqueries can be powerful but need careful optimization:

```python
# Inefficient approach with two separate queries
active_author_ids = User.objects.filter(status='active').select('id')
articles = Article.objects.filter(author_id__in=active_author_ids)

# More efficient with a single query using subquery
articles = Article.objects.filter(
    author_id__in=User.objects.filter(status='active').select('id')
)

# Even better with a join if you need author data
articles = Article.objects.join('author').filter(author__status='active')
```

### Correlated vs. Non-correlated Subqueries

- **Non-correlated subqueries** execute independently of the outer query and are generally more efficient
- **Correlated subqueries** reference the outer query and may execute once for each row in the outer query

## LIMIT and Pagination

Always limit result sets when dealing with potentially large datasets:

```python
# Retrieve only what you need
recent_articles = Article.objects.order_by('-published_at').limit(10)

# Implement pagination
page = 2
page_size = 20
articles = Article.objects.order_by('id').offset((page - 1) * page_size).limit(page_size)

# For large datasets, cursor-based pagination is more efficient
last_id = 1000  # ID of the last item from the previous page
next_page = Article.objects.filter(id__gt=last_id).order_by('id').limit(page_size)
```

## Database-Specific Optimizations

### PostgreSQL

```python
# Use PostgreSQL-specific index types
class CreateArticlesTable(Migration):
    def up(self):
        # ... table creation code ...
        
        # GIN index for full-text search
        self.execute("CREATE INDEX articles_content_idx ON articles USING gin(to_tsvector('english', content))")
        
        # BRIN index for large tables with ordered data
        self.execute("CREATE INDEX articles_created_at_idx ON articles USING brin(created_at)")
```

### MySQL/MariaDB

```python
# Use MySQL-specific index hints
query = Article.objects.raw("SELECT * FROM articles USE INDEX (idx_published_at) WHERE status = 'published'")
```

### SQLite

```python
# Enable WAL mode for better concurrency
from rhosocial.activerecord.connection import connection
connection.execute("PRAGMA journal_mode=WAL;")
```

## Performance Considerations

1. **N+1 Query Problem**: Always watch for and eliminate N+1 query patterns by using eager loading

```python
# N+1 problem (1 query for users + N queries for articles)
users = User.objects.all()
for user in users:
    articles = user.articles  # Triggers a separate query for each user

# Solution: eager loading (2 queries total)
users = User.objects.prefetch_related('articles')
for user in users:
    articles = user.articles  # No additional queries
```

2. **Query Caching**: Use query result caching for frequently executed queries

```python
from rhosocial.activerecord.cache import QueryCache

# Cache query results for 5 minutes
active_users = QueryCache.get_or_set(
    'active_users',
    lambda: User.objects.filter(status='active').all(),
    ttl=300
)
```

3. **Batch Processing**: Process large datasets in chunks

```python
# Process records in batches of 1000
for batch in Article.objects.in_batches(1000):
    for article in batch:
        # Process each article
        process_article(article)
```

## Monitoring and Profiling

Regularly monitor and profile your queries to identify optimization opportunities:

```python
from rhosocial.activerecord.profiler import QueryProfiler

# Profile a specific query
with QueryProfiler() as profiler:
    articles = Article.objects.filter(status='published').order_by('-published_at').limit(10)

# View profiling results
print(profiler.summary())
for query in profiler.queries:
    print(f"Query: {query.sql}")
    print(f"Time: {query.duration_ms} ms")
    print(f"Rows: {query.row_count}")
```

## Best Practices Summary

1. **Understand your data access patterns** and optimize for the most common queries
2. **Create appropriate indexes** based on your query patterns
3. **Select only the columns you need** rather than using `SELECT *`
4. **Use eager loading** to avoid N+1 query problems
5. **Limit result sets** to avoid retrieving unnecessary data
6. **Monitor and profile** your queries regularly
7. **Consider database-specific optimizations** for your chosen database
8. **Use query caching** for frequently executed queries
9. **Batch process** large datasets
10. **Optimize joins and subqueries** to minimize data processing

By applying these query optimization techniques, you can significantly improve the performance of your rhosocial ActiveRecord applications, resulting in better response times and resource utilization.