# tests/providers/scenarios.py
"""SQLite后端的简化测试场景配置映射表"""

import os
import tempfile
from typing import Dict, Any, Tuple, Type
from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig

# 场景名 -> 配置字典 的映射表（只关心SQLite）
SCENARIO_MAP: Dict[str, Dict[str, Any]] = {}

def register_scenario(name: str, config: Dict[str, Any]):
    """注册SQLite测试场景"""
    SCENARIO_MAP[name] = config

def get_scenario(name: str) -> Tuple[Type[SQLiteBackend], SQLiteConnectionConfig]:
    """
    Retrieves the backend class and a connection configuration object for a given
    scenario name. This is called by the provider to set up the database for a test.
    """
    if name not in SCENARIO_MAP:
        name = "memory"  # Fallback to the default in-memory scenario if not found.
    
    # Unpack the configuration dictionary into the dataclass constructor.
    config = SQLiteConnectionConfig(**SCENARIO_MAP[name])
    return SQLiteBackend, config

def get_enabled_scenarios() -> Dict[str, Any]:
    """
    Returns the map of all currently enabled scenarios. The testsuite's conftest
    uses this to parameterize the tests, causing them to run for each scenario.
    """
    return SCENARIO_MAP

def _register_default_scenarios():
    """
    Registers the default scenarios supported by this SQLite backend.
    More complex scenarios (e.g., for performance or concurrency testing)
    can be added here, often controlled by environment variables.
    """
    # The default, fastest scenario using an in-memory SQLite database.
    register_scenario("memory", {
        "database": ":memory:",
    })
    
    # 临时文件数据库（持久化测试）
    if os.getenv("TEST_SQLITE_FILE", "false").lower() == "true":
        temp_dir = tempfile.gettempdir()
        register_scenario("tempfile", {
            "database": os.path.join(temp_dir, "test_activerecord.sqlite"),
            "delete_on_close": True
        })
    
    # 调试模式（显示SQL语句）。注意：'echo' 和 'auto_commit' 不是 SQLiteConnectionConfig 的参数。
    # 要启用 SQL 回显，请配置 'rhosocial.activerecord' 的日志级别。
    if os.getenv("TEST_SQLITE_DEBUG", "false").lower() == "true":
        register_scenario("debug", {
            "database": ":memory:",
        })
    
    # 性能测试模式（优化设置）。注意：'echo' 不是 SQLiteConnectionConfig 的参数。
    if os.getenv("TEST_SQLITE_PERFORMANCE", "false").lower() == "true":
        register_scenario("performance", {
            "database": ":memory:",
            "pragmas": {
                "synchronous": "OFF",
                "journal_mode": "MEMORY",
                "temp_store": "MEMORY",
                "cache_size": 10000
            }
        })
    
    # 并发测试模式（WAL模式）。注意：'echo' 和 'auto_commit' 是不是 SQLiteConnectionConfig 的参数。
    if os.getenv("TEST_SQLITE_CONCURRENT", "false").lower() == "true":
        register_scenario("concurrent", {
            "database": "test_concurrent.sqlite",
            "delete_on_close": True,
            "pragmas": {
                "journal_mode": "WAL",
                "synchronous": "NORMAL"
            }
        })

# 初始化时注册默认场景
_register_default_scenarios()