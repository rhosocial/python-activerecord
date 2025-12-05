#!/usr/bin/env python3
"""
Pydantic & rhosocial ActiveRecord Integration Demo (with GraphQL support)
Demonstrates complete workflow including database schema, model definition, and REST + GraphQL API integration
"""

from typing import List, Optional, ClassVar
import sqlite3
import graphene
import logging
from graphene import ObjectType, String, Int, Boolean, List as GList, NonNull
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import EmailStr, Field
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig


# Enable debug logging
logging.basicConfig(level=logging.DEBUG)


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
async def startup_event():
    User.setup_logger()
    logging.getLogger('activerecord').setLevel(logging.DEBUG)
    
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
from graphql import graphql, graphql_sync, print_schema


class GraphQLApp:
    def __init__(self, schema):
        self.schema = schema

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            request = Request(scope, receive)

            if request.method == "GET":
                # Display GraphiQL interface or return GraphQL Schema
                # Build schema document
                try:
                    schema_str = print_schema(self.schema.graphql_schema)
                except:
                    schema_str = ''

                html_content = f"""
                <!DOCTYPE html>
                <html>
                <head>
                    <title>GraphiQL</title>
                    <script src="https://unpkg.com/react@^18/umd/react.development.js"></script>
                    <script src="https://unpkg.com/react-dom@^18/umd/react-dom.development.js"></script>
                    <link rel="stylesheet" href="https://unpkg.com/graphiql@^2/graphiql.min.css" />
                    <script src="https://unpkg.com/graphiql@^2/graphiql.min.js"></script>
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
                                    document: `{schema_str}`,
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

                result = graphql_sync(
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