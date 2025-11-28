# Pydantic 集成优势

rhosocial ActiveRecord 与 Pydantic 的紧密集成提供了显著的优势，值得特别关注：

## 1. 无缝生态系统集成

rhosocial ActiveRecord 模型可以直接与其他基于 Pydantic 的库和框架一起使用：

- **FastAPI**：模型可以用作请求/响应模式，无需转换
- **Pydantic Settings**：使用相同验证的配置管理
- **数据验证库**：适用于 pydantic-extra-types、email-validator 等
- **模式生成**：自动 OpenAPI 模式生成
- **数据转换**：使用 model_dump() 和 parse_obj() 进行简单的模型转换

## 2. 高级类型验证

rhosocial ActiveRecord 继承了 Pydantic 的强大验证能力：

- **复杂类型**：支持嵌套模型、联合类型、字面量和泛型
- **自定义验证器**：字段级和模型级验证函数
- **约束类型**：最小/最大值、字符串模式、长度约束
- **强制转换**：在可能的情况下自动类型转换
- **错误处理**：详细的验证错误消息

## 3. 模式演变和文档

- **JSON 模式生成**：将模型定义导出为 JSON 模式
- **自动文档**：模型是自文档化的，包含字段描述
- **模式管理**：使用版本字段跟踪模型更改
- **数据迁移**：在模式版本之间转换

## 4. 实际开发优势

- **IDE 集成**：更好的类型提示和自动完成
- **测试**：带验证的更精确模拟对象
- **错误预防**：在运行时捕获数据问题，防止它们到达数据库
- **代码重用**：对数据库访问、API 端点和业务逻辑使用相同的模型

## 集成示例

以下是一个完整的示例，展示了 rhosocial ActiveRecord 模型如何与 FastAPI 应用程序无缝集成：

### SQLite 数据库模式

```sql
-- 用户表
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    is_active BOOLEAN DEFAULT 1
);
```

### 完整示例代码

```python
#!/usr/bin/env python3
"""
完整 Pydantic 与 rhosocial ActiveRecord 集成示例
"""

from typing import List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr, Field
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
import sqlite3


# SQLite 数据库模式定义
sqlite_schema = """
-- 用户表
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    is_active BOOLEAN DEFAULT 1
);
"""


def setup_database(db_path: str = "demo.db"):
    """设置SQLite数据库，创建所需的表"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # 执行SQL模式
    cursor.executescript(sqlite_schema)
    conn.commit()
    conn.close()


# 使用 Pydantic 风格的类型注释定义 ActiveRecord 模型
class User(ActiveRecord):
    __table_name__ = 'users'

    id: Optional[int] = None
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    is_active: bool = True


def configure_models(db_path: str = "demo.db"):
    """配置模型以使用SQLite后端"""
    config = SQLiteConnectionConfig(database=db_path)
    backend = SQLiteBackend(connection_config=config)

    # 为模型配置后端
    User.configure(config, SQLiteBackend)


# FastAPI 应用
app = FastAPI(
    title="Pydantic & ActiveRecord Integration Demo",
    description="演示 Pydantic 与 rhosocial ActiveRecord 的无缝集成",
    version="1.0.0"
)

# 直接使用 ActiveRecord 模型作为 FastAPI 响应模型
@app.get("/users/", response_model=List[User])
async def get_users():
    """获取所有用户"""
    users = User.query().all()
    return users

@app.get("/users/{user_id}", response_model=User)
async def get_user(user_id: int):
    """获取特定用户"""
    user = User.find(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.post("/users/", response_model=User)
async def create_user(user: User):
    """创建新用户"""
    # 用户已由 Pydantic 验证
    user.save()
    return user


def run_demo():
    """运行完整演示流程"""
    # 1. 设置数据库
    setup_database()

    # 2. 配置模型
    configure_models()

    # 3. 演示数据操作
    new_user = User(name="Alice Smith", email="alice@example.com", is_active=True)
    new_user.save()

    # 4. 查询数据验证
    users = User.query().all()
    print(f"数据库中共有 {len(users)} 个用户")

    # 5. 演示 Pydantic 验证
    try:
        invalid_user = User(name="Test", email="invalid-email", is_active=True)
        print("邮箱验证失败 - 应该抛出异常但没有")
    except Exception as e:
        print(f"Pydantic 验证成功捕获无效邮箱: {type(e).__name__}")


if __name__ == "__main__":
    run_demo()
```

### 运行应用

要运行此应用，请执行以下命令：

```bash
# 启动 FastAPI 服务器
uvicorn pydantic_integration_demo:app --reload --port 8000
```

然后访问 `http://127.0.0.1:8000/docs` 来查看交互式 API 文档。

### 完整源代码

本示例的完整源代码可在以下位置找到：[pydantic_integration_demo.py](pydantic_integration_demo.py)

### FastAPI 接口使用示例

启动服务器后，您可以使用以下 API 接口：

#### 启动服务器

要启动FastAPI服务器，请切换到包含示例文件的目录并执行以下命令：

```bash
# 切换到示例文件所在目录
cd docs/zh_CN/1.introduction/

# 启动服务器
uvicorn pydantic_integration_demo:app --reload --port 8000
```

注意：模型会在服务器启动时自动配置数据库后端，确保在使用模型之前已正确初始化。

#### 获取所有用户
- **GET** `/users/`
- 示例：
```bash
curl http://127.0.0.1:8000/users/
```
- 使用 jq 美化输出：
```bash
curl http://127.0.0.1:8000/users/ | jq '.'
```
- 示例响应：
```json
[
  {
    "id": 1,
    "name": "Test User 1 1764297021",
    "email": "test11764297021@example.com",
    "is_active": true
  },
  {
    "id": 2,
    "name": "Test User 2 1764297021",
    "email": "test21764297021@example.com",
    "is_active": true
  }
]
```

#### 获取特定用户
- **GET** `/users/{user_id}`
- 示例：
```bash
curl http://127.0.0.1:8000/users/1
```
- 使用 jq 美化输出：
```bash
curl http://127.0.0.1:8000/users/1 | jq '.'
```
- 示例响应：
```json
{
  "id": 1,
  "name": "Test User 1 1764297021",
  "email": "test11764297021@example.com",
  "is_active": true
}
```

#### 创建新用户
- **POST** `/users/`
- 请求体：
```json
{
  "name": "张三",
  "email": "zhangsan@example.com",
  "is_active": true
}
```
- 示例：
```bash
curl -X POST http://127.0.0.1:8000/users/ \
  -H "Content-Type: application/json" \
  -d '{"name":"张三","email":"zhangsan@example.com","is_active":true}'
```
- 使用 jq 美化输出：
```bash
curl -X POST http://127.0.0.1:8000/users/ \
  -H "Content-Type: application/json" \
  -d '{"name":"张三","email":"zhangsan@example.com","is_active":true}' | jq '.'
```
- 示例响应：
```json
{
  "id": 3,
  "name": "张三",
  "email": "zhangsan@example.com",
  "is_active": true
}
```

这种无缝集成在没有额外转换层或辅助库的情况下，无法通过其他 ORM 实现。Pydantic 的验证功能直接在 ActiveRecord 模型中可用，使数据验证和类型检查成为数据库交互的自然部分。