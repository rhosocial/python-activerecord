# src/rhosocial/activerecord/base/ddl_handlers.py
"""
Metaclass feature handlers for DDL-related model declarations.

Registered via ``DDLMixin`` in ``base/ddl_mixin.py``.

``DDLFieldAnnotationHandler``
    Reads per-field ``Annotated[T, ...]`` DDL markers and stores three dicts:

    - ``__table_field_sql_types__``   ``{field_name: UseSqlType}``
    - ``__table_field_indexes__``     ``{field_name: [IndexDefinition, ...]}``
    - ``__table_field_constraints__`` ``{field_name: [ColumnConstraint, ...]}``

``DDLModelAnnotationHandler``
    Reads model-level ``__table_options__``, ``__table_indexes__``, ``__table_constraints__``
    and attaches final, validated collections:

    - ``__ddl_indexes__``         ``List[IndexDefinition]``
    - ``__ddl_table_options__``   ``Optional[TableOptions]``
    - ``__ddl_constraints__``     ``List[TableConstraint]``

    Field-level ``UseIndex`` entries (from ``__table_field_indexes__``) are
    automatically merged into ``__ddl_indexes__``.

Both handlers raise ``TypeError`` when re-invoked on an already-processed class.
"""

from typing import (
    Any,
    ClassVar,
    Dict,
    List,
    Optional,
    get_origin,
    get_type_hints,
)

from .ddl import IndexDefinition, TableConstraint
from .fields import UseConstraint, UseIndex, UseSqlType


def _skip_classvar(field_type: Any) -> bool:
    """Return True when *field_type* is a bare ``ClassVar`` annotation."""
    return get_origin(field_type) is ClassVar


class DDLFieldAnnotationHandler:
    """Process ``UseSqlType`` / ``UseIndex`` / ``UseConstraint`` annotations
    on model fields and store structured metadata as class attributes."""

    @staticmethod
    def handle(new_class: type) -> None:
        for attr in (
            "__table_field_sql_types__",
            "__table_field_indexes__",
            "__table_field_constraints__",
        ):
            if attr in new_class.__dict__:
                raise TypeError(
                    f"Class '{new_class.__name__}' already defines '{attr}'. "
                    "DDL field handler may only be run once per class."
                )

        hints: Dict[str, Any]
        try:
            hints = get_type_hints(new_class, include_extras=True)
        except (NameError, AttributeError, TypeError):
            # Python 3.8's typing.get_type_hints has no ``include_extras``;
            # typing_extensions backports it, preserving Annotated metadata.
            try:
                from typing_extensions import get_type_hints as _te_get_type_hints

                hints = _te_get_type_hints(new_class, include_extras=True)
            except (ImportError, NameError, AttributeError, TypeError):
                hints = getattr(new_class, "__annotations__", {})

        sql_types: Dict[str, UseSqlType] = {}
        indexes: Dict[str, List[IndexDefinition]] = {}
        constraints: Dict[str, List] = {}

        for field_name, field_type in hints.items():
            if _skip_classvar(field_type):
                continue
            col_name = (
                new_class.get_column_name(field_name)
                if hasattr(new_class, "get_column_name")
                else field_name
            )
            if not hasattr(field_type, "__metadata__"):
                continue
            seen_sql_type = False
            for meta in field_type.__metadata__:
                if isinstance(meta, UseSqlType) and meta.data_type is not None:
                    if seen_sql_type:
                        raise TypeError(
                            f"Field {field_name!r} declares multiple UseSqlType "
                            f"markers. Combine the types into a single "
                            f"UseSqlType(type_a, type_b, ...) instead."
                        )
                    seen_sql_type = True
                    sql_types[field_name] = meta
                elif isinstance(meta, UseIndex):
                    indexes.setdefault(field_name, []).append(
                        meta.to_index_definition(col_name)
                    )
                elif isinstance(meta, UseConstraint):
                    constraints.setdefault(field_name, []).append(meta.constraint)

        new_class.__table_field_sql_types__ = sql_types
        new_class.__table_field_indexes__ = indexes
        new_class.__table_field_constraints__ = constraints


class DDLModelAnnotationHandler:
    """Read ``__table_options__``, ``__table_indexes__``, ``__table_constraints__``
    class variables and write the final, merged collections to the class.

    Merges field-level ``UseIndex`` entries (``__table_field_indexes__``) into
    ``__ddl_indexes__`` with duplicate-name detection.
    """

    @staticmethod
    def handle(new_class: type) -> None:
        for attr in (
            "__ddl_indexes__",
            "__ddl_table_options__",
            "__ddl_constraints__",
        ):
            if attr in new_class.__dict__:
                raise TypeError(
                    f"Class '{new_class.__name__}' already defines '{attr}'. "
                    "DDL model handler may only be run once per class (directly defined, not inherited)."
                )

        new_class.__ddl_table_options__ = getattr(new_class, "__table_options__", None)

        constraint_list: List[TableConstraint] = list(
            getattr(new_class, "__table_constraints__", None) or []
        )
        new_class.__ddl_constraints__ = constraint_list

        raw_indexes: Optional[List[Any]] = (
            getattr(new_class, "__table_indexes__", None) or []
        )
        model_indexes: List[IndexDefinition] = []
        seen_names: set = set()
        _check = DDLModelAnnotationHandler._validate_index
        for entry in raw_indexes:
            idx = _check(entry)
            if idx:
                if idx.name in seen_names:
                    raise ValueError(
                        f"Duplicate index name '{idx.name}' on "
                        f"'{new_class.__name__}'."
                    )
                seen_names.add(idx.name)
                model_indexes.append(idx)

        field_dict: Dict[str, List[IndexDefinition]] = getattr(
            new_class, "__table_field_indexes__", {}
        )
        for field_name, defs in field_dict.items():
            for idx in defs:
                if idx.name in seen_names:
                    raise ValueError(
                        f"Duplicate index name '{idx.name}' on "
                        f"'{new_class.__name__}' (UseIndex on field "
                        f"'{field_name}')."
                    )
                seen_names.add(idx.name)
                model_indexes.append(idx)

        new_class.__ddl_indexes__ = model_indexes

    @staticmethod
    def _validate_index(entry: Any) -> Optional[IndexDefinition]:
        if isinstance(entry, IndexDefinition):
            return entry
        if isinstance(entry, dict):
            try:
                return IndexDefinition(**entry)
            except TypeError as exc:
                raise ValueError(
                    f"Invalid IndexDefinition dict in '__table_indexes__': {exc}"
                ) from exc
        raise TypeError(
            f"__table_indexes__ entries must be IndexDefinition or dict, "
            f"got {type(entry).__name__}: {entry!r}"
        )