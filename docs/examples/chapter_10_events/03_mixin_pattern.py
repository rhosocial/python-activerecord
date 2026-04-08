"""
Events Chapter: Example 3 - Mixin Pattern for Events
Demonstrates core concepts:
1. Creating reusable event logic via Mixins
2. Combining multiple Mixins
3. Real-world Mixin examples (Timestamp, SoftDelete, Audit)
"""

from datetime import datetime, timezone
from typing import Optional, ClassVar
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.interface.base import ModelEvent
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend, SQLiteConnectionConfig
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType

# --- Reusable Mixins ---

class TimestampMixin:
    """Mixin that automatically manages created_at and updated_at timestamps.

    Uses separate events for INSERT and UPDATE operations:
    - BEFORE_INSERT: Sets both created_at and updated_at for new records
    - BEFORE_UPDATE: Updates only updated_at for existing records
    """

    def __init__(self, **data):
        super().__init__(**data)
        self.on(ModelEvent.BEFORE_INSERT, self._set_timestamps_on_insert)
        self.on(ModelEvent.BEFORE_UPDATE, self._set_updated_at)

    def _set_timestamps_on_insert(self, instance, data, **kwargs):
        """Set both created_at and updated_at for INSERT operations."""
        now = datetime.now(timezone.utc)
        if hasattr(self, 'created_at'):
            self.created_at = now
            data['created_at'] = now
        if hasattr(self, 'updated_at'):
            self.updated_at = now
            data['updated_at'] = now

    def _set_updated_at(self, instance, data, **kwargs):
        """Set updated_at for UPDATE operations."""
        if hasattr(self, 'updated_at'):
            now = datetime.now(timezone.utc)
            self.updated_at = now
            data['updated_at'] = now


class SoftDeleteMixin:
    """Mixin that implements soft delete functionality."""

    def __init__(self, **data):
        super().__init__(**data)
        self.on(ModelEvent.BEFORE_DELETE, self._soft_delete)

    def _soft_delete(self, instance, **kwargs):
        """Prevent actual deletion, set deleted_at instead."""
        if hasattr(self, 'deleted_at'):
            self.deleted_at = datetime.now(timezone.utc)
            # Cancel the actual delete by raising an exception
            # or override delete() method
            print(f"  [SoftDelete] Marking '{self}' as deleted")
            # In real implementation, you would:
            # 1. Set deleted_at
            # 2. Save the record
            # 3. Prevent the actual delete


class AuditMixin:
    """Mixin that logs all changes for audit purposes.

    Uses separate events for INSERT and UPDATE to provide
    more specific audit information.
    """

    _audit_log: ClassVar[list] = []

    def __init__(self, **data):
        super().__init__(**data)
        self.on(ModelEvent.AFTER_INSERT, self._log_insert)
        self.on(ModelEvent.AFTER_UPDATE, self._log_update)
        self.on(ModelEvent.AFTER_DELETE, self._log_delete)

    def _log_insert(self, instance, data, result, **kwargs):
        """Log INSERT operations."""
        AuditMixin._audit_log.append({
            'action': 'CREATE',
            'model': self.__class__.__name__,
            'id': self.id,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        print(f"  [Audit] CREATE: {self.__class__.__name__}#{self.id}")

    def _log_update(self, instance, data, dirty_fields, result, **kwargs):
        """Log UPDATE operations."""
        AuditMixin._audit_log.append({
            'action': 'UPDATE',
            'model': self.__class__.__name__,
            'id': self.id,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        print(f"  [Audit] UPDATE: {self.__class__.__name__}#{self.id}")

    def _log_delete(self, instance, result, **kwargs):
        """Log DELETE operations."""
        AuditMixin._audit_log.append({
            'action': 'DELETE',
            'model': self.__class__.__name__,
            'id': self.id,
            'timestamp': datetime.now(timezone.utc).isoformat()
        })
        print(f"  [Audit] DELETE: {self.__class__.__name__}#{self.id}")

    @classmethod
    def get_audit_log(cls):
        return cls._audit_log


class CacheInvalidationMixin:
    """Mixin that handles cache invalidation on save/delete."""

    def __init__(self, **data):
        super().__init__(**data)
        self.on(ModelEvent.AFTER_INSERT, self._invalidate_cache)
        self.on(ModelEvent.AFTER_UPDATE, self._invalidate_cache)
        self.on(ModelEvent.AFTER_DELETE, self._invalidate_cache)

    def _invalidate_cache(self, instance, **kwargs):
        """Invalidate related caches."""
        cache_key = f"{self.__class__.__name__}:{self.id}"
        print(f"  [Cache] Invalidating cache key: {cache_key}")
        # In real implementation: redis.delete(cache_key), etc.

# --- Models using Mixins ---

class User(TimestampMixin, AuditMixin, ActiveRecord):
    """User model with timestamp and audit support."""
    __table_name__ = "users"
    id: Optional[int] = None
    username: str
    email: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class Article(TimestampMixin, CacheInvalidationMixin, ActiveRecord):
    """Article model with timestamp and cache invalidation."""
    __table_name__ = "articles"
    id: Optional[int] = None
    title: str
    content: str
    author_id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

# --- Main Execution ---

def main():
    print("=" * 60)
    print("Example 3: Mixin Pattern for Events")
    print("=" * 60)

    # Configure database
    config = SQLiteConnectionConfig(database=':memory:')
    User.configure(config, SQLiteBackend)

    # Create tables
    backend = User.backend()
    backend.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username VARCHAR(50),
            email VARCHAR(100),
            created_at TIMESTAMP,
            updated_at TIMESTAMP
        )
    """, options=ExecutionOptions(stmt_type=StatementType.DDL))

    # 1. TimestampMixin demonstration
    print("\n" + "-" * 40)
    print("TimestampMixin - Automatic timestamps:")
    print("-" * 40)
    user = User(username="alice", email="alice@example.com")
    user.save()
    print(f"  created_at: {user.created_at}")
    print(f"  updated_at: {user.updated_at}")

    print("\nUpdating user:")
    user.email = "alice.new@example.com"
    user.save()
    print(f"  updated_at changed: {user.updated_at}")

    # 2. Multiple Mixins working together
    print("\n" + "-" * 40)
    print("Multiple Mixins (Timestamp + Audit):")
    print("-" * 40)

    user2 = User(username="bob", email="bob@example.com")
    user2.save()

    user3 = User(username="charlie", email="charlie@example.com")
    user3.save()

    # 3. CacheInvalidationMixin
    print("\n" + "-" * 40)
    print("CacheInvalidationMixin:")
    print("-" * 40)

    Article.configure(config, SQLiteBackend)
    # Create table using Article's backend
    article_backend = Article.backend()
    article_backend.execute("""
        CREATE TABLE articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title VARCHAR(200),
            content TEXT,
            author_id INTEGER,
            created_at TIMESTAMP,
            updated_at TIMESTAMP
        )
    """, options=ExecutionOptions(stmt_type=StatementType.DDL))

    article = Article(title="Hello World", content="My first article", author_id=1)
    article.save()

    article.content = "Updated content"
    article.save()

    # 4. View audit log
    print("\n" + "-" * 40)
    print("Audit Log (all recorded actions):")
    print("-" * 40)
    for entry in AuditMixin.get_audit_log():
        print(f"  {entry['timestamp']}: {entry['action']} {entry['model']}#{entry['id']}")

if __name__ == "__main__":
    main()
