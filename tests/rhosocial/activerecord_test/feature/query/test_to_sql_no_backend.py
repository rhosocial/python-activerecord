# tests/rhosocial/activerecord_test/feature/query/test_to_sql_no_backend.py
import pytest
from pydantic import Field
from typing import ClassVar, Optional, List

from rhosocial.activerecord.backend.expression import CaseExpression, Column
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.relation import HasMany, BelongsTo

from rhosocial.activerecord.backend.base import StorageBackend


class UserModel(ActiveRecord):
    __table_name__: ClassVar[str] = "users"
    id: Optional[int] = Field(default=None, json_schema_extra={'primary_key': True})
    name: str
    email: str

    posts: ClassVar[HasMany['PostModel']] = HasMany(foreign_key='user_id', inverse_of='user')
    comments: ClassVar[HasMany['CommentModel']] = HasMany(foreign_key='user_id', inverse_of='user')


class PostModel(ActiveRecord):
    __table_name__: ClassVar[str] = "posts"
    id: Optional[int] = Field(default=None, json_schema_extra={'primary_key': True})
    user_id: int = Field(json_schema_extra={'foreign_key': "users.id"})
    title: str

    user: ClassVar[BelongsTo['UserModel']] = BelongsTo(foreign_key='user_id', inverse_of='posts')
    comments: ClassVar[HasMany['CommentModel']] = HasMany(foreign_key='post_id', inverse_of='post')


class CommentModel(ActiveRecord):
    __table_name__: ClassVar[str] = "comments"
    id: Optional[int] = Field(default=None, json_schema_extra={'primary_key': True})
    user_id: int
    post_id: int = Field(json_schema_extra={'foreign_key': "posts.id"})
    content: str

    user: ClassVar[BelongsTo['UserModel']] = BelongsTo(foreign_key='user_id', inverse_of='comments')
    post: ClassVar[BelongsTo['PostModel']] = BelongsTo(foreign_key='post_id', inverse_of='comments')


@pytest.fixture
def unconfigured_models():
    """Provides models that have no backend configured."""
    models = [UserModel, PostModel, CommentModel]
    for model in models:
        # Ensure no backend is configured before each test
        model.__backend__ = None
        model.__backend_class__ = None
        model.__connection_config__ = None
        model.model_rebuild()
    yield UserModel, PostModel, CommentModel
    # Clean up after test
    for model in models:
        model.__backend__ = None
        model.__backend_class__ = None
        model.__connection_config__ = None
        try:
            delattr(model, '_dummy_backend')
        except AttributeError:
            pass


def test_to_sql_with_dummy_backend(unconfigured_models):
    """
    Test that to_sql() works correctly even when no real backend is configured,
    falling back to DummyBackend.
    """
    User, _, _ = unconfigured_models

    # Verify that the backend is indeed DummyBackend
    backend_instance = User.backend()
    assert isinstance(backend_instance, StorageBackend)
    from rhosocial.activerecord.backend.impl.dummy.backend import DummyBackend
    assert isinstance(backend_instance, DummyBackend)

    # Build a query
    query_builder = User.query().query({'name': 'Alice'}).limit(5).offset(10).order_by("id DESC")
    sql, params = query_builder.to_sql()

    # Expected SQL from DummyDialect (uses double quotes for identifiers, ? for placeholders)
    expected_sql = 'SELECT * FROM "users" WHERE name = ? ORDER BY "id" DESC LIMIT ? OFFSET ?'
    expected_params = ("Alice", 5, 10)

    assert sql == expected_sql
    assert params == expected_params

    # Test another query with multiple conditions
    query_builder_2 = User.query().query({'name__like': '%Bob%'}).where('email = ?', ("bob@example.com",))
    sql_2, params_2 = query_builder_2.to_sql()
    expected_sql_2 = (
        'SELECT * FROM "users" WHERE name LIKE ? AND email = ?'
    )
    expected_params_2 = ("%Bob%", "bob@example.com")
    assert sql_2 == expected_sql_2
    assert params_2 == expected_params_2


def test_to_sql_with_manual_joins(unconfigured_models):
    """Test `to_sql` for queries with manually specified JOIN clauses."""
    User, Post, _ = unconfigured_models
    sql, params = User.query().select(
        "users.name", "posts.title"
    ).inner_join(
        'posts', 'posts.user_id', 'users.id'
    ).where("users.id = ?", (1,)).to_sql()

    expected_sql = 'SELECT "users"."name", "posts"."title" FROM "users" INNER JOIN "posts" ON "posts"."user_id" = "users"."id" WHERE users.id = ?'
    expected_params = (1,)
    assert sql == expected_sql
    assert params == expected_params


