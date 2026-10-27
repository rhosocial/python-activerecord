# src/rhosocial/activerecord/testsuite/feature/basic/transaction/test_async_owner_task.py
"""Async contract for `AsyncTransactionManager._owner_task` safety check.

`AsyncTransactionManager` tracks which asyncio task owns an active outermost
transaction. Nesting is a savepoint, and only the owner may nest: when another
task enters the same manager while a transaction is active, it MUST raise
`TransactionError` naming the cause.

Earlier this was a `UserWarning` emitted by `transaction()`, and nothing more.
It was not enough:

* the second task could still proceed, so both drove the same level counter --
  two "Beginning transaction (level 0)" in a row, then a commit that found
  level 0 and raised "No active transaction to commit", a message that names
  neither the cause nor the caller;
* `pool.transaction()` calls `begin_transaction()` directly, bypassing the
  warning entirely, so the deployments that needed the check most never saw it.

Coverage:
- T1 a single task may nest without error
- T2 a different task entering while an outer is active is refused
- T3 the refusal message names the cause and the fix
- T4 the owner's transaction survives a refused attempt
- T5 owner_task is cleared after the outermost transaction exits cleanly
- T6 the same task re-entering after a clean exit re-acquires ownership
- T7 another task may use the connection once the owner has committed
"""
import asyncio

import pytest

from rhosocial.activerecord.backend.errors import TransactionError


@pytest.fixture
async def mgr_and_backend(async_pool_and_model):
    """Acquire a backend via pool.connection() and yield (backend, mgr).

    Mechanism note: we stub `_do_begin / _do_commit / _do_rollback /
    _do_create_savepoint / _do_release_savepoint / _do_rollback_savepoint`
    on the async transaction manager with no-ops, because the ownership check
    fires *before* `_do_begin()` is awaited. Stubbing the I/O layer lets us
    exercise the pure state machine -- including concurrent multi-task
    execution on a real asyncio event loop -- without dragging in SQLite's
    thread-affinity rules, which otherwise cause spurious "cannot start a
    transaction within a transaction" when a second task reuses the same
    aiosqlite connection.
    """
    pool, _model = async_pool_and_model
    cm = pool.connection()
    backend = await cm.__aenter__()
    mgr = backend.transaction_manager

    async def _noop(*args, **kwargs):
        return None

    mgr._do_begin = _noop
    mgr._do_commit = _noop
    mgr._do_rollback = _noop
    mgr._do_create_savepoint = _noop
    mgr._do_release_savepoint = _noop
    mgr._do_rollback_savepoint = _noop

    try:
        yield backend, mgr
    finally:
        try:
            await cm.__aexit__(None, None, None)
        except Exception:
            pass


class TestAsyncOwnerTaskSameTask:
    async def test_same_task_nested_transaction_is_allowed(self, mgr_and_backend):
        _backend, mgr = mgr_and_backend
        async with mgr.transaction():
            async with mgr.transaction():
                assert mgr.transaction_level == 2

    async def test_same_task_reentry_after_clean_exit_is_allowed(self, mgr_and_backend):
        _backend, mgr = mgr_and_backend
        async with mgr.transaction():
            pass
        async with mgr.transaction():
            pass


class TestAsyncOwnerTaskCrossTaskRefusal:
    async def test_cross_task_share_is_refused(self, mgr_and_backend):
        """A different task entering during an active outer transaction MUST
        raise TransactionError -- the second task cannot be allowed to drive
        the owner's level counter."""
        _backend, mgr = mgr_and_backend

        outer_started = asyncio.Event()
        proceed = asyncio.Event()

        async def owner():
            async with mgr.transaction():
                outer_started.set()
                await proceed.wait()

        async def second_task(refusals):
            try:
                async with mgr.transaction():
                    refusals.append(None)
            except TransactionError as exc:
                refusals.append(exc)

        refusals: list = []
        owner_task = asyncio.create_task(owner())
        second = asyncio.create_task(second_task(refusals))
        try:
            await asyncio.wait_for(outer_started.wait(), timeout=5.0)
            await asyncio.sleep(0.05)
        finally:
            proceed.set()
            await asyncio.gather(owner_task, second)

        assert refusals and isinstance(refusals[0], TransactionError), (
            "the second task must be refused, not silently allowed"
        )

    async def test_refusal_message_names_the_cause_and_the_fix(self, mgr_and_backend):
        _backend, mgr = mgr_and_backend

        outer_started = asyncio.Event()
        proceed = asyncio.Event()

        async def owner():
            async with mgr.transaction():
                outer_started.set()
                await proceed.wait()

        async def second_task(refusals):
            try:
                await mgr.begin()
            except TransactionError as exc:
                refusals.append(exc)

        refusals: list = []
        owner_task = asyncio.create_task(owner())
        second = asyncio.create_task(second_task(refusals))
        try:
            await asyncio.wait_for(outer_started.wait(), timeout=5.0)
            await asyncio.sleep(0.05)
        finally:
            proceed.set()
            await asyncio.gather(owner_task, second)

        message = str(refusals[0])
        assert "owned by another task" in message
        assert "AsyncBackendPool" in message

    async def test_the_owner_keeps_its_transaction_after_a_refusal(self, mgr_and_backend):
        _backend, mgr = mgr_and_backend

        async with mgr.transaction():
            assert mgr.transaction_level == 1

            async def intruder():
                with pytest.raises(TransactionError):
                    await mgr.begin()

            await asyncio.create_task(intruder())

            assert mgr.transaction_level == 1, "the refusal must not disturb the owner"
            assert mgr.is_active

    async def test_another_task_may_use_the_connection_after_the_commit(self, mgr_and_backend):
        _backend, mgr = mgr_and_backend

        async with mgr.transaction():
            pass

        async def later():
            async with mgr.transaction():
                assert mgr.transaction_level == 1

        await asyncio.create_task(later())


class TestAsyncOwnerTaskLifecycle:
    async def test_owner_task_cleared_after_outermost_exits(self, mgr_and_backend):
        """After a clean outermost commit, _owner_task MUST reset to None."""
        _backend, mgr = mgr_and_backend
        async with mgr.transaction():
            assert mgr.is_active
            async with mgr.transaction():
                pass

        assert mgr._owner_task is None

    async def test_owner_task_cleared_after_outermost_rolls_back(self, mgr_and_backend):
        _backend, mgr = mgr_and_backend
        with pytest.raises(RuntimeError):
            async with mgr.transaction():
                async with mgr.transaction():
                    raise RuntimeError("force rollback")
        assert mgr._owner_task is None

    async def test_owner_task_reacquired_by_same_task_after_clean_exit(self, mgr_and_backend):
        """After a clean reset the same task re-entering re-acquires ownership."""
        _backend, mgr = mgr_and_backend
        async with mgr.transaction():
            async with mgr.transaction():
                pass
        async with mgr.transaction():
            pass
