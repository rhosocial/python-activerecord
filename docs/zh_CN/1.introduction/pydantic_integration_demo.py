#!/usr/bin/env python3
"""
Pydantic 与 rhosocial ActiveRecord 集成演示
展示了完整的流程，包括数据库模式、模型定义和 API 集成
"""

from typing import List, Optional
import sqlite3
from fastapi import FastAPI, HTTPException
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


# FastAPI 应用
app = FastAPI(
    title="Pydantic & ActiveRecord Integration Demo",
    description="演示 Pydantic 与 rhosocial ActiveRecord 的无缝集成",
    version="1.0.0"
)

# 在FastAPI应用启动时配置模型
@app.on_event("startup")
def startup_event():
    configure_models()

# 直接使用 ActiveRecord 模型作为 FastAPI 响应模型
@app.get("/users/", response_model=List[User])
async def get_users():
    """获取所有用户"""
    users = User.query().all()
    return users

@app.get("/users/{user_id}", response_model=User)
async def get_user(user_id: int):
    """获取特定用户"""
    user = User.find_one(user_id)
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
    configure_models()  # 确保每次运行时都配置模型

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


if __name__ == "__main__":
    run_demo()