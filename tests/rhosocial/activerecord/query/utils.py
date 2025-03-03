import logging
import time
import uuid
from typing import List, Optional, Type, Tuple, Any, Dict

import pytest

from src.rhosocial.activerecord.backend.typing import ConnectionConfig
from src.rhosocial.activerecord.interface import IActiveRecord
from tests.rhosocial.activerecord.utils import load_schema_file, DB_HELPERS, DB_CONFIGS, DBTestConfig


def generate_unique_test_id():
    """生成唯一的测试ID

    Returns:
        str: 唯一的测试ID
    """
    return f"{int(time.time())}_{uuid.uuid4().hex[:8]}"

def generate_case_id():
    """生成唯一的测试用例ID

    Returns:
        str: 唯一的测试用例ID
    """
    return uuid.uuid4().hex[:8]

def modify_sqlite_config(config, config_name, test_id, case_id):
    """为SQLite配置修改数据库连接参数，使每个测试用例有自己的连接

    Args:
        config: 数据库配置
        config_name: 配置名称
        test_id: 测试ID
        case_id: 测试用例ID

    Returns:
        dict: 修改后的配置
    """
    if config_name == 'file' and 'database' in config:
        if config['database'] != ':memory:':
            config['database'] = f"test_db_{test_id}_{config_name}_{case_id}.sqlite"
    elif config_name == 'memory' and 'database' in config:
        # 为内存数据库使用唯一URI，加入测试用例ID确保每个测试有自己的连接
        config['database'] = f"file:memdb_{test_id}_{case_id}?mode=memory&cache=shared"
        # 添加URI选项以启用URI文件名解析
        if 'options' not in config:
            config['options'] = {}
        config['options']['uri'] = True
    return config

def generate_test_configs(model_classes: List[Type[IActiveRecord]], configs: Optional[List[str]] = None, test_id: Optional[str] = None):
    """生成测试配置组合

    Args:
        model_classes: ActiveRecord模型类列表
        configs: 数据库配置名列表。如果为None，使用所有可用配置

    Yields:
        DBTestConfig: 测试配置对象
    """
    # 如果没有提供测试ID，则生成一个新的
    if test_id is None:
        test_id = generate_unique_test_id()

    for backend in DB_HELPERS.keys():
        # 检查所有模型是否都支持当前后端
        supported = True
        for model_class in model_classes:
            if hasattr(model_class, "__supported_backends__"):
                if backend not in model_class.__supported_backends__:
                    supported = False
                    break
        if not supported:
            continue

        # 获取当前后端的所有配置
        backend_configs = DB_CONFIGS[backend]
        test_configs = configs if configs else list(backend_configs.keys())

        for config_name in test_configs:
            if config_name in backend_configs:
                # 创建配置的深拷贝
                config = backend_configs[config_name].copy()

                # 为SQLite数据库创建唯一标识
                if backend == 'sqlite':
                    if config_name == 'file' and 'database' in config:
                        if config['database'] != ':memory:':
                            config['database'] = f"test_db_{test_id}_{config_name}.sqlite"
                    elif config_name == 'memory' and 'database' in config:
                        # 为内存数据库使用唯一URI
                        config['database'] = f"file:memdb_{test_id}?mode=memory&cache=shared"
                        # 添加URI选项以启用URI文件名解析
                        if 'options' not in config:
                            config['options'] = {}
                        config['options']['uri'] = True

                yield DBTestConfig(backend, config_name, config)


