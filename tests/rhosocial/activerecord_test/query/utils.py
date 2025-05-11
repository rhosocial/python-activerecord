import logging
import os
import tempfile
import time
import uuid
from typing import List, Optional, Type, Tuple, Any, Dict

import pytest

from src.rhosocial.activerecord.backend.config import ConnectionConfig
from src.rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from src.rhosocial.activerecord.interface import IActiveRecord
from tests.rhosocial.activerecord_test.query.fixtures.models import JsonUser
from tests.rhosocial.activerecord_test.utils import load_schema_file, DB_HELPERS, DB_CONFIGS, DBTestConfig


def get_test_db():
    """Create a temporary database for testing."""
    temp_db = tempfile.NamedTemporaryFile(delete=False, suffix='.db')
    temp_db.close()
    db_path = temp_db.name

    # Register cleanup
    pytest.add_cleanup(lambda: os.unlink(db_path) if os.path.exists(db_path) else None)

    return db_path


def generate_unique_test_id():
    """Generate a unique test ID.

    Returns:
        str: Unique test ID
    """
    return f"{int(time.time())}_{uuid.uuid4().hex[:8]}"


def generate_case_id():
    """Generate a unique test case ID.

    Returns:
        str: Unique test case ID
    """
    return uuid.uuid4().hex[:8]


def modify_sqlite_config(config, config_name, test_id, case_id):
    """Modify SQLite connection parameters to give each test case its own connection.

    Args:
        config: Database configuration
        config_name: Configuration name
        test_id: Test ID
        case_id: Test case ID

    Returns:
        dict: Modified configuration
    """
    if config_name == 'file' and 'database' in config:
        if config['database'] != ':memory:':
            config['database'] = f"test_db_{test_id}_{config_name}_{case_id}.sqlite"
    elif config_name == 'memory' and 'database' in config:
        # Use unique URI for in-memory database, including test case ID to ensure each test has its own connection
        config['database'] = f"file:memdb_{test_id}_{case_id}?mode=memory&cache=shared"
        # Add URI option to enable URI filename parsing
        config['uri'] = True  # Set the uri parameter directly in SQLiteConnectionConfig instead of putting it in options
    return config


def generate_test_configs(model_classes: List[Type[IActiveRecord]], configs: Optional[List[str]] = None,
                          test_id: Optional[str] = None):
    """Generate test configuration combinations.

    Args:
        model_classes: List of ActiveRecord model classes
        configs: List of database configuration names. If None, use all available configurations
        test_id: Test ID. If None, generate a new one

    Yields:
        DBTestConfig: Test configuration object
    """
    # If no test ID is provided, generate a new one
    if test_id is None:
        test_id = generate_unique_test_id()

    for backend in DB_HELPERS.keys():
        # Check if all models support the current backend
        supported = True
        for model_class in model_classes:
            if hasattr(model_class, "__supported_backends__"):
                if backend not in model_class.__supported_backends__:
                    supported = False
                    break
        if not supported:
            continue

        # Get all configurations for the current backend
        backend_configs = DB_CONFIGS[backend]
        test_configs = configs if configs else list(backend_configs.keys())

        for config_name in test_configs:
            if config_name in backend_configs:
                # Create a deep copy of the configuration
                config = backend_configs[config_name].copy()
                yield DBTestConfig(backend, config_name, config)


def drop_table_if_exists(model_class, logger=None):
    """Drop table if it exists.

    Args:
        model_class: ActiveRecord model class
        logger: Optional logger instance

    Returns:
        bool: True if successful, False otherwise
    """
    if logger is None:
        logger = logging.getLogger('activerecord_test')

    table_name = model_class.__table_name__
    backend = model_class.__backend__

    try:
        logger.debug(f"Attempting to drop table {table_name} if it exists")
        drop_result = backend.execute(f"DROP TABLE IF EXISTS {table_name}")
        logger.debug(f"Drop table result affected_rows: {drop_result.affected_rows if drop_result else 'N/A'}")

        # For MySQL, ensure the drop operation is completed (flush)
        # if backend.__class__.__name__.lower().find('mysql') >= 0 and hasattr(backend, 'commit_transaction'):
        #     backend.commit_transaction()
        #     logger.debug(f"Committed drop table operation for MySQL")
        return True
    except Exception as e:
        logger.error(f"Error dropping table {table_name}: {e}")
        return False


