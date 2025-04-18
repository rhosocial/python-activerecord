# ETL Process Implementation

This document explores how to leverage rhosocial ActiveRecord for implementing Extract, Transform, Load (ETL) processes in command-line environments.

## Introduction

ETL (Extract, Transform, Load) processes are essential for data integration, migration, and warehousing operations. rhosocial ActiveRecord provides a robust ORM framework that simplifies database interactions in ETL workflows, allowing developers to create maintainable and efficient data pipelines.

## ETL Process Overview

A typical ETL process consists of three main stages:

1. **Extract**: Retrieving data from various source systems
2. **Transform**: Cleaning, validating, and restructuring the data
3. **Load**: Writing the transformed data to target systems

rhosocial ActiveRecord can be effectively utilized in all three stages, particularly when databases are involved as sources or targets.

## Implementing ETL with ActiveRecord

### Basic ETL Pipeline

Here's a simple example of an ETL process using ActiveRecord:

```python
import sys
from rhosocial.activerecord import ActiveRecord, Field
from rhosocial.activerecord.backend import SQLiteBackend, MySQLBackend

# Source model (Extract)
class SourceCustomer(ActiveRecord):
    table_name = 'customers'
    id = Field(int, primary_key=True)
    name = Field(str)
    email = Field(str)
    address = Field(str)
    created_at = Field(str)

# Target model (Load)
class TargetCustomer(ActiveRecord):
    table_name = 'customer_dim'
    id = Field(int, primary_key=True)
    full_name = Field(str)
    email = Field(str)
    address_line = Field(str)
    city = Field(str)
    state = Field(str)
    postal_code = Field(str)
    created_date = Field(str)

# Setup connections
source_db = SQLiteBackend('source.sqlite')
SourceCustomer.connect(source_db)

target_db = MySQLBackend(host='localhost', database='data_warehouse', 
                         user='etl_user', password='password')
TargetCustomer.connect(target_db)

def extract_transform_load():
    # Extract data from source
    source_customers = SourceCustomer.find_all()
    
    # Process in batches for better performance
    batch_size = 100
    processed_count = 0
    
    # Use transaction for better performance and data integrity
    with TargetCustomer.transaction():
        for source_customer in source_customers:
            # Transform data
            target_customer = TargetCustomer()
            target_customer.id = source_customer.id
            target_customer.full_name = source_customer.name
            target_customer.email = source_customer.email
            
            # Address transformation (parsing components)
            address_parts = parse_address(source_customer.address)
            target_customer.address_line = address_parts.get('line', '')
            target_customer.city = address_parts.get('city', '')
            target_customer.state = address_parts.get('state', '')
            target_customer.postal_code = address_parts.get('postal_code', '')
            
            # Date transformation
            target_customer.created_date = source_customer.created_at.split(' ')[0]
            
            # Load data to target
            if target_customer.save():
                processed_count += 1
            else:
                print(f"Error saving customer {source_customer.id}: {target_customer.errors}")
            
            # Report progress periodically
            if processed_count % batch_size == 0:
                print(f"Processed {processed_count} customers")
    
    print(f"ETL process completed: {processed_count} customers processed")

def parse_address(address_string):
    # Simple address parser (in real scenarios, use a proper address parsing library)
    parts = {}
    try:
        # This is a simplified example - real address parsing is more complex
        components = address_string.split(', ')
        parts['line'] = components[0]
        parts['city'] = components[1] if len(components) > 1 else ''
        
        if len(components) > 2:
            state_zip = components[2].split(' ')
            parts['state'] = state_zip[0]
            parts['postal_code'] = state_zip[1] if len(state_zip) > 1 else ''
    except Exception as e:
        print(f"Error parsing address '{address_string}': {e}")
    
    return parts

if __name__ == '__main__':
    extract_transform_load()
```

### Incremental ETL

In many cases, you'll want to implement incremental ETL to process only new or changed data since the last run:

