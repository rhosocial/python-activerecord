# src/rhosocial/activerecord/base/ddl/contracts.py
"""Type contracts for the DDL model declaration interfaces (Gate 0).

Each overridable DDL interface declares the expression base its return value
must satisfy, so the framework can reject a mis-declared candidate independently
of the backend. The backend then only decides "can I render it" (Gates 1-2).
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Type

from ...backend.expression.statements.ddl_partition import PartitionClause
from ...backend.expression.statements.ddl_table import (
    ColumnConstraint,
    CreateTableOptions,
    GeneratedColumnExpression,
    IndexDefinition,
    StorageOptionsExpression,
    TableConstraint,
)
from .attributes import ColumnAttribute
from .options import ColumnOptions


class DeclarationContract:
    """The expected shape of one DDL interface's return value.

    ``additive`` distinguishes the list semantics: ``True`` keeps **every**
    applicable candidate (composite indexes / constraints); ``False`` treats a
    list as **alternatives** and selects the first applicable one (partition,
    options, per-column single attributes).
    """

    def __init__(
        self,
        base: Optional[Type[Any]] = None,
        additive: bool = False,
        optional: bool = True,
    ):
        self.base = base
        self.additive = additive
        self.optional = optional

    def normalize(self, declared: Any) -> List[Any]:
        """Normalize "expression or list" into a list of candidates."""
        if declared is None:
            return []
        if isinstance(declared, (list, tuple)):
            return list(declared)
        return [declared]

    def validate(self, candidate: Any, interface: str) -> None:
        """Gate 0: the candidate must be an instance of the contract base."""
        if self.base is None:
            return
        if not isinstance(candidate, self.base):
            raise TypeError(
                f"{interface}() returned {type(candidate).__name__}; expected "
                f"{self.base.__name__} or a subclass."
            )


TABLE_CONTRACTS: Dict[str, DeclarationContract] = {
    "table_options": DeclarationContract(CreateTableOptions),
    "table_storage_options": DeclarationContract(StorageOptionsExpression),
    "table_partition": DeclarationContract(PartitionClause),
    "table_indexes": DeclarationContract(IndexDefinition, additive=True),
    "table_constraints": DeclarationContract(TableConstraint, additive=True),
}

COLUMN_CONTRACTS: Dict[str, DeclarationContract] = {
    # Physical column name: a plain str, directly usable as the ``name``
    # construction parameter of ``ColumnDefinition`` (§5.5).
    "column_name": DeclarationContract(str),
    # Exempt from a type contract (B9): ``column_type`` returns dialect-free
    # type candidates (a ``UseSqlType`` marker, a ``DataType``, or a list of
    # them) which the deriver resolves per dialect through the type resolver
    # (``base.ddl.types.ColumnTypeResolver``) — not directly usable as an
    # expression construction parameter, so Gate 0 does not apply.
    "column_type": DeclarationContract(None),
    "column_constraints": DeclarationContract(ColumnConstraint, additive=True),
    "column_attributes": DeclarationContract(ColumnAttribute, additive=True),
    "column_comment": DeclarationContract(None),
    "generated_column": DeclarationContract(GeneratedColumnExpression),
    "column_options": DeclarationContract(ColumnOptions),
}
