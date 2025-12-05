#!/usr/bin/env python3
"""
Pydantic 与 rhosocial ActiveRecord 集成演示（包含GraphQL支持）
展示了完整的流程，包括数据库模式、模型定义和 REST + GraphQL API 集成
"""

from typing import List, Optional
import sqlite3
import graphene
import logging
from graphene import ObjectType, String, Int, Boolean, List as GList, NonNull
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import EmailStr, Field
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig


# 启用调试日志
logging.basicConfig(level=logging.DEBUG)


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
async def startup_event():
    # 设置ActiveRecord模型的日志级别
    User.setup_logger()
    logging.getLogger('activerecord').setLevel(logging.DEBUG)

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
from graphql import graphql, graphql_sync, print_schema


class GraphQLApp:
    def __init__(self, schema):
        self.schema = schema

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            request = Request(scope, receive)

            if request.method == "GET":
                # 显示GraphiQL界面或返回GraphQL Schema
                # 构建schema文档
                try:
                    schema_str = print_schema(self.schema.graphql_schema)
                except:
                    schema_str = ''

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
                                    document: `{schema_str}`,
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

                result = graphql_sync(
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
    print("  查询所有用户: { users { id name email is_active } }")
    print("  查询特定用户: { user(id: 1) { id name email } }")
    print("  创建用户: mutation { createUser(name: \"John\", email: \"john@example.com\") { id name email } }")


if __name__ == "__main__":
    run_demo()