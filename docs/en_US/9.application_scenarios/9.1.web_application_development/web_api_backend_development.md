# Web API Backend Development

Building Web API backends is one of the most common use cases for rhosocial ActiveRecord. This document explores how to effectively implement ActiveRecord in API-driven applications, with practical examples and best practices.

## Contents

- [Overview](#overview)
- [Basic API Backend Architecture](#basic-api-backend-architecture)
- [Implementing REST APIs with ActiveRecord](#implementing-rest-apis-with-activerecord)
- [GraphQL Implementation](#graphql-implementation)
- [Authentication and Authorization](#authentication-and-authorization)
- [API Versioning Strategies](#api-versioning-strategies)
- [Performance Considerations](#performance-considerations)
- [Error Handling and Response Formatting](#error-handling-and-response-formatting)
- [Examples](#examples)

## Overview

Modern web applications often separate frontend and backend concerns, with the backend exposing APIs that frontend applications consume. rhosocial ActiveRecord provides an elegant solution for the data access layer of API backends, offering:

- Intuitive model definitions that map directly to API resources
- Flexible query building for complex data retrieval
- Transaction support for maintaining data integrity
- Relationship management for handling connected resources

## Basic API Backend Architecture

A typical API backend using rhosocial ActiveRecord consists of these components:

```
┌─────────────────────────────────────┐
│ API Framework (Flask/FastAPI/Django) │
├─────────────────────────────────────┤
│ Resource/Controller Layer            │
├─────────────────────────────────────┤
│ Service Layer                        │
├─────────────────────────────────────┤
│ ActiveRecord Models                  │
├─────────────────────────────────────┤
│ Database                             │
└─────────────────────────────────────┘
```

### Example Project Structure

```
api_project/
├── app/
│   ├── __init__.py
│   ├── config.py                # Configuration settings
│   ├── models/                  # ActiveRecord models
│   │   ├── __init__.py
│   │   ├── user.py
│   │   └── product.py
│   ├── resources/               # API endpoints/resources
│   │   ├── __init__.py
│   │   ├── user_resource.py
│   │   └── product_resource.py
│   ├── services/                # Business logic
│   │   ├── __init__.py
│   │   ├── user_service.py
│   │   └── product_service.py
│   └── utils/                   # Utility functions
│       ├── __init__.py
│       ├── auth.py
│       └── validators.py
├── migrations/                  # Database migrations
├── tests/                       # Test suite
└── main.py                      # Application entry point
```

## Implementing REST APIs with ActiveRecord

REST (Representational State Transfer) is a common architectural style for web APIs. Here's how ActiveRecord models map to REST resources:

| HTTP Method | URL Pattern       | ActiveRecord Operation      | Description           |
|-------------|-------------------|-----------------------------|----------------------|
| GET         | /resources        | Model.query().all()         | List resources       |
| GET         | /resources/:id    | Model.find(id)              | Get single resource  |
| POST        | /resources        | Model().save()              | Create resource      |
| PUT/PATCH   | /resources/:id    | model.update()/model.save() | Update resource      |
| DELETE      | /resources/:id    | model.delete()              | Delete resource      |

### Example with Flask

```python
from flask import Flask, request, jsonify
from app.models.user import User

app = Flask(__name__)

@app.route('/users', methods=['GET'])
def get_users():
    users = User.query().all()
    return jsonify([user.to_dict() for user in users])

@app.route('/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    user = User.find(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify(user.to_dict())

@app.route('/users', methods=['POST'])
def create_user():
    data = request.get_json()
    user = User(**data)
    if user.save():
        return jsonify(user.to_dict()), 201
    return jsonify({"error": "Failed to create user"}), 400

@app.route('/users/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    user = User.find(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    data = request.get_json()
    if user.update(data):
        return jsonify(user.to_dict())
    return jsonify({"error": "Failed to update user"}), 400

@app.route('/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    user = User.find(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    if user.delete():
        return jsonify({"message": "User deleted"})
    return jsonify({"error": "Failed to delete user"}), 400
```

### Example with FastAPI

```python
from fastapi import FastAPI, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from app.models.user import User

app = FastAPI()

class UserSchema(BaseModel):
    name: str
    email: str
    age: Optional[int] = None

class UserResponse(UserSchema):
    id: int
    
    class Config:
        orm_mode = True

@app.get("/users", response_model=List[UserResponse])
def get_users():
    return User.query().all()

@app.get("/users/{user_id}", response_model=UserResponse)
def get_user(user_id: int):
    user = User.find(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.post("/users", response_model=UserResponse, status_code=201)
def create_user(user_data: UserSchema):
    user = User(**user_data.dict())
    if not user.save():
        raise HTTPException(status_code=400, detail="Failed to create user")
    return user

@app.put("/users/{user_id}", response_model=UserResponse)
def update_user(user_id: int, user_data: UserSchema):
    user = User.find(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not user.update(user_data.dict()):
        raise HTTPException(status_code=400, detail="Failed to update user")
    return user

@app.delete("/users/{user_id}")
def delete_user(user_id: int):
    user = User.find(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not user.delete():
        raise HTTPException(status_code=400, detail="Failed to delete user")
    return {"message": "User deleted"}
```

## GraphQL Implementation

GraphQL provides a more flexible alternative to REST for API development. ActiveRecord works well with GraphQL libraries like Graphene:

```python
import graphene
from graphene import relay
from graphene_sqlalchemy import SQLAlchemyObjectType, SQLAlchemyConnectionField
from app.models.user import User as UserModel

class User(SQLAlchemyObjectType):
    class Meta:
        model = UserModel
        interfaces = (relay.Node, )

class Query(graphene.ObjectType):
    node = relay.Node.Field()
    users = SQLAlchemyConnectionField(User.connection)
    user = graphene.Field(User, id=graphene.Int())
    
    def resolve_user(self, info, id):
        return UserModel.find(id)

class CreateUser(graphene.Mutation):
    class Arguments:
        name = graphene.String(required=True)
        email = graphene.String(required=True)
    
    user = graphene.Field(lambda: User)
    
    def mutate(self, info, name, email):
        user = UserModel(name=name, email=email)
        user.save()
        return CreateUser(user=user)

class Mutation(graphene.ObjectType):
    create_user = CreateUser.Field()

schema = graphene.Schema(query=Query, mutation=Mutation)
```

## Authentication and Authorization

API backends typically require authentication and authorization. ActiveRecord models can be extended to support these requirements:

```python
from werkzeug.security import generate_password_hash, check_password_hash
from app.models.base import ActiveRecord

class User(ActiveRecord):
    __tablename__ = 'users'
    
    # Define fields
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    @classmethod
    def authenticate(cls, username, password):
        user = cls.query().where('username = ?', (username,)).one()
        if user and user.check_password(password):
            return user
        return None
    
    def generate_token(self):
        # Token generation logic
        pass
    
    @classmethod
    def verify_token(cls, token):
        # Token verification logic
        pass
```

## API Versioning Strategies

As APIs evolve, versioning becomes important. Common strategies include:

1. **URL Path Versioning**: `/api/v1/users`, `/api/v2/users`
2. **Query Parameter Versioning**: `/api/users?version=1`
3. **Header Versioning**: Using custom headers like `API-Version: 1`
4. **Content Type Versioning**: `Accept: application/vnd.company.v1+json`

ActiveRecord models can support versioning through inheritance or composition:

```python
# Base model for all versions
class UserBase(ActiveRecord):
    __abstract__ = True
    __tablename__ = 'users'
    
    # Common fields and methods

# V1 API model
class UserV1(UserBase):
    # V1-specific methods
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            # V1 format
        }

# V2 API model with extended functionality
class UserV2(UserBase):
    # V2-specific methods
    def to_dict(self):
        return {
            'id': self.id,
            'full_name': self.name,
            'profile': self.get_profile_data(),
            # V2 format with more data
        }
```

## Performance Considerations

API backends often need to handle high request volumes. Consider these ActiveRecord optimization strategies:

1. **Query Optimization**:
   - Use eager loading to avoid N+1 query problems
   - Apply appropriate indexes on database tables
   - Utilize query caching for frequently accessed data

2. **Response Optimization**:
   - Implement pagination for large result sets
   - Use projection to select only needed fields
   - Consider serialization performance

3. **Concurrency Handling**:
   - Use appropriate transaction isolation levels
   - Implement optimistic locking for concurrent updates
   - Consider connection pooling for high-traffic APIs

## Error Handling and Response Formatting

Consistent error handling is crucial for API usability:

```python
from flask import jsonify
from app.models.exceptions import RecordNotFoundError, ValidationError

@app.errorhandler(RecordNotFoundError)
def handle_not_found(error):
    return jsonify({
        "error": "not_found",
        "message": str(error)
    }), 404

@app.errorhandler(ValidationError)
def handle_validation_error(error):
    return jsonify({
        "error": "validation_error",
        "message": str(error),
        "fields": error.fields
    }), 400
```

## Examples

### Complete REST API Example

Here's a more complete example of a REST API using Flask and ActiveRecord:

```python
from flask import Flask, request, jsonify, Blueprint
from app.models.user import User
from app.models.post import Post
from app.utils.auth import token_required

api = Blueprint('api', __name__)

# User endpoints
@api.route('/users', methods=['GET'])
def get_users():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 20, type=int)
    
    query = User.query()
    
    # Apply filters if provided
    if 'name' in request.args:
        query = query.where('name LIKE ?', (f'%{request.args["name"]}%',))
    
    # Apply sorting
    sort_by = request.args.get('sort_by', 'id')
    sort_dir = request.args.get('sort_dir', 'asc')
    if sort_dir.lower() == 'desc':
        query = query.order_by(f'{sort_by} DESC')
    else:
        query = query.order_by(sort_by)
    
    # Apply pagination
    total = query.count()
    users = query.limit(per_page).offset((page - 1) * per_page).all()
    
    return jsonify({
        'data': [user.to_dict() for user in users],
        'meta': {
            'page': page,
            'per_page': per_page,
            'total': total,
            'pages': (total + per_page - 1) // per_page
        }
    })

@api.route('/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    user = User.find(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    # Include related posts if requested
    include_posts = request.args.get('include_posts', '').lower() == 'true'
    user_data = user.to_dict()
    
    if include_posts:
        posts = Post.query().where('user_id = ?', (user_id,)).all()
        user_data['posts'] = [post.to_dict() for post in posts]
    
    return jsonify(user_data)

@api.route('/users', methods=['POST'])
@token_required
def create_user():
    data = request.get_json()
    
    # Validate required fields
    required_fields = ['name', 'email', 'password']
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing required field: {field}"}), 400
    
    # Check if email already exists
    existing_user = User.query().where('email = ?', (data['email'],)).one()
    if existing_user:
        return jsonify({"error": "Email already in use"}), 409
    
    # Create user with transaction
    try:
        with User.transaction():
            user = User(
                name=data['name'],
                email=data['email']
            )
            user.set_password(data['password'])
            user.save()
            
            # Create initial profile if data provided
            if 'profile' in data:
                profile_data = data['profile']
                profile_data['user_id'] = user.id
                profile = Profile(**profile_data)
                profile.save()
                
        return jsonify(user.to_dict()), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 400

# Post endpoints
@api.route('/users/<int:user_id>/posts', methods=['GET'])
def get_user_posts(user_id):
    user = User.find(user_id)
    if not user:
        return jsonify({"error": "User not found"}), 404
    
    posts = Post.query().where('user_id = ?', (user_id,)).all()
    return jsonify([post.to_dict() for post in posts])

@api.route('/posts/<int:post_id>', methods=['GET'])
def get_post(post_id):
    post = Post.find(post_id)
    if not post:
        return jsonify({"error": "Post not found"}), 404
    
    # Include user data if requested
    include_user = request.args.get('include_user', '').lower() == 'true'
    post_data = post.to_dict()
    
    if include_user:
        user = User.find(post.user_id)
        post_data['user'] = user.to_dict() if user else None
    
    return jsonify(post_data)

app = Flask(__name__)
app.register_blueprint(api, url_prefix='/api/v1')

if __name__ == '__main__':
    app.run(debug=True)
```

### Async API with FastAPI

Leveraging ActiveRecord's async support with FastAPI:

```python
from fastapi import FastAPI, HTTPException, Depends, Query
from typing import List, Optional
from app.models.user import User
from app.schemas.user import UserCreate, UserResponse, UserUpdate
from app.utils.auth import get_current_user

app = FastAPI()

@app.get("/users", response_model=List[UserResponse])
async def get_users(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    name: Optional[str] = None
):
    query = User.query()
    
    if name:
        query = query.where('name LIKE ?', (f'%{name}%',))
    
    total = await query.count_async()
    users = await query.limit(limit).offset((page - 1) * limit).all_async()
    
    return users

@app.get("/users/{user_id}", response_model=UserResponse)
async def get_user(user_id: int):
    user = await User.find_async(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.post("/users", response_model=UserResponse, status_code=201)
async def create_user(user_data: UserCreate):
    # Check if email already exists
    existing_user = await User.query().where('email = ?', (user_data.email,)).one_async()
    if existing_user:
        raise HTTPException(status_code=409, detail="Email already registered")
    
    user = User(
        name=user_data.name,
        email=user_data.email
    )
    user.set_password(user_data.password)
    
    if not await user.save_async():
        raise HTTPException(status_code=400, detail="Failed to create user")
    
    return user

@app.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    current_user: User = Depends(get_current_user)
):
    # Check permissions
    if current_user.id != user_id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    user = await User.find_async(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    update_data = user_data.dict(exclude_unset=True)
    
    if not await user.update_async(update_data):
        raise HTTPException(status_code=400, detail="Failed to update user")
    
    return user
```

These examples demonstrate how rhosocial ActiveRecord can be effectively used in API backend development, providing a clean, intuitive interface for database operations while integrating seamlessly with popular web frameworks.