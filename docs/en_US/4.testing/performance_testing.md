# Performance Testing

This guide covers performance testing approaches for RhoSocial ActiveRecord applications, using both social media and e-commerce examples to demonstrate testing strategies.

## Benchmark Testing

### Setting Up Benchmarks

```python
import pytest
import time
from statistics import mean, stdev
from typing import List, Dict, Any

def run_benchmark(func: callable, iterations: int = 1000) -> Dict[str, float]:
    """Run benchmark and collect metrics."""
    times: List[float] = []
    
    for _ in range(iterations):
        start = time.perf_counter()
        func()
        end = time.perf_counter()
        times.append(end - start)
    
    return {
        'min': min(times),
        'max': max(times),
        'mean': mean(times),
        'stdev': stdev(times),
        'total': sum(times)
    }

@pytest.fixture
def benchmark_data():
    """Create benchmark dataset."""
    return {
        'users': create_test_users(1000),
        'posts': create_test_posts(5000),
        'comments': create_test_comments(10000)
    }
```

### Model Operation Benchmarks

```python
def test_user_creation_performance(benchmark_data):
    """Benchmark user creation performance."""
    def create_user():
        user = User(
            username=f"user_{time.time_ns()}",
            email=f"user_{time.time_ns()}@example.com"
        )
        user.save()
    
    results = run_benchmark(create_user, iterations=100)
    assert results['mean'] < 0.01  # Less than 10ms average
    assert results['stdev'] < 0.005  # Stable performance

def test_order_processing_performance(benchmark_data):
    """Benchmark order processing performance."""
    def process_order():
        order = create_test_order(
            items_count=5,
            user_id=random.choice(benchmark_data['users'])['id']
        )
        with Order.transaction():
            order.process()
    
    results = run_benchmark(process_order, iterations=50)
    assert results['mean'] < 0.1  # Less than 100ms average
```

### Query Performance Benchmarks

```python
def test_query_performance(benchmark_data):
    """Benchmark complex query performance."""
    def complex_query():
        return User.query()\
            .with_('posts.comments.author')\
            .where('status = ?', ('active',))\
            .limit(20)\
            .all()
    
    results = run_benchmark(complex_query, iterations=100)
    
    # Analyze query performance
    print(f"Query Performance Metrics:")
    print(f"Average time: {results['mean']*1000:.2f}ms")
    print(f"Standard deviation: {results['stdev']*1000:.2f}ms")
    print(f"Min time: {results['min']*1000:.2f}ms")
    print(f"Max time: {results['max']*1000:.2f}ms")

def test_order_search_performance(benchmark_data):
    """Benchmark order search performance."""
    def search_orders():
        return Order.query()\
            .with_('items.product', 'user')\
            .where('status = ?', ('completed',))\
            .where('total > ?', (Decimal('100'),))\
            .order_by('created_at DESC')\
            .limit(10)\
            .all()
    
    results = run_benchmark(search_orders)
    assert results['mean'] < 0.05  # Less than 50ms average
```

## Load Testing

### Setting Up Load Tests

```python
import asyncio
import aiohttp
from concurrent.futures import ThreadPoolExecutor

class LoadTest:
    def __init__(self, concurrent_users: int = 10):
        self.concurrent_users = concurrent_users
        self.results: List[Dict[str, float]] = []
    
    async def run(self, operation: callable, duration: int = 60):
        """Run load test for specified duration."""
        start_time = time.time()
        tasks = []
        
        while time.time() - start_time < duration:
            # Create tasks for concurrent users
            for _ in range(self.concurrent_users):
                task = asyncio.create_task(self.execute_operation(operation))
                tasks.append(task)
            
            # Wait for all tasks
            await asyncio.gather(*tasks)
        
        return self.analyze_results()
    
    async def execute_operation(self, operation: callable):
        """Execute operation and record metrics."""
        start = time.perf_counter()
        try:
            await operation()
            duration = time.perf_counter() - start
            self.results.append({
                'duration': duration,
                'success': True
            })
        except Exception as e:
            duration = time.perf_counter() - start
            self.results.append({
                'duration': duration,
                'success': False,
                'error': str(e)
            })
    
    def analyze_results(self) -> Dict[str, Any]:
        """Analyze load test results."""
        durations = [r['duration'] for r in self.results]
        success_count = sum(1 for r in self.results if r['success'])
        
        return {
            'total_requests': len(self.results),
            'successful_requests': success_count,
            'error_rate': (len(self.results) - success_count) / len(self.results),
            'avg_response_time': mean(durations),
            'p95_response_time': percentile(durations, 95),
            'p99_response_time': percentile(durations, 99)
        }
```

### Social Media Load Tests

```python
async def test_social_media_load(benchmark_data):
    """Test social media platform under load."""
    load_test = LoadTest(concurrent_users=50)
    
    async def view_feed():
        """Simulate user viewing their feed."""
        user_id = random.choice(benchmark_data['users'])['id']
        posts = Post.query()\
            .with_('author', 'comments.author')\
            .where('user_id IN (SELECT followed_id FROM follows WHERE follower_id = ?)', 
                  (user_id,))\
            .order_by('created_at DESC')\
            .limit(20)\
            .all()
        
        # Simulate reading posts
        await asyncio.sleep(0.1)
    
    results = await load_test.run(view_feed, duration=300)
    
    assert results['error_rate'] < 0.01  # Less than 1% errors
    assert results['avg_response_time'] < 0.2  # Less than 200ms average
    assert results['p95_response_time'] < 0.5  # 95% under 500ms
```