```python
import datetime
import json
import os
from rhosocial.activerecord import ActiveRecord, Field
from rhosocial.activerecord.backend import PostgreSQLBackend, MySQLBackend

# Source model
class SourceOrder(ActiveRecord):
    table_name = 'orders'
    id = Field(int, primary_key=True)
    customer_id = Field(int)
    order_date = Field(str)
    total_amount = Field(float)
    status = Field(str)
    last_updated = Field(str)  # Timestamp for tracking changes

# Target model
class TargetOrder(ActiveRecord):
    table_name = 'order_fact'
    order_id = Field(int, primary_key=True)
    customer_id = Field(int)
    order_date = Field(str)
    order_amount = Field(float)
    order_status = Field(str)
    etl_timestamp = Field(str)  # When this record was processed

# Setup connections
source_db = PostgreSQLBackend(host='source-db.example.com', database='sales', 
                             user='reader', password='password')
SourceOrder.connect(source_db)

target_db = MySQLBackend(host='target-db.example.com', database='data_warehouse', 
                        user='etl_user', password='password')
TargetOrder.connect(target_db)

# State file to track last run
STATE_FILE = 'etl_state.json'

def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, 'r') as f:
            return json.load(f)
    return {'last_run': None}

def save_state(state):
    with open(STATE_FILE, 'w') as f:
        json.dump(state, f)

def incremental_etl():
    # Load state from previous run
    state = load_state()
    last_run = state.get('last_run')
    
    # Current timestamp for this run
    current_run = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    print(f"Starting incremental ETL at {current_run}")
    print(f"Last successful run: {last_run if last_run else 'Never'}")
    
    # Extract only new/changed records since last run
    if last_run:
        source_orders = SourceOrder.find_all(
            conditions=["last_updated > ?", last_run],
            order="id"
        )
    else:
        # First run - process all records
        source_orders = SourceOrder.find_all(order="id")
    
    print(f"Found {len(source_orders)} orders to process")
    
    # Process records
    processed_count = 0
    error_count = 0
    
    with TargetOrder.transaction():
        for source_order in source_orders:
            try:
                # Check if record already exists in target
                target_order = TargetOrder.find_by_order_id(source_order.id)
                
                if not target_order:
                    target_order = TargetOrder()
                    target_order.order_id = source_order.id
                
                # Transform and load data
                target_order.customer_id = source_order.customer_id
                target_order.order_date = source_order.order_date
                target_order.order_amount = source_order.total_amount
                target_order.order_status = source_order.status
                target_order.etl_timestamp = current_run
                
                if target_order.save():
                    processed_count += 1
                else:
                    error_count += 1
                    print(f"Error saving order {source_order.id}: {target_order.errors}")
            
            except Exception as e:
                error_count += 1
                print(f"Error processing order {source_order.id}: {e}")
    
    # Update state if successful
    if error_count == 0:
        state['last_run'] = current_run
        save_state(state)
    
    print(f"ETL process completed: {processed_count} orders processed, {error_count} errors")
    return error_count == 0

if __name__ == '__main__':
    success = incremental_etl()
    sys.exit(0 if success else 1)
```

## Advanced ETL Techniques

### Data Validation and Cleansing

Implementing data validation and cleansing as part of the transformation phase:

```python
from rhosocial.activerecord import ActiveRecord, Field

class DataValidator:
    @staticmethod
    def validate_email(email):
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None
    
    @staticmethod
    def validate_phone(phone):
        import re
        # Remove non-numeric characters
        digits_only = re.sub(r'\D', '', phone)
        # Check if it has a valid length
        return 10 <= len(digits_only) <= 15
    
    @staticmethod
    def clean_text(text):
        if not text:
            return ''
        # Remove extra whitespace
        cleaned = ' '.join(text.split())
        # Remove special characters if needed
        # cleaned = re.sub(r'[^\w\s]', '', cleaned)
        return cleaned

# Usage in ETL process
def transform_customer_data(source_customer):
    target_customer = TargetCustomer()
    
    # Clean and validate data
    target_customer.full_name = DataValidator.clean_text(source_customer.name)
    
    # Validate email
    if source_customer.email and DataValidator.validate_email(source_customer.email):
        target_customer.email = source_customer.email.lower()
    else:
        target_customer.email = None
        log_validation_error(source_customer.id, 'Invalid email format')
    
    # Validate phone
    if source_customer.phone and DataValidator.validate_phone(source_customer.phone):
        target_customer.phone = standardize_phone_format(source_customer.phone)
    else:
        target_customer.phone = None
        log_validation_error(source_customer.id, 'Invalid phone format')
    
    return target_customer

def log_validation_error(customer_id, error_message):
    # Log validation errors for later review
    print(f"Validation error for customer {customer_id}: {error_message}")
    # In a real system, you might log to a database or file
```

### Parallel ETL Processing

For large datasets, implement parallel processing to improve performance:

