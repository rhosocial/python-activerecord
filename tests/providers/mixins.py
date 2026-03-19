# tests/providers/mixins.py
"""
This file provides the concrete implementation of the `IMixinsProvider` interface
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
import sys
import logging
from typing import Type, List

from rhosocial.activerecord.model import ActiveRecord

# Setup logging for fixture selection debugging
logger = logging.getLogger(__name__)

# Import the fixture selector utility
from rhosocial.activerecord.testsuite.utils import select_fixture

# Import base version models (Python 3.8+)
from rhosocial.activerecord.testsuite.feature.mixins.fixtures.models import (
    TimestampedPost as TimestampedPostBase,
    VersionedProduct as VersionedProductBase,
    Task as TaskBase,
    CombinedArticle as CombinedArticleBase
)

# Conditionally import Python 3.10+ models
TimestampedPost310 = VersionedProduct310 = Task310 = CombinedArticle310 = None

if sys.version_info >= (3, 10):
    try:
        from rhosocial.activerecord.testsuite.feature.mixins.fixtures.models_py310 import (
            TimestampedPost as TimestampedPost310,
            VersionedProduct as VersionedProduct310,
            Task as Task310,
            CombinedArticle as CombinedArticle310
        )
    except ImportError as e:
        logger.warning(f"Failed to import Python 3.10+ fixtures: {e}")

# Conditionally import Python 3.11+ models
TimestampedPost311 = VersionedProduct311 = Task311 = CombinedArticle311 = None

if sys.version_info >= (3, 11):
    try:
        from rhosocial.activerecord.testsuite.feature.mixins.fixtures.models_py311 import (
            TimestampedPost as TimestampedPost311,
            VersionedProduct as VersionedProduct311,
            Task as Task311,
            CombinedArticle as CombinedArticle311
        )
    except ImportError as e:
        logger.warning(f"Failed to import Python 3.11+ fixtures: {e}")

# Conditionally import Python 3.12+ models
TimestampedPost312 = VersionedProduct312 = Task312 = CombinedArticle312 = None

if sys.version_info >= (3, 12):
    try:
        from rhosocial.activerecord.testsuite.feature.mixins.fixtures.models_py312 import (
            TimestampedPost as TimestampedPost312,
            VersionedProduct as VersionedProduct312,
            Task as Task312,
            CombinedArticle as CombinedArticle312
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


# Select models
TimestampedPost = _select_model_class(TimestampedPostBase, TimestampedPost312, TimestampedPost311, TimestampedPost310, "TimestampedPost")
VersionedProduct = _select_model_class(VersionedProductBase, VersionedProduct312, VersionedProduct311, VersionedProduct310, "VersionedProduct")
Task = _select_model_class(TaskBase, Task312, Task311, Task310, "Task")
CombinedArticle = _select_model_class(CombinedArticleBase, CombinedArticle312, CombinedArticle311, CombinedArticle310, "CombinedArticle")

from rhosocial.activerecord.testsuite.feature.mixins.interfaces import IMixinsProvider
# ...and the scenarios are defined specifically for this backend.
from .scenarios import get_enabled_scenarios, get_scenario


class MixinsProvider(IMixinsProvider):
    """
    This is the SQLite backend's implementation for the mixins features test group.
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

    # --- Implementation of the IMixinsProvider interface ---

    def setup_timestamped_post_model(self, scenario_name: str) -> Type[ActiveRecord]:
        """Sets up the database for the timestamped post model tests."""
        return self._setup_model(TimestampedPost, scenario_name, "timestamped_posts")

    def setup_versioned_product_model(self, scenario_name: str) -> Type[ActiveRecord]:
        """Sets up the database for the versioned product model tests."""
        return self._setup_model(VersionedProduct, scenario_name, "versioned_products")

    def setup_task_model(self, scenario_name: str) -> Type[ActiveRecord]:
        """Sets up the database for the task model tests."""
        return self._setup_model(Task, scenario_name, "tasks")

    def setup_combined_article_model(self, scenario_name: str) -> Type[ActiveRecord]:
        """Sets up the database for the combined article model tests."""
        return self._setup_model(CombinedArticle, scenario_name, "combined_articles")

    def _load_sqlite_schema(self, filename: str) -> str:
        """Helper to load a SQL schema file from this project's fixtures."""
        # Schemas are stored in the centralized location for mixins feature.
        schema_dir = os.path.join(os.path.dirname(__file__), "..", "rhosocial", "activerecord_test", "feature", "mixins", "schema")
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