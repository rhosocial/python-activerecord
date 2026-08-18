# tests/providers/relation.py
"""
This file provides the concrete implementation of the `IRelationProvider` interface
that is defined in the `rhosocial-activerecord-testsuite` package.

Its main responsibilities are:
1.  Reporting which test scenarios (database configurations) are available.
2.  Setting up the database environment for a given test. This includes:
    - Getting the correct database configuration for the scenario.
    - Configuring the ActiveRecord model with a database connection.
    - Dropping any old tables and creating the necessary table schema.
3.  Cleaning up any resources (like temporary database files) after a test runs.
"""
import os
import tempfile
import uuid
from typing import Dict, List, Tuple, Type

from rhosocial.activerecord.model import ActiveRecord, AsyncActiveRecord
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.backend.impl.sqlite.backend.async_backend import AsyncSQLiteBackend
from rhosocial.activerecord.testsuite.feature.relation.interfaces import IRelationSyncProvider, IRelationAsyncProvider
from rhosocial.activerecord.testsuite.feature.relation.fixtures.models import (
    Employee,
    Department,
    Author,
    Book,
    Chapter,
    Profile,
    User,
    Post,
    Comment,
    AsyncUser,
    AsyncPost,
    AsyncComment,
    BoundaryOwner,
    BoundaryProfile,
    BoundaryPost,
    AsyncBoundaryOwner,
    AsyncBoundaryProfile,
    AsyncBoundaryPost,
)
from .scenarios import get_enabled_scenarios, get_scenario


EMPLOYEE_DEPARTMENT_SCHEMA = """
    CREATE TABLE IF NOT EXISTS employees (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT NOT NULL,
        department_id INTEGER NOT NULL,
        FOREIGN KEY (department_id) REFERENCES departments(id)
    );
    CREATE TABLE IF NOT EXISTS departments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT DEFAULT ''
    );
    DELETE FROM employees;
    DELETE FROM departments;
"""

AUTHOR_BOOK_SCHEMA = """
    CREATE TABLE IF NOT EXISTS authors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS books (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        author_id INTEGER NOT NULL,
        FOREIGN KEY (author_id) REFERENCES authors(id)
    );
    CREATE TABLE IF NOT EXISTS chapters (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        book_id INTEGER NOT NULL,
        FOREIGN KEY (book_id) REFERENCES books(id)
    );
    CREATE TABLE IF NOT EXISTS profiles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bio TEXT NOT NULL,
        author_id INTEGER NOT NULL,
        FOREIGN KEY (author_id) REFERENCES authors(id)
    );
    DELETE FROM chapters;
    DELETE FROM books;
    DELETE FROM profiles;
    DELETE FROM authors;
"""

USER_POST_COMMENT_SCHEMA = """
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT,
        settings TEXT
    );
    CREATE TABLE IF NOT EXISTS posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        body TEXT NOT NULL,
        user_id INTEGER NOT NULL,
        view_count INTEGER NOT NULL DEFAULT 0,
        metadata TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id)
    );
    CREATE TABLE IF NOT EXISTS comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        body TEXT NOT NULL,
        post_id INTEGER NOT NULL,
        meta TEXT,
        FOREIGN KEY (post_id) REFERENCES posts(id)
    );
    DELETE FROM comments;
    DELETE FROM posts;
    DELETE FROM users;
"""

RELATION_BOUNDARY_SCHEMA = """
    CREATE TABLE IF NOT EXISTS relation_boundary_owners (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS relation_boundary_profiles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bio TEXT NOT NULL,
        owner_id INTEGER
    );
    CREATE TABLE IF NOT EXISTS relation_boundary_posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        owner_id INTEGER
    );
    DELETE FROM relation_boundary_posts;
    DELETE FROM relation_boundary_profiles;
    DELETE FROM relation_boundary_owners;
"""


