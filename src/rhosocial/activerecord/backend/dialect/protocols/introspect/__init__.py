"""Reading the catalogue, and controlling transactions.

Introspection is split into four families, each a same-stem protocol/mixin
pair whose stem is the family name ending in ``Introspection``:

* :mod:`~.structure` -- what the catalogue declares an object to be;
* :mod:`~.operational_stats` -- how the objects have behaved;
* :mod:`~.data_profile` -- what the rows in a column look like;
* :mod:`~.ddl_extraction` -- the text that would recreate an object.

Each family renders the queries that read a live engine's catalogue, which is
the opposite direction from every other protocol here: it builds a query
rather than reading an expression the caller supplied. The families are split
by the question asked -- declaration, behaviour, data, retained text -- so a
dialect can answer one without claiming the others.

``TransactionControlSupport`` belongs beside them only because both describe
the session rather than a statement about objects.
"""

from .structure import StructureIntrospectionSupport, AsyncStructureIntrospectionSupport
from .operational_stats import (
    OperationalStatsIntrospectionSupport,
    AsyncOperationalStatsIntrospectionSupport,
)
from .data_profile import DataProfileIntrospectionSupport, AsyncDataProfileIntrospectionSupport
from .ddl_extraction import DdlExtractionIntrospectionSupport, AsyncDdlExtractionIntrospectionSupport
from .transaction import TransactionControlSupport

__all__ = [
    "StructureIntrospectionSupport",
    "AsyncStructureIntrospectionSupport",
    "OperationalStatsIntrospectionSupport",
    "AsyncOperationalStatsIntrospectionSupport",
    "DataProfileIntrospectionSupport",
    "AsyncDataProfileIntrospectionSupport",
    "DdlExtractionIntrospectionSupport",
    "AsyncDdlExtractionIntrospectionSupport",
    "TransactionControlSupport",
]
