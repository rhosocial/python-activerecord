# Data Synchronization Strategies

> **❌ NOT IMPLEMENTED**: The data synchronization functionality described in this document is **not implemented**. This documentation describes planned functionality and is provided for future reference only. Current users should implement data synchronization at the application level. This feature may be developed in future releases with no guaranteed timeline. The API described in this document is subject to significant changes when implementation begins.

This document outlines various strategies for synchronizing data between multiple databases when using rhosocial ActiveRecord in a cross-database environment.

## Overview

Data synchronization is the process of maintaining data consistency across multiple database systems. In applications that use multiple databases, synchronization becomes essential to ensure that data remains consistent, accurate, and up-to-date across all systems.

rhosocial ActiveRecord provides several approaches to handle data synchronization between different databases, each with its own advantages and trade-offs.

## Common Synchronization Scenarios

### 1. Master-Slave Replication

In this scenario, one database serves as the master (primary) where all write operations occur, while one or more slave (replica) databases receive copies of the data for read operations.

```python
from rhosocial.activerecord import ConnectionManager, ActiveRecord

# Configure master and slave connections
ConnectionManager.configure('master', {
    'driver': 'mysql',
    'host': 'master-db.example.com',
    'database': 'app_data',
    'username': 'master_user',
    'password': 'master_password'
})

ConnectionManager.configure('slave', {
    'driver': 'mysql',
    'host': 'slave-db.example.com',
    'database': 'app_data',
    'username': 'slave_user',
    'password': 'slave_password'
})

# Base model that handles read/write splitting
class BaseModel(ActiveRecord):
    __abstract__ = True
    
    @classmethod
    def get_read_connection(cls):
        return ConnectionManager.get('slave')
    
    @classmethod
    def get_write_connection(cls):
        return ConnectionManager.get('master')
    
    @classmethod
    def find(cls, *args, **kwargs):
        # Use slave connection for reads
        with cls.using_connection(cls.get_read_connection()):
            return super().find(*args, **kwargs)
    
    def save(self, *args, **kwargs):
        # Use master connection for writes
        with self.using_connection(self.get_write_connection()):
            return super().save(*args, **kwargs)

# Application models inherit from BaseModel
class User(BaseModel):
    __tablename__ = 'users'
```

### 2. Dual-Write Pattern

In this pattern, the application writes data to multiple databases simultaneously to keep them in sync.

```python
class DualWriteModel(ActiveRecord):
    __abstract__ = True
    __primary_connection__ = 'primary_db'
    __secondary_connection__ = 'secondary_db'
    
    def save(self, *args, **kwargs):
        # Save to primary database
        with self.using_connection(ConnectionManager.get(self.__primary_connection__)):
            result = super().save(*args, **kwargs)
        
        # Save to secondary database
        try:
            with self.using_connection(ConnectionManager.get(self.__secondary_connection__)):
                # Create a copy of the model for the secondary database
                secondary_model = self.__class__()
                for field in self.get_fields():
                    setattr(secondary_model, field, getattr(self, field))
                secondary_model.save(*args, **kwargs)
        except Exception as e:
            # Log the error but don't fail the primary save
            import logging
            logging.error(f"Failed to save to secondary database: {e}")
        
        return result
```

### 3. Event-Based Synchronization

This approach uses events or message queues to propagate changes from one database to another asynchronously.

```python
from rhosocial.activerecord import ActiveRecord
import json
import redis

# Configure Redis for message queue
redis_client = redis.Redis(host='localhost', port=6379, db=0)

class EventSyncModel(ActiveRecord):
    __abstract__ = True
    
    def after_save(self):
        # Publish change event to Redis after saving
        event_data = {
            'model': self.__class__.__name__,
            'id': self.id,
            'action': 'save',
            'data': self.to_dict()
        }
        redis_client.publish('data_sync', json.dumps(event_data))
    
    def after_destroy(self):
        # Publish delete event to Redis after destroying
        event_data = {
            'model': self.__class__.__name__,
            'id': self.id,
            'action': 'destroy',
            'data': None
        }
        redis_client.publish('data_sync', json.dumps(event_data))

# Example consumer (would run in a separate process)
def sync_consumer():
    pubsub = redis_client.pubsub()
    pubsub.subscribe('data_sync')
    
    for message in pubsub.listen():
        if message['type'] == 'message':
            try:
                event = json.loads(message['data'])
                sync_to_secondary_database(event)
            except Exception as e:
                import logging
                logging.error(f"Failed to process sync event: {e}")

def sync_to_secondary_database(event):
    # Connect to secondary database and apply changes
    with ConnectionManager.using('secondary_db'):
        model_class = get_model_class(event['model'])
        
        if event['action'] == 'save':
            instance = model_class.find(event['id']) or model_class()
            for key, value in event['data'].items():
                setattr(instance, key, value)
            instance.save()
        
        elif event['action'] == 'destroy':
            instance = model_class.find(event['id'])
            if instance:
                instance.destroy()
```

