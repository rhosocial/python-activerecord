# 企业数据库集成

本文档探讨了将rhosocial ActiveRecord与企业数据库系统集成的策略和技术，解决了企业环境中的常见挑战，并为企业环境提供了实用的解决方案。

## 企业数据库集成简介

企业环境通常具有复杂的数据库生态系统，包括多个数据库系统、遗留数据库和专业数据存储。rhosocial ActiveRecord提供了强大的功能，可以与这些多样化的系统集成，同时保持一致的编程接口。

## 关键集成场景

### 遗留数据库集成

许多企业维护着需要与现代应用集成的遗留数据库。ActiveRecord可以连接到这些系统，同时提供现代接口。

```python
# 连接到遗留Oracle数据库
from rhosocial.activerecord import ConnectionManager

ConnectionManager.configure({
    'legacy_system': {
        'driver': 'oracle',
        'host': 'legacy-oracle-server',
        'port': 1521,
        'service_name': 'LEGACYDB',
        'user': 'app_user',
        'password': 'secure_password',
        # 遗留系统兼容性的特殊选项
        'options': {
            'nls_lang': 'AMERICAN_AMERICA.WE8MSWIN1252',
            'mode': 'SYSDBA'
        }
    }
})

# 定义映射到遗留表的模型
class LegacyCustomer(ActiveRecord):
    __tablename__ = 'CUST_MASTER'  # 遗留表名
    __connection__ = 'legacy_system'
    
    # 将现代字段名映射到遗留列名
    id = PrimaryKeyField(db_column='CUST_ID')
    name = StringField(db_column='CUST_NAME')
    status = StringField(db_column='CUST_STATUS_CD')
    created_date = DateField(db_column='CUST_CREATE_DT')
    
    # 处理遗留状态代码
    def get_status_description(self):
        status_map = {
            'A': '活跃',
            'I': '不活跃',
            'P': '待处理',
            'S': '已暂停'
        }
        return status_map.get(self.status, '未知')
```

### 多数据库事务

企业应用通常需要协调跨多个数据库系统的事务。ActiveRecord提供了管理这些复杂场景的工具。

```python
from rhosocial.activerecord import TransactionManager

async def transfer_data_between_systems():
    # 启动分布式事务
    async with TransactionManager.begin_distributed(['erp_system', 'crm_system']) as tx:
        try:
            # 从ERP系统获取数据
            erp_orders = await Order.find().where(Order.status == 'new').using('erp_system').all()
            
            # 处理并插入到CRM系统
            for order in erp_orders:
                customer = await Customer.find_by_id(order.customer_id).using('crm_system').one()
                
                # 在CRM中创建活动记录
                activity = CustomerActivity(
                    customer_id=customer.id,
                    activity_type='new_order',
                    details={
                        'order_id': order.id,
                        'order_amount': float(order.total_amount),
                        'order_date': order.created_at.isoformat()
                    }
                )
                await activity.save().using('crm_system')
                
                # 在ERP中更新订单状态
                await order.update(status='processed').using('erp_system')
                
            # 如果一切成功，事务将被提交
        except Exception as e:
            # 出错时，事务将在两个系统中回滚
            print(f"传输过程中出错: {e}")
            raise
```

### 数据仓库集成

ActiveRecord可用于高效地提取、转换和加载数据到企业数据仓库。

```python
class DataWarehouseETL:
    def __init__(self):
        # 配置源系统和目标系统的连接
        self.source_systems = ['sales', 'inventory', 'customer']
        self.target = 'data_warehouse'
    
    async def extract_from_source(self, source, last_etl_time):
        # 从上次ETL运行以来提取更改的数据
        if source == 'sales':
            return await SalesOrder.find()\
                .where(SalesOrder.updated_at > last_etl_time)\
                .using(source)\
                .all()
        elif source == 'inventory':
            return await InventoryItem.find()\
                .where(InventoryItem.updated_at > last_etl_time)\
                .using(source)\
                .all()
        # ... 其他源
    
    def transform_sales_data(self, sales_data):
        # 转换销售数据为仓库格式
        transformed = []
        for order in sales_data:
            # 创建事实表记录
            for item in order.items:
                transformed.append({
                    'order_id': order.id,
                    'product_id': item.product_id,
                    'customer_id': order.customer_id,
                    'date_key': self.date_to_key(order.order_date),
                    'quantity': item.quantity,
                    'unit_price': float(item.unit_price),
                    'total_price': float(item.total_price),
                    'discount': float(item.discount)
                })
        return transformed
    
    async def load_to_warehouse(self, table_name, transformed_data):
        # 批量插入到数据仓库
        if table_name == 'sales_fact':
            await SalesFact.bulk_create(
                [SalesFact(**data) for data in transformed_data],
                using=self.target
            )
        # ... 其他表
    
    async def run_etl_job(self):
        last_etl_time = await self.get_last_etl_time()
        
        for source in self.source_systems:
            # 提取
            source_data = await self.extract_from_source(source, last_etl_time)
            
            # 转换
            if source == 'sales':
                transformed_data = self.transform_sales_data(source_data)
                await self.load_to_warehouse('sales_fact', transformed_data)
            # ... 处理其他源
        
        # 更新ETL作业元数据
        await self.update_etl_metadata()
```

