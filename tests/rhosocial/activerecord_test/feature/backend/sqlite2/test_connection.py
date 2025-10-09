# tests/rhosocial/activerecord_test/feature/backend/sqlite2/test_connection.py
import pytest
from rhosocial.activerecord.backend.errors import ConnectionError
from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend


def test_connect_success(db_path):
    """Test successful connection"""
    backend = SQLiteBackend(database=db_path)
    backend.connect()
    assert backend._connection is not None
    backend.disconnect()


def test_connect_invalid_path():
    """Test connection failure with invalid path"""
    backend = SQLiteBackend(database="/invalid/path/db.sqlite")
    with pytest.raises(ConnectionError):
        backend.connect()


def test_disconnect(db):
    """Test disconnection"""
    db.disconnect()
    assert db._connection is None
    assert db._cursor is None


def test_ping(db):
    """Test ping functionality"""
    assert db.ping() is True
    db.disconnect()
    assert db.ping(reconnect=False) is False
    assert db.ping(reconnect=True) is True
