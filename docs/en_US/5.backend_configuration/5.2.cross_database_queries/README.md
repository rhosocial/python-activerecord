# Cross-database Queries

> **❌ NOT IMPLEMENTED**: The multiple database connection functionality (including master-slave configuration) described in this document is **not implemented**. This documentation describes planned functionality and is provided for future reference only. Current users should work with single database connections only. This feature may be developed in future releases with no guaranteed timeline. Cross-database transactions described here are theoretical concepts and **cannot achieve cross-database atomicity**.

> **⚠️ ASPIRATIONAL DOCUMENTATION**: This section covers planned functionality for working with multiple databases simultaneously in rhosocial ActiveRecord, including connecting to different database systems, integrating heterogeneous data sources, synchronizing data between databases, and handling transactions across multiple databases. **None of these features are currently available.**

## Contents

- [Cross-database Connection Configuration](connection_configuration.md)
- [Heterogeneous Data Source Integration](heterogeneous_data_source_integration.md)
- [Data Synchronization Strategies](data_synchronization_strategies.md)
- [Cross-database Transaction Handling](cross_database_transaction_handling.md)

## Cross-database Connection Configuration

rhosocial ActiveRecord allows you to configure and connect to multiple databases simultaneously, even if they are of different types. This capability is essential for applications that need to access data from various sources or that use different databases for different parts of the application.

### Configuring Multiple Database Connections

To work with multiple databases, you need to configure each connection separately and give each a unique name:

```python
from rhosocial.activerecord import ConnectionManager

# Configure primary database (SQLite)
primary_config = {
    'driver': 'sqlite',
    'database': 'main.db'
}

# Configure secondary database (PostgreSQL)
secondary_config = {
    'driver': 'postgresql',
    'host': 'localhost',
    'port': 5432,
    'database': 'analytics',
    'username': 'user',
    'password': 'password'
}

# Register connections with unique names
ConnectionManager.configure('primary', primary_config)
ConnectionManager.configure('secondary', secondary_config)
```

### Specifying the Database Connection in Models

Once you have configured multiple connections, you can specify which connection each model should use:

```python
from rhosocial.activerecord import ActiveRecord

class User(ActiveRecord):
    __connection__ = 'primary'  # Use the primary database
    # Model definition...

class AnalyticsData(ActiveRecord):
    __connection__ = 'secondary'  # Use the secondary database
    # Model definition...
```

### Switching Connections at Runtime

You can also switch database connections at runtime for specific operations:

```python
# Using the connection context manager
with User.using_connection('secondary'):
    # All User operations in this block will use the secondary connection
    users = User.all()

# Or using the connection method for a single query
users = User.using('secondary').all()
```

## Heterogeneous Data Source Integration

Integrating data from heterogeneous sources (different database systems) requires handling differences in SQL dialects, data types, and features.

### Cross-database Queries

rhosocial ActiveRecord abstracts away many database-specific differences, allowing you to write queries that work across different database systems:

```python
# This query will work regardless of whether User is in SQLite, MySQL, or PostgreSQL
active_users = User.where(status='active').order_by('created_at').limit(10).all()
```

However, when using database-specific features, you may need to check the database type:

```python
from rhosocial.activerecord import get_connection

conn = get_connection('primary')
if conn.dialect.name == 'postgresql':
    # Use PostgreSQL-specific features
    result = User.raw_query("SELECT * FROM users WHERE data @> '{"premium": true}'")
else:
    # Use a more generic approach for other databases
    result = User.where(premium=True).all()
```

### Working with Different Schema Structures

When integrating data from sources with different schema structures, you can use model inheritance and composition to create a unified interface:

```python
class LegacyUser(ActiveRecord):
    __connection__ = 'legacy_db'
    __tablename__ = 'old_users'
    # Legacy schema mapping...

class ModernUser(ActiveRecord):
    __connection__ = 'new_db'
    # Modern schema mapping...

class UnifiedUserService:
    def get_user_by_email(self, email):
        # Try modern database first
        user = ModernUser.where(email=email).first()
        if user:
            return self._convert_to_unified_format(user, 'modern')
        
        # Fall back to legacy database
        legacy_user = LegacyUser.where(email_address=email).first()
        if legacy_user:
            return self._convert_to_unified_format(legacy_user, 'legacy')
        
        return None
    
    def _convert_to_unified_format(self, user_obj, source):
        # Convert different user objects to a standard format
        # ...
```

## Data Synchronization Strategies

When working with multiple databases, you may need to synchronize data between them. rhosocial ActiveRecord provides several approaches for data synchronization.

### Batch Synchronization

For periodic synchronization of large datasets:

