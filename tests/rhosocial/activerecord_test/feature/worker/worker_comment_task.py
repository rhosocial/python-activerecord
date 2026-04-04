# tests/rhosocial/activerecord_test/feature/worker/worker_comment_task.py
"""
Comment task module: defines pickle-serializable task functions.

This module can be correctly imported by Worker processes.
Uses User, Post, Comment models from testsuite.
"""

from typing import Optional

# Import models from testsuite
from rhosocial.activerecord.testsuite.feature.query.fixtures.models import User, Post, Comment


def submit_comment_task(params: dict) -> int:
    """
    Submit comment task.

    This is a fully independent task function that can be executed anywhere:
    - Direct call in single thread
    - Execution via WorkerPool

    Args:
        params: Dictionary containing the following keys
            - db_path: Database path
            - post_id: Post ID
            - user_id: User ID
            - content: Comment content

    Returns:
        int: ID of the newly created comment

    Raises:
        ValueError: Parameter validation failed
    """
    db_path = params['db_path']
    post_id = params['post_id']
    user_id = params['user_id']
    content = params['content']

    # 1. Configure database connection
    from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
    from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig

    config = SQLiteConnectionConfig(database=db_path)
    User.configure(config, SQLiteBackend)
    Post.__backend__ = User.backend()
    Comment.__backend__ = User.backend()

    comment_id: Optional[int] = None

    try:
        # 2. Execute business logic in transaction
        with Post.transaction():
            post = Post.find_one(post_id)
            if post is None:
                raise ValueError(f"Post {post_id} not found")

            # Validate user
            user = User.find_one(user_id)
            if user is None:
                raise ValueError(f"User {user_id} not found")
            if not user.is_active:
                raise ValueError(f"User {user_id} is not active")

            # Validate post status
            if post.status != 'published':
                raise ValueError(f"Post {post_id} is not published")

            # Create comment
            comment = Comment(
                post_id=post.id,
                user_id=user_id,
                content=content
            )
            comment.save()
            comment_id = comment.id

        # 3. Return result
        return comment_id  # type: ignore

    finally:
        # 4. Cleanup connection
        User.backend().disconnect()
