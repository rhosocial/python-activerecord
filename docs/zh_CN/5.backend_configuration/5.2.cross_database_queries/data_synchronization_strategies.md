# 数据同步策略

> **❌ 未实现**：本文档中描述的数据同步功能**未实现**。此文档描述了计划中的功能，仅用于未来参考。当前用户应在应用程序级别实现数据同步。此功能可能会在未来版本中开发，但没有保证的时间表。

本文档概述了在使用rhosocial ActiveRecord进行跨数据库环境时，在多个数据库之间同步数据的各种策略。**注意：这些功能目前非实现状态。**

## 概述

数据同步是在多个数据库系统之间保持数据一致性的过程。在使用多个数据库的应用程序中，同步变得至关重要，以确保数据在所有系统中保持一致、准确和最新。

rhosocial ActiveRecord提供了几种处理不同数据库之间数据同步的方法，每种方法都有其自身的优势和权衡。

## 常见同步场景

### 1. 主从复制

在这种场景中，一个数据库作为主数据库（主要），所有写操作都在这里进行，而一个或多个从数据库（副本）接收数据副本用于读操作。

```python
from rhosocial.activerecord import ConnectionManager, ActiveRecord

# 配置主从连接
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

# 处理读/写分离的基础模型
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
        # 使用从连接进行读取
        with cls.using_connection(cls.get_read_connection()):
            return super().find(*args, **kwargs)
    
    def save(self, *args, **kwargs):
        # 使用主连接进行写入
        with self.using_connection(self.get_write_connection()):
            return super().save(*args, **kwargs)

# 应用程序模型继承自BaseModel
class User(BaseModel):
    __tablename__ = 'users'
```

### 2. 双写模式

在这种模式中，应用程序同时向多个数据库写入数据以保持它们同步。

```python
class DualWriteModel(ActiveRecord):
    __abstract__ = True
    __primary_connection__ = 'primary_db'
    __secondary_connection__ = 'secondary_db'
    
    def save(self, *args, **kwargs):
        # 保存到主数据库
        with self.using_connection(ConnectionManager.get(self.__primary_connection__)):
            result = super().save(*args, **kwargs)
        
        # 保存到辅助数据库
        try:
            with self.using_connection(ConnectionManager.get(self.__secondary_connection__)):
                # 为辅助数据库创建模型副本
                secondary_model = self.__class__()
                for field in self.get_fields():
                    setattr(secondary_model, field, getattr(self, field))
                secondary_model.save(*args, **kwargs)
        except Exception as e:
            # 记录错误但不使主保存失败
            import logging
            logging.error(f"保存到辅助数据库失败: {e}")
        
        return result
```

### 3. 基于事件的同步

这种方法使用事件或消息队列异步地将更改从一个数据库传播到另一个数据库。

```python
from rhosocial.activerecord import ActiveRecord
import json
import redis

# 配置Redis作为消息队列
redis_client = redis.Redis(host='localhost', port=6379, db=0)

class EventSyncModel(ActiveRecord):
    __abstract__ = True
    
    def after_save(self):
        # 保存后将更改事件发布到Redis
        event_data = {
            'model': self.__class__.__name__,
            'id': self.id,
            'action': 'save',
            'data': self.to_dict()
        }
        redis_client.publish('data_sync', json.dumps(event_data))
    
    def after_destroy(self):
        # 销毁后将删除事件发布到Redis
        event_data = {
            'model': self.__class__.__name__,
            'id': self.id,
            'action': 'destroy',
            'data': None
        }
        redis_client.publish('data_sync', json.dumps(event_data))

# 示例消费者（将在单独的进程中运行）
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
                logging.error(f"处理同步事件失败: {e}")

def sync_to_secondary_database(event):
    # 连接到辅助数据库并应用更改
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

## 批量同步策略

### 1. 定期全量同步

这种策略涉及定期将所有数据从一个数据库复制到另一个数据库。

```python
def full_sync_users():
    # 从主数据库获取所有用户
    with ConnectionManager.using('primary_db'):
        users = User.all()
        user_data = [user.to_dict() for user in users]
    
    # 在辅助数据库中更新所有用户
    with ConnectionManager.using('secondary_db'):
        # 可选：首先清除现有数据
        User.delete_all()
        
        # 插入所有用户
        for data in user_data:
            user = User()
            for key, value in data.items():
                setattr(user, key, value)
            user.save()
