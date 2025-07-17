# tests/rhosocial/activerecord_test/fixtures/storage.py
"""Storage Backend Fixtures"""
import pytest
from pathlib import Path
from typing import Generator

from src.rhosocial.activerecord.backend.base import StorageBackend
from src.rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from src.rhosocial.activerecord.backend.typing import ConnectionConfig


@pytest.fixture(params=['memory', 'file'])
def storage_backend(request, tmp_path) -> Generator[StorageBackend, None, None]:
    """参数化的存储后端夹具"""
    if request.param == 'memory':
        config = ConnectionConfig(database=":memory:")
    else:
        db_path = tmp_path / "test.db"
        config = ConnectionConfig(database=str(db_path))

    backend = SQLiteBackend(config.database)
    yield backend
    backend.disconnect()

    if request.param == 'file':
        Path(config.database).unlink(missing_ok=True)