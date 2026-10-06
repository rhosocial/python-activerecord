"""Reading the catalogue, and controlling transactions.

``IntrospectionSupport`` renders the queries that read a live engine's
catalogue -- tables, columns, indexes, views, triggers -- which is the opposite
direction from every other protocol here: it builds a query rather than
reading an expression the caller supplied.

``TransactionControlSupport`` belongs beside it only because both describe the
session rather than a statement about objects.
"""

from .introspection import IntrospectionSupport
from .transaction import TransactionControlSupport

__all__ = [
    "IntrospectionSupport",
    "TransactionControlSupport",
]