```python
def sync_users_to_analytics():
    # Get last sync timestamp
    last_sync = SyncLog.where(entity='users').order_by('-sync_time').first()
    last_sync_time = last_sync.sync_time if last_sync else None
    
    # Get users updated since last sync
    query = User.select('id', 'email', 'created_at', 'updated_at')
    if last_sync_time:
        query = query.where('updated_at > ?', last_sync_time)
    
    # Process in batches to avoid memory issues
    for batch in query.batch(1000):
        analytics_data = []
        for user in batch:
            analytics_data.append({
                'user_id': user.id,
                'email_domain': user.email.split('@')[1],
                'signup_date': user.created_at.date(),
                'last_update': user.updated_at
            })
        
        # Bulk insert/update to analytics database
        with AnalyticsUserData.using_connection('analytics'):
            AnalyticsUserData.bulk_insert_or_update(analytics_data, conflict_keys=['user_id'])
    
    # Update sync log
    SyncLog.create(entity='users', sync_time=datetime.now())
```

### Real-time Synchronization

For real-time synchronization, you can use event-driven approaches:

```python
class User(ActiveRecord):
    __connection__ = 'primary'
    
    def after_save(self):
        # Synchronize to analytics database after each save
        self._sync_to_analytics()
    
    def after_destroy(self):
        # Remove from analytics database when deleted
        with AnalyticsUserData.using_connection('analytics'):
            AnalyticsUserData.where(user_id=self.id).delete()
    
    def _sync_to_analytics(self):
        with AnalyticsUserData.using_connection('analytics'):
            analytics_data = {
                'user_id': self.id,
                'email_domain': self.email.split('@')[1],
                'signup_date': self.created_at.date(),
                'last_update': self.updated_at
            }
            AnalyticsUserData.insert_or_update(analytics_data, conflict_keys=['user_id'])
```

### Using Message Queues for Synchronization

For more robust synchronization, especially in distributed systems, you can use message queues:

```python
class User(ActiveRecord):
    __connection__ = 'primary'
    
    def after_save(self):
        # Publish change event to message queue
        self._publish_change_event('user_updated')
    
    def after_destroy(self):
        # Publish deletion event to message queue
        self._publish_change_event('user_deleted')
    
    def _publish_change_event(self, event_type):
        event_data = {
            'event': event_type,
            'user_id': self.id,
            'timestamp': datetime.now().isoformat(),
            'data': self.to_dict()
        }
        # Publish to message queue (implementation depends on your queue system)
        message_queue.publish('user_events', json.dumps(event_data))

# In a separate consumer process/service
def process_user_events():
    for event in message_queue.subscribe('user_events'):
        event_data = json.loads(event)
        
        if event_data['event'] == 'user_updated':
            with AnalyticsUserData.using_connection('analytics'):
                user_data = event_data['data']
                analytics_data = {
                    'user_id': user_data['id'],
                    'email_domain': user_data['email'].split('@')[1],
                    'signup_date': datetime.fromisoformat(user_data['created_at']).date(),
                    'last_update': datetime.fromisoformat(user_data['updated_at'])
                }
                AnalyticsUserData.insert_or_update(analytics_data, conflict_keys=['user_id'])
        
        elif event_data['event'] == 'user_deleted':
            with AnalyticsUserData.using_connection('analytics'):
                AnalyticsUserData.where(user_id=event_data['user_id']).delete()
```

## Cross-database Transaction Handling

> **⚠️ IMPORTANT NOTE:** Cross-database transactions described here are essentially nested transactions initiated by two separate ActiveRecord classes and **cannot achieve true cross-database atomicity**. The strategies described below are workarounds for this limitation.

Handling transactions across multiple databases is challenging because most database systems don't support distributed transactions natively. rhosocial ActiveRecord provides several strategies to manage cross-database operations.

### Two-Phase Commit Protocol

For critical operations that must be atomic across databases, you can implement a two-phase commit protocol:

```python
from rhosocial.activerecord import get_connection, Transaction

def transfer_user_data(user_id, from_db='legacy', to_db='modern'):
    # Phase 1: Prepare both databases
    from_conn = get_connection(from_db)
    to_conn = get_connection(to_db)
    
    try:
        # Start transactions on both connections
        from_tx = Transaction(from_conn)
        to_tx = Transaction(to_conn)
        
        # Get user data from source database
        with from_tx:
            user_data = LegacyUser.where(id=user_id).first()
            if not user_data:
                raise ValueError(f"User {user_id} not found in {from_db} database")
            
            # Mark as being migrated
            user_data.migration_status = 'in_progress'
            user_data.save()
        
        # Insert into destination database
        with to_tx:
            new_user = ModernUser()
            new_user.id = user_data.id
            new_user.email = user_data.email_address
            new_user.name = f"{user_data.first_name} {user_data.last_name}"
            new_user.created_at = user_data.creation_date
            new_user.save()
        
        # Phase 2: Commit both transactions
        from_tx.prepare()  # Prepare phase
        to_tx.prepare()
        
        from_tx.commit()  # Commit phase
        to_tx.commit()
        
        # Final update to mark migration as complete
        with Transaction(from_conn):
            user_data.migration_status = 'completed'
            user_data.save()
        
        return True
    
    except Exception as e:
        # If anything fails, try to rollback both transactions
        try:
            if 'from_tx' in locals():
                from_tx.rollback()
            if 'to_tx' in locals():
                to_tx.rollback()
        except:
            pass  # Best effort rollback
        
        # Log the error
        logger.error(f"Failed to transfer user {user_id}: {str(e)}")
        
        # Update status to failed if possible
        try:
            with Transaction(from_conn):
                user_data.migration_status = 'failed'
                user_data.save()
        except:
            pass  # Best effort status update
        
        return False
```

