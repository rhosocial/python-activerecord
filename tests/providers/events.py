# tests/providers/events.py
"""
This file provides the concrete implementation of the `IEventsProvider` interface
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
from rhosocial.activerecord.testsuite.feature.events.fixtures.models import (
    EventTestModel as EventTestModelBase,
    EventTrackingModel as EventTrackingModelBase
)

# Conditionally import Python 3.10+ models
EventTestModel310 = EventTrackingModel310 = None

if sys.version_info >= (3, 10):
    try:
        from rhosocial.activerecord.testsuite.feature.events.fixtures.models_py310 import (
            EventTestModel as EventTestModel310,
            EventTrackingModel as EventTrackingModel310
        )
    except ImportError as e:
        logger.warning(f"Failed to import Python 3.10+ fixtures: {e}")

# Conditionally import Python 3.11+ models
EventTestModel311 = EventTrackingModel311 = None

if sys.version_info >= (3, 11):
    try:
        from rhosocial.activerecord.testsuite.feature.events.fixtures.models_py311 import (
            EventTestModel as EventTestModel311,
            EventTrackingModel as EventTrackingModel311
        )
    except ImportError as e:
        logger.warning(f"Failed to import Python 3.11+ fixtures: {e}")

# Conditionally import Python 3.12+ models
EventTestModel312 = EventTrackingModel312 = None

if sys.version_info >= (3, 12):
    try:
        from rhosocial.activerecord.testsuite.feature.events.fixtures.models_py312 import (
            EventTestModel as EventTestModel312,
            EventTrackingModel as EventTrackingModel312
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
EventTestModel = _select_model_class(EventTestModelBase, EventTestModel312, EventTestModel311, EventTestModel310, "EventTestModel")
EventTrackingModel = _select_model_class(EventTrackingModelBase, EventTrackingModel312, EventTrackingModel311, EventTrackingModel310, "EventTrackingModel")

from rhosocial.activerecord.testsuite.feature.events.interfaces import IEventsProvider
# ...and the scenarios are defined specifically for this backend.
from .scenarios import get_enabled_scenarios, get_scenario


class EventsProvider(IEventsProvider):
    """
    This is the SQLite backend's implementation for the events features test group.
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

    # --- Implementation of the IEventsProvider interface ---

    def setup_event_model(self, scenario_name: str) -> Type[ActiveRecord]:
        """Sets up the database for the event model tests."""
        return self._setup_model(EventTestModel, scenario_name, "event_tests")

    def setup_event_tracking_model(self, scenario_name: str) -> Type[ActiveRecord]:
        """Sets up the database for the event tracking model tests."""
        return self._setup_model(EventTrackingModel, scenario_name, "event_tracking_models")

    def _load_sqlite_schema(self, filename: str) -> str:
        """Helper to load a SQL schema file from this project's fixtures."""
        # Schemas are stored in the centralized location for events feature.
        schema_dir = os.path.join(os.path.dirname(__file__), "..", "rhosocial", "activerecord_test", "feature", "events", "schema")
        schema_path = os.path.join(schema_dir, filename)
        
        # If the specific schema file doesn't exist, fall back to a generic one
        if not os.path.exists(schema_path):
            # Handle specific cases
            if filename == "event_tests.sql":
                return """
                CREATE TABLE event_tests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'draft',
                    revision INTEGER NOT NULL DEFAULT 1,
                    content TEXT,
                    created_at TEXT,
                    updated_at TEXT
                );
                """
            elif filename == "event_tracking_models.sql":
                return """
                CREATE TABLE event_tracking_models (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    content TEXT NOT NULL,
                    view_count INTEGER DEFAULT 0,
                    last_viewed_at TEXT
                );
                """
            else:
                # Fall back to a generic schema
                table_name = filename.replace(".sql", "")
                return f"""
                CREATE TABLE {table_name} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'draft',
                    revision INTEGER NOT NULL DEFAULT 1,
                    content TEXT,
                    created_at TEXT,
                    updated_at TEXT
                );
                """
        
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