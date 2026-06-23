# src/rhosocial/activerecord/backend/schema/snapshot.py
"""Immutable schema snapshot and builders (sync / async)."""

from __future__ import annotations

import importlib
import inspect
import typing
from dataclasses import MISSING, dataclass, field, fields as dc_fields
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

from ..introspection.base import SyncAbstractIntrospector, AsyncAbstractIntrospector
from ..introspection.types import (
    DatabaseInfo,
    TableInfo,
    ColumnInfo,
    IndexInfo,
    IndexColumnInfo,
    ForeignKeyInfo,
    TableType,
    ColumnNullable,
    IndexType,
    ReferentialAction,
)

if TYPE_CHECKING:
    from ..dialect.base import SQLDialectBase
    from ..expression.types._base import DataType


# ---------------------------------------------------------------------------
# Serialisation helpers (DataType <-> dict)
# ---------------------------------------------------------------------------

_MISSING = object()


def _data_type_to_dict(dt: "DataType") -> dict:
    """Serialize a ``DataType`` instance to a JSON-safe dict.

    Format: ``{"type": "fully.qualified.ClassName", "params": {...}}``
    """
    from ..expression.types._base import DataType

    sig = inspect.signature(dt.__init__)
    param_names = [p for p in sig.parameters if p not in ("self", "dialect")]
    params = {}
    for name in param_names:
        val = getattr(dt, name, _MISSING)
        if val is _MISSING:
            continue
        if isinstance(val, DataType):
            params[name] = _data_type_to_dict(val)
        elif isinstance(val, Enum):
            params[name] = val.value
        else:
            params[name] = val
    return {
        "type": f"{type(dt).__module__}.{type(dt).__qualname__}",
        "params": params,
    }


def _data_type_from_dict(data: dict) -> "DataType":
    """Reconstruct a ``DataType`` from a dict emitted by ``_data_type_to_dict``."""
    module_path, class_name = data["type"].rsplit(".", 1)
    module = importlib.import_module(module_path)
    cls = getattr(module, class_name)
    params = {}
    for k, v in data.get("params", {}).items():
        if isinstance(v, dict) and "type" in v:
            params[k] = _data_type_from_dict(v)
        elif isinstance(v, list):
            params[k] = list(v)
        else:
            params[k] = v
    return cls(**params)


# ---------------------------------------------------------------------------
# Generic dataclass <-> dict serialisation
# ---------------------------------------------------------------------------

_DC_TYPE_CACHE: Dict[type, Dict[str, type]] = {}

# Namespace for evaluating annotation strings that ``get_type_hints`` cannot
# resolve (e.g. ``"DataType"`` imported only under ``TYPE_CHECKING``).
_ANNOTATION_NS: Dict[str, Any] = {
    "str": str,
    "int": int,
    "float": float,
    "bool": bool,
    "datetime": datetime,
    "Any": Any,
    "Optional": Optional,
    "List": List,
    "Dict": Dict,
    "Tuple": Tuple,
    "ColumnNullable": ColumnNullable,
    "TableType": TableType,
    "IndexType": IndexType,
    "ReferentialAction": ReferentialAction,
    "DatabaseInfo": DatabaseInfo,
    "TableInfo": TableInfo,
    "ColumnInfo": ColumnInfo,
    "IndexInfo": IndexInfo,
    "IndexColumnInfo": IndexColumnInfo,
    "ForeignKeyInfo": ForeignKeyInfo,
    "DataType": None,  # marker — handled by content-based detection
}


def _resolve_forward_ref(t: type) -> type:
    """Recursively resolve ``ForwardRef`` or plain string types.

    Some Python versions (notably 3.8 with ``from __future__ import annotations``)
    fail to resolve particularly quoted forward references (e.g.
    ``"'DatabaseInfo'"``) inside a ``ForwardRef``, returning the ``ForwardRef``
    instance itself instead of the target class.  We work around this by
    manually stripping surrounding quotes and looking up the name.
    """
    _MAX_DEPTH = 20

    def _resolve(t: type, _depth: int = 0) -> type:
        if _depth > _MAX_DEPTH:
            return t
        if isinstance(t, typing.ForwardRef):
            arg = t.__forward_arg__
            # Strip outer quotes if the arg looks like a string literal.
            if len(arg) >= 2 and arg[0] in ("'", '"') and arg[-1] == arg[0]:
                arg = arg[1:-1]
            resolved = _ANNOTATION_NS.get(arg)
            if resolved is not None:
                return _resolve(resolved, _depth + 1)
            # Fall back to standard evaluation
            return _eval_type_safe(t)
        if isinstance(t, str):
            return _ANNOTATION_NS.get(t, t)
        origin = getattr(t, "__origin__", None)
        args = getattr(t, "__args__", None)
        if origin is not None and args:
            resolved_args = tuple(_resolve(a, _depth + 1) for a in args)
            if resolved_args == getattr(t, "__args__", None):
                return t
            try:
                return origin[resolved_args]
            except TypeError:
                return t
        return t

    return _resolve(t)


