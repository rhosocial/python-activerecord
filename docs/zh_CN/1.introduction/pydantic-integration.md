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

## 5. 与GraphQL的集成

rhosocial ActiveRecord 与 GraphQL 的集成提供了现代Web应用开发的强大功能。由于模型本身基于 Pydantic，可以轻松地与 GraphQL 框架（如 Graphene 或 Strawberry）集成：

**重要提示**: 在定义关系时，由于ActiveRecord继承自Pydantic的BaseModel，为了避免Pydantic将关系视为普通字段，需要使用`typing.ClassVar`类型提示来定义关系：

```python
from typing import ClassVar
from rhosocial.activerecord.relation.descriptors import HasMany, BelongsTo

class User(ActiveRecord):
    # 普通字段使用常规类型注释
    id: Optional[int] = None
    name: str

    # 关系必须使用ClassVar避免被Pydantic处理为普通字段
    posts: ClassVar = HasMany["Post"](
        foreign_key="user_id",
        inverse_of="user"
    )
```

这种做法确保了Pydantic的验证和序列化功能只应用于实际的数据字段，而不是关系描述符。

- **类型复用**: ActiveRecord 模型可以作为 GraphQL 类型的基础
- **验证复用**: Pydantic 验证器自动应用于 GraphQL 输入
- **数据一致性**: 相同的模型用于数据库操作和 API 响应
- **性能优化**: 利用 ActiveRecord 的预加载功能避免 N+1 查询问题

### GraphQL 集成示例

以下示例展示了如何将 rhosocial ActiveRecord 模型与 GraphQL 集成：

#### 完整示例代码

