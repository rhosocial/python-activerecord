# 与各种Web框架集成

rhosocial ActiveRecord设计为与流行的Web框架无缝集成。本文档探讨如何有效地将ActiveRecord与各种Web框架结合使用，提供实用示例和最佳实践。

## 目录

- [概述](#概述)
- [与Flask集成](#与flask集成)
- [与FastAPI集成](#与fastapi集成)
- [与Django集成](#与django集成)
- [与Pyramid集成](#与pyramid集成)
- [与Tornado集成](#与tornado集成)
- [与Starlette集成](#与starlette集成)
- [最佳实践](#最佳实践)
- [常见模式](#常见模式)

## 概述

虽然rhosocial ActiveRecord可以作为独立的ORM使用，但它在与Web框架集成时真正发挥其优势。ActiveRecord模式补充了大多数Web框架使用的MVC（模型-视图-控制器）或类似的架构模式。

将ActiveRecord与Web框架集成的主要优势包括：

1. **一致的数据访问**：在整个应用程序中统一的数据库操作方法
2. **关注点清晰分离**：模型处理数据持久化，而控制器/视图处理请求处理
3. **简化测试**：模型可以独立于Web框架进行测试
4. **灵活的迁移路径**：能够更改Web框架，同时保持相同的数据层

## 与Flask集成

Flask是一个轻量级的WSGI Web应用框架，与ActiveRecord的极简方法配合得很好。

### 基本设置

```python
from flask import Flask
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.backend import SQLiteBackend

app = Flask(__name__)

# 配置ActiveRecord
ActiveRecord.configure({
    'backend': SQLiteBackend,
    'database': 'app.db',
    'echo': app.debug  # 在调试模式下启用SQL日志记录
})

# 定义模型
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

# Flask路由
@app.route('/users')
def list_users():
    users = User.query().all()
    return {'users': [user.to_dict() for user in users]}

@app.route('/users/<int:user_id>')
def get_user(user_id):
    user = User.find(user_id)
    if not user:
        return {'error': '用户未找到'}, 404
    return user.to_dict()

if __name__ == '__main__':
    app.run(debug=True)
```

### Flask应用工厂模式

```python
# app/__init__.py
from flask import Flask
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.backend import SQLiteBackend

def create_app(config=None):
    app = Flask(__name__)
    
    # 加载配置
    app.config.from_object('app.config.default')
    if config:
        app.config.from_object(config)
    
    # 初始化ActiveRecord
    ActiveRecord.configure({
        'backend': SQLiteBackend,
        'database': app.config['DATABASE_URI'],
        'echo': app.config['SQL_ECHO']
    })
    
    # 注册蓝图
    from app.views.users import users_bp
    app.register_blueprint(users_bp)
    
    return app

# app/models/user.py
from rhosocial.activerecord import ActiveRecord

class User(ActiveRecord):
    __tablename__ = 'users'
    # 模型定义

# app/views/users.py
from flask import Blueprint, jsonify
from app.models.user import User

users_bp = Blueprint('users', __name__, url_prefix='/users')

@users_bp.route('/')
def list_users():
    users = User.query().all()
    return jsonify([user.to_dict() for user in users])
```

### Flask-RESTful集成

```python
from flask import Flask
from flask_restful import Api, Resource
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.backend import SQLiteBackend

app = Flask(__name__)
api = Api(app)

# 配置ActiveRecord
ActiveRecord.configure({
    'backend': SQLiteBackend,
    'database': 'app.db'
})

class User(ActiveRecord):
    __tablename__ = 'users'
    # 模型定义

class UserResource(Resource):
    def get(self, user_id=None):
        if user_id:
            user = User.find(user_id)
            if not user:
                return {'error': '用户未找到'}, 404
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
        return {'error': '创建用户失败'}, 400

api.add_resource(UserResource, '/users', '/users/<int:user_id>')

if __name__ == '__main__':
    app.run(debug=True)
```

## 与FastAPI集成

FastAPI是一个现代、高性能的Web框架，特别是在使用异步功能时，与ActiveRecord配合得很好。

### 基本设置

```python
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.backend import PostgreSQLBackend

app = FastAPI()

# 配置ActiveRecord
ActiveRecord.configure({
    'backend': PostgreSQLBackend,
    'host': 'localhost',
    'database': 'fastapi_db',
    'user': 'postgres',
    'password': 'password'
})

# 定义模型
class User(ActiveRecord):
    __tablename__ = 'users'
    # 模型定义

# Pydantic模式
class UserBase(BaseModel):
    name: str
    email: str

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    
    class Config:
        orm_mode = True

# FastAPI路由
@app.get("/users", response_model=List[UserResponse])
async def read_users():
    users = await User.query().all_async()
    return users

@app.get("/users/{user_id}", response_model=UserResponse)
async def read_user(user_id: int):
    user = await User.find_async(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户未找到")
    return user

@app.post("/users", response_model=UserResponse, status_code=201)
async def create_user(user: UserCreate):
    db_user = User(
        name=user.name,
        email=user.email
    )
    db_user.set_password(user.password)
    
    if not await db_user.save_async():
        raise HTTPException(status_code=400, detail="创建用户失败")
    return db_user
```

### 依赖注入

```python
from fastapi import Depends, FastAPI, HTTPException
from rhosocial.activerecord import ActiveRecord

app = FastAPI()

# 配置ActiveRecord
# ...

class User(ActiveRecord):
    __tablename__ = 'users'
    # 模型定义

async def get_user(user_id: int):
    user = await User.find_async(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="用户未找到")
    return user

@app.get("/users/{user_id}/profile")
async def read_user_profile(user: User = Depends(get_user)):
    profile = await user.get_profile_async()
    return profile.to_dict()
```

## 与Django集成

虽然Django有自己的ORM，但您可能希望使用ActiveRecord来实现特定功能或在逐步迁移时使用。

### 基本设置

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

# 配置ActiveRecord
ActiveRecord.configure(settings.ACTIVERECORD_CONFIG)

class User(ActiveRecord):
    __tablename__ = 'ar_users'  # 不同的表以避免冲突
    # 模型定义

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
            return JsonResponse({'error': '用户未找到'}, status=404)
        return JsonResponse(user.to_dict())
```

### Django REST Framework集成

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
            return Response({'error': '用户未找到'}, status=404)
        serializer = UserSerializer(user)
        return Response(serializer.data)
    
    def create(self, request):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response(serializer.data, status=201)
        return Response(serializer.errors, status=400)
```

## 与Pyramid集成

Pyramid是一个灵活的Web框架，可以轻松与ActiveRecord集成。

```python
from pyramid.config import Configurator
from pyramid.response import Response
from pyramid.view import view_config
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.backend import SQLiteBackend

# 配置ActiveRecord
ActiveRecord.configure({
    'backend': SQLiteBackend,
    'database': 'pyramid_app.db'
})

class User(ActiveRecord):
    __tablename__ = 'users'
    # 模型定义

@view_config(route_name='users', renderer='json')
def list_users(request):
    users = User.query().all()
    return {'users': [user.to_dict() for user in users]}

@view_config(route_name='user', renderer='json')
def get_user(request):
    user_id = request.matchdict['id']
    user = User.find(user_id)
    if not user:
        return Response(json_body={'error': '用户未找到'}, status=404)
    return user.to_dict()

def main(global_config, **settings):
    config = Configurator(settings=settings)
    config.add_route('users', '/users')
    config.add_route('user', '/users/{id}')
    config.scan()
    return config.make_wsgi_app()
```

## 与Tornado集成

Tornado是一个异步Web框架，可以与ActiveRecord的异步功能集成。

```python
import tornado.ioloop
import tornado.web
import json
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.backend import MySQLBackend

# 配置ActiveRecord
ActiveRecord.configure({
    'backend': MySQLBackend,
    'host': 'localhost',
    'database': 'tornado_db',
    'user': 'tornado',
    'password': 'password'
})

class User(ActiveRecord):
    __tablename__ = 'users'
    # 模型定义

class UserListHandler(tornado.web.RequestHandler):
    async def get(self):
        users = await User.query().all_async()
        self.write(json.dumps({'users': [user.to_dict() for user in users]}))

class UserHandler(tornado.web.RequestHandler):
    async def get(self, user_id):
        user = await User.find_async(int(user_id))
        if not user:
            self.set_status(404)
            self.write(json.dumps({'error': '用户未找到'}))
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

## 与Starlette集成

Starlette是一个轻量级的ASGI框架，与ActiveRecord的异步功能配合得很好。

```python
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route
import uvicorn
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.backend import PostgreSQLBackend

# 配置ActiveRecord
ActiveRecord.configure({
    'backend': PostgreSQLBackend,
    'host': 'localhost',
    'database': 'starlette_db',
    'user': 'postgres',
    'password': 'password'
})

class User(ActiveRecord):
    __tablename__ = 'users'
    # 模型定义

async def list_users(request):
    users = await User.query().all_async()
    return JSONResponse({'users': [user.to_dict() for user in users]})

async def get_user(request):
    user_id = request.path_params['user_id']
    user = await User.find_async(user_id)
    if not user:
        return JSONResponse({'error': '用户未找到'}, status_code=404)
    return JSONResponse(user.to_dict())

routes = [
    Route('/users', endpoint=list_users),
    Route('/users/{user_id:int}', endpoint=get_user),
]

app = Starlette(debug=True, routes=routes)

if __name__ == '__main__':
    uvicorn.run(app, host='0.0.0.0', port=8000)
```

## 最佳实践

### 1. 关注点分离

保持Web框架代码和ActiveRecord模型之间的清晰分离：

```python
# models/user.py - ActiveRecord模型
from rhosocial.activerecord import ActiveRecord

class User(ActiveRecord):
    __tablename__ = 'users'
    
    def to_dict(self):
        # 模型特定的序列化
        return {...}

# api/user_api.py - 框架特定代码
from models.user import User

# Flask示例
@app.route('/users')
def list_users():
    # 框架特定的请求处理
    users = User.query().all()
    return jsonify([user.to_dict() for user in users])
```

### 2. 配置管理

根据框架的约定管理ActiveRecord配置：

```python
# Flask示例
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

### 3. 连接生命周期管理

根据框架的请求生命周期确保适当的连接处理：

```python
# Flask示例，每个请求一个连接
@app.before_request
def before_request():
    ActiveRecord.connect()

@app.teardown_request
def teardown_request(exception=None):
    ActiveRecord.disconnect()
```

### 4. 错误处理

将ActiveRecord异常与框架的错误处理集成：

```python
# Flask示例
from rhosocial.activerecord.exceptions import RecordNotFoundError, ValidationError

@app.errorhandler(RecordNotFoundError)
def handle_not_found(error):
    return jsonify({'error': str(error)}), 404

@app.errorhandler(ValidationError)
def handle_validation_error(error):
    return jsonify({'error': str(error), 'fields': error.fields}), 400
```

## 常见模式

### 仓库模式

使用仓库来抽象Web控制器中的数据库操作：

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

# Flask示例
@app.route('/users/<int:user_id>')
def get_user(user_id):
    user = UserRepository.find_by_id(user_id)
    if not user:
        return jsonify({'error': '用户未找到'}), 404
    return jsonify(user.to_dict())
```

### 服务层

实现服务层处理复杂业务逻辑：

```python
# services/user_service.py
from repositories.user_repository import UserRepository
from services.email_service import EmailService

class UserService:
    @staticmethod
    def register_user(data):
        # 验证数据
        if not data.get('email') or not data.get('password'):
            raise ValueError("邮箱和密码是必填项")
        
        # 检查用户是否存在
        existing_user = UserRepository.find_by_email(data['email'])
        if existing_user:
            raise ValueError("邮箱已注册")
        
        # 创建用户
        user = UserRepository.create(data)
        
        # 发送欢迎邮件
        EmailService.send_welcome_email(user.email)
        
        return user

# controllers/user_controller.py
from services.user_service import UserService

# Flask示例
@app.route('/users', methods=['POST'])
def create_user():
    data = request.get_json()
    try:
        user = UserService.register_user(data)
        return jsonify(user.to_dict()), 201
    except ValueError as e:
        return jsonify({'error': str(e)}), 400
```

### 认证中间件

使用ActiveRecord模型实现认证中间件：

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
            return jsonify({'error': '缺少令牌'}), 401
        
        try:
            # 如果存在，移除'Bearer '前缀
            if token.startswith('Bearer '):
                token = token[7:]
            
            # 验证令牌并获取用户
            user = User.verify_token(token)
            if not user:
                return jsonify({'error': '无效令牌'}), 401
            
            # 将用户添加到请求上下文
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

通过遵循这些集成模式和最佳实践，您可以有效地将rhosocial ActiveRecord与您首选的Web框架结合使用，创建可维护且高效的Web应用程序。