```

### 2. 增量同步

这种方法只同步自上次同步以来已更改的记录。

```python
class SyncableModel(ActiveRecord):
    __abstract__ = True
    
    # 添加last_updated时间戳来跟踪更改
    def before_save(self):
        self.last_updated = datetime.datetime.now()

def incremental_sync(model_class, last_sync_time):
    # 获取自上次同步以来更新的记录
    with ConnectionManager.using('primary_db'):
        updated_records = model_class.where("last_updated > ?", last_sync_time).all()
        record_data = [record.to_dict() for record in updated_records]
    
    # 在辅助数据库中更新记录
    with ConnectionManager.using('secondary_db'):
        for data in record_data:
            record = model_class.find(data['id']) or model_class()
            for key, value in data.items():
                setattr(record, key, value)
            record.save()
    
    # 返回当前时间作为新的last_sync_time
    return datetime.datetime.now()
```

## 变更数据捕获 (CDC)

变更数据捕获是一种模式，用于识别和跟踪数据库中数据的变更，然后将这些变更应用到另一个数据库。

```python
# 使用数据库触发器进行CDC的示例
def setup_cdc_triggers():
    with ConnectionManager.using('primary_db'):
        # 创建变更跟踪表
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
        
        # 创建触发器函数
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
        
        # 将触发器应用到表
        ActiveRecord.execute_sql("""
        CREATE TRIGGER users_changes
        AFTER INSERT OR UPDATE OR DELETE ON users
        FOR EACH ROW EXECUTE FUNCTION track_data_changes();
        """)

# 处理CDC事件
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
            
            # 将变更应用到辅助数据库
            if operation == 'DELETE':
                ActiveRecord.execute_sql(f"DELETE FROM {table_name} WHERE id = ?", record_id)
            elif operation == 'INSERT':
                # 动态生成INSERT语句
                columns = ', '.join(data.keys())
                placeholders = ', '.join(['?'] * len(data))
                values = list(data.values())
                ActiveRecord.execute_sql(f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders})", *values)
            elif operation == 'UPDATE':
                # 动态生成UPDATE语句
                set_clause = ', '.join([f"{key} = ?" for key in data.keys() if key != 'id'])
                values = [data[key] for key in data.keys() if key != 'id']
                values.append(record_id)
                ActiveRecord.execute_sql(f"UPDATE {table_name} SET {set_clause} WHERE id = ?", *values)
    
    # 返回最后处理的变更的ID
    return changes[-1]['id'] if changes else last_processed_id
```

## 冲突解决策略

在数据库之间同步数据时，可能会发生冲突。以下是一些处理冲突的策略：

### 1. 最后写入胜出

```python
def resolve_conflict_last_write_wins(primary_record, secondary_record):
    # 比较时间戳并使用最新版本
    if primary_record.updated_at > secondary_record.updated_at:
        return primary_record
    else:
        return secondary_record
```

### 2. 主数据库胜出

```python
def resolve_conflict_primary_wins(primary_record, secondary_record):
    # 始终使用主数据库版本
    return primary_record
```

### 3. 合并策略

```python
def resolve_conflict_merge(primary_record, secondary_record):
    # 创建一个包含合并数据的新记录
    merged_record = primary_record.__class__()
    
    # 从主记录复制所有字段
    for field in primary_record.get_fields():
        setattr(merged_record, field, getattr(primary_record, field))
    
    # 用辅助记录中的非空字段覆盖
    for field in secondary_record.get_fields():
        if getattr(secondary_record, field) is not None:
            setattr(merged_record, field, getattr(secondary_record, field))
    
    return merged_record
```

## 监控和错误处理

适当的监控和错误处理对于数据同步至关重要：

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

# 使用示例
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
        logging.error(f"同步过程失败: {e}")
    
    return sync_monitor.get_sync_status()
```

## 数据同步的最佳实践

### 1. 使用幂等操作

确保同步操作可以安全地重试，而不会导致重复数据或其他问题。

### 2. 实施适当的错误处理

记录同步错误并为失败的操作实施重试机制。

### 3. 考虑性能影响

在非高峰时段安排密集型同步操作，以最小化对应用程序性能的影响。

### 4. 维护数据完整性

尽可能使用事务来确保同步过程中的数据完整性。

### 5. 监控同步过程

实施监控以跟踪同步状态、延迟和错误。

## 结论

数据同步是在rhosocial ActiveRecord中使用多个数据库的关键方面。通过选择适当的同步策略并实施适当的错误处理和监控，您可以在数据库系统之间保持一致的数据，同时最小化对应用程序性能和用户体验的影响。