```python
#!/usr/bin/env python3
"""
Pydantic 与 rhosocial ActiveRecord 集成演示（包含GraphQL支持）
展示了完整的流程，包括数据库模式、模型定义和 REST + GraphQL API 集成
"""

from typing import List, Optional
import sqlite3
import graphene
from graphene import ObjectType, String, Int, Boolean, List as GList
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import EmailStr, Field
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig


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


# 立即配置模型后端
def configure_models(db_path: str = "demo.db"):
    """配置模型以使用SQLite后端"""
    config = SQLiteConnectionConfig(database=db_path)
    backend = SQLiteBackend(connection_config=config)

    # 为模型配置后端
    User.configure(config, SQLiteBackend)


# GraphQL 类型定义
class UserGQL(ObjectType):
    id = Int(description="用户唯一标识符")
    name = String(description="用户名")
    email = String(description="用户邮箱")
    is_active = Boolean(description="用户是否激活", name="isActive")

    @staticmethod
    def from_active_record(user: User) -> 'UserGQL':
        """从ActiveRecord模型实例创建GraphQL类型实例"""
        return UserGQL(
            id=user.id,
            name=user.name,
            email=user.email,
            is_active=user.is_active
        )


# GraphQL 查询定义
class Query(ObjectType):
    user = graphene.Field(UserGQL, id=Int(required=True), description="根据ID获取特定用户")
    users = GList(UserGQL, description="获取所有用户")

    def resolve_user(self, info, id: int) -> Optional[UserGQL]:
        """根据ID获取特定用户"""
        user = User.find_one(id)
        return UserGQL.from_active_record(user) if user else None

    def resolve_users(self, info) -> List[UserGQL]:
        """获取所有用户"""
        users = User.query().all()
        return [UserGQL.from_active_record(user) for user in users]


# GraphQL 变更定义
class CreateUser(graphene.Mutation):
    class Arguments:
        name = String(required=True)
        email = String(required=True)
        is_active = Boolean(default_value=True)

    Output = UserGQL

    def mutate(self, info, name: str, email: str, is_active: bool = True):
        user = User(name=name, email=email, is_active=is_active)
        user.save()
        return UserGQL.from_active_record(user)


class UpdateUser(graphene.Mutation):
    class Arguments:
        id = Int(required=True)
        name = String()
        email = String()
        is_active = Boolean()

    Output = UserGQL

    def mutate(self, info, id: int, name: Optional[str] = None, email: Optional[str] = None, is_active: Optional[bool] = None):
        user = User.find_one(id)
        if not user:
            return None

        if name is not None:
            user.name = name
        if email is not None:
            user.email = email
        if is_active is not None:
            user.is_active = is_active

        user.save()
        return UserGQL.from_active_record(user)


class DeleteUser(graphene.Mutation):
    class Arguments:
        id = Int(required=True)

    Output = Boolean

    def mutate(self, info, id: int):
        user = User.find_one(id)
        if not user:
            return False

        user.delete()
        return True


class Mutation(ObjectType):
    create_user = CreateUser.Field()
    update_user = UpdateUser.Field()
    delete_user = DeleteUser.Field()


# 创建GraphQL Schema
schema = graphene.Schema(query=Query, mutation=Mutation)


# FastAPI 应用
app = FastAPI(
    title="Pydantic & ActiveRecord Integration Demo with GraphQL",
    description="演示 Pydantic 与 rhosocial ActiveRecord 的无缝集成，支持 REST 和 GraphQL APIs",
    version="1.0.0"
)

# 添加 CORS 中间件以支持前端访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 在FastAPI应用启动时配置模型
@app.on_event("startup")
def startup_event():
    setup_database()  # 确保数据库被创建
    configure_models()

# 直接使用 ActiveRecord 模型作为 FastAPI 响应模型 - 保持原有的REST API
@app.get("/users/", response_model=List[User])
async def get_users_rest():
    """获取所有用户 (REST API)"""
    users = User.query().all()
    return users

@app.get("/users/{user_id}", response_model=User)
async def get_user_rest(user_id: int):
    """获取特定用户 (REST API)"""
    user = User.find_one(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.post("/users/", response_model=User)
async def create_user_rest(user: User):
    """创建新用户 (REST API)"""
    # 用户已由 Pydantic 验证
    user.save()
    return user


# GraphQL 集成 - 添加GraphQL endpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import Receive, Send
from graphql import graphql, print_schema


class GraphQLApp:
    def __init__(self, schema):
        self.schema = schema

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            request = Request(scope, receive)

            if request.method == "GET":
                # 显示GraphiQL界面或返回GraphQL Schema
                html_content = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>GraphiQL</title>
                    <script src="https://unpkg.com/react@^18/umd/react.development.js"></script>
                    <script src="https://unpkg.com/react-dom@^18/umd/react-dom.development.js"></script>
                    <link rel="stylesheet" href="https://unpkg.com/graphiql@^2/graphiql.min.css" />
                    <script src="https://unpkg.com/graphiql@^2/graphiql.min.js"></script>
                </head>
                <body style="margin: 0; overflow: hidden; width: 100%; height: 100vh;">
                    <div id="graphiql" style="height: 100vh;"></div>
                    <script>
                        const root = ReactDOM.createRoot(document.getElementById('graphiql'));
                        root.render(
                            React.createElement(
                                GraphiQL,
                                {
                                    fetcher: GraphiQL.createFetcher({{ url: '/graphql' }}),
                                    document: `{print_schema(self.schema)}`,
                                },
                            ),
                        );
                    </script>
                </body>
                </html>
                """
                response = Response(content=html_content, media_type="text/html")
                await response(scope, receive, send)
            elif request.method == "POST":
                content = await request.json()
                query = content.get("query")
                variables = content.get("variables")

                result = graphql(
                    self.schema.graphql_schema,
                    query,
                    variable_values=variables
                )

                response_data = {"data": result.data}
                if result.errors:
                    response_data["errors"] = [str(error) for error in result.errors]

                response = JSONResponse(response_data)
                await response(scope, receive, send)


graphql_app = GraphQLApp(schema=schema)
app.add_route("/graphql", graphql_app)


def run_demo():
    """运行完整演示流程"""
    # 1. 设置数据库
    setup_database()

    # 2. 配置模型
    configure_models()

    # 3. 演示数据操作
    # 使用时间戳确保唯一性
    import time
    timestamp = str(int(time.time()))
    new_user = User(name=f"Alice Smith {timestamp}", email=f"alice{timestamp}@example.com", is_active=True)
    new_user.save()
    print(f"已创建用户: {new_user.name} ({new_user.email})")

    # 4. 查询数据验证
    users = User.query().all()
    print(f"数据库中共有 {len(users)} 个用户")

    # 5. 演示 Pydantic 验证
    try:
        invalid_user = User(name="Test", email="invalid-email", is_active=True)
        print("邮箱验证失败 - 应该抛出异常但没有")
    except Exception as e:
        print(f"Pydantic 验证成功捕获无效邮箱: {type(e).__name__}")

    # 6. 演示GraphQL查询 (概念性)
    print("\nGraphQL API 可通过 /graphql 端点访问")
    print("示例查询:")
    print("  查询所有用户: { users { id name email isActive } }")
    print("  查询特定用户: { user(id: 1) { id name email } }")
    print("  创建用户: mutation { createUser(name: \"John\", email: \"john@example.com\") { id name email } }")


if __name__ == "__main__":
    run_demo()
```