class RelationProviderBase:
    """
    SQLite-specific shared helper base for relation feature test providers.
    Contains only non-I/O helper methods shared between sync and async providers.
    """

    def __init__(self):
        # Track the actual database file used for each scenario in the current test run.
        self._scenario_db_files: Dict[str, List[str]] = {}

    def get_test_scenarios(self) -> List[str]:
        return list(get_enabled_scenarios().keys())

    def _make_unique_config(self, scenario_name, original_config):
        if original_config.database != ":memory:":
            from providers.pooling import resolve_database_file, should_keep_database

            unique_filename = resolve_database_file(scenario_name)
            self._scenario_db_files.setdefault(scenario_name, []).append(unique_filename)
            return SQLiteConnectionConfig(
                database=unique_filename,
                delete_on_close=original_config.delete_on_close and not should_keep_database(scenario_name),
                pragmas=original_config.pragmas,
            )
        return original_config


class RelationSyncProvider(RelationProviderBase, IRelationSyncProvider):
    """
    Sync-only SQLite implementation for the relation features test group.
    Connects generic testsuite tests to the actual SQLite database.
    """

    def __init__(self):
        super().__init__()
        # Track active backend instances for proper cleanup.
        # IMPORTANT: SQLite connections hold file locks. If we attempt to delete
        # the database file before disconnecting, the file remains locked and
        # subsequent tests will hang indefinitely waiting for the lock to release.
        self._active_backends = []
        self._sync_user_post_comment_setup = False
        self._sync_relation_boundary_setup = False

    def _setup_employee_department(self, scenario_name):
        """Sets up Employee and Department models for sync tests."""
        backend_class, config = get_scenario(scenario_name)
        config = self._make_unique_config(scenario_name, config)
        Employee.configure(config, backend_class)
        backend = Employee.backend()
        backend.connect()
        backend.introspect_and_adapt()
        self._active_backends.append(backend)
        backend.executescript(EMPLOYEE_DEPARTMENT_SCHEMA)
        Department.configure(config, backend_class)
        return Employee, Department

    def _setup_author_book(self, scenario_name):
        """Sets up Author, Book, Chapter, and Profile models for sync tests."""
        backend_class, config = get_scenario(scenario_name)
        config = self._make_unique_config(scenario_name, config)
        Author.configure(config, backend_class)
        backend = Author.backend()
        backend.connect()
        backend.introspect_and_adapt()
        self._active_backends.append(backend)
        backend.executescript(AUTHOR_BOOK_SCHEMA)
        Book.configure(config, backend_class)
        Chapter.configure(config, backend_class)
        Profile.configure(config, backend_class)
        return Author, Book, Chapter, Profile

    def _setup_user_post_comment_sync(self, scenario_name):
        """Sets up User, Post, and Comment models for sync tests (shared backend, one-time setup)."""
        if not self._sync_user_post_comment_setup:
            backend_class, config = get_scenario(scenario_name)
            config = self._make_unique_config(scenario_name, config)
            User.configure(config, backend_class)
            backend = User.backend()
            backend.connect()
            backend.introspect_and_adapt()
            self._active_backends.append(backend)
            backend.executescript(USER_POST_COMMENT_SCHEMA)
            # Share the same backend instance with Post and Comment
            Post.__connection_config__ = config
            Post.__backend_class__ = backend_class
            Post.__backend__ = backend
            Comment.__connection_config__ = config
            Comment.__backend_class__ = backend_class
            Comment.__backend__ = backend
            self._sync_user_post_comment_setup = True

    def _setup_relation_boundary_sync(self, scenario_name):
        """Sets up BoundaryOwner, BoundaryProfile, and BoundaryPost models for sync boundary tests."""
        if not self._sync_relation_boundary_setup:
            backend_class, config = get_scenario(scenario_name)
            config = self._make_unique_config(scenario_name, config)
            BoundaryOwner.configure(config, backend_class)
            backend = BoundaryOwner.backend()
            backend.connect()
            backend.introspect_and_adapt()
            self._active_backends.append(backend)
            backend.executescript(RELATION_BOUNDARY_SCHEMA)
            # Share the same backend instance with BoundaryProfile and BoundaryPost
            BoundaryProfile.__connection_config__ = config
            BoundaryProfile.__backend_class__ = backend_class
            BoundaryProfile.__backend__ = backend
            BoundaryPost.__connection_config__ = config
            BoundaryPost.__backend_class__ = backend_class
            BoundaryPost.__backend__ = backend
            self._sync_relation_boundary_setup = True

    # --- Implementation of the IRelationSyncProvider interface ---

    def setup_employee_department_fixtures(self, scenario_name: str) -> Tuple[Type[ActiveRecord], Type[ActiveRecord]]:
        """Sets up Employee and Department models for the given scenario."""
        return self._setup_employee_department(scenario_name)

    def setup_author_book_fixtures(
        self, scenario_name: str
    ) -> Tuple[Type[ActiveRecord], Type[ActiveRecord], Type[ActiveRecord], Type[ActiveRecord]]:
        """Sets up Author, Book, Chapter, and Profile models for the given scenario."""
        return self._setup_author_book(scenario_name)

    def setup_user_model(self, scenario_name: str) -> Type[ActiveRecord]:
        """Sets up User model with HasMany posts and HasMany comments."""
        self._setup_user_post_comment_sync(scenario_name)
        return User

    def setup_post_model(self, scenario_name: str) -> Type[ActiveRecord]:
        """Sets up Post model with BelongsTo user."""
        self._setup_user_post_comment_sync(scenario_name)
        return Post

    def setup_comment_model(self, scenario_name: str) -> Type[ActiveRecord]:
        """Sets up Comment model with BelongsTo post."""
        self._setup_user_post_comment_sync(scenario_name)
        return Comment

    def setup_relation_boundary_fixtures(
        self,
        scenario_name: str,
    ) -> Tuple[Type[ActiveRecord], Type[ActiveRecord], Type[ActiveRecord]]:
        """Sets up Owner, Profile, and Post models for relation boundary tests."""
        self._setup_relation_boundary_sync(scenario_name)
        return BoundaryOwner, BoundaryProfile, BoundaryPost

    def load_relation_boundary_dataset(self, scenario_name: str, dataset_name: str) -> Dict[str, int]:
        """Loads a named relation boundary dataset with stable IDs for testing."""
        self._setup_relation_boundary_sync(scenario_name)
        return self._load_relation_boundary_dataset(
            BoundaryOwner,
            BoundaryProfile,
            BoundaryPost,
            dataset_name,
        )

    def _load_relation_boundary_dataset(self, owner_class, profile_class, post_class, dataset_name):
        """Internal helper to load specific relation boundary datasets."""
        if dataset_name == "null_foreign_key":
            profile = profile_class(bio="No owner", owner_id=None)
            profile.save()
            return {"profile_id": profile.id}

        if dataset_name == "orphan_foreign_key":
            missing_owner_id = 999999
            post = post_class(title="Orphan post", owner_id=missing_owner_id)
            post.save()
            return {"post_id": post.id, "missing_owner_id": missing_owner_id}

        if dataset_name == "owner_without_children":
            owner = owner_class(name="Owner without children")
            owner.save()
            return {"owner_id": owner.id}

        if dataset_name == "multiple_has_one_matches":
            owner = owner_class(name="Owner with duplicate profiles")
            owner.save()
            first = profile_class(bio="First profile", owner_id=owner.id)
            first.save()
            second = profile_class(bio="Second profile", owner_id=owner.id)
            second.save()
            return {
                "owner_id": owner.id,
                "first_profile_id": first.id,
                "second_profile_id": second.id,
            }

        raise ValueError(f"Unknown relation boundary dataset: {dataset_name}")

    def cleanup_after_test(self, scenario_name: str) -> None:
        """
        Performs cleanup after a sync test. Disconnects backends and deletes
        temporary database files.

        Backend disconnection MUST happen before file deletion; otherwise the
        SQLite file lock prevents removal on some platforms.
        """
        for backend in self._active_backends:
            try:
                backend.disconnect()
            except Exception:
                pass
        self._active_backends.clear()
        self._sync_user_post_comment_setup = False
        self._sync_relation_boundary_setup = False

        if scenario_name in self._scenario_db_files:
            from providers.pooling import should_keep_database

            if not should_keep_database(scenario_name):
                for db_file in self._scenario_db_files.pop(scenario_name):
                    if db_file and os.path.exists(db_file):
                        try:
                            os.remove(db_file)
                        except OSError:
                            pass
            else:
                self._scenario_db_files.pop(scenario_name, None)


