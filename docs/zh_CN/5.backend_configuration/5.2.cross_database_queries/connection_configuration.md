# 跨数据库连接配置

> **❌ 未实现**：本文档中描述的多数据库连接功能（包括主从配置）**未实现**。此文档描述了计划中的功能，仅用于未来参考。当前用户应仅使用单个数据库连接。此功能可能会在未来版本中开发，但没有保证的时间表。

本文档提供了关于在rhosocial ActiveRecord中配置和管理多个数据库连接的详细信息，包括如何设置连接到不同的数据库系统、管理连接池以及在运行时切换连接。**注意：这些功能目前非实现状态。**

## 基本连接配置

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

### 连接配置选项

每个数据库连接可以根据数据库类型配置各种选项。以下是一些常见的配置选项：

#### 所有数据库类型的通用选项

- `driver`：要使用的数据库驱动程序（例如，'sqlite'、'mysql'、'postgresql'）
- `database`：数据库的名称
- `pool_size`：连接池中保持的最大连接数
- `pool_timeout`：等待连接池中连接的最长时间（以秒为单位）
- `pool_recycle`：连接被回收的秒数
- `echo`：是否记录SQL语句（布尔值，默认为False）

#### MySQL/MariaDB特定选项

- `host`：数据库服务器主机名或IP地址
- `port`：数据库服务器端口（默认为3306）
- `username`：用于认证的用户名
- `password`：用于认证的密码
- `charset`：要使用的字符集（默认为'utf8mb4'）
- `ssl`：SSL配置选项（字典）

#### PostgreSQL特定选项

- `host`：数据库服务器主机名或IP地址
- `port`：数据库服务器端口（默认为5432）
- `username`：用于认证的用户名
- `password`：用于认证的密码
- `schema`：要使用的模式（默认为'public'）
- `sslmode`：要使用的SSL模式（例如，'require'、'verify-full'）

#### Oracle特定选项

- `host`：数据库服务器主机名或IP地址
- `port`：数据库服务器端口（默认为1521）
- `username`：用于认证的用户名
- `password`：用于认证的密码
- `service_name`：Oracle服务名称
- `sid`：Oracle SID（service_name的替代方案）

#### SQL Server特定选项

- `host`：数据库服务器主机名或IP地址
- `port`：数据库服务器端口（默认为1433）
- `username`：用于认证的用户名
- `password`：用于认证的密码
- `driver`：要使用的ODBC驱动程序（例如，'ODBC Driver 17 for SQL Server'）
- `trusted_connection`：是否使用Windows认证（布尔值）

### 连接池

rhosocial ActiveRecord使用连接池来高效管理数据库连接。连接池维护一组可以重用的开放连接，减少为每个数据库操作建立新连接的开销。

您可以为每个数据库连接配置连接池参数：

```python
from rhosocial.activerecord import ConnectionManager

# 配置带有池设置的连接
config = {
    'driver': 'postgresql',
    'host': 'localhost',
    'port': 5432,
    'database': 'myapp',
    'username': 'user',
    'password': 'password',
    'pool_size': 10,        # 池中的最大连接数
    'pool_timeout': 30,     # 等待连接的最长时间（以秒为单位）
    'pool_recycle': 1800    # 30分钟后回收连接
}

ConnectionManager.configure('main', config)
```

#### 池大小考虑因素

在确定应用程序的适当池大小时，请考虑以下因素：

- 应用程序处理的并发请求数量
- 数据库服务器的最大连接限制
- 每个连接的资源使用情况

一般准则是将池大小设置为与应用程序需要执行的最大并发数据库操作数量相匹配，再加上一个小缓冲区以应对开销。

## 使用多个数据库连接

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

### 直接访问连接对象

在某些情况下，您可能需要直接访问底层连接对象：

```python
from rhosocial.activerecord import get_connection

# 按名称获取连接
conn = get_connection('primary')

# 使用连接执行原始SQL
result = conn.execute_raw("SELECT COUNT(*) FROM users WHERE status = 'active'")
```

## 连接管理策略

### 应用程序级别的连接配置

对于大多数应用程序，最好在应用程序启动时配置所有数据库连接：

```python
def configure_database_connections():
    # 从环境或配置文件加载配置
    primary_config = load_config('primary_db')
    analytics_config = load_config('analytics_db')
    reporting_config = load_config('reporting_db')
    
    # 配置连接
    ConnectionManager.configure('primary', primary_config)
    ConnectionManager.configure('analytics', analytics_config)
    ConnectionManager.configure('reporting', reporting_config)

# 在应用程序初始化期间调用此函数
configure_database_connections()
```

### 动态连接配置

在某些情况下，您可能需要在运行时动态配置连接：

