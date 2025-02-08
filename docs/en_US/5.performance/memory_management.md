# Connection Pooling

This guide covers connection pooling in RhoSocial ActiveRecord to efficiently manage database connections. We'll explore configuration options and best practices.

## Basic Configuration

### Setting Up Connection Pool

```python
from rhosocial.activerecord.backend.typing import ConnectionConfig

# Basic pool configuration
config = ConnectionConfig(
    database='app.db',
    pool_size=5,          # Number of connections
    pool_timeout=30       # Timeout in seconds
)

# Configure models with pool
def configure_models():
    for model in [User, Post, Comment]:
        model.configure(config, SQLiteBackend)
```

### Pool Size Calculation

Guidelines for determining pool size:
```python
import multiprocessing

def calculate_pool_size():
    cpu_count = multiprocessing.cpu_count()
    worker_processes = cpu_count * 2
    connections_per_worker = 2
    
    return {
        'min_size': worker_processes,
        'max_size': worker_processes * connections_per_worker
    }

# Configure based on server capacity
pool_params = calculate_pool_size()
config = ConnectionConfig(
    database='app.db',
    pool_size=pool_params['max_size'],
    pool_timeout=30
)
```

## Advanced Configuration

### Environment-Based Configuration

```python
import os

def get_pool_config():
    """Get pool configuration from environment"""
    return ConnectionConfig(
        database=os.getenv('DB_NAME', 'app.db'),
        pool_size=int(os.getenv('DB_POOL_SIZE', '5')),
        pool_timeout=int(os.getenv('DB_POOL_TIMEOUT', '30')),
        pool_recycle=int(os.getenv('DB_POOL_RECYCLE', '3600'))
    )

# Social media example configuration
class SocialMediaConfig:
    def __init__(self):
        self.config = get_pool_config()
        self.models = [User, Post, Comment]
    
    def configure(self):
        for model in self.models:
            model.configure(self.config, SQLiteBackend)

# E-commerce example configuration
class ECommerceConfig:
    def __init__(self):
        self.config = get_pool_config()
        self.models = [User, Order, Product, OrderItem]
    
    def configure(self):
        for model in self.models:
            model.configure(self.config, SQLiteBackend)
```

### Pool Events

```python
class ConnectionPool:
    def on_checkout(self, dbapi_connection, connection_record, connection_proxy):
        """Called when connection is checked out from pool"""
        print(f"Connection checkout: {connection_record}")
    
    def on_checkin(self, dbapi_connection, connection_record):
        """Called when connection is returned to pool"""
        print(f"Connection checkin: {connection_record}")
    
    def on_connect(self, dbapi_connection, connection_record):
        """Called when new connection is created"""
        print(f"New connection: {connection_record}")
```

## Pool Management

### Transaction Management

```python
def process_order(order_id: int) -> None:
    """Process order with proper connection handling"""
    with Order.transaction() as tx:
        # Connection is automatically checked out
        order = Order.find_one_or_fail(order_id)
        
        # Process order items
        for item in order.items:
            process_item(item)
        
        # Connection is automatically returned to pool
        order.status = 'processed'
        order.save()

# Batch processing example
def process_pending_orders():
    """Process multiple orders efficiently"""
    orders = Order.query()\
        .where('status = ?', ('pending',))\
        .all()
    
    for order in orders:
        with Order.transaction():
            process_order(order.id)
```

### Connection Lifecycle

```python
class DatabaseManager:
    def __init__(self, config: ConnectionConfig):
        self.config = config
        self.pool = None
    
    def initialize_pool(self):
        """Initialize connection pool"""
        if self.pool is None:
            self.pool = create_pool(
                size=self.config.pool_size,
                timeout=self.config.pool_timeout
            )
    
    def cleanup_pool(self):
        """Cleanup pool connections"""
        if self.pool is not None:
            self.pool.dispose()
            self.pool = None
```

## Load Balancing

### Basic Load Balancing

```python
class LoadBalancer:
    def __init__(self, configs: List[ConnectionConfig]):
        self.configs = configs
        self.current = 0
    
    def get_next_config(self) -> ConnectionConfig:
        """Round-robin load balancing"""
        config = self.configs[self.current]
        self.current = (self.current + 1) % len(self.configs)
        return config

# Usage
def configure_with_load_balancing():
    balancer = LoadBalancer([
        ConnectionConfig(database='db1.sqlite'),
        ConnectionConfig(database='db2.sqlite'),
        ConnectionConfig(database='db3.sqlite')
    ])
    
    for model in [User, Post, Comment]:
        model.configure(balancer.get_next_config(), SQLiteBackend)
```

### Advanced Load Balancing

```python
class WeightedLoadBalancer:
    def __init__(self, configs: List[Tuple[ConnectionConfig, int]]):
        self.configs = configs  # List of (config, weight) tuples
        self.total_weight = sum(weight for _, weight in configs)
    
    def get_config(self) -> ConnectionConfig:
        """Weighted random selection"""
        r = random.uniform(0, self.total_weight)
        upto = 0
        
        for config, weight in self.configs:
            upto += weight
            if upto > r:
                return config
```

## Best Practices

1. **Pool Sizing**
   - Consider server resources
   - Monitor connection usage
   - Adjust based on workload
   - Set appropriate timeouts

2. **Connection Management**
   - Use context managers
   - Release connections promptly
   - Handle connection errors
   - Monitor pool health

3. **Configuration**
   - Use environment variables
   - Scale pools appropriately
   - Set connection timeouts
   - Configure connection recycling

4. **Monitoring**
   - Track pool statistics
   - Monitor connection usage
   - Watch for connection leaks
   - Log pool events

5. **Load Balancing**
   - Distribute connections evenly
   - Monitor server load
   - Implement failover
   - Balance read/write operations

## Next Steps

1. Study [Memory Management](memory_management.md)
2. Learn about [Query Optimization](query_optimization.md)
3. Explore [Performance Testing](performance_testing.md)