def _eval_type_safe(fwdref: typing.ForwardRef) -> type:
    """Call ``typing._eval_type`` with a compatible signature across Python versions.

    Python 3.15+ added a mandatory ``type_params`` positional parameter;
    older versions (3.8–3.14) do not accept it.
    """
    try:
        sig = inspect.signature(typing._eval_type)
        if "type_params" in sig.parameters:
            return typing._eval_type(fwdref, _ANNOTATION_NS, None, ())
    except (TypeError, ValueError):
        pass
    return typing._eval_type(fwdref, _ANNOTATION_NS, None)


def _resolve_field_types(cls: type) -> Dict[str, type]:
    """Resolve string annotations for a dataclass (with caching)."""
    if cls not in _DC_TYPE_CACHE:
        hints: Dict[str, type] = {}
        for f in dc_fields(cls):
            raw = f.type
            if isinstance(raw, str):
                resolved = _eval_type_safe(typing.ForwardRef(raw))
                hints[f.name] = _resolve_forward_ref(resolved)
            else:
                hints[f.name] = raw
        _DC_TYPE_CACHE[cls] = hints
    return _DC_TYPE_CACHE[cls]


def _to_plain(val: Any) -> Any:
    """Recursively convert a value tree to JSON-safe plain types."""
    if val is None:
        return None
    if isinstance(val, (str, int, float, bool)):
        return val
    if isinstance(val, datetime):
        return val.isoformat()
    if isinstance(val, Enum):
        return val.value
    if isinstance(val, tuple):
        return [_to_plain(v) for v in val]
    if isinstance(val, list):
        return [_to_plain(v) for v in val]
    if isinstance(val, dict):
        return {k: _to_plain(v) for k, v in val.items()}
    from ..expression.types._base import DataType
    if isinstance(val, DataType):
        return _data_type_to_dict(val)
    if hasattr(val, "__dataclass_fields__"):
        return {f.name: _to_plain(getattr(val, f.name)) for f in dc_fields(val)}
    return val


def _from_plain(t: type, data: Any) -> Any:
    """Reconstruct a value of type *t* from its plain representation."""
    if data is None:
        return None

    # Resolve any ForwardRef at the top level
    t = _resolve_forward_ref(t)

    origin = getattr(t, "__origin__", None)
    args = getattr(t, "__args__", (Any,))
    # Resolve ForwardRef / string type arguments (``from __future__
    # import annotations`` can produce nested ForwardRef that are not
    # automatically resolved inside parameterized types).
    args = tuple(_resolve_forward_ref(a) for a in args)

    # DataType (heuristic: dict has "type" key and is not a recognized type)
    if isinstance(data, dict) and "type" in data and "params" in data:
        return _data_type_from_dict(data)

    # Enum
    if isinstance(t, type) and issubclass(t, Enum):
        return t(data)

    # datetime
    if t is datetime:
        return datetime.fromisoformat(data)

    # tuple
    if origin is tuple and isinstance(data, list):
        return tuple(_from_plain(args[i] if i < len(args) else Any, v) for i, v in enumerate(data))

    # list / List[X]
    if origin is list and isinstance(data, list):
        elem_type = args[0] if args else Any
        return [_from_plain(elem_type, v) for v in data]

    # dict / Dict[K, V]
    if origin is dict and isinstance(data, dict):
        val_type = args[1] if len(args) > 1 else Any
        return {k: _from_plain(val_type, v) for k, v in data.items()}

    # Dataclass
    if isinstance(data, dict) and isinstance(t, type) and hasattr(t, "__dataclass_fields__"):
        hints = _resolve_field_types(t)
        kwargs = {}
        for f in dc_fields(t):
            if f.name in data:
                ft = hints.get(f.name, f.type)
                kwargs[f.name] = _from_plain(ft, data[f.name])
            elif f.default is not MISSING or f.default_factory is not MISSING:
                continue
        return t(**kwargs)

    return data


