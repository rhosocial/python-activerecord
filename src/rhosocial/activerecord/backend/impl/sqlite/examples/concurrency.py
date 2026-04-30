# src/rhosocial/activerecord/backend/impl/sqlite/examples/concurrency.py
"""
Example demonstrating ConcurrencyAware protocol usage.

This example shows how to query the concurrency hint from a backend
to understand its concurrency constraints.
"""

import logging

from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.backend.protocols import ConcurrencyAware

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def main():
    logger.info("=== ConcurrencyAware Protocol Example ===")

    config = SQLiteConnectionConfig(database=":memory:")
    backend = SQLiteBackend(connection_config=config)
    backend.connect()

    if isinstance(backend, ConcurrencyAware):
        logger.info("Backend implements ConcurrencyAware protocol")

        hint = backend.get_concurrency_hint()
        logger.info(f"Concurrency hint: max_concurrency={hint.max_concurrency}, reason={hint.reason!r}")
    else:
        logger.warning("Backend does not implement ConcurrencyAware protocol")

    backend.disconnect()


if __name__ == "__main__":
    main()