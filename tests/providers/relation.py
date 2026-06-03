# tests/providers/relation.py
import asyncio
from typing import Dict, List, Tuple, Type

from rhosocial.activerecord.model import ActiveRecord, AsyncActiveRecord
from rhosocial.activerecord.backend.impl.sqlite.backend.async_backend import AsyncSQLiteBackend
from rhosocial.activerecord.testsuite.feature.relation.interfaces import IRelationProvider
from rhosocial.activerecord.testsuite.feature.relation.fixtures.models import (
    Employee, Department, Author, Book, Chapter, Profile,
    User, Post, Comment,
    AsyncUser, AsyncPost, AsyncComment,
    BoundaryOwner, BoundaryProfile, BoundaryPost,
    AsyncBoundaryOwner, AsyncBoundaryProfile, AsyncBoundaryPost,
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


class RelationProvider(IRelationProvider):

    def __init__(self):
        self._active_backends = []
        self._active_async_backends = []
        self._sync_user_post_comment_setup = False
        self._async_user_post_comment_setup = False
        self._sync_relation_boundary_setup = False
        self._async_relation_boundary_setup = False

    def get_test_scenarios(self) -> List[str]:
        return list(get_enabled_scenarios().keys())

    def _setup_employee_department(self, scenario_name):
        backend_class, config = get_scenario(scenario_name)
        Employee.configure(config, backend_class)
        backend = Employee.backend()
        backend.connect()
        backend.introspect_and_adapt()
        self._active_backends.append(backend)
        backend.executescript(EMPLOYEE_DEPARTMENT_SCHEMA)
        Department.configure(config, backend_class)
        return Employee, Department

    def _setup_author_book(self, scenario_name):
        backend_class, config = get_scenario(scenario_name)
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
        if not self._sync_user_post_comment_setup:
            backend_class, config = get_scenario(scenario_name)
            User.configure(config, backend_class)
            backend = User.backend()
            backend.connect()
            backend.introspect_and_adapt()
            self._active_backends.append(backend)
            backend.executescript(USER_POST_COMMENT_SCHEMA)
            Post.configure(config, backend_class)
            Comment.configure(config, backend_class)
            self._sync_user_post_comment_setup = True

    def _setup_user_post_comment_async(self, scenario_name):
        if not self._async_user_post_comment_setup:
            _, config = get_scenario(scenario_name)

            async def _setup():
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

            asyncio.run(_setup())
            self._async_user_post_comment_setup = True

    def _setup_relation_boundary_sync(self, scenario_name):
        if not self._sync_relation_boundary_setup:
            backend_class, config = get_scenario(scenario_name)
            BoundaryOwner.configure(config, backend_class)
            backend = BoundaryOwner.backend()
            backend.connect()
            backend.introspect_and_adapt()
            self._active_backends.append(backend)
            backend.executescript(RELATION_BOUNDARY_SCHEMA)
            BoundaryProfile.configure(config, backend_class)
            BoundaryPost.configure(config, backend_class)
            self._sync_relation_boundary_setup = True

    def _setup_relation_boundary_async(self, scenario_name):
        if not self._async_relation_boundary_setup:
            _, config = get_scenario(scenario_name)

            async def _setup():
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

            asyncio.run(_setup())
            self._async_relation_boundary_setup = True

    def setup_employee_department_fixtures(self, scenario_name: str) -> Tuple[Type[ActiveRecord], Type[ActiveRecord]]:
        return self._setup_employee_department(scenario_name)

    def setup_author_book_fixtures(self, scenario_name: str) -> Tuple[Type[ActiveRecord], Type[ActiveRecord], Type[ActiveRecord], Type[ActiveRecord]]:
        return self._setup_author_book(scenario_name)

    def setup_user_model(self, scenario_name: str) -> Type[ActiveRecord]:
        self._setup_user_post_comment_sync(scenario_name)
        return User

    def setup_post_model(self, scenario_name: str) -> Type[ActiveRecord]:
        self._setup_user_post_comment_sync(scenario_name)
        return Post

    def setup_comment_model(self, scenario_name: str) -> Type[ActiveRecord]:
        self._setup_user_post_comment_sync(scenario_name)
        return Comment

    def setup_async_user_model(self, scenario_name: str) -> Type[AsyncActiveRecord]:
        self._setup_user_post_comment_async(scenario_name)
        return AsyncUser

    def setup_async_post_model(self, scenario_name: str) -> Type[AsyncActiveRecord]:
        self._setup_user_post_comment_async(scenario_name)
        return AsyncPost

    def setup_async_comment_model(self, scenario_name: str) -> Type[AsyncActiveRecord]:
        self._setup_user_post_comment_async(scenario_name)
        return AsyncComment

    def setup_relation_boundary_fixtures(
        self,
        scenario_name: str,
    ) -> Tuple[Type[ActiveRecord], Type[ActiveRecord], Type[ActiveRecord]]:
        self._setup_relation_boundary_sync(scenario_name)
        return BoundaryOwner, BoundaryProfile, BoundaryPost

    def setup_async_relation_boundary_fixtures(
        self,
        scenario_name: str,
    ) -> Tuple[Type[AsyncActiveRecord], Type[AsyncActiveRecord], Type[AsyncActiveRecord]]:
        self._setup_relation_boundary_async(scenario_name)
        return AsyncBoundaryOwner, AsyncBoundaryProfile, AsyncBoundaryPost

    def load_relation_boundary_dataset(self, scenario_name: str, dataset_name: str) -> Dict[str, int]:
        self._setup_relation_boundary_sync(scenario_name)
        return self._load_relation_boundary_dataset(
            BoundaryOwner,
            BoundaryProfile,
            BoundaryPost,
            dataset_name,
        )

    async def load_async_relation_boundary_dataset(
        self,
        scenario_name: str,
        dataset_name: str,
    ) -> Dict[str, int]:
        self._setup_relation_boundary_async(scenario_name)
        return await self._load_async_relation_boundary_dataset(dataset_name)

    def _load_relation_boundary_dataset(self, owner_class, profile_class, post_class, dataset_name):
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

    async def _load_async_relation_boundary_dataset(self, dataset_name):
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

    def cleanup_after_test(self, scenario_name: str) -> None:
        for backend in self._active_backends:
            try:
                backend.disconnect()
            except Exception:
                pass
        self._active_backends.clear()
        for backend in self._active_async_backends:
            try:
                asyncio.run(backend.disconnect())
            except Exception:
                pass
        self._active_async_backends.clear()
        self._sync_user_post_comment_setup = False
        self._async_user_post_comment_setup = False
        self._sync_relation_boundary_setup = False
        self._async_relation_boundary_setup = False
