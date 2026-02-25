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
