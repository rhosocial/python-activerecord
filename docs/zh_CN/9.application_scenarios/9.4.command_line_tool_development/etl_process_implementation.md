# ETL流程实现

本文档探讨如何在命令行环境中利用rhosocial ActiveRecord实现提取、转换、加载（ETL）流程。

## 引言

ETL（提取、转换、加载）流程对于数据集成、迁移和仓库操作至关重要。rhosocial ActiveRecord提供了一个强大的ORM框架，简化了ETL工作流中的数据库交互，使开发人员能够创建可维护和高效的数据管道。

## ETL流程概述

典型的ETL流程包括三个主要阶段：

1. **提取（Extract）**：从各种源系统检索数据
2. **转换（Transform）**：清洗、验证和重构数据
3. **加载（Load）**：将转换后的数据写入目标系统

rhosocial ActiveRecord可以在所有三个阶段有效使用，特别是当数据库作为源或目标时。

## 使用ActiveRecord实现ETL

### 基本ETL管道

以下是使用ActiveRecord的简单ETL流程示例：

```python
import sys
from rhosocial.activerecord import ActiveRecord, Field
from rhosocial.activerecord.backend import SQLiteBackend, MySQLBackend

# 源模型（提取）
class SourceCustomer(ActiveRecord):
    table_name = 'customers'
    id = Field(int, primary_key=True)
    name = Field(str)
    email = Field(str)
    address = Field(str)
    created_at = Field(str)

# 目标模型（加载）
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

# 设置连接
source_db = SQLiteBackend('source.sqlite')
SourceCustomer.connect(source_db)

target_db = MySQLBackend(host='localhost', database='data_warehouse', 
                         user='etl_user', password='password')
TargetCustomer.connect(target_db)

def extract_transform_load():
    # 从源提取数据
    source_customers = SourceCustomer.find_all()
    
    # 批量处理以提高性能
    batch_size = 100
    processed_count = 0
    
    # 使用事务以提高性能和确保数据完整性
    with TargetCustomer.transaction():
        for source_customer in source_customers:
            # 转换数据
            target_customer = TargetCustomer()
            target_customer.id = source_customer.id
            target_customer.full_name = source_customer.name
            target_customer.email = source_customer.email
            
            # 地址转换（解析组件）
            address_parts = parse_address(source_customer.address)
            target_customer.address_line = address_parts.get('line', '')
            target_customer.city = address_parts.get('city', '')
            target_customer.state = address_parts.get('state', '')
            target_customer.postal_code = address_parts.get('postal_code', '')
            
            # 日期转换
            target_customer.created_date = source_customer.created_at.split(' ')[0]
            
            # 将数据加载到目标
            if target_customer.save():
                processed_count += 1
            else:
                print(f"保存客户 {source_customer.id} 时出错: {target_customer.errors}")
            
            # 定期报告进度
            if processed_count % batch_size == 0:
                print(f"已处理 {processed_count} 个客户")
    
    print(f"ETL流程完成: 已处理 {processed_count} 个客户")

def parse_address(address_string):
    # 简单地址解析器（在实际场景中，使用适当的地址解析库）
    parts = {}
    try:
        # 这是一个简化示例 - 实际地址解析更复杂
        components = address_string.split(', ')
        parts['line'] = components[0]
        parts['city'] = components[1] if len(components) > 1 else ''
        
        if len(components) > 2:
            state_zip = components[2].split(' ')
            parts['state'] = state_zip[0]
            parts['postal_code'] = state_zip[1] if len(state_zip) > 1 else ''
    except Exception as e:
        print(f"解析地址 '{address_string}' 时出错: {e}")
    
    return parts

if __name__ == '__main__':
    extract_transform_load()
```

### 增量ETL

在许多情况下，您需要实现增量ETL，仅处理自上次运行以来的新数据或更改的数据：

