# 11.2 GraphQL Integration

GraphQL is a powerful API query language that allows clients to request exactly the data they need. `rhosocial-activerecord` integrates seamlessly with Python GraphQL libraries like `graphene`.

This chapter demonstrates how to build a social network API containing `User`, `Post`, and `Comment` models, using FastAPI as the web server.

## Core Architecture

*   **Web Framework**: FastAPI (supports async)
*   **GraphQL Library**: Graphene (supports async execution)
*   **ORM**: rhosocial-activerecord (synchronous SQLite)
*   **Concurrency Model**: Since the ORM is synchronous while FastAPI and Graphene (v3+) are asynchronous, we utilize `starlette.concurrency.run_in_threadpool` to execute synchronous database queries in a thread pool, preventing blocking of the main event loop.
*   **N+1 Optimization**: Use `aiodataloader` for batch loading.

## 1. Model Definition

First, define three related models and enable `FieldProxy` to support type-safe query construction:

```python
# models.py
import uuid
from typing import ClassVar
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.base import FieldProxy
from rhosocial.activerecord.field import UUIDMixin, TimestampMixin
from rhosocial.activerecord.relation import BelongsTo, HasMany

class User(UUIDMixin, TimestampMixin, ActiveRecord):
    username: str
    email: str
    
    # Field Proxy
    c: ClassVar[FieldProxy] = FieldProxy()
    
    # Relations
    posts: ClassVar[HasMany['Post']] = HasMany(foreign_key='user_id')
    comments: ClassVar[HasMany['Comment']] = HasMany(foreign_key='user_id')

class Post(UUIDMixin, TimestampMixin, ActiveRecord):
    user_id: uuid.UUID
    title: str
    content: str
    
    # Field Proxy
    c: ClassVar[FieldProxy] = FieldProxy()
    
    # Relations
    user: ClassVar[BelongsTo['User']] = BelongsTo(foreign_key='user_id')
    comments: ClassVar[HasMany['Comment']] = HasMany(foreign_key='post_id')

class Comment(UUIDMixin, TimestampMixin, ActiveRecord):
    user_id: uuid.UUID
    post_id: uuid.UUID
    content: str
    
    # Field Proxy
    c: ClassVar[FieldProxy] = FieldProxy()
    
    # Relations
    user: ClassVar[BelongsTo['User']] = BelongsTo(foreign_key='user_id')
    post: ClassVar[BelongsTo['Post']] = BelongsTo(foreign_key='post_id')
```

## 2. Solving N+1 Problem (DataLoader)

The most common performance pitfall in GraphQL is the N+1 problem. For example, querying authors for 10 posts might trigger 1 query for posts + 10 queries for users.

We use `aiodataloader` (Async DataLoader) to solve this. Since `rhosocial-activerecord` is synchronous, we need to use `run_in_threadpool` inside `batch_load_fn` to execute actual database queries.

```python
# schema.py
from aiodataloader import DataLoader
from starlette.concurrency import run_in_threadpool
from models import User, Post, Comment

class UserLoader(DataLoader):
    async def batch_load_fn(self, keys):
        # Execute synchronous query in thread pool
        def load_users():
            # Use FieldProxy to build type-safe IN query
            users = User.query().where(User.c.id.in_(keys)).all()
            user_map = {str(u.id): u for u in users}
            return [user_map.get(str(k)) for k in keys]
            
        return await run_in_threadpool(load_users)

class CommentsByPostLoader(DataLoader):
    async def batch_load_fn(self, post_ids):
        def load_comments():
            comments = Comment.query().where(Comment.c.post_id.in_(post_ids)).all()
            
            from collections import defaultdict
            comments_by_post = defaultdict(list)
            for comment in comments:
                comments_by_post[str(comment.post_id)].append(comment)
                
            return [comments_by_post.get(str(pid), []) for pid in post_ids]
            
        return await run_in_threadpool(load_comments)
```

## 3. Defining Schema

Use Async Resolvers and DataLoaders in Graphene type definitions:

```python
# schema.py
import graphene
from graphene import ObjectType, String, Field, List

class UserType(ObjectType):
    id = String()
    username = String()
    email = String()
    posts = List(lambda: PostType)
    
    async def resolve_posts(root, info):
        return await info.context['loaders'].posts_by_user_loader.load(root.id)

class PostType(ObjectType):
    id = String()
    title = String()
    content = String()
    user = Field(UserType)
    comments = List(lambda: CommentType)
    
    async def resolve_user(root, info):
        return await info.context['loaders'].user_loader.load(root.user_id)
        
    async def resolve_comments(root, info):
        return await info.context['loaders'].comments_by_post_loader.load(root.id)

class CommentType(ObjectType):
    id = String()
    content = String()
    user = Field(UserType)
    post = Field(PostType)
    
    async def resolve_user(root, info):
        return await info.context['loaders'].user_loader.load(root.user_id)

    async def resolve_post(root, info):
        return await info.context['loaders'].post_loader.load(root.post_id)

class Query(ObjectType):
    users = List(UserType)
    posts = List(PostType)

    async def resolve_users(root, info):
        return await run_in_threadpool(lambda: User.find_all())

    async def resolve_posts(root, info):
        return await run_in_threadpool(lambda: Post.find_all())

schema = graphene.Schema(query=Query)
```

## 4. FastAPI Integration

To run GraphQL in asynchronous FastAPI, we need to:
1.  Initialize `Loaders` for each request.
2.  Use `schema.execute_async` to execute asynchronous GraphQL queries.

```python
# main.py
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse
from schema import schema, UserLoader, CommentsByPostLoader

app = FastAPI()

class Loaders:
    def __init__(self):
        self.user_loader = UserLoader()
        self.comments_by_post_loader = CommentsByPostLoader()
        # ... Initialize other loaders

@app.post("/graphql")
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

    # 1. Create context, including Loaders for this request
    context = {"request": request, "loaders": Loaders()}
    
    # 2. Execute asynchronous query
    result = await schema.execute_async(
        query,
        variable_values=variables,
        context_value=context,
        operation_name=operation_name
    )
    
    response_data = {}
    if result.data:
        response_data["data"] = result.data
    if result.errors:
        response_data["errors"] = [{"message": str(e)} for e in result.errors]
        
    return JSONResponse(response_data)

# Integrate GraphiQL Interface
@app.get("/graphql")
async def graphiql_interface():
    # Return GraphiQL HTML page (built with React)
    return HTMLResponse(...)
```

## Complete Example

The complete code example is located in the `docs/examples/chapter_09_scenarios/graphql_fastapi` directory.

This example includes:
*   Complete `User`, `Post`, `Comment` model definitions.
*   N+1 optimization implementation based on `aiodataloader`.
*   Integrated React-based GraphiQL interface for testing queries directly in the browser.

### Running the Example

```bash
cd docs/examples/chapter_09_scenarios/graphql_fastapi
pip install -r requirements.txt
python main.py
```

Visit `http://localhost:8000/graphql` to use the GraphiQL interface.