### E-commerce Load Tests

```python
async def test_ecommerce_load(benchmark_data):
    """Test e-commerce platform under load."""
    load_test = LoadTest(concurrent_users=100)
    
    async def browse_products():
        """Simulate user browsing products."""
        # Search products
        products = Product.query()\
            .where('stock > 0')\
            .order_by('price ASC')\
            .limit(20)\
            .all()
        
        # Simulate product view
        if products:
            product = random.choice(products)
            similar = Product.query()\
                .where('category_id = ?', (product.category_id,))\
                .where('id != ?', (product.id,))\
                .limit(5)\
                .all()
        
        await asyncio.sleep(0.2)
    
    results = await load_test.run(browse_products, duration=300)
    
    assert results['error_rate'] < 0.005  # Less than 0.5% errors
    assert results['avg_response_time'] < 0.3  # Less than 300ms average
    assert results['p99_response_time'] < 1.0  # 99% under 1s
```

## Profile Tools

### Query Profiling

```python
class QueryProfiler:
    def __init__(self):
        self.queries = []
    
    def start_query(self, sql: str, params: tuple):
        """Record start of query execution."""
        self.queries.append({
            'sql': sql,
            'params': params,
            'start_time': time.perf_counter()
        })
    
    def end_query(self):
        """Record end of query execution."""
        if self.queries:
            query = self.queries[-1]
            query['duration'] = time.perf_counter() - query['start_time']
    
    def analyze(self) -> Dict[str, Any]:
        """Analyze recorded queries."""
        return {
            'total_queries': len(self.queries),
            'total_time': sum(q['duration'] for q in self.queries),
            'avg_time': mean(q['duration'] for q in self.queries),
            'slowest_queries': sorted(
                self.queries,
                key=lambda q: q['duration'],
                reverse=True
            )[:5]
        }

def test_query_profiling():
    """Test with query profiling enabled."""
    profiler = QueryProfiler()
    
    # Enable profiling
    User.backend().profiler = profiler
    
    # Run test operations
    users = User.query()\
        .with_('posts.comments')\
        .where('status = ?', ('active',))\
        .all()
    
    # Analyze results
    analysis = profiler.analyze()
    print(f"Total queries: {analysis['total_queries']}")
    print(f"Average query time: {analysis['avg_time']*1000:.2f}ms")
    
    # Show slowest queries
    print("\nSlowest queries:")
    for query in analysis['slowest_queries']:
        print(f"SQL: {query['sql']}")
        print(f"Duration: {query['duration']*1000:.2f}ms\n")
```

### Memory Profiling

```python
import tracemalloc
from collections import defaultdict

class MemoryProfiler:
    def __init__(self):
        self.snapshots = []
    
    def start(self):
        """Start memory profiling."""
        tracemalloc.start()
    
    def take_snapshot(self, label: str):
        """Take memory snapshot."""
        snapshot = tracemalloc.take_snapshot()
        self.snapshots.append((label, snapshot))
    
    def compare_snapshots(self, label1: str, label2: str) -> Dict[str, Any]:
        """Compare two snapshots."""
        snapshot1 = next(s for l, s in self.snapshots if l == label1)
        snapshot2 = next(s for l, s in self.snapshots if l == label2)
        
        diff = snapshot2.compare_to(snapshot1, 'lineno')
        
        return {
            'total_diff': sum(s.size_diff for s in diff),
            'top_allocations': [
                {
                    'file': str(s.traceback[0]),
                    'size_diff': s.size_diff,
                    'count_diff': s.count_diff
                }
                for s in diff[:10]
            ]
        }

def test_memory_usage():
    """Test memory usage patterns."""
    profiler = MemoryProfiler()
    profiler.start()
    
    # Initial state
    profiler.take_snapshot('initial')
    
    # Load large dataset
    users = create_test_users(1000)
    profiler.take_snapshot('after_users')
    
    # Process data
    posts = create_test_posts(5000)
    profiler.take_snapshot('after_posts')
    
    # Analyze memory usage
    diff = profiler.compare_snapshots('initial', 'after_posts')
    print(f"Total memory increase: {diff['total_diff'] / 1024 / 1024:.2f}MB")
    
    print("\nTop memory allocations:")
    for alloc in diff['top_allocations']:
        print(f"File: {alloc['file']}")
        print(f"Size diff: {alloc['size_diff'] / 1024:.2f}KB")
        print(f"Count diff: {alloc['count_diff']}\n")
```

## Best Practices

1. **Regular Benchmarking**: Run benchmarks regularly
2. **Realistic Data**: Use realistic dataset sizes
3. **Monitor Resources**: Track memory and CPU usage
4. **Profile Queries**: Monitor query performance
5. **Load Testing**: Test under expected load

## Next Steps

1. Study [Query Optimization](../5.performance/query_optimization.md)
2. Learn about [Memory Management](../5.performance/memory_management.md)
3. Explore [Connection Pooling](../5.performance/connection_pooling.md)