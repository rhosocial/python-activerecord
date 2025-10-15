# 跨数据库查询

> **❌ 未实现**：本文档中描述的多数据库连接功能（包括主从配置）**未实现**。此文档描述了计划中的功能，仅用于未来参考。当前用户应仅使用单个数据库连接。此功能可能会在未来版本中开发，但没有保证的时间表。

本节介绍如何在rhosocial ActiveRecord中同时使用多个数据库，包括连接不同的数据库系统、集成异构数据源、在数据库之间同步数据以及处理跨多个数据库的事务。**注意：这些功能目前非实现状态。**

## 目录

- [跨数据库连接配置](connection_configuration.md)
- [异构数据源集成](heterogeneous_data_source_integration.md)
- [数据同步策略](data_synchronization_strategies.md)
- [跨数据库事务处理](cross_database_transaction_handling.md)

## 跨数据库连接配置

rhosocial ActiveRecord允许您同时配置和连接多个数据库，即使它们是不同类型的数据库。这种能力对于需要访问来自各种来源的数据或者对应用程序的不同部分使用不同数据库的应用程序至关重要。

### 配置多个数据库连接

要使用多个数据库，您需要分别配置每个连接并为每个连接指定一个唯一的名称：

```python
from rhosocial.activerecord import ConnectionManager

# 配置主数据库（SQLite）
primary_config = {
    'driver': 'sqlite',
    'database': 'main.db'
}

# 配置辅助数据库（PostgreSQL）
secondary_config = {
    'driver': 'postgresql',
    'host': 'localhost',
    'port': 5432,
    'database': 'analytics',
    'username': 'user',
    'password': 'password'
}

# 使用唯一名称注册连接
ConnectionManager.configure('primary', primary_config)
ConnectionManager.configure('secondary', secondary_config)
```

### 在模型中指定数据库连接

一旦您配置了多个连接，您可以指定每个模型应该使用哪个连接：

```python
from rhosocial.activerecord import ActiveRecord

class User(ActiveRecord):
    __connection__ = 'primary'  # 使用主数据库
    # 模型定义...

class AnalyticsData(ActiveRecord):
    __connection__ = 'secondary'  # 使用辅助数据库
    # 模型定义...
```

### 在运行时切换连接

您还可以在运行时为特定操作切换数据库连接：

```python
# 使用连接上下文管理器
with User.using_connection('secondary'):
    # 此块中的所有User操作将使用辅助连接
    users = User.all()

# 或者使用连接方法进行单个查询
users = User.using('secondary').all()
```

## 异构数据源集成

集成来自异构源（不同数据库系统）的数据需要处理SQL方言、数据类型和功能的差异。

### 跨数据库查询

rhosocial ActiveRecord抽象了许多特定于数据库的差异，允许您编写适用于不同数据库系统的查询：

```python
# 无论User是在SQLite、MySQL还是PostgreSQL中，此查询都将有效
active_users = User.where(status='active').order_by('created_at').limit(10).all()
```

然而，当使用特定于数据库的功能时，您可能需要检查数据库类型：

```python
from rhosocial.activerecord import get_connection

conn = get_connection('primary')
if conn.dialect.name == 'postgresql':
    # 使用PostgreSQL特定功能
    result = User.raw_query("SELECT * FROM users WHERE data @> '{"premium": true}'")
else:
    # 为其他数据库使用更通用的方法
    result = User.where(premium=True).all()
```

### 处理不同的模式结构

当集成来自具有不同模式结构的源的数据时，您可以使用模型继承和组合来创建统一的接口：

```python
class LegacyUser(ActiveRecord):
    __connection__ = 'legacy_db'
    __tablename__ = 'old_users'
    # 旧版模式映射...

class ModernUser(ActiveRecord):
    __connection__ = 'new_db'
    # 现代模式映射...

class UnifiedUserService:
    def get_user_by_email(self, email):
        # 首先尝试现代数据库
        user = ModernUser.where(email=email).first()
        if user:
            return self._convert_to_unified_format(user, 'modern')
        
        # 回退到旧版数据库
        legacy_user = LegacyUser.where(email_address=email).first()
        if legacy_user:
            return self._convert_to_unified_format(legacy_user, 'legacy')
        
        return None
    
    def _convert_to_unified_format(self, user_obj, source):
        # 将不同的用户对象转换为标准格式
        # ...
```

