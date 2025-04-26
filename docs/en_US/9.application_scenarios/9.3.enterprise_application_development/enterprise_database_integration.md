# Enterprise Database Integration

This document explores strategies and techniques for integrating rhosocial ActiveRecord with enterprise database systems, addressing common challenges and providing practical solutions for enterprise environments.

## Introduction to Enterprise Database Integration

Enterprise environments often feature complex database ecosystems with multiple database systems, legacy databases, and specialized data stores. rhosocial ActiveRecord provides robust capabilities for integrating with these diverse systems while maintaining a consistent programming interface.

## Key Integration Scenarios

### Legacy Database Integration

Many enterprises maintain legacy databases that need to be integrated with modern applications. ActiveRecord can connect to these systems while providing a modern interface.

```python
# Connecting to a legacy Oracle database
from rhosocial.activerecord import ConnectionManager

ConnectionManager.configure({
    'legacy_system': {
        'driver': 'oracle',
        'host': 'legacy-oracle-server',
        'port': 1521,
        'service_name': 'LEGACYDB',
        'user': 'app_user',
        'password': 'secure_password',
        # Special options for legacy system compatibility
        'options': {
            'nls_lang': 'AMERICAN_AMERICA.WE8MSWIN1252',
            'mode': 'SYSDBA'
        }
    }
})

# Define a model that maps to a legacy table
class LegacyCustomer(ActiveRecord):
    __tablename__ = 'CUST_MASTER'  # Legacy table name
    __connection__ = 'legacy_system'
    
    # Map modern field names to legacy column names
    id = PrimaryKeyField(db_column='CUST_ID')
    name = StringField(db_column='CUST_NAME')
    status = StringField(db_column='CUST_STATUS_CD')
    created_date = DateField(db_column='CUST_CREATE_DT')
    
    # Handle legacy status codes
    def get_status_description(self):
        status_map = {
            'A': 'Active',
            'I': 'Inactive',
            'P': 'Pending',
            'S': 'Suspended'
        }
        return status_map.get(self.status, 'Unknown')
```

### Multi-Database Transactions

Enterprise applications often need to coordinate transactions across multiple database systems. ActiveRecord provides tools for managing these complex scenarios.

```python
from rhosocial.activerecord import TransactionManager

async def transfer_data_between_systems():
    # Start a distributed transaction
    async with TransactionManager.begin_distributed(['erp_system', 'crm_system']) as tx:
        try:
            # Fetch data from ERP system
            erp_orders = await Order.find().where(Order.status == 'new').using('erp_system').all()
            
            # Process and insert into CRM system
            for order in erp_orders:
                customer = await Customer.find_by_id(order.customer_id).using('crm_system').one()
                
                # Create activity record in CRM
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
                
                # Update order status in ERP
                await order.update(status='processed').using('erp_system')
                
            # If everything succeeds, the transaction will be committed
        except Exception as e:
            # On error, the transaction will be rolled back in both systems
            print(f"Error during transfer: {e}")
            raise
```

### Data Warehouse Integration

ActiveRecord can be used to efficiently extract, transform, and load data into enterprise data warehouses.

```python
class DataWarehouseETL:
    def __init__(self):
        # Configure connections to source and target systems
        self.source_systems = ['sales', 'inventory', 'customer']
        self.target = 'data_warehouse'
    
    async def extract_from_source(self, source, last_etl_time):
        # Extract changed data since last ETL run
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
        # ... other sources
    
    def transform_sales_data(self, sales_data):
        # Transform sales data for warehouse format
        transformed = []
        for order in sales_data:
            # Create fact table records
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
        # Bulk insert into data warehouse
        if table_name == 'sales_fact':
            await SalesFact.bulk_create(
                [SalesFact(**data) for data in transformed_data],
                using=self.target
            )
        # ... other tables
    
    async def run_etl_job(self):
        last_etl_time = await self.get_last_etl_time()
        
        for source in self.source_systems:
            # Extract
            source_data = await self.extract_from_source(source, last_etl_time)
            
            # Transform
            if source == 'sales':
                transformed_data = self.transform_sales_data(source_data)
                await self.load_to_warehouse('sales_fact', transformed_data)
            # ... handle other sources
        
        # Update ETL job metadata
        await self.update_etl_metadata()
```

## Enterprise Integration Patterns

### Federation Pattern

The federation pattern allows ActiveRecord to present a unified view of data that's physically distributed across multiple databases.

```python
class FederatedCustomerView:
    """A service that provides a unified view of customer data from multiple systems"""
    
    async def get_customer_profile(self, customer_id):
        # Gather customer data from multiple systems in parallel
        tasks = [
            self.get_core_customer_data(customer_id),
            self.get_customer_orders(customer_id),
            self.get_customer_support_tickets(customer_id),
            self.get_customer_marketing_data(customer_id)
        ]
        
        results = await asyncio.gather(*tasks)
        
        # Combine results into a unified customer profile
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
    
    # Additional methods for other data sources
```

### Change Data Capture (CDC)

ActiveRecord can be used to implement CDC patterns for tracking and propagating database changes across enterprise systems.

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

# Example ActiveRecord model with change tracking
class Product(ActiveRecord):
    __tablename__ = 'products'
    
    id = PrimaryKeyField()
    name = StringField()
    price = DecimalField()
    stock = IntegerField()
    updated_at = TimestampField(auto_now=True)
    
    async def after_save(self):
        # Log changes for CDC
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

