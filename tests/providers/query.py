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
from typing import Type, List
from rhosocial.activerecord import ActiveRecord
from rhosocial.activerecord.testsuite.feature.query.interfaces import IQueryProvider
# The models are defined generically in the testsuite...
from rhosocial.activerecord.testsuite.feature.query.fixtures.models import QueryTestModel
# ...and the scenarios are defined specifically for this backend.
from .scenarios import get_enabled_scenarios, get_scenario


class QueryProvider(IQueryProvider):
    """
    This is the SQLite backend's implementation for the query features test group.
    It connects the generic tests in the testsuite with the actual SQLite database.
    """

    def get_test_scenarios(self) -> List[str]:
        """Returns a list of names for all enabled scenarios for this backend."""
        return list(get_enabled_scenarios().keys())

    def _setup_model(self, model_class: Type[ActiveRecord], scenario_name: str, table_name: str) -> Type[ActiveRecord]:
        """A generic helper method to handle the setup for any given model."""
        # 1. Get the backend class (SQLiteBackend) and connection config for the requested scenario.
        backend_class, config = get_scenario(scenario_name)
        
        # 2. Configure the generic model class with our specific backend and config.
        #    This is the key step that links the testsuite's model to our database.
        model_class.configure(config, backend_class)
        
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

    # --- Implementation of the IQueryProvider interface ---

    def setup_query_test_model(self, scenario_name: str) -> Type[ActiveRecord]:
        """Sets up the database for the `QueryTestModel` model tests."""
        return self._setup_model(QueryTestModel, scenario_name, "query_test_models")

    def _load_sqlite_schema(self, filename: str) -> str:
        """Helper to load a SQL schema file from this project's fixtures."""
        # Schemas are stored locally within this backend's test directory.
        schema_dir = os.path.join(os.path.dirname(__file__), "..", "fixtures", "schemas", "sqlite")
        schema_path = os.path.join(schema_dir, filename)
        
        with open(schema_path, 'r', encoding='utf-8') as f:
            return f.read()

    def cleanup_after_test(self, scenario_name: str):
        """
        Performs cleanup after a test. For file-based scenarios, this involves
        deleting the temporary database file.
        """
        _, config = get_scenario(scenario_name)
        if config.delete_on_close and config.database != ":memory:" and os.path.exists(config.database):
            try:
                # Attempt to remove the temp db file.
                os.remove(config.database)
            except OSError:
                # Ignore errors if the file is already gone or locked, etc.
                pass