def create_order_fixtures():
    """创建订单相关的多表测试夹具

    按照外键依赖关系创建表：
    1. users (被orders引用)
    2. orders (被order_items引用)
    3. order_items
    """
    from .fixtures.models import User, Order, OrderItem
    model_classes = [User, Order, OrderItem]
    test_id = generate_unique_test_id()

    @pytest.fixture(
        params=list(generate_test_configs(model_classes, test_id=test_id)),
        ids=lambda x: f"{x.backend}-{x.config_name}"
    )
    def _fixture(request) -> Tuple[Type[User], Type[Order], Type[OrderItem]]:
        """创建和配置订单相关表的测试环境"""
        db_config = request.param

        # 为每个测试用例生成唯一ID
        case_id = generate_case_id()

        # 创建配置副本，以便修改不影响其他测试
        config = db_config.config.copy()

        # 如果是SQLite，为每个测试用例创建唯一连接
        if db_config.backend == 'sqlite':
            config = modify_sqlite_config(config, db_config.config_name, test_id, case_id)

        # 创建后端实例
        backend = db_config.helper["class"](**config)
        logging.log(logging.DEBUG, f"db_config: {config}, case_id: {case_id}")

        # 配置所有模型使用相同的后端实例
        for model_class in model_classes:
            model_class.__connection_config__ = ConnectionConfig(**config)
            model_class.__backend_class__ = db_config.helper["class"]
            model_class.__backend__ = backend
            # result = model_class.backend().execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name= ?;", (model_class.__table_name__, ), returning=True)
            # logging.log(logging.DEBUG, f"Check whether if the {model_class.__table_name__} exists: {result}")
            # model_class.backend().execute(f"DROP TABLE IF EXISTS {model_class.__table_name__}")

        # 按依赖顺序创建表
        for model_class in model_classes:
            schema = load_schema_file(
                model_class,
                db_config.backend,
                f"{model_class.__table_name__}.sql"
            )
            result = model_class.__backend__.execute(schema)
            # 验证表创建结果
            if result is None or result.affected_rows != -1:  # SQLite创建表成功时返回-1
                raise RuntimeError(f"Failed to create table {model_class.__table_name__}")

        yield User, Order, OrderItem

        # 按相反顺序清理表
        for model_class in reversed(model_classes):
            model_class.__backend__.execute(f"DROP TABLE IF EXISTS {model_class.__table_name__}")
            model_class.__backend__.disconnect()
            model_class.__backend__ = None

    return _fixture


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

    @pytest.fixture(
        params=list(generate_test_configs(model_classes, test_id=test_id)),
        ids=lambda x: f"{x.backend}-{x.config_name}"
    )
    def _fixture(request) -> Tuple[Type[IActiveRecord], ...]:
        """Create and configure test environment for related tables."""
        db_config = request.param

        # 为每个测试用例生成唯一ID
        case_id = generate_case_id()

        # 创建配置副本，以便修改不影响其他测试
        config = db_config.config.copy()

        # 如果是SQLite，为每个测试用例创建唯一连接
        if db_config.backend == 'sqlite':
            config = modify_sqlite_config(config, db_config.config_name, test_id, case_id)

        # Create backend instance
        backend = db_config.helper["class"](**config)
        logging.log(logging.DEBUG, f"db_config: {config}")

        # Configure all models to use the same backend instance
        for model_class in model_classes:
            model_class.__connection_config__ = ConnectionConfig(**config)
            model_class.__backend_class__ = db_config.helper["class"]
            model_class.__backend__ = backend
            # result = model_class.backend().execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name= ?;", (model_class.__table_name__, ), returning=True)
            # logging.log(logging.DEBUG, f"Check whether if the {model_class.__table_name__} exists: {result}")
            # model_class.backend().execute(f"DROP TABLE IF EXISTS {model_class.__table_name__}")

        # Create tables in dependency order
        for model_class in model_classes:
            schema = load_schema_file(
                model_class,
                db_config.backend,
                schema_map[model_class.__table_name__]
            )
            result = model_class.__backend__.execute(schema)
            # Verify table creation
            if result is None or result.affected_rows != -1:
                raise RuntimeError(f"Failed to create table {model_class.__table_name__}")

        yield tuple(model_classes)

        # Cleanup tables in reverse order
        for model_class in reversed(model_classes):
            model_class.__backend__.execute(f"DROP TABLE IF EXISTS {model_class.__table_name__}")
            model_class.__backend__.disconnect()
            model_class.__backend__ = None


    return _fixture


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

    def create_order_fixture(Order: Type[IActiveRecord]) -> Any:
        """Create fixture for specific Order variant.

        Args:
            Order: Order model class variant to use

        Returns:
            pytest fixture that yields (User, Order, OrderItem)
        """
        model_classes = [User, Order, OrderItem]
        schema_map = base_schema_map or {
            User.__table_name__: "users.sql",
            Order.__table_name__: "orders.sql",  # All Order variants use same schema
            OrderItem.__table_name__: "order_items.sql"
        }
        return create_table_fixture(model_classes, schema_map)

    return create_order_fixture


# Create fixture factory for order-related tests
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

# Example usage in tests:
# from .utils import setup_order_fixtures
# order_fixtures = setup_order_fixtures(User, OrderItem)
#
# def test_basic_order(order_fixtures['basic_order']):
#     User, Order, OrderItem = order_fixtures['basic_order']
#     ...
#
# def test_custom_cache(order_fixtures['custom_cache_order']):
#     User, Order, OrderItem = order_fixtures['custom_cache_order']
#     ...

def create_blog_fixtures():
    """Create blog-related table fixtures.

    Creates tables in dependency order:
    1. users
    2. posts (depends on users)
    3. comments (depends on users and posts)
    """
    from .fixtures.models import User, Post, Comment
    model_classes = [User, Post, Comment]
    test_id = generate_unique_test_id()

    @pytest.fixture(params=list(generate_test_configs(model_classes)),
                    ids=lambda x: f"{x.backend}-{x.config_name}", scope="function")
    def _fixture(request) -> Tuple[Type[User], Type[Post], Type[Comment]]:
        """Create and configure blog test environment."""
        db_config = request.param

        # 为每个测试用例生成唯一ID
        case_id = generate_case_id()

        # 创建配置副本，以便修改不影响其他测试
        config = db_config.config.copy()

        # 如果是SQLite，为每个测试用例创建唯一连接
        if db_config.backend == 'sqlite':
            config = modify_sqlite_config(config, db_config.config_name, test_id, case_id)

        # Create backend instance
        backend = db_config.helper["class"](**config)
        logging.log(logging.DEBUG, f"Test ID: {test_id}, db_config: {config}")

        # Configure all models to use the same backend instance
        for model_class in model_classes:
            model_class.__connection_config__ = ConnectionConfig(**config)
            model_class.__backend_class__ = db_config.helper["class"]
            model_class.__backend__ = backend
            # result = model_class.backend().execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name= ?;", (model_class.__table_name__, ), returning=True)
            # logging.log(logging.DEBUG, f"Check whether if the {model_class.__table_name__} exists: {result}")
            # model_class.backend().execute(f"DROP TABLE IF EXISTS {model_class.__table_name__}")

        # Create tables in dependency order
        table_schemas = {
            User: "users.sql",
            Post: "posts.sql",
            Comment: "comments.sql"
        }

        for model_class in model_classes:
            schema = load_schema_file(
                model_class,
                db_config.backend,
                table_schemas[model_class]
            )
            result = model_class.__backend__.execute(schema)
            if result is None or result.affected_rows != -1:
                raise RuntimeError(f"Failed to create table {model_class.__table_name__}")

        yield User, Post, Comment

        # Cleanup tables in reverse order
        for model_class in reversed(model_classes):
            model_class.__backend__.execute(f"DROP TABLE IF EXISTS {model_class.__table_name__}")
            model_class.__backend__.disconnect()
            model_class.__backend__ = None


    return _fixture