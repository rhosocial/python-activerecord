# .experiments/field_type_adaptation.py
"""Experiment: ActiveRecord field definitions vs dialect data-type adaptation.

Goal
----
Prototype the Phase-1 type-resolution algorithm for "ActiveRecord derived DDL":

    Python field type (from the model)  ->  generic DataType (core mapping)
      ->  dialect.supports_data_types() / dialect.suggested_data_types()
      ->  rendered SQL type

and produce, for every installed backend dialect, a matrix plus a gap report.

The experiment deliberately reuses the existing dialect surface
(``supports_data_types`` / ``suggested_data_types`` / ``format_data_type``) and
adds nothing to it, proving no new protocol method is required.

Run::

    PYTHONPATH=tests .venv3.14-ubuntu26.04/bin/python .experiments/field_type_adaptation.py
"""

from __future__ import annotations

import typing
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from enum import Enum
from typing import Annotated, Optional, get_args, get_origin
from uuid import UUID

from rhosocial.activerecord.backend.expression.statements.ddl_table import (
    ColumnConstraint,
    ColumnConstraintType,
    ColumnDefinition,
    CreateTableExpression,
)
from rhosocial.activerecord.backend.expression.types import (
    ArrayType,
    BigIntType,
    BlobType,
    BooleanType,
    DateType,
    DateTimeType,
    DecimalType,
    DoubleType,
    EnumType,
    IntegerType,
    IntervalType,
    JsonType,
    TextType,
    TimeType,
    UUIDType,
    VarCharType,
)
from rhosocial.activerecord.base.fields import UseSqlType
from rhosocial.activerecord.model import ActiveRecord

# ---------------------------------------------------------------------------
# 1. Canonical Python type -> generic DataType (the core-side proposal)
# ---------------------------------------------------------------------------

PY_TO_GENERIC = {
    bool: BooleanType,
    int: IntegerType,
    float: DoubleType,
    Decimal: DecimalType,
    str: TextType,
    bytes: BlobType,
    datetime: DateTimeType,
    date: DateType,
    time: TimeType,
    timedelta: IntervalType,
    dict: JsonType,
    list: JsonType,
    tuple: JsonType,
    set: JsonType,
    UUID: UUIDType,
}


class Color(Enum):
    RED = "red"
    GREEN = "green"


def generic_for(py: type) -> Optional[object]:
    """Map a Python type to its canonical generic DataType instance."""
    if isinstance(py, type) and issubclass(py, Enum):
        return EnumType(values=[str(e.value) for e in py])
    factory = PY_TO_GENERIC.get(py)
    if factory is not None:
        return factory()
    if isinstance(py, type):
        if issubclass(py, str):
            return TextType()
        if issubclass(py, bool):
            return BooleanType()
        if issubclass(py, int):
            return IntegerType()
        if issubclass(py, float):
            return DoubleType()
        if issubclass(py, datetime):
            return DateTimeType()
        if issubclass(py, date):
            return DateType()
        if issubclass(py, bytes):
            return BlobType()
    return None


# ---------------------------------------------------------------------------
# 2. Annotation analysis (what the derivation engine must read off a model)
# ---------------------------------------------------------------------------


def analyze_annotation(ann: object) -> tuple:
    """Return (base_python_type, is_optional, markers).

    Unwraps ``Annotated[...]`` collecting marker instances and peels
    ``Optional``/``Union[..., None]`` down to the single non-None type.
    """
    markers = []
    while get_origin(ann) is Annotated:
        args = get_args(ann)
        ann = args[0]
        markers.extend(args[1:])
    optional = False
    if get_origin(ann) is typing.Union:
        args = [a for a in get_args(ann) if a is not type(None)]
        optional = len(args) < len(get_args(ann))
        if len(args) == 1:
            ann = args[0]
    return ann, optional, markers


# ---------------------------------------------------------------------------
# 3. Resolver: reuse supports_data_types() + suggested_data_types()
# ---------------------------------------------------------------------------


def instantiate_suggestion(repl: type, orig) -> tuple:
    """Instantiate a suggested DataType class, carrying the original's params.

    Suggestions are classes, and many are parameterised (e.g. ``MySQLEnumType``
    requires ``values``). Carry the original instance's ``get_params()`` over so
    the suggestion keeps the declaration's semantics.
    """
    params = orig.get_params() if hasattr(orig, "get_params") else {}
    try:
        return repl(**params), None
    except Exception as first:  # noqa: BLE001
        try:
            return repl(), None
        except Exception as second:  # noqa: BLE001
            return None, f"{type(first).__name__}/{type(second).__name__}: {second}"


def clone_with_dialect(dt, dialect):
    """Re-instantiate a DataType and bind the dialect (per-node binding).

    The model-declared markers are dialect-free (declaration time); the
    derivation must bind every node it emits. Re-instantiating avoids mutating
    the shared annotation instance bound to another dialect.
    """
    params = dict(dt.get_params()) if hasattr(dt, "get_params") else {}
    params.pop("dialect", None)
    try:
        clone = type(dt)(**params)
    except Exception:  # noqa: BLE001
        clone = dt
    try:
        clone.dialect = dialect
    except Exception:  # noqa: BLE001
        pass
    return clone


