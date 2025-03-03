import os

import pytest
from typing import Generator
from src.rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend

@pytest.fixture(params=["memory", "file"])
def db_path(request) -> str:
    """返回测试数据库路径"""
    if request.param == "memory":
        return ":memory:"  # 使用内存数据库便于测试
    elif request.param == "file":
        return "tests.activerecord.implementations.sqlite.sqlite"

@pytest.fixture
def db(db_path) -> Generator[SQLiteBackend, None, None]:
    """提供数据库连接"""
    backend = SQLiteBackend(database=db_path)
    backend.connect()
    yield backend
    backend.disconnect()

    # 测试结束后清理文件
    if db_path != ":memory:" and os.path.exists(db_path):
        os.remove(db_path)

@pytest.fixture
def setup_test_table(db):
    """创建测试表"""
    db.execute("""
        CREATE TABLE test_table (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            age INTEGER,
            created_at DATETIME
        )
    """)
    yield
    db.execute("DROP TABLE IF EXISTS test_table")