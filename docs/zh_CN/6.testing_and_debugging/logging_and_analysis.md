# 日志配置

rhosocial ActiveRecord 中的日志当前基本，依赖于Python的标准日志模块。框架尚未提供高级日志功能。

## 设置基本日志

在ActiveRecord应用程序中启用日志：

```python
import logging

# 配置基本日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# 用于更详细的日志（包括SQL查询，如可用）
logging.getLogger('rhosocial.activerecord').setLevel(logging.DEBUG)
```

## 当前日志功能

当前实现提供：

- 基本SQL查询日志（如在后端实现）
- 连接状态日志
- 错误日志

## 示例用法

```python
import logging
from rhosocial.activerecord import ActiveRecord

logger = logging.getLogger('rhosocial.activerecord')

# 启用调试日志以查看查询
logger.setLevel(logging.DEBUG)

# 任何数据库操作现在都将在DEBUG级别记录
user = User(name="日志测试", email="log@example.com")
user.save()
```

## 限制

- 无结构化日志
- 无自动性能指标
- 无查询执行时间日志
- 框架操作的有限洞察

高级日志和分析功能将在未来版本中添加。

## 设置日志记录

rhosocial ActiveRecord提供了一个灵活的日志系统，与Python的标准日志模块集成。

### 基本日志配置

```python
import logging
from rhosocial.activerecord import configure_logging

# 配置全局日志
configure_logging(
    level=logging.INFO,  # 全局日志级别
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    file_path="activerecord.log"  # 可选：记录到文件
)
```

### 组件特定日志

您可以为特定组件配置不同的日志级别：

```python
# 为特定组件配置日志
configure_logging(component="query", level=logging.DEBUG)
configure_logging(component="transaction", level=logging.INFO)
configure_logging(component="relation", level=logging.WARNING)
```

### 可用的日志组件

rhosocial ActiveRecord提供了几个日志组件：

- `query`：记录SQL查询及其参数
- `transaction`：记录事务操作（开始、提交、回滚）
- `relation`：记录关系加载和缓存
- `model`：记录模型操作（创建、更新、删除）
- `migration`：记录架构迁移操作
- `connection`：记录数据库连接事件
- `cache`：记录缓存操作

### 生产环境中的日志记录

对于生产环境，考虑以下日志实践：

```python
# 生产环境日志配置
configure_logging(
    level=logging.WARNING,  # 只记录警告和错误
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    file_path="/var/log/myapp/activerecord.log",
    max_bytes=10485760,  # 10MB
    backup_count=5  # 保留5个备份文件
)

# 为关键组件启用性能日志
configure_logging(component="query", level=logging.INFO)
```

## 日志分析技术

设置好日志后，您可以分析日志以了解应用程序的行为。

### 基本日志分析

#### 过滤日志

使用标准Unix工具过滤日志：

```bash
# 查找所有错误日志
grep "ERROR" activerecord.log

# 查找慢查询（耗时超过100毫秒）
grep "execution time" activerecord.log | grep -E "[0-9]{3,}\.[0-9]+ms"

# 按类型统计查询
grep "Executing SQL:" activerecord.log | grep -c "SELECT"
grep "Executing SQL:" activerecord.log | grep -c "INSERT"
grep "Executing SQL:" activerecord.log | grep -c "UPDATE"
grep "Executing SQL:" activerecord.log | grep -c "DELETE"
```

#### 分析查询模式

```bash
# 提取唯一查询模式（移除参数值）
grep "Executing SQL:" activerecord.log | sed -E 's/\[.*\]/[params]/g' | sort | uniq -c | sort -nr
```

### 高级日志分析

#### 使用Python进行日志分析

```python
import re
from collections import defaultdict

# 分析查询频率和执行时间
def analyze_query_logs(log_file):
    query_pattern = re.compile(r"Executing SQL: (.*) with params (.*) \(([0-9.]+)ms\)")
    query_stats = defaultdict(list)
    
    with open(log_file, 'r') as f:
        for line in f:
            match = query_pattern.search(line)
            if match:
                sql, params, time = match.groups()
                # 通过将文字值替换为占位符来标准化SQL
                normalized_sql = re.sub(r"'[^']*'", "'?'", sql)
                query_stats[normalized_sql].append(float(time))
    
    # 计算统计数据
    results = []
    for sql, times in query_stats.items():
        results.append({
            'sql': sql,
            'count': len(times),
            'avg_time': sum(times) / len(times),
            'min_time': min(times),
            'max_time': max(times),
            'total_time': sum(times)
        })
    
    # 按总时间排序（最耗时的查询在前）
    return sorted(results, key=lambda x: x['total_time'], reverse=True)

# 使用方法
stats = analyze_query_logs('activerecord.log')
for query in stats[:10]:  # 前10个最耗时的查询
    print(f"查询: {query['sql']}")
    print(f"次数: {query['count']}, 平均: {query['avg_time']:.2f}ms, 总计: {query['total_time']:.2f}ms")
    print()
```

#### 可视化日志数据

