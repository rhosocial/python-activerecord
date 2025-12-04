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

## 5. GraphQL Integration

rhosocial ActiveRecord's integration with GraphQL provides powerful features for modern web application development. Since models are based on Pydantic, they can easily integrate with GraphQL frameworks (like Graphene or Strawberry):

**Important Note**: When defining relationships, since ActiveRecord inherits from Pydantic's BaseModel, to avoid Pydantic treating relationships as regular fields, use the `typing.ClassVar` type hint to define relationships:

```python
from typing import ClassVar
from rhosocial.activerecord.relation.descriptors import HasMany, BelongsTo

class User(ActiveRecord):
    # Regular fields use regular type annotations
    id: Optional[int] = None
    name: str

    # Relationships must use ClassVar to avoid being processed by Pydantic as regular fields
    posts: ClassVar = HasMany["Post"](
        foreign_key="user_id",
        inverse_of="user"
    )
```

This approach ensures Pydantic's validation and serialization features only apply to actual data fields, not relationship descriptors.

- **Type reuse**: ActiveRecord models can serve as GraphQL type foundations
- **Validation reuse**: Pydantic validators automatically apply to GraphQL inputs
- **Data consistency**: Same models used for database operations and API responses
- **Performance optimization**: Leverage ActiveRecord's preloading features to avoid N+1 query problems

### GraphQL Integration Example

Here's an example showing how to integrate rhosocial ActiveRecord models with GraphQL:

#### Complete Example Code

