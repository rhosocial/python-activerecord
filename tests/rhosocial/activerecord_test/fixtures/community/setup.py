# tests/rhosocial/activerecord_test/fixtures/community/setup.py
from src.activerecord.backend.base import StorageBackend


def create_community_tables(backend: StorageBackend) -> None:
    """创建用户社区相关表"""
    # 创建表的SQL语句...
    pass

def drop_community_tables(backend: StorageBackend) -> None:
    """删除用户社区相关表"""
    # 删除表的SQL语句...
    pass