### 运行应用

要运行包含GraphQL功能的应用，请执行以下命令：

```bash
# 安装GraphQL依赖
pip install graphene graphql-core

# 启动 FastAPI 服务器
uvicorn pydantic_graphql_demo:app --reload --port 8000
```

然后访问 `http://127.0.0.1:8000/graphql` 来查看 GraphiQL 界面进行GraphQL查询。

### GraphQL 接口使用示例

启动服务器后，您可以使用以下 GraphQL 接口：

#### 查询所有用户
```graphql
{
  users {
    id
    name
    email
    isActive
  }
}
```

#### 查询特定用户
```graphql
{
  user(id: 1) {
    id
    name
    email
    isActive
  }
}
```

#### 创建新用户
```graphql
mutation {
  createUser(name: "张三", email: "zhangsan@example.com", isActive: true) {
    id
    name
    email
    is_active
  }
}
```

#### 更新用户信息
```graphql
mutation {
  updateUser(id: 1, name: "张三修改") {
    id
    name
    email
    isActive
  }
}
```

#### 删除用户
```graphql
mutation {
  deleteUser(id: 1)
}
```

这种集成方式保留了 ActiveRecord 模型的所有功能，包括预加载、事务处理等，并且通过 GraphQL 提供了灵活的数据查询能力。

## 关系预加载与GraphQL优化

rhosocial ActiveRecord 拥有内置的关系预加载功能，可以有效解决 GraphQL 查询中常见的 N+1 问题。在 GraphQL 解析器中，你可以使用 `with_` 方法来预加载相关数据：

```python
# GraphQL 解析器中预加载相关数据
class Query(ObjectType):
    user_with_posts = graphene.Field(UserWithPostsGQL, id=Int(required=True))

    def resolve_user_with_posts(self, info, id: int):
        # 预加载用户和其所有帖子，避免N+1查询问题
        user = User.query().with_('posts').where('id = ?', (id, )).one()
        return UserWithPostsGQL.from_active_record(user)
```

以下是一个更复杂的示例，展示如何在关系模型中使用预加载：