## Batch Synchronization Strategies

### 1. Periodic Full Synchronization

This strategy involves periodically copying all data from one database to another.

```python
def full_sync_users():
    # Get all users from primary database
    with ConnectionManager.using('primary_db'):
        users = User.all()
        user_data = [user.to_dict() for user in users]
    
    # Update all users in secondary database
    with ConnectionManager.using('secondary_db'):
        # Optional: Clear existing data first
        User.delete_all()
        
        # Insert all users
        for data in user_data:
            user = User()
            for key, value in data.items():
                setattr(user, key, value)
            user.save()
```

### 2. Incremental Synchronization

This approach only synchronizes records that have changed since the last synchronization.

```python
class SyncableModel(ActiveRecord):
    __abstract__ = True
    
    # Add a last_updated timestamp to track changes
    def before_save(self):
        self.last_updated = datetime.datetime.now()

def incremental_sync(model_class, last_sync_time):
    # Get records updated since last sync
    with ConnectionManager.using('primary_db'):
        updated_records = model_class.where("last_updated > ?", last_sync_time).all()
        record_data = [record.to_dict() for record in updated_records]
    
    # Update records in secondary database
    with ConnectionManager.using('secondary_db'):
        for data in record_data:
            record = model_class.find(data['id']) or model_class()
            for key, value in data.items():
                setattr(record, key, value)
            record.save()
    
    # Return current time as the new last_sync_time
    return datetime.datetime.now()
```

## Change Data Capture (CDC)

Change Data Capture is a pattern that identifies and tracks changes to data in a database, then applies those changes to another database.

```python
# Example using database triggers for CDC
def setup_cdc_triggers():
    with ConnectionManager.using('primary_db'):
        # Create a changes tracking table
        ActiveRecord.execute_sql("""
        CREATE TABLE IF NOT EXISTS data_changes (
            id SERIAL PRIMARY KEY,
            table_name VARCHAR(255) NOT NULL,
            record_id INTEGER NOT NULL,
            operation VARCHAR(10) NOT NULL,
            changed_data JSONB,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        
        # Create a trigger function
        ActiveRecord.execute_sql("""
        CREATE OR REPLACE FUNCTION track_data_changes()
        RETURNS TRIGGER AS $$
        BEGIN
            IF (TG_OP = 'DELETE') THEN
                INSERT INTO data_changes (table_name, record_id, operation, changed_data)
                VALUES (TG_TABLE_NAME, OLD.id, 'DELETE', row_to_json(OLD));
                RETURN OLD;
            ELSIF (TG_OP = 'UPDATE') THEN
                INSERT INTO data_changes (table_name, record_id, operation, changed_data)
                VALUES (TG_TABLE_NAME, NEW.id, 'UPDATE', row_to_json(NEW));
                RETURN NEW;
            ELSIF (TG_OP = 'INSERT') THEN
                INSERT INTO data_changes (table_name, record_id, operation, changed_data)
                VALUES (TG_TABLE_NAME, NEW.id, 'INSERT', row_to_json(NEW));
                RETURN NEW;
            END IF;
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;
        """)
        
        # Apply the trigger to tables
        ActiveRecord.execute_sql("""
        CREATE TRIGGER users_changes
        AFTER INSERT OR UPDATE OR DELETE ON users
        FOR EACH ROW EXECUTE FUNCTION track_data_changes();
        """)

# Process CDC events
def process_cdc_events(last_processed_id=0):
    with ConnectionManager.using('primary_db'):
        changes = ActiveRecord.execute_sql("""
        SELECT * FROM data_changes 
        WHERE id > ? 
        ORDER BY id ASC
        """, last_processed_id).fetchall()
    
    with ConnectionManager.using('secondary_db'):
        for change in changes:
            table_name = change['table_name']
            record_id = change['record_id']
            operation = change['operation']
            data = change['changed_data']
            
            # Apply the change to the secondary database
            if operation == 'DELETE':
                ActiveRecord.execute_sql(f"DELETE FROM {table_name} WHERE id = ?", record_id)
            elif operation == 'INSERT':
                # Generate INSERT statement dynamically
                columns = ', '.join(data.keys())
                placeholders = ', '.join(['?'] * len(data))
                values = list(data.values())
                ActiveRecord.execute_sql(f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})", *values)
            elif operation == 'UPDATE':
                # Generate UPDATE statement dynamically
                set_clause = ', '.join([f"{key} = ?" for key in data.keys() if key != 'id'])
                values = [data[key] for key in data.keys() if key != 'id']
                values.append(record_id)
                ActiveRecord.execute_sql(f"UPDATE {table_name} SET {set_clause} WHERE id = ?", *values)
    
    # Return the ID of the last processed change
    return changes[-1]['id'] if changes else last_processed_id
```