# ---------------------------------------------------------------------------
# SchemaSnapshot
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SchemaSnapshot:
    """Immutable point-in-time capture of a database schema.

    Fields
    ------
    dialect_class : str
        Fully-qualified class name of the dialect that produced this snapshot
        (e.g. ``"rhosocial.activerecord.backend.impl.postgres.dialect.PostgreSQLDialect"``).
        Used by ``SchemaDiffer`` for dialect compatibility check. Stored as a
        string so the snapshot is a pure data object that can be hashed,
        serialised, and compared without holding a runtime reference.
    captured_at : datetime
        UTC timestamp when the snapshot was taken.
    database_info : DatabaseInfo
        Vendor / version metadata from ``introspector.get_database_info()``.
    tables : Dict[str, TableInfo]
        Mapping of table name → ``TableInfo`` (columns, indexes, FKs).
    schema_name : Optional[str]
        The schema / database name scoped during capture.
    """

    dialect_class: str
    captured_at: datetime
    database_info: "DatabaseInfo"
    tables: Dict[str, "TableInfo"]
    schema_name: Optional[str] = None
    extra: Dict = field(default_factory=dict)

    # ----- JSON serialisation -----

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to a plain dict suitable for JSON dumping.

        ``DataType`` instances are expanded as
        ``{"type": "fully.qualified.ClassName", "params": {...}}``,
        ``datetime`` becomes ISO 8601, and ``Enum`` fields become their
        ``.value``.

        Roundtrip::

            snap2 = SchemaSnapshot.from_dict(snap.to_dict())
            assert snap2 == snap
        """
        return _to_plain(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "SchemaSnapshot":
        """Reconstruct a ``SchemaSnapshot`` from a dict (e.g. loaded from JSON).

        Inverse of ``to_dict``.
        """
        return _from_plain(cls, data)


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------


class SyncSchemaSnapshotBuilder:
    """Build a ``SchemaSnapshot`` synchronously.

    Usage::

        builder = SyncSchemaSnapshotBuilder(introspector, dialect)
        snapshot = builder.build(schema="public")
    """

    def __init__(self, introspector: SyncAbstractIntrospector, dialect: "SQLDialectBase"):
        self._introspector = introspector
        self._dialect = dialect

    def build(
        self,
        schema: Optional[str] = None,
        include_system: bool = False,
    ) -> SchemaSnapshot:
        self._introspector.invalidate_cache()
        db_info = self._introspector.get_database_info()
        table_list = self._introspector.list_tables(schema=schema, include_system=include_system)
        tables: Dict[str, "TableInfo"] = {}
        for tbl in table_list:
            full = self._introspector.get_table_info(tbl.name, schema=schema)
            if full is not None:
                tables[tbl.name] = full
        return SchemaSnapshot(
            dialect_class=f"{type(self._dialect).__module__}.{type(self._dialect).__qualname__}",
            captured_at=datetime.now(tz=timezone.utc),
            database_info=db_info,
            tables=tables,
            schema_name=schema,
        )


class AsyncSchemaSnapshotBuilder:
    """Build a ``SchemaSnapshot`` asynchronously.

    Usage::

        builder = AsyncSchemaSnapshotBuilder(introspector, dialect)
        snapshot = await builder.build(schema="public")
    """

    def __init__(self, introspector: AsyncAbstractIntrospector, dialect: "SQLDialectBase"):
        self._introspector = introspector
        self._dialect = dialect

    async def build(
        self,
        schema: Optional[str] = None,
        include_system: bool = False,
    ) -> SchemaSnapshot:
        self._introspector.invalidate_cache()
        db_info = await self._introspector.get_database_info()
        table_list = await self._introspector.list_tables(schema=schema, include_system=include_system)
        tables: Dict[str, "TableInfo"] = {}
        for tbl in table_list:
            full = await self._introspector.get_table_info(tbl.name, schema=schema)
            if full is not None:
                tables[tbl.name] = full
        return SchemaSnapshot(
            dialect_class=f"{type(self._dialect).__module__}.{type(self._dialect).__qualname__}",
            captured_at=datetime.now(tz=timezone.utc),
            database_info=db_info,
            tables=tables,
            schema_name=schema,
        )