def test_to_sql_with_relation_joins(unconfigured_models):
    """Test `to_sql` for queries with JOINs based on model relationships."""
    User, Post, _ = unconfigured_models
    sql, params = User.query().join(Post).to_sql()
    expected_sql = 'SELECT * FROM "users" INNER JOIN "posts" ON "posts"."user_id" = "users"."id"'
    expected_params = ()
    assert sql == expected_sql
    assert params == expected_params

    sql, params = Post.query().join(User).to_sql()
    expected_sql = 'SELECT * FROM "posts" INNER JOIN "users" ON "posts"."user_id" = "users"."id"'
    assert sql == expected_sql
    assert params == expected_params

def test_to_sql_with_aggregate(unconfigured_models):
    """Test `to_sql` for queries with aggregate functions."""
    User, _, _ = unconfigured_models
    sql, params = User.query().select("COUNT(*) as user_count").to_sql()
    expected_sql = 'SELECT COUNT(*) as user_count FROM "users"'
    assert sql == expected_sql
    assert params == ()

    sql, params = User.query().select("name", "COUNT(id) as c").group_by("name").to_sql()
    expected_sql = 'SELECT name, COUNT(id) as c FROM "users" GROUP BY "name"'
    assert sql == expected_sql
    assert params == ()


def test_to_sql_with_cte(unconfigured_models):
    """Test `to_sql` for queries with Common Table Expressions (CTE)."""
    User, _, _ = unconfigured_models
    high_id_users_query = User.query().select("id", "name").where("id > ?", (10,))
    sql, params = User.query().with_cte("high_id_users", high_id_users_query).select("*").from_cte("high_id_users").to_sql()

    expected_sql = 'WITH high_id_users AS (SELECT "id", "name" FROM "users" WHERE id > ?) SELECT * FROM high_id_users'
    expected_params = (10,)
    assert sql == expected_sql
    assert params == expected_params


def test_to_sql_with_case_expression(unconfigured_models):
    """Test `to_sql` for queries with CASE expressions."""
    User, _, _ = unconfigured_models

    query = User.query().select('name').case(
        [("name = 'Alice'", "is_alice")],
        else_result="not_alice",
        alias="status"
    )
    sql, params = query.to_sql()

    # Note: The current CaseExpression implementation formats results as string literals
    expected_sql = "SELECT name, CASE WHEN name = 'Alice' THEN 'is_alice' ELSE 'not_alice' END as status FROM \"users\""
    expected_params = ()

    assert sql == expected_sql
    assert params == expected_params

def test_sync_execution_fails_with_dummy_backend(unconfigured_models):
    """
    Test that synchronous execution methods on an unconfigured model
    raise NotImplementedError when using DummyBackend.
    """
    User, _, _ = unconfigured_models

    # Attempt to execute a query that requires database interaction
    with pytest.raises(NotImplementedError) as excinfo:
        User.query().one()
    assert "DummyBackend does not support real database operations. Did you forget to configure a concrete backend?" in str(excinfo.value)

    with pytest.raises(NotImplementedError) as excinfo:
        User.query().all()
    assert "DummyBackend does not support real database operations. Did you forget to configure a concrete backend?" in str(excinfo.value)


def test_to_sql_with_eager_loading(unconfigured_models):
    """
    Test that `with_()` for eager loading does not affect the main SQL query.
    """
    User, Post, _ = unconfigured_models

    # Test with a simple relationship
    sql, params = User.query().with_('posts').to_sql()
    assert sql == 'SELECT * FROM "users"'
    assert params == ()

    # Test with a nested relationship
    sql, params = User.query().with_('posts.comments').to_sql()
    assert sql == 'SELECT * FROM "users"'
    assert params == ()

    # Test with multiple relationships
    sql, params = Post.query().with_('user', 'comments').to_sql()
    assert sql == 'SELECT * FROM "posts"'
    assert params == ()


@pytest.mark.asyncio
async def test_async_execution_fails_with_dummy_backend(unconfigured_models):
    """
    Test that asynchronous execution methods on an unconfigured model
    raise NotImplementedError when using DummyBackend.
    """
    User, _, _ = unconfigured_models

    # Attempt to execute an async query (should implicitly call an async method on backend)
    # Since DummyBackend has sync methods, awaiting them will cause TypeError
    with pytest.raises(NotImplementedError) as excinfo:
        await User.query().one() # This will try to await a sync backend.one() which does not exist

    # The error message might vary slightly depending on how pytest-asyncio and Python handle it,
    assert "DummyBackend does not support real database operations. Did you forget to configure a concrete backend?" in str(excinfo.value)


# TODO: Add comprehensive async ActiveRecord/ActiveQuery tests with AsyncDummyBackend once async support is implemented in ActiveRecord.
# This would include tests for:
# - async_backend() method returning AsyncDummyBackend when no backend configured
# - AsyncDummyBackend working properly with async query methods like async query().one(), query().all(), etc.
# - async save() and async delete() methods (when implemented)
# - async transaction support with async context managers