## Conflict Resolution Strategies

When synchronizing data between databases, conflicts can occur. Here are some strategies to handle them:

### 1. Last-Write-Wins

```python
def resolve_conflict_last_write_wins(primary_record, secondary_record):
    # Compare timestamps and use the most recent version
    if primary_record.updated_at > secondary_record.updated_at:
        return primary_record
    else:
        return secondary_record
```

### 2. Primary Database Wins

```python
def resolve_conflict_primary_wins(primary_record, secondary_record):
    # Always use the primary database version
    return primary_record
```

### 3. Merge Strategy

```python
def resolve_conflict_merge(primary_record, secondary_record):
    # Create a new record with merged data
    merged_record = primary_record.__class__()
    
    # Copy all fields from primary record
    for field in primary_record.get_fields():
        setattr(merged_record, field, getattr(primary_record, field))
    
    # Override with non-null fields from secondary record
    for field in secondary_record.get_fields():
        if getattr(secondary_record, field) is not None:
            setattr(merged_record, field, getattr(secondary_record, field))
    
    return merged_record
```

## Monitoring and Error Handling

Proper monitoring and error handling are crucial for data synchronization:

```python
class SyncMonitor:
    def __init__(self):
        self.sync_errors = []
        self.last_sync_time = None
        self.records_synced = 0
    
    def record_sync_start(self):
        self.sync_start_time = datetime.datetime.now()
        self.records_synced = 0
        self.sync_errors = []
    
    def record_sync_success(self):
        self.last_sync_time = datetime.datetime.now()
        self.records_synced += 1
    
    def record_sync_error(self, record_id, error):
        self.sync_errors.append({
            'record_id': record_id,
            'error': str(error),
            'timestamp': datetime.datetime.now()
        })
    
    def get_sync_status(self):
        return {
            'last_sync_time': self.last_sync_time,
            'records_synced': self.records_synced,
            'error_count': len(self.sync_errors),
            'recent_errors': self.sync_errors[-10:] if self.sync_errors else []
        }

# Example usage
sync_monitor = SyncMonitor()

def sync_with_monitoring(model_class, last_sync_time):
    sync_monitor.record_sync_start()
    
    try:
        with ConnectionManager.using('primary_db'):
            updated_records = model_class.where("last_updated > ?", last_sync_time).all()
        
        for record in updated_records:
            try:
                with ConnectionManager.using('secondary_db'):
                    secondary_record = model_class.find(record.id) or model_class()
                    for field in record.get_fields():
                        setattr(secondary_record, field, getattr(record, field))
                    secondary_record.save()
                sync_monitor.record_sync_success()
            except Exception as e:
                sync_monitor.record_sync_error(record.id, e)
    
    except Exception as e:
        import logging
        logging.error(f"Sync process failed: {e}")
    
    return sync_monitor.get_sync_status()
```

## Best Practices for Data Synchronization

### 1. Use Idempotent Operations

Ensure that synchronization operations can be safely retried without causing duplicate data or other issues.

### 2. Implement Proper Error Handling

Log synchronization errors and implement retry mechanisms for failed operations.

### 3. Consider Performance Impact

Schedule intensive synchronization operations during off-peak hours to minimize impact on application performance.

### 4. Maintain Data Integrity

Use transactions where possible to ensure data integrity during synchronization.

### 5. Monitor Synchronization Processes

Implement monitoring to track synchronization status, lag, and errors.

## Conclusion

Data synchronization is a critical aspect of working with multiple databases in rhosocial ActiveRecord. By choosing the appropriate synchronization strategy and implementing proper error handling and monitoring, you can maintain consistent data across your database systems while minimizing the impact on application performance and user experience.