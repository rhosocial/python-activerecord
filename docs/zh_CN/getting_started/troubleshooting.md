# 常见错误与解决

本文档帮助你在使用 `rhosocial-activerecord` 时快速定位和解决常见问题。

## 快速诊断

| 错误信息 | 跳转章节 |
|---------|---------|
| `No backend configured` | [后端未配置](#后端未配置) |
| `FieldProxy not found` / 查询字段无法补全 | [FieldProxy 未定义](#fieldproxy-未定义) |
| `ModuleNotFoundError` / `ImportError` | [导入错误](#导入错误) |
| `PYTHONPATH` 相关警告（仅开发者） | [PYTHONPATH 问题](#pythonpath-问题) |
| 类型检查错误 | [类型注解错误](#类型注解错误) |
| `RuntimeError: cannot be used in async context` | [同步异步混用](#同步异步混用) |
| 数据库连接失败 | [数据库连接问题](#数据库连接问题) |

---

## 后端未配置

### 错误信息

```python
NoBackendConfiguredError: No backend configured for model User. 
Call User.configure(backend) first.
```

### 原因

在使用模型之前，没有为其配置数据库后端。

### 解决

在使用模型前调用 `configure()` 方法：

```python
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend, SQLiteConnectionConfig

# 1. 创建配置
config = SQLiteConnectionConfig(database='myapp.db')

# 2. 配置模型（必须在首次使用前）
User.configure(config, SQLiteBackend)

# 3. 现在可以使用了
user = User(name="Alice")
user.save()
```

### 最佳实践

建议在应用启动时一次性配置所有模型：

```python
# app/config.py
def setup_database():
    config = SQLiteConnectionConfig(database='app.db')
    
    # 配置所有模型
    User.configure(config, SQLiteBackend)
    Post.configure(config, SQLiteBackend)  # 共享同一个后端
    Comment.configure(config, SQLiteBackend)
    
    # 创建表（开发环境）
    create_tables()

# main.py
from app.config import setup_database

if __name__ == "__main__":
    setup_database()  # 应用启动时配置
    # ... 其他代码
```

> 💡 **AI 提示词：** "我的 rhosocial-activerecord 模型提示 'No backend configured'，请帮我写一个完整的配置示例。"

---

## FieldProxy 未定义

### 症状

- IDE 无法自动补全查询字段（如 `User.c.name`）
- 运行时报错：`AttributeError: 'FieldProxy' object has no attribute 'xxx'`
- 查询时类型检查失败

### 原因

忘记在模型中定义 `c` 字段，或使用了错误的类型注解。

### 解决

确保每个模型都正确定义 `FieldProxy`：

```python
from typing import ClassVar
from rhosocial.activerecord.base import FieldProxy

class User(ActiveRecord):
    # ❌ 错误：没有定义 FieldProxy
    name: str
    
    # ✅ 正确：定义 ClassVar 类型的 FieldProxy
    c: ClassVar[FieldProxy] = FieldProxy()
    name: str
```

### 常见错误

```python
# ❌ 错误 1：不是 ClassVar
class User(ActiveRecord):
    c = FieldProxy()  # Pydantic 会把它当作模型字段

# ❌ 错误 2：类型注解错误
class User(ActiveRecord):
    c: FieldProxy = FieldProxy()  # 缺少 ClassVar

# ❌ 错误 3：位置错误（在字段之后）
class User(ActiveRecord):
    name: str
    c: ClassVar[FieldProxy] = FieldProxy()  # 应该在最前面

# ✅ 正确
class User(ActiveRecord):
    c: ClassVar[FieldProxy] = FieldProxy()
    name: str
    email: str
```

> 💡 **AI 提示词：** "为什么 rhosocial-activerecord 需要 FieldProxy？解释 ClassVar 的作用。"

---

## 导入错误

### 症状

```python
ModuleNotFoundError: No module named 'rhosocial'
```

### 原因 1：包未安装

```bash
# ❌ 错误：直接使用源码但没有安装
python my_script.py  # 报错
```

### 解决 1：安装包

```bash
# 从 PyPI 安装
pip install rhosocial-activerecord

# 或从本地源码安装（开发模式）
cd /path/to/rhosocial-activerecord
pip install -e .
```

### 原因 2：PYTHONPATH 未设置

如果你直接使用源码而不安装，需要设置 `PYTHONPATH`。

### 解决 2：设置 PYTHONPATH

```bash
# macOS/Linux
export PYTHONPATH=/path/to/src:$PYTHONPATH
python my_script.py

# Windows PowerShell
$env:PYTHONPATH = "C:\path\to\src;$env:PYTHONPATH"
python my_script.py

# Windows CMD
set PYTHONPATH=C:\path\to\src;%PYTHONPATH%
python my_script.py
```

### IDE 中设置 PYTHONPATH

**VS Code:**
在项目根目录创建 `.env` 文件：
```
PYTHONPATH=src
```

**PyCharm:**
1. Run → Edit Configurations
2. Environment variables 添加：`PYTHONPATH=src`

> 💡 **AI 提示词：** "如何在 VS Code / PyCharm 中设置 PYTHONPATH 以便开发 rhosocial-activerecord？"

### 原因 3：错误的导入语句

```python
# ❌ 错误：不能直接导入 rhosocial.activerecord
from rhosocial.activerecord import ActiveRecord  # ModuleNotFoundError!
```

### 解决 3：使用正确的导入路径

```python
# ✅ 正确：从 model 模块导入
from rhosocial.activerecord.model import ActiveRecord

# ✅ 正确：导入其他常用组件
from rhosocial.activerecord.base import FieldProxy
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
from rhosocial.activerecord.field import TimestampMixin
```

### 为什么会这样？

`rhosocial.activerecord` 是一个**开放命名空间包**（namespace package），用于支持后端扩展插件（如 `rhosocial-activerecord-mysql`、`rhosocial-activerecord-postgres` 等）。因此它**没有 `__init__.py`** 文件，也就不能直接从中导入类。

所有核心功能都分散在各个子模块中：
- `rhosocial.activerecord.model` - `ActiveRecord` 和 `AsyncActiveRecord` 类
- `rhosocial.activerecord.base` - `FieldProxy` 等基础组件
- `rhosocial.activerecord.backend.impl.sqlite` - SQLite 后端
- `rhosocial.activerecord.field` - 字段 Mixin（如 `TimestampMixin`）
- `rhosocial.activerecord.relation` - 关系定义（如 `HasMany`）

> 💡 **AI 提示词：** "rhosocial-activerecord 为什么不能直接 `from rhosocial.activerecord import ActiveRecord`？"

---

## PYTHONPATH 问题（仅框架/后端开发者）

> ⚠️ **注意**：此问题仅影响**直接开发 rhosocial-activerecord 框架或其数据库后端的开发者**。普通用户通过 `pip install` 安装后不会遇到此问题。

### 场景

当你从源码直接运行框架或开发自定义后端时，没有使用 `pip install -e .` 进行编辑模式安装：

```bash
# 你是这样运行的（没有 pip install -e .）
git clone https://github.com/rhosocial/rhosocial-activerecord.git
cd rhosocial-activerecord
python -c "from rhosocial.activerecord.model import ActiveRecord"  # ModuleNotFoundError!
```

### 解决

#### 方案 1：编辑模式安装（推荐）

```bash
# 在框架源码目录下
pip install -e .

# 现在可以正常导入
python -c "from rhosocial.activerecord.model import ActiveRecord"
```

#### 方案 2：设置 PYTHONPATH

如果你不想安装，可以临时设置环境变量：

```bash
# macOS/Linux
export PYTHONPATH=src
pytest tests/

# Windows PowerShell
$env:PYTHONPATH = "src"
pytest tests/

# 或使用 Python -m pytest（项目根目录）
PYTHONPATH=src python -m pytest tests/
```

#### 方案 3：添加 conftest.py

在 `tests/` 目录下创建 `conftest.py`（适用于测试场景）：

```python
# tests/conftest.py
import sys
from pathlib import Path

# 添加 src 到路径
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))
```

### 对普通用户

如果你是普通用户，直接通过 pip 安装：

```bash
pip install rhosocial-activerecord
```

安装后即可正常使用，无需任何 PYTHONPATH 配置。

---

## 类型注解错误

### 错误 1：Python 3.8 兼容性问题

```python
# ❌ Python 3.8 不支持 list[str]（需要 from __future__ import annotations）
def get_users() -> list[User]:
    ...

# ✅ 兼容 Python 3.8
from typing import List

def get_users() -> List[User]:
    ...
```

### 错误 2：可选字段未标记 Optional

```python
# ❌ 缺少 Optional，Pydantic 会要求必须传入
class User(ActiveRecord):
    bio: str  # 报错：bio 是必需字段

# ✅ 正确标记可选
from typing import Optional

class User(ActiveRecord):
    bio: Optional[str] = None
    # 或
    bio: Optional[str] = Field(default=None)
```

### 错误 3：ClassVar 和普通字段混淆

```python
# ❌ 错误：FieldProxy 不是 ClassVar
class User(ActiveRecord):
    c: FieldProxy = FieldProxy()  # Pydantic 会尝试验证它

# ✅ 正确
class User(ActiveRecord):
    c: ClassVar[FieldProxy] = FieldProxy()
```

> 💡 **AI 提示词：** "rhosocial-activerecord 的类型注解最佳实践，特别是 ClassVar 和 Optional 的使用。"

---

## 同步异步混用

### 错误 1：在异步代码中使用同步模型

```python
# ❌ 错误：在 async 函数中使用同步模型
async def get_user():
    user = User(name="Alice")
    user.save()  # RuntimeError: cannot be used in async context
```

### 解决 1：使用异步模型

```python
# ✅ 正确
async def get_user():
    user = AsyncUser(name="Alice")
    await user.save()  # 使用 await
```

### 错误 2：忘记 await

```python
# ❌ 错误：忘记 await
async def get_user():
    user = await AsyncUser.find_one({'name': 'Alice'})
    posts = user.posts()  # 返回的是协程对象，不是列表

# ✅ 正确
async def get_user():
    user = await AsyncUser.find_one({'name': 'Alice'})
    posts = await user.posts()  # 记得 await
```

### 错误 3：混合使用同步和异步后端

```python
# ❌ 错误：User 配置了同步后端，AsyncUser 也配置了同步后端
User.configure(sync_config, SQLiteBackend)
AsyncUser.configure(sync_config, SQLiteBackend)  # 错误！

# ✅ 正确
User.configure(sync_config, SQLiteBackend)
AsyncUser.configure(async_config, AsyncSQLiteBackend)  # 使用异步后端
```

### 快速对照表

| 操作 | 同步 | 异步 |
|-----|------|------|
| 基类 | `ActiveRecord` | `AsyncActiveRecord` |
| 后端 | `SQLiteBackend` | `AsyncSQLiteBackend` |
| 保存 | `user.save()` | `await user.save()` |
| 查询 | `User.find_one(...)` | `await AsyncUser.find_one(...)` |
| 关联 | `user.posts()` | `await user.posts()` |

> 💡 **AI 提示词：** "rhosocial-activerecord 同步和异步模型的区别，如何避免混用错误？"

---

## 数据库连接问题

### 错误 1：数据库文件路径错误

```python
# ❌ 相对路径可能导致找不到文件
config = SQLiteConnectionConfig(database='app.db')
# 取决于当前工作目录，可能在不同目录运行时会找不到

# ✅ 使用绝对路径
from pathlib import Path

db_path = Path(__file__).parent / "app.db"
config = SQLiteConnectionConfig(database=str(db_path))
```

### 错误 2：权限问题

```python
# ❌ 在只读目录创建数据库
config = SQLiteConnectionConfig(database='/var/lib/app.db')  # 权限不足

# ✅ 确保有写入权限
config = SQLiteConnectionConfig(database='/home/user/app.db')
```

### 错误 3：连接泄漏

```python
# ❌ 多次配置导致连接混乱
User.configure(config1, SQLiteBackend)
User.configure(config2, SQLiteBackend)  # 覆盖之前的配置

# ✅ 应用生命周期内只配置一次
```

### 错误 4：内存数据库在连接间不共享

```python
# ❌ 每个模型使用独立的内存数据库
User.configure(SQLiteConnectionConfig(database=':memory:'), SQLiteBackend)
Post.configure(SQLiteConnectionConfig(database=':memory:'), SQLiteBackend)  # 不同的数据库！

# ✅ 共享同一个后端
backend = SQLiteBackend(SQLiteConnectionConfig(database=':memory:'))
User.configure(backend)
Post.configure(backend)  # 共享连接
```

> 💡 **AI 提示词：** "rhosocial-activerecord SQLite 内存数据库如何共享连接？"

---

## 其他常见问题

### 表不存在错误

```python
OperationalError: no such table: users
```

**原因：** 忘记创建表或表名不匹配

**解决：**

```python
# 确保表名正确
class User(ActiveRecord):
    @classmethod
    def table_name(cls) -> str:
        return 'users'  # 确认与数据库表名一致

# 创建表
User.backend().execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY,
        name TEXT
    )
""")
```

### 字段验证失败

```python
ValidationError: 1 validation error for User
name
  ensure this value has at most 50 characters (type=value_error.any_str.max_length)
```

**解决：** 检查 Pydantic 验证规则

```python
class User(ActiveRecord):
    name: str = Field(..., max_length=50)  # 确保传入值符合要求
```

### 主键冲突

```python
IntegrityError: UNIQUE constraint failed: users.id
```

**解决：** 保存前检查是否为已存在实例

```python
if user.id is None:
    user.save()  # INSERT
else:
    user.save()  # UPDATE
```

---

## 仍有问题？

如果以上方案无法解决你的问题：

1. **查看详细错误信息**：`python -v my_script.py` 获取完整堆栈
2. **开启调试模式**：设置环境变量 `DEBUG=1`
3. **提交 Issue**：到 GitHub 提交问题，附带：
   - Python 版本
   - 完整错误信息
   - 最小可复现代码

> 💡 **AI 提示词：** "我遇到了 [错误描述]，这是我的代码：[粘贴代码]，请帮我找出问题。"

---

## 另请参阅

- [安装指南](installation.md) — 完整安装步骤
- [配置](configuration.md) — 数据库配置详解
- [第一个 CRUD 应用](first_crud.md) — 完整入门示例
