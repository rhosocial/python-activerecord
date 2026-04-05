# tests/providers/query.py
"""
This file provides the concrete implementation of the `IQueryProvider` interface
that is defined in the `rhosocial-activerecord-testsuite` package.

Its main responsibilities are:
1.  Reporting which test scenarios (database configurations) are available.
2.  Setting up the database environment for a given test. This includes:
    - Getting the correct database configuration for the scenario.
    - Configuring the ActiveRecord model with a database connection.
    - Dropping any old tables and creating the necessary table schema.
3.  Cleaning up any resources (like temporary database files) after a test runs.
"""
import asyncio

import os
import sys
import time
import uuid
import tempfile
import logging
from typing import Type, List, Tuple

from rhosocial.activerecord.model import ActiveRecord, AsyncActiveRecord

# Setup logging for fixture selection debugging
logger = logging.getLogger(__name__)

# Import the fixture selector utility
from rhosocial.activerecord.testsuite.utils import select_fixture

# Import base version models (Python 3.8+)
from rhosocial.activerecord.testsuite.feature.query.fixtures.models import (
    User as UserBase, JsonUser as JsonUserBase,
    Order as OrderBase, OrderItem as OrderItemBase,
    Post as PostBase, Comment as CommentBase,
    MappedUser as MappedUserBase, MappedPost as MappedPostBase, MappedComment as MappedCommentBase
)

# Conditionally import Python 3.10+ models
User310 = JsonUser310 = Order310 = OrderItem310 = Post310 = Comment310 = None
MappedUser310 = MappedPost310 = MappedComment310 = None

if sys.version_info >= (3, 10):
    try:
        from rhosocial.activerecord.testsuite.feature.query.fixtures.models_py310 import (
            User as User310, JsonUser as JsonUser310,
            Order as Order310, OrderItem as OrderItem310,
            Post as Post310, Comment as Comment310,
            MappedUser as MappedUser310, MappedPost as MappedPost310, MappedComment as MappedComment310
        )
    except ImportError as e:
        logger.warning(f"Failed to import Python 3.10+ fixtures: {e}")

# Conditionally import Python 3.11+ models
User311 = JsonUser311 = Order311 = OrderItem311 = Post311 = Comment311 = None
MappedUser311 = MappedPost311 = MappedComment311 = None

if sys.version_info >= (3, 11):
    try:
        from rhosocial.activerecord.testsuite.feature.query.fixtures.models_py311 import (
            User as User311, JsonUser as JsonUser311,
            Order as Order311, OrderItem as OrderItem311,
            Post as Post311, Comment as Comment311,
            MappedUser as MappedUser311, MappedPost as MappedPost311, MappedComment as MappedComment311
        )
    except ImportError as e:
        logger.warning(f"Failed to import Python 3.11+ fixtures: {e}")

# Conditionally import Python 3.12+ models
User312 = JsonUser312 = Order312 = OrderItem312 = Post312 = Comment312 = None
MappedUser312 = MappedPost312 = MappedComment312 = None

if sys.version_info >= (3, 12):
    try:
        from rhosocial.activerecord.testsuite.feature.query.fixtures.models_py312 import (
            User as User312, JsonUser as JsonUser312,
            Order as Order312, OrderItem as OrderItem312,
            Post as Post312, Comment as Comment312,
            MappedUser as MappedUser312, MappedPost as MappedPost312, MappedComment as MappedComment312
        )
    except ImportError as e:
        logger.warning(f"Failed to import Python 3.12+ fixtures: {e}")


# Select appropriate fixture classes based on Python version
def _select_model_class(base_cls, py312_cls, py311_cls, py310_cls, model_name: str) -> Type:
    """Select the most appropriate model class for the current Python version."""
    candidates = [c for c in [py312_cls, py311_cls, py310_cls, base_cls] if c is not None]
    selected = select_fixture(*candidates)
    logger.info(f"Selected {model_name}: {selected.__name__} from {selected.__module__}")
    return selected


