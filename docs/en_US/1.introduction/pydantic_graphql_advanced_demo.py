#!/usr/bin/env python3
"""
Advanced Pydantic & rhosocial ActiveRecord Integration Demo (with GraphQL Preloading Optimization)
Demonstrates how to use ActiveRecord's preloading features to solve N+1 query problems in GraphQL environments
"""

from typing import List, Optional, ClassVar
import sqlite3
import graphene
import logging
from graphene import ObjectType, String, Int, Boolean, List as GList
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import EmailStr, Field
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.relation.descriptors import HasMany, BelongsTo


# Enable debug logging
logging.basicConfig(level=logging.DEBUG)


# SQLite database schema definition
sqlite_schema = """
-- Users table
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    is_active BOOLEAN DEFAULT 1
);

-- Posts table
CREATE TABLE IF NOT EXISTS posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    content TEXT,
    user_id INTEGER NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users (id)
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


# Define ActiveRecord Models
class User(ActiveRecord):
    __table_name__ = 'users'

    id: Optional[int] = None
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    is_active: bool = True

    # Define relationship: one user has many posts (using ClassVar to avoid Pydantic treating it as a regular field)
    posts: ClassVar[HasMany["Post"]] = HasMany["Post"](
        foreign_key="user_id",
        inverse_of="user"
    )


class Post(ActiveRecord):
    __table_name__ = 'posts'

    id: Optional[int] = None
    title: str
    content: Optional[str] = None
    user_id: int

    # Define relationship: one post belongs to one user (using ClassVar to avoid Pydantic treating it as a regular field)
    user: ClassVar[BelongsTo[User]] = BelongsTo[User](
        foreign_key="user_id",
        inverse_of="posts"
    )


# Configure model backend
def configure_models(db_path: str = "demo.db"):
    """Configure models to use SQLite backend"""
    config = SQLiteConnectionConfig(database=db_path)
    User.configure(config, SQLiteBackend)
    Post.configure(config, SQLiteBackend)


# GraphQL Type Definitions
class UserGQL(ObjectType):
    id = Int(description="User unique identifier")
    name = String(description="User name")
    email = String(description="User email")
    is_active = Boolean(description="User is active", name="isActive")
    posts = GList(lambda: PostGQL, description="All posts of the user")

    @staticmethod
    def from_active_record(user: User, include_posts: bool = True) -> 'UserGQL':
        """Create GraphQL type instance from ActiveRecord model instance"""
        user_gql = UserGQL(
            id=user.id,
            name=user.name,
            email=user.email,
            is_active=user.is_active
        )

        if include_posts:
            # If user's posts have been preloaded via with_(), use cached value
            posts_relation = getattr(user, 'posts', None)  # Get relation descriptor
            if posts_relation is not None:
                # Call the relation to get actual data
                posts_data = posts_relation() if callable(posts_relation) else posts_relation
                if posts_data:
                    print(f"Cached posts({len(posts_data)}) found.")
                    user_gql.posts = [PostGQL.from_active_record(post) for post in posts_data]
                else:
                    print("Posts relation accessed but no data found.")
            else:
                print("No posts relation found.")
        return user_gql


class PostGQL(ObjectType):
    id = Int(description="Post unique identifier")
    title = String(description="Post title")
    content = String(description="Post content")
    user_id = Int(description="User ID", name="userId")
    user = graphene.Field(lambda: UserGQL, description="Author of the post")

    @staticmethod
    def from_active_record(post: Post, include_user: bool = True) -> 'PostGQL':
        """Create GraphQL type instance from ActiveRecord model instance"""
        post_gql = PostGQL(
            id=post.id,
            title=post.title,
            content=post.content,
            user_id=post.user_id
        )

        if include_user:
            # If post's user has been preloaded via with_(), use cached value
            user_relation = getattr(post, 'user', None)  # Get relation descriptor
            if user_relation is not None:
                # Call the relation to get actual data
                user_data = user_relation() if callable(user_relation) else user_relation
                if user_data is not None:
                    post_gql.user = UserGQL.from_active_record(user_data, include_posts=False)

        return post_gql


# GraphQL Query Definitions
class Query(ObjectType):
    user = graphene.Field(UserGQL, id=Int(required=True), description="Get specific user by ID")
    users = GList(UserGQL, description="Get all users (with posts)")
    post = graphene.Field(PostGQL, id=Int(required=True), description="Get specific post by ID")
    posts = GList(PostGQL, description="Get all posts (with authors)")

    def resolve_user(self, info, id: int) -> Optional[UserGQL]:
        """Get specific user by ID (with posts)"""
        # Use preloading to avoid N+1 problem
        try:
            user = User.query().with_('posts').where('id = ?', (id, )).one()
            return UserGQL.from_active_record(user) if user else None
        except Exception as e:
            print(f"Error in resolve_user: {e}")
            raise

    def resolve_users(self, info) -> List[UserGQL]:
        """Get all users (with posts)"""
        # Use preloading to avoid N+1 problem
        try:
            users = User.query().with_('posts').all()
            return [UserGQL.from_active_record(user) for user in users]
        except Exception as e:
            print(f"Error in resolve_users: {e}")
            # If with_ causes problems, fall back to basic query
            users = User.query().all()
            return [UserGQL.from_active_record(user, include_posts=False) for user in users]

    def resolve_post(self, info, id: int) -> Optional[PostGQL]:
        """Get specific post by ID (with author)"""
        # Use preloading to avoid N+1 problem
        try:
            post = Post.query().with_('user').where('id = ?', (id, )).one()
            return PostGQL.from_active_record(post) if post else None
        except Exception as e:
            print(f"Error in resolve_post: {e}")
            raise

    def resolve_posts(self, info) -> List[PostGQL]:
        """Get all posts (with authors)"""
        # Use preloading to avoid N+1 problem
        try:
            posts = Post.query().with_('user').all()
            return [PostGQL.from_active_record(post) for post in posts]
        except Exception as e:
            print(f"Error in resolve_posts: {e}")
            # If with_ causes problems, fall back to basic query
            posts = Post.query().all()
            return [PostGQL.from_active_record(post, include_user=False) for post in posts]


# GraphQL Mutation Definitions
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


class CreatePost(graphene.Mutation):
    class Arguments:
        title = String(required=True)
        content = String()
        user_id = Int(required=True)

    Output = PostGQL

    def mutate(self, info, title: str, content: Optional[str], user_id: int):
        post = Post(title=title, content=content, user_id=user_id)
        post.save()
        return PostGQL.from_active_record(post)


class Mutation(ObjectType):
    create_user = CreateUser.Field()
    create_post = CreatePost.Field()


# Create GraphQL Schema
schema = graphene.Schema(query=Query, mutation=Mutation)


# FastAPI Application
app = FastAPI(
    title="Advanced Pydantic & ActiveRecord GraphQL Demo",
    description="Demonstrates using ActiveRecord's preloading features to solve N+1 query problems in GraphQL",
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
    # Set logging level for ActiveRecord models
    User.setup_logger()
    Post.setup_logger()
    logging.getLogger('activerecord').setLevel(logging.DEBUG)

    setup_database()  # Ensure database is created
    configure_models()  # Configure models

    # Create sample data
    user_count = User.query().count()
    print(f"User count before creation: {user_count}")

    if user_count == 0:
        print("Creating sample data...")
        user1 = User(name="Alice Smith", email="alice@example.com", is_active=True)
        user1.save()
        print(f"Created user1 with id: {user1.id}")

        user2 = User(name="Bob Johnson", email="bob@example.com", is_active=True)
        user2.save()
        print(f"Created user2 with id: {user2.id}")

        post1 = Post(title="First Post", content="This is the first post", user_id=user1.id)
        post1.save()
        print(f"Created post1 with id: {post1.id}")

        post2 = Post(title="Second Post", content="This is the second post", user_id=user1.id)
        post2.save()
        print(f"Created post2 with id: {post2.id}")

        post3 = Post(title="Bob's Post", content="This is Bob's post", user_id=user2.id)
        post3.save()
        print(f"Created post3 with id: {post3.id}")

        print(f"Total users after creation: {User.query().count()}")
        print(f"Total posts after creation: {Post.query().count()}")
    else:
        print(f"Found existing {user_count} users, skipping sample data creation")


# GraphQL Integration
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
    # Set up database and models
    setup_database()
    configure_models()

    print("GraphQL N+1 Optimization Demo")
    print("==============================")

    # Demonstrate preloading vs non-preloading performance differences
    print("\nScenario 1: Get all users and their posts (using preloading)")
    print("Query: { users { id name email isActive posts { id title } } }")
    print(" - Using User.query().with_('posts').all() - 2 database queries")
    print("   1 query for all users")
    print("   1 query for all users' posts (via user_id IN (...))")

    print("\nScenario 2: Get all posts and their authors (using preloading)")
    print("Query: { posts { id title user { id name email isActive } } }")
    print(" - Using Post.query().with_('user').all() - 2 database queries")
    print("   1 query for all posts")
    print("   1 query for all posts' authors (via id IN (...))")

    print("\nScenario 3: Without preloading")
    print("Query: { users { id name email isActive posts { id title } } }")
    print(" - Using regular query - N+1 database queries")
    print("   1 query for all users")
    print("   N queries for each user's posts")

    print("\nGraphQL API available at /graphql endpoint")
    print("Preloading features ensure high performance even with complex nested queries")


if __name__ == "__main__":
    run_demo()