import pytest
from src.rhosocial.activerecord.backend.errors import ConnectionError
from src.rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend


def test_connect_success(db_path):
    """测试连接成功"""
    backend = SQLiteBackend(database=db_path)
    backend.connect()
    assert backend._connection is not None
    backend.disconnect()

def test_connect_invalid_path():
    """测试无效路径连接失败"""
    backend = SQLiteBackend(database="/invalid/path/db.sqlite")
    with pytest.raises(ConnectionError):
        backend.connect()

def test_disconnect(db):
    """测试断开连接"""
    db.disconnect()
    assert db._connection is None
    assert db._cursor is None

def test_ping(db):
    """测试ping功能"""
    assert db.ping() is True
    db.disconnect()
    assert db.ping(reconnect=False) is False
    assert db.ping(reconnect=True) is True