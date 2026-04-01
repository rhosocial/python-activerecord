# 环境隔离配置 (Configuration Management)

将数据库凭据和路径硬编码在源代码中，会使同一套代码无法安全地部署到开发、测试和生产环境。
本文将 [12-Factor App](https://12factor.net/config) 原则应用于 `rhosocial-activerecord` 的配置管理。

> 💡 **AI 提示词：** "如何在不修改模型代码的情况下，让开发环境和生产环境使用不同的数据库？"

---

## 1. 三环境模式

| 环境 | 典型后端 | 用途 |
| --- | --- | --- |
| `development` | SQLite（本地文件） | 快速迭代，无需外部服务 |
| `test` | SQLite（`:memory:`） | 隔离运行，每次测试后自动重置 |
| `production` | MySQL / PostgreSQL | 真实数据，连接池 |

---

## 2. 从环境变量读取配置

绝对不要在源代码中存储凭据。在应用启动时从环境变量读取：

```python
# config.py
import os

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///dev.db")
APP_ENV      = os.environ.get("APP_ENV", "development")
```

### 使用 python-dotenv（推荐用于本地开发）

```bash
# .env  （永远不要提交到版本控制）
APP_ENV=development
DATABASE_URL=sqlite:///dev.db
```

```python
from dotenv import load_dotenv
load_dotenv()  # 在读取 os.environ 之前加载 .env
```

### 使用 pydantic-settings（推荐用于较大项目）

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    app_env: str = "development"
    db_path: str = "dev.db"
    db_host: str = "localhost"
    db_port: int = 3306
    db_name: str = "myapp"
    db_user: str = "app"
    db_password: str = ""

    class Config:
        env_file = ".env"

settings = Settings()
```

---

## 3. 按环境创建后端的工厂函数

将所有后端构造逻辑集中在一个工厂函数中：

```python
# config/database.py
import os
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend, SQLiteConnectionConfig

def make_backend():
    env = os.environ.get("APP_ENV", "development")

    if env == "test":
        # 内存数据库：完全隔离，测试会话结束后自动清除
        config = SQLiteConnectionConfig(database=":memory:")
        return SQLiteBackend(config)

    if env == "development":
        config = SQLiteConnectionConfig(database="dev.db")
        return SQLiteBackend(config)

    if env == "production":
        # 生产环境切换到 MySQL / PostgreSQL
        from rhosocial.activerecord.backend.impl.mysql import MySQLBackend, MySQLConnectionConfig
        config = MySQLConnectionConfig(
            host=os.environ["DB_HOST"],
            port=int(os.environ.get("DB_PORT", 3306)),
            database=os.environ["DB_NAME"],
            user=os.environ["DB_USER"],
            password=os.environ["DB_PASSWORD"],
            pool_size=int(os.environ.get("DB_POOL_SIZE", 5)),
        )
        return MySQLBackend(config)

    raise ValueError(f"未知的 APP_ENV: {env!r}")
```

---

## 4. 集中式启动配置

在单一入口点调用 `configure()`，确保不遗漏任何模型：

```python
# app.py
from config.database import make_backend
from myapp.models import User, Order, Product

def configure_models():
    """配置所有模型。在应用启动时调用一次。"""
    backend = make_backend()
    for cls in [User, Order, Product]:
        cls.configure(backend=backend)

configure_models()
```

> ✅ 使用模型类列表，方便在代码审查时确认所有模型都已注册，并快速发现遗漏。

---

## 5. 测试环境隔离

测试中使用内存 SQLite 后端，每个测试会话（或每个测试）配置一次：

```python
# tests/conftest.py
import pytest
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend, SQLiteConnectionConfig
from myapp.models import User, Order

@pytest.fixture(scope="session", autouse=True)
def configure_test_db():
    """整个测试会话共享的内存数据库。"""
    config = SQLiteConnectionConfig(database=":memory:")
    backend = SQLiteBackend(config)
    User.configure(backend=backend)
    Order.configure(backend=backend)
    # 创建表结构
    User.create_table()
    Order.create_table()
    yield
    # 清理：:memory: 数据库随进程结束自动销毁，无需手动清理

@pytest.fixture(autouse=True)
def clean_tables():
    """测试间清空数据，保证隔离。"""
    yield
    User.query().delete()
    Order.query().delete()
```

如需每个测试完全隔离，使用独立的内存数据库：

```python
@pytest.fixture
def fresh_db():
    """每个测试独享一个全新的内存数据库——最强隔离。"""
    config = SQLiteConnectionConfig(database=":memory:")
    backend = SQLiteBackend(config)
    User.configure(backend=backend)
    User.create_table()
    yield backend
    # 无需显式清理；:memory: 数据库在测试结束后自动释放
```

---

## 6. 配置管理检查清单

- [ ] 源代码中没有硬编码的凭据或数据库路径
- [ ] `.env` 文件已加入 `.gitignore`，不提交到版本控制
- [ ] `APP_ENV` 变量控制创建哪种后端
- [ ] 所有 `configure()` 调用集中在单一启动函数中
- [ ] 测试使用 `:memory:` SQLite，且测试之间重置数据状态
- [ ] 生产环境凭据通过环境变量或密钥管理服务提供

---

## 可运行示例

参见 [`docs/examples/chapter_03_modeling/configuration_management.py`](../../../examples/chapter_03_modeling/configuration_management.py)，
该脚本自包含，完整演示了上述五种模式。

---

## 另请参阅

- [线程安全](concurrency.md) — fork 类和异步服务器中何时调用 `configure()`
- [多个独立连接](best_practices.md#8-多个独立连接-multiple-independent-connections) — 不同模型类使用独立后端
