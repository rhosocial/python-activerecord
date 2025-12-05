#!/usr/bin/env python3
"""
高级 Pydantic 与 rhosocial ActiveRecord 集成演示（包含GraphQL预加载优化）
展示了如何在GraphQL环境中利用ActiveRecord的预加载功能解决N+1查询问题
"""

from typing import List, Optional, ClassVar
import sqlite3
import graphene
import logging
from graphene import ObjectType, String, Int, Boolean, List as GList
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import EmailStr, Field
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.relation.descriptors import HasMany, BelongsTo


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

-- 帖子表
CREATE TABLE IF NOT EXISTS posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    content TEXT,
    user_id INTEGER NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users (id)
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


# 定义 ActiveRecord 模型
class User(ActiveRecord):
    __table_name__ = 'users'

    id: Optional[int] = None
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    is_active: bool = True

    # 定义关系：一个用户有多个帖子 (使用ClassVar避免Pydantic将其视为普通字段)
    posts: ClassVar[HasMany["Post"]] = HasMany["Post"](
        foreign_key="user_id",
        inverse_of="user"
    )


class Post(ActiveRecord):
    __table_name__ = 'posts'

    id: Optional[int] = None
    title: str
    content: Optional[str] = None
    user_id: int

    # 定义关系：一个帖子属于一个用户 (使用ClassVar避免Pydantic将其视为普通字段)
    user: ClassVar[BelongsTo[User]] = BelongsTo[User](
        foreign_key="user_id",
        inverse_of="posts"
    )


# 配置模型后端
def configure_models(db_path: str = "demo.db"):
    """配置模型以使用SQLite后端"""
    config = SQLiteConnectionConfig(database=db_path)
    User.configure(config, SQLiteBackend)
    Post.configure(config, SQLiteBackend)


# GraphQL 类型定义
class UserGQL(ObjectType):
    id = Int(description="用户唯一标识符")
    name = String(description="用户名")
    email = String(description="用户邮箱")
    is_active = Boolean(description="用户是否激活", name="isActive")
    posts = GList(lambda: PostGQL, description="用户的所有帖子")

    @staticmethod
    def from_active_record(user: User, include_posts: bool = True) -> 'UserGQL':
        """从ActiveRecord模型实例创建GraphQL类型实例"""
        user_gql = UserGQL(
            id=user.id,
            name=user.name,
            email=user.email,
            is_active=user.is_active
        )

        if include_posts:
            # 如果用户实例的posts已经通过预加载加载，则使用缓存的值
            posts_relation = getattr(user, 'posts', None)  # 获取关系描述符
            if posts_relation is not None:
                # 调用关系以获取实际数据
                posts_data = posts_relation() if callable(posts_relation) else posts_relation
                if posts_data:
                    print(f"Cached posts({len(posts_data)}) found.")
                    user_gql.posts = [PostGQL.from_active_record(post) for post in posts_data]
                else:
                    print("Posts relation accessed but no data found.")
            else:
                print("No posts relation found.")
        return user_gql


class PostGQL(ObjectType):
    id = Int(description="帖子唯一标识符")
    title = String(description="帖子标题")
    content = String(description="帖子内容")
    user_id = Int(description="用户ID", name="userId")
    user = graphene.Field(lambda: UserGQL, description="帖子的作者")

    @staticmethod
    def from_active_record(post: Post, include_user: bool = True) -> 'PostGQL':
        """从ActiveRecord模型实例创建GraphQL类型实例"""
        post_gql = PostGQL(
            id=post.id,
            title=post.title,
            content=post.content,
            user_id=post.user_id
        )

        if include_user:
            # 如果帖子实例的user已经通过预加载加载，则使用缓存的值
            user_relation = getattr(post, 'user', None)  # 获取关系描述符
            if user_relation is not None:
                # 调用关系以获取实际数据
                user_data = user_relation() if callable(user_relation) else user_relation
                if user_data is not None:
                    post_gql.user = UserGQL.from_active_record(user_data, include_posts=False)

        return post_gql


