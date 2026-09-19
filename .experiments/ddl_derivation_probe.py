# .experiments/ddl_derivation_probe.py
"""Experiment: list/enum/interval mapping strategies + PK/nullability derivation.

Companion to ``field_type_adaptation.py``. Answers, per dialect:

A. ``list``/``tuple`` mapping: JSON (portable) vs Array (native)?
B. Enum strategy: native/suggested, and what to do where generic ``enum`` is absent.
C. ``timedelta``/interval strategy: INTERVAL vs a fallback.
D. Primary-key derivation: integer PK + auto-increment rendering, and
   ``supports_auto_increment()``.
E. Nullability derivation: Optional -> NULL, required -> (no auto NOT NULL),
   explicit override demo.

Run::

    PYTHONPATH=tests .venv3.14-ubuntu26.04/bin/python .experiments/ddl_derivation_probe.py
"""

from __future__ import annotations

from datetime import timedelta
from enum import Enum
from typing import Annotated, Optional

from rhosocial.activerecord.backend.expression.statements.ddl_table import (
    ColumnConstraint,
    ColumnConstraintType,
    ColumnDefinition,
    CreateTableExpression,
)
from rhosocial.activerecord.backend.expression.types import (
    ArrayType,
    BooleanType,
    DateTimeType,
    EnumType,
    IntegerType,
    IntervalType,
    JsonType,
    TextType,
    VarCharType,
)
from rhosocial.activerecord.base.fields import UseConstraint
from rhosocial.activerecord.model import ActiveRecord


class Color(Enum):
    RED = "red"
    GREEN = "green"


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def dialect_instances():
    from rhosocial.activerecord.backend.impl.clickhouse.dialect import ClickHouseDialect
    from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect
    from rhosocial.activerecord.backend.impl.firebird.dialect import FirebirdDialect
    from rhosocial.activerecord.backend.impl.mariadb.dialect import MariaDBDialect
    from rhosocial.activerecord.backend.impl.mysql.dialect import MySQLDialect
    from rhosocial.activerecord.backend.impl.oracle.dialect import OracleDialect
    from rhosocial.activerecord.backend.impl.postgres.dialect import PostgresDialect
    from rhosocial.activerecord.backend.impl.snowflake.dialect import SnowflakeDialect
    from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
    from rhosocial.activerecord.backend.impl.sqlserver.dialect import SQLServerDialect

    return [
        ("sqlite", SQLiteDialect((3, 53, 0))),
        ("dummy", DummyDialect()),
        ("mysql", MySQLDialect((8, 0, 0))),
        ("postgres", PostgresDialect((16, 0, 0))),
        ("mariadb", MariaDBDialect((10, 11, 0))),
        ("sqlserver", SQLServerDialect((2022, 0, 0))),
        ("oracle", OracleDialect((21, 0, 0))),
        ("clickhouse", ClickHouseDialect((24, 1, 0))),
        ("snowflake", SnowflakeDialect()),
        ("firebird", FirebirdDialect((4, 0, 0))),
    ]


def render_type(dialect, dt) -> str:
    try:
        sql, _ = dialect.format_data_type(dt)
        return sql
    except Exception as exc:  # noqa: BLE001
        return f"<{type(exc).__name__}>"


def try_candidates(dialect, candidates) -> tuple:
    supported = dialect.supports_data_types()
    for cand in candidates:
        if cand.name in supported:
            try:
                cand.dialect = dialect
            except Exception:  # noqa: BLE001
                pass
            return cand, render_type(dialect, cand)
    return None, None


# ---------------------------------------------------------------------------
# A. list / tuple mapping
# ---------------------------------------------------------------------------


def probe_list(dialects) -> None:
    print("A. list/tuple mapping  (JSON vs ARRAY)")
    print(f"{'dialect':11} {'json':22} {'array[int]':28} {'array[text]':28}")
    for dname, d in dialects:
        j, jsql = try_candidates(d, [JsonType()])
        a1, a1sql = try_candidates(d, [ArrayType(element_type=IntegerType())])
        a2, a2sql = try_candidates(d, [ArrayType(element_type=TextType())])
        print(f"{dname:11} {jsql or '!unsupported':22} {a1sql or '!unsupported':28} {a2sql or '!unsupported':28}")