```python
import multiprocessing
import time
from rhosocial.activerecord import ActiveRecord, Field

# Setup models and connections as before

def process_batch(batch_ids):
    # Create a new database connection for this process
    source_db = PostgreSQLBackend(host='source-db.example.com', database='sales', 
                                user='reader', password='password')
    target_db = MySQLBackend(host='target-db.example.com', database='data_warehouse', 
                            user='etl_user', password='password')
    
    # Connect models to these connections
    SourceOrder.connect(source_db)
    TargetOrder.connect(target_db)
    
    results = {'processed': 0, 'errors': 0}
    
    with TargetOrder.transaction():
        for order_id in batch_ids:
            try:
                source_order = SourceOrder.find_by_id(order_id)
                if not source_order:
                    results['errors'] += 1
                    continue
                
                # Transform and load as before
                target_order = TargetOrder.find_by_order_id(order_id) or TargetOrder()
                target_order.order_id = source_order.id
                # ... other transformations
                
                if target_order.save():
                    results['processed'] += 1
                else:
                    results['errors'] += 1
            except Exception as e:
                results['errors'] += 1
                print(f"Error processing order {order_id}: {e}")
    
    return results

def parallel_etl():
    start_time = time.time()
    
    # Get all order IDs to process
    order_ids = [order.id for order in SourceOrder.find_all(select='id')]
    total_orders = len(order_ids)
    
    print(f"Starting parallel ETL for {total_orders} orders")
    
    # Determine optimal batch size and process count
    cpu_count = multiprocessing.cpu_count()
    process_count = min(cpu_count, 8)  # Limit to avoid too many DB connections
    batch_size = max(100, total_orders // (process_count * 10))
    
    # Split into batches
    batches = [order_ids[i:i + batch_size] for i in range(0, total_orders, batch_size)]
    
    # Process in parallel
    total_processed = 0
    total_errors = 0
    
    with multiprocessing.Pool(processes=process_count) as pool:
        results = pool.map(process_batch, batches)
        
        # Aggregate results
        for result in results:
            total_processed += result['processed']
            total_errors += result['errors']
    
    elapsed_time = time.time() - start_time
    print(f"ETL completed in {elapsed_time:.2f} seconds")
    print(f"Processed: {total_processed}, Errors: {total_errors}")
    
    return total_errors == 0

if __name__ == '__main__':
    success = parallel_etl()
    sys.exit(0 if success else 1)
```

### ETL Monitoring and Logging

Implement comprehensive logging and monitoring for ETL processes:

```python
import logging
import time
from datetime import datetime
from rhosocial.activerecord import ActiveRecord, Field

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f"etl_{datetime.now().strftime('%Y%m%d')}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("etl_process")

class ETLMetrics(ActiveRecord):
    table_name = 'etl_metrics'
    id = Field(int, primary_key=True)
    job_name = Field(str)
    start_time = Field(str)
    end_time = Field(str)
    records_processed = Field(int)
    records_failed = Field(int)
    execution_time_seconds = Field(float)
    status = Field(str)  # 'success', 'failed', 'running'

# Connect to monitoring database
monitoring_db = SQLiteBackend('etl_monitoring.sqlite')
ETLMetrics.connect(monitoring_db)

def run_etl_with_monitoring(job_name, etl_function):
    # Create metrics record
    metrics = ETLMetrics()
    metrics.job_name = job_name
    metrics.start_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    metrics.status = 'running'
    metrics.save()
    
    logger.info(f"Starting ETL job: {job_name}")
    start_time = time.time()
    
    records_processed = 0
    records_failed = 0
    status = 'failed'
    
    try:
        # Run the actual ETL process
        result = etl_function()
        
        # Update metrics based on result
        if isinstance(result, dict):
            records_processed = result.get('processed', 0)
            records_failed = result.get('failed', 0)
            status = 'success' if result.get('success', False) else 'failed'
        elif isinstance(result, bool):
            status = 'success' if result else 'failed'
        else:
            status = 'success'
            
    except Exception as e:
        logger.error(f"ETL job failed with error: {e}", exc_info=True)
        status = 'failed'
    finally:
        # Calculate execution time
        execution_time = time.time() - start_time
        
        # Update metrics record
        metrics.end_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        metrics.records_processed = records_processed
        metrics.records_failed = records_failed
        metrics.execution_time_seconds = execution_time
        metrics.status = status
        metrics.save()
        
        logger.info(f"ETL job {job_name} completed with status: {status}")
        logger.info(f"Processed: {records_processed}, Failed: {records_failed}, Time: {execution_time:.2f}s")
    
    return status == 'success'

# Example usage
def customer_etl_process():
    # Implementation of customer ETL
    # ...
    return {'processed': 1250, 'failed': 5, 'success': True}

if __name__ == '__main__':
    success = run_etl_with_monitoring('customer_etl', customer_etl_process)
    sys.exit(0 if success else 1)
```

## ETL Workflow Orchestration

For complex ETL pipelines with multiple stages, implement workflow orchestration:

