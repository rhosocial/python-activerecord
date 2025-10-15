# 性能分析

当前，rhosocial ActiveRecord 不包含内置性能分析工具。性能分析依赖于通用Python分析工具和手动技术。

## 使用标准Python分析器

对于ActiveRecord应用程序的性能分析，请使用标准Python分析工具：

### cProfile
```python
import cProfile
import pstats
from rhosocial.activerecord import ActiveRecord

def performance_test():
    # 您的ActiveRecord操作
    users = User.find_all().limit(100).all()
    for user in users:
        user.email = f"updated_{user.email}"
        user.save()

# 分析函数
profiler = cProfile.Profile()
profiler.enable()
performance_test()
profiler.disable()

# 打印统计信息
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats()
```

### 使用 line_profiler（如已安装）
```python
# 为要分析的函数添加@profile装饰器
@profile
def slow_function():
    # ActiveRecord操作
    pass
```

## 基本性能测量

用于简单计时测量：

```python
import time
from rhosocial.activerecord import ActiveRecord

def time_operation():
    start_time = time.time()
    
    # ActiveRecord操作
    users = User.find_all().limit(1000).all()
    
    end_time = time.time()
    print(f"操作耗时 {end_time - start_time:.2f} 秒")
```

## 查询性能

当前，查询性能分析依赖于：
- 手动检查SQL查询
- 使用数据库特定工具分析查询计划
- 使用标准Python计时函数对查询执行计时

## 当前限制

- 无内置查询计时
- 无自动性能指标
- 无查询计划分析工具
- 无ActiveRecord特定分析工具

分析功能将在框架成熟后添加。

## 查询分析

### 内置查询统计

rhosocial ActiveRecord提供了内置的查询统计功能，帮助您识别慢查询：

```python
from rhosocial.activerecord import stats

# 启用查询统计
stats.enable()

# 执行一些查询
users = User.find_all()
posts = Post.find_by_user_id(user_id)

# 获取查询统计
query_stats = stats.get_stats()
print(f"执行的查询总数: {query_stats['total_queries']}")
print(f"平均查询时间: {query_stats['avg_query_time']}ms")

# 获取最慢的查询
slow_queries = stats.get_slow_queries(limit=5)
for query in slow_queries:
    print(f"查询: {query['sql']}")
    print(f"执行时间: {query['execution_time']}ms")
    print(f"参数: {query['params']}")
    print("---")

# 重置统计
stats.reset()
```

### 使用数据库工具

大多数数据库系统提供了用于分析查询性能的工具：

- **MySQL**: EXPLAIN命令和性能模式
- **PostgreSQL**: EXPLAIN ANALYZE命令
- **SQLite**: EXPLAIN QUERY PLAN命令

示例：使用EXPLAIN分析查询：

```python
from rhosocial.activerecord import raw_sql

# 获取查询的执行计划
query = User.where(status='active').order_by('created_at').limit(10).to_sql()
explain_result = raw_sql(f"EXPLAIN {query}")

# 分析结果
for row in explain_result:
    print(row)
```

## 内存使用分析

### 跟踪对象分配

大型ActiveRecord应用程序可能会遇到内存使用问题，特别是在处理大型结果集时：

```python
import tracemalloc

# 启动内存跟踪
tracemalloc.start()

# 执行一些ActiveRecord操作
users = User.find_all(include=['posts', 'comments'])

# 获取内存快照
snapshot = tracemalloc.take_snapshot()
top_stats = snapshot.statistics('lineno')

# 显示内存使用情况
print("内存使用最多的位置:")
for stat in top_stats[:10]:
    print(f"{stat.count} 块: {stat.size / 1024:.1f} KiB")
    print(f"  {stat.traceback.format()[0]}")

# 停止跟踪
tracemalloc.stop()
```

### 减少内存使用的技巧

- 使用迭代器而不是加载所有记录
- 只选择需要的字段
- 使用批处理处理大型数据集
- 适当使用懒加载关系

## 与Python分析器集成

### 使用cProfile

Python的内置分析器cProfile可以帮助识别代码中的性能瓶颈：

```python
import cProfile
import pstats

# 使用分析器运行代码
def run_queries():
    for i in range(100):
        User.find_by_id(i)
        Post.find_by_user_id(i)

# 创建分析器并运行函数
profiler = cProfile.Profile()
profiler.enable()
run_queries()
profiler.disable()

# 分析结果
stats = pstats.Stats(profiler).sort_stats('cumtime')
stats.print_stats(20)  # 打印前20个结果
```

### 使用line_profiler进行行级分析

对于更详细的分析，可以使用line_profiler包进行行级分析：

```bash
pip install line_profiler
```

```python
# 在代码中添加装饰器
from line_profiler import profile

@profile
def complex_query_function():
    users = User.where(status='active')
    result = []
    for user in users:
        posts = user.posts.where(published=True).order_by('-created_at')
        result.append((user, posts[:5]))
    return result

# 运行函数
result = complex_query_function()
```

然后使用kernprof运行脚本：

```bash
kernprof -l script.py
python -m line_profiler script.py.lprof
```

## 性能监控工具

### 集成APM工具

对于生产环境，考虑使用应用程序性能监控(APM)工具：

- **New Relic**
- **Datadog**
- **Prometheus + Grafana**

这些工具可以提供实时性能监控、查询分析和警报功能。

### 自定义性能指标

rhosocial ActiveRecord允许您定义和收集自定义性能指标：

```python
from rhosocial.activerecord import metrics

# 注册自定义指标
metrics.register('user_query_time', 'histogram')

# 在代码中记录指标
with metrics.timer('user_query_time'):
    users = User.find_all()

# 导出指标
all_metrics = metrics.export()
print(all_metrics)
```

## 最佳实践

- 定期进行性能分析，而不仅仅是在出现问题时
- 建立性能基准，以便可以比较更改前后的性能
- 关注最常执行的查询和最慢的查询
- 使用适当的索引优化数据库查询
- 考虑使用缓存减少数据库负载
- 在开发环境中模拟生产负载进行测试

## 结论

性能分析是一个持续的过程，而不是一次性的活动。通过使用本指南中描述的工具和技术，您可以识别和解决ActiveRecord应用程序中的性能瓶颈，确保您的应用程序在各种负载条件下都能高效运行。