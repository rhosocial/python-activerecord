import inspect
import os
from typing import Type, List, Optional, Dict

import pytest

from src.rhosocial.activerecord.interface import IActiveRecord
from src.rhosocial.activerecord.backend.typing import ConnectionConfig
from src.rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend

# 存储后端助手映射
DB_HELPERS = {
    'sqlite': {
        "class": SQLiteBackend,
    }
}

# 数据库配置
DB_CONFIGS = {
    "sqlite": {
        "memory": {
            "database": ":memory:",
        },
        "file": {
            "database": "test_db.sqlite",
        },
    },
    "mysql": {
        "local": {
            "host": "localhost",
            "port": 3306,
            "user": "test_user",
            "password": "test_password",
            "database": "test_db",
        },
    },
    "postgresql": {
        "local": {
            "host": "localhost",
            "port": 5432,
            "user": "test_user",
            "password": "test_password",
            "database": "test_db",
        },
    },
}

def get_backend_name(model_class: Type[IActiveRecord]) -> str:
    """获取模型类使用的后端名称"""
    return model_class.__backend__.__class__.__name__.lower().replace('backend', '')


def load_schema_file(model_class: Type[IActiveRecord], backend: str, filename: str) -> str:
    """从文件加载指定数据库的表结构定义

    Args:
        model_class: ActiveRecord 模型类，用于定位 schema 文件
        backend: 数据库后端名称 (sqlite, mysql, postgresql)
        filename: SQL文件名

    Returns:
        str: SQL语句内容
    """
    # 获取模型类所在的文件路径
    model_file = inspect.getfile(model_class)
    model_dir = os.path.dirname(os.path.abspath(model_file))

    # schema 文件路径相对于模型文件所在目录
    schema_path = os.path.join(model_dir, 'schema', backend, filename)

    with open(schema_path, 'r', encoding='utf-8') as f:
        return f.read()


class DBTestConfig:
    """数据库测试配置类"""
    def __init__(self, backend: str, config_name: str):
        self.backend = backend
        self.config_name = config_name

    def __str__(self) -> str:
        return f"{self.backend}, {self.config_name}"

    def __repr__(self) -> str:
        return self.__str__()

    @property
    def config(self) -> Dict:
        return DB_CONFIGS[self.backend][self.config_name]

    @property
    def helper(self):
        return DB_HELPERS[self.backend]


def generate_test_configs(model_class, configs):
    """生成测试配置组合"""
    for backend in DB_HELPERS.keys():
        # 检查模型是否支持当前后端
        if hasattr(model_class, "__supported_backends__"):
            if backend not in model_class.__supported_backends__:
                continue

        # 获取当前后端的所有配置
        backend_configs = DB_CONFIGS[backend]
        test_configs = configs if configs else list(backend_configs.keys())

        for config_name in test_configs:
            if config_name in backend_configs:
                yield DBTestConfig(backend, config_name)

def create_active_record_fixture(model_class: Type[IActiveRecord],
                                 configs: Optional[List[str]] = None):
    """创建特定 ActiveRecord 类的夹具工厂函数"""

    @pytest.fixture(params=list(generate_test_configs(model_class, configs)), ids=lambda x: f"{x.backend}-{x.config_name}")
    def _fixture(request):
        """实际的夹具函数"""
        db_config = request.param

        # 配置模型类
        model_class.configure(
            config=ConnectionConfig(**db_config.config),
            backend_class=db_config.helper["class"]
        )

        # 创建表结构
        schema = load_schema_file(
            model_class,
            db_config.backend,
            f"{model_class.__table_name__}.sql"
        )
        result = model_class.__backend__.execute(schema)

        # 验证建表成功
        assert result is not None
        assert result.affected_rows == -1

        yield model_class

        # 清理
        model_class.__backend__.execute(f"DROP TABLE IF EXISTS {model_class.__table_name__}")
        model_class.__backend__ = None

    return _fixture
