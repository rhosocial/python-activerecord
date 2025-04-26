# Applications in Microservice Architecture

This document explores how rhosocial ActiveRecord can be effectively utilized in microservice architectures, providing patterns, best practices, and implementation strategies.

## Introduction to Microservices with ActiveRecord

Microservice architecture is an approach to application development where a large application is built as a suite of small, independently deployable services. Each service runs in its own process and communicates with other services through well-defined APIs, typically HTTP-based RESTful interfaces or message queues.

rhosocial ActiveRecord offers several features that make it particularly well-suited for microservice implementations:

- **Lightweight and focused**: ActiveRecord provides just what you need for data persistence without unnecessary overhead
- **Database abstraction**: Allows different microservices to use different database technologies as needed
- **Transaction support**: Ensures data consistency within each microservice's domain
- **Asynchronous capabilities**: Supports non-blocking operations for responsive microservices

## Microservice Data Patterns with ActiveRecord

### Database-per-Service Pattern

In this pattern, each microservice has its own dedicated database, ensuring loose coupling and independent scalability.

```python
# Configuration for a specific microservice
from rhosocial.activerecord import ConnectionManager

# Each microservice configures its own database connection
ConnectionManager.configure({
    'default': {
        'driver': 'postgresql',
        'host': 'user-service-db',
        'database': 'user_service',
        'user': 'app_user',
        'password': 'secure_password'
    }
})
```

### API Composition Pattern

When data from multiple microservices needs to be combined, an API composition layer can use ActiveRecord to fetch and combine the data.

```python
class UserOrderCompositionService:
    async def get_user_with_orders(self, user_id):
        # Connect to user service database
        user_db = UserServiceConnection.get()
        user = await User.find_by_id(user_id).using(user_db).one()
        
        # Connect to order service database
        order_db = OrderServiceConnection.get()
        orders = await Order.find().where(Order.user_id == user_id).using(order_db).all()
        
        # Compose the result
        return {
            'user': user.to_dict(),
            'orders': [order.to_dict() for order in orders]
        }
```

### Event Sourcing with ActiveRecord

Event sourcing stores all changes to application state as a sequence of events, which ActiveRecord can efficiently persist and query.

```python
class EventStore(ActiveRecord):
    __tablename__ = 'events'
    
    id = PrimaryKeyField()
    aggregate_id = StringField()
    event_type = StringField()
    event_data = JSONField()
    created_at = TimestampField(auto_now_add=True)
    
    @classmethod
    async def append_event(cls, aggregate_id, event_type, data):
        event = cls(aggregate_id=aggregate_id, event_type=event_type, event_data=data)
        await event.save()
        # Publish event to message broker for other services
        await publish_event(event)
        
    @classmethod
    async def get_events_for_aggregate(cls, aggregate_id):
        return await cls.find().where(cls.aggregate_id == aggregate_id).order_by(cls.created_at).all()
```

## Cross-Service Transaction Management

Managing transactions across microservices is challenging. ActiveRecord can help implement patterns like the Saga pattern to maintain data consistency.

```python
class OrderSaga:
    async def create_order(self, user_id, product_ids, quantities):
        # Start a saga for order creation
        saga_id = generate_unique_id()
        
        try:
            # Step 1: Verify inventory
            inventory_result = await self.inventory_service.reserve_products(
                saga_id, product_ids, quantities)
            if not inventory_result['success']:
                return {'success': False, 'error': 'Insufficient inventory'}
                
            # Step 2: Create order
            order = await Order(user_id=user_id, status='pending').save()
            for i, product_id in enumerate(product_ids):
                await OrderItem(order_id=order.id, product_id=product_id, 
                               quantity=quantities[i]).save()
            
            # Step 3: Process payment
            payment_result = await self.payment_service.process_payment(
                saga_id, user_id, self.calculate_total(product_ids, quantities))
            if not payment_result['success']:
                # Compensating transaction: release inventory
                await self.inventory_service.release_products(saga_id, product_ids, quantities)
                await order.update(status='failed')
                return {'success': False, 'error': 'Payment failed'}
            
            # Complete order
            await order.update(status='completed')
            return {'success': True, 'order_id': order.id}
            
        except Exception as e:
            # Handle any unexpected errors with compensating transactions
            await self.rollback_saga(saga_id, product_ids, quantities)
            return {'success': False, 'error': str(e)}
```

