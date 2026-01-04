# src/rhosocial/activerecord/backend/options.py
"""
This module defines classes for encapsulating execution options for the backend.
Using the Options pattern keeps method signatures clean and makes the API
extensible without introducing breaking changes.
"""
from dataclasses import dataclass
from typing import Optional, Dict, Tuple, Type, List

from .expression import SQLPredicate
from .schema import StatementType
from .type_adapter import SQLTypeAdapter


@dataclass
class ExecutionOptions:
    """
    Encapsulates all options for a single, low-level backend execution.
    This object is the single source of truth for controlling how a query is
    executed and how its results are processed.
    """
    # Essential: The type of SQL statement being executed (DQL, DML, etc.).
    # This dictates key backend behavior, such as result set processing.
    stmt_type: StatementType

    # A dictionary mapping database column names to type adapters.
    # Used to convert database-native types back into Python types during
    # result set processing.
    column_adapters: Optional[Dict[str, Tuple[SQLTypeAdapter, Type]]] = None

    # A dictionary for remapping column names from the database result set
    # to different field names in the final Python dictionary.
    column_mapping: Optional[Dict[str, str]] = None


@dataclass
class InsertOptions:
    """Encapsulates all options for a high-level `insert` operation."""
    # The name of the table to insert into.
    table: str
    # A dictionary of column names to values for the new record.
    data: Dict

    # See ExecutionOptions for details on these result-processing parameters.
    column_adapters: Optional[Dict[str, Tuple[SQLTypeAdapter, Type]]] = None
    column_mapping: Optional[Dict[str, str]] = None

    # If True, commits the transaction if one is not already active.
    auto_commit: Optional[bool] = True
    # The name of the primary key field. (Used by some backends for RETURNING emulation).
    primary_key: Optional[str] = None
    # Columns to include in the RETURNING clause.
    returning_columns: Optional[List[str]] = None


@dataclass
class UpdateOptions:
    """Encapsulates all options for a high-level `update` operation."""
    # The name of the table to update.
    table: str
    # A dictionary of column names to their new values.
    data: Dict
    # The WHERE clause, as a structured SQLPredicate object.
    where: SQLPredicate

    # See ExecutionOptions for details on these result-processing parameters.
    column_adapters: Optional[Dict[str, Tuple[SQLTypeAdapter, Type]]] = None
    column_mapping: Optional[Dict[str, str]] = None

    # If True, commits the transaction if not already active.
    auto_commit: bool = True
    # Columns to include in the RETURNING clause.
    returning_columns: Optional[List[str]] = None


@dataclass
class DeleteOptions:
    """Encapsulates all options for a `delete` operation."""
    # The name of the table to delete from.
    table: str
    # The WHERE clause, as a structured SQLPredicate object.
    where: SQLPredicate

    # See ExecutionOptions for details on these result-processing parameters.
    column_adapters: Optional[Dict[str, Tuple[SQLTypeAdapter, Type]]] = None
    column_mapping: Optional[Dict[str, str]] = None

    # If True, commits the transaction if not already active.
    auto_commit: bool = True
    # Columns to include in the RETURNING clause.
    returning_columns: Optional[List[str]] = None