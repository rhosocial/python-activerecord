# tests/rhosocial/activerecord_test/feature/backend/error_taxonomy/test_execute_contract.py
"""Core execute contract: phase-specific error types and no swallowed failures."""

import logging

import pytest

from rhosocial.activerecord.backend.base.execution import AsyncExecutionMixin, ExecutionMixin
from rhosocial.activerecord.backend.errors import (
    DatabaseError,
    QueryError,
    TransactionError,
    TypeConversionError,
)
from rhosocial.activerecord.backend.options import ExecutionOptions, StatementType
from rhosocial.activerecord.backend.result import QueryResult


class _Cursor:
    rowcount = 0
    description = None
    error = None

    def execute(self, sql, params=None):
        if self.error is not None:
            raise self.error
        return self

    def executemany(self, sql, params_list):
        if self.error is not None:
            raise self.error
        return self

    def close(self):
        pass


class _Connection:
    closed = False

    def __init__(self, commit_error=None):
        self._commit_error = commit_error

    def cursor(self):
        return _Cursor()

    def commit(self):
        if self._commit_error is not None:
            raise self._commit_error


class _BaseStub:
    def __init__(self, *, execute_error=None, commit_error=None, convert_error=None,
                 handler_returns_none=False):
        self._connection = None
        self.logger = logging.getLogger("test.execute.contract")
        self.execute_error = execute_error
        self.commit_error = commit_error
        self.convert_error = convert_error
        self.handler_returns_none = handler_returns_none

    def connect(self):
        self._connection = _Connection(self.commit_error)

    def _get_cursor(self):
        cursor = self._connection.cursor()
        cursor.error = self.execute_error
        return cursor

    def get_default_adapter_suggestions(self):
        return {}

    def prepare_parameters(self, params, adapters):
        if self.convert_error is not None:
            raise self.convert_error
        return params

    def _prepare_sql_and_params(self, sql, params):
        return sql, params

    def _execute_query(self, cursor, sql, params):
        if self.execute_error is not None:
            raise self.execute_error
        return cursor

    def _process_result_set(self, cursor, is_select, adapters, mapping):
        return []

    def _build_query_result(self, cursor, data, duration):
        return QueryResult(affected_rows=cursor.rowcount, data=data, duration=duration)

    def _handle_auto_commit_if_needed(self):
        if self.commit_error is not None:
            raise TransactionError("auto-commit failed") from self.commit_error

    def _handle_execution_error(self, error):
        if self.handler_returns_none:
            return None
        if isinstance(error, DatabaseError):
            raise error
        if isinstance(error, ValueError):
            raise QueryError(str(error)) from error
        raise DatabaseError(str(error)) from error


class _SyncBackend(ExecutionMixin, _BaseStub):
    pass


class _AsyncBackend(AsyncExecutionMixin, _BaseStub):
    async def connect(self):
        self._connection = _Connection(self.commit_error)

    async def _get_cursor(self):
        cursor = self._connection.cursor()
        cursor.error = self.execute_error
        return cursor

    async def _execute_query(self, cursor, sql, params):
        if self.execute_error is not None:
            raise self.execute_error
        return cursor

    async def _process_result_set(self, cursor, is_select, adapters, mapping):
        return []

    async def _handle_auto_commit_if_needed(self):
        if self.commit_error is not None:
            raise TransactionError("auto-commit failed") from self.commit_error

    async def _handle_execution_error(self, error):
        if self.handler_returns_none:
            return None
        if isinstance(error, DatabaseError):
            raise error
        if isinstance(error, ValueError):
            raise QueryError(str(error)) from error
        raise DatabaseError(str(error)) from error


def _options():
    return ExecutionOptions(stmt_type=StatementType.DML)


def test_driver_error_maps_to_query_error():
    backend = _SyncBackend(execute_error=ValueError("bad sql"))
    with pytest.raises(QueryError):
        backend.execute("select 1", options=_options())


def test_framework_error_is_not_re_wrapped():
    backend = _SyncBackend(convert_error=TypeConversionError("bad value"))
    with pytest.raises(TypeConversionError):
        backend.execute("insert into t values (?)", (object(),), options=_options())


def test_handler_that_returns_none_does_not_return_none():
    backend = _SyncBackend(execute_error=ValueError("boom"), handler_returns_none=True)
    with pytest.raises(DatabaseError):
        backend.execute("select 1", options=_options())


def test_auto_commit_failure_raises_transaction_error():
    backend = _SyncBackend(commit_error=RuntimeError("commit failed"))
    with pytest.raises(TransactionError) as info:
        backend.execute("insert into t values (1)", options=_options())
    assert isinstance(info.value.__cause__, RuntimeError)


def test_execute_many_auto_commit_failure_raises_transaction_error():
    backend = _SyncBackend(commit_error=RuntimeError("commit failed"))
    with pytest.raises(TransactionError):
        backend.execute_many("insert into t values (?)", [(1,)], options=_options())


def test_execute_many_handler_none_does_not_return_none():
    backend = _SyncBackend(execute_error=ValueError("boom"), handler_returns_none=True)
    with pytest.raises(DatabaseError):
        backend.execute_many("insert into t values (?)", [(1,)], options=_options())


@pytest.mark.asyncio
async def test_async_framework_error_is_not_re_wrapped():
    backend = _AsyncBackend(convert_error=TypeConversionError("bad value"))
    with pytest.raises(TypeConversionError):
        await backend.execute("insert into t values (?)", (object(),), options=_options())


@pytest.mark.asyncio
async def test_async_auto_commit_failure_raises_transaction_error():
    backend = _AsyncBackend(commit_error=RuntimeError("commit failed"))
    with pytest.raises(TransactionError):
        await backend.execute("insert into t values (1)", options=_options())


@pytest.mark.asyncio
async def test_async_handler_none_does_not_return_none():
    backend = _AsyncBackend(execute_error=ValueError("boom"), handler_returns_none=True)
    with pytest.raises(DatabaseError):
        await backend.execute("select 1", options=_options())
