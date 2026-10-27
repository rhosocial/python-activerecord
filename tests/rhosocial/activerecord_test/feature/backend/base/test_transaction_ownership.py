# tests/rhosocial/activerecord_test/feature/backend/base/test_transaction_ownership.py
"""A connection's transaction belongs to the caller that opened it.

Two callers driving one connection's transaction interleave ``BEGIN``/``COMMIT``
and drive the level counter to zero in the middle of someone else's work. The
symptom appears much later and somewhere else:

    TransactionError: No active transaction to commit

That message names nothing useful, so the check belongs where the mistake is
made -- the second ``begin()`` -- with an error that says what to do instead.

The check was missing from ``begin()`` entirely. Only the ``transaction()``
context manager warned, so code that used ``pool.transaction()`` (which calls
``begin_transaction()`` directly) got no warning at all.
"""

from __future__ import annotations

import asyncio
import threading
from unittest.mock import MagicMock

import pytest

from rhosocial.activerecord.backend.errors import TransactionError
from rhosocial.activerecord.backend.transaction import (
    AsyncTransactionManager,
    TransactionManager,
)


class _SyncManager(TransactionManager):
    def _do_begin(self) -> None: ...
    def _do_commit(self) -> None: ...
    def _do_rollback(self) -> None: ...
    def _do_create_savepoint(self, name: str) -> None: ...
    def _do_release_savepoint(self, name: str) -> None: ...
    def _do_rollback_savepoint(self, name: str) -> None: ...
    def supports_savepoint(self) -> bool:
        return True


class _AsyncManager(AsyncTransactionManager):
    async def _do_begin(self) -> None: ...
    async def _do_commit(self) -> None: ...
    async def _do_rollback(self) -> None: ...
    async def _do_create_savepoint(self, name: str) -> None: ...
    async def _do_release_savepoint(self, name: str) -> None: ...
    async def _do_rollback_savepoint(self, name: str) -> None: ...
    async def supports_savepoint(self) -> bool:
        return True


class TestAsyncOwnership:
    def test_a_second_task_cannot_begin_the_same_transaction(self) -> None:
        manager = _AsyncManager(MagicMock())

        async def scenario() -> None:
            await manager.begin()
            try:
                with pytest.raises(TransactionError, match="owned by another task"):
                    await asyncio.create_task(manager.begin())
                # The owner's transaction is untouched by the refusal.
                assert manager.transaction_level == 1
                await manager.commit()
            finally:
                if manager.is_active:
                    await manager.rollback()

        asyncio.run(scenario())

    def test_the_owner_may_nest(self) -> None:
        manager = _AsyncManager(MagicMock())

        async def scenario() -> None:
            await manager.begin()
            await manager.begin()
            assert manager.transaction_level == 2
            await manager.commit()
            await manager.commit()
            assert manager.transaction_level == 0

        asyncio.run(scenario())

    def test_another_task_may_use_the_connection_after_the_commit(self) -> None:
        manager = _AsyncManager(MagicMock())

        async def scenario() -> None:
            await manager.begin()
            await manager.commit()

            async def later() -> None:
                await manager.begin()
                await manager.commit()

            await asyncio.create_task(later())

        asyncio.run(scenario())


class TestSyncOwnership:
    def test_another_thread_cannot_begin_the_same_transaction(self) -> None:
        manager = _SyncManager(MagicMock())
        captured: list[BaseException] = []

        manager.begin()
        try:

            def other_thread() -> None:
                try:
                    manager.begin()
                except BaseException as exc:  # noqa: BLE001 - the point of the test
                    captured.append(exc)

            thread = threading.Thread(target=other_thread)
            thread.start()
            thread.join(timeout=10)

            assert captured, "the second thread must be refused"
            assert isinstance(captured[0], TransactionError)
            assert "owned by another thread" in str(captured[0])
            assert manager.transaction_level == 1
        finally:
            manager.commit()

    def test_another_thread_may_use_the_connection_after_the_commit(self) -> None:
        manager = _SyncManager(MagicMock())
        captured: list[BaseException] = []

        manager.begin()
        manager.commit()

        def other_thread() -> None:
            try:
                manager.begin()
                manager.commit()
            except BaseException as exc:  # noqa: BLE001 - the point of the test
                captured.append(exc)

        thread = threading.Thread(target=other_thread)
        thread.start()
        thread.join(timeout=10)

        assert not captured, f"the connection was free, yet: {captured!r}"