```python
import time
import logging
from rhosocial.activerecord import ActiveRecord, Field

logger = logging.getLogger("etl_workflow")

class ETLWorkflow:
    def __init__(self, name):
        self.name = name
        self.steps = []
        self.current_step = 0
    
    def add_step(self, name, function, depends_on=None):
        self.steps.append({
            'name': name,
            'function': function,
            'depends_on': depends_on,
            'status': 'pending',
            'result': None
        })
        return self
    
    def run(self):
        logger.info(f"Starting ETL workflow: {self.name}")
        start_time = time.time()
        
        success = True
        for i, step in enumerate(self.steps):
            self.current_step = i
            
            # Check dependencies
            if step['depends_on']:
                dependency_index = self._find_step_index(step['depends_on'])
                if dependency_index >= 0 and self.steps[dependency_index]['status'] != 'success':
                    logger.warning(f"Skipping step '{step['name']}' because dependency '{step['depends_on']}' failed or was skipped")
                    step['status'] = 'skipped'
                    success = False
                    continue
            
            # Run the step
            logger.info(f"Running step {i+1}/{len(self.steps)}: {step['name']}")
            step_start = time.time()
            
            try:
                step['result'] = step['function']()
                step_success = True
                
                # Check result if it's a boolean or dict with success key
                if isinstance(step['result'], bool):
                    step_success = step['result']
                elif isinstance(step['result'], dict) and 'success' in step['result']:
                    step_success = step['result']['success']
                
                step['status'] = 'success' if step_success else 'failed'
                if not step_success:
                    success = False
                    
            except Exception as e:
                logger.error(f"Step '{step['name']}' failed with error: {e}", exc_info=True)
                step['status'] = 'failed'
                step['result'] = str(e)
                success = False
            
            step_time = time.time() - step_start
            logger.info(f"Step '{step['name']}' completed with status: {step['status']} in {step_time:.2f}s")
        
        total_time = time.time() - start_time
        logger.info(f"ETL workflow '{self.name}' completed in {total_time:.2f}s with overall status: {'success' if success else 'failed'}")
        
        return success
    
    def _find_step_index(self, step_name):
        for i, step in enumerate(self.steps):
            if step['name'] == step_name:
                return i
        return -1

# Example usage
def extract_customers():
    logger.info("Extracting customer data")
    # Implementation
    return {'success': True, 'count': 1000}

def transform_customers():
    logger.info("Transforming customer data")
    # Implementation
    return {'success': True, 'count': 950}

def load_customers():
    logger.info("Loading customer data to target")
    # Implementation
    return {'success': True, 'count': 950}

def extract_orders():
    logger.info("Extracting order data")
    # Implementation
    return {'success': True, 'count': 5000}

def transform_orders():
    logger.info("Transforming order data")
    # Implementation
    return {'success': True, 'count': 4980}

def load_orders():
    logger.info("Loading order data to target")
    # Implementation
    return {'success': True, 'count': 4980}

def update_data_mart():
    logger.info("Updating data mart views")
    # Implementation
    return {'success': True}

if __name__ == '__main__':
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Create and run workflow
    workflow = ETLWorkflow("Daily Data Warehouse Update")
    
    # Add steps with dependencies
    workflow.add_step("Extract Customers", extract_customers)
    workflow.add_step("Transform Customers", transform_customers, depends_on="Extract Customers")
    workflow.add_step("Load Customers", load_customers, depends_on="Transform Customers")
    
    workflow.add_step("Extract Orders", extract_orders)
    workflow.add_step("Transform Orders", transform_orders, depends_on="Extract Orders")
    workflow.add_step("Load Orders", load_orders, depends_on="Transform Orders")
    
    # This step depends on both customer and order data being loaded
    workflow.add_step("Update Data Mart", update_data_mart, depends_on="Load Orders")
    
    # Run the workflow
    success = workflow.run()
    sys.exit(0 if success else 1)
```

## Conclusion

rhosocial ActiveRecord provides a powerful foundation for implementing ETL processes, offering a clean, object-oriented approach to database interactions. By leveraging ActiveRecord's ORM capabilities, developers can create maintainable, efficient, and robust ETL pipelines that handle complex data transformation requirements.

The examples in this document demonstrate various ETL patterns and techniques, from basic data movement to advanced workflow orchestration. As you develop your own ETL solutions with ActiveRecord, remember to implement proper error handling, logging, and monitoring to ensure reliable operation in production environments.

For large-scale ETL requirements, consider combining ActiveRecord with specialized ETL frameworks or tools that provide additional features like visual workflow design, scheduling, and distributed processing capabilities.