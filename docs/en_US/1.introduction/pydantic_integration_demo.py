#!/usr/bin/env python3
"""
Pydantic & rhosocial ActiveRecord Integration Demo
Shows the complete flow, including database schema, model definition, and API integration
"""

from typing import List, Optional
import sqlite3
from fastapi import FastAPI, HTTPException
from pydantic import EmailStr, Field
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig


# SQLite database schema definition
sqlite_schema = """
-- Users table
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    is_active BOOLEAN DEFAULT 1
);
"""


def setup_database(db_path: str = "demo.db"):
    """Set up SQLite database, creating required tables"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Execute SQL schema
    cursor.executescript(sqlite_schema)
    conn.commit()
    conn.close()


# Define ActiveRecord model with Pydantic-style type annotations
class User(ActiveRecord):
    __table_name__ = 'users'

    id: Optional[int] = None
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    is_active: bool = True


# 立即配置模型后端
def configure_models(db_path: str = "demo.db"):
    """Configure models to use SQLite backend"""
    config = SQLiteConnectionConfig(database=db_path)
    backend = SQLiteBackend(connection_config=config)

    # Configure backend for the model
    User.configure(config, SQLiteBackend)


# FastAPI application
app = FastAPI(
    title="Pydantic & ActiveRecord Integration Demo",
    description="Demonstrates seamless integration of Pydantic with rhosocial ActiveRecord",
    version="1.0.0"
)

# Configure models when FastAPI starts up
@app.on_event("startup")
def startup_event():
    configure_models()

# Use ActiveRecord model directly as FastAPI response model
@app.get("/users/", response_model=List[User])
async def get_users():
    """Get all users"""
    users = User.query().all()
    return users

@app.get("/users/{user_id}", response_model=User)
async def get_user(user_id: int):
    """Get a specific user"""
    user = User.find_one(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.post("/users/", response_model=User)
async def create_user(user: User):
    """Create a new user"""
    # User is already validated by Pydantic
    user.save()
    return user


def run_demo():
    """Run complete demonstration"""
    # 1. Set up database
    setup_database()

    # 2. Configure models
    configure_models()  # Ensure models are configured each time

    # 3. Demonstrate data operations
    # Use timestamp to ensure uniqueness
    import time
    timestamp = str(int(time.time()))
    new_user = User(name=f"Alice Smith {timestamp}", email=f"alice{timestamp}@example.com", is_active=True)
    new_user.save()
    print(f"Created user: {new_user.name} ({new_user.email})")

    # 4. Query data for validation
    users = User.query().all()
    print(f"Database contains {len(users)} users")

    # 5. Demonstrate Pydantic validation
    try:
        invalid_user = User(name="Test", email="invalid-email", is_active=True)
        print("Email validation failed - should have thrown an exception")
    except Exception as e:
        print(f"Pydantic validation successfully caught invalid email: {type(e).__name__}")


if __name__ == "__main__":
    run_demo()