def verify_table_dropped(model_class, db_config, logger=None):
    """Verify table has been dropped.

    Args:
        model_class: ActiveRecord model class
        db_config: Database configuration
        logger: Optional logger instance

    Returns:
        bool: True if table doesn't exist, False otherwise
    """
    if logger is None:
        logger = logging.getLogger('activerecord_test')

    table_name = model_class.__table_name__
    backend = model_class.__backend__

    try:
        if db_config.backend.startswith('mysql'):
            # For MySQL, check information_schema
            db_name = db_config.config.get('database')
            verify_query = f"SELECT COUNT(*) as count FROM information_schema.tables WHERE table_schema = '{db_name}' AND table_name = '{table_name}'"
            verify_result = backend.execute(verify_query, returning=True)
            result = verify_result.data[0] if verify_result and verify_result.data else None
            count = result.get('count', 0) if result else 0

            if count > 0:
                logger.error(f"CLEANUP FAILED: Table {table_name} still exists after DROP")
                return False
            else:
                logger.debug(f"CLEANUP VERIFIED: Table {table_name} successfully dropped")
                return True
        elif db_config.backend == 'sqlite':
            # For SQLite, try to query the sqlite_master table
            if db_config.config.get('database') != ":memory:":  # Skip for in-memory databases
                verify_query = f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'"
                verify_result = backend.execute(verify_query, returning=True)
                rows = verify_result.data if verify_result else []

                if rows and len(rows) > 0:
                    logger.error(f"CLEANUP FAILED: Table {table_name} still exists after DROP")
                    return False
                else:
                    logger.debug(f"CLEANUP VERIFIED: Table {table_name} successfully dropped")
                    return True
            return True
    except Exception as e:
        logger.error(f"Error verifying table cleanup: {e}")

    return False


