# Debugging Guide

This guide covers debugging techniques and tools for RhoSocial ActiveRecord applications, with practical examples from both social media and e-commerce domains.

## Debugging Tools

### Query Logger

```python
from rhosocial.activerecord.logger import QueryLogger

# Enable query logging
logger = QueryLogger()
User.backend().set_logger(logger)

# Log query execution
users = User.query()\
    .with_('posts')\
    .where('status = ?', ('active',))\
    .all()

# Print logged queries
for entry in logger.entries:
    print(f"Query: {entry.sql}")
    print(f"Parameters: {entry.params}")
    print(f"Duration: {entry.duration:.3f}s")
```

### Query Profiler

```python
from rhosocial.activerecord.profiler import QueryProfiler

class OrderProfiler:
    def __init__(self):
        self.profiler = QueryProfiler()
    
    def profile_order_processing(self, order_id: int):
        """Profile order processing."""
        self.profiler.start()
        
        try:
            order = Order.find_one(order_id)
            order.process()
        finally:
            results = self.profiler.stop()
            
            print("Query Profile:")
            print(f"Total Queries: {results.query_count}")
            print(f"Total Time: {results.total_time:.3f}s")
            print("\nSlow Queries:")
            for query in results.slow_queries:
                print(f"Query: {query.sql}")
                print(f"Time: {query.duration:.3f}s")

# Usage
profiler = OrderProfiler()
profiler.profile_order_processing(order_id=1)
```

### Memory Profiler

```python
from rhosocial.activerecord.profiler import MemoryProfiler
import tracemalloc

class MemoryDebugger:
    def __init__(self):
        self.profiler = MemoryProfiler()
    
    def analyze_memory(self, func, *args, **kwargs):
        """Analyze memory usage of function."""
        tracemalloc.start()
        start_snapshot = tracemalloc.take_snapshot()
        
        result = func(*args, **kwargs)
        
        end_snapshot = tracemalloc.take_snapshot()
        stats = end_snapshot.compare_to(start_snapshot, 'lineno')
        
        print("\nMemory Analysis:")
        for stat in stats[:10]:
            print(f"{stat.size_diff / 1024:.1f} KB: {stat.traceback[0]}")
        
        return result

# Usage
debugger = MemoryDebugger()
def load_user_data():
    return User.query().with_('posts.comments').all()

users = debugger.analyze_memory(load_user_data)
```

## Debugging Techniques

### Step-by-Step Debugging

```python
def debug_order_processing(order_id: int):
    """Debug order processing step by step."""
    print("Starting order processing debug...")
    
    # Step 1: Load order
    print("\n1. Loading order...")
    try:
        order = Order.find_one_or_fail(order_id)
        print(f"Order loaded: #{order.id}, Status: {order.status}")
    except RecordNotFound:
        print(f"Error: Order #{order_id} not found")
        return
    
    # Step 2: Check items
    print("\n2. Checking order items...")
    if not order.items:
        print("Error: Order has no items")
        return
    
    for item in order.items:
        print(f"Item: {item.product.name}, Quantity: {item.quantity}")
    
    # Step 3: Verify inventory
    print("\n3. Verifying inventory...")
    inventory_issues = []
    for item in order.items:
        if item.product.stock < item.quantity:
            inventory_issues.append(
                f"Insufficient stock for {item.product.name}: "
                f"needed {item.quantity}, have {item.product.stock}"
            )
    
    if inventory_issues:
        print("Inventory issues found:")
        for issue in inventory_issues:
            print(f"- {issue}")
        return
    
    # Step 4: Process order
    print("\n4. Processing order...")
    try:
        with Order.transaction():
            order.process()
        print("Order processed successfully")
    except Exception as e:
        print(f"Error processing order: {e}")
```

### Transaction Debugging