```python
#!/usr/bin/env python3
"""
Pydantic & rhosocial ActiveRecord Integration Demo (with GraphQL support)
Demonstrates complete workflow including database schema, model definition, and REST + GraphQL API integration
"""

from typing import List, Optional
import sqlite3
import graphene
from graphene import ObjectType, String, Int, Boolean, List as GList
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import EmailStr, Field
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig


# SQLite Database Schema Definition
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
    """Setup SQLite database, creating required tables"""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Execute SQL schema
    cursor.executescript(sqlite_schema)
    conn.commit()
    conn.close()


# Define ActiveRecord Model with Pydantic-style type annotations
class User(ActiveRecord):
    __table_name__ = 'users'

    id: Optional[int] = None
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    is_active: bool = True


# Configure model backend immediately
def configure_models(db_path: str = "demo.db"):
    """Configure models to use SQLite backend"""
    config = SQLiteConnectionConfig(database=db_path)
    backend = SQLiteBackend(connection_config=config)

    # Configure backend for models
    User.configure(config, SQLiteBackend)


# GraphQL Type Definition
class UserGQL(ObjectType):
    id = Int(description="User unique identifier")
    name = String(description="User name")
    email = String(description="User email")
    is_active = Boolean(description="User is active", name="isActive")

    @staticmethod
    def from_active_record(user: User) -> 'UserGQL':
        """Create GraphQL type instance from ActiveRecord model instance"""
        return UserGQL(
            id=user.id,
            name=user.name,
            email=user.email,
            is_active=user.is_active
        )


# GraphQL Query Definition
class Query(ObjectType):
    user = graphene.Field(UserGQL, id=Int(required=True), description="Get specific user by ID")
    users = GList(UserGQL, description="Get all users")

    def resolve_user(self, info, id: int) -> Optional[UserGQL]:
        """Get specific user by ID"""
        user = User.find_one(id)
        return UserGQL.from_active_record(user) if user else None

    def resolve_users(self, info) -> List[UserGQL]:
        """Get all users"""
        users = User.query().all()
        return [UserGQL.from_active_record(user) for user in users]


# GraphQL Mutation Definition
class CreateUser(graphene.Mutation):
    class Arguments:
        name = String(required=True)
        email = String(required=True)
        is_active = Boolean(default_value=True)

    Output = UserGQL

    def mutate(self, info, name: str, email: str, is_active: bool = True):
        user = User(name=name, email=email, is_active=is_active)
        user.save()
        return UserGQL.from_active_record(user)


class UpdateUser(graphene.Mutation):
    class Arguments:
        id = Int(required=True)
        name = String()
        email = String()
        is_active = Boolean()

    Output = UserGQL

    def mutate(self, info, id: int, name: Optional[str] = None, email: Optional[str] = None, is_active: Optional[bool] = None):
        user = User.find_one(id)
        if not user:
            return None

        if name is not None:
            user.name = name
        if email is not None:
            user.email = email
        if is_active is not None:
            user.is_active = is_active

        user.save()
        return UserGQL.from_active_record(user)


class DeleteUser(graphene.Mutation):
    class Arguments:
        id = Int(required=True)

    Output = Boolean

    def mutate(self, info, id: int):
        user = User.find_one(id)
        if not user:
            return False

        user.delete()
        return True


class Mutation(ObjectType):
    create_user = CreateUser.Field()
    update_user = UpdateUser.Field()
    delete_user = DeleteUser.Field()


# Create GraphQL Schema
schema = graphene.Schema(query=Query, mutation=Mutation)


# FastAPI Application
app = FastAPI(
    title="Pydantic & ActiveRecord Integration Demo with GraphQL",
    description="Demonstrates seamless integration between Pydantic and rhosocial ActiveRecord, supporting both REST and GraphQL APIs",
    version="1.0.0"
)

# Add CORS middleware for frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure models on application startup
@app.on_event("startup")
def startup_event():
    setup_database()  # Ensure database is created
    configure_models()

# Use ActiveRecord models directly as FastAPI response models - keep existing REST API
@app.get("/users/", response_model=List[User])
async def get_users_rest():
    """Get all users (REST API)"""
    users = User.query().all()
    return users

@app.get("/users/{user_id}", response_model=User)
async def get_user_rest(user_id: int):
    """Get specific user (REST API)"""
    user = User.find_one(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@app.post("/users/", response_model=User)
async def create_user_rest(user: User):
    """Create new user (REST API)"""
    # User has already been validated by Pydantic
    user.save()
    return user


# GraphQL Integration - Add GraphQL endpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.types import Receive, Send
from graphql import graphql, print_schema


class GraphQLApp:
    def __init__(self, schema):
        self.schema = schema

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            request = Request(scope, receive)

            if request.method == "GET":
                # Show GraphiQL interface or return GraphQL Schema
                html_content = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>GraphiQL</title>
                    <script src="https://unpkg.com/react@17/umd/react.development.js"></script>
                    <script src="https://unpkg.com/react-dom@17/umd/react-dom.development.js"></script>
                    <link rel="stylesheet" href="https://unpkg.com/graphiql@2.0.0/graphiql.min.css" />
                    <script src="https://unpkg.com/graphiql@2.0.0/graphiql.min.js"></script>
                </head>
                <body style="margin: 0; overflow: hidden; width: 100%; height: 100vh;">
                    <div id="graphiql" style="height: 100vh;"></div>
                    <script>
                        const root = ReactDOM.createRoot(document.getElementById('graphiql'));
                        root.render(
                            React.createElement(
                                GraphiQL,
                                {{
                                    fetcher: GraphiQL.createFetcher({{ url: '/graphql' }}),
                                    document: `{print_schema(self.schema)}`,
                                }},
                            ),
                        );
                    </script>
                </body>
                </html>
                """
                response = Response(content=html_content, media_type="text/html")
                await response(scope, receive, send)
            elif request.method == "POST":
                content = await request.json()
                query = content.get("query")
                variables = content.get("variables")

                result = graphql(
                    self.schema.graphql_schema,
                    query,
                    variable_values=variables
                )

                response_data = {"data": result.data}
                if result.errors:
                    response_data["errors"] = [str(error) for error in result.errors]

                response = JSONResponse(response_data)
                await response(scope, receive, send)


graphql_app = GraphQLApp(schema=schema)
app.add_route("/graphql", graphql_app)


def run_demo():
    """Run complete demonstration flow"""
    # 1. Setup database
    setup_database()

    # 2. Configure models
    configure_models()

    # 3. Demonstrate data operations
    # Use timestamp to ensure uniqueness
    import time
    timestamp = str(int(time.time()))
    new_user = User(name=f"Alice Smith {timestamp}", email=f"alice{timestamp}@example.com", is_active=True)
    new_user.save()
    print(f"Created user: {new_user.name} ({new_user.email})")

    # 4. Query data verification
    users = User.query().all()
    print(f"Database contains {len(users)} users")

    # 5. Demonstrate Pydantic validation
    try:
        invalid_user = User(name="Test", email="invalid-email", is_active=True)
        print("Email validation failed - should throw exception but did not")
    except Exception as e:
        print(f"Pydantic validation successfully caught invalid email: {type(e).__name__}")

    # 6. Demonstrate GraphQL queries (conceptual)
    print("\nGraphQL API available at /graphql endpoint")
    print("Example queries:")
    print("  Query all users: { users { id name email isActive } }")
    print("  Query specific user: { user(id: 1) { id name email } }")
    print("  Create user: mutation { createUser(name: \"John\", email: \"john@example.com\") { id name email } }")


if __name__ == "__main__":
    run_demo()
```

### Running the App

To run the app with GraphQL functionality, execute the following command:

```bash
# Install GraphQL dependencies
pip install graphene graphql-core

# Start the FastAPI server
uvicorn pydantic_graphql_demo:app --reload --port 8000
```

Then visit `http://127.0.0.1:8000/graphql` to access the GraphiQL interface for GraphQL queries.

### GraphQL Interface Usage Examples

After starting the server, you can use the following GraphQL interfaces:

#### Query All Users
```graphql
{
  users {
    id
    name
    email
    isActive
  }
}
```

#### Query Specific User
```graphql
{
  user(id: 1) {
    id
    name
    email
    isActive
  }
}
```

#### Create New User
```graphql
mutation {
  createUser(name: "John Doe", email: "john@example.com", isActive: true) {
    id
    name
    email
    is_active
  }
}
```

#### Update User Information
```graphql
mutation {
  updateUser(id: 1, name: "John Updated") {
    id
    name
    email
    isActive
  }
}
```

#### Delete User
```graphql
mutation {
  deleteUser(id: 1)
}
```

