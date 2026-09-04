# tests/rhosocial/activerecord_test/feature/backend/adapters/test_adapters_backend.py
"""Offline adapter round-trip coverage for the SQLite backend."""
import uuid
import pytest

from rhosocial.activerecord.backend.impl.sqlite.adapters import (
    SQLiteBlobAdapter,
    SQLiteJSONAdapter,
    SQLiteUUIDAdapter,
)


@pytest.fixture
def blob(): return SQLiteBlobAdapter()
@pytest.fixture
def json_a(): return SQLiteJSONAdapter()
@pytest.fixture
def uuid_a(): return SQLiteUUIDAdapter()


class TestBlob:
    def test_roundtrip(self, blob):
        assert blob.to_database(b"data", bytes) == b"data"
        assert blob.from_database(b"data", bytes) == b"data"
    def test_none(self, blob):
        assert blob.to_database(None, bytes) is None

class TestJSON:
    def test_roundtrip(self, json_a):
        val = {"x": 1, "y": [2, 3]}
        s = json_a.to_database(val, str)
        assert isinstance(s, str)
        assert json_a.from_database(s, dict) == val

class TestUUID:
    def test_roundtrip(self, uuid_a):
        u = uuid.uuid4()
        assert uuid_a.to_database(u, str) == str(u)
        assert uuid_a.from_database(str(u), uuid.UUID) == u