```python
class TransactionDebugger:
    """Debug transaction execution."""
    
    def __init__(self):
        self.depth = 0
        self.events = []
    
    def log_event(self, event: str):
        """Log transaction event."""
        indent = "  " * self.depth
        self.events.append(f"{indent}{event}")
    
    def debug_transaction(self, func):
        """Debug transaction execution."""
        def wrapper(*args, **kwargs):
            self.depth = 0
            self.events.clear()
            
            try:
                with Order.transaction() as tx:
                    self.log_event("Begin transaction")
                    self.depth += 1
                    
                    try:
                        result = func(*args, **kwargs)
                        self.log_event("Operation successful")
                    except Exception as e:
                        self.log_event(f"Operation failed: {e}")
                        raise
                    
                    self.depth -= 1
                    self.log_event("Commit transaction")
                    return result
                    
            except Exception as e:
                self.depth -= 1
                self.log_event(f"Rollback transaction: {e}")
                raise
            finally:
                print("\nTransaction Debug Log:")
                for event in self.events:
                    print(event)
        
        return wrapper

# Usage
debugger = TransactionDebugger()

@debugger.debug_transaction
def process_order(order_id: int):
    order = Order.find_one_or_fail(order_id)
    order.process()
```

### Relationship Debugging

```python
class RelationshipDebugger:
    """Debug model relationships."""
    
    def analyze_relationships(self, instance: ActiveRecord):
        """Analyze model relationships."""
        print(f"\nAnalyzing relationships for {instance.__class__.__name__}:")
        
        for name, relation in instance.__class__.__dict__.items():
            if isinstance(relation, (HasOne, HasMany, BelongsTo)):
                print(f"\nRelationship: {name}")
                print(f"Type: {relation.__class__.__name__}")
                print(f"Foreign Key: {relation.foreign_key}")
                
                try:
                    value = getattr(instance, name)
                    if value is None:
                        print("Status: No related record")
                    elif isinstance(value, list):
                        print(f"Status: {len(value)} related records")
                    else:
                        print("Status: Related record found")
                except Exception as e:
                    print(f"Error: {e}")

# Usage
debugger = RelationshipDebugger()
order = Order.find_one(1)
debugger.analyze_relationships(order)
```

## Common Debugging Scenarios

### Query Debugging

```python
def debug_query(query: 'IQuery'):
    """Debug query execution."""
    print("\nQuery Debug Info:")
    
    # Get SQL
    sql, params = query.to_sql()
    print(f"SQL: {sql}")
    print(f"Parameters: {params}")
    
    # Get execution plan
    plan = query.explain()
    print(f"\nExecution Plan:\n{plan}")
    
    # Execute with timing
    start = time.perf_counter()
    result = query.all()
    duration = time.perf_counter() - start
    
    print(f"\nExecution Time: {duration:.3f}s")
    print(f"Result Count: {len(result)}")
    
    return result

# Usage
query = User.query()\
    .with_('posts.comments')\
    .where('status = ?', ('active',))

users = debug_query(query)
```

### Performance Debugging

```python
def debug_performance(func):
    """Debug function performance."""
    def wrapper(*args, **kwargs):
        print(f"\nDebug: {func.__name__}")
        
        # Memory before
        tracemalloc.start()
        start_snapshot = tracemalloc.take_snapshot()
        
        # Time execution
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        duration = time.perf_counter() - start_time
        
        # Memory after
        end_snapshot = tracemalloc.take_snapshot()
        memory_stats = end_snapshot.compare_to(start_snapshot, 'lineno')
        
        print(f"\nExecution Time: {duration:.3f}s")
        print("\nMemory Usage:")
        for stat in memory_stats[:3]:
            print(f"{stat.size_diff / 1024:.1f} KB: {stat.traceback[0]}")
        
        return result
    
    return wrapper

# Usage
@debug_performance
def process_orders():
    return Order.query()\
        .with_('items.product')\
        .where('status = ?', ('pending',))\
        .all()
```

## Best Practices

1. **Systematic Approach**
   - Follow debugging steps
   - Document findings
   - Test thoroughly
   - Review changes

2. **Tools Usage**
   - Use appropriate tools
   - Monitor performance
   - Track resource usage
   - Log important events

3. **Problem Isolation**
   - Isolate issues
   - Test components
   - Verify assumptions
   - Document solutions

4. **Prevention**
   - Write testable code
   - Add logging
   - Monitor performance
   - Review regularly

## Next Steps

1. Study [Performance Problems](performance_problems.md)
2. Learn about [Error Resolution](error_resolution.md)
3. Review [Common Issues](common_issues.md)