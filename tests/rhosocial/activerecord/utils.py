import inspect
import logging
import os
import sys
from typing import Type, List, Optional, Dict

import pytest

from src.rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from src.rhosocial.activerecord.backend.typing import ConnectionConfig
from src.rhosocial.activerecord.interface import IActiveRecord

# Database backend helper mapping
DB_HELPERS = {
    'sqlite': {
        "class": SQLiteBackend,
    },
}

# Database configurations
DB_CONFIGS = {
    "sqlite": {
        "memory": {
            "database": ":memory:",
        },
        "file": {
            "database": "test_db.sqlite",
            "delete_on_close": True,
        },
    },
    # "postgresql": {
    #     "local": {
    #         "host": "localhost",
    #         "port": 5432,
    #         "user": "test_user",
    #         "password": "test_password",
    #         "database": "test_db",
    #     },
    # },
}

# Setup logger
logger = logging.getLogger('activerecord_test')
logger.setLevel(logging.DEBUG)
handler = logging.StreamHandler(sys.stdout)
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)


def get_backend_name(model_class: Type[IActiveRecord]) -> str:
    """Get the backend name used by the model class"""
    return model_class.__backend__.__class__.__name__.lower().replace('backend', '')


def load_schema_file(model_class: Type[IActiveRecord], backend: str, filename: str) -> str:
    """Load the table schema definition file for the specified database

    Args:
        model_class: ActiveRecord model class, used to locate the schema file
        backend: Database backend name (sqlite, mysql, postgresql)
        filename: SQL file name

    Returns:
        str: SQL statement content
    """
    # Get the file path of the model class
    model_file = inspect.getfile(model_class)
    model_dir = os.path.dirname(os.path.abspath(model_file))

    # Schema file path relative to the model file directory
    schema_path = os.path.join(model_dir, 'schema', backend, filename)

    with open(schema_path, 'r', encoding='utf-8') as f:
        return f.read()


class DBTestConfig:
    """Database test configuration class"""

    def __init__(self, backend: str, config_name: str, custom_config: Optional[Dict] = None):
        self.backend = backend
        self.config_name = config_name
        self._custom_config = custom_config

    def __str__(self) -> str:
        return f"{self.backend}, {self.config_name}"

    def __repr__(self) -> str:
        return self.__str__()

    @property
    def config(self) -> Dict:
        # If a custom configuration is provided, use it instead of getting from DB_CONFIGS
        if self._custom_config is not None:
            return self._custom_config
        return DB_CONFIGS[self.backend][self.config_name]

    @property
    def helper(self):
        return DB_HELPERS[self.backend]


def generate_test_configs(model_class, configs):
    """Generate test configuration combinations"""
    for backend in DB_HELPERS.keys():
        # Check if the model supports the current backend
        if hasattr(model_class, "__supported_backends__"):
            if backend not in model_class.__supported_backends__:
                continue

        # Get all configurations for the current backend
        backend_configs = DB_CONFIGS[backend]
        test_configs = configs if configs else list(backend_configs.keys())

        for config_name in test_configs:
            if config_name in backend_configs:
                yield DBTestConfig(backend, config_name)


