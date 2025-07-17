# tests/rhosocial/activerecord_test/fixtures/community/models.py
from typing import Optional

import pytest

from src.activerecord.base import ActiveRecord
from src.activerecord.fields import TimestampMixin, SoftDeleteMixin

@pytest.fixture
def community_models(storage_backend):
    """用户社区相关模型夹具"""

    class User(TimestampMixin, ActiveRecord):
        """用户模型"""
        id: Optional[int]
        username: str
        email: str
        password_hash: str
        bio: Optional[str]
        avatar_url: Optional[str]
        status: str = 'active'  # active/disabled

        __table_name__ = 'users'

    class Article(TimestampMixin, SoftDeleteMixin, ActiveRecord):
        """文章模型"""
        id: Optional[int]
        user_id: int
        title: str
        content: str
        status: str = 'draft'  # draft/published/archived
        view_count: int = 0

        __table_name__ = 'articles'

    class Comment(TimestampMixin, ActiveRecord):
        """评论模型"""
        id: Optional[int]
        article_id: int
        user_id: int
        content: str
        status: str = 'normal'  # normal/hidden

        __table_name__ = 'comments'

    class Friendship(TimestampMixin, ActiveRecord):
        """好友关系模型"""
        id: Optional[int]
        user_id: int
        friend_id: int
        status: str = 'pending'  # pending/accepted/rejected/blocked

        __table_name__ = 'friendships'

    # 设置后端
    for model in [User, Article, Comment, Friendship]:
        model.set_backend(storage_backend)

    # 创建表结构
    storage_backend.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            bio TEXT,
            avatar_url TEXT,
            status TEXT NOT NULL DEFAULT 'active',
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL
        )
    """)

    storage_backend.execute("""
        CREATE TABLE articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'draft',
            view_count INTEGER NOT NULL DEFAULT 0,
            deleted_at DATETIME,
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    storage_backend.execute("""
        CREATE TABLE comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            article_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            content TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'normal',
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL,
            FOREIGN KEY (article_id) REFERENCES articles(id),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    storage_backend.execute("""
        CREATE TABLE friendships (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            friend_id INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at DATETIME NOT NULL,
            updated_at DATETIME NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id),
            FOREIGN KEY (friend_id) REFERENCES users(id),
            UNIQUE (user_id, friend_id)
        )
    """)

    yield {
        'User': User,
        'Article': Article,
        'Comment': Comment,
        'Friendship': Friendship
    }

    # 清理表
    for table in ['friendships', 'comments', 'articles', 'users']:
        storage_backend.execute(f"DROP TABLE {table}")