# GraphQL Integration

GraphQL is a powerful API query language that lets clients request exactly the data they need. `rhosocial-activerecord` integrates seamlessly with Python GraphQL libraries such as `graphene`.

This chapter demonstrates a social-network API with `User`, `Post`, and `Comment`, served by FastAPI.

> The complete runnable example lives in `docs/examples/chapter_14_scenarios/graphql_fastapi/`; its tests all pass.

## Core Architecture

*   **Web framework**: FastAPI (async)
*   **GraphQL library**: Graphene (async execution)
*   **ORM**: rhosocial-activerecord (async SQLite, `AsyncActiveRecord`)
*   **Concurrency model**: `AsyncBackendPool` + request-level `contextvar` isolation (same as the [FastAPI scenario](fastapi.md))
*   **N+1 optimization**: `aiodataloader` for batch loading
*   **Table creation**: derived DDL via `generate_create_table()` — no handwritten SQL

## Table of Contents

1. [Understanding the GraphQL Schema](#1-understanding-the-graphql-schema)
2. [Model Definitions](#2-model-definitions)
3. [Database: Connection Pool + Derived DDL](#3-database-connection-pool--derived-ddl)
4. [Defining the Schema (Type + Resolver)](#4-defining-the-schema-type--resolver)
5. [Solving the N+1 Problem (DataLoader)](#5-solving-the-n1-problem-dataloader)
6. [FastAPI Service Entry](#6-fastapi-service-entry)
7. [How Developers Use GraphQL](#7-how-developers-use-graphql)
8. [Verifying in Postman](#8-verifying-in-postman)
9. [Running and Testing](#9-running-and-testing)
10. [Common Issues](#10-common-issues)

## 1. Understanding the GraphQL Schema

**The schema is the heart of GraphQL** — and the biggest difference from REST. In REST, each endpoint (e.g. `GET /users/:id`) has a hard-coded response shape. In GraphQL, the server declares, via a **schema**, "what the client may query and which fields each object has", and the client picks what it needs.

```
┌─────────────┐   schema declares types & fields   ┌──────────────────┐
│  Client/tool │ ────────────────────────────────► │  Schema          │
│  (Postman…)  │ ◄──────────────────────────────── │  query { users } │
└─────────────┘        introspection discovery     └──────────────────┘
```

### Three Questions the Schema Answers

| Question | Schema element | This example |
|----------|----------------|--------------|
| What queries can I run? | `Query` type (root type) | `users`, `posts`, `user(id)`, `post(id)` |
| What does each object look like? | `ObjectType` | `UserType`, `PostType`, `CommentType` |
| Is a field a scalar/list/required? | Field types `String`/`[PostType]`, `!` non-null | `id: String`, `posts: [PostType]` |

**Model vs schema type**: an `ActiveRecord` model (`User`) describes a **database table**; a GraphQL type (`UserType`) describes the **shape of the exposed API**. They need not match — the schema only exposes the fields you explicitly declare, acting as an "interface allow-list".

### Making the Schema Visible: Printing & Introspection

A schema can be printed as standard Schema Definition Language (SDL):

```python
from app.schema import schema

print(schema)
# outputs:
# type Query {
#   users: [UserType]
#   user(id: String!): UserType
#   ...
# }
# type UserType {
#   id: String
#   username: String
#   ...
# }
```

Clients (GraphiQL, Postman) discover your API automatically through the standard **`__schema` introspection query** — no extra docs needed:

```graphql
query IntrospectionQuery {
  __schema {
    queryType { name }
    types { name kind }
  }
}
```

> Once defined, the schema is the **contract between frontend and backend**: adding/removing fields is reflected in it, and clients get autocomplete from introspection.

## 2. Model Definitions

Define three related models, enable `FieldProxy`, and declare column types with `UseSqlType`:

```python
# app/models.py
import uuid
from typing import Annotated, ClassVar

from rhosocial.activerecord.base import FieldProxy, UseSqlType
from rhosocial.activerecord.backend.expression.types import TextType, VarCharType
from rhosocial.activerecord.field import DefaultTimestampMixin, UUIDMixin
from rhosocial.activerecord.model import AsyncActiveRecord
from rhosocial.activerecord.relation import AsyncBelongsTo, AsyncHasMany


class User(UUIDMixin, DefaultTimestampMixin, AsyncActiveRecord):
    __table_name__ = "users"

    username: Annotated[str, UseSqlType(VarCharType(length=50))]
    email: Annotated[str, UseSqlType(VarCharType(length=120))]

    c: ClassVar[FieldProxy] = FieldProxy()
    posts: ClassVar[AsyncHasMany["Post"]] = AsyncHasMany(foreign_key="user_id", inverse_of="user")
    comments: ClassVar[AsyncHasMany["Comment"]] = AsyncHasMany(foreign_key="user_id", inverse_of="user")


class Post(UUIDMixin, DefaultTimestampMixin, AsyncActiveRecord):
    __table_name__ = "posts"

    user_id: uuid.UUID
    title: Annotated[str, UseSqlType(VarCharType(length=200))]
    content: Annotated[str, UseSqlType(TextType())]

    c: ClassVar[FieldProxy] = FieldProxy()
    user: ClassVar[AsyncBelongsTo["User"]] = AsyncBelongsTo(foreign_key="user_id", inverse_of="posts")
    comments: ClassVar[AsyncHasMany["Comment"]] = AsyncHasMany(foreign_key="post_id", inverse_of="post")


class Comment(UUIDMixin, DefaultTimestampMixin, AsyncActiveRecord):
    __table_name__ = "comments"

    user_id: uuid.UUID
    post_id: uuid.UUID
    content: Annotated[str, UseSqlType(TextType())]

    c: ClassVar[FieldProxy] = FieldProxy()
    user: ClassVar[AsyncBelongsTo["User"]] = AsyncBelongsTo(foreign_key="user_id", inverse_of="comments")
    post: ClassVar[AsyncBelongsTo["Post"]] = AsyncBelongsTo(foreign_key="post_id", inverse_of="comments")
```

## 3. Database: Connection Pool + Derived DDL

Exactly the same pool pattern as the FastAPI scenario (see [FastAPI Integration · Connection Pool & Derived DDL](fastapi.md#4-connection-pool--derived-ddl)):

```python
# app/database.py
from typing import AsyncGenerator, List, Type

from fastapi import Request
from rhosocial.activerecord.backend.impl.sqlite import AsyncSQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType
from rhosocial.activerecord.connection.pool import AsyncBackendPool, PoolConfig
from rhosocial.activerecord.interface.model import IAsyncActiveRecord


async def create_pool(config: SQLiteConnectionConfig) -> AsyncBackendPool:
    pool_config = PoolConfig(
        min_size=2, max_size=10, connection_mode="auto",
        backend_factory=lambda: AsyncSQLiteBackend(connection_config=config),
    )
    return await AsyncBackendPool.create(pool_config)


async def create_schema(models: List[Type[IAsyncActiveRecord]]) -> None:
    options = ExecutionOptions(stmt_type=StatementType.DDL)
    for model in models:
        expr = model.generate_create_table(if_not_exists=True)
        sql, params = expr.to_sql()
        await model.backend().execute(sql, params, options=options)


async def get_db_context(request: Request) -> AsyncGenerator[None, None]:
    """Borrow a dedicated connection for the current request (native async generator dependency)."""
    pool: AsyncBackendPool = request.app.state.pool
    async with pool.connection():
        yield
```

## 4. Defining the Schema (Type + Resolver)

Defining a schema is usually three steps:

1. Define an **`ObjectType`** for each model, declaring the fields it exposes;
2. Define the root **`Query`** type, declaring the available queries and their arguments;
3. Assemble them into a **`Schema`** instance.

### Step 1: Define ObjectTypes

Each `ObjectType` declares fields with Graphene field syntax (`String`, `Int`, `Field(...)`, `List(...)`) and pairs them with `resolve_*` methods as **resolvers** — deciding where the field's data comes from:

```python
# app/schema.py
from graphene import Field, List, ObjectType, Schema, String


class UserType(ObjectType):
    id = String()
    username = String()
    email = String()
    posts = List(lambda: PostType)          # relation: a User's posts

    async def resolve_posts(root, info):
        # root is the User model instance; return its posts
        return await info.context["loaders"].posts_by_user_loader.load(root.id)


class PostType(ObjectType):
    id = String()
    title = String()
    content = String()
    user = Field(UserType)
    comments = List(lambda: CommentType)

    async def resolve_user(root, info):
        return await info.context["loaders"].user_loader.load(root.user_id)

    async def resolve_comments(root, info):
        return await info.context["loaders"].comments_by_post_loader.load(root.id)


class CommentType(ObjectType):
    id = String()
    content = String()
    user = Field(UserType)
    post = Field(PostType)

    async def resolve_user(root, info):
        return await info.context["loaders"].user_loader.load(root.user_id)

    async def resolve_post(root, info):
        return await info.context["loaders"].post_loader.load(root.post_id)
```

> `root` (the resolver's first argument) is the object returned by the parent field. `info.context` carries request-level context — here we put `loaders` (the DataLoader set) there for resolvers.

### Step 2: Define the Root Query Type

`Query` is the **entry point** for GraphQL queries. `user(id: String!)` declares a query field with a required `id` argument:

```python
# app/schema.py (continued)
class Query(ObjectType):
    users = List(UserType)
    posts = List(PostType)
    user = Field(UserType, id=String(required=True))
    post = Field(PostType, id=String(required=True))

    async def resolve_users(root, info):
        return await User.find_all()

    async def resolve_posts(root, info):
        return await Post.find_all()

    async def resolve_user(root, info, id):
        return await User.find_one(id)

    async def resolve_post(root, info, id):
        return await Post.find_one(id)
```

### Step 3: Assemble the Schema

```python
# app/schema.py (end)
schema = Schema(query=Query)
```

> A schema exposing only `Query` means a **read-only** API. To support writes, define a `Mutation` type and pass it via `Schema(query=..., mutation=...)` — this example focuses on queries and N+1 optimization, so it omits mutations.

## 5. Solving the N+1 Problem (DataLoader)

The most common GraphQL performance trap is the N+1 problem: querying 10 posts' authors can trigger 1 post query + 10 user queries.

We use `aiodataloader` (async DataLoader). **Because the models are async, `batch_load_fn` directly `await`s queries** — no `run_in_threadpool` needed.

```python
# app/schema.py
from aiodataloader import DataLoader
from .models import Comment, Post, User


class UserLoader(DataLoader):
    async def batch_load_fn(self, keys):
        users = await User.query().where(User.c.id.in_(keys)).all()
        user_map = {str(u.id): u for u in users}
        return [user_map.get(str(k)) for k in keys]


class PostsByUserLoader(DataLoader):
    async def batch_load_fn(self, user_ids):
        posts = await Post.query().where(Post.c.user_id.in_(user_ids)).all()
        from collections import defaultdict

        posts_by_user = defaultdict(list)
        for post in posts:
            posts_by_user[str(post.user_id)].append(post)
        return [posts_by_user.get(str(uid), []) for uid in user_ids]


class CommentsByPostLoader(DataLoader):
    async def batch_load_fn(self, post_ids):
        comments = await Comment.query().where(Comment.c.post_id.in_(post_ids)).all()
        from collections import defaultdict

        comments_by_post = defaultdict(list)
        for comment in comments:
            comments_by_post[str(comment.post_id)].append(comment)
        return [comments_by_post.get(str(pid), []) for pid in post_ids]


class Loaders:
    """Create a fresh set of DataLoaders per request to avoid cross-request cache bleed."""

    def __init__(self):
        self.user_loader = UserLoader()
        self.post_loader = PostLoader()
        self.posts_by_user_loader = PostsByUserLoader()
        self.comments_by_post_loader = CommentsByPostLoader()
```

> **Why create a fresh `Loaders` per request**: DataLoader caches keys already loaded in this batch. Reusing a cross-request DataLoader could let one request read stale data from another's cache. A fresh instance per request guarantees freshness.

## 6. FastAPI Service Entry

```python
# app/main.py
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse

from .database import (configure_models, create_pool, create_schema,
                       get_db_context, make_connection_config)
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


app = FastAPI(title="Blog GraphQL API",
              description="rhosocial-activerecord + Graphene + FastAPI",
              version="1.0.0", lifespan=lifespan)


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
```

Key points:

- **`schema.execute_async`**: Graphene's async execution entry point (resolvers are coroutines, so async execution is required).
- **`get_db_context` dependency**: mounted on the whole `/graphql` route — all resolvers within a single GraphQL query share one request connection.
- **`context`**: `loaders` are placed into the GraphQL context and accessed by resolvers via `info.context["loaders"]`.

### GraphiQL Interactive Interface

`GET /graphql` returns an interactive GraphiQL page with a docs explorer and autocomplete:

```python
@app.get("/graphql")
async def graphiql_interface():
    html = """<!DOCTYPE html>
    <html><head>
      <link rel="stylesheet" href="https://unpkg.com/graphiql/graphiql.min.css" />
    </head><body>
      <div id="graphiql">Loading...</div>
      <script crossorigin src="https://unpkg.com/react@18/umd/react.development.js"></script>
      <script crossorigin src="https://unpkg.com/react-dom@18/umd/react-dom.development.js"></script>
      <script crossorigin src="https://unpkg.com/graphiql/graphiql.min.js"></script>
      <script>
        const root = ReactDOM.createRoot(document.getElementById('graphiql'));
        root.render(React.createElement(GraphiQL, {
          fetcher: GraphiQL.createFetcher({ url: '/graphql' })
        }));
      </script>
    </body></html>"""
    return HTMLResponse(html)
```

## 7. How Developers Use GraphQL

To callers (frontend, Postman, scripts), GraphQL has **a single endpoint** (`POST /graphql`); every query is described in the request body.

### Request Format

Clients send JSON to `POST /graphql`:

| Field | Required | Description |
|-------|----------|-------------|
| `query` | ✅ | the GraphQL query string |
| `variables` | optional | variables dict (matching `$var` in the query) |
| `operationName` | optional | which operation to run when the body has several |

```json
{
  "query": "query GetUser($id: String!) { user(id: $id) { id username email } }",
  "variables": { "id": "550e8400-e29b-41d4-a716-446655440000" }
}
```

### Basic Queries: Request Only the Fields You Need

Clients **request only the fields they need** — GraphQL's core strength:

```graphql
query {
  users {
    id
    username
  }
}
```

The response contains **only** the requested fields:

```json
{
  "data": {
    "users": [
      { "id": "550e8400-...", "username": "alice" }
    ]
  }
}
```

### Nested Queries & Aliases

Traverse several relation levels at once (where the N+1 fix pays off):

```graphql
query {
  users {
    username
    posts {
      title
      comments {
        content
      }
    }
  }
}
```

To query the same field twice with different results, use an **alias**:

```graphql
query {
  firstUser: users { username }
  firstPost: posts { title }
}
```

### Variables & Required Arguments

A single-user query with a required `id` argument:

```graphql
query GetUser($id: String!) {
  user(id: $id) {
    id
    username
    email
  }
}
```

Together with the body's `variables`:

```json
{ "query": "query GetUser($id: String!) { ... }", "variables": { "id": "..." } }
```

### Fragments for Reuse

Reuse a common field set with fragments:

```graphql
query {
  users {
    ...UserSummary
    posts { title }
  }
  posts {
    user { ...UserSummary }
  }
}

fragment UserSummary on UserType {
  id
  username
}
```

### Error Responses

On errors the server returns `errors`; other fields are unaffected:

```json
{
  "errors": [{ "message": "Relation 'x' not found ..." }]
}
```

### Explore with Introspection

Discover the available queries and fields without docs:

```graphql
{
  __schema {
    queryType { name }
    types { name }
  }
}
```

## 8. Verifying in Postman

Postman has native GraphQL support: send requests, manage variables, view docs, and get autocomplete.

### Method A: Postman GraphQL Request Type (Recommended)

1. **Create a request**: click `New` → `HTTP Request`.
2. **Set method and URL**: method `POST`, URL `http://localhost:8000/graphql`.
3. **Switch Body to GraphQL**: in the Body tab choose **GraphQL** (instead of `raw`). Postman reads the server's introspection and enables **Docs** and autocomplete on the right.
4. **In the Query editor type**:

   ```graphql
   query {
     users {
       id
       username
       posts {
         title
       }
     }
   }
   ```

5. Click **Send** and view the returned JSON `data` below.

### Method B: Plain JSON POST (equivalent)

A GraphQL endpoint is just a JSON POST. If you prefer not to use the GraphQL type:

1. New request, method `POST`, URL `http://localhost:8000/graphql`.
2. Body → **raw**, type **JSON**:

   ```json
   {
     "query": "{ users { id username } }"
   }
   ```

3. Send; you get `{"data":{"users":[...]}}`.

### Using Variables

1. Declare a variable in the query: `query GetUser($id: String!) { user(id: $id) { username } }`
2. Under the query, open the **Variables** tab (GraphQL type) or add `variables` to the JSON body (JSON type):

   ```json
   { "id": "550e8400-e29b-41d4-a716-446655440000" }
   ```

### History & Collections

- Every request appears in the left **History**.
- Save requests into a **Collection** for sharing/running with your team.
- Use Postman **environment variables** (e.g. `{{graphql_url}}`) to switch environments.

### Handy Verification Queries

| Purpose | Query |
|---------|-------|
| List all users | `{ users { id username email } }` |
| One user + their posts | `query($id: String!){ user(id:$id){ username posts{ title } } }` |
| Posts + author + comments | `{ posts { title user{username} comments{content} } }` |
| Discover the schema | `{ __schema { types { name } } }` |

> **Tip**: start the server first (`uvicorn app.main:app --reload --port 8000`). Postman's GraphQL type reads introspection automatically; if autocomplete does not appear, run `{ __schema { types { name } } }` once to trigger the introspection cache.

## 9. Running and Testing

### Start

```bash
uvicorn app.main:app --reload --port 8000
```

Visit `http://localhost:8000/graphql` (GraphiQL).

### Integration Tests

The example ships `tests/test_graphql.py`:

```bash
PYTHONPATH=docs/examples/chapter_14_scenarios/graphql_fastapi \
    pytest -o asyncio_mode=auto docs/examples/chapter_14_scenarios/graphql_fastapi/tests/
```

## 10. Common Issues

### Why does `schema.execute` report "can't be awaited"?

graphene's `Schema.execute` is a **sync** entry point; when resolvers are `async`, you must use **`schema.execute_async`**:

```python
# ❌
result = await schema.execute(query, ...)

# ✅
result = await schema.execute_async(query, ...)
```

### Why does the query return empty data?

If seed data is inserted in a **separate event loop** from the one running the requests, the pool fails across loops or reads empty data. Be sure to put "pool → create schema → seed → requests → close" inside the **same** `asyncio.run()` (as the example tests do).

### Why is a field null?

- The field's resolver raised: look at the response `errors`.
- Related data not loaded: confirm the resolver uses the DataLoader and the context is passed.
- The attribute on the model instance is genuinely empty (e.g. a user with no posts — `posts` should be `[]`, not `null`).

### How do I add writes (Mutation)?

The current schema exposes only `Query` (read-only). Add writes by defining a `Mutation`:

```python
from graphene import Mutation, String

class CreateUser(Mutation):
    class Arguments:
        username = String(required=True)
        email = String(required=True)

    user = Field(lambda: UserType)

    async def mutate(root, info, username, email):
        user = User(username=username, email=email)
        await user.save()
        return CreateUser(user=user)


class Mutation(ObjectType):
    create_user = CreateUser.Field()


schema = Schema(query=Query, mutation=Mutation)
```

Clients call it like this (the return type is the `user` field on `CreateUser`, so use a nested selection):

```graphql
mutation {
  createUser(username: "carol", email: "carol@example.com") {
    user {
      id
      username
    }
  }
}
```

### How to verify the N+1 fix?

Compare SQL counts with/without DataLoaders. DataLoaders merge N sub-queries into one `IN` query — exactly what `User.c.id.in_(keys)` does.

---

## Next Steps

- **[FastAPI Integration](fastapi.md)**: REST API + connection pool + Prometheus metrics
- **[Querying Interface](../querying/README.md)**: ActiveQuery / CTEQuery / SetOperationQuery