## Service Discovery and Configuration

ActiveRecord can be configured dynamically based on service discovery mechanisms:

```python
class DatabaseConfigService:
    def __init__(self, service_registry_url):
        self.service_registry_url = service_registry_url
        
    async def configure_database_connections(self):
        # Get service configurations from registry
        registry_data = await self.fetch_service_registry()
        
        # Configure connections for each service
        for service_name, service_config in registry_data.items():
            if 'database' in service_config:
                ConnectionManager.configure({
                    service_name: service_config['database']
                })
                
    async def fetch_service_registry(self):
        # Implementation to fetch from service registry (e.g., Consul, etcd)
        pass
```

## Deployment Considerations

When deploying microservices that use ActiveRecord:

1. **Database Migrations**: Each service should manage its own database schema migrations
2. **Connection Pooling**: Configure appropriate connection pool sizes based on service load
3. **Health Checks**: Implement database health checks as part of service readiness probes
4. **Monitoring**: Set up monitoring for database performance metrics

```python
class HealthCheckService:
    @classmethod
    async def check_database_health(cls):
        try:
            # Simple query to check database connectivity
            result = await ActiveRecord.execute_raw("SELECT 1")
            return {'status': 'healthy', 'database': 'connected'}
        except Exception as e:
            return {'status': 'unhealthy', 'database': str(e)}
```

## Scaling Strategies

ActiveRecord supports various scaling strategies for microservices:

### Read Replicas

```python
ConnectionManager.configure({
    'orders': {
        'write': {
            'driver': 'postgresql',
            'host': 'orders-primary-db',
            'database': 'orders'
        },
        'read': [
            {
                'driver': 'postgresql',
                'host': 'orders-replica-1',
                'database': 'orders'
            },
            {
                'driver': 'postgresql',
                'host': 'orders-replica-2',
                'database': 'orders'
            }
        ]
    }
})

# Write operations use primary
await new_order.save()

# Read operations can use replicas
orders = await Order.find().using_read_replica().all()
```

### Sharding

```python
class ShardedUserService:
    def get_shard_for_user(self, user_id):
        # Simple sharding by user_id modulo number of shards
        shard_number = user_id % 4  # 4 shards
        return f'user_shard_{shard_number}'
    
    async def find_user(self, user_id):
        shard = self.get_shard_for_user(user_id)
        return await User.find_by_id(user_id).using(shard).one()
    
    async def create_user(self, user_data):
        # For new users, generate ID first to determine shard
        user_id = generate_user_id()
        shard = self.get_shard_for_user(user_id)
        
        user = User(id=user_id, **user_data)
        await user.save().using(shard)
        return user
```

## Real-World Example: E-commerce Microservices

Here's how ActiveRecord might be used in a microservice-based e-commerce platform:

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  User Service   │    │ Product Service  │    │  Order Service  │
│  (PostgreSQL)   │    │   (MongoDB)     │    │   (PostgreSQL)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
        │                      │                      │
        ▼                      ▼                      ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ User ActiveRecord│    │Product ActiveRec│    │Order ActiveRecord
│    Models       │    │    Models       │    │    Models       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
        │                      │                      │
        └──────────────┬──────────────┬──────────────┘
                       │              │
                       ▼              ▼
               ┌─────────────┐  ┌─────────────┐
               │  API Layer  │  │Message Broker│
               └─────────────┘  └─────────────┘
```

Each service uses ActiveRecord configured for its specific database needs, while maintaining a consistent data access pattern across the application.

## Conclusion

rhosocial ActiveRecord provides a flexible and powerful foundation for building microservice architectures. By leveraging its database abstraction, transaction support, and performance optimization features, developers can create robust, scalable, and maintainable microservice systems.

The patterns and examples provided in this document demonstrate how ActiveRecord can be adapted to various microservice scenarios, from simple database-per-service implementations to complex event-driven architectures with distributed transactions.