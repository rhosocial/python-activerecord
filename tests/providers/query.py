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
import os
import time
from typing import Type, List, Tuple
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.testsuite.feature.query.interfaces import IQueryProvider
# The models are defined generically in the testsuite...

# ...and the scenarios are defined specifically for this backend.
from .scenarios import get_enabled_scenarios, get_scenario


class QueryProvider(IQueryProvider):
    """
    This is the SQLite backend's implementation for the query features test group.
    It connects the generic tests in the testsuite with the actual SQLite database.
    """
    
    def __init__(self):
        # Track the actual database file used for each scenario in the current test
        self._scenario_db_files = {}

    def get_test_scenarios(self) -> List[str]:
        """Returns a list of names for all enabled scenarios for this backend."""
        return list(get_enabled_scenarios().keys())

    def _setup_model(self, model_class: Type[ActiveRecord], scenario_name: str, table_name: str, shared_backend=None) -> Type[ActiveRecord]:
        """A generic helper method to handle the setup for any given model."""
        # 1. Get the backend class (SQLiteBackend) and connection config for the requested scenario.
        backend_class, original_config = get_scenario(scenario_name)
        
        # Check if this is a file-based scenario, and if so, generate a unique filename
        import os
        import tempfile
        import uuid
        config = original_config  # default to the original config
        
        if original_config.database != ":memory:":
            # For file-based scenarios, create a unique temporary file
            unique_filename = os.path.join(
                tempfile.gettempdir(),
                f"test_activerecord_{scenario_name}_{uuid.uuid4().hex}.sqlite"
            )
            
            # Store the actual database file used for this scenario in this test
            self._scenario_db_files[scenario_name] = unique_filename
            
            # Create a new config with the unique database path
            from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
            config = SQLiteConnectionConfig(
                database=unique_filename,
                delete_on_close=original_config.delete_on_close,
                pragmas=original_config.pragmas
            )

        # 2. Configure the generic model class with our specific backend and config.
        #    This is the key step that links the testsuite's model to our database.
        if shared_backend is None:
            # Create a new backend instance for complete isolation
            model_class.configure(config, backend_class)
        else:
            # Reuse the shared backend instance for subsequent models in the group
            model_class.__connection_config__ = config
            model_class.__backend_class__ = backend_class
            model_class.__backend__ = shared_backend

        # On Windows, add a small delay after each save operation to ensure
        # proper timestamp ordering since multiple rapid operations may have
        # nearly identical timestamps, causing flaky tests
        original_save = model_class.save

        def delayed_save(self, *args, **kwargs):
            result = original_save(self, *args, **kwargs)
            # Add small delay to ensure timestamp differences on Windows
            time.sleep(0.001)  # 1ms delay
            return result

        model_class.save = delayed_save

        # 3. Prepare the database schema. To ensure tests are isolated, we drop
        #    the table if it exists and recreate it from the schema file.
        try:
            model_class.__backend__.execute(f"DROP TABLE IF EXISTS {table_name}")
        except Exception:
            # Ignore errors if the table doesn't exist, which is expected on the first run.
            pass
            
        schema_sql = self._load_sqlite_schema(f"{table_name}.sql")
        model_class.__backend__.execute(schema_sql)
        
        return model_class

    def _setup_multiple_models(self, models_and_tables, scenario_name: str) -> Tuple[Type[ActiveRecord], ...]:
        """A helper to set up multiple models for fixture groups."""
        result = []
        shared_backend = None
        for i, (model_class, table_name) in enumerate(models_and_tables):
            if i == 0:
                # For the first model, create a new backend instance
                configured_model = self._setup_model(model_class, scenario_name, table_name)
                shared_backend = configured_model.__backend__
            else:
                # For subsequent models, reuse the shared backend instance
                configured_model = self._setup_model(model_class, scenario_name, table_name, shared_backend=shared_backend)
            result.append(configured_model)
        return tuple(result)

    # --- Implementation of the IQueryProvider interface ---

    def setup_order_fixtures(self, scenario_name: str) -> Tuple[Type[ActiveRecord], Type[ActiveRecord], Type[ActiveRecord]]:
        """Sets up the database for order-related models (User, Order, OrderItem) tests."""
        from rhosocial.activerecord.testsuite.feature.query.fixtures.models import User, Order, OrderItem
        models_and_tables = [
            (User, "users"),
            (Order, "orders"),
            (OrderItem, "order_items")
        ]
        return self._setup_multiple_models(models_and_tables, scenario_name)

    def setup_blog_fixtures(self, scenario_name: str) -> Tuple[Type[ActiveRecord], Type[ActiveRecord], Type[ActiveRecord]]:
        """Sets up the database for blog-related models (User, Post, Comment) tests."""
        from rhosocial.activerecord.testsuite.feature.query.fixtures.models import User, Post, Comment
        models_and_tables = [
            (User, "users"),
            (Post, "posts"),
            (Comment, "comments")
        ]
        return self._setup_multiple_models(models_and_tables, scenario_name)

    def setup_json_user_fixtures(self, scenario_name: str) -> Tuple[Type[ActiveRecord], ...]:
        """Sets up the database for the JSON user model."""
        from rhosocial.activerecord.testsuite.feature.query.fixtures.models import JsonUser
        models_and_tables = [
            (JsonUser, "json_users"),
        ]
        return self._setup_multiple_models(models_and_tables, scenario_name)

    def setup_tree_fixtures(self, scenario_name: str) -> Tuple[Type[ActiveRecord], ...]:
        """Sets up the database for the tree structure (Node) model."""
        from rhosocial.activerecord.testsuite.feature.query.fixtures.cte_models import Node
        models_and_tables = [
            (Node, "nodes"),
        ]
        return self._setup_multiple_models(models_and_tables, scenario_name)

    def setup_extended_order_fixtures(self, scenario_name: str) -> Tuple[Type[ActiveRecord], Type[ActiveRecord], Type[ActiveRecord]]:
        """Sets up the database for extended order-related models (User, ExtendedOrder, ExtendedOrderItem) tests."""
        from rhosocial.activerecord.testsuite.feature.query.fixtures.extended_models import User, ExtendedOrder, ExtendedOrderItem
        models_and_tables = [
            (User, "users"),
            (ExtendedOrder, "extended_orders"),
            (ExtendedOrderItem, "extended_order_items")
        ]
        return self._setup_multiple_models(models_and_tables, scenario_name)

    def setup_combined_fixtures(self, scenario_name: str) -> Tuple[Type[ActiveRecord], Type[ActiveRecord], Type[ActiveRecord], Type[ActiveRecord], Type[ActiveRecord]]:
        """Sets up the database for combined models (User, Order, OrderItem, Post, Comment) tests."""
        from rhosocial.activerecord.testsuite.feature.query.fixtures.models import User, Order, OrderItem, Post, Comment
        models_and_tables = [
            (User, "users"),
            (Order, "orders"),
            (OrderItem, "order_items"),
            (Post, "posts"),
            (Comment, "comments")
        ]
        return self._setup_multiple_models(models_and_tables, scenario_name)

    def _load_sqlite_schema(self, filename: str) -> str:
        """Helper to load a SQL schema file from this project's fixtures."""
        # Schemas are stored in the centralized location for query feature.
        schema_dir = os.path.join(os.path.dirname(__file__), "..", "rhosocial", "activerecord_test", "feature", "query", "schema")
        schema_path = os.path.join(schema_dir, filename)
        
        with open(schema_path, 'r', encoding='utf-8') as f:
            return f.read()

    def cleanup_after_test(self, scenario_name: str):
        """
        Performs cleanup after a test. For file-based scenarios, this involves
        deleting the temporary database file.
        """
        # Use the dynamically generated database file if available, otherwise use the original config
        if scenario_name in self._scenario_db_files:
            db_file = self._scenario_db_files[scenario_name]
            if os.path.exists(db_file):
                try:
                    # Attempt to remove the temp db file.
                    os.remove(db_file)
                    # Remove from tracking dict
                    del self._scenario_db_files[scenario_name]
                except OSError:
                    # Ignore errors if the file is already gone or locked, etc.
                    pass
        else:
            # Fallback to original behavior for in-memory databases
            _, config = get_scenario(scenario_name)
            if config.delete_on_close and config.database != ":memory:" and os.path.exists(config.database):
                try:
                    # Attempt to remove the temp db file.
                    os.remove(config.database)
                except OSError:
                    # Ignore errors if the file is already gone or locked, etc.
                    pass