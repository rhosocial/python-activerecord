# Large Dataset Handling

Working with large datasets efficiently is a common challenge in database applications. This document explores various techniques and strategies for handling large volumes of data in rhosocial ActiveRecord applications without compromising performance or memory usage.

## Introduction

When dealing with tables containing thousands or millions of records, loading all data at once can lead to performance issues, memory exhaustion, and poor user experience. rhosocial ActiveRecord provides several approaches to work with large datasets efficiently.

## Pagination

Pagination is the most common technique for breaking large result sets into manageable chunks, especially for user interfaces.

### Basic Pagination

```python
from rhosocial.activerecord.models import Article

# Configure pagination parameters
page = 2  # Page number (1-based)
page_size = 20  # Items per page

# Retrieve a specific page of results
articles = Article.objects.order_by('id')\
                        .offset((page - 1) * page_size)\
                        .limit(page_size)\
                        .all()

# Get total count for pagination controls
total_count = Article.objects.count()
total_pages = (total_count + page_size - 1) // page_size
```

### Pagination Helper

rhosocial ActiveRecord provides a pagination helper for convenience:

```python
from rhosocial.activerecord.pagination import paginate

# Get a paginated result
pagination = paginate(Article.objects.order_by('published_at'), page=2, per_page=20)

# Access pagination data
articles = pagination.items
total_pages = pagination.pages
total_count = pagination.total
current_page = pagination.page

# Check if there are more pages
has_next = pagination.has_next
has_prev = pagination.has_prev

# Get next/previous page numbers
next_page = pagination.next_page
prev_page = pagination.prev_page
```

## Cursor-based Pagination

Cursor-based pagination is more efficient than offset-based pagination for large datasets, as it uses a "cursor" (typically a unique, indexed column value) to track position.

```python
from rhosocial.activerecord.models import Article

# Initial query (first page)
page_size = 20
articles = Article.objects.order_by('id').limit(page_size).all()

# Get the last ID as the cursor for the next page
if articles:
    last_id = articles[-1].id
    
    # Get the next page using the cursor
    next_page = Article.objects.filter(id__gt=last_id)\
                             .order_by('id')\
                             .limit(page_size)\
                             .all()
```

### Cursor Pagination Helper

rhosocial ActiveRecord provides a helper for cursor-based pagination:

```python
from rhosocial.activerecord.pagination import cursor_paginate

# Initial page (no cursor)
result = cursor_paginate(Article.objects.order_by('published_at'), 
                        cursor_field='published_at',
                        limit=20)

# Access results and pagination metadata
articles = result.items
next_cursor = result.next_cursor
prev_cursor = result.prev_cursor

# Get next page using the cursor
next_page = cursor_paginate(Article.objects.order_by('published_at'),
                           cursor_field='published_at',
                           cursor=next_cursor,
                           limit=20)
```

## Chunked Processing

For background processing or data analysis, chunked processing allows you to work with large datasets in manageable pieces:

```python
from rhosocial.activerecord.models import Article

# Process all articles in chunks of 1000
chunk_size = 1000
offset = 0

while True:
    # Get the next chunk
    articles = Article.objects.order_by('id')\
                            .offset(offset)\
                            .limit(chunk_size)\
                            .all()
    
    # Exit the loop if no more articles
    if not articles:
        break
    
    # Process the chunk
    for article in articles:
        process_article(article)
    
    # Update the offset for the next chunk
    offset += chunk_size
```

### Batch Processing Helper

rhosocial ActiveRecord provides a helper for batch processing:

```python
from rhosocial.activerecord.models import Article

# Process all articles in batches of 1000
for batch in Article.objects.in_batches(1000):
    for article in batch:
        process_article(article)

# Process with a specific query
for batch in Article.objects.filter(status='published').in_batches(1000):
    for article in batch:
        process_article(article)
```

## Stream Processing

For extremely large datasets, stream processing allows you to work with one record at a time without loading the entire result set into memory:

```python
from rhosocial.activerecord.models import Article

# Stream all articles one by one
for article in Article.objects.stream():
    process_article(article)

# Stream with a specific query
for article in Article.objects.filter(status='published').stream():
    process_article(article)
```