# CDC processor that propagates changes to other systems
class CDCProcessor:
    async def process_pending_changes(self):
        # Find unprocessed changes
        changes = await ChangeTracker.find()\
            .where(ChangeTracker.processed == False)\
            .order_by(ChangeTracker.created_at)\
            .limit(100)\
            .all()
        
        for change in changes:
            # Process based on table and operation
            if change.table_name == 'products':
                await self.sync_product_change(change)
            # ... handle other tables
            
            # Mark as processed
            await change.update(processed=True)
    
    async def sync_product_change(self, change):
        # Sync to other systems like inventory, e-commerce platform, etc.
        if change.operation in ('INSERT', 'UPDATE'):
            # Update product in e-commerce system
            await self.ecommerce_api.update_product(
                product_id=change.record_id,
                product_data=change.changed_data
            )
            
            # Update inventory system
            if 'stock' in change.changed_data:
                await self.inventory_api.update_stock(
                    product_id=change.record_id,
                    stock=change.changed_data['stock']
                )
        
        elif change.operation == 'DELETE':
            # Remove from other systems
            await self.ecommerce_api.delete_product(change.record_id)
```

## Enterprise Database Security Integration

ActiveRecord can be integrated with enterprise security frameworks to enforce data access controls.

```python
from enterprise_security import SecurityContext, AccessControl

class SecureActiveRecord(ActiveRecord):
    """Base class that integrates with enterprise security framework"""
    
    @classmethod
    async def find(cls, *args, **kwargs):
        query = await super().find(*args, **kwargs)
        
        # Apply security filters based on current user context
        security_context = SecurityContext.get_current()
        if security_context:
            # Add row-level security predicates
            access_predicates = AccessControl.get_predicates_for_table(
                cls.__tablename__, security_context.user_id, security_context.roles)
            
            if access_predicates:
                for predicate in access_predicates:
                    query = query.where(predicate)
        
        return query
    
    async def before_save(self):
        # Check write permissions
        security_context = SecurityContext.get_current()
        if security_context:
            has_permission = await AccessControl.check_write_permission(
                self.__tablename__, 
                self.id if hasattr(self, 'id') and self.id else None,
                security_context.user_id,
                security_context.roles
            )
            
            if not has_permission:
                raise PermissionError(f"No write permission for {self.__tablename__}")

# Example usage with secure base class
class EmployeeRecord(SecureActiveRecord):
    __tablename__ = 'employee_records'
    
    id = PrimaryKeyField()
    employee_id = StringField()
    department_id = StringField()
    salary = DecimalField()
    performance_rating = IntegerField()
    notes = TextField()
```

## Integration with Enterprise Monitoring and Observability

ActiveRecord can be configured to integrate with enterprise monitoring systems to track database performance and issues.

```python
from rhosocial.activerecord import ConnectionManager
from enterprise_monitoring import MetricsCollector, LogAggregator

# Configure ActiveRecord with monitoring hooks
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
            'slow_query_threshold': 1.0,  # seconds
            'log_level': 'WARNING'
        }
    }
})

# Custom query monitor
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
                message=f"Database error: {exc_val}",
                context={
                    "exception": exc_type.__name__,
                    "duration": duration
                }
            )

# Usage with monitoring
async def get_critical_business_data():
    async with QueryPerformanceMonitor('erp_system'):
        return await BusinessData.find().where(BusinessData.is_critical == True).all()
```

## Real-World Example: Enterprise Resource Planning (ERP) Integration

Here's an example of how ActiveRecord might be used to integrate with various components of an enterprise ERP system:

```
┌─────────────────────────────────────────────────────────────────┐
│                      ERP System Integration                      │
└─────────────────────────────────────────────────────────────────┘
                               │
           ┌──────────────────┼──────────────────┐
           │                  │                  │
           ▼                  ▼                  ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│  Finance Module │  │   HR Module    │  │ Inventory Module│
│   (Oracle DB)   │  │  (SQL Server)  │  │  (PostgreSQL)   │
└─────────────────┘  └─────────────────┘  └─────────────────┘
           │                  │                  │
           ▼                  ▼                  ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│Finance ActiveRec│  │   HR ActiveRec │  │Inventory ActiveR│
│    Models       │  │    Models      │  │    Models       │
└─────────────────┘  └─────────────────┘  └─────────────────┘
           │                  │                  │
           └──────────────────┼──────────────────┘
                              │
                              ▼
                     ┌─────────────────┐
                     │ Integration Layer│
                     │ (ActiveRecord   │
                     │  Federation)    │
                     └─────────────────┘
                              │
           ┌──────────────────┼──────────────────┐
           │                  │                  │
           ▼                  ▼                  ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│  Reporting &    │  │ Business Intel. │  │ External System │
│   Analytics     │  │    Dashboard    │  │   Integration   │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

## Conclusion

rhosocial ActiveRecord provides a robust foundation for enterprise database integration, offering features that address the unique challenges of enterprise environments. By leveraging ActiveRecord's flexibility, transaction support, and extensibility, developers can create reliable integrations with diverse enterprise database systems.

The patterns and examples in this document demonstrate how ActiveRecord can be adapted to various enterprise integration scenarios, from legacy system integration to complex data synchronization across multiple databases. These approaches help organizations maintain data consistency and reliability while modernizing their data access patterns.