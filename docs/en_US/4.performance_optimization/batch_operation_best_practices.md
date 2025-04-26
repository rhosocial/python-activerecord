# Batch Operation Best Practices

Batch operations allow you to perform actions on multiple records efficiently, significantly improving performance when working with large datasets. This document explores best practices and techniques for implementing batch operations in rhosocial ActiveRecord applications.

## Introduction

When you need to create, update, or delete multiple records, performing individual operations can be inefficient due to the overhead of multiple database queries and transactions. Batch operations address this by consolidating multiple operations into fewer database interactions.

## Batch Creation

### Basic Batch Insert

```python
from rhosocial.activerecord.models import Article

# Instead of creating articles one by one
# for title in titles:
#     Article(title=title, status='draft').save()

# Create multiple articles in a single operation
articles = [
    Article(title="Article 1", status="draft"),
    Article(title="Article 2", status="draft"),
    Article(title="Article 3", status="draft")
]

# Insert all articles in a single query
Article.objects.bulk_create(articles)
```

### Batch Insert with Returning IDs

```python
from rhosocial.activerecord.models import Article

# Create articles and get their IDs
articles = [
    Article(title="Article 1", status="draft"),
    Article(title="Article 2", status="draft"),
    Article(title="Article 3", status="draft")
]

# Insert and return IDs
Article.objects.bulk_create(articles, return_ids=True)

# Now the article instances have their IDs populated
for article in articles:
    print(f"Created article with ID: {article.id}")
```

### Chunked Batch Insert

For very large datasets, you may need to break the insertion into chunks:

```python
from rhosocial.activerecord.models import Article

# Generate a large number of articles
articles = [Article(title=f"Article {i}", status="draft") for i in range(1, 10001)]

# Insert in chunks of 1000
chunk_size = 1000
for i in range(0, len(articles), chunk_size):
    chunk = articles[i:i+chunk_size]
    Article.objects.bulk_create(chunk)
```

## Batch Updates

### Update Multiple Records with the Same Values

```python
from rhosocial.activerecord.models import Article

# Instead of updating articles one by one
# for article in Article.objects.filter(status='draft'):
#     article.status = 'published'
#     article.save()

# Update all draft articles to published in a single query
Article.objects.filter(status='draft').update(status='published')
```

### Conditional Batch Updates

```python
from rhosocial.activerecord.models import Article
from datetime import datetime, timedelta

# Update articles older than 30 days to archived status
thirty_days_ago = datetime.now() - timedelta(days=30)
Article.objects.filter(
    status='published',
    published_at__lt=thirty_days_ago
).update(status='archived')
```

### Update with Expressions

```python
from rhosocial.activerecord.models import Article
from rhosocial.activerecord.expressions import F

# Increment view count for all articles in a category
Article.objects.filter(category_id=5).update(views=F('views') + 1)

# Apply a percentage discount to all products in a category
Product.objects.filter(category_id=3).update(
    price=F('price') * 0.9  # 10% discount
)
```

## Batch Deletes

### Delete Multiple Records

```python
from rhosocial.activerecord.models import Article

# Instead of deleting articles one by one
# for article in Article.objects.filter(status='draft'):
#     article.delete()

# Delete all draft articles in a single query
Article.objects.filter(status='draft').delete()
```

### Conditional Batch Deletes

```python
from rhosocial.activerecord.models import Article
from datetime import datetime, timedelta

# Delete articles older than 1 year
one_year_ago = datetime.now() - timedelta(days=365)
Article.objects.filter(created_at__lt=one_year_ago).delete()
```

### Soft Deletes

If your model uses soft deletes, batch operations respect this behavior:

```python
from rhosocial.activerecord.models import Article

# Soft delete all draft articles
Article.objects.filter(status='draft').delete()  # Sets deleted_at timestamp

# Force hard delete even with soft delete models
Article.objects.filter(status='draft').hard_delete()
```

## Transaction Management for Batch Operations

Wrapping batch operations in transactions ensures atomicity:

```python
from rhosocial.activerecord.models import Article, Category
from rhosocial.activerecord.transaction import transaction

# Ensure all operations succeed or all fail
with transaction():
    # Update all articles in a category
    Article.objects.filter(category_id=5).update(status='archived')
    
    # Update the category itself
    Category.objects.filter(id=5).update(active=False)
```

### Nested Transactions

```python
from rhosocial.activerecord.models import Article, Category, Comment
from rhosocial.activerecord.transaction import transaction

# Outer transaction
with transaction():
    # Archive category
    Category.objects.filter(id=5).update(active=False)
    
    # Inner transaction for article operations
    with transaction():
        # Archive all articles in the category
        Article.objects.filter(category_id=5).update(status='archived')
        
        # Archive all comments on those articles
        article_ids = Article.objects.filter(category_id=5).values_list('id', flat=True)
        Comment.objects.filter(article_id__in=article_ids).update(status='archived')
```

## Error Handling in Batch Operations

### Basic Error Handling