# Select sync models
User = _select_model_class(UserBase, User312, User311, User310, "User")
JsonUser = _select_model_class(JsonUserBase, JsonUser312, JsonUser311, JsonUser310, "JsonUser")
Order = _select_model_class(OrderBase, Order312, Order311, Order310, "Order")
OrderItem = _select_model_class(OrderItemBase, OrderItem312, OrderItem311, OrderItem310, "OrderItem")
Post = _select_model_class(PostBase, Post312, Post311, Post310, "Post")
Comment = _select_model_class(CommentBase, Comment312, Comment311, Comment310, "Comment")
MappedUser = _select_model_class(MappedUserBase, MappedUser312, MappedUser311, MappedUser310, "MappedUser")
MappedPost = _select_model_class(MappedPostBase, MappedPost312, MappedPost311, MappedPost310, "MappedPost")
MappedComment = _select_model_class(MappedCommentBase, MappedComment312, MappedComment311, MappedComment310, "MappedComment")

from rhosocial.activerecord.testsuite.feature.query.interfaces import IQueryProvider
from rhosocial.activerecord.testsuite.core.protocols import WorkerTestProtocol
# Scenarios are defined specifically for this backend.
from .scenarios import get_enabled_scenarios, get_scenario


class QueryProvider(IQueryProvider, WorkerTestProtocol):
    """
    This is the SQLite backend's implementation for the query features test group.
    It connects the generic tests in the testsuite with the actual SQLite database.
    """

    def __init__(self):
        # Track the actual database file used for each scenario in the current test run.
        self._scenario_db_files = {}
        # Track active backend instances for proper cleanup.
        # IMPORTANT: SQLite connections hold file locks. If we attempt to delete
        # the database file before disconnecting, the file remains locked and
        # subsequent tests will hang indefinitely waiting for the lock to release.
        # This was discovered during WorkerPool tests where cleanup would hang
        # on Windows and some Linux configurations.
        # See: python-activerecord-mysql/docs/zh_CN/scenarios/parallel_workers.md
        # See: python-activerecord-postgres/docs/zh_CN/scenarios/parallel_workers.md
        self._active_backends = []
        self._active_async_backends = []

    def get_test_scenarios(self) -> List[str]:
        """Returns a list of names for all enabled scenarios for this backend."""
        return list(get_enabled_scenarios().keys())

    # --- Synchronous Implementation ---

    def _setup_model(self, model_class: Type[ActiveRecord], scenario_name: str, table_name: str, shared_backend=None) -> Type[ActiveRecord]:
        """A generic helper method to handle the setup for any given synchronous model."""
        backend_class, original_config = get_scenario(scenario_name)
        config = original_config

        if original_config.database != ":memory:":
            unique_filename = os.path.join(
                tempfile.gettempdir(),
                f"test_activerecord_{scenario_name}_sync_{uuid.uuid4().hex}.sqlite"
            )
            self._scenario_db_files.setdefault(scenario_name, []).append(unique_filename)
            from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
            config = SQLiteConnectionConfig(
                database=unique_filename,
                delete_on_close=original_config.delete_on_close,
                pragmas=original_config.pragmas
            )

        if shared_backend is None:
            model_class.configure(config, backend_class)
            # Track the backend instance for cleanup
            if model_class.__backend__ not in self._active_backends:
                self._active_backends.append(model_class.__backend__)
        else:
            model_class.__connection_config__ = config
            model_class.__backend_class__ = backend_class
            model_class.__backend__ = shared_backend

        # Monkey-patch for Windows timestamp resolution issues
        if os.name == 'nt' and not hasattr(model_class, '_save_patched_sync'):
            original_save = model_class.save
            def delayed_save(self, *args, **kwargs):
                result = original_save(self, *args, **kwargs)
                time.sleep(0.001)
                return result
            model_class.save = delayed_save
            setattr(model_class, '_save_patched_sync', True)

        # Prepare schema
        from rhosocial.activerecord.backend.options import ExecutionOptions
        from rhosocial.activerecord.backend.schema import StatementType
        options = ExecutionOptions(stmt_type=StatementType.DDL)
        model_class.__backend__.execute(f"DROP TABLE IF EXISTS {table_name}", options=options)
        schema_sql = self._load_sqlite_schema(f"{table_name}.sql")
        model_class.__backend__.execute(schema_sql, options=options)

        return model_class

    def _setup_multiple_models(self, models_and_tables, scenario_name: str) -> Tuple[Type[ActiveRecord], ...]:
        """A helper to set up multiple synchronous models for fixture groups."""
        result = []
        shared_backend = None
        for i, (model_class, table_name) in enumerate(models_and_tables):
            if i == 0:
                configured_model = self._setup_model(model_class, scenario_name, table_name)
                shared_backend = configured_model.__backend__
            else:
                configured_model = self._setup_model(model_class, scenario_name, table_name, shared_backend=shared_backend)
            result.append(configured_model)
        return tuple(result)

    def setup_order_fixtures(self, scenario_name: str) -> Tuple[Type[ActiveRecord], Type[ActiveRecord], Type[ActiveRecord]]:
        models_and_tables = [(User, "users"), (Order, "orders"), (OrderItem, "order_items")]
        return self._setup_multiple_models(models_and_tables, scenario_name)

    def setup_blog_fixtures(self, scenario_name: str) -> Tuple[Type[ActiveRecord], Type[ActiveRecord], Type[ActiveRecord]]:
        models_and_tables = [(User, "users"), (Post, "posts"), (Comment, "comments")]
        return self._setup_multiple_models(models_and_tables, scenario_name)

    def setup_json_user_fixtures(self, scenario_name: str) -> Tuple[Type[ActiveRecord], ...]:
        return self._setup_multiple_models([(JsonUser, "json_users")], scenario_name)

    def setup_tree_fixtures(self, scenario_name: str) -> Tuple[Type[ActiveRecord], ...]:
        from rhosocial.activerecord.testsuite.feature.query.fixtures.cte_models import Node
        return self._setup_multiple_models([(Node, "nodes")], scenario_name)

    def setup_extended_order_fixtures(self, scenario_name: str) -> Tuple[Type[ActiveRecord], Type[ActiveRecord], Type[ActiveRecord]]:
        from rhosocial.activerecord.testsuite.feature.query.fixtures.extended_models import User, ExtendedOrder, ExtendedOrderItem
        models_and_tables = [(User, "users"), (ExtendedOrder, "extended_orders"), (ExtendedOrderItem, "extended_order_items")]
        return self._setup_multiple_models(models_and_tables, scenario_name)

    def setup_combined_fixtures(self, scenario_name: str) -> Tuple:
        models_and_tables = [(User, "users"), (Order, "orders"), (OrderItem, "order_items"), (Post, "posts"), (Comment, "comments")]
        return self._setup_multiple_models(models_and_tables, scenario_name)

    def setup_annotated_query_fixtures(self, scenario_name: str) -> Tuple[Type[ActiveRecord], ...]:
        from rhosocial.activerecord.testsuite.feature.query.fixtures.annotated_adapter_models import SearchableItem
        return self._setup_multiple_models([(SearchableItem, "searchable_items")], scenario_name)

    def setup_mapped_models(self, scenario_name: str) -> Tuple:
        models_and_tables = [(MappedUser, "users"), (MappedPost, "posts"), (MappedComment, "comments")]
        return self._setup_multiple_models(models_and_tables, scenario_name)

    def cleanup_after_test(self, scenario_name: str):
        """
        Performs cleanup after a test, disconnecting backends and deleting files.

        CRITICAL: Backend disconnection MUST happen before file deletion.
        SQLite maintains file locks on open connections. Attempting to delete
        a database file while connections are still open will:
        1. Fail silently on Unix (file remains until all handles closed)
        2. Hang indefinitely on Windows (exclusive lock prevents deletion)
        3. Cause subsequent tests to fail due to locked database files
        """
        # First, disconnect all active backends
        # This releases file locks before we attempt to delete the database file
        for backend_instance in self._active_backends:
            try:
                backend_instance.disconnect()
            except Exception:
                pass
        self._active_backends.clear()

        # Then delete the database files
        if scenario_name in self._scenario_db_files:
            for db_file in self._scenario_db_files[scenario_name]:
                if os.path.exists(db_file):
                    try:
                        os.remove(db_file)
                    except OSError:
                        pass
            del self._scenario_db_files[scenario_name]

    # --- Asynchronous Implementation (Completely Separate) ---

    async def _setup_model_async(self, model_class: Type[AsyncActiveRecord], scenario_name: str, table_name: str, shared_backend=None) -> Type[AsyncActiveRecord]:
        """A generic helper method to handle the setup for any given asynchronous model."""
        from rhosocial.activerecord_test.feature.backend.sqlite_async.async_backend import AsyncSQLiteBackend
        _, original_config = get_scenario(scenario_name)
        config = original_config

        if original_config.database != ":memory:":
            unique_filename = os.path.join(
                tempfile.gettempdir(),
                f"test_activerecord_{scenario_name}_async_{uuid.uuid4().hex}.sqlite"
            )
            self._scenario_db_files.setdefault(scenario_name, []).append(unique_filename)
            from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
            config = SQLiteConnectionConfig(
                database=unique_filename,
                delete_on_close=original_config.delete_on_close,
                pragmas=original_config.pragmas
            )

        if shared_backend is None:
            await model_class.configure(config, AsyncSQLiteBackend)
            await model_class.__backend__.connect()
            # Track the async backend instance for cleanup
            if model_class.__backend__ not in self._active_async_backends:
                self._active_async_backends.append(model_class.__backend__)
        else:
            model_class.__connection_config__ = config
            model_class.__backend_class__ = AsyncSQLiteBackend
            model_class.__backend__ = shared_backend

        # Monkey-patch for Windows timestamp resolution issues
        if os.name == 'nt' and not hasattr(model_class, '_save_patched_async'):
            original_save = model_class.save
            async def delayed_save(self, *args, **kwargs):
                result = await original_save(self, *args, **kwargs)
                await asyncio.sleep(0.001)
                return result
            model_class.save = delayed_save
            setattr(model_class, '_save_patched_async', True)

        # Prepare schema
        from rhosocial.activerecord.backend.options import ExecutionOptions
        from rhosocial.activerecord.backend.schema import StatementType
        options = ExecutionOptions(stmt_type=StatementType.DDL)
        await model_class.__backend__.execute(f"DROP TABLE IF EXISTS {table_name}", options=options)
        schema_sql = self._load_sqlite_schema(f"{table_name}.sql")
        await model_class.__backend__.execute(schema_sql, options=options)

        return model_class

    async def _setup_multiple_models_async(self, models_and_tables, scenario_name: str) -> Tuple[Type[AsyncActiveRecord], ...]:
        """A helper to set up multiple asynchronous models for fixture groups."""
        result = []
        shared_backend = None
        for i, (model_class, table_name) in enumerate(models_and_tables):
            if i == 0:
                configured_model = await self._setup_model_async(model_class, scenario_name, table_name)
                shared_backend = configured_model.__backend__
            else:
                configured_model = await self._setup_model_async(model_class, scenario_name, table_name, shared_backend=shared_backend)
            result.append(configured_model)
        return tuple(result)

    async def setup_async_order_fixtures(self, scenario_name: str) -> Tuple[Type[AsyncActiveRecord], Type[AsyncActiveRecord], Type[AsyncActiveRecord]]:
        """Sets up the database for async order-related models (AsyncUser, AsyncOrder, AsyncOrderItem) tests."""
        from rhosocial.activerecord.testsuite.feature.query.fixtures.async_models import AsyncUser, AsyncOrder, AsyncOrderItem
        models_and_tables = [(AsyncUser, "users"), (AsyncOrder, "orders"), (AsyncOrderItem, "order_items")]
        return await self._setup_multiple_models_async(models_and_tables, scenario_name)

    async def setup_async_blog_fixtures(self, scenario_name: str) -> Tuple[Type[AsyncActiveRecord], Type[AsyncActiveRecord], Type[AsyncActiveRecord]]:
        """Sets up the database for async blog-related models (AsyncUser, AsyncPost, AsyncComment) tests."""
        from rhosocial.activerecord.testsuite.feature.query.fixtures.async_blog_models import AsyncUser, AsyncPost, AsyncComment
        models_and_tables = [(AsyncUser, "users"), (AsyncPost, "posts"), (AsyncComment, "comments")]
        return await self._setup_multiple_models_async(models_and_tables, scenario_name)

    async def setup_async_json_user_fixtures(self, scenario_name: str) -> Tuple[Type[AsyncActiveRecord], ...]:
        """Sets up the database for async JSON user model (AsyncJsonUser) tests."""
        from rhosocial.activerecord.testsuite.feature.query.fixtures.async_json_models import AsyncJsonUser
        return await self._setup_multiple_models_async([(AsyncJsonUser, "json_users")], scenario_name)

    async def setup_async_tree_fixtures(self, scenario_name: str) -> Tuple[Type[AsyncActiveRecord], ...]:
        """Sets up the database for async tree structure model (AsyncNode) tests."""
        from rhosocial.activerecord.testsuite.feature.query.fixtures.async_cte_models import AsyncNode
        return await self._setup_multiple_models_async([(AsyncNode, "nodes")], scenario_name)

    async def setup_async_extended_order_fixtures(self, scenario_name: str) -> Tuple[Type[AsyncActiveRecord], Type[AsyncActiveRecord], Type[AsyncActiveRecord]]:
        """Sets up the database for async extended order-related models (AsyncUser, AsyncExtendedOrder, AsyncExtendedOrderItem) tests."""
        from rhosocial.activerecord.testsuite.feature.query.fixtures.async_extended_models import AsyncUser, AsyncExtendedOrder, AsyncExtendedOrderItem
        models_and_tables = [(AsyncUser, "users"), (AsyncExtendedOrder, "extended_orders"), (AsyncExtendedOrderItem, "extended_order_items")]
        return await self._setup_multiple_models_async(models_and_tables, scenario_name)

    async def setup_async_combined_fixtures(self, scenario_name: str) -> Tuple[Type[AsyncActiveRecord], Type[AsyncActiveRecord], Type[AsyncActiveRecord], Type[AsyncActiveRecord], Type[AsyncActiveRecord]]:
        """Sets up the database for async combined models (AsyncUser, AsyncOrder, AsyncOrderItem, AsyncPost, AsyncComment) tests."""
        from rhosocial.activerecord.testsuite.feature.query.fixtures.async_models import AsyncUser, AsyncOrder, AsyncOrderItem
        from rhosocial.activerecord.testsuite.feature.query.fixtures.async_blog_models import AsyncPost, AsyncComment
        models_and_tables = [(AsyncUser, "users"), (AsyncOrder, "orders"), (AsyncOrderItem, "order_items"), (AsyncPost, "posts"), (AsyncComment, "comments")]
        return await self._setup_multiple_models_async(models_and_tables, scenario_name)

    async def setup_async_annotated_query_fixtures(self, scenario_name: str) -> Tuple[Type[AsyncActiveRecord], ...]:
        """Sets up the database for async models using Annotated type adapters in queries (AsyncSearchableItem) tests."""
        from rhosocial.activerecord.testsuite.feature.query.fixtures.async_annotated_adapter_models import AsyncSearchableItem
        return await self._setup_multiple_models_async([(AsyncSearchableItem, "searchable_items")], scenario_name)

    async def setup_async_mapped_models(self, scenario_name: str) -> Tuple[Type[AsyncActiveRecord], Type[AsyncActiveRecord], Type[AsyncActiveRecord]]:
        """Sets up the database for async mapped models (AsyncMappedUser, AsyncMappedPost, AsyncMappedComment) tests."""
        from rhosocial.activerecord.testsuite.feature.query.fixtures.async_mapped_models import AsyncMappedUser, AsyncMappedPost, AsyncMappedComment
        models_and_tables = [(AsyncMappedUser, "users"), (AsyncMappedPost, "posts"), (AsyncMappedComment, "comments")]
        return await self._setup_multiple_models_async(models_and_tables, scenario_name)

    async def cleanup_after_test_async(self, scenario_name: str):
        """
        Performs async cleanup, disconnecting backends and deleting files.

        CRITICAL: Backend disconnection MUST happen before file deletion.
        See cleanup_after_test() for details on SQLite file locking behavior.
        """
        # First, disconnect all active async backends
        # This releases file locks before we attempt to delete the database file
        for backend_instance in self._active_async_backends:
            try:
                await backend_instance.disconnect()
            except Exception:
                pass
        self._active_async_backends.clear()

        # Then delete the database files
        if scenario_name in self._scenario_db_files:
            for db_file in self._scenario_db_files[scenario_name]:
                if os.path.exists(db_file):
                    try:
                        os.remove(db_file)
                    except OSError:
                        pass
            del self._scenario_db_files[scenario_name]

    # --- Common Helpers ---

    def _load_sqlite_schema(self, filename: str) -> str:
        """Helper to load a SQL schema file from this project's fixtures."""
        schema_dir = os.path.join(os.path.dirname(__file__), "..", "rhosocial", "activerecord_test", "feature", "query", "schema")
        schema_path = os.path.join(schema_dir, filename)
        with open(schema_path, 'r', encoding='utf-8') as f:
            return f.read()

    def __del__(self):
        """Ensure all temp files are cleaned up when the provider is destroyed."""
        for scenario_name in list(self._scenario_db_files.keys()):
            self.cleanup_after_test(scenario_name)

    # --- Implementation of WorkerTestProtocol ---

    def get_worker_connection_params(self, scenario_name: str, fixture_type: str = 'order') -> dict:
        """
        Return serializable connection parameters for Worker processes.

        This method provides all information needed to recreate the database
        connection in a Worker process, including the schema SQL for table creation.

        Args:
            scenario_name: The test scenario name
            fixture_type: Type of fixture ('order', 'blog', 'user', 'combined',
                         or with 'async_' prefix for async backends)

        Returns:
            Dictionary with connection parameters and schema SQL
        """
        # Get the database file path used in this scenario
        if scenario_name in self._scenario_db_files:
            # Use the first file from the list (they all share the same database)
            database_path = self._scenario_db_files[scenario_name][0]
        else:
            _, config = get_scenario(scenario_name)
            database_path = config.database

        # Determine if async backend is needed based on fixture_type
        is_async = fixture_type and fixture_type.startswith('async_')
        backend_class_name = 'AsyncSQLiteBackend' if is_async else 'SQLiteBackend'

        # Get base fixture type (remove 'async_' prefix if present)
        base_fixture_type = fixture_type.replace('async_', '') if fixture_type else 'order'

        # Build schema SQL based on fixture type
        schema_sql = self._get_schema_sql_for_fixture_type(base_fixture_type)

        return {
            'backend_module': 'rhosocial.activerecord.backend.impl.sqlite',
            'backend_class_name': backend_class_name,
            'config_class_module': 'rhosocial.activerecord.backend.impl.sqlite.config',
            'config_class_name': 'SQLiteConnectionConfig',
            'config_kwargs': {
                'database': database_path,
            },
            'schema_sql': schema_sql,
        }

    def get_worker_schema_sql(self, scenario_name: str, table_name: str) -> str:
        """
        Return the SQL statement to create a specific table.

        Args:
            scenario_name: The test scenario name (unused for SQLite as schema is fixed)
            table_name: Name of the table to create

        Returns:
            CREATE TABLE SQL statement
        """
        return self._load_sqlite_schema(f'{table_name}.sql')

    def _get_schema_sql_for_fixture_type(self, fixture_type: str) -> dict:
        """
        Get schema SQL for a specific fixture type.

        Args:
            fixture_type: Type of fixture ('order', 'blog', 'user', 'combined')

        Returns:
            Dictionary mapping table names to CREATE TABLE statements
        """
        schemas = {}

        if fixture_type == 'order':
            tables = ['users', 'orders', 'order_items']
        elif fixture_type == 'blog':
            tables = ['users', 'posts', 'comments']
        elif fixture_type == 'user':
            tables = ['users']
        elif fixture_type == 'combined':
            tables = ['users', 'orders', 'order_items', 'posts', 'comments']
        else:
            tables = ['users']

        for table in tables:
            schemas[table] = self._load_sqlite_schema(f'{table}.sql')

        return schemas