def create_table_fixture(model_classes: List[Type[IActiveRecord]], schema_map: Optional[Dict[str, str]] = None):
    """Create a pytest fixture for a group of related tables.

    Args:
        model_classes: List of model classes in dependency order
        schema_map: Optional mapping of table names to schema files
            If not provided, uses {table_name}.sql for each model

    Returns:
        pytest fixture that yields model classes
    """
    schema_map = schema_map or {
        model.__table_name__: f"{model.__table_name__}.sql"
        for model in model_classes
    }
    test_id = generate_unique_test_id()
    logger = logging.getLogger('activerecord_test')

    @pytest.fixture(
        params=list(generate_test_configs(model_classes, test_id=test_id)),
        ids=lambda x: f"{x.backend}-{x.config_name}"
    )
    def _fixture(request) -> Tuple[Type[IActiveRecord], ...]:
        """Create and configure test environment for related tables."""
        db_config = request.param

        # Generate a unique ID for each test case
        case_id = generate_case_id()

        # Create a copy of the configuration to avoid affecting other tests
        config = db_config.config.copy()

        # If SQLite, create a unique connection for each test case
        if db_config.backend == 'sqlite':
            config = modify_sqlite_config(config, db_config.config_name, test_id, case_id)

        # Create configuration objects based on different backend types
        if db_config.backend == 'sqlite':
            # Use SQLiteConnectionConfig to create a configuration
            connection_config = SQLiteConnectionConfig(**config)
            # Create a backend instance and pass in a new connection_config
            backend = db_config.helper["class"](connection_config=connection_config)
        else:
            # Other database backends use the generic ConnectionConfig
            connection_config = ConnectionConfig(**config)
            # Create a backend instance and pass in a generic connection_config
            backend = db_config.helper["class"](connection_config=connection_config)

        logger.debug(f"db_config: {config}, case_id: {case_id}")

        # Configure all models to use the same backend instance
        for model_class in model_classes:
            model_class.__connection_config__ = connection_config
            model_class.__backend_class__ = db_config.helper["class"]
            model_class.__backend__ = backend

        # First drop any existing tables in reverse dependency order
        for model_class in reversed(model_classes):
            if not drop_table_if_exists(model_class, logger):
                raise RuntimeError(f"Error dropping table {model_class.__table_name__}")

        # Create tables in dependency order
        for model_class in model_classes:
            table_name = model_class.__table_name__
            try:
                schema = load_schema_file(
                    model_class,
                    db_config.backend,
                    schema_map[table_name]
                )
                logger.debug(f"Creating table {table_name} with schema")
                result = model_class.__backend__.execute(schema)

                # Verify table creation success
                if result is None:
                    raise RuntimeError(f"Failed to create table {table_name}: No result returned")

                logger.debug(f"Table {table_name} created successfully, affected_rows: {result.affected_rows}")
            except Exception as e:
                logger.error(f"Error creating table {table_name}: {e}")
                # Clean up resources even if table creation fails
                for cleanup_model in reversed(model_classes):
                    try:
                        drop_table_if_exists(cleanup_model, logger)
                    except:
                        pass

                try:
                    backend.disconnect()
                except:
                    pass

                for model_class in model_classes:
                    model_class.__backend__ = None

                raise  # Re-raise the exception to fail the test

        yield tuple(model_classes)

        # Cleanup tables in reverse order
        for model_class in reversed(model_classes):
            try:
                # Ensure any pending transactions are finished before dropping the table
                if hasattr(model_class.__backend__, 'commit_transaction'):
                    try:
                        logger.debug(f"Committing any pending transactions before cleanup")
                        model_class.__backend__.commit_transaction()
                    except Exception as e:
                        logger.error(f"Error committing pending transactions: {e}")
                        # Try to rollback if commit fails
                        if hasattr(model_class.__backend__, 'rollback_transaction'):
                            try:
                                model_class.__backend__.rollback_transaction()
                                logger.debug(f"Rolled back pending transactions")
                            except Exception as rollback_err:
                                logger.error(f"Error rolling back transactions: {rollback_err}")
                                # raise
                        # raise

                drop_table_if_exists(model_class, logger)
                verify_table_dropped(model_class, db_config, logger)
            except Exception as e:
                logger.error(f"Error during cleanup for table {model_class.__table_name__}: {e}")
                # raise

        # Disconnect from the database
        try:
            logger.debug(f"Disconnecting database connection")
            backend.disconnect()
            logger.debug(f"Database disconnected successfully")
        except Exception as e:
            logger.error(f"Error disconnecting from database: {e}")
            raise

        # Clear backend reference
        for model_class in model_classes:
            model_class.__backend__ = None

    return _fixture


def create_order_fixtures():
    """Create test fixtures for order-related tables.

    Creates tables in dependency order:
    1. users (referenced by orders)
    2. orders (referenced by order_items)
    3. order_items
    """
    from .fixtures.models import User, Order, OrderItem
    model_classes = [User, Order, OrderItem]

    # Define schema mapping
    schema_map = {
        User.__table_name__: "users.sql",
        Order.__table_name__: "orders.sql",
        OrderItem.__table_name__: "order_items.sql"
    }

    return create_table_fixture(model_classes, schema_map)


def create_blog_fixtures():
    """Create blog-related table fixtures.

    Creates tables in dependency order:
    1. users
    2. posts (depends on users)
    3. comments (depends on users and posts)
    """
    from .fixtures.models import User, Post, Comment
    model_classes = [User, Post, Comment]

    # Define schema mapping
    schema_map = {
        User.__table_name__: "users.sql",
        Post.__table_name__: "posts.sql",
        Comment.__table_name__: "comments.sql"
    }

    return create_table_fixture(model_classes, schema_map)


def create_order_fixture_factory(User: Type[IActiveRecord],
                                 OrderItem: Type[IActiveRecord],
                                 base_schema_map: Optional[Dict[str, str]] = None):
    """Create a factory function for order-related fixtures with different Order variants.

    Args:
        User: User model class
        OrderItem: OrderItem model class
        base_schema_map: Optional base schema mapping

    Returns:
        Function that creates fixtures for specific Order variants
    """
    base_schema_map = base_schema_map or {
        User.__table_name__: "users.sql",
        "orders": "orders.sql",  # Generic schema for all Order variants
        OrderItem.__table_name__: "order_items.sql"
    }

    def create_order_fixture(Order: Type[IActiveRecord]) -> Any:
        """Create fixture for specific Order variant.

        Args:
            Order: Order model class variant to use

        Returns:
            pytest fixture that yields (User, Order, OrderItem)
        """
        model_classes = [User, Order, OrderItem]
        schema_map = base_schema_map.copy()
        schema_map[Order.__table_name__] = base_schema_map["orders"]
        return create_table_fixture(model_classes, schema_map)

    return create_order_fixture