class RelationAsyncProvider(RelationProviderBase, IRelationAsyncProvider):
    """
    Async-only SQLite implementation for the relation features test group.
    Connects generic testsuite async tests to the actual SQLite database.
    """

    def __init__(self):
        super().__init__()
        # Track active async backend instances for proper cleanup.
        # CRITICAL: Without disconnecting async backends, the aiosqlite background
        # thread (a non-daemon threading.Thread in aiosqlite >= 0.20) is never
        # joined and blocks process exit on Python 3.9+.
        self._active_async_backends = []
        self._async_user_post_comment_setup = False
        self._async_relation_boundary_setup = False

    async def _setup_user_post_comment_async(self, scenario_name):
        """Sets up AsyncUser, AsyncPost, and AsyncComment models for async tests (one-time setup)."""
        if not self._async_user_post_comment_setup:
            _, config = get_scenario(scenario_name)
            config = self._make_unique_config(scenario_name, config)

            await AsyncUser.configure(config, AsyncSQLiteBackend)
            backend = AsyncUser.backend()
            await backend.connect()
            await backend.introspect_and_adapt()
            self._active_async_backends.append(backend)
            await backend.executescript(USER_POST_COMMENT_SCHEMA)
            # Share the same backend instance with AsyncPost and AsyncComment
            AsyncPost.__connection_config__ = config
            AsyncPost.__backend_class__ = AsyncSQLiteBackend
            AsyncPost.__backend__ = backend
            AsyncComment.__connection_config__ = config
            AsyncComment.__backend_class__ = AsyncSQLiteBackend
            AsyncComment.__backend__ = backend

            self._async_user_post_comment_setup = True

    async def _setup_relation_boundary_async(self, scenario_name):
        """Sets up AsyncBoundaryOwner, AsyncBoundaryProfile, and AsyncBoundaryPost for async boundary tests."""
        if not self._async_relation_boundary_setup:
            _, config = get_scenario(scenario_name)
            config = self._make_unique_config(scenario_name, config)

            await AsyncBoundaryOwner.configure(config, AsyncSQLiteBackend)
            backend = AsyncBoundaryOwner.backend()
            await backend.connect()
            await backend.introspect_and_adapt()
            self._active_async_backends.append(backend)
            await backend.executescript(RELATION_BOUNDARY_SCHEMA)
            AsyncBoundaryProfile.__connection_config__ = config
            AsyncBoundaryProfile.__backend_class__ = AsyncSQLiteBackend
            AsyncBoundaryProfile.__backend__ = backend
            AsyncBoundaryPost.__connection_config__ = config
            AsyncBoundaryPost.__backend_class__ = AsyncSQLiteBackend
            AsyncBoundaryPost.__backend__ = backend

            self._async_relation_boundary_setup = True

    # --- Implementation of the IRelationAsyncProvider interface ---

    def _setup_employee_department(self, scenario_name):
        """Sets up Employee and Department models for async tests (sync helper, shared with sync provider)."""
        backend_class, config = get_scenario(scenario_name)
        config = self._make_unique_config(scenario_name, config)
        Employee.configure(config, backend_class)
        backend = Employee.backend()
        backend.connect()
        backend.introspect_and_adapt()
        self._active_async_backends.append(backend)
        backend.executescript(EMPLOYEE_DEPARTMENT_SCHEMA)
        Department.configure(config, backend_class)
        return Employee, Department

    def _setup_author_book(self, scenario_name):
        """Sets up Author, Book, Chapter, and Profile models for async tests (sync helper)."""
        backend_class, config = get_scenario(scenario_name)
        config = self._make_unique_config(scenario_name, config)
        Author.configure(config, backend_class)
        backend = Author.backend()
        backend.connect()
        backend.introspect_and_adapt()
        self._active_async_backends.append(backend)
        backend.executescript(AUTHOR_BOOK_SCHEMA)
        Book.configure(config, backend_class)
        Chapter.configure(config, backend_class)
        Profile.configure(config, backend_class)
        return Author, Book, Chapter, Profile

    async def setup_employee_department_fixtures(self, scenario_name: str) -> Tuple[Type[ActiveRecord], Type[ActiveRecord]]:
        """Sets up Employee and Department models for async tests."""
        return self._setup_employee_department(scenario_name)

    async def setup_author_book_fixtures(
        self, scenario_name: str
    ) -> Tuple[Type[ActiveRecord], Type[ActiveRecord], Type[ActiveRecord], Type[ActiveRecord]]:
        """Sets up Author, Book, Chapter, and Profile models for async tests."""
        return self._setup_author_book(scenario_name)

    async def setup_user_model(self, scenario_name: str) -> Type[AsyncActiveRecord]:
        """Sets up AsyncUser model with HasMany posts."""
        await self._setup_user_post_comment_async(scenario_name)
        return AsyncUser

    async def setup_post_model(self, scenario_name: str) -> Type[AsyncActiveRecord]:
        """Sets up AsyncPost model with BelongsTo user."""
        await self._setup_user_post_comment_async(scenario_name)
        return AsyncPost

    async def setup_comment_model(self, scenario_name: str) -> Type[AsyncActiveRecord]:
        """Sets up AsyncComment model with BelongsTo post."""
        await self._setup_user_post_comment_async(scenario_name)
        return AsyncComment

    async def setup_relation_boundary_fixtures(
        self,
        scenario_name: str,
    ) -> Tuple[Type[AsyncActiveRecord], Type[AsyncActiveRecord], Type[AsyncActiveRecord]]:
        """Sets up Owner, Profile, and Post models for async relation boundary tests."""
        await self._setup_relation_boundary_async(scenario_name)
        return AsyncBoundaryOwner, AsyncBoundaryProfile, AsyncBoundaryPost

    async def load_relation_boundary_dataset(
        self,
        scenario_name: str,
        dataset_name: str,
    ) -> Dict[str, int]:
        """Loads a named async relation boundary dataset with stable IDs for testing."""
        await self._setup_relation_boundary_async(scenario_name)
        return await self._load_relation_boundary_dataset(dataset_name)

    async def _load_relation_boundary_dataset(self, dataset_name):
        if dataset_name == "null_foreign_key":
            profile = AsyncBoundaryProfile(bio="No owner", owner_id=None)
            await profile.save()
            return {"profile_id": profile.id}

        if dataset_name == "orphan_foreign_key":
            missing_owner_id = 999999
            post = AsyncBoundaryPost(title="Orphan post", owner_id=missing_owner_id)
            await post.save()
            return {"post_id": post.id, "missing_owner_id": missing_owner_id}

        if dataset_name == "owner_without_children":
            owner = AsyncBoundaryOwner(name="Owner without children")
            await owner.save()
            return {"owner_id": owner.id}

        if dataset_name == "multiple_has_one_matches":
            owner = AsyncBoundaryOwner(name="Owner with duplicate profiles")
            await owner.save()
            first = AsyncBoundaryProfile(bio="First profile", owner_id=owner.id)
            await first.save()
            second = AsyncBoundaryProfile(bio="Second profile", owner_id=owner.id)
            await second.save()
            return {
                "owner_id": owner.id,
                "first_profile_id": first.id,
                "second_profile_id": second.id,
            }

        raise ValueError(f"Unknown relation boundary dataset: {dataset_name}")

    async def cleanup_after_test(self, scenario_name: str) -> None:
        """
        Performs cleanup after an async test. Disconnects backends and deletes
        temporary database files.

        CRITICAL: Backend disconnection MUST happen before file deletion.
        Without disconnecting, the aiosqlite background thread (a non-daemon
        threading.Thread) keeps running and prevents the process from exiting
        on Python 3.9+.
        """
        for backend in self._active_async_backends:
            try:
                await backend.disconnect()
            except Exception:
                pass
        self._active_async_backends.clear()
        self._async_user_post_comment_setup = False
        self._async_relation_boundary_setup = False

        if scenario_name in self._scenario_db_files:
            from providers.pooling import should_keep_database

            if not should_keep_database(scenario_name):
                for db_file in self._scenario_db_files.pop(scenario_name):
                    if db_file and os.path.exists(db_file):
                        try:
                            os.remove(db_file)
                        except OSError:
                            pass
            else:
                self._scenario_db_files.pop(scenario_name, None)