```python
def connect_to_tenant_database(tenant_id):
    # 加载租户特定配置
    tenant_config = get_tenant_db_config(tenant_id)
    
    # 使用租户特定名称配置连接
    connection_name = f"tenant_{tenant_id}"
    ConnectionManager.configure(connection_name, tenant_config)
    
    return connection_name

# 使用方法
tenant_connection = connect_to_tenant_database('tenant123')
with User.using_connection(tenant_connection):
    tenant_users = User.all()
```

### 连接生命周期管理

rhosocial ActiveRecord自动管理数据库连接的生命周期，但如果需要，您可以显式控制连接的创建和处置：

```python
from rhosocial.activerecord import ConnectionManager

# 显式创建所有配置的连接
ConnectionManager.initialize_all()

# 处置特定连接
ConnectionManager.dispose('secondary')

# 处置所有连接（例如，在应用程序关闭期间）
ConnectionManager.dispose_all()
```

## 跨数据库连接配置的最佳实践

1. **使用描述性连接名称**：选择清楚指示每个数据库用途或内容的连接名称。

2. **集中连接配置**：将所有数据库连接配置保存在单一位置，以便更容易管理。

3. **使用环境变量存储敏感信息**：将敏感连接信息（如密码）存储在环境变量中，而不是硬编码它们。

```python
import os

config = {
    'driver': 'postgresql',
    'host': os.environ.get('DB_HOST', 'localhost'),
    'port': int(os.environ.get('DB_PORT', 5432)),
    'database': os.environ.get('DB_NAME', 'myapp'),
    'username': os.environ.get('DB_USER', 'user'),
    'password': os.environ.get('DB_PASSWORD', ''),
}
```

4. **配置适当的池大小**：根据应用程序的需求和数据库服务器的能力设置连接池大小。

5. **监控连接使用情况**：实施监控以跟踪连接使用情况并检测连接泄漏或池耗尽。

6. **实现连接重试逻辑**：对于关键操作，实现重试逻辑以处理临时连接故障。

```python
from rhosocial.activerecord import ConnectionError

def perform_critical_operation():
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            with Transaction(get_connection('primary')):
                # 执行关键数据库操作
                return result
        except ConnectionError as e:
            retry_count += 1
            if retry_count >= max_retries:
                raise
            time.sleep(1)  # 重试前等待
```

7. **在空闲期间关闭连接**：对于有不活动期的长时间运行的应用程序，考虑在空闲期间处置未使用的连接。

8. **在适当时使用读写分离**：对于高流量应用程序，考虑为读和写操作配置单独的连接。

```python
# 配置单独的读写连接
ConnectionManager.configure('primary_write', write_config)
ConnectionManager.configure('primary_read', read_config)

class User(ActiveRecord):
    __connection__ = 'primary_write'  # 写操作的默认连接
    
    @classmethod
    def find_active(cls):
        # 为此查询使用读连接
        with cls.using_connection('primary_read'):
            return cls.where(status='active').all()
```

## 连接问题故障排除

### 常见连接问题

1. **连接池耗尽**：如果您的应用程序遇到性能缓慢或超时，您可能正在耗尽连接池。

   解决方案：增加池大小或优化代码以更快地释放连接。

2. **连接超时**：如果连接超时，数据库服务器可能过载或存在网络问题。

   解决方案：检查数据库服务器负载、网络连接，并在适当时增加连接超时。

3. **认证失败**：不正确的凭据或权限问题可能导致认证失败。

   解决方案：验证用户名、密码，并确保用户具有适当的权限。

### 调试连接问题

要调试连接问题，您可以启用SQL日志记录：

```python
config = {
    # 其他配置选项...
    'echo': True  # 启用SQL日志记录
}

ConnectionManager.configure('debug_connection', config)
```

您还可以实现自定义连接事件监听器：

```python
from rhosocial.activerecord import ConnectionEvents

# 注册连接事件监听器
ConnectionEvents.on_checkout(lambda conn: print(f"连接 {conn.id} 已检出"))
ConnectionEvents.on_checkin(lambda conn: print(f"连接 {conn.id} 已检入"))
ConnectionEvents.on_connect(lambda conn: print(f"新连接 {conn.id} 已建立"))
ConnectionEvents.on_disconnect(lambda conn: print(f"连接 {conn.id} 已关闭"))
```

## 结论

正确配置和管理数据库连接对于使用多个数据库的应用程序至关重要。rhosocial ActiveRecord提供了一个灵活而强大的连接管理系统，允许您同时使用多个不同类型的数据库，同时抽象出许多相关的复杂性。

通过遵循本文档中概述的最佳实践，您可以确保应用程序的数据库连接高效、可靠且安全。