# ---------------------------------------------------------------------------
# B. enum strategy
# ---------------------------------------------------------------------------


def probe_enum(dialects) -> None:
    print()
    print("B. enum strategy  (generic enum -> native/suggested, else VARCHAR fallback)")
    values = [e.value for e in Color]
    for dname, d in dialects:
        native = EnumType(values=values)
        _, nsql = try_candidates(d, [native])
        vsql = render_type(d, _bound(d, VarCharType(length=255)))
        print(f"{dname:11} enum={nsql or '!not-supported':20} varchar-fallback={vsql}")


def _bound(dialect, dt):
    try:
        dt.dialect = dialect
    except Exception:  # noqa: BLE001
        pass
    return dt


# ---------------------------------------------------------------------------
# C. interval strategy
# ---------------------------------------------------------------------------


def probe_interval(dialects) -> None:
    print()
    print("C. timedelta/interval strategy  (INTERVAL, else BIGINT seconds fallback)")
    for dname, d in dialects:
        _, isql = try_candidates(d, [IntervalType()])
        bsql = render_type(d, _bound(d, IntegerType()))
        print(f"{dname:11} interval={isql or '!not-supported':22} bigint-fallback={bsql}")


# ---------------------------------------------------------------------------
# D. primary-key / auto-increment derivation
# ---------------------------------------------------------------------------


def probe_pk(dialects) -> None:
    print()
    print("D. primary-key derivation  (INTEGER PK + is_auto_increment)")
    for dname, d in dialects:
        try:
            supports = d.supports_auto_increment()
        except Exception as exc:  # noqa: BLE001
            supports = f"<{type(exc).__name__}>"
        constraints = [ColumnConstraint(d, ColumnConstraintType.PRIMARY_KEY, is_auto_increment=bool(supports) is True)]
        col = ColumnDefinition(d, "id", IntegerType(d), constraints=constraints)
        try:
            sql, _ = CreateTableExpression(d, "t", columns=[col]).to_sql()
        except Exception as exc:  # noqa: BLE001
            sql = f"<{type(exc).__name__}: {exc}>"
        print(f"{dname:11} supports_auto_increment={supports!s:6} {sql}")


# ---------------------------------------------------------------------------
# E. nullability derivation
# ---------------------------------------------------------------------------


class NullProbe(ActiveRecord):
    __table_name__ = "null_probe"

    id: int
    required_name: str
    optional_name: Optional[str]
    forced_not_null: Annotated[Optional[str], UseConstraint(ColumnConstraintType.NOT_NULL)]
    forced_null: Annotated[str, UseConstraint(ColumnConstraintType.NULL)]


def probe_nullability(dialects) -> None:
    print()
    print("E. nullability derivation")
    for fname, finfo in NullProbe.model_fields.items():
        ann = finfo.annotation
        optional = False
        markers = list(getattr(finfo, "metadata", ()) or ())
        import typing

        if typing.get_origin(ann) is typing.Union:
            args = [a for a in typing.get_args(ann) if a is not type(None)]
            optional = len(args) < len(typing.get_args(ann))
            ann = args[0] if len(args) == 1 else ann
        override = next((m for m in markers if isinstance(m, UseConstraint)), None)
        if override is not None:
            decision = f"explicit({override.constraint.constraint_type.name})"
        elif optional:
            decision = "auto: NULL"
        else:
            decision = "auto: (unspecified)"
        print(f"  {fname:18} optional={optional!s:5} -> {decision}")
    for dname, d in dialects[:2]:
        print(f"  [{dname}] rendering is exercised via column constraints (no DB needed)")


def main() -> None:
    dialects = dialect_instances()
    print("=" * 96)
    probe_list(dialects)
    probe_enum(dialects)
    probe_interval(dialects)
    probe_pk(dialects)
    probe_nullability(dialects)
    print("=" * 96)


if __name__ == "__main__":
    main()
