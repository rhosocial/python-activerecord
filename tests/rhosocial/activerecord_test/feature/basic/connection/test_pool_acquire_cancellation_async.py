# src/rhosocial/activerecord/testsuite/feature/basic/connection/test_pool_acquire_cancellation_async.py
"""A cancelled acquire must give its permit back.

A readiness probe gives up after a couple of seconds. When the database is
restarting, the acquire it gives up on is mid-connect -- so the cancellation
lands after the semaphore permit was taken and before any backend was handed
out. ``CancelledError`` is a ``BaseException``, and the preparation code only
caught ``Exception``: the permit stayed taken, and the pool it belonged to
answered ``available=0, in_use=0`` while every later request waited out the
acquire timeout.

These tests pin the property, not the implementation: cancel an acquire that is
stuck creating a connection, then acquire again.
"""
import asyncio

import pytest


class TestAcquireCancellation:
    async def test_a_cancelled_acquire_returns_its_permit(self, async_pool_and_model):
        pool, _model = async_pool_and_model
        # Force the create path: nothing idle, so acquire has to connect.
        pool._available.clear()
        pool._stats.current_available = 0

        original_create = pool._create_backend

        async def stuck(*_args, **_kwargs):
            await asyncio.sleep(3_600)

        pool._create_backend = stuck
        task = asyncio.create_task(pool.acquire())
        await asyncio.sleep(0.05)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task

        pool._create_backend = original_create
        backend = await asyncio.wait_for(pool.acquire(), timeout=5)
        await pool.release(backend)

    async def test_the_pool_survives_repeated_cancellations(self, async_pool_and_model):
        """One probe per interval adds up: the pool must not erode."""
        pool, _model = async_pool_and_model
        original_create = pool._create_backend

        async def stuck(*_args, **_kwargs):
            await asyncio.sleep(3_600)

        for _ in range(pool.config.max_size + 2):
            pool._available.clear()
            pool._stats.current_available = 0
            pool._create_backend = stuck
            task = asyncio.create_task(pool.acquire())
            await asyncio.sleep(0.01)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task

        pool._create_backend = original_create
        backend = await asyncio.wait_for(pool.acquire(), timeout=5)
        await pool.release(backend)
        assert pool._stats.current_in_use == 0
