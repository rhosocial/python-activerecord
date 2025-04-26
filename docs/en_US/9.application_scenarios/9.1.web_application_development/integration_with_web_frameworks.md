# Integration with Various Web Frameworks

rhosocial ActiveRecord is designed to integrate seamlessly with popular web frameworks. This document explores how to effectively combine ActiveRecord with various web frameworks, providing practical examples and best practices.

## Contents

- [Overview](#overview)
- [Integration with Flask](#integration-with-flask)
- [Integration with FastAPI](#integration-with-fastapi)
- [Integration with Django](#integration-with-django)
- [Integration with Pyramid](#integration-with-pyramid)
- [Integration with Tornado](#integration-with-tornado)
- [Integration with Starlette](#integration-with-starlette)
- [Best Practices](#best-practices)
- [Common Patterns](#common-patterns)

## Overview

While rhosocial ActiveRecord can be used as a standalone ORM, it truly shines when integrated with web frameworks. The ActiveRecord pattern complements the MVC (Model-View-Controller) or similar architectural patterns used by most web frameworks.

Key benefits of integrating ActiveRecord with web frameworks include:

1. **Consistent Data Access**: Uniform approach to database operations across your application
2. **Clean Separation of Concerns**: Models handle data persistence while controllers/views handle request processing
3. **Simplified Testing**: Models can be tested independently from the web framework
4. **Flexible Migration Path**: Ability to change web frameworks while maintaining the same data layer

## Integration with Flask

Flask is a lightweight WSGI web application framework that pairs well with ActiveRecord's minimalist approach.

### Basic Setup

```python
from flask import Flask
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.backend import SQLiteBackend

app = Flask(__name__)

# Configure ActiveRecord
ActiveRecord.configure({
    'backend': SQLiteBackend,
    'database': 'app.db',
    'echo': app.debug  # Enable SQL logging in debug mode
})

# Define models
class User(ActiveRecord):
    __tablename__ = 'users'
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

# Flask routes
@app.route('/users')
def list_users():
    users = User.query().all()
    return {'users': [user.to_dict() for user in users]}

@app.route('/users/<int:user_id>')
def get_user(user_id):
    user = User.find(user_id)
    if not user:
        return {'error': 'User not found'}, 404
    return user.to_dict()

if __name__ == '__main__':
    app.run(debug=True)
```

### Flask Application Factory Pattern

```python
# app/__init__.py
from flask import Flask
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.backend import SQLiteBackend

def create_app(config=None):
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object('app.config.default')
    if config:
        app.config.from_object(config)
    
    # Initialize ActiveRecord
    ActiveRecord.configure({
        'backend': SQLiteBackend,
        'database': app.config['DATABASE_URI'],
        'echo': app.config['SQL_ECHO']
    })
    
    # Register blueprints
    from app.views.users import users_bp
    app.register_blueprint(users_bp)
    
    return app

# app/models/user.py
from rhosocial.activerecord import ActiveRecord

class User(ActiveRecord):
    __tablename__ = 'users'
    # Model definition

# app/views/users.py
from flask import Blueprint, jsonify
from app.models.user import User

users_bp = Blueprint('users', __name__, url_prefix='/users')

@users_bp.route('/')
def list_users():
    users = User.query().all()
    return jsonify([user.to_dict() for user in users])
```

### Flask-RESTful Integration

```python
from flask import Flask
from flask_restful import Api, Resource
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.backend import SQLiteBackend

app = Flask(__name__)
api = Api(app)

# Configure ActiveRecord
ActiveRecord.configure({
    'backend': SQLiteBackend,
    'database': 'app.db'
})

class User(ActiveRecord):
    __tablename__ = 'users'
    # Model definition

class UserResource(Resource):
    def get(self, user_id=None):
        if user_id:
            user = User.find(user_id)
            if not user:
                return {'error': 'User not found'}, 404
            return user.to_dict()
        else:
            users = User.query().all()
            return {'users': [user.to_dict() for user in users]}
    
    def post(self):
        from flask import request
        data = request.get_json()
        user = User(**data)
        if user.save():
            return user.to_dict(), 201
        return {'error': 'Failed to create user'}, 400

api.add_resource(UserResource, '/users', '/users/<int:user_id>')

if __name__ == '__main__':
    app.run(debug=True)
```

## Integration with FastAPI

FastAPI is a modern, high-performance web framework that works well with ActiveRecord, especially when using async features.

### Basic Setup

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.backend import PostgreSQLBackend

app = FastAPI()

# Configure ActiveRecord
ActiveRecord.configure({
    'backend': PostgreSQLBackend,
    'host': 'localhost',
    'database': 'fastapi_db',
    'user': 'postgres',
    'password': 'password'
})

# Define models
class User(ActiveRecord):
    __tablename__ = 'users'
    # Model definition

# Pydantic schemas
class UserBase(BaseModel):
    name: str
    email: str

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    
    class Config:
        orm_mode = True

# FastAPI routes
@app.get("/users", response_model=List[UserResponse])
async def read_users():
    users = await User.query().all_async()
    return users

@app.get("/users/{user_id}", response_model=UserResponse)
async def read_user(user_id: int):
    user = await User.find_async(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.post("/users", response_model=UserResponse, status_code=201)
async def create_user(user: UserCreate):
    db_user = User(
        name=user.name,
        email=user.email
    )
    db_user.set_password(user.password)
    
    if not await db_user.save_async():
        raise HTTPException(status_code=400, detail="Failed to create user")
    return db_user
```

### Dependency Injection

```python
from fastapi import Depends, FastAPI, HTTPException
from rhosocial.activerecord import ActiveRecord

app = FastAPI()

# Configure ActiveRecord
# ...

class User(ActiveRecord):
    __tablename__ = 'users'
    # Model definition

async def get_user(user_id: int):
    user = await User.find_async(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.get("/users/{user_id}/profile")
async def read_user_profile(user: User = Depends(get_user)):
    profile = await user.get_profile_async()
    return profile.to_dict()
```

## Integration with Django

While Django has its own ORM, you might want to use ActiveRecord for specific functionality or when migrating gradually.

### Basic Setup

```python
# settings.py
ACTIVERECORD_CONFIG = {
    'backend': 'rhosocial.activerecord.backend.PostgreSQLBackend',
    'host': 'localhost',
    'database': 'django_db',
    'user': 'django',
    'password': 'password'
}

# apps/users/models.py
from rhosocial.activerecord import ActiveRecord
from django.conf import settings

# Configure ActiveRecord
ActiveRecord.configure(settings.ACTIVERECORD_CONFIG)

class User(ActiveRecord):
    __tablename__ = 'ar_users'  # Different table to avoid conflicts
    # Model definition

# apps/users/views.py
from django.http import JsonResponse
from django.views import View
from .models import User

class UserListView(View):
    def get(self, request):
        users = User.query().all()
        return JsonResponse({'users': [user.to_dict() for user in users]})

class UserDetailView(View):
    def get(self, request, user_id):
        user = User.find(user_id)
        if not user:
            return JsonResponse({'error': 'User not found'}, status=404)
        return JsonResponse(user.to_dict())
```

### Django REST Framework Integration

```python
from rest_framework import viewsets, serializers
from rest_framework.response import Response
from .models import User

class UserSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField()
    email = serializers.EmailField()
    
    def create(self, validated_data):
        user = User(**validated_data)
        user.save()
        return user
    
    def update(self, instance, validated_data):
        for key, value in validated_data.items():
            setattr(instance, key, value)
        instance.save()
        return instance

class UserViewSet(viewsets.ViewSet):
    def list(self, request):
        users = User.query().all()
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data)
    
    def retrieve(self, request, pk=None):
        user = User.find(pk)
        if not user:
            return Response({'error': 'User not found'}, status=404)
        serializer = UserSerializer(user)
        return Response(serializer.data)
    
    def create(self, request):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)
```

## Integration with Pyramid

Pyramid is a flexible web framework that can be easily integrated with ActiveRecord.

```python
from pyramid.config import Configurator
from pyramid.response import Response
from pyramid.view import view_config
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.backend import SQLiteBackend

# Configure ActiveRecord
ActiveRecord.configure({
    'backend': SQLiteBackend,
    'database': 'pyramid_app.db'
})

class User(ActiveRecord):
    __tablename__ = 'users'
    # Model definition

@view_config(route_name='users', renderer='json')
def list_users(request):
    users = User.query().all()
    return {'users': [user.to_dict() for user in users]}

@view_config(route_name='user', renderer='json')
def get_user(request):
    user_id = request.matchdict['id']
    user = User.find(user_id)
    if not user:
        return Response(json_body={'error': 'User not found'}, status=404)
    return user.to_dict()

def main(global_config, **settings):
    config = Configurator(settings=settings)
    config.add_route('users', '/users')
    config.add_route('user', '/users/{id}')
    config.scan()
    return config.make_wsgi_app()
```

## Integration with Tornado

Tornado is an asynchronous web framework that can be integrated with ActiveRecord's async features.

```python
import tornado.ioloop
import tornado.web
import json
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.backend import MySQLBackend

# Configure ActiveRecord
ActiveRecord.configure({
    'backend': MySQLBackend,
    'host': 'localhost',
    'database': 'tornado_db',
    'user': 'tornado',
    'password': 'password'
})

class User(ActiveRecord):
    __tablename__ = 'users'
    # Model definition

class UserListHandler(tornado.web.RequestHandler):
    async def get(self):
        users = await User.query().all_async()
        self.write(json.dumps({'users': [user.to_dict() for user in users]}))

class UserHandler(tornado.web.RequestHandler):
    async def get(self, user_id):
        user = await User.find_async(int(user_id))
        if not user:
            self.set_status(404)
            self.write(json.dumps({'error': 'User not found'}))
            return
        self.write(json.dumps(user.to_dict()))

def make_app():
    return tornado.web.Application([
        (r"/users", UserListHandler),
        (r"/users/([0-9]+)", UserHandler),
    ])

if __name__ == "__main__":
    app = make_app()
    app.listen(8888)
    tornado.ioloop.IOLoop.current().start()
```

## Integration with Starlette

Starlette is a lightweight ASGI framework that works well with ActiveRecord's async capabilities.

```python
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
import uvicorn
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.backend import PostgreSQLBackend

# Configure ActiveRecord
ActiveRecord.configure({
    'backend': PostgreSQLBackend,
    'host': 'localhost',
    'database': 'starlette_db',
    'user': 'postgres',
    'password': 'password'
})

class User(ActiveRecord):
    __tablename__ = 'users'
    # Model definition

async def list_users(request):
    users = await User.query().all_async()
    return JSONResponse({'users': [user.to_dict() for user in users]})

async def get_user(request):
    user_id = request.path_params['user_id']
    user = await User.find_async(user_id)
    if not user:
        return JSONResponse({'error': 'User not found'}, status_code=404)
    return JSONResponse(user.to_dict())

routes = [
    Route('/users', endpoint=list_users),
    Route('/users/{user_id:int}', endpoint=get_user),
]

app = Starlette(debug=True, routes=routes)

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000)
```

## Best Practices

### 1. Separation of Concerns

Maintain a clear separation between your web framework code and ActiveRecord models:

```python
# models/user.py - ActiveRecord models
from rhosocial.activerecord import ActiveRecord

class User(ActiveRecord):
    __tablename__ = 'users'
    
    def to_dict(self):
        # Model-specific serialization
        return {...}

# api/user_api.py - Framework-specific code
from models.user import User

# Flask example
@app.route('/users')
def list_users():
    # Framework-specific request handling
    users = User.query().all()
    return jsonify([user.to_dict() for user in users])
```

### 2. Configuration Management

Manage ActiveRecord configuration according to your framework's conventions:

```python
# Flask example
app = Flask(__name__)
app.config.from_object('config.DevelopmentConfig')

ActiveRecord.configure({
    'backend': app.config['DB_BACKEND'],
    'host': app.config['DB_HOST'],
    'database': app.config['DB_NAME'],
    'user': app.config['DB_USER'],
    'password': app.config['DB_PASSWORD'],
    'echo': app.config['DB_ECHO']
})
```

### 3. Connection Lifecycle Management

Ensure proper connection handling based on your framework's request lifecycle:

```python
# Flask example with connection per request
@app.before_request
def before_request():
    ActiveRecord.connect()

@app.teardown_request
def teardown_request(exception=None):
    ActiveRecord.disconnect()
```

### 4. Error Handling

Integrate ActiveRecord exceptions with your framework's error handling:

```python
# Flask example
from rhosocial.activerecord.exceptions import RecordNotFoundError, ValidationError

@app.errorhandler(RecordNotFoundError)
def handle_not_found(error):
    return jsonify({'error': str(error)}), 404

@app.errorhandler(ValidationError)
def handle_validation_error(error):
    return jsonify({'error': str(error), 'fields': error.fields}), 400
```

## Common Patterns

### Repository Pattern

Use repositories to abstract database operations from your web controllers:

```python
# repositories/user_repository.py
from models.user import User

class UserRepository:
    @staticmethod
    def find_by_id(user_id):
        return User.find(user_id)
    
    @staticmethod
    def find_by_email(email):
        return User.query().where('email = ?', (email,)).one()
    
    @staticmethod
    def create(data):
        user = User(**data)
        user.save()
        return user
    
    @staticmethod
    def update(user_id, data):
        user = User.find(user_id)
        if not user:
            return None
        user.update(data)
        return user

# controllers/user_controller.py
from repositories.user_repository import UserRepository

# Flask example
@app.route('/users/<int:user_id>')
def get_user(user_id):
    user = UserRepository.find_by_id(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404
    return jsonify(user.to_dict())
```

### Service Layer

Implement a service layer for complex business logic:

```python
# services/user_service.py
from repositories.user_repository import UserRepository
from services.email_service import EmailService

class UserService:
    @staticmethod
    def register_user(data):
        # Validate data
        if not data.get('email') or not data.get('password'):
            raise ValueError("Email and password are required")
        
        # Check if user exists
        existing_user = UserRepository.find_by_email(data['email'])
        if existing_user:
            raise ValueError("Email already registered")
        
        # Create user
        user = UserRepository.create(data)
        
        # Send welcome email
        EmailService.send_welcome_email(user.email)
        
        return user

# controllers/user_controller.py
from services.user_service import UserService

# Flask example
@app.route('/users', methods=['POST'])
def create_user():
    data = request.get_json()
    try:
        user = UserService.register_user(data)
        return jsonify(user.to_dict()), 201
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
```

### Middleware for Authentication

Implement authentication middleware using ActiveRecord models:

```python
# middleware/auth.py
from models.user import User
from flask import request, jsonify
from functools import wraps

def token_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        token = request.headers.get('Authorization')
        if not token:
            return jsonify({'error': 'Token is missing'}), 401
        
        try:
            # Remove 'Bearer ' prefix if present
            if token.startswith('Bearer '):
                token = token[7:]
            
            # Verify token and get user
            user = User.verify_token(token)
            if not user:
                return jsonify({'error': 'Invalid token'}), 401
            
            # Add user to request context
            request.user = user
        except Exception as e:
            return jsonify({'error': str(e)}), 401
        
        return f(*args, **kwargs)
    return decorated

# controllers/user_controller.py
from middleware.auth import token_required

@app.route('/profile')
@token_required
def get_profile():
    return jsonify(request.user.to_dict())
```

By following these integration patterns and best practices, you can effectively combine rhosocial ActiveRecord with your preferred web framework, creating maintainable and efficient web applications.