This integration approach preserves all ActiveRecord model features, including preloading and transaction processing, while providing flexible data query capabilities through GraphQL.

## Relationship Preloading & GraphQL Optimization

rhosocial ActiveRecord has built-in relationship preloading features that can effectively solve the N+1 query problem common in GraphQL queries. In GraphQL resolvers, you can use the `with_` method to preload related data:

```python
# GraphQL resolver preloading related data
class Query(ObjectType):
    user_with_posts = graphene.Field(UserWithPostsGQL, id=Int(required=True))

    def resolve_user_with_posts(self, info, id: int):
        # Preload user and all their posts, avoiding N+1 query problem
        user = User.query().with_('posts').find_one(id)
        return UserWithPostsGQL.from_active_record(user)
```

Here's a more complex example showing how to use preloading with relationship models:

```python
# Define models with relationships
class User(ActiveRecord):
    __table_name__ = 'users'

    id: Optional[int] = None
    name: str
    email: EmailStr
    is_active: bool = True

    # One user has many posts (using ClassVar to avoid Pydantic treating it as a regular field)
    posts: ClassVar = HasMany["Post"](
        foreign_key="user_id",
        inverse_of="user"
    )

class Post(ActiveRecord):
    __table_name__ = 'posts'

    id: Optional[int] = None
    title: str
    content: Optional[str]
    user_id: int

    # One post belongs to one user (using ClassVar to avoid Pydantic treating it as a regular field)
    user: ClassVar = BelongsTo[User](
        foreign_key="user_id",
        inverse_of="posts"
    )


# GraphQL Type Definitions
class UserGQL(ObjectType):
    id = Int()
    name = String()
    email = String()
    is_active = Boolean(name="isActive")  # Using camelCase field name
    posts = GList(lambda: PostGQL)  # All posts of the user

    @staticmethod
    def from_active_record(user: User, include_posts: bool = True) -> 'UserGQL':
        user_gql = UserGQL(
            id=user.id,
            name=user.name,
            email=user.email,
            is_active=user.is_active
        )
        # If preloading has been executed, this will use cached relation data
        if include_posts:
            posts_relation = getattr(user, 'posts', None)  # Get relation descriptor
            if posts_relation is not None:
                # Call the relation to get actual data
                posts_data = posts_relation() if callable(posts_relation) else posts_relation
                if posts_data:
                    user_gql.posts = [PostGQL.from_active_record(post) for post in posts_data]
        return user_gql


class PostGQL(ObjectType):
    id = Int()
    title = String()
    content = String()
    user_id = Int(name="userId")  # Using camelCase field name
    user = graphene.Field(lambda: UserGQL)  # Author of the post

    @staticmethod
    def from_active_record(post: Post, include_user: bool = True) -> 'PostGQL':
        post_gql = PostGQL(
            id=post.id,
            title=post.title,
            content=post.content,
            user_id=post.user_id
        )
        # If preloading has been executed, this will use cached relation data
        if include_user:
            user_relation = getattr(post, 'user', None)  # Get relation descriptor
            if user_relation is not None:
                # Call the relation to get actual data
                user_data = user_relation() if callable(user_relation) else user_relation
                if user_data is not None:
                    post_gql.user = UserGQL.from_active_record(user_data, include_posts=False)
        return post_gql


# GraphQL Query Definition, using preloading optimization
class Query(ObjectType):
    users = GList(UserGQL)  # Get all users with posts
    posts = GList(PostGQL)  # Get all posts with authors

    def resolve_users(self, info):
        # Use preloading to get users and their posts in one go, avoiding N+1 queries
        users = User.query().with_('posts').all()
        return [UserGQL.from_active_record(user) for user in users]

    def resolve_posts(self, info):
        # Use preloading to get posts and their authors in one go, avoiding N+1 queries
        posts = Post.query().with_('user').all()
        return [PostGQL.from_active_record(post) for post in posts]
```

Through this approach, when GraphQL clients request nested data (like `{ users { posts { title } } }`), the backend only requires a limited number of database queries rather than a separate query for each relationship.

This design ensures high performance is maintained when using GraphQL for complex queries.

## Testing GraphQL API with Postman

After starting the application, you can test the GraphQL API using Postman:

1. After starting with uvicorn, fill in http://localhost:8000/graphql in Postman and change to POST method.
2. Switch Body to GraphQL, and enable Auto Fetch. On first use, you may need to manually click the "Refresh" button.
3. In the QUERY box, you can enter queries such as "{ users { id,posts { id,title } } }". The query result will be:

```json
{
    "data": {
        "users": [
            {
                "id": 1,
                "posts": [
                    {
                        "id": 1,
                        "title": "First Post"
                    },
                    {
                        "id": 2,
                        "title": "Second Post"
                    }
                ]
            },
            {
                "id": 2,
                "posts": [
                    {
                        "id": 3,
                        "title": "Bob's Post"
                    }
                ]
            }
        ]
    }
}
```

This seamless integration is not possible with other ORMs without additional conversion layers or helper libraries. Pydantic's validation features are directly available in ActiveRecord models, making data validation and type checking a natural part of database interactions.