## Memory Optimization Techniques

### Select Only Needed Columns

```python
from rhosocial.activerecord.models import Article

# Instead of selecting all columns
# articles = Article.objects.all()

# Select only the columns you need
articles = Article.objects.select('id', 'title', 'published_at').all()
```

### Defer Loading of Large Columns

```python
from rhosocial.activerecord.models import Article

# Defer loading of large text columns
articles = Article.objects.defer('content', 'metadata').all()

# Later, if needed, load the deferred column
article = articles[0]
content = article.content  # Triggers an additional query to load just the content
```

### Use Iterators Instead of Loading All Records

```python
from rhosocial.activerecord.models import Article

# Instead of loading all records at once
# articles = Article.objects.all()

# Use an iterator to process one record at a time
for article in Article.objects.iterator():
    process_article(article)
```

## Working with Aggregations on Large Datasets

Performing aggregations on large datasets can be resource-intensive. Optimize by pushing the work to the database:

```python
from rhosocial.activerecord.models import Article

# Instead of loading all records and calculating in Python
# articles = Article.objects.all()
# total_views = sum(article.views for article in articles)  # Inefficient

# Let the database do the work
total_views = Article.objects.sum('views')

# Complex aggregations
results = Article.objects.group_by('category_id')\
                       .select('category_id', 'COUNT(*) as article_count', 'AVG(views) as avg_views')\
                       .having('COUNT(*) > 10')\
                       .all()
```

## Database-Specific Optimizations

### PostgreSQL

```python
# Use PostgreSQL's COPY command for bulk imports
from rhosocial.activerecord.connection import connection

def bulk_import_from_csv(file_path):
    with open(file_path, 'r') as f:
        cursor = connection.cursor()
        cursor.copy_expert(f"COPY articles(title, content, published_at) FROM STDIN WITH CSV HEADER", f)
        connection.commit()
```

### MySQL/MariaDB

```python
# Use MySQL's LOAD DATA INFILE for bulk imports
from rhosocial.activerecord.connection import connection

def bulk_import_from_csv(file_path):
    query = f"LOAD DATA INFILE '{file_path}' INTO TABLE articles FIELDS TERMINATED BY ',' ENCLOSED BY '\"' LINES TERMINATED BY '\n' IGNORE 1 ROWS (title, content, published_at)"
    connection.execute(query)
```

## Performance Considerations

### Indexing for Large Datasets

Proper indexing is crucial for large dataset performance:

```python
from rhosocial.activerecord.migration import Migration

class OptimizeArticlesTable(Migration):
    def up(self):
        # Add indexes for commonly queried columns
        self.add_index('articles', 'published_at')
        self.add_index('articles', ['status', 'published_at'])
        
        # For cursor-based pagination
        self.add_index('articles', 'id')
```

### Query Optimization

```python
# Use EXPLAIN to understand query execution
query = Article.objects.filter(status='published').order_by('published_at')
explain_result = query.explain()
print(explain_result)

# Optimize the query based on the EXPLAIN output
optimized_query = Article.objects.filter(status='published')\
                               .order_by('published_at')\
                               .select('id', 'title', 'published_at')\
                               .limit(100)
```

## Monitoring and Profiling

Regularly monitor and profile your large dataset operations:

```python
from rhosocial.activerecord.profiler import QueryProfiler

# Profile a large dataset operation
with QueryProfiler() as profiler:
    for batch in Article.objects.in_batches(1000):
        for article in batch:
            process_article(article)

# View profiling results
print(profiler.summary())
```

## Best Practices Summary

1. **Never load entire large datasets** into memory at once
2. **Use pagination** for user interfaces
3. **Consider cursor-based pagination** for very large datasets
4. **Process large datasets in chunks** for background operations
5. **Stream records** when processing extremely large datasets
6. **Select only needed columns** to reduce memory usage
7. **Use database aggregations** instead of loading data into Python
8. **Ensure proper indexing** for query performance
9. **Monitor and profile** your large dataset operations
10. **Consider database-specific optimizations** for bulk operations

By applying these large dataset handling techniques, you can work efficiently with tables containing millions of records while maintaining good performance and memory usage in your rhosocial ActiveRecord applications.