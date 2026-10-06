# src/rhosocial/activerecord/backend/expression/execution_testing.py
"""
Reusable execution-confirmation helpers for expression packages.

Rendering is not execution. A formatter can produce SQL that looks perfect and
is still rejected by the server -- that is exactly how PostgreSQL 9 and
ClickHouse rendered well-formed ``GENERATED ... AS IDENTITY`` clauses their
servers refused. This module is the reusable counterpart to
:mod:`roundtrip_testing`: round-trip testing asks whether an expression survives
serialization; execution confirmation asks whether the SQL it renders is
accepted by a live server.

Backend test suites use it like this::

    from rhosocial.activerecord.backend.expression.execution_testing import (
        ExecutionOutcome,
        classify_execution,
        confirm_expression_execution,
    )

    # A sentinel first: a deliberately invalid statement must be classified
    # REJECTED, or a null result could be read as acceptance.
    assert classify_execution(backend, "THIS IS NOT SQL") is ExecutionOutcome.REJECTED

    outcome = confirm_expression_execution(
        backend,
        CreateTableExpression(dialect, table, columns),
        teardown=[DropTableExpression(dialect, table)],
    )
    if outcome is ExecutionOutcome.NOT_RENDERED:
        pytest.skip("dialect does not render this expression")

Three outcomes are distinguished, and must never be conflated:

* :attr:`ExecutionOutcome.ACCEPTED` -- the server accepted the SQL.
* :attr:`ExecutionOutcome.REJECTED` -- the server refused it. This is the
  failure the helper exists to catch; ``confirm_expression_execution`` raises
  :class:`ExecutionConfirmationError` carrying the SQL and the server error.
* :attr:`ExecutionOutcome.NOT_RENDERED` -- the expression itself refused to
  render (``UnsupportedFeatureError``). That is fail-closed behaviour working
  as designed, and the caller decides whether it is a skip. It is returned,
  not raised, and it is *not* the same thing as a rejection: treating both as
  a skip is how a suite goes green for the wrong reason.

The helper is synchronous only; an async backend can await its own ``execute``
and classify with the same three states.
"""

from enum import Enum
from typing import Any, Iterable, Tuple, Union

from .bases import BaseExpression

#: A preparation or teardown step: a renderable expression, or raw SQL+params.
ExecutionStep = Union[BaseExpression, Tuple[str, Tuple]]


class ExecutionOutcome(Enum):
    """The three states an execution confirmation distinguishes."""

    ACCEPTED = "accepted"
    REJECTED = "rejected"
    NOT_RENDERED = "not-rendered"


class ExecutionConfirmationError(AssertionError):
    """The server rejected SQL an expression rendered.

    An :class:`AssertionError` because that is what it is: the confirmation
    assertion failed. The original server error is attached as ``__cause__``.
    """


def classify_execution(backend: Any, sql: str, params: Tuple = ()) -> ExecutionOutcome:
    """Execute raw SQL and classify the server's answer.

    This is the sentinel channel: run a statement known to be invalid and
    assert it comes back :attr:`ExecutionOutcome.REJECTED` before trusting any
    :attr:`ExecutionOutcome.ACCEPTED` from the same path. A classifier that
    cannot see a rejection would make every confirmation vacuous.

    Args:
        backend: A synchronous storage backend (anything exposing
            ``execute(sql, params)`` and raising on rejection).
        sql: The statement to execute.
        params: Optional bind parameters.

    Returns:
        ACCEPTED when ``execute`` returned, REJECTED when it raised.
    """
    try:
        backend.execute(sql, params)
    except Exception:
        return ExecutionOutcome.REJECTED
    return ExecutionOutcome.ACCEPTED


def _execute_step(backend: Any, step: ExecutionStep) -> None:
    """Execute one preparation/teardown step (expression or raw SQL)."""
    if isinstance(step, BaseExpression):
        sql, params = step.to_sql()
    else:
        sql, params = step
    backend.execute(sql, params)


def confirm_expression_execution(
    backend: Any,
    expression: BaseExpression,
    *,
    prepare: Iterable[ExecutionStep] = (),
    teardown: Iterable[ExecutionStep] = (),
) -> ExecutionOutcome:
    """Render an expression, execute it against a live backend, confirm acceptance.

    The expression is rendered first. A refusal to render (an
    ``UnsupportedFeatureError``) returns :attr:`ExecutionOutcome.NOT_RENDERED`
    immediately, before any preparation runs. Any *other* exception from
    rendering propagates: a defect must not hide behind the not-rendered
    classification.

    Both shapes are supported:

    * **DDL** -- pass the statements that undo the creation through
      ``teardown``; they run in a ``finally`` block whether the confirmation
      succeeded or failed.
    * **Query-shaped** -- pass the statements that build the schema the query
      needs through ``prepare``; they run before the expression. A failure
      there propagates as a setup failure, because it is not a verdict on the
      expression.

    Args:
        backend: A synchronous storage backend (anything exposing
            ``execute(sql, params)`` and raising on rejection).
        expression: The expression to render and execute.
        prepare: Schema preparation steps for query-shaped expressions.
        teardown: Cleanup steps for DDL expressions.

    Returns:
        :attr:`ExecutionOutcome.ACCEPTED` when the server accepted the SQL,
        :attr:`ExecutionOutcome.NOT_RENDERED` when the expression refused to
        render.

    Raises:
        ExecutionConfirmationError: When the expression rendered but the
            server rejected the SQL. The message carries the expression type,
            the SQL, the parameters, and the server error.
        Exception: Any other rendering failure, and any preparation or
            teardown failure, propagate unchanged.
    """
    from ..dialect.exceptions import UnsupportedFeatureError

    try:
        sql, params = expression.to_sql()
    except UnsupportedFeatureError:
        return ExecutionOutcome.NOT_RENDERED

    for step in prepare:
        _execute_step(backend, step)

    try:
        backend.execute(sql, params)
    except Exception as exc:
        raise ExecutionConfirmationError(
            f"the server rejected SQL the expression rendered.\n"
            f"  expression: {type(expression).__name__}\n"
            f"  sql: {sql!r}\n"
            f"  params: {params!r}\n"
            f"  server error: {type(exc).__name__}: {exc}"
        ) from exc
    finally:
        for step in teardown:
            _execute_step(backend, step)

    return ExecutionOutcome.ACCEPTED
