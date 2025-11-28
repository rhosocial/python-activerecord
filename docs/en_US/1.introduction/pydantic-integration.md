# Pydantic Integration Advantages

rhosocial ActiveRecord's tight integration with Pydantic provides significant advantages that deserve special attention:

## 1. Seamless Ecosystem Integration

rhosocial ActiveRecord models can be directly used with other Pydantic-based libraries and frameworks:

- **FastAPI**: Models can be used as request/response schemas without conversion
- **Pydantic Settings**: Configuration management with the same validation
- **Data Validation Libraries**: Works with pydantic-extra-types, email-validator, etc.
- **Schema Generation**: Automatic OpenAPI schema generation
- **Data Transformation**: Easy model conversion with model_dump() and parse_obj()

## 2. Advanced Type Validation

rhosocial ActiveRecord inherits Pydantic's robust validation capabilities:

- **Complex Types**: Support for nested models, unions, literals, and generics
- **Custom Validators**: Field-level and model-level validation functions
- **Constrained Types**: Min/max values, string patterns, length constraints
- **Coercion**: Automatic type conversion when possible
- **Error Handling**: Detailed validation error messages

## 3. Schema Evolution and Documentation

- **JSON Schema Generation**: Export model definitions as JSON schema
- **Automatic Documentation**: Models are self-documenting with field descriptions
- **Schema Management**: Track model changes with version fields
- **Data Migration**: Convert between schema versions

## 4. Practical Development Benefits

- **IDE Integration**: Better type hints and autocompletion
- **Testing**: More precise mock objects with validation
- **Error Prevention**: Catch data issues at runtime before they reach the database
- **Code Reuse**: Use the same models for database access, API endpoints, and business logic

## Integration Example

Here's a complete example demonstrating how rhosocial ActiveRecord models integrate seamlessly with a FastAPI application:

### SQLite Database Schema

```sql
-- Users table
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    is_active BOOLEAN DEFAULT 1
);
```

### Complete Example Code

```python
#!/usr/bin/env python3
"""
Complete Pydantic & rhosocial ActiveRecord Integration Example
"""

from typing import List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr, Field
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
import sqlite3


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

# Use ActiveRecord model directly as FastAPI response model
@app.get("/users/", response_model=List[User])
async def get_users():
    """Get all users"""
    users = User.query().all()
    return users

@app.get("/users/{user_id}", response_model=User)
async def get_user(user_id: int):
    """Get a specific user"""
    user = User.find(user_id)
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
    configure_models()

    # 3. Demonstrate data operations
    new_user = User(name="Alice Smith", email="alice@example.com", is_active=True)
    new_user.save()

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
```

### Running the Application

To run this application, execute the following commands:

```bash
# Start the FastAPI server
uvicorn pydantic_integration_demo:app --reload --port 8000
```

Then visit `http://127.0.0.1:8000/docs` to view the interactive API documentation.

### Complete Source Code

The complete source code for this example can be found at: [pydantic_integration_demo.py](pydantic_integration_demo.py)

### FastAPI API Usage Examples

After starting the server, you can use the following API endpoints:

#### Starting the Server

To start the FastAPI server, switch to the directory containing the example file and execute the following commands:

```bash
# Switch to the example file directory
cd docs/en_US/1.introduction/

# Start the server
uvicorn pydantic_integration_demo:app --reload --port 8000
```

Note: The models will automatically configure the database backend when the server starts, ensuring proper initialization before using the models.

#### Get All Users
- **GET** `/users/`
- Example:
```bash
curl http://127.0.0.1:8000/users/
```
- Using jq for formatted output:
```bash
curl http://127.0.0.1:8000/users/ | jq '.'
```
- Example response:
```json
[
  {
    "id": 1,
    "name": "Test User 1 1764297021",
    "email": "test11764297021@example.com",
    "is_active": true
  },
  {
    "id": 2,
    "name": "Test User 2 1764297021",
    "email": "test21764297021@example.com",
    "is_active": true
  }
]
```

#### Get Specific User
- **GET** `/users/{user_id}`
- Example:
```bash
curl http://127.0.0.1:8000/users/1
```
- Using jq for formatted output:
```bash
curl http://127.0.0.1:8000/users/1 | jq '.'
```
- Example response:
```json
{
  "id": 1,
  "name": "Test User 1 1764297021",
  "email": "test11764297021@example.com",
  "is_active": true
}
```

#### Create New User
- **POST** `/users/`
- Request body:
```json
{
  "name": "John Doe",
  "email": "john@example.com",
  "is_active": true
}
```
- Example:
```bash
curl -X POST http://127.0.0.1:8000/users/ \
  -H "Content-Type: application/json" \
  -d '{"name":"John Doe","email":"john@example.com","is_active":true}'
```
- Using jq for formatted output:
```bash
curl -X POST http://127.0.0.1:8000/users/ \
  -H "Content-Type: application/json" \
  -d '{"name":"John Doe","email":"john@example.com","is_active":true}' | jq '.'
```
- Example response:
```json
{
  "id": 3,
  "name": "John Doe",
  "email": "john@example.com",
  "is_active": true
}
```

This seamless integration is not possible with other ORMs without additional conversion layers or helper libraries. Pydantic's validation features are directly available in ActiveRecord models, making data validation and type checking a natural part of database interactions.