# src/rhosocial/activerecord/testsuite/feature/basic/transaction/test_savepoint_api.py
"""
Black-box contracts for `TransactionManager.savepoint / release / rollback_to`.

These tests target the three first-class savepoint APIs exposed by
`backend.transaction_manager` (see python-activerecord
`src/rhosocial/activerecord/backend/transaction.py:494-592`):

- ``savepoint(name=None) -> str``   create a savepoint (auto-named if None)
- ``release(name) -> None``        release a savepoint
- ``rollback_to(name) -> None``    rollback to a savepoint, truncating newer ones

Scope: pure API-shaped contracts that should hold on any backend whose
dialect advertises ``supports_savepoint()``. Isolation-level phenomena
and dialect-specific SQL formatting are out of scope here (see
test_isolation_behavior.py / test_read_only_mode.py in later tasks).

Backend providers that do not support savepoints should skip the whole
module via scenario filter rather than per-test markers, since every
test here is grounded on the savepoint primitive.
"""
import pytest

from rhosocial.activerecord.backend.errors import TransactionError


@pytest.fixture
def txn_backend(sync_pool_and_model):
    """Yield a backend inside an outer transaction context.

    All savepoint operations require an already-active transaction; opening
    one ``with pool.transaction()`` also lets the block cleanup gracefully on
    test errors, keeping pool connection state consistent across tests.
    """
    pool, _model = sync_pool_and_model
    cm = pool.transaction()
    backend = cm.__enter__()
    try:
        yield backend
    finally:
        try:
            cm.__exit__(None, None, None)
        except Exception:
            pass


class TestSavepointCreate:
    """``TransactionManager.savepoint()`` creation contracts."""

    def test_savepoint_autoname_is_returned_and_prefixed(self, txn_backend):
        mgr = txn_backend.transaction_manager
        name = mgr.savepoint()
        assert isinstance(name, str)
        assert name  # non-empty
        assert name in mgr._active_savepoints

    def test_savepoint_explicit_name_is_honored(self, txn_backend):
        mgr = txn_backend.transaction_manager
        name = mgr.savepoint(name="cust_sp_a")
        assert name == "cust_sp_a"
        assert "cust_sp_a" in mgr._active_savepoints

    def test_savepoint_increments_active_savepoints(self, txn_backend):
        mgr = txn_backend.transaction_manager
        before = len(mgr._active_savepoints)
        mgr.savepoint(name="sp_first")
        mgr.savepoint(name="sp_second")
        assert len(mgr._active_savepoints) == before + 2
        assert mgr._active_savepoints[-1] == "sp_second"
        assert mgr._active_savepoints[-2] == "sp_first"

    def test_savepoint_seq_autoname_do_not_collide(self, txn_backend):
        mgr = txn_backend.transaction_manager
        names = {mgr.savepoint() for _ in range(3)}
        assert len(names) == 3


class TestRelease:
    """``TransactionManager.release()`` contracts."""

    def test_release_removes_named_savepoint(self, txn_backend):
        mgr = txn_backend.transaction_manager
        n = mgr.savepoint(name="rel_target")
        assert n in mgr._active_savepoints
        mgr.release(n)
        assert n not in mgr._active_savepoints

    def test_release_does_not_touch_other_savepoints(self, txn_backend):
        mgr = txn_backend.transaction_manager
        a = mgr.savepoint(name="keep_a")
        b = mgr.savepoint(name="rel_b")
        c = mgr.savepoint(name="keep_c")
        mgr.release(b)
        assert a in mgr._active_savepoints
        assert c in mgr._active_savepoints
        assert b not in mgr._active_savepoints

    def test_release_unknown_name_raises(self, txn_backend):
        mgr = txn_backend.transaction_manager
        mgr.savepoint(name="real_one")
        with pytest.raises(TransactionError):
            mgr.release("never_created")

    def test_release_outside_transaction_raises(self, sync_pool_and_model):
        pool, _model = sync_pool_and_model
        with pool.connection() as backend:
            mgr = backend.transaction_manager
            # No outer transaction active on this fresh connection
            assert not mgr.is_active
            with pytest.raises(TransactionError):
                mgr.release("any_sp")


