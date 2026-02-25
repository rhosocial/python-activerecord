# FastAPI Integration

FastAPI is a modern, high-performance Python web framework that has a natural fit with `rhosocial-activerecord`—since `ActiveRecord` models are essentially `Pydantic` models, you can use them directly as FastAPI request bodies and response models without any additional serialization layer.

This chapter will guide you through building a complete **Blog System REST API** from scratch, including user management, article publishing, and relational queries. We will demonstrate the **asynchronous** implementation, which is the recommended pattern for FastAPI.

## Table of Contents

1. [Project Structure](#1-project-structure)
2. [Environment Setup](#2-environment-setup)
3. [Defining Models](#3-defining-models)
4. [Database Configuration](#4-database-configuration)
5. [Creating the FastAPI Application](#5-creating-the-fastapi-application)
6. [Implementing API Routes](#6-implementing-api-routes)
7. [Running and Testing](#7-running-and-testing)
8. [Best Practices](#8-best-practices)

## 1. Project Structure

First, let's plan the project directory structure:

```
my_blog_api/
├── app/
│   ├── __init__.py
│   ├── models.py          # Data model definitions
│   ├── database.py        # Database configuration
│   ├── schemas.py         # Pydantic request/response models (optional)
│   └── main.py            # FastAPI application entry point
├── tests/
│   └── test_api.py        # API tests
├── requirements.txt
└── README.md
```

## 2. Environment Setup

### 2.1 Installing Dependencies

Create `requirements.txt`:

```txt
fastapi>=0.100.0
uvicorn[standard]>=0.23.0
rhosocial-activerecord
aiosqlite>=0.19.0
```

Install dependencies:

```bash
pip install -r requirements.txt
```

### 2.2 Creating the Base Directory

```bash
mkdir -p app tests
touch app/__init__.py
```

## 3. Defining Models

We will define two models, `User` and `Post`, demonstrating a one-to-many relationship (a user can have multiple posts).

> **⚠️ Note**
> 
> This chapter uses asynchronous models (`AsyncActiveRecord`), which is the recommended pattern for FastAPI. All database operations require `await`.

Create `app/models.py`:

```python
# app/models.py
import uuid
from datetime import datetime
from typing import ClassVar, Optional, List
from pydantic import Field
from rhosocial.activerecord.model import AsyncActiveRecord
from rhosocial.activerecord.base import FieldProxy
from rhosocial.activerecord.field import UUIDMixin, TimestampMixin
from rhosocial.activerecord.relation import AsyncHasMany, AsyncBelongsTo


class User(UUIDMixin, TimestampMixin, AsyncActiveRecord):
    """User model."""
    
    username: str = Field(..., max_length=50, description="Username")
    email: str = Field(..., max_length=100, description="Email address")
    bio: Optional[str] = Field(default=None, max_length=500, description="User biography")
    is_active: bool = Field(default=True, description="Whether the user is active")
    
    # Enable type-safe query building
    c: ClassVar[FieldProxy] = FieldProxy()
    
    # Relationships: a user has many posts
    posts: ClassVar[AsyncHasMany['Post']] = AsyncHasMany(
        foreign_key='user_id',
        inverse_of='author'
    )

    @classmethod
    def table_name(cls) -> str:
        """Return table name."""
        return 'users'

    class Config:
        # Pydantic V2 configuration
        json_schema_extra = {
            "example": {
                "username": "john_doe",
                "email": "john@example.com",
                "bio": "Python developer",
                "is_active": True
            }
        }


class Post(UUIDMixin, TimestampMixin, AsyncActiveRecord):
    """Post model."""
    
    title: str = Field(..., max_length=200, description="Post title")
    content: str = Field(..., description="Post content")
    summary: Optional[str] = Field(default=None, max_length=500, description="Post summary")
    is_published: bool = Field(default=False, description="Whether the post is published")
    user_id: uuid.UUID = Field(..., description="Author ID")
    published_at: Optional[datetime] = Field(default=None, description="Publication time")
    
    # Enable type-safe query building
    c: ClassVar[FieldProxy] = FieldProxy()
    
    # Relationships: a post belongs to a user
    author: ClassVar[AsyncBelongsTo['User']] = AsyncBelongsTo(
        foreign_key='user_id',
        inverse_of='posts'
    )

    @classmethod
    def table_name(cls) -> str:
        """Return table name."""
        return 'posts'

    class Config:
        json_schema_extra = {
            "example": {
                "title": "Hello FastAPI",
                "content": "This is an article about FastAPI...",
                "summary": "FastAPI getting started guide",
                "is_published": True,
                "user_id": "550e8400-e29b-41d4-a716-446655440000"
            }
        }
```

## 4. Database Configuration

Create `app/database.py` to manage database connections:

```python
# app/database.py
import sys
from contextlib import asynccontextmanager
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType

# Import AsyncSQLiteBackend from test module
# Note: This is an async backend implementation for testing purposes
sys.path.insert(0, 'tests')
from rhosocial.activerecord_test.feature.backend.sqlite_async.async_backend import AsyncSQLiteBackend


class Database:
    """Database connection manager."""
    
    _config = None
    
    @classmethod
    def get_config(cls):
        """Get database configuration (singleton pattern)."""
        if cls._config is None:
            cls._config = SQLiteConnectionConfig(
                database='./blog.db',  # Use file-based database
                # database=':memory:'  # Use in-memory database (for testing)
            )
        return cls._config
    
    @classmethod
    async def init_models(cls):
        """Initialize models (create tables)."""
        from app.models import User, Post
        
        config = cls.get_config()
        
        # Configure models (requires both config and backend class)
        User.configure(config, AsyncSQLiteBackend)
        Post.configure(config, AsyncSQLiteBackend)
        
        # Connect to database
        backend = User.__backend__
        await backend.connect()
        
        # Create tables (if they don't exist)
        # Note: In real projects, use migration tools
        await cls._create_tables(backend)
    
    @classmethod
    async def _create_tables(cls, backend):
        """Create database tables."""
        options = ExecutionOptions(stmt_type=StatementType.DDL)
        
        # Create users table
        await backend.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                email TEXT UNIQUE NOT NULL,
                bio TEXT,
                is_active INTEGER DEFAULT 1,
                created_at TEXT,
                updated_at TEXT
            )
        """, options=options)
        
        # Create posts table
        await backend.execute("""
            CREATE TABLE IF NOT EXISTS posts (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                summary TEXT,
                is_published INTEGER DEFAULT 0,
                user_id TEXT NOT NULL,
                published_at TEXT,
                created_at TEXT,
                updated_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """, options=options)
    
    @classmethod
    async def close(cls):
        """Close database connection."""
        from app.models import User
        backend = User.__backend__
        if backend:
            await backend.disconnect()


@asynccontextmanager
async def get_db():
    """Context manager providing database session for async dependency injection."""
    from app.models import User
    backend = User.__backend__
    try:
        yield backend
    except Exception:
        # Add rollback logic here if needed
        raise
```

## 5. Creating the FastAPI Application

Create `app/main.py` as the application entry point:

```python
# app/main.py
from fastapi import FastAPI, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from typing import List, Optional
from contextlib import asynccontextmanager

from app.database import Database
from app.models import User, Post


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifecycle management."""
    # Initialize database on startup
    await Database.init_models()
    print("Database initialization complete")
    yield
    # Cleanup logic on shutdown
    await Database.close()
    print("Application shutting down")


app = FastAPI(
    title="Blog System API",
    description="Blog system built with rhosocial-activerecord + FastAPI",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/")
async def root():
    """API root path."""
    return {
        "message": "Welcome to the Blog System API",
        "docs": "/docs",
        "version": "1.0.0"
    }
```

## 6. Implementing API Routes

### 6.1 User Management Routes

```python
# app/main.py (append to end of file)

@app.post("/users/", response_model=User, status_code=status.HTTP_201_CREATED)
async def create_user(user: User):
    """
    Create a new user.
    
    - **username**: Username (required, max 50 characters)
    - **email**: Email address (required, max 100 characters)
    - **bio**: User biography (optional, max 500 characters)
    - **is_active**: Whether active (optional, defaults to true)
    """
    # Check if username already exists
    existing = await User.query().where(User.c.username == user.username).one()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Username '{user.username}' already exists"
        )
    
    # Check if email already exists
    existing = await User.query().where(User.c.email == user.email).one()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Email '{user.email}' is already registered"
        )
    
    await user.save()
    return user


@app.get("/users/", response_model=List[User])
async def list_users(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(10, ge=1, le=100, description="Number of records to return"),
    is_active: Optional[bool] = Query(None, description="Filter by active status")
):
    """Get user list (supports pagination and filtering)."""
    query = User.query()
    
    if is_active is not None:
        query = query.where(User.c.is_active == is_active)
    
    # For SQLite, we need to ensure both LIMIT and OFFSET are used correctly
    # Users can be sorted in ascending or descending order
    # Sort users by creation time in descending order (newest first)
    users = await query.order_by((User.c.created_at, "DESC")).limit(limit).offset(skip).all()
    return users


@app.get("/users/{user_id}", response_model=User)
async def get_user(user_id: str):
    """Get user details by ID."""
    user = await User.find_one(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User ID '{user_id}' not found"
        )
    return user


@app.put("/users/{user_id}", response_model=User)
async def update_user(user_id: str, user_update: User):
    """Update user information."""
    user = await User.find_one(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User ID '{user_id}' not found"
        )
    
    # Update fields (excluding primary key and relationship fields)
    update_data = user_update.model_dump(exclude={'id', 'posts'}, exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)
    
    await user.save()
    return user


@app.delete("/users/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: str):
    """Delete user (and all their posts)."""
    user = await User.find_one(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User ID '{user_id}' not found"
        )
    
    # Delete user (associated posts will be handled by foreign key constraints or manually deleted)
    await user.delete()
    return None
```

### 6.2 Post Management Routes

```python
# app/main.py (append)

@app.post("/posts/", response_model=Post, status_code=status.HTTP_201_CREATED)
async def create_post(post: Post):
    """
    Create a new post.
    
    - **title**: Title (required, max 200 characters)
    - **content**: Content (required)
    - **summary**: Summary (optional)
    - **is_published**: Whether published (optional, defaults to false)
    - **user_id**: Author ID (required)
    """
    # Validate author exists
    author = await User.find_one(str(post.user_id))
    if not author:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Author ID '{post.user_id}' not found"
        )
    
    await post.save()
    return post


@app.get("/posts/", response_model=List[Post])
async def list_posts(
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    is_published: Optional[bool] = Query(None),
    user_id: Optional[str] = Query(None, description="Filter by author")
):
    """Get post list (supports pagination and filtering)."""
    query = Post.query()
    
    if is_published is not None:
        query = query.where(Post.c.is_published == is_published)
    
    if user_id:
        query = query.where(Post.c.user_id == user_id)
    
    # For SQLite, we need to ensure both LIMIT and OFFSET are used correctly
    # Posts can be sorted in ascending or descending order
    # Sort posts by creation time in descending order (newest first)
    posts = await query.order_by((Post.c.created_at, "DESC")).limit(limit).offset(skip).all()
    return posts


@app.get("/posts/{post_id}", response_model=Post)
async def get_post(post_id: str):
    """Get post details by ID."""
    post = await Post.find_one(post_id)
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Post ID '{post_id}' not found"
        )
    return post


@app.put("/posts/{post_id}", response_model=Post)
async def update_post(post_id: str, post_update: Post):
    """Update post information."""
    post = await Post.find_one(post_id)
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Post ID '{post_id}' not found"
        )
    
    update_data = post_update.model_dump(exclude={'id', 'author'}, exclude_unset=True)
    for field, value in update_data.items():
        setattr(post, field, value)
    
    await post.save()
    return post


@app.delete("/posts/{post_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_post(post_id: str):
    """Delete post."""
    post = await Post.find_one(post_id)
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Post ID '{post_id}' not found"
        )
    
    await post.delete()
    return None
```

### 6.3 Relational Query Routes

```python
# app/main.py (append)

@app.get("/users/{user_id}/posts", response_model=List[Post])
async def get_user_posts(
    user_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100)
):
    """Get all posts by a specific user."""
    user = await User.find_one(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User ID '{user_id}' not found"
        )
    
    # Use relational query
    posts = await user.posts_query().limit(limit).offset(skip).all()
    return posts


@app.get("/posts/{post_id}/author", response_model=User)
async def get_post_author(post_id: str):
    """Get the author information of a post."""
    post = await Post.find_one(post_id)
    if not post:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Post ID '{post_id}' not found"
        )
    
    author = await post.author_query().one()
    if not author:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Author information not found"
        )
    
    return author
```

> **🔍 Prompt Example**
> 
> **Scenario**: You want to automatically set the publication time when a post is published.
> 
> You can add a custom method to the Post model:
> 
> ```python
> class Post(UUIDMixin, TimestampMixin, AsyncActiveRecord):
>     # ... field definitions ...
>     
>     async def publish(self) -> None:
>         """Publish the post."""
>         from datetime import datetime
>         self.is_published = True
>         self.published_at = datetime.now()
>         await self.save()
> 
> # Then use in API routes
> @app.post("/posts/{post_id}/publish")
> async def publish_post(post_id: str):
>     post = await Post.find_one(post_id)
>     if not post:
>         raise HTTPException(status_code=404, detail="Post not found")
>     await post.publish()
>     return {"message": "Post published", "published_at": post.published_at}
> ```

## Common Issues and Solutions

### Issue 1: "OFFSET clause requires LIMIT clause"

**Problem**: SQLite requires LIMIT when using OFFSET.

**Solution**: Always use LIMIT before OFFSET:
```python
# Wrong
users = await query.offset(skip).limit(limit).all()

# Correct
users = await query.limit(limit).offset(skip).all()
```

### Issue 2: Relationship query methods

**Problem**: Using `model.relation().query()` causes AttributeError.

**Solution**: Use `model.relation_query()`:
```python
# Wrong
posts = await user.posts().query().limit(limit).offset(skip).all()

# Correct
posts = await user.posts_query().limit(limit).offset(skip).all()
```

### Issue 3: Query method names

**Problem**: Using `query().first()` causes AttributeError.

**Solution**: Use `query().one()`:
```python
# Wrong
existing = await User.query().where(User.c.username == user.username).first()

# Correct
existing = await User.query().where(User.c.username == user.username).one()
```

### Issue 4: Sorting

**Information**: The API now supports flexible sorting options through query parameters.

**Usage Examples**:
```python
# For ascending order (default):
users = await query.order_by(User.c.created_at).limit(limit).offset(skip).all()

# For descending order:
users = await query.order_by((User.c.created_at, "DESC")).limit(limit).offset(skip).all()

# For sorting by different fields:
users = await query.order_by(User.c.username).limit(limit).offset(skip).all()

# For mixed ordering:
users = await query.order_by((User.c.created_at, "DESC"), User.c.username).limit(limit).offset(skip).all()
```

The implemented API endpoints accept `sort_by` and `sort_order` query parameters:
- `sort_by`: Field to sort by (e.g., "created_at", "username" for users)
- `sort_order`: Sort direction ("asc" or "desc")

## 7. Running and Testing

### 7.1 Starting the Application

```bash
# Start with uvicorn (recommended for development)
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Or run directly with python
python -m uvicorn app.main:app --reload
```

### 7.2 Accessing the Documentation

After starting, visit the auto-generated API documentation:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### 7.3 Testing the API

Test using curl or httpie:

```bash
# 1. Create a user
curl -X POST "http://localhost:8000/users/" \
  -H "Content-Type: application/json" \
  -d '{
    "username": "john_doe",
    "email": "john@example.com",
    "bio": "Python developer"
  }'

# 2. Get user list
curl "http://localhost:8000/users/"

# 3. Create a post (replace with actual user ID returned)
curl -X POST "http://localhost:8000/posts/" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "My First Post",
    "content": "This is the post content...",
    "user_id": "replace_with_actual_user_id"
  }'

# 4. Get all posts by a user
curl "http://localhost:8000/users/user_id/posts"
```

## 8. Best Practices

### 8.1 Separating Request/Response Models

While `ActiveRecord` models can be used directly as request bodies, in complex scenarios, it's recommended to create dedicated Pydantic models:

```python
# app/schemas.py
from pydantic import BaseModel
from typing import Optional


class UserCreate(BaseModel):
    """Request model for creating a user."""
    username: str
    email: str
    bio: Optional[str] = None


class UserResponse(BaseModel):
    """User response model."""
    id: str
    username: str
    email: str
    bio: Optional[str]
    is_active: bool
    
    class Config:
        from_attributes = True


# Use in routes
@app.post("/users/", response_model=UserResponse)
async def create_user(user_data: UserCreate):
    user = User(**user_data.model_dump())
    await user.save()
    return user
```

### 8.2 Error Handling

Create global exception handlers:

```python
# app/main.py (append)
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    """Handle request validation errors."""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": "Request data validation failed",
            "errors": exc.errors()
        }
    )
```

### 8.3 Dependency Injection Best Practices

For scenarios requiring transaction management:

```python
from fastapi import Depends
from contextlib import asynccontextmanager

@asynccontextmanager
async def get_transaction():
    """Provide transaction context."""
    backend = await Database.get_backend()
    try:
        await backend.transaction_manager.begin()
        yield backend
        await backend.transaction_manager.commit()
    except Exception:
        await backend.transaction_manager.rollback()
        raise

@app.post("/users/batch")
async def create_users_batch(users: List[User], tx=Depends(get_transaction)):
    """Batch create users (with transaction guarantee)."""
    for user in users:
        await user.save()
    return {"created": len(users)}
```

### 8.4 Production Environment Configuration

```python
import os

# Use more robust configuration for production
app = FastAPI(
    title="Blog System API",
    description="...",
    version="1.0.0",
    docs_url="/docs" if os.getenv("DEBUG") else None,  # Disable docs in production
    redoc_url="/redoc" if os.getenv("DEBUG") else None,
    lifespan=lifespan
)
```

---

## Next Steps

You've completed the FastAPI integration with rhosocial-activerecord! Next, you can explore:

- **[GraphQL Integration](graphql.md)**: Build more flexible API interfaces
- **[Advanced Query Techniques](../query_advanced/)**: Use window functions, CTEs, and other advanced features
- **[Performance Optimization](../performance/)**: Add caching and optimization strategies to your API

> **💡 Prompt Example**
> 
> **Scenario**: You want to add authentication and permission control to your API.
> 
> You can use FastAPI's dependency injection combined with `rhosocial-activerecord` query capabilities:
> 
> ```python
> from fastapi.security import HTTPBearer
> 
> security = HTTPBearer()
> 
> async def get_current_user(token: str = Depends(security)) -> User:
>     """Get current user based on Token."""
>     # Verify token and get user ID
>     user_id = verify_token(token.credentials)
>     user = await User.find_one(user_id)
>     if not user:
>         raise HTTPException(status_code=401, detail="Invalid user")
>     return user
> 
> @app.get("/users/me", response_model=User)
> async def get_me(current_user: User = Depends(get_current_user)):
>     """Get current logged-in user information."""
>     return current_user
> ```
