# docs/examples/chapter_14_scenarios/graphql_fastapi/app/main.py
"""FastAPI + Graphene GraphQL 服务入口。

- lifespan 中创建连接池并推导 DDL 建表
- ``/graphql`` POST 端点执行查询，GET 返回 GraphiQL 交互界面
- 每个请求经 ``get_db_context`` 依赖借出独立连接（contextvar 隔离）
"""
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse

from .database import configure_models, create_pool, create_schema, get_db_context, make_connection_config
from .models import Comment, Post, User
from .schema import Loaders, schema

ALL_MODELS = [User, Post, Comment]


@asynccontextmanager
async def lifespan(app: FastAPI):
    config = make_connection_config(database="graphql.db")
    configure_models(ALL_MODELS, config)
    pool = await create_pool(config)
    app.state.pool = pool

    async with pool.connection():
        await create_schema(ALL_MODELS)
        if await User.query().count() == 0:
            alice = User(username="alice", email="alice@example.com")
            await alice.save()
            bob = User(username="bob", email="bob@example.com")
            await bob.save()
            p1 = Post(user_id=alice.id, title="Hello GraphQL", content="A post about GraphQL.")
            await p1.save()
            p2 = Post(user_id=alice.id, title="FastAPI Integration", content="FastAPI + Graphene.")
            await p2.save()
            await Comment(user_id=bob.id, post_id=p1.id, content="Great post!").save()
            await Comment(user_id=alice.id, post_id=p1.id, content="Thanks Bob!").save()

    yield
    await pool.close()


app = FastAPI(
    title="博客 GraphQL API",
    description="rhosocial-activerecord + Graphene + FastAPI",
    version="1.0.0",
    lifespan=lifespan,
)


@app.post("/graphql", dependencies=[Depends(get_db_context)])
async def graphql_server(request: Request):
    try:
        data = await request.json()
    except Exception:
        data = {}

    query = data.get("query")
    variables = data.get("variables")
    operation_name = data.get("operationName")

    if not query:
        return JSONResponse({"errors": ["No query provided"]}, status_code=400)

    context = {"request": request, "loaders": Loaders()}
    result = await schema.execute_async(
        query,
        variable_values=variables,
        context_value=context,
        operation_name=operation_name,
    )

    response_data = {}
    if result.data:
        response_data["data"] = result.data
    if result.errors:
        response_data["errors"] = [{"message": str(e)} for e in result.errors]
    return JSONResponse(response_data)


@app.get("/graphql")
async def graphiql_interface():
    html = """
    <!DOCTYPE html>
    <html>
      <head>
        <style>body { margin: 0; width: 100%; height: 100vh; overflow: hidden; }</style>
        <link rel="stylesheet" href="https://unpkg.com/graphiql/graphiql.min.css" />
      </head>
      <body>
        <div id="graphiql">Loading...</div>
        <script
          crossorigin
          src="https://unpkg.com/react@18/umd/react.development.js"
        ></script>
        <script
          crossorigin
          src="https://unpkg.com/react-dom@18/umd/react-dom.development.js"
        ></script>
        <script
          crossorigin
          src="https://unpkg.com/graphiql/graphiql.min.js"
        ></script>
        <script>
          const root = ReactDOM.createRoot(document.getElementById('graphiql'));
          const fetcher = GraphiQL.createFetcher({ url: '/graphql' });
          root.render(React.createElement(GraphiQL, { fetcher: fetcher }));
        </script>
      </body>
    </html>
    """
    return HTMLResponse(html)


@app.get("/health")
async def health():
    return {"status": "healthy"}