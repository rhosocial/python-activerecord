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
import time
import uuid
import tempfile
from typing import Type, List, Tuple

from rhosocial.activerecord.model import ActiveRecord, AsyncActiveRecord
from rhosocial.activerecord.testsuite.feature.query.interfaces import IQueryProvider
# Sync models are defined generically in the testsuite
from rhosocial.activerecord.testsuite.feature.query.fixtures.models import MappedUser, MappedPost, MappedComment
# Scenarios are defined specifically for this backend.
from .scenarios import get_enabled_scenarios, get_scenario


class QueryProvider(IQueryProvider):
    """
    This is the SQLite backend's implementation for the query features test group.
    It connects the generic tests in the testsuite with the actual SQLite database.
    """

    def __init__(self):
        # Track the actual database file used for each scenario in the current test run.
        self._scenario_db_files = {}

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
        from rhosocial.activerecord.testsuite.feature.query.fixtures.models import User, Order, OrderItem
        models_and_tables = [(User, "users"), (Order, "orders"), (OrderItem, "order_items")]
        return self._setup_multiple_models(models_and_tables, scenario_name)

    def setup_blog_fixtures(self, scenario_name: str) -> Tuple[Type[ActiveRecord], Type[ActiveRecord], Type[ActiveRecord]]:
        from rhosocial.activerecord.testsuite.feature.query.fixtures.models import User, Post, Comment
        models_and_tables = [(User, "users"), (Post, "posts"), (Comment, "comments")]
        return self._setup_multiple_models(models_and_tables, scenario_name)

    def setup_json_user_fixtures(self, scenario_name: str) -> Tuple[Type[ActiveRecord], ...]:
        from rhosocial.activerecord.testsuite.feature.query.fixtures.models import JsonUser
        return self._setup_multiple_models([(JsonUser, "json_users")], scenario_name)

    def setup_tree_fixtures(self, scenario_name: str) -> Tuple[Type[ActiveRecord], ...]:
        from rhosocial.activerecord.testsuite.feature.query.fixtures.cte_models import Node
        return self._setup_multiple_models([(Node, "nodes")], scenario_name)

    def setup_extended_order_fixtures(self, scenario_name: str) -> Tuple[Type[ActiveRecord], Type[ActiveRecord], Type[ActiveRecord]]:
        from rhosocial.activerecord.testsuite.feature.query.fixtures.extended_models import User, ExtendedOrder, ExtendedOrderItem
        models_and_tables = [(User, "users"), (ExtendedOrder, "extended_orders"), (ExtendedOrderItem, "extended_order_items")]
        return self._setup_multiple_models(models_and_tables, scenario_name)

    def setup_combined_fixtures(self, scenario_name: str) -> Tuple:
        from rhosocial.activerecord.testsuite.feature.query.fixtures.models import User, Order, OrderItem, Post, Comment
        models_and_tables = [(User, "users"), (Order, "orders"), (OrderItem, "order_items"), (Post, "posts"), (Comment, "comments")]
        return self._setup_multiple_models(models_and_tables, scenario_name)

    def setup_annotated_query_fixtures(self, scenario_name: str) -> Tuple[Type[ActiveRecord], ...]:
        from rhosocial.activerecord.testsuite.feature.query.fixtures.annotated_adapter_models import SearchableItem
        return self._setup_multiple_models([(SearchableItem, "searchable_items")], scenario_name)

    def setup_mapped_models(self, scenario_name: str) -> Tuple:
        models_and_tables = [(MappedUser, "users"), (MappedPost, "posts"), (MappedComment, "comments")]
        return self._setup_multiple_models(models_and_tables, scenario_name)

    def cleanup_after_test(self, scenario_name: str):
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
            model_class.configure(config, AsyncSQLiteBackend)
            await model_class.__backend__.connect()
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
        """Performs async cleanup. Logic is identical to sync for file operations."""
        self.cleanup_after_test(scenario_name)

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
