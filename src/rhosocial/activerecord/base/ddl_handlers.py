# src/rhosocial/activerecord/base/ddl_handlers.py
"""
Validation for DDL-related model declarations.

Registered via ``DDLMixin`` in ``base/ddl_mixin.py``.

``DDLModelAnnotationHandler``
    Validates model-level DDL declarations at class-creation time:

    - ``__table_options__``      must be a ``TableOptions`` (or None)
    - ``__table_indexes__``      entries must be ``IndexDefinition`` /
                                 ``DDLSpec`` / dict; duplicate index names
                                 rejected
    - ``__table_constraints__``  entries must be constraints or ``DDLSpec``
    - ``__table_partition__``    entries must be ``PartitionSpec`` instances

    **No derived state is stored.** The declarations themselves are the only
    source of truth; ``ModelSchemaGenerator`` reads them directly at
    ``generate_create_table(dialect)`` time. Field-level ``Annotated`` markers
    (``UseSqlType`` / ``UseConstraint`` / ``UseIndex``) are likewise read at
    generation time from ``model_fields[name].metadata``.
"""

from typing import Any, List, Optional

from .ddl import IndexDefinition
from ..backend.expression.statements.ddl_spec import DDLSpec, PartitionSpec


class DDLModelAnnotationHandler:
    """Validate model-level DDL declarations at class-creation time.

    No derived attributes are written — the declared constants remain the
    single source of truth, consumed directly by the generator.
    """

    @staticmethod
    def handle(new_class: type) -> None:
        raw_indexes: Optional[List[Any]] = (
            getattr(new_class, "__table_indexes__", None) or []
        )
        seen_names: set = set()
        _check = DDLModelAnnotationHandler._validate_index
        for entry in raw_indexes:
            idx = _check(entry)
            if idx is not None and idx.name:
                if idx.name in seen_names:
                    raise ValueError(
                        f"Duplicate index name '{idx.name}' on "
                        f"'{new_class.__name__}'."
                    )
                seen_names.add(idx.name)

        raw_partitions: List[Any] = (
            getattr(new_class, "__table_partition__", None) or []
        )
        for entry in raw_partitions:
            if not isinstance(entry, PartitionSpec):
                raise TypeError(
                    f"__table_partition__ entries must be PartitionSpec "
                    f"instances, got {type(entry).__name__}: {entry!r}"
                )

    @staticmethod
    def _validate_index(entry: Any) -> Optional[IndexDefinition]:
        if isinstance(entry, (IndexDefinition, DDLSpec)):
            return entry
        if isinstance(entry, dict):
            try:
                return IndexDefinition(**entry)
            except TypeError as exc:
                raise ValueError(
                    f"Invalid IndexDefinition dict in '__table_indexes__': {exc}"
                ) from exc
        raise TypeError(
            f"__table_indexes__ entries must be IndexDefinition, DDLSpec or dict, "
            f"got {type(entry).__name__}: {entry!r}"
        )