```python
# 定义具有关系的模型
class User(ActiveRecord):
    __table_name__ = 'users'

    id: Optional[int] = None
    name: str
    email: EmailStr
    is_active: bool = True

    # 一个用户有多个帖子 (使用ClassVar避免Pydantic将其视为普通字段)
    posts: ClassVar = HasMany["Post"](
        foreign_key="user_id",
        inverse_of="user"
    )

class Post(ActiveRecord):
    __table_name__ = 'posts'

    id: Optional[int] = None
    title: str
    content: Optional[str]
    user_id: int

    # 一个帖子属于一个用户 (使用ClassVar避免Pydantic将其视为普通字段)
    user: ClassVar = BelongsTo[User](
        foreign_key="user_id",
        inverse_of="posts"
    )


# GraphQL 类型定义
class UserGQL(ObjectType):
    id = Int()
    name = String()
    email = String()
    is_active = Boolean(name="isActive")  # 使用camelCase字段名
    posts = GList(lambda: PostGQL)  # 用户的所有帖子

    @staticmethod
    def from_active_record(user: User, include_posts: bool = True) -> 'UserGQL':
        user_gql = UserGQL(
            id=user.id,
            name=user.name,
            email=user.email,
            is_active=user.is_active
        )
        # 如果预加载已执行，这里将使用缓存的关系数据
        if include_posts:
            posts_relation = getattr(user, 'posts', None)  # 获取关系描述符
            if posts_relation is not None:
                # 调用关系以获取实际数据
                posts_data = posts_relation() if callable(posts_relation) else posts_relation
                if posts_data:
                    user_gql.posts = [PostGQL.from_active_record(post) for post in posts_data]
        return user_gql


class PostGQL(ObjectType):
    id = Int()
    title = String()
    content = String()
    user_id = Int(name="userId")  # 使用camelCase字段名
    user = graphene.Field(lambda: UserGQL)  # 帖子的作者

    @staticmethod
    def from_active_record(post: Post, include_user: bool = True) -> 'PostGQL':
        post_gql = PostGQL(
            id=post.id,
            title=post.title,
            content=post.content,
            user_id=post.user_id
        )
        # 如果预加载已执行，这里将使用缓存的关系数据
        if include_user:
            user_relation = getattr(post, 'user', None)  # 获取关系描述符
            if user_relation is not None:
                # 调用关系以获取实际数据
                user_data = user_relation() if callable(user_relation) else user_relation
                if user_data is not None:
                    post_gql.user = UserGQL.from_active_record(user_data, include_posts=False)
        return post_gql


# GraphQL 查询定义，使用预加载优化
class Query(ObjectType):
    users = GList(UserGQL)  # 获取所有用户及其帖子
    posts = GList(PostGQL)  # 获取所有帖子及其作者

    def resolve_users(self, info):
        # 使用预加载一次性获取用户和他们的帖子，避免N+1查询
        users = User.query().with_('posts').all()
        return [UserGQL.from_active_record(user) for user in users]

    def resolve_posts(self, info):
        # 使用预加载一次性获取帖子和他们的作者，避免N+1查询
        posts = Post.query().with_('user').all()
        return [PostGQL.from_active_record(post) for post in posts]
```

通过这种方式，当GraphQL客户端请求嵌套数据（如`{ users { posts { title } } }`）时，后端只需要有限数量的数据库查询，而不是为每个关系进行单独查询。

这种设计确保了在使用 GraphQL 进行复杂查询时仍能保持高性能。

## 使用Postman测试GraphQL API

在启动应用后，您可以使用Postman来测试GraphQL API：

1. 使用uvicorn启动后,可以在postman中填写 http://localhost:8000/graphql 地址,并改为POST方法.
2. Body 切换到 GraphQL,并启用Auto Fetch.第一次可能需要手动点击"刷新"按钮.
3. 在 QUERY 框中可以填写查询,例如"{ users { id,posts { id,title } } }". 查询结果为:

```json
{
    "data": {
        "users": [
            {
                "id": 1,
                "posts": [
                    {
                        "id": 1,
                        "title": "First Post"
                    },
                    {
                        "id": 2,
                        "title": "Second Post"
                    }
                ]
            },
            {
                "id": 2,
                "posts": [
                    {
                        "id": 3,
                        "title": "Bob's Post"
                    }
                ]
            }
        ]
    }
}
```

这种无缝集成在没有额外转换层或辅助库的情况下，无法通过其他 ORM 实现。Pydantic 的验证功能直接在 ActiveRecord 模型中可用，使数据验证和类型检查成为数据库交互的自然部分。