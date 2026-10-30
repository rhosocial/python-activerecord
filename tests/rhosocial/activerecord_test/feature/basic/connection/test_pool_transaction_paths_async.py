# src/rhosocial/activerecord/testsuite/feature/basic/connection/test_pool_transaction_paths_async.py
"""Async white-box contracts for `pool.transaction()` dispatch branches.

Mirror of test_pool_transaction_paths.py exercising AsyncBackendPool
(`connection/pool/async_pool.py:579-638`). Every test MUST have a sync
twin in test_pool_transaction_paths.py to guarantee the sync/async
symmetry required by the project code style.
"""
import pytest

from rhosocial.activerecord.backend.errors import TransactionError

from rhosocial.activerecord.connection.pool import (
    get_current_async_transaction_backend,
    get_current_async_connection_backend,
    get_current_async_backend,
)


class TestAsyncPath1ExistingTransactionIsReused:
    async def test_inner_pool_transaction_yields_same_backend(self, async_pool_and_model):
        pool, _model = async_pool_and_model
        async with pool.transaction() as outer:
            async with pool.transaction() as inner:
                assert inner is outer

    async def test_inner_exits_does_not_commit_outer(self, async_pool_and_model):
        pool, _model = async_pool_and_model
        async with pool.transaction() as outer:
            mgr = outer.transaction_manager
            assert mgr.is_active
            async with pool.transaction() as _:
                assert mgr.transaction_level == 1
            assert mgr.is_active
            assert mgr.transaction_level == 1

    async def test_path1_does_not_register_a_new_transaction_backend(self, async_pool_and_model):
        pool, _model = async_pool_and_model
        async with pool.transaction() as outer:
            async with pool.transaction() as _inner:
                assert get_current_async_transaction_backend() is outer


class TestAsyncPath2ConnectionOnlyBranch:
    async def test_transaction_reuses_the_connection_backend(self, async_pool_and_model):
        pool, _model = async_pool_and_model
        async with pool.connection() as conn:
            async with pool.transaction() as tx_backend:
                assert tx_backend is conn

    async def test_tx_token_set_during_path2_and_cleared_after(self, async_pool_and_model):
        pool, _model = async_pool_and_model
        async with pool.connection():
            assert get_current_async_transaction_backend() is None
            async with pool.transaction() as tx:
                assert get_current_async_transaction_backend() is tx
            assert get_current_async_transaction_backend() is None
            assert get_current_async_connection_backend() is tx

    async def test_path2_commits_visible_after_exit(self, async_pool_and_model):
        pool, model = async_pool_and_model
        async with pool.connection():
            async with pool.transaction() as _backend:
                instance = model(name="Path2User", email="p2@test.local")
                await instance.save()
        async with pool.connection() as _check:
            assert await model.query().where("name = ?", ("Path2User",)).count() == 1

    async def test_path2_rollback_on_exception_leaves_no_tx_token(self, async_pool_and_model):
        pool, _model = async_pool_and_model
        with pytest.raises(RuntimeError):
            async with pool.connection() as conn:
                async with pool.transaction() as tx:
                    assert tx is conn
                    raise RuntimeError("boom")
        assert get_current_async_transaction_backend() is None
        assert get_current_async_connection_backend() is None

    async def test_path2_failure_does_not_break_outer_connection(self, async_pool_and_model):
        pool, model = async_pool_and_model
        async with pool.connection() as conn:
            try:
                async with pool.transaction() as _tx:
                    raise RuntimeError("intentional")
            except RuntimeError:
                pass
            assert not conn.transaction_manager.is_active
            instance = model(name="AfterFailure", email="af@test.local")
            await instance.save()
        async with pool.connection() as _check:
            assert await model.query().where("name = ?", ("AfterFailure",)).count() == 1


