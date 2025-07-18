# tests/rhosocial/activerecord_test/fixtures/community/setup.py
from src.rhosocial.activerecord.backend.base import StorageBackend


def create_community_tables(backend: StorageBackend) -> None:
    """Create a user community-related table"""
    # Create a SQL statement for the table...
    pass

def drop_community_tables(backend: StorageBackend) -> None:
    """Delete the user community related table"""
    # Delete the table's SQL statement...
    pass