```python
import datetime
import json
import os
from rhosocial.activerecord import ActiveRecord, Field
from rhosocial.activerecord.backend import PostgreSQLBackend, MySQLBackend

# 源模型
class SourceOrder(ActiveRecord):
    table_name = 'orders'
    id = Field(int, primary_key=True)
    customer_id = Field(int)
    order_date = Field(str)
    total_amount = Field(float)
    status = Field(str)
    last_updated = Field(str)  # 用于跟踪更改的时间戳

# 目标模型
class TargetOrder(ActiveRecord):
    table_name = 'order_fact'
    order_id = Field(int, primary_key=True)
    customer_id = Field(int)
    order_date = Field(str)
    order_amount = Field(float)
    order_status = Field(str)
    etl_timestamp = Field(str)  # 处理此记录的时间

# 设置连接
source_db = PostgreSQLBackend(host='source-db.example.com', database='sales', 
                             user='reader', password='password')
SourceOrder.connect(source_db)

target_db = MySQLBackend(host='target-db.example.com', database='data_warehouse', 
                        user='etl_user', password='password')
TargetOrder.connect(target_db)

# 用于跟踪上次运行的状态文件
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
    # 加载上次运行的状态
    state = load_state()
    last_run = state.get('last_run')
    
    # 本次运行的当前时间戳
    current_run = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    print(f"在 {current_run} 开始增量ETL")
    print(f"上次成功运行: {last_run if last_run else '从未'}")
    
    # 仅提取自上次运行以来的新/更改记录
    if last_run:
        source_orders = SourceOrder.find_all(
            conditions=["last_updated > ?", last_run],
            order="id"
        )
    else:
        # 首次运行 - 处理所有记录
        source_orders = SourceOrder.find_all(order="id")
    
    print(f"找到 {len(source_orders)} 个订单需要处理")
    
    # 处理记录
    processed_count = 0
    error_count = 0
    
    with TargetOrder.transaction():
        for source_order in source_orders:
            try:
                # 检查记录是否已存在于目标中
                target_order = TargetOrder.find_by_order_id(source_order.id)
                
                if not target_order:
                    target_order = TargetOrder()
                    target_order.order_id = source_order.id
                
                # 转换并加载数据
                target_order.customer_id = source_order.customer_id
                target_order.order_date = source_order.order_date
                target_order.order_amount = source_order.total_amount
                target_order.order_status = source_order.status
                target_order.etl_timestamp = current_run
                
                if target_order.save():
                    processed_count += 1
                else:
                    error_count += 1
                    print(f"保存订单 {source_order.id} 时出错: {target_order.errors}")
            
            except Exception as e:
                error_count += 1
                print(f"处理订单 {source_order.id} 时出错: {e}")
    
    # 如果成功则更新状态
    if error_count == 0:
        state['last_run'] = current_run
        save_state(state)
    
    print(f"ETL流程完成: 已处理 {processed_count} 个订单, {error_count} 个错误")
    return error_count == 0

if __name__ == '__main__':
    success = incremental_etl()
    sys.exit(0 if success else 1)
```

## 高级ETL技术

### 数据验证和清洗

作为转换阶段的一部分实现数据验证和清洗：

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
        # 移除非数字字符
        digits_only = re.sub(r'\D', '', phone)
        # 检查是否有有效长度
        return 10 <= len(digits_only) <= 15
    
    @staticmethod
    def clean_text(text):
        if not text:
            return ''
        # 移除多余空格
        cleaned = ' '.join(text.split())
        # 如果需要，移除特殊字符
        # cleaned = re.sub(r'[^\w\s]', '', cleaned)
        return cleaned

# 在ETL流程中使用
def transform_customer_data(source_customer):
    target_customer = TargetCustomer()
    
    # 清洗和验证数据
    target_customer.full_name = DataValidator.clean_text(source_customer.name)
    
    # 验证电子邮件
    if source_customer.email and DataValidator.validate_email(source_customer.email):
        target_customer.email = source_customer.email.lower()
    else:
        target_customer.email = None
        log_validation_error(source_customer.id, '无效的电子邮件格式')
    
    # 验证电话
    if source_customer.phone and DataValidator.validate_phone(source_customer.phone):
        target_customer.phone = standardize_phone_format(source_customer.phone)
    else:
        target_customer.phone = None
        log_validation_error(source_customer.id, '无效的电话格式')
    
    return target_customer

def log_validation_error(customer_id, error_message):
    # 记录验证错误以供日后审查
    print(f"客户 {customer_id} 的验证错误: {error_message}")
    # 在实际系统中，您可能会记录到数据库或文件
```

### 并行ETL处理

对于大型数据集，实现并行处理以提高性能：

```python
import multiprocessing
import time
from rhosocial.activerecord import ActiveRecord, Field

