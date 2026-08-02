# src/rhosocial/activerecord/testsuite/feature/basic/transaction/test_savepoint_api_async.py
"""Async black-box contracts for savepoint / release / rollback_to.

Mirror of test_savepoint_api.py exercising AsyncTransactionManager.
Every test in this module MUST have a sync twin in test_savepoint_api.py
to guarantee the sync/async symmetry required by the project's code style.
"""
import pytest

from rhosocial.activerecord.backend.errors import TransactionError


@pytest.fixture
async def async_txn_backend(async_pool_and_model):
    """Async fixture: open a transaction and yield the backend."""
    pool, _model = async_pool_and_model
    cm = pool.transaction()
    backend = await cm.__aenter__()
    try:
        yield backend
    finally:
        try:
            await cm.__aexit__(None, None, None)
        except Exception:
            pass


class TestAsyncSavepointCreate:
    async def test_savepoint_autoname_is_returned_and_prefixed(self, async_txn_backend):
        mgr = async_txn_backend.transaction_manager
        name = await mgr.savepoint()
        assert isinstance(name, str)
        assert name
        assert name in mgr._active_savepoints

    async def test_savepoint_explicit_name_is_honored(self, async_txn_backend):
        mgr = async_txn_backend.transaction_manager
        name = await mgr.savepoint(name="cust_sp_a")
        assert name == "cust_sp_a"
        assert "cust_sp_a" in mgr._active_savepoints

    async def test_savepoint_increments_active_savepoints(self, async_txn_backend):
        mgr = async_txn_backend.transaction_manager
        before = len(mgr._active_savepoints)
        await mgr.savepoint(name="sp_first")
        await mgr.savepoint(name="sp_second")
        assert len(mgr._active_savepoints) == before + 2
        assert mgr._active_savepoints[-1] == "sp_second"
        assert mgr._active_savepoints[-2] == "sp_first"

    async def test_savepoint_seq_autoname_do_not_collide(self, async_txn_backend):
        mgr = async_txn_backend.transaction_manager
        names = {await mgr.savepoint() for _ in range(3)}
        assert len(names) == 3


class TestAsyncRelease:
    async def test_release_removes_named_savepoint(self, async_txn_backend):
        mgr = async_txn_backend.transaction_manager
        n = await mgr.savepoint(name="rel_target")
        assert n in mgr._active_savepoints
        await mgr.release(n)
        assert n not in mgr._active_savepoints

    async def test_release_does_not_touch_other_savepoints(self, async_txn_backend):
        mgr = async_txn_backend.transaction_manager
        a = await mgr.savepoint(name="keep_a")
        b = await mgr.savepoint(name="rel_b")
        c = await mgr.savepoint(name="keep_c")
        await mgr.release(b)
        assert a in mgr._active_savepoints
        assert c in mgr._active_savepoints
        assert b not in mgr._active_savepoints

    async def test_release_unknown_name_raises(self, async_txn_backend):
        mgr = async_txn_backend.transaction_manager
        await mgr.savepoint(name="real_one")
        with pytest.raises(TransactionError):
            await mgr.release("never_created")

    async def test_release_outside_transaction_raises(self, async_pool_and_model):
        pool, _model = async_pool_and_model
        async with pool.connection() as backend:
            mgr = backend.transaction_manager
            assert not mgr.is_active
            with pytest.raises(TransactionError):
                await mgr.release("any_sp")


class TestAsyncRollbackTo:
    async def test_rollback_to_truncates_newer_savepoints(self, async_txn_backend):
        mgr = async_txn_backend.transaction_manager
        await mgr.savepoint(name="lvl1")
        await mgr.savepoint(name="lvl2")
        await mgr.savepoint(name="lvl3")
        await mgr.savepoint(name="lvl4")
        await mgr.rollback_to("lvl2")
        assert "lvl2" in mgr._active_savepoints
        assert "lvl1" in mgr._active_savepoints
        assert "lvl3" not in mgr._active_savepoints
        assert "lvl4" not in mgr._active_savepoints
        assert mgr._active_savepoints == ["lvl1", "lvl2"]

    async def test_rollback_to_oldest_keeps_all_older(self, async_txn_backend):
        mgr = async_txn_backend.transaction_manager
        await mgr.savepoint(name="a")
        await mgr.savepoint(name="b")
        await mgr.savepoint(name="c")
        await mgr.rollback_to("a")
        assert mgr._active_savepoints == ["a"]

    async def test_rollback_to_same_savepoint_keeps_it(self, async_txn_backend):
        mgr = async_txn_backend.transaction_manager
        top = await mgr.savepoint(name="top")
        await mgr.rollback_to(top)
        assert top in mgr._active_savepoints

    async def test_rollback_to_unknown_raises(self, async_txn_backend):
        mgr = async_txn_backend.transaction_manager
        await mgr.savepoint(name="actual")
        with pytest.raises(TransactionError):
            await mgr.rollback_to("phantom")

    async def test_rollback_to_outside_transaction_raises(self, async_pool_and_model):
        pool, _model = async_pool_and_model
        async with pool.connection() as backend:
            mgr = backend.transaction_manager
            assert not mgr.is_active
            with pytest.raises(TransactionError):
                await mgr.rollback_to("any_sp")


class TestAsyncSavepointOutsideTransaction:
    async def test_savepoint_outside_transaction_raises(self, async_pool_and_model):
        pool, _model = async_pool_and_model
        async with pool.connection() as backend:
            mgr = backend.transaction_manager
            assert not mgr.is_active
            with pytest.raises(TransactionError):
                await mgr.savepoint(name="orphan_sp")


class TestAsyncSavepointDataSemantics:
    async def test_rollback_to_discards_writes_after_savepoint(self, async_pool_and_model):
        pool, model = async_pool_and_model
        async with pool.transaction() as backend:
            mgr = backend.transaction_manager
            await mgr.savepoint(name="before_changes")
            instance = model(name="Alice", email="alice@test.local")
            await instance.save()
            assert await model.query().where("name = ?", ("Alice",)).count() == 1
            await mgr.rollback_to("before_changes")
            assert await model.query().where("name = ?", ("Alice",)).count() == 0


class TestAsyncCommitWithPendingSavepoint:
    async def test_outer_commit_with_unreleased_savepoint_succeeds(self, async_pool_and_model):
        pool, model = async_pool_and_model
        async with pool.transaction() as backend:
            mgr = backend.transaction_manager
            await mgr.savepoint(name="left_open")
            instance = model(name="Bob", email="bob@test.local")
            await instance.save()
        async with pool.connection() as _backend:
            assert await model.query().where("name = ?", ("Bob",)).count() == 1