## 数据同步策略

当使用多个数据库时，您可能需要在它们之间同步数据。rhosocial ActiveRecord提供了几种数据同步方法。

### 批量同步

对于大型数据集的定期同步：

```python
def sync_users_to_analytics():
    # 获取上次同步时间戳
    last_sync = SyncLog.where(entity='users').order_by('-sync_time').first()
    last_sync_time = last_sync.sync_time if last_sync else None
    
    # 获取自上次同步以来更新的用户
    query = User.select('id', 'email', 'created_at', 'updated_at')
    if last_sync_time:
        query = query.where('updated_at > ?', last_sync_time)
    
    # 分批处理以避免内存问题
    for batch in query.batch(1000):
        analytics_data = []
        for user in batch:
            analytics_data.append({
                'user_id': user.id,
                'email_domain': user.email.split('@')[1],
                'signup_date': user.created_at.date(),
                'last_update': user.updated_at
            })
        
        # 批量插入/更新到分析数据库
        with AnalyticsUserData.using_connection('analytics'):
            AnalyticsUserData.bulk_insert_or_update(analytics_data, conflict_keys=['user_id'])
    
    # 更新同步日志
    SyncLog.create(entity='users', sync_time=datetime.now())
```

### 实时同步

对于实时同步，您可以使用事件驱动的方法：

```python
class User(ActiveRecord):
    __connection__ = 'primary'
    
    def after_save(self):
        # 每次保存后同步到分析数据库
        self._sync_to_analytics()
    
    def after_destroy(self):
        # 删除时从分析数据库中移除
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

### 使用消息队列进行同步

对于更强大的同步，特别是在分布式系统中，您可以使用消息队列：

```python
class User(ActiveRecord):
    __connection__ = 'primary'
    
    def after_save(self):
        # 将更改事件发布到消息队列
        self._publish_change_event('user_updated')
    
    def after_destroy(self):
        # 将删除事件发布到消息队列
        self._publish_change_event('user_deleted')
    
    def _publish_change_event(self, event_type):
        event_data = {
            'event': event_type,
            'user_id': self.id,
            'timestamp': datetime.now().isoformat(),
            'data': self.to_dict()
        }
        # 发布到消息队列（实现取决于您的队列系统）
        message_queue.publish('user_events', json.dumps(event_data))

# 在单独的消费者进程/服务中
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

## 跨数据库事务处理

处理跨多个数据库的事务是具有挑战性的，因为大多数数据库系统本身不支持分布式事务。rhosocial ActiveRecord提供了几种策略来管理跨数据库操作。

### 两阶段提交协议

对于必须在数据库之间保持原子性的关键操作，您可以实现两阶段提交协议：

```python
from rhosocial.activerecord import get_connection, Transaction

def transfer_user_data(user_id, from_db='legacy', to_db='modern'):
    # 阶段1：准备两个数据库
    from_conn = get_connection(from_db)
    to_conn = get_connection(to_db)
    
    try:
        # 在两个连接上开始事务
        from_tx = Transaction(from_conn)
        to_tx = Transaction(to_conn)
        
        # 从源数据库获取用户数据
        with from_tx:
            user_data = LegacyUser.where(id=user_id).first()
            if not user_data:
                raise ValueError(f"在{from_db}数据库中未找到用户{user_id}")
            
            # 标记为正在迁移
            user_data.migration_status = 'in_progress'
            user_data.save()
        
        # 插入到目标数据库
        with to_tx:
            new_user = ModernUser()
            new_user.id = user_data.id
            new_user.email = user_data.email_address
            new_user.name = f"{user_data.first_name} {user_data.last_name}"
            new_user.created_at = user_data.creation_date
            new_user.save()
        
        # 阶段2：提交两个事务
        from_tx.prepare()  # 准备阶段
        to_tx.prepare()
        
        from_tx.commit()  # 提交阶段
        to_tx.commit()
        
        # 最终更新以标记迁移完成
        with Transaction(from_conn):
            user_data.migration_status = 'completed'
            user_data.save()
        
        return True
    
    except Exception as e:
        # 如果任何操作失败，尝试回滚两个事务
        try:
            if 'from_tx' in locals():
                from_tx.rollback()
            if 'to_tx' in locals():
                to_tx.rollback()
        except:
            pass  # 尽力回滚
        
        # 记录错误
        logger.error(f"转移用户{user_id}失败：{str(e)}")
        
        # 如果可能，更新状态为失败
        try:
            with Transaction(from_conn):
                user_data.migration_status = 'failed'
                user_data.save()
        except:
            pass  # 尽力更新状态
        
        return False
```