class TestRollbackTo:
    """``TransactionManager.rollback_to()`` contracts.

    Per backend/transaction.py:587, rollback_to truncates _active_savepoints
    to include the named savepoint (kept) and drop those created after it.
    This non-stack rollback-to-named-point behaviour is a deliberate
    design choice and a key differentiator versus strictly-stack APIs.
    """

    def test_rollback_to_truncates_newer_savepoints(self, txn_backend):
        mgr = txn_backend.transaction_manager
        mgr.savepoint(name="lvl1")
        mgr.savepoint(name="lvl2")
        mgr.savepoint(name="lvl3")
        mgr.savepoint(name="lvl4")
        mgr.rollback_to("lvl2")
        # lvl2 retained; lvl3, lvl4 dropped
        assert "lvl2" in mgr._active_savepoints
        assert "lvl1" in mgr._active_savepoints
        assert "lvl3" not in mgr._active_savepoints
        assert "lvl4" not in mgr._active_savepoints
        assert mgr._active_savepoints == ["lvl1", "lvl2"]

    def test_rollback_to_oldest_keeps_all_older(self, txn_backend):
        mgr = txn_backend.transaction_manager
        mgr.savepoint(name="a")
        mgr.savepoint(name="b")
        mgr.savepoint(name="c")
        mgr.rollback_to("a")
        assert mgr._active_savepoints == ["a"]

    def test_rollback_to_same_savepoint_keeps_it(self, txn_backend):
        """Rolling back to the top savepoint keeps exactly that savepoint.

        This is intentionally different from release() which removes it.
        rollback_to(name) keeps ``name`` alive so further rollback_to(name)
        can be invoked again without recreating it.
        """
        mgr = txn_backend.transaction_manager
        top = mgr.savepoint(name="top")
        mgr.rollback_to(top)
        assert top in mgr._active_savepoints

    def test_rollback_to_unknown_raises(self, txn_backend):
        mgr = txn_backend.transaction_manager
        mgr.savepoint(name="actual")
        with pytest.raises(TransactionError):
            mgr.rollback_to("phantom")

    def test_rollback_to_outside_transaction_raises(self, sync_pool_and_model):
        pool, _model = sync_pool_and_model
        with pool.connection() as backend:
            mgr = backend.transaction_manager
            assert not mgr.is_active
            with pytest.raises(TransactionError):
                mgr.rollback_to("any_sp")


class TestSavepointOutsideTransaction:
    """``savepoint()`` itself requires an active transaction."""

    def test_savepoint_outside_transaction_raises(self, sync_pool_and_model):
        pool, _model = sync_pool_and_model
        with pool.connection() as backend:
            mgr = backend.transaction_manager
            assert not mgr.is_active
            with pytest.raises(TransactionError):
                mgr.savepoint(name="orphan_sp")


class TestSavepointDataSemantics:
    """``rollback_to`` actually rolls back DML done after the savepoint.

    This is the only test in this module that crosses into data semantics;
    keep it minimal so it stays a pure contract: it proves rollback_to is
    not merely state accounting but reaches the database.
    """

    def test_rollback_to_discards_writes_after_savepoint(self, sync_pool_and_model):
        pool, model = sync_pool_and_model
        with pool.transaction() as backend:
            mgr = backend.transaction_manager
            mgr.savepoint(name="before_changes")
            instance = model(name="Alice", email="alice@test.local")
            instance.save()
            assert model.query().where("name = ?", ("Alice",)).count() == 1
            mgr.rollback_to("before_changes")
            # Write made after the savepoint should have been undone.
            assert model.query().where("name = ?", ("Alice",)).count() == 0


class TestCommitWithPendingSavepoint:
    """Outer commit still succeeds when savepoints are unreleased.

    Per backend/transaction.py:413-420, outermost commit() releases any
    lingering savepoint tracking structures and issues a real COMMIT; it
    does not require the user to release() every savepoint manually.
    """

    def test_outer_commit_with_unreleased_savepoint_succeeds(self, sync_pool_and_model):
        pool, model = sync_pool_and_model
        with pool.transaction() as backend:
            mgr = backend.transaction_manager
            mgr.savepoint(name="left_open")
            instance = model(name="Bob", email="bob@test.local")
            instance.save()
            # No release() call: when the outer context exits, commit() should
            # still flush _active_savepoints and COMMIT cleanly.
        # Data should be persisted.
        with pool.connection() as _backend:
            assert model.query().where("name = ?", ("Bob",)).count() == 1