```python
from rhosocial.activerecord.models import Article
from rhosocial.activerecord.exceptions import DatabaseError

try:
    # Attempt batch update
    Article.objects.filter(status='draft').update(published_at=datetime.now())
except DatabaseError as e:
    # Handle database errors
    print(f"Batch update failed: {e}")
    # Implement recovery logic
```

### Partial Success Handling

For operations that don't support transactions or when you want to allow partial success:

```python
from rhosocial.activerecord.models import Article

articles = [Article(title=f"Article {i}") for i in range(1, 101)]
success_count = 0
failed_articles = []

# Process in smaller batches to allow partial success
for i in range(0, len(articles), 10):
    chunk = articles[i:i+10]
    try:
        Article.objects.bulk_create(chunk)
        success_count += len(chunk)
    except Exception as e:
        failed_articles.extend(chunk)
        print(f"Failed to create batch {i//10 + 1}: {e}")

print(f"Successfully created {success_count} articles")
print(f"Failed to create {len(failed_articles)} articles")
```

## Performance Optimization Techniques

### Choosing the Right Batch Size

The optimal batch size depends on your specific database and data:

```python
from rhosocial.activerecord.models import Article
from rhosocial.activerecord.profiler import QueryProfiler

articles = [Article(title=f"Article {i}") for i in range(1, 10001)]

# Test different batch sizes to find the optimal one
batch_sizes = [100, 500, 1000, 2000, 5000]
results = {}

for size in batch_sizes:
    with QueryProfiler() as profiler:
        for i in range(0, len(articles), size):
            chunk = articles[i:i+size]
            Article.objects.bulk_create(chunk)
    
    results[size] = profiler.total_duration_ms

# Find the optimal batch size
optimal_size = min(results, key=results.get)
print(f"Optimal batch size: {optimal_size}")
```

### Disabling Validation for Trusted Data

```python
from rhosocial.activerecord.models import Article

articles = [Article(title=f"Article {i}", status="draft") for i in range(1, 1001)]

# Skip validation for trusted data to improve performance
Article.objects.bulk_create(articles, validate=False)
```

### Disabling Hooks for Maximum Performance

```python
from rhosocial.activerecord.models import Article

articles = [Article(title=f"Article {i}", status="draft") for i in range(1, 1001)]

# Skip lifecycle hooks for maximum performance
Article.objects.bulk_create(articles, hooks=False)
```

## Database-Specific Optimizations

### PostgreSQL

```python
# Use PostgreSQL's COPY command for maximum insert performance
from rhosocial.activerecord.connection import connection
import io
import csv

def bulk_insert_with_copy(records):
    # Prepare data in CSV format
    output = io.StringIO()
    writer = csv.writer(output)
    for record in records:
        writer.writerow([record.title, record.status])
    output.seek(0)
    
    # Use COPY command
    cursor = connection.cursor()
    cursor.copy_expert("COPY articles(title, status) FROM STDIN WITH CSV", output)
    connection.commit()
```

### MySQL/MariaDB

```python
# Use MySQL's INSERT IGNORE for handling duplicates
from rhosocial.activerecord.models import Article

# Custom SQL for optimized inserts
sql = "INSERT IGNORE INTO articles (title, status) VALUES (%s, %s)"
values = [(f"Article {i}", "draft") for i in range(1, 1001)]

from rhosocial.activerecord.connection import connection
with connection.cursor() as cursor:
    cursor.executemany(sql, values)
```

## Monitoring and Profiling Batch Operations

```python
from rhosocial.activerecord.models import Article
from rhosocial.activerecord.profiler import QueryProfiler
import time

# Generate test data
articles = [Article(title=f"Article {i}", status="draft") for i in range(1, 10001)]

# Profile batch creation
with QueryProfiler() as profiler:
    start_time = time.time()
    
    for i in range(0, len(articles), 1000):
        chunk = articles[i:i+1000]
        Article.objects.bulk_create(chunk)
    
    elapsed_time = time.time() - start_time

print(f"Created 10,000 articles in {elapsed_time:.2f} seconds")
print(f"Total queries: {profiler.query_count}")
print(f"Average query time: {profiler.average_duration_ms:.2f} ms")
```

## Best Practices Summary

1. **Use Batch Operations** whenever you need to create, update, or delete multiple records

2. **Choose Appropriate Batch Sizes** based on your database and data characteristics
   - Smaller batches (100-1000) for most operations
   - Larger batches for simpler data structures
   - Test different sizes to find the optimal balance

3. **Use Transactions** to ensure atomicity of related batch operations

4. **Consider Disabling Validation and Hooks** for trusted data and maximum performance

5. **Implement Proper Error Handling** to manage failures in batch operations

6. **Monitor and Profile** your batch operations to identify optimization opportunities

7. **Consider Database-Specific Optimizations** for maximum performance

8. **Process Very Large Datasets in Chunks** to manage memory usage

9. **Use Expressions for Complex Updates** rather than loading and modifying records

10. **Balance Performance with Data Integrity** based on your application requirements

By following these batch operation best practices, you can significantly improve the performance of your rhosocial ActiveRecord applications when working with multiple records, resulting in faster processing times and reduced database load.