### 补偿事务

对于不需要完美原子性的操作，您可以使用补偿事务：

```python
def create_user_with_analytics(user_data):
    # 首先，在主数据库中创建用户
    try:
        with Transaction(get_connection('primary')):
            user = User()
            user.email = user_data['email']
            user.name = user_data['name']
            user.save()
            
            # 存储新用户ID用于分析
            user_id = user.id
    except Exception as e:
        logger.error(f"创建用户失败：{str(e)}")
        return None
    
    # 然后，在辅助数据库中创建分析记录
    try:
        with Transaction(get_connection('analytics')):
            analytics = UserAnalytics()
            analytics.user_id = user_id
            analytics.source = user_data.get('source', 'direct')
            analytics.signup_date = datetime.now()
            analytics.save()
    except Exception as e:
        # 补偿事务：如果分析创建失败，删除用户
        logger.error(f"为用户{user_id}创建分析失败：{str(e)}")
        try:
            with Transaction(get_connection('primary')):
                User.where(id=user_id).delete()
            logger.info(f"补偿事务：已删除用户{user_id}")
        except Exception as comp_error:
            logger.critical(f"补偿事务失败：{str(comp_error)}")
        return None
    
    return user_id
```

### 事件驱动一致性

对于可以接受最终一致性的系统，您可以使用事件驱动的方法：

```python
def register_user(user_data):
    # 在主数据库中创建用户
    with Transaction(get_connection('primary')):
        user = User()
        user.email = user_data['email']
        user.name = user_data['name']
        user.save()
        
        # 记录需要创建分析的任务
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

# 在后台进程/工作者中
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
            
            # 标记任务为已完成
            with Transaction(get_connection('primary')):
                task.status = 'completed'
                task.completed_at = datetime.now()
                task.save()
        
        except Exception as e:
            # 记录错误并增加重试计数
            logger.error(f"处理分析任务{task.id}失败：{str(e)}")
            
            with Transaction(get_connection('primary')):
                task.retry_count = (task.retry_count or 0) + 1
                task.last_error = str(e)
                
                if task.retry_count >= 5:
                    task.status = 'failed'
                
                task.save()
```

## 跨数据库操作的最佳实践

1. **最小化跨数据库事务**：尽可能设计您的应用程序以避免跨越多个数据库的事务。

2. **谨慎使用特定于数据库的功能**：了解哪些功能是特定于数据库的，并为不支持这些功能的数据库提供备选方案。

3. **考虑最终一致性**：对于许多应用程序，最终一致性已经足够，并且比严格的跨数据库原子性更容易实现。

4. **监控同步过程**：为同步过程实现监控和警报，以快速检测和解决问题。

5. **实现幂等操作**：设计您的同步操作为幂等的，这样在失败的情况下可以安全地重试。

6. **使用连接池**：为每个数据库配置适当的连接池设置以优化性能。

7. **处理特定于数据库的错误**：不同的数据库可能会为类似的问题返回不同的错误代码。实现考虑到这些差异的错误处理。

8. **彻底测试跨数据库操作**：跨数据库操作可能有复杂的失败模式。彻底测试它们，包括模拟网络故障和数据库中断。