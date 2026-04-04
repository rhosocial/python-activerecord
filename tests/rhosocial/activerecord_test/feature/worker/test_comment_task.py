# tests/rhosocial/activerecord_test/feature/worker/test_comment_task.py
# ruff: noqa: E402
"""
Comment task tests: demonstrate task running independently and via WorkerPool.

Design principles:
1. Tasks are fully independent functions, not dependent on WorkerPool
2. Tasks manage their own database connections, ORM configuration, transactions
3. Input and output are serializable simple types
"""

import os
import sys
import tempfile

# Ensure src directory is in path
src = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "..", "..", "src"))
if src not in sys.path:
    sys.path.insert(0, src)

import pytest

# Import models from testsuite
from rhosocial.activerecord.testsuite.feature.query.fixtures.models import User, Post, Comment

# Import task function from separate module
from worker_comment_task import submit_comment_task  # noqa: E402


# ─────────────────────────────────────────────────────────────────────────────
# Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestCommentTask:
    """Test comment task"""

    @pytest.fixture
    def temp_db(self):
        """Create temporary database and initialize test data"""
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)

        # Use sqlite3 directly to create tables
        import sqlite3
        conn = sqlite3.connect(path)
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                email TEXT NOT NULL,
                age INTEGER,
                balance REAL DEFAULT 0.0,
                is_active INTEGER DEFAULT 1,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                status TEXT DEFAULT 'published',
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cursor.execute("""
            CREATE TABLE comments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                post_id INTEGER NOT NULL,
                content TEXT NOT NULL,
                is_hidden INTEGER DEFAULT 0,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Insert test users
        cursor.execute("INSERT INTO users (username, email, is_active) VALUES ('alice', 'alice@test.com', 1)")
        cursor.execute("INSERT INTO users (username, email, is_active) VALUES ('bob', 'bob@test.com', 1)")

        # Insert test posts
        cursor.execute(
            "INSERT INTO posts (user_id, title, content, status) "
            "VALUES (1, 'Hello', 'Hello World', 'published')"
        )

        conn.commit()
        conn.close()

        yield path

        try:
            os.unlink(path)
        except Exception:
            pass

    def test_task_single_thread(self, temp_db):
        """Test: execute task directly in single thread (without WorkerPool)"""
        # Read initial data
        from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
        from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig

        config = SQLiteConnectionConfig(database=temp_db)
        User.configure(config, SQLiteBackend)
        Post.__backend__ = User.backend()
        Comment.__backend__ = User.backend()

        user2 = User.query().where(User.c.username == 'bob').one()
        post = Post.query().one()

        User.backend().disconnect()

        # Call task function directly
        result = submit_comment_task({
            'db_path': temp_db,
            'post_id': post.id,
            'user_id': user2.id,
            'content': 'Great post!'
        })

        # Verify result
        assert isinstance(result, int)
        assert result > 0

        # Verify comment was created
        User.configure(config, SQLiteBackend)
        Post.__backend__ = User.backend()
        Comment.__backend__ = User.backend()

        comment = Comment.find_one(result)
        assert comment is not None
        assert comment.content == 'Great post!'
        assert comment.user_id == user2.id
        assert comment.post_id == post.id

        User.backend().disconnect()

    def test_task_via_worker_pool(self, temp_db):
        """Test: execute task via WorkerPool"""
        from rhosocial.activerecord.worker import WorkerPool

        # Read initial data
        from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
        from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig

        config = SQLiteConnectionConfig(database=temp_db)
        User.configure(config, SQLiteBackend)
        Post.__backend__ = User.backend()
        Comment.__backend__ = User.backend()

        user2 = User.query().where(User.c.username == 'bob').one()
        post = Post.query().one()

        User.backend().disconnect()

        # Execute task via WorkerPool
        with WorkerPool(n_workers=2) as pool:
            future = pool.submit(submit_comment_task, {
                'db_path': temp_db,
                'post_id': post.id,
                'user_id': user2.id,
                'content': 'Nice article!'
            })

            comment_id = future.result(timeout=10)

        # Verify result
        assert isinstance(comment_id, int)
        assert comment_id > 0

        # Verify comment was created
        User.configure(config, SQLiteBackend)
        Post.__backend__ = User.backend()
        Comment.__backend__ = User.backend()

        comment = Comment.find_one(comment_id)
        assert comment is not None
        assert comment.content == 'Nice article!'

        User.backend().disconnect()

    def test_task_batch_via_worker_pool(self, temp_db):
        """Test: execute batch tasks via WorkerPool"""
        from rhosocial.activerecord.worker import WorkerPool

        # Read initial data
        from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
        from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig

        config = SQLiteConnectionConfig(database=temp_db)
        User.configure(config, SQLiteBackend)
        Post.__backend__ = User.backend()
        Comment.__backend__ = User.backend()

        user2 = User.query().where(User.c.username == 'bob').one()
        post = Post.query().one()

        User.backend().disconnect()

        # Batch submit comments
        comments_data = [
            {'db_path': temp_db, 'post_id': post.id, 'user_id': user2.id, 'content': f'Comment {i}'}
            for i in range(5)
        ]

        with WorkerPool(n_workers=2) as pool:
            futures = [pool.submit(submit_comment_task, data) for data in comments_data]
            comment_ids = [f.result(timeout=10) for f in futures]

        # Verify results
        assert len(comment_ids) == 5
        assert all(isinstance(cid, int) and cid > 0 for cid in comment_ids)

        # Verify comments were created
        User.configure(config, SQLiteBackend)
        Post.__backend__ = User.backend()
        Comment.__backend__ = User.backend()

        for i, comment_id in enumerate(comment_ids):
            comment = Comment.find_one(comment_id)
            assert comment is not None
            assert comment.content == f'Comment {i}'

        User.backend().disconnect()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
