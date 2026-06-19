# tests/providers/registry.py
"""
Test Provider Registry

This module registers concrete implementations of test suite interfaces.
The registry system allows the test suite to be decoupled from specific
backend implementations, enabling the same tests to run against different
database backends.

Feature Detection in Testing
----------------------------
The test suite uses protocol-based feature detection to determine which
tests should run against which backends. Each backend implements various
protocols that indicate feature support, and tests can check for required
features before execution using isinstance() checks.

This approach enables:
1. Runtime feature detection based on protocol implementation
2. Backend-specific test execution
3. Flexible feature testing
4. Direct protocol-based feature checking

When a test needs to check for a feature, it can use isinstance() checks
against the appropriate protocol. Tests that require specific features
can check protocol implementation before execution.
"""

from rhosocial.activerecord.testsuite.core.registry import ProviderRegistry
from .basic import BasicProvider
from .events import EventsProvider
from .mixins import MixinsProvider
from .query import QueryProvider
from .basic_connection import BasicConnectionProvider
try:
    from .composite_pk import CompositePKProvider
    _HAS_COMPOSITE_PK = True
except ImportError:
    _HAS_COMPOSITE_PK = False
from .query_connection import QueryConnectionProvider
from .derived_field import DerivedFieldProvider
from .relation import RelationProvider
from .crud_benchmark import CrudBenchmarkProvider
from .fastapi_benchmark import FastAPIBenchmarkProvider
from .mixin_benchmark import MixinBenchmarkProvider
from .query_benchmark import QueryBenchmarkProvider
from .transaction_benchmark import TransactionBenchmarkProvider

# Create a single, global instance of the ProviderRegistry.
provider_registry = ProviderRegistry()

# Register the concrete `BasicProvider` as the implementation for the
# `feature.basic.IBasicProvider` interface defined in the testsuite.
# When the testsuite needs to run a "basic" feature test, it will ask the registry
# for the "feature.basic.IBasicProvider" and will receive our `BasicProvider`.
provider_registry.register("feature.basic.IBasicProvider", BasicProvider)

# Register the concrete `EventsProvider` as the implementation for the
# `feature.events.IEventsProvider` interface defined in the testsuite.
provider_registry.register("feature.events.IEventsProvider", EventsProvider)

# Register the concrete `MixinsProvider` as the implementation for the
# `feature.mixins.IMixinsProvider` interface defined in the testsuite.
provider_registry.register("feature.mixins.IMixinsProvider", MixinsProvider)

# Register the concrete `QueryProvider` as the implementation for the
# `feature.query.IQueryProvider` interface defined in the testsuite.
provider_registry.register("feature.query.IQueryProvider", QueryProvider)

# Register the concrete `BasicConnectionProvider` as the implementation for the
# `feature.basic.connection.IBasicConnectionProvider` interface defined in the testsuite.
provider_registry.register("feature.basic.connection.IBasicConnectionProvider", BasicConnectionProvider)

# Register the concrete `QueryConnectionProvider` as the implementation for the
# `feature.query.connection.IQueryConnectionProvider` interface defined in the testsuite.
provider_registry.register("feature.query.connection.IQueryConnectionProvider", QueryConnectionProvider)

provider_registry.register("feature.derived_field.IDerivedFieldProvider", DerivedFieldProvider)

provider_registry.register("feature.relation.IRelationProvider", RelationProvider)

# Register benchmark providers.
if _HAS_COMPOSITE_PK:
    provider_registry.register("feature.composite_pk.ICompositePKProvider", CompositePKProvider)

provider_registry.register("benchmark.crud.ICrudBenchmarkProvider", CrudBenchmarkProvider)
provider_registry.register("benchmark.query.IQueryBenchmarkProvider", QueryBenchmarkProvider)
provider_registry.register(
    "benchmark.transaction.ITransactionBenchmarkProvider",
    TransactionBenchmarkProvider,
)
provider_registry.register("benchmark.mixin.IMixinBenchmarkProvider", MixinBenchmarkProvider)
provider_registry.register("benchmark.fastapi.IFastAPIBenchmarkProvider", FastAPIBenchmarkProvider)