def resolve_type(py: type, dialect, use_sql_type: Optional[UseSqlType] = None) -> tuple:
    """Resolve (DataType | None, status, detail) for a Python type on a dialect.

    Priority: explicit UseSqlType candidates (first dialect-supported), then the
    canonical generic DataType, then the dialect's suggestion for that generic
    name. A suggestion that resolves to an unsupported name is reported as a
    broken/looping suggestion rather than silently accepted.
    """
    supported = dialect.supports_data_types()
    suggested = dialect.suggested_data_types()

    candidates = []
    if use_sql_type is not None:
        candidates.extend(use_sql_type.data_types)
    auto = generic_for(py)
    if auto is not None:
        candidates.append(auto)

    for cand in candidates:
        if cand.name in supported:
            return clone_with_dialect(cand, dialect), "ok", f"{cand.name}:supported"

    for cand in candidates:
        repl = suggested.get(cand.name)
        if repl is None:
            continue
        inst, err = instantiate_suggestion(repl, cand)
        if inst is None:
            return None, "suggestion-error", f"{cand.name}->{repl.__name__}:{err}"
        if inst.name in supported:
            return clone_with_dialect(inst, dialect), "ok", f"{cand.name}->{inst.name}:suggested"
        return None, "broken-suggestion", f"{cand.name}->{repl.__name__}(name={inst.name}):unsupported"

    name = auto.name if auto is not None else "?"
    return None, "gap", f"{name}:no support / no suggestion"


# ---------------------------------------------------------------------------
# 4. Sample model exercising the whole surface
# ---------------------------------------------------------------------------


class SampleRecord(ActiveRecord):
    __table_name__ = "sample_records"

    id: int
    name: str
    nickname: Optional[str]
    age: Optional[int]
    huge: Optional[int]
    score: Optional[float]
    balance: Optional[Decimal]
    active: bool = True
    raw: Optional[bytes]
    born: Optional[date]
    wake: Optional[time]
    created_at: Optional[datetime]
    elapsed: Optional[timedelta]
    payload: Optional[dict]
    tags: Optional[list]
    uid: Optional[UUID]
    color: Optional[Color]
    code: Annotated[str, UseSqlType(VarCharType(length=10))]


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


# ---------------------------------------------------------------------------
# 5. Matrix + gap report
# ---------------------------------------------------------------------------


def collect_fields():
    fields = []
    for fname, finfo in SampleRecord.model_fields.items():
        base, optional, markers = analyze_annotation(finfo.annotation)
        for meta in getattr(finfo, "metadata", ()) or ():
            if meta not in markers:
                markers.append(meta)
        override = next((m for m in markers if isinstance(m, UseSqlType)), None)
        fields.append((fname, base, optional, override))
    return fields


def main() -> None:
    dialects = dialect_instances()
    fields = collect_fields()
    names = [n for n, _ in dialects]

    print("=" * 100)
    print("Type-resolution matrix  (cell = rendered SQL type | status)")
    print("=" * 100)
    header = f"{'field':12} {'python':14} " + " ".join(f"{n:>16}" for n in names)
    print(header)
    print("-" * len(header))

    gaps: dict = {n: [] for n in names}
    for fname, base, optional, override in fields:
        pyname = getattr(base, "__name__", str(base))
        cells = []
        for dname, dialect in dialects:
            dt, status, detail = resolve_type(base, dialect, override)
            if status == "ok":
                try:
                    sql, _ = dialect.format_data_type(dt)
                except Exception as exc:  # noqa: BLE001
                    sql = f"<render {type(exc).__name__}>"
                    status = "render-error"
                    gaps[dname].append((fname, "render-error", detail))
                cells.append(sql)
            else:
                cells.append(f"!{status}")
                gaps[dname].append((fname, status, detail))
        print(f"{fname:12} {pyname:14} " + " ".join(f"{c:>16}" for c in cells))

    print()
    print("=" * 100)
    print("Gap / anomaly report (per dialect)")
    print("=" * 100)
    any_gap = False
    for dname in names:
        if gaps[dname]:
            any_gap = True
            print(f"\n[{dname}]")
            for fname, status, detail in gaps[dname]:
                print(f"  - {fname:12} {status:18} {detail}")
    if not any_gap:
        print("No gaps: every canonical Python type resolves on every dialect.")

    # Full CREATE TABLE rendering (end-to-end) for one dialect as a smoke test.
    print()
    print("=" * 100)
    print("End-to-end CREATE TABLE smoke test (per dialect)")
    print("=" * 100)
    for dname, dialect in dialects:
        cols = []
        skipped = []
        for fname, base, optional, override in fields:
            dt, status, _ = resolve_type(base, dialect, override)
            if status != "ok":
                skipped.append(f"{fname}({status})")
                continue
            constraints = []
            if fname == "id":
                constraints.append(ColumnConstraint(dialect, ColumnConstraintType.PRIMARY_KEY))
            elif not optional:
                constraints.append(ColumnConstraint(dialect, ColumnConstraintType.NOT_NULL))
            cols.append(ColumnDefinition(dialect, fname, dt, constraints=constraints))
        try:
            expr = CreateTableExpression(dialect, SampleRecord.__table_name__, columns=cols)
            sql, _ = expr.to_sql()
            note = f"  [skipped: {', '.join(skipped)}]" if skipped else ""
            print(f"\n[{dname}] {sql}{note}")
        except Exception as exc:  # noqa: BLE001
            print(f"\n[{dname}] FAILED: {type(exc).__name__}: {exc}")


if __name__ == "__main__":
    main()
