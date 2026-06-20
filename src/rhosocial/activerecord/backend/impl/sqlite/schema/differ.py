# src/rhosocial/activerecord/backend/impl/sqlite/schema/differ.py
"""SQLite schema differ — uses default column equivalence."""

from ....schema.differ import SchemaDiffer


class SQLiteSchemaDiffer(SchemaDiffer):
    """SQLite schema differ.

    SQLite has no column-order semantics, so the default
    ``_columns_equivalent`` is sufficient — only type, nullability,
    and default value are compared.
    """
    pass