## 企业集成模式

### 联邦模式

联邦模式允许ActiveRecord呈现物理上分布在多个数据库中的数据的统一视图。

```python
class FederatedCustomerView:
    """提供来自多个系统的客户数据统一视图的服务"""
    
    async def get_customer_profile(self, customer_id):
        # 并行收集来自多个系统的客户数据
        tasks = [
            self.get_core_customer_data(customer_id),
            self.get_customer_orders(customer_id),
            self.get_customer_support_tickets(customer_id),
            self.get_customer_marketing_data(customer_id)
        ]
        
        results = await asyncio.gather(*tasks)
        
        # 将结果组合成统一的客户资料
        return {
            'core_data': results[0],
            'orders': results[1],
            'support': results[2],
            'marketing': results[3]
        }
    
    async def get_core_customer_data(self, customer_id):
        return await Customer.find_by_id(customer_id).using('crm_system').one_or_none()
    
    async def get_customer_orders(self, customer_id):
        return await Order.find()\
            .where(Order.customer_id == customer_id)\
            .order_by(Order.created_at.desc())\
            .limit(10)\
            .using('order_system')\
            .all()
    
    # 其他数据源的附加方法
```

### 变更数据捕获 (CDC)

ActiveRecord可用于实现CDC模式，用于跟踪和传播企业系统间的数据库变更。

```python
class ChangeTracker(ActiveRecord):
    __tablename__ = 'change_log'
    
    id = PrimaryKeyField()
    table_name = StringField()
    record_id = StringField()
    operation = StringField()  # INSERT, UPDATE, DELETE
    changed_data = JSONField()
    created_at = TimestampField(auto_now_add=True)
    processed = BooleanField(default=False)
    
    @classmethod
    async def log_change(cls, table_name, record_id, operation, data):
        change = cls(
            table_name=table_name,
            record_id=str(record_id),
            operation=operation,
            changed_data=data
        )
        await change.save()

# 带有变更跟踪的ActiveRecord模型示例
class Product(ActiveRecord):
    __tablename__ = 'products'
    
    id = PrimaryKeyField()
    name = StringField()
    price = DecimalField()
    stock = IntegerField()
    updated_at = TimestampField(auto_now=True)
    
    async def after_save(self):
        # 为CDC记录变更
        await ChangeTracker.log_change(
            table_name=self.__tablename__,
            record_id=self.id,
            operation='UPDATE' if self.id else 'INSERT',
            data=self.to_dict()
        )
    
    async def after_delete(self):
        await ChangeTracker.log_change(
            table_name=self.__tablename__,
            record_id=self.id,
            operation='DELETE',
            data={'id': self.id}
        )

# 将变更传播到其他系统的CDC处理器
class CDCProcessor:
    async def process_pending_changes(self):
        # 查找未处理的变更
        changes = await ChangeTracker.find()\
            .where(ChangeTracker.processed == False)\
            .order_by(ChangeTracker.created_at)\
            .limit(100)\
            .all()
        
        for change in changes:
            # 根据表和操作进行处理
            if change.table_name == 'products':
                await self.sync_product_change(change)
            # ... 处理其他表
            
            # 标记为已处理
            await change.update(processed=True)
    
    async def sync_product_change(self, change):
        # 同步到其他系统，如库存、电子商务平台等
        if change.operation in ('INSERT', 'UPDATE'):
            # 更新电子商务系统中的产品
            await self.ecommerce_api.update_product(
                product_id=change.record_id,
                product_data=change.changed_data
            )
            
            # 更新库存系统
            if 'stock' in change.changed_data:
                await self.inventory_api.update_stock(
                    product_id=change.record_id,
                    stock=change.changed_data['stock']
                )
        
        elif change.operation == 'DELETE':
            # 从其他系统中移除
            await self.ecommerce_api.delete_product(change.record_id)
```

## 企业数据库安全集成

ActiveRecord可以与企业安全框架集成，以实施数据访问控制。