# GraphQL 查询定义
class Query(ObjectType):
    user = graphene.Field(UserGQL, id=Int(required=True), description="根据ID获取特定用户")
    users = GList(UserGQL, description="获取所有用户（带帖子）")
    post = graphene.Field(PostGQL, id=Int(required=True), description="根据ID获取特定帖子")
    posts = GList(PostGQL, description="获取所有帖子（带作者）")

    def resolve_user(self, info, id: int) -> Optional[UserGQL]:
        """根据ID获取特定用户（带帖子）"""
        # 使用预加载避免N+1问题
        try:
            user = User.query().with_('posts').find_one(id)
            return UserGQL.from_active_record(user) if user else None
        except Exception as e:
            print(f"Error in resolve_user: {e}")
            raise

    def resolve_users(self, info) -> List[UserGQL]:
        """获取所有用户（带帖子）"""
        # 使用预加载避免N+1问题
        try:
            users = User.query().with_('posts').all()
            return [UserGQL.from_active_record(user) for user in users]
        except Exception as e:
            print(f"Error in resolve_users: {e}")
            # 如果with_导致问题，回退到基本查询
            users = User.query().all()
            return [UserGQL.from_active_record(user, include_posts=False) for user in users]

    def resolve_post(self, info, id: int) -> Optional[PostGQL]:
        """根据ID获取特定帖子（带作者）"""
        # 使用预加载避免N+1问题
        try:
            post = Post.query().with_('user').find_one(id)
            return PostGQL.from_active_record(post) if post else None
        except Exception as e:
            print(f"Error in resolve_post: {e}")
            raise

    def resolve_posts(self, info) -> List[PostGQL]:
        """获取所有帖子（带作者）"""
        # 使用预加载避免N+1问题
        try:
            posts = Post.query().with_('user').all()
            return [PostGQL.from_active_record(post) for post in posts]
        except Exception as e:
            print(f"Error in resolve_posts: {e}")
            # 如果with_导致问题，回退到基本查询
            posts = Post.query().all()
            return [PostGQL.from_active_record(post, include_user=False) for post in posts]


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


class CreatePost(graphene.Mutation):
    class Arguments:
        title = String(required=True)
        content = String()
        user_id = Int(required=True)

    Output = PostGQL

    def mutate(self, info, title: str, content: Optional[str], user_id: int):
        post = Post(title=title, content=content, user_id=user_id)
        post.save()
        return PostGQL.from_active_record(post)


class Mutation(ObjectType):
    create_user = CreateUser.Field()
    create_post = CreatePost.Field()


# 创建GraphQL Schema
schema = graphene.Schema(query=Query, mutation=Mutation)


# FastAPI 应用
app = FastAPI(
    title="高级 Pydantic & ActiveRecord GraphQL Demo",
    description="演示如何在GraphQL中利用ActiveRecord的预加载功能解决N+1查询问题",
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
    Post.setup_logger()
    logging.getLogger('activerecord').setLevel(logging.DEBUG)

    setup_database()  # 确保数据库被创建
    configure_models()  # 配置模型

    # 创建示例数据
    user_count = User.query().count()
    print(f"User count before creation: {user_count}")

    if user_count == 0:
        print("Creating sample data...")
        user1 = User(name="Alice Smith", email="alice@example.com", is_active=True)
        user1.save()
        print(f"Created user1 with id: {user1.id}")

        user2 = User(name="Bob Johnson", email="bob@example.com", is_active=True)
        user2.save()
        print(f"Created user2 with id: {user2.id}")

        post1 = Post(title="First Post", content="This is the first post", user_id=user1.id)
        post1.save()
        print(f"Created post1 with id: {post1.id}")

        post2 = Post(title="Second Post", content="This is the second post", user_id=user1.id)
        post2.save()
        print(f"Created post2 with id: {post2.id}")

        post3 = Post(title="Bob's Post", content="This is Bob's post", user_id=user2.id)
        post3.save()
        print(f"Created post3 with id: {post3.id}")

        print(f"Total users after creation: {User.query().count()}")
        print(f"Total posts after creation: {Post.query().count()}")
    else:
        print(f"Found existing {user_count} users, skipping sample data creation")


# GraphQL 集成
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
                                {{
                                    fetcher: GraphiQL.createFetcher({{ url: '/graphql' }}),
                                    document: `{schema_str}`,
                                }},
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
    # 设置数据库和模型
    setup_database()
    configure_models()

    print("GraphQL N+1优化演示")
    print("=====================")
    
    # 演示预加载与非预加载的性能差异
    print("\n场景1: 获取所有用户及其帖子（使用预加载）")
    print("查询: { users { id name email isActive posts { id title } } }")
    print(" - 使用User.query().with_('posts').all() - 2次数据库查询")
    print("   1次查询所有用户")
    print("   1次查询所有用户的帖子（通过user_id IN (...)）")

    print("\n场景2: 获取所有帖子及作者（使用预加载）")
    print("查询: { posts { id title user { id name email isActive } } }")
    print(" - 使用Post.query().with_('user').all() - 2次数据库查询")
    print("   1次查询所有帖子")
    print("   1次查询所有帖子的作者（通过id IN (...)）")

    print("\n场景3: 如果不使用预加载")
    print("查询: { users { id name email isActive posts { id title } } }")
    print(" - 使用普通查询 - N+1次数据库查询")
    print("   1次查询所有用户")
    print("   N次查询每个用户的帖子")
    
    print("\nGraphQL API 可通过 /graphql 端点访问")
    print("预加载功能确保了即使在复杂的嵌套查询中也能保持高性能")


if __name__ == "__main__":
    run_demo()