def create_json_test_fixtures():
    """Create test fixtures specifically for JSON functionality tests.

    This creates a separate json_users table that won't interfere with
    other tests using the standard users table.

    Returns:
        pytest fixture that yields JsonUser model
    """
    model_classes = [JsonUser]

    # Define schema mapping
    schema_map = {
        JsonUser.__table_name__: "json_users.sql"
    }

    return create_table_fixture(model_classes, schema_map)


def setup_order_fixtures():
    """Set up fixture factory for order-related tests.

    Returns dictionary of fixtures for different Order variants.
    """
    from .fixtures.models import (
        User, OrderItem,
        Order, OrderWithCustomCache,
        OrderWithLimitedCache, OrderWithComplexCache
    )

    # Create fixture factory
    create_fixture = create_order_fixture_factory(User, OrderItem)

    return {
        'basic_order': create_fixture(Order),
        'custom_cache_order': create_fixture(OrderWithCustomCache),
        'limited_cache_order': create_fixture(OrderWithLimitedCache),
        'complex_cache_order': create_fixture(OrderWithComplexCache)
    }


def get_mysql_version(request):
    """Get MySQL version from test request.

    Extract MySQL version information from the test name.

    Args:
        request: pytest request object

    Returns:
        tuple: MySQL version as (major, minor, patch) or None if not MySQL or version can't be determined
    """
    if not hasattr(request, 'node'):
        return None

    # Extract backend name from test name (e.g., 'mysql80-memory-Test.test_method')
    backend_name = request.node.name.split('-')[0]

    if not backend_name.startswith('mysql'):
        return None

    # Extract version from backend name
    if backend_name == 'mysql56':
        return (5, 6, 0)
    elif backend_name == 'mysql57':
        return (5, 7, 0)
    elif backend_name == 'mysql8' or backend_name == 'mysql80':
        return (8, 0, 0)
    elif backend_name == 'mysql83':
        return (8, 3, 0)

    # If we can't determine the version from the name,
    # try to get it from the backend directly
    try:
        if hasattr(request, 'getfixturevalue'):
            model_classes = request.getfixturevalue('order_fixtures')
            if model_classes and len(model_classes) > 0:
                model_class = model_classes[0]
                if hasattr(model_class, '__backend__') and model_class.__backend__:
                    return model_class.__backend__.get_server_version()
    except:
        pass

    return None


def create_tree_fixtures():
    """Create test fixtures for tree structure (for recursive CTEs).

    Returns:
        pytest fixture that yields Node model
    """
    from .fixtures.cte_models import Node
    model_classes = [Node]

    # Define schema mapping
    schema_map = {
        Node.__table_name__: "nodes.sql"
    }

    # Use the pattern in create_table_fixture to create the fixture
    # but make sure it yields the Node model directly, not a tuple
    return create_table_fixture(model_classes, schema_map)


def create_combined_fixtures():
    """Create combined test fixtures for both order and blog tests.

    Creates tables in dependency order:
    1. users (shared by orders, posts, and comments)
    2. orders (referenced by order_items)
    3. order_items
    4. posts (depends on users)
    5. comments (depends on users and posts)

    Returns:
        pytest fixture for (User, Order, OrderItem, Post, Comment)
    """
    from .fixtures.models import User, Order, OrderItem, Post, Comment
    model_classes = [User, Order, OrderItem, Post, Comment]

    # Define schema mapping
    schema_map = {
        User.__table_name__: "users.sql",
        Order.__table_name__: "orders.sql",
        OrderItem.__table_name__: "order_items.sql",
        Post.__table_name__: "posts.sql",
        Comment.__table_name__: "comments.sql"
    }

    return create_table_fixture(model_classes, schema_map)