def create_active_record_fixture(model_class: Type[IActiveRecord],
                                 configs: Optional[List[str]] = None):
    """Create a fixture factory function for a specific ActiveRecord class"""

    @pytest.fixture(params=list(generate_test_configs(model_class, configs)),
                    ids=lambda x: f"{x.backend}-{x.config_name}", scope="function")
    def _fixture(request):
        """Actual fixture function"""
        db_config = request.param
        table_name = model_class.__table_name__

        # Configure the model class
        model_class.configure(
            config=ConnectionConfig(**db_config.config),
            backend_class=db_config.helper["class"]
        )
        logger.debug(f"Test fixture setup for {model_class.__name__} with config: {db_config}")

        # ENHANCEMENT 1: Drop table if exists before creating it
        try:
            logger.debug(f"Attempting to drop table {table_name} if it exists")
            drop_result = model_class.__backend__.execute(f"DROP TABLE IF EXISTS {table_name}")
            logger.debug(f"Drop table result affected_rows: {drop_result.affected_rows if drop_result else 'N/A'}")

            # For MySQL, ensure the drop operation is completed (flush)
            if db_config.backend.startswith('mysql') and hasattr(model_class.__backend__, 'commit'):
                model_class.__backend__.commit()
                logger.debug(f"Committed drop table operation for MySQL")
        except Exception as e:
            logger.error(f"Error dropping table {table_name}: {e}")
            # Continue even if drop fails - the create table might still work

        # Create table structure
        try:
            schema = load_schema_file(
                model_class,
                db_config.backend,
                f"{table_name}.sql"
            )
            logger.debug(f"Creating table {table_name} with schema")
            result = model_class.__backend__.execute(schema)

            # Verify table creation success
            assert result is not None
            # Different databases return different affected_rows for DDL statements
            # MySQL usually returns 0, SQLite might return -1
            # Just check that we have a result object, don't verify specific affected_rows value
            logger.debug(f"Table creation result affected_rows: {result.affected_rows}")
            logger.debug(f"Table {table_name} created successfully")
        except Exception as e:
            logger.error(f"Error creating table {table_name}: {e}")
            # Clean up resources even if table creation fails
            try:
                model_class.__backend__.disconnect()
            except:
                pass
            model_class.__backend__ = None
            raise  # Re-raise the exception to fail the test

        yield model_class

        # ENHANCEMENT 2: Improved cleanup process with logging
        try:
            # Ensure any pending transactions are finished before dropping the table
            # This helps with MySQL where open transactions can prevent cleanup
            try:
                if hasattr(model_class.__backend__, 'commit'):
                    logger.debug(f"Committing any pending transactions before cleanup")
                    model_class.__backend__.commit()
            except Exception as e:
                logger.error(f"Error committing pending transactions: {e}")
                # Try to rollback if commit fails
                if hasattr(model_class.__backend__, 'rollback'):
                    try:
                        model_class.__backend__.rollback()
                        logger.debug(f"Rolled back pending transactions")
                    except Exception as rollback_err:
                        logger.error(f"Error rolling back transactions: {rollback_err}")

            logger.debug(f"Cleanup: Dropping table {table_name}")
            cleanup_result = model_class.__backend__.execute(f"DROP TABLE IF EXISTS {table_name}")
            logger.debug(
                f"Cleanup drop table result affected_rows: {cleanup_result.affected_rows if cleanup_result else 'N/A'}")

            # Verify table doesn't exist anymore (using database-specific approach)
            if db_config.backend.startswith('mysql'):
                try:
                    # For MySQL, check information_schema
                    db_name = db_config.config.get('database')
                    verify_query = f"SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = '{db_name}' AND table_name = '{table_name}'"
                    verify_result = model_class.__backend__.execute(verify_query)
                    rows = verify_result.fetch_all()
                    if rows and rows[0][0] > 0:
                        logger.error(f"CLEANUP FAILED: Table {table_name} still exists after DROP")
                    else:
                        logger.debug(f"CLEANUP VERIFIED: Table {table_name} successfully dropped")
                except Exception as e:
                    logger.error(f"Error verifying table cleanup: {e}")
            elif db_config.backend == 'sqlite':
                try:
                    # For SQLite, try to query the sqlite_master table
                    if db_config.config.get('database') != ":memory:":  # Skip for in-memory databases
                        verify_query = f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'"
                        verify_result = model_class.__backend__.execute(verify_query)
                        rows = verify_result.fetch_all()
                        if rows and len(rows) > 0:
                            logger.error(f"CLEANUP FAILED: Table {table_name} still exists after DROP")
                        else:
                            logger.debug(f"CLEANUP VERIFIED: Table {table_name} successfully dropped")
                except Exception as e:
                    logger.error(f"Error verifying table cleanup: {e}")
        except Exception as e:
            logger.error(f"Error during table cleanup: {e}")

        # Disconnect from the database
        try:
            logger.debug(f"Disconnecting database connection")
            model_class.__backend__.disconnect()
            logger.debug(f"Database disconnected successfully")
        except Exception as e:
            logger.error(f"Error disconnecting from database: {e}")
            raise

        model_class.__backend__ = None

    return _fixture