```python
from enterprise_security import SecurityContext, AccessControl

class SecureActiveRecord(ActiveRecord):
    """与企业安全框架集成的基类"""
    
    @classmethod
    async def find(cls, *args, **kwargs):
        query = await super().find(*args, **kwargs)
        
        # 根据当前用户上下文应用安全过滤器
        security_context = SecurityContext.get_current()
        if security_context:
            # 添加行级安全谓词
            access_predicates = AccessControl.get_predicates_for_table(
                cls.__tablename__, security_context.user_id, security_context.roles)
            
            if access_predicates:
                for predicate in access_predicates:
                    query = query.where(predicate)
        
        return query
    
    async def before_save(self):
        # 检查写入权限
        security_context = SecurityContext.get_current()
        if security_context:
            has_permission = await AccessControl.check_write_permission(
                self.__tablename__, 
                self.id if hasattr(self, 'id') and self.id else None,
                security_context.user_id,
                security_context.roles
            )
            
            if not has_permission:
                raise PermissionError(f"没有{self.__tablename__}的写入权限")

# 使用安全基类的示例
class EmployeeRecord(SecureActiveRecord):
    __tablename__ = 'employee_records'
    
    id = PrimaryKeyField()
    employee_id = StringField()
    department_id = StringField()
    salary = DecimalField()
    performance_rating = IntegerField()
    notes = TextField()
```

## 与企业监控和可观察性的集成

ActiveRecord可以配置为与企业监控系统集成，以跟踪数据库性能和问题。

```python
from rhosocial.activerecord import ConnectionManager
from enterprise_monitoring import MetricsCollector, LogAggregator

# 配置带有监控钩子的ActiveRecord
ConnectionManager.configure({
    'erp_system': {
        'driver': 'postgresql',
        'host': 'erp-db-server',
        'database': 'erp_production',
        'user': 'app_user',
        'password': 'secure_password',
        'monitoring': {
            'query_logger': LogAggregator('erp_database_queries'),
            'metrics_collector': MetricsCollector('erp_database_metrics'),
            'slow_query_threshold': 1.0,  # 秒
            'log_level': 'WARNING'
        }
    }
})

# 自定义查询监控器
class QueryPerformanceMonitor:
    def __init__(self, connection_name):
        self.connection_name = connection_name
        self.metrics = MetricsCollector(f"{connection_name}_query_metrics")
    
    async def __aenter__(self):
        self.start_time = time.time()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        self.metrics.record_duration(duration)
        
        if exc_type is not None:
            self.metrics.record_error(exc_type.__name__)
            LogAggregator(f"{self.connection_name}_errors").log(
                level="ERROR",
                message=f"数据库错误: {exc_val}",
                context={
                    "exception": exc_type.__name__,
                    "duration": duration
                }
            )

# 使用监控的示例
async def get_critical_business_data():
    async with QueryPerformanceMonitor('erp_system'):
        return await BusinessData.find().where(BusinessData.is_critical == True).all()
```

## 实际案例：企业资源规划(ERP)集成

以下是ActiveRecord如何用于与企业ERP系统的各个组件集成的示例：

```
┌─────────────────────────────────────────────────────────────────┐
│                      ERP系统集成                                 │
└─────────────────────────────────────────────────────────────────┘
                               │
           ┌──────────────────┼──────────────────┐
           │                  │                  │
           ▼                  ▼                  ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│   财务模块      │  │    人力资源模块 │  │   库存模块      │
│   (Oracle DB)   │  │  (SQL Server)  │  │  (PostgreSQL)   │
└─────────────────┘  └─────────────────┘  └─────────────────┘
           │                  │                  │
           ▼                  ▼                  ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│财务ActiveRecord │  │人力ActiveRecord │  │库存ActiveRecord │
│     模型        │  │     模型       │  │     模型        │
└─────────────────┘  └─────────────────┘  └─────────────────┘
           │                  │                  │
           └──────────────────┼──────────────────┘
                              │
                              ▼
                     ┌─────────────────┐
                     │   集成层        │
                     │ (ActiveRecord   │
                     │    联邦)        │
                     └─────────────────┘
                              │
           ┌──────────────────┼──────────────────┐
           │                  │                  │
           ▼                  ▼                  ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│   报表与        │  │  商业智能      │  │  外部系统       │
│   分析          │  │    仪表板      │  │    集成         │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

## 结论

rhosocial ActiveRecord为企业数据库集成提供了坚实的基础，提供了解决企业环境独特挑战的功能。通过利用ActiveRecord的灵活性、事务支持和可扩展性，开发人员可以创建与多样化企业数据库系统的可靠集成。

本文档中的模式和示例演示了ActiveRecord如何适应各种企业集成场景，从遗留系统集成到跨多个数据库的复杂数据同步。这些方法帮助组织在现代化其数据访问模式的同时保持数据一致性和可靠性。