class TestAsyncPath3AcquireBranch:
    async def test_path3_yields_a_backend_bound_to_both_tx_and_conn_tokens(self, async_pool_and_model):
        pool, _model = async_pool_and_model
        async with pool.transaction() as backend:
            assert get_current_async_transaction_backend() is backend
            assert get_current_async_connection_backend() is backend
            assert get_current_async_backend() is backend

    async def test_path3_tokens_cleared_after_exit(self, async_pool_and_model):
        pool, _model = async_pool_and_model
        async with pool.transaction():
            pass
        assert get_current_async_transaction_backend() is None
        assert get_current_async_connection_backend() is None
        assert get_current_async_backend() is None

    async def test_path3_commit_on_clean_exit(self, async_pool_and_model):
        pool, model = async_pool_and_model
        async with pool.transaction() as _backend:
            u = model(name="P3Ok", email="p3ok@test.local")
            await u.save()
        async with pool.connection() as _check:
            assert await model.query().where("name = ?", ("P3Ok",)).count() == 1

    async def test_path3_rollback_on_exception(self, async_pool_and_model):
        pool, model = async_pool_and_model
        with pytest.raises(RuntimeError):
            async with pool.transaction() as _backend:
                u = model(name="P3Fail", email="p3fail@test.local")
                await u.save()
                raise RuntimeError("intentional")
        async with pool.connection() as _check:
            assert await model.query().where("name = ?", ("P3Fail",)).count() == 0

    async def test_path3_tokens_cleared_after_exception(self, async_pool_and_model):
        pool, _model = async_pool_and_model
        with pytest.raises(RuntimeError):
            async with pool.transaction():
                raise RuntimeError("intentional")
        assert get_current_async_transaction_backend() is None
        assert get_current_async_connection_backend() is None


class TestAsyncPathPrecedence:
    async def test_transaction_context_beats_connection_only(self, async_pool_and_model):
        pool, _model = async_pool_and_model
        async with pool.transaction() as tx:
            async with pool.transaction() as inner:
                assert inner is tx

    async def test_no_savepoint_created_when_reentering_via_pool(self, async_pool_and_model):
        pool, _model = async_pool_and_model
        async with pool.transaction() as outer:
            mgr = outer.transaction_manager
            saved_sp = list(mgr._active_savepoints)
            async with pool.transaction():
                assert mgr._active_savepoints == saved_sp
            assert mgr.transaction_level == 1


class TestAsyncRollbackFailureKeepsTheOriginalError:
    """A failing rollback must not replace the error that caused it.

    This is the shape of a real ledger entry: an ``IntegrityError`` inside a
    transaction, then a rollback on a transaction that was already gone
    (``TransactionError: No active transaction to rollback``), and the caller
    was told about the rollback instead of the duplicate key.
    """

    @staticmethod
    def _break_rollback(backend) -> None:  # noqa: ANN001 - a test double
        async def broken(*_args, **_kwargs):  # noqa: ANN002, ANN003, ANN202
            raise TransactionError("No active transaction to rollback")

        backend.rollback_transaction = broken

    async def test_path2_keeps_the_body_error(self, async_pool_and_model) -> None:
        pool, _model = async_pool_and_model
        async with pool.connection():
            with pytest.raises(RuntimeError, match="the body failed"):
                async with pool.transaction() as tx:
                    self._break_rollback(tx)
                    raise RuntimeError("the body failed")

    async def test_path3_keeps_the_body_error(self, async_pool_and_model) -> None:
        pool, _model = async_pool_and_model
        with pytest.raises(RuntimeError, match="the body failed"):
            async with pool.transaction() as backend:
                self._break_rollback(backend)
                raise RuntimeError("the body failed")

    async def test_tokens_are_cleared_after_a_failed_rollback(
        self, async_pool_and_model
    ) -> None:
        pool, _model = async_pool_and_model
        with pytest.raises(RuntimeError):
            async with pool.transaction() as backend:
                self._break_rollback(backend)
                raise RuntimeError("the body failed")
        assert get_current_async_transaction_backend() is None
        assert get_current_async_connection_backend() is None