# 如前所述设置模型和连接

def process_batch(batch_ids):
    # 为此进程创建新的数据库连接
    source_db = PostgreSQLBackend(host='source-db.example.com', database='sales', 
                                user='reader', password='password')
    target_db = MySQLBackend(host='target-db.example.com', database='data_warehouse', 
                            user='etl_user', password='password')
    
    # 将模型连接到这些连接
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
                
                # 如前所述转换和加载
                target_order = TargetOrder.find_by_order_id(order_id) or TargetOrder()
                target_order.order_id = source_order.id
                # ... 其他转换
                
                if target_order.save():
                    results['processed'] += 1
                else:
                    results['errors'] += 1
            except Exception as e:
                results['errors'] += 1
                print(f"处理订单 {order_id} 时出错: {e}")
    
    return results

def parallel_etl():
    start_time = time.time()
    
    # 获取所有要处理的订单ID
    order_ids = [order.id for order in SourceOrder.find_all(select='id')]
    total_orders = len(order_ids)
    
    print(f"开始为 {total_orders} 个订单进行并行ETL")
    
    # 确定最佳批量大小和进程数
    cpu_count = multiprocessing.cpu_count()
    process_count = min(cpu_count, 8)  # 限制以避免过多的数据库连接
    batch_size = max(100, total_orders // (process_count * 10))
    
    # 分割成批次
    batches = [order_ids[i:i + batch_size] for i in range(0, total_orders, batch_size)]
    
    # 并行处理
    total_processed = 0
    total_errors = 0
    
    with multiprocessing.Pool(processes=process_count) as pool:
        results = pool.map(process_batch, batches)
        
        # 汇总结果
        for result in results:
            total_processed += result['processed']
            total_errors += result['errors']
    
    elapsed_time = time.time() - start_time
    print(f"ETL在 {elapsed_time:.2f} 秒内完成")
    print(f"已处理: {total_processed}, 错误: {total_errors}")
    
    return total_errors == 0

if __name__ == '__main__':
    success = parallel_etl()
    sys.exit(0 if success else 1)
```

### ETL监控和日志记录

为ETL流程实现全面的日志记录和监控：

```python
import logging
import time
from datetime import datetime
from rhosocial.activerecord import ActiveRecord, Field

# 配置日志
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

# 连接到监控数据库
monitoring_db = SQLiteBackend('etl_monitoring.sqlite')
ETLMetrics.connect(monitoring_db)

def run_etl_with_monitoring(job_name, etl_function):
    # 创建指标记录
    metrics = ETLMetrics()
    metrics.job_name = job_name
    metrics.start_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    metrics.status = 'running'
    metrics.save()
    
    logger.info(f"开始ETL作业: {job_name}")
    start_time = time.time()
    
    records_processed = 0
    records_failed = 0
    status = 'failed'
    
    try:
        # 运行实际的ETL流程
        result = etl_function()
        
        # 根据结果更新指标
        if isinstance(result, dict):
            records_processed = result.get('processed', 0)
            records_failed = result.get('failed', 0)
            status = 'success' if result.get('success', False) else 'failed'
        elif isinstance(result, bool):
            status = 'success' if result else 'failed'
        else:
            status = 'success'
            
    except Exception as e:
        logger.error(f"ETL作业失败，错误: {e}", exc_info=True)
        status = 'failed'
    finally:
        # 计算执行时间
        execution_time = time.time() - start_time
        
        # 更新指标记录
        metrics.end_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        metrics.records_processed = records_processed
        metrics.records_failed = records_failed
        metrics.execution_time_seconds = execution_time
        metrics.status = status
        metrics.save()
        
        logger.info(f"ETL作业 {job_name} 完成，状态: {status}")
        logger.info(f"已处理: {records_processed}, 失败: {records_failed}, 时间: {execution_time:.2f}秒")
    
    return status == 'success'

# 示例用法
def customer_etl_process():
    # 客户ETL的实现
    # ...
    return {'processed': 1250, 'failed': 5, 'success': True}

if __name__ == '__main__':
    success = run_etl_with_monitoring('customer_etl', customer_etl_process)
    sys.exit(0 if success else 1)
```

## ETL工作流编排

对于具有多个阶段的复杂ETL管道，实现工作流编排：

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
        logger.info(f"开始ETL工作流: {self.name}")
        start_time = time.time()
        
        success = True
        for i, step in enumerate(self.steps):
            self.current_step = i
            
            # 检查依赖关系
            if step['depends_on']:
                dependency_index = self._find_step_index(step['depends_on'])
                if dependency_index >= 0 and self.steps[dependency_index]['status'] != 'success':
                    logger.warning(f"跳过步骤 '{step['name']}' 因为依赖项 '{step['depends_on']}' 失败或被跳过")
                    step['status'] = 'skipped'
                    success = False
                    continue
            
            # 运行步骤
            logger.info(f"运行步骤 {i+1}/{len(self.steps)}: {step['name']}")
            step_start = time.time()
            
            try:
                step['result'] = step['function']()
                step_success = True
                
                # 检查结果是否为布尔值或带有success键的字典
                if isinstance(step['result'], bool):
                    step_success = step['result']
                elif isinstance(step['result'], dict) and 'success' in step['result']:
                    step_success = step['result']['success']
                
                step['status'] = 'success' if step_success else 'failed'
                if not step_success:
                    success = False
                    
            except Exception as e:
                logger.error(f"步骤 '{step['name']}' 失败，错误: {e}", exc_info=True)
                step['status'] = 'failed'
                step['result'] = str(e)
                success = False
            
            step_time = time.time() - step_start
            logger.info(f"步骤 '{step['name']}' 完成，状态: {step['status']}，用时 {step_time:.2f}秒")
        
        total_time = time.time() - start_time
        logger.info(f"ETL工作流 '{self.name}' 在 {total_time:.2f}秒内完成，总体状态: {'success' if success else 'failed'}")
        
        return success
    
    def _find_step_index(self, step_name):
        for i, step in enumerate(self.steps):
            if step['name'] == step_name:
                return i
        return -1

# 示例用法
def extract_customers():
    logger.info("提取客户数据")
    # 实现
    return {'success': True, 'count': 1000}

def transform_customers():
    logger.info("转换客户数据")
    # 实现
    return {'success': True, 'count': 950}

def load_customers():
    logger.info("将客户数据加载到目标")
    # 实现
    return {'success': True, 'count': 950}

def extract_orders():
    logger.info("提取订单数据")
    # 实现
    return {'success': True, 'count': 5000}

def transform_orders():
    logger.info("转换订单数据")
    # 实现
    return {'success': True, 'count': 4980}

def load_orders():
    logger.info("将订单数据加载到目标")
    # 实现
    return {'success': True, 'count': 4980}

def update_data_mart():
    logger.info("更新数据集市视图")
    # 实现
    return {'success': True}

if __name__ == '__main__':
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # 创建并运行工作流
    workflow = ETLWorkflow("每日数据仓库更新")
    
    # 添加带有依赖关系的步骤
    workflow.add_step("提取客户", extract_customers)
    workflow.add_step("转换客户", transform_customers, depends_on="提取客户")
    workflow.add_step("加载客户", load_customers, depends_on="转换客户")
    
    workflow.add_step("提取订单", extract_orders)
    workflow.add_step("转换订单", transform_orders, depends_on="提取订单")
    workflow.add_step("加载订单", load_orders, depends_on="转换订单")
    
    # 此步骤依赖于客户和订单数据都已加载
    workflow.add_step("更新数据集市", update_data_mart, depends_on="加载订单")
    
    # 运行工作流
    success = workflow.run()
    sys.exit(0 if success else 1)
```

## 结论

rhosocial ActiveRecord为实现ETL流程提供了强大的基础，提供了一种干净、面向对象的数据库交互方法。通过利用ActiveRecord的ORM功能，开发人员可以创建可维护、高效和健壮的ETL管道，处理复杂的数据转换需求。

本文档中的示例演示了各种ETL模式和技术，从基本数据移动到高级工作流编排。在使用ActiveRecord开发自己的ETL解决方案时，请记住实现适当的错误处理、日志记录和监控，以确保在生产环境中可靠运行。

对于大规模ETL需求，考虑将ActiveRecord与专业ETL框架或工具结合使用，这些框架或工具提供额外功能，如可视化工作流设计、调度和分布式处理能力。