"""SQLite direct backend benchmark workloads."""

from typing import Any, Dict, List

from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType

DML_OPTIONS = ExecutionOptions(stmt_type=StatementType.DML, process_result_set=False)
DQL_OPTIONS = ExecutionOptions(stmt_type=StatementType.DQL, process_result_set=True)


def execute_insert_one(context: Any, payload: Dict[str, object]) -> Any:
    result = context.backend.execute(
        context.sql["insert"],
        context.params_factory("insert", payload),
        options=DML_OPTIONS,
    )
    if result.affected_rows != 1 or result.last_insert_id is None:
        raise AssertionError("SQLite insert benchmark did not return last_insert_id")
    return result.last_insert_id


async def execute_insert_one_async(context: Any, payload: Dict[str, object]) -> Any:
    result = await context.backend.execute(
        context.sql["insert"],
        context.params_factory("insert", payload),
        options=DML_OPTIONS,
    )
    if result.affected_rows != 1 or result.last_insert_id is None:
        raise AssertionError("async SQLite insert benchmark did not return last_insert_id")
    return result.last_insert_id


def execute_find_one(context: Any, record_id: Any) -> Dict[str, object]:
    result = context.backend.execute(context.sql["find_one"], (record_id,), options=DQL_OPTIONS)
    if len(result.data) != 1 or result.data[0]["id"] != record_id:
        raise AssertionError("SQLite find benchmark returned an unexpected row")
    return result.data[0]


async def execute_find_one_async(context: Any, record_id: Any) -> Dict[str, object]:
    result = await context.backend.execute(context.sql["find_one"], (record_id,), options=DQL_OPTIONS)
    if len(result.data) != 1 or result.data[0]["id"] != record_id:
        raise AssertionError("async SQLite find benchmark returned an unexpected row")
    return result.data[0]


def execute_update_one(context: Any, record_id: Any, username: str) -> None:
    result = context.backend.execute(
        context.sql["update"],
        (username, record_id),
        options=DML_OPTIONS,
    )
    if result.affected_rows != 1:
        raise AssertionError("SQLite update benchmark did not affect exactly one row")


async def execute_update_one_async(context: Any, record_id: Any, username: str) -> None:
    result = await context.backend.execute(
        context.sql["update"],
        (username, record_id),
        options=DML_OPTIONS,
    )
    if result.affected_rows != 1:
        raise AssertionError("async SQLite update benchmark did not affect exactly one row")


def execute_delete_one(context: Any, record_id: Any) -> None:
    result = context.backend.execute(context.sql["delete"], (record_id,), options=DML_OPTIONS)
    if result.affected_rows != 1:
        raise AssertionError("SQLite delete benchmark did not affect exactly one row")


async def execute_delete_one_async(context: Any, record_id: Any) -> None:
    result = await context.backend.execute(context.sql["delete"], (record_id,), options=DML_OPTIONS)
    if result.affected_rows != 1:
        raise AssertionError("async SQLite delete benchmark did not affect exactly one row")


def execute_many_insert(context: Any, payloads: List[Dict[str, object]]) -> int:
    params_list = [context.params_factory("insert", payload) for payload in payloads]
    result = context.backend.execute_many(context.sql["insert"], params_list)
    if result.affected_rows != len(payloads):
        raise AssertionError("SQLite execute_many insert affected unexpected row count")
    return result.affected_rows


async def execute_many_insert_async(context: Any, payloads: List[Dict[str, object]]) -> int:
    params_list = [context.params_factory("insert", payload) for payload in payloads]
    result = await context.backend.execute_many(context.sql["insert"], params_list)
    if result.affected_rows != len(payloads):
        raise AssertionError("async SQLite execute_many insert affected unexpected row count")
    return result.affected_rows
