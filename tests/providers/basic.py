# tests/providers/basic.py
"""
This file provides the concrete implementation of the `IBasicProvider` interface
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
from typing import Type, List, Tuple

from rhosocial.activerecord.backend.type_adapter import BaseSQLTypeAdapter
from rhosocial.activerecord.model import ActiveRecord
# The models are defined generically in the testsuite...
from rhosocial.activerecord.testsuite.feature.basic.fixtures.models import (
    User, TypeCase, ValidatedFieldUser, TypeTestModel, ValidatedUser, TypeAdapterTest, YesOrNoBooleanAdapter,
    MappedUser, MappedPost, MappedComment, ColumnMappingModel, MixedAnnotationModel
)
# Import async models (now in the same file as sync models)
from rhosocial.activerecord.testsuite.feature.basic.fixtures.models import (
    AsyncUser, AsyncTypeCase, AsyncValidatedUser, AsyncValidatedFieldUser, AsyncTypeTestModel
)
# Import async type adapter model
from rhosocial.activerecord.testsuite.feature.basic.fixtures.models import (
    AsyncTypeAdapterTest, AsyncYesOrNoBooleanAdapter
)
from rhosocial.activerecord.testsuite.feature.basic.interfaces import IBasicProvider
# ...and the scenarios are defined specifically for this backend.
from .scenarios import get_enabled_scenarios, get_scenario


class BasicProvider(IBasicProvider):
    """
    This is the SQLite backend's implementation for the basic features test group.
    It connects the generic tests in the testsuite with the actual SQLite database.
    """
    
    def __init__(self):
        # Track the actual database file used for each scenario in the current test
        self._scenario_db_files = {}

    def get_test_scenarios(self) -> List[str]:
        """Returns a list of names for all enabled scenarios for this backend."""
        return list(get_enabled_scenarios().keys())

    def _setup_model(self, model_class: Type[ActiveRecord], scenario_name: str, table_name: str) -> Type[ActiveRecord]:
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
        model_class.configure(config, backend_class)

        # 3. Prepare the database schema. To ensure tests are isolated, we drop
        #    the table if it exists and recreate it from the schema file.
        from rhosocial.activerecord.backend.options import ExecutionOptions
        from rhosocial.activerecord.backend.schema import StatementType
        try:
            model_class.__backend__.execute(f"DROP TABLE IF EXISTS {table_name}", options=ExecutionOptions(stmt_type=StatementType.DDL))
        except Exception:
            # Ignore errors if the table doesn't exist, which is expected on the first run.
            pass

        schema_sql = self._load_sqlite_schema(f"{table_name}.sql")
        model_class.__backend__.execute(schema_sql, options=ExecutionOptions(stmt_type=StatementType.DDL))

        return model_class

    async def _setup_async_model(self, model_class: Type[ActiveRecord], scenario_name: str, table_name: str) -> Type[ActiveRecord]:
        """A generic helper method to handle the setup for any given async model."""
        # 1. Get the backend class (AsyncSQLiteBackend) and connection config for the requested scenario.
        from rhosocial.activerecord_test.feature.backend.sqlite_async.async_backend import AsyncSQLiteBackend
        backend_class = AsyncSQLiteBackend
        _, original_config = get_scenario(scenario_name)

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

        # 2. Configure the generic async model class with our specific async backend and config.
        #    This is the key step that links the testsuite's async model to our database.
        model_class.configure(config, backend_class)

        # 3. Prepare the database schema. To ensure tests are isolated, we drop
        #    the table if it exists and recreate it from the schema file.
        from rhosocial.activerecord.backend.options import ExecutionOptions
        from rhosocial.activerecord.backend.schema import StatementType
        try:
            await model_class.__backend__.execute(f"DROP TABLE IF EXISTS {table_name}", options=ExecutionOptions(stmt_type=StatementType.DDL))
        except Exception:
            # Ignore errors if the table doesn't exist, which is expected on the first run.
            pass

        schema_sql = self._load_sqlite_schema(f"{table_name}.sql")
        await model_class.__backend__.execute(schema_sql, options=ExecutionOptions(stmt_type=StatementType.DDL))

        return model_class

    # --- Implementation of the IBasicProvider interface ---

    def setup_user_model(self, scenario_name: str) -> Type[ActiveRecord]:
        """Sets up the database for the `User` model tests."""
        return self._setup_model(User, scenario_name, "users")

    def setup_type_case_model(self, scenario_name: str) -> Type[ActiveRecord]:
        """Sets up the database for the `TypeCase` model tests."""
        return self._setup_model(TypeCase, scenario_name, "type_cases")

    def setup_type_test_model(self, scenario_name: str) -> Type[ActiveRecord]:
        """Sets up the database for the `TypeTestModel` model tests."""
        return self._setup_model(TypeTestModel, scenario_name, "type_tests")

    def setup_validated_field_user_model(self, scenario_name: str) -> Type[ActiveRecord]:
        """Sets up the database for the `ValidatedFieldUser` model tests."""
        return self._setup_model(ValidatedFieldUser, scenario_name, "validated_field_users")

    def setup_validated_user_model(self, scenario_name: str) -> Type[ActiveRecord]:
        """Sets up the database for the `ValidatedUser` model tests."""
        return self._setup_model(ValidatedUser, scenario_name, "validated_users")

    def setup_mapped_models(self, scenario_name: str):
        """Sets up the database for MappedUser, MappedPost, and MappedComment models."""
        user = self._setup_model(MappedUser, scenario_name, "users")
        post = self._setup_model(MappedPost, scenario_name, "posts")
        comment = self._setup_model(MappedComment, scenario_name, "comments")
        return user, post, comment

    def setup_mixed_models(self, scenario_name: str) -> Tuple[Type[ActiveRecord], ...]:
        """Sets up the database for ColumnMappingModel and MixedAnnotationModel."""
        column_mapping_model = self._setup_model(ColumnMappingModel, scenario_name, "column_mapping_items")
        mixed_annotation_model = self._setup_model(MixedAnnotationModel, scenario_name, "mixed_annotation_items")
        return column_mapping_model, mixed_annotation_model

    def setup_type_adapter_model_and_schema(self, scenario_name: str) -> Type[ActiveRecord]:
        """Sets up the database for the `TypeAdapterTest` model tests."""
        return self._setup_model(TypeAdapterTest, scenario_name, "type_adapter_tests")

    async def setup_async_user_model(self, scenario_name: str) -> Type[ActiveRecord]:
        """Sets up the database for the `AsyncUser` model tests."""
        return await self._setup_async_model(AsyncUser, scenario_name, "users")

    async def setup_async_type_case_model(self, scenario_name: str) -> Type[ActiveRecord]:
        """Sets up the database for the `AsyncTypeCase` model tests."""
        return await self._setup_async_model(AsyncTypeCase, scenario_name, "type_cases")

    async def setup_async_validated_user_model(self, scenario_name: str) -> Type[ActiveRecord]:
        """Sets up the database for the `AsyncValidatedFieldUser` model tests."""
        return await self._setup_async_model(AsyncValidatedFieldUser, scenario_name, "validated_field_users")

    async def setup_async_type_test_model(self, scenario_name: str) -> Type[ActiveRecord]:
        """Sets up the database for the `AsyncTypeTestModel` model tests."""
        return await self._setup_async_model(AsyncTypeTestModel, scenario_name, "type_tests")

    async def setup_async_validated_field_user_model(self, scenario_name: str) -> Type[ActiveRecord]:
        """Sets up the database for the `AsyncValidatedFieldUser` model tests."""
        return await self._setup_async_model(AsyncValidatedFieldUser, scenario_name, "validated_field_users")

    async def setup_async_mapped_models(self, scenario_name: str):
        """Sets up the database for AsyncMappedUser, AsyncMappedPost, and AsyncMappedComment models."""
        from rhosocial.activerecord.testsuite.feature.basic.fixtures.models import AsyncMappedUser, AsyncMappedPost, AsyncMappedComment

        # Use shared backend for all models to ensure proper cleanup
        user = await self._setup_async_model(AsyncMappedUser, scenario_name, "users")
        shared_backend = user.__backend__

        # Configure remaining models with the same backend instance
        post_model_class = AsyncMappedPost
        post_model_class.__connection_config__ = user.__connection_config__
        post_model_class.__backend_class__ = user.__backend_class__
        post_model_class.__backend__ = shared_backend
        await self._initialize_async_model_schema(post_model_class, scenario_name, "posts")

        comment_model_class = AsyncMappedComment
        comment_model_class.__connection_config__ = user.__connection_config__
        comment_model_class.__backend_class__ = user.__backend_class__
        comment_model_class.__backend__ = shared_backend
        await self._initialize_async_model_schema(comment_model_class, scenario_name, "comments")

        return user, post_model_class, comment_model_class

    async def _initialize_async_model_schema(self, model_class: Type[ActiveRecord], scenario_name: str, table_name: str):
        """Initialize schema for a model that shares backend with another model."""
        from rhosocial.activerecord.backend.options import ExecutionOptions
        from rhosocial.activerecord.backend.schema import StatementType
        options = ExecutionOptions(stmt_type=StatementType.DDL)
        await model_class.__backend__.execute(f"DROP TABLE IF EXISTS {table_name}", options=options)
        schema_sql = self._load_sqlite_schema(f"{table_name}.sql")
        await model_class.__backend__.execute(schema_sql, options=options)

    async def setup_async_mixed_models(self, scenario_name: str) -> Tuple[Type[ActiveRecord], ...]:
        """Sets up the database for AsyncColumnMappingModel and AsyncMixedAnnotationModel."""
        from rhosocial.activerecord.testsuite.feature.basic.fixtures.models import AsyncColumnMappingModel, AsyncMixedAnnotationModel

        # Use shared backend for all models to ensure proper cleanup
        column_mapping_model = await self._setup_async_model(AsyncColumnMappingModel, scenario_name, "column_mapping_items")
        shared_backend = column_mapping_model.__backend__

        # Configure remaining models with the same backend instance
        mixed_annotation_model_class = AsyncMixedAnnotationModel
        mixed_annotation_model_class.__connection_config__ = column_mapping_model.__connection_config__
        mixed_annotation_model_class.__backend_class__ = column_mapping_model.__backend_class__
        mixed_annotation_model_class.__backend__ = shared_backend
        await self._initialize_async_model_schema(mixed_annotation_model_class, scenario_name, "mixed_annotation_items")

        return column_mapping_model, mixed_annotation_model_class

    def get_yes_no_adapter(self) -> BaseSQLTypeAdapter:
        """Returns an instance of the YesOrNoBooleanAdapter."""
        return YesOrNoBooleanAdapter()

    async def setup_async_type_adapter_model_and_schema(self, scenario_name: str) -> Type[ActiveRecord]:
        """Sets up the database for the `AsyncTypeAdapterTest` model tests."""
        return await self._setup_async_model(AsyncTypeAdapterTest, scenario_name, "type_adapter_tests")

    async def cleanup_after_test_async(self, scenario_name: str):
        """
        Performs async cleanup after a test. For file-based scenarios, this involves
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

    def _load_sqlite_schema(self, filename: str) -> str:
        """Helper to load a SQL schema file from this project's fixtures."""
        # Schemas are stored in the centralized location for basic feature.
        schema_dir = os.path.join(os.path.dirname(__file__), "..", "rhosocial", "activerecord_test", "feature", "basic", "schema")
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