### Compensating Transactions

For operations where perfect atomicity isn't required, you can use compensating transactions:

```python
def create_user_with_analytics(user_data):
    # First, create the user in the primary database
    try:
        with Transaction(get_connection('primary')):
            user = User()
            user.email = user_data['email']
            user.name = user_data['name']
            user.save()
            
            # Store the new user ID for analytics
            user_id = user.id
    except Exception as e:
        logger.error(f"Failed to create user: {str(e)}")
        return None
    
    # Then, create analytics record in the secondary database
    try:
        with Transaction(get_connection('analytics')):
            analytics = UserAnalytics()
            analytics.user_id = user_id
            analytics.source = user_data.get('source', 'direct')
            analytics.signup_date = datetime.now()
            analytics.save()
    except Exception as e:
        # Compensating transaction: delete the user if analytics creation fails
        logger.error(f"Failed to create analytics for user {user_id}: {str(e)}")
        try:
            with Transaction(get_connection('primary')):
                User.where(id=user_id).delete()
            logger.info(f"Compensating transaction: deleted user {user_id}")
        except Exception as comp_error:
            logger.critical(f"Compensating transaction failed: {str(comp_error)}")
        return None
    
    return user_id
```

### Event-Driven Consistency

For systems where eventual consistency is acceptable, you can use an event-driven approach:

```python
def register_user(user_data):
    # Create user in primary database
    with Transaction(get_connection('primary')):
        user = User()
        user.email = user_data['email']
        user.name = user_data['name']
        user.save()
        
        # Record that analytics needs to be created
        pending_task = PendingTask()
        pending_task.task_type = 'create_user_analytics'
        pending_task.entity_id = user.id
        pending_task.data = json.dumps({
            'user_id': user.id,
            'source': user_data.get('source', 'direct'),
            'signup_date': datetime.now().isoformat()
        })
        pending_task.save()
    
    return user.id

# In a background process/worker
def process_pending_analytics_tasks():
    with Transaction(get_connection('primary')):
        tasks = PendingTask.where(task_type='create_user_analytics', status='pending').limit(100).all()
    
    for task in tasks:
        try:
            task_data = json.loads(task.data)
            
            with Transaction(get_connection('analytics')):
                analytics = UserAnalytics()
                analytics.user_id = task_data['user_id']
                analytics.source = task_data.get('source', 'direct')
                analytics.signup_date = datetime.fromisoformat(task_data['signup_date'])
                analytics.save()
            
            # Mark task as completed
            with Transaction(get_connection('primary')):
                task.status = 'completed'
                task.completed_at = datetime.now()
                task.save()
        
        except Exception as e:
            # Log error and increment retry count
            logger.error(f"Failed to process analytics task {task.id}: {str(e)}")
            
            with Transaction(get_connection('primary')):
                task.retry_count = (task.retry_count or 0) + 1
                task.last_error = str(e)
                
                if task.retry_count >= 5:
                    task.status = 'failed'
                
                task.save()
```

## Best Practices for Cross-database Operations

1. **Minimize Cross-database Transactions**: Whenever possible, design your application to avoid transactions that span multiple databases.

2. **Use Database-Specific Features Carefully**: Be aware of which features are database-specific and provide fallbacks for databases that don't support them.

3. **Consider Eventual Consistency**: For many applications, eventual consistency is sufficient and much easier to implement than strict cross-database atomicity.

4. **Monitor Synchronization Processes**: Implement monitoring and alerting for synchronization processes to detect and resolve issues quickly.

5. **Implement Idempotent Operations**: Design your synchronization operations to be idempotent so they can be safely retried in case of failures.

6. **Use Connection Pooling**: Configure appropriate connection pool settings for each database to optimize performance.

7. **Handle Database-Specific Errors**: Different databases may return different error codes for similar issues. Implement error handling that accounts for these differences.

8. **Test Cross-database Operations Thoroughly**: Cross-database operations can have complex failure modes. Test them thoroughly, including simulating network failures and database outages.