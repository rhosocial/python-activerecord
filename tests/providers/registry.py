from rhosocial.activerecord.testsuite.core.registry import ProviderRegistry
from .basic import BasicProvider
from .events import EventsProvider
from .mixins import MixinsProvider

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

# As we migrate more test groups (e.g., relations, query), we will add
# their provider registrations here.
#
# Example:
# from .relations import RelationsProvider
# provider_registry.register("feature.relations.IRelationsProvider", RelationsProvider)