import sys
import os
import asyncio
from promise import Promise

# Add src to path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.abspath(os.path.join(current_dir, "../../../../src"))
sys.path.insert(0, src_dir)

# Also ensure current dir is in path for imports (it usually is, but just in case)
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from schema import schema
from models import User, Post, Comment, setup_database, seed_data
from main import Loaders # Import Loaders from main

# Override backend to use memory for testing
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend, SQLiteConnectionConfig

def test_query():
    # Setup DB
    # Let's manually setup backend to :memory: to be safe and clean
    backend = SQLiteBackend(connection_config=SQLiteConnectionConfig(
        database=":memory:", 
        options={"check_same_thread": False}
    ))
    User.__backend__ = backend
    Post.__backend__ = backend
    Comment.__backend__ = backend
    
    # Create tables manually (copying from models.py essentially)
    with backend.connection as conn:
        conn.execute(f"CREATE TABLE {User.table_name()} (id TEXT PRIMARY KEY, username TEXT, email TEXT, created_at INTEGER, updated_at INTEGER)")
        conn.execute(f"CREATE TABLE {Post.table_name()} (id TEXT PRIMARY KEY, user_id TEXT, title TEXT, content TEXT, created_at INTEGER, updated_at INTEGER)")
        conn.execute(f"CREATE TABLE {Comment.table_name()} (id TEXT PRIMARY KEY, user_id TEXT, post_id TEXT, content TEXT, created_at INTEGER, updated_at INTEGER)")
        
    # Seed data
    u1 = User(username="alice", email="alice@example.com")
    u1.save()
    u2 = User(username="bob", email="bob@example.com")
    u2.save()
    
    p1 = Post(user_id=u1.id, title="Alice's First Post", content="Hello World")
    p1.save()
    
    c1 = Comment(user_id=u2.id, post_id=p1.id, content="Nice post Alice!")
    c1.save()
    
    print("Data seeded.")

    query = """
    query {
        users {
            username
            posts {
                title
                comments {
                    content
                    user {
                        username
                    }
                }
            }
        }
    }
    """
    
    # Mock context with loaders
    context = {"loaders": Loaders()}
    
    # Run async query
    loop = asyncio.get_event_loop()
    result = loop.run_until_complete(schema.execute_async(query, context_value=context))
    
    if result.errors:
        print("Errors:", result.errors)
        sys.exit(1)
        
    print("Result:", result.data)
    
    # Verify data
    users = result.data['users']
    alice = next((u for u in users if u['username'] == 'alice'), None)
    if not alice:
        print("Alice not found")
        sys.exit(1)
        
    if len(alice['posts']) != 1:
        print(f"Expected 1 post for Alice, got {len(alice['posts'])}")
        sys.exit(1)
        
    post = alice['posts'][0]
    if post['title'] != "Alice's First Post":
        print(f"Unexpected title: {post['title']}")
        sys.exit(1)
        
    if len(post['comments']) != 1:
        print(f"Expected 1 comment, got {len(post['comments'])}")
        sys.exit(1)
        
    comment = post['comments'][0]
    if comment['content'] != "Nice post Alice!":
        print(f"Unexpected comment content: {comment['content']}")
        sys.exit(1)
        
    if comment['user']['username'] != "bob":
        print(f"Unexpected comment user: {comment['user']['username']}")
        sys.exit(1)
    
    print("GraphQL Test Passed!")

if __name__ == "__main__":
    test_query()