使用Python库如matplotlib或pandas来可视化日志数据：

```python
import matplotlib.pyplot as plt
import pandas as pd

# 将查询统计转换为DataFrame
def visualize_query_stats(stats):
    df = pd.DataFrame(stats)
    
    # 绘制查询频率
    plt.figure(figsize=(12, 6))
    df.sort_values('count', ascending=False)[:10].plot(kind='bar', x='sql', y='count')
    plt.title('前10个最频繁的查询')
    plt.tight_layout()
    plt.savefig('query_frequency.png')
    
    # 绘制查询执行时间
    plt.figure(figsize=(12, 6))
    df.sort_values('total_time', ascending=False)[:10].plot(kind='bar', x='sql', y='total_time')
    plt.title('前10个最耗时的查询')
    plt.tight_layout()
    plt.savefig('query_time.png')

# 使用方法
visualize_query_stats(stats)
```

## 识别性能瓶颈

日志对于识别ActiveRecord应用程序中的性能瓶颈非常有价值。

### 检测慢查询

```python
import re
from datetime import datetime

def find_slow_queries(log_file, threshold_ms=100):
    slow_queries = []
    timestamp_pattern = re.compile(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3})")
    query_pattern = re.compile(r"Executing SQL: (.*) with params (.*) \(([0-9.]+)ms\)")
    
    with open(log_file, 'r') as f:
        for line in f:
            timestamp_match = timestamp_pattern.search(line)
            query_match = query_pattern.search(line)
            
            if timestamp_match and query_match:
                timestamp = timestamp_match.group(1)
                sql, params, time = query_match.groups()
                time_ms = float(time)
                
                if time_ms > threshold_ms:
                    slow_queries.append({
                        'timestamp': timestamp,
                        'sql': sql,
                        'params': params,
                        'time_ms': time_ms
                    })
    
    return sorted(slow_queries, key=lambda x: x['time_ms'], reverse=True)

# 使用方法
slow_queries = find_slow_queries('activerecord.log', threshold_ms=100)
for query in slow_queries:
    print(f"[{query['timestamp']}] {query['time_ms']:.2f}ms: {query['sql']}")
    print(f"参数: {query['params']}")
    print()
```

### 识别N+1查询问题

N+1查询问题发生在代码执行N个额外查询来获取N条记录的相关数据时：

```python
import re
from collections import defaultdict

def detect_n_plus_1(log_file, time_window_seconds=1):
    query_pattern = re.compile(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),(\d{3}) .* Executing SQL: (.*) with params (.*)")
    query_groups = []
    current_group = []
    last_timestamp = None
    
    with open(log_file, 'r') as f:
        for line in f:
            match = query_pattern.search(line)
            if match:
                timestamp_str, ms, sql, params = match.groups()
                timestamp = datetime.strptime(f"{timestamp_str}.{ms}", "%Y-%m-%d %H:%M:%S.%f")
                
                if last_timestamp is None:
                    last_timestamp = timestamp
                    current_group.append((timestamp, sql, params))
                elif (timestamp - last_timestamp).total_seconds() <= time_window_seconds:
                    current_group.append((timestamp, sql, params))
                else:
                    if len(current_group) > 5:  # 潜在的N+1问题
                        query_groups.append(current_group)
                    current_group = [(timestamp, sql, params)]
                    last_timestamp = timestamp
    
    # 检查最后一组
    if len(current_group) > 5:
        query_groups.append(current_group)
    
    # 分析潜在的N+1问题
    n_plus_1_candidates = []
    for group in query_groups:
        # 寻找相同查询以不同参数重复的模式
        normalized_queries = defaultdict(list)
        for timestamp, sql, params in group:
            # 通过将文字值替换为占位符来标准化SQL
            normalized_sql = re.sub(r"'[^']*'", "'?'", sql)
            normalized_queries[normalized_sql].append((timestamp, sql, params))
        
        # 如果单个查询模式出现多次，可能是N+1问题
        for normalized_sql, instances in normalized_queries.items():
            if len(instances) > 5 and "WHERE" in normalized_sql:
                n_plus_1_candidates.append({
                    'pattern': normalized_sql,
                    'count': len(instances),
                    'examples': instances[:3]  # 前3个示例
                })
    
    return n_plus_1_candidates

# 使用方法
n_plus_1_problems = detect_n_plus_1('activerecord.log')
for problem in n_plus_1_problems:
    print(f"潜在的N+1问题: {problem['pattern']}")
    print(f"重复 {problem['count']} 次")
    print("示例:")
    for timestamp, sql, params in problem['examples']:
        print(f"  {sql} with params {params}")
    print()
```

### 分析事务性能

```python
import re
from datetime import datetime

def analyze_transactions(log_file):
    transaction_pattern = re.compile(r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}),(\d{3}) .* Transaction (BEGIN|COMMIT|ROLLBACK)")
    transactions = []
    current_transaction = None
    
    with open(log_file, 'r') as f:
        for line in f:
            match = transaction_pattern.search(line)
            if match:
                timestamp_str, ms, action = match.groups()
                timestamp = datetime.strptime(f"{timestamp_str}.{ms}", "%Y-%m-%d %H:%M:%S.%f")
                
                if action == "BEGIN":
                    current_transaction = {'start': timestamp, 'queries': []}
                elif action in ("COMMIT", "ROLLBACK") and current_transaction:
                    current_transaction['end'] = timestamp
                    current_transaction['duration'] = (current_transaction['end'] - current_transaction['start']).total_seconds()
                    current_transaction['action'] = action
                    transactions.append(current_transaction)
                    current_transaction = None
            
            # 捕获事务内的查询
            elif current_transaction and "Executing SQL:" in line:
                current_transaction['queries'].append(line.strip())
    
    # 按持续时间排序（最长的在前）
    return sorted(transactions, key=lambda x: x['duration'], reverse=True)

# 使用方法
transactions = analyze_transactions('activerecord.log')
for i, txn in enumerate(transactions[:10]):  # 前10个最长的事务
    print(f"事务 {i+1}: {txn['duration']:.6f} 秒 ({txn['action']})")
    print(f"查询数: {len(txn['queries'])}")
    if len(txn['queries']) > 0:
        print(f"第一个查询: {txn['queries'][0]}")
        print(f"最后一个查询: {txn['queries'][-1]}")
    print()
```

## 与监控工具集成

对于生产应用程序，考虑将日志与监控工具集成。

### 结构化日志

使用结构化日志以更好地与日志分析工具集成：

```python
import json
import logging

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            'timestamp': self.formatTime(record, self.datefmt),
            'name': record.name,
            'level': record.levelname,
            'message': record.getMessage(),
        }
        
        # 添加额外属性
        for key, value in record.__dict__.items():
            if key not in ('args', 'asctime', 'created', 'exc_info', 'exc_text', 'filename',
                          'funcName', 'id', 'levelname', 'levelno', 'lineno', 'module',
                          'msecs', 'message', 'msg', 'name', 'pathname', 'process',
                          'processName', 'relativeCreated', 'stack_info', 'thread', 'threadName'):
                log_record[key] = value
        
        return json.dumps(log_record)

# 配置JSON日志
def configure_json_logging():
    logger = logging.getLogger('rhosocial.activerecord')
    handler = logging.FileHandler('activerecord.json.log')
    handler.setFormatter(JSONFormatter())
    logger.addHandler(handler)
    return logger

# 使用方法
json_logger = configure_json_logging()
```

### 与ELK Stack集成

对于较大的应用程序，考虑使用ELK Stack（Elasticsearch、Logstash、Kibana）：

```python
# 配置日志输出为与Logstash兼容的格式
configure_logging(
    level=logging.INFO,
    format='{"timestamp": "%(asctime)s", "level": "%(levelname)s", "logger": "%(name)s", "message": "%(message)s"}',
    file_path="/var/log/myapp/activerecord.log"
)
```

然后配置Logstash摄取这些日志并将它们发送到Elasticsearch以便使用Kibana进行分析。

### 与Prometheus集成

对于基于指标的监控，考虑将日志中的关键指标暴露给Prometheus：

```python
from prometheus_client import Counter, Histogram, start_http_server
import time

# 定义指标
query_counter = Counter('activerecord_queries_total', 'SQL查询总数', ['query_type'])
query_duration = Histogram('activerecord_query_duration_seconds', '查询执行时间', ['query_type'])
transaction_counter = Counter('activerecord_transactions_total', '事务总数', ['status'])
transaction_duration = Histogram('activerecord_transaction_duration_seconds', '事务执行时间')

# 启动Prometheus指标服务器
start_http_server(8000)

# 猴子补丁ActiveRecord以收集指标
original_execute = db_connection.execute

def instrumented_execute(sql, params=None):
    query_type = sql.split()[0].upper() if sql else 'UNKNOWN'
    query_counter.labels(query_type=query_type).inc()
    
    start_time = time.time()
    result = original_execute(sql, params)
    duration = time.time() - start_time
    
    query_duration.labels(query_type=query_type).observe(duration)
    return result

db_connection.execute = instrumented_execute
```

## 日志记录的最佳实践

1. **使用适当的日志级别**：为每条消息使用正确的日志级别（DEBUG、INFO、WARNING、ERROR、CRITICAL）

2. **包含上下文**：在日志消息中包含相关上下文（用户ID、请求ID等）

3. **结构化日志**：使用结构化日志格式（JSON）以便更容易解析和分析

4. **日志轮转**：配置日志轮转以防止日志消耗过多磁盘空间

5. **性能考虑**：注意大量日志记录的性能影响

6. **敏感数据**：避免记录敏感数据（密码、个人信息等）

7. **关联ID**：使用关联ID跟踪跨多个组件的请求

8. **定期分析**：定期分析日志以识别模式和问题

9. **告警**：为关键日志事件设置告警

10. **保留策略**：根据您的需求和监管要求定义日志保留策略