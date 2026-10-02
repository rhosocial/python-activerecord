# tests/rhosocial/activerecord_test/feature/backend/base/test_get_current_schema.py

"""The base class answers "which namespace?" when the backend cannot.

Ten backends implement ``get_current_schema`` by asking the server, and the
abstract base declares it too -- but as a method that raises rather than as an
abstract one. A backend whose server has no namespace to report is not missing
an implementation; it has a legitimate answer, and forcing every such backend to
write a method that raises would mean a subclass outside this repository fails at
instantiation for saying so.

The tests below pin that choice: the default must exist, must not be abstract,
and must say the same thing the per-backend overrides say.
"""

import pytest

from rhosocial.activerecord.backend.base import AsyncStorageBackend, StorageBackend
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect

_ABSTRACT_METHODS = (
    "connect",
    "disconnect",
    "ping",
    "_handle_error",
    "get_server_version",
    "introspect_and_adapt",
)


def _minimal_backend(base, *, is_async):
    """Build a subclass that satisfies every abstract method but this one.

    The point is what is *absent*: no ``get_current_schema`` here. If the base
    ever becomes abstract on this method, instantiating raises TypeError and
    these tests fail instead of quietly testing a signature that no third-party
    backend could satisfy.
    """
    namespace = {
        "__init__": lambda self, **kwargs: None,
        "dialect": property(lambda self: SQLiteDialect()),
    }
    for name in _ABSTRACT_METHODS:
        if is_async:

            async def _stub(self, *args, **kwargs):
                return None

        else:

            def _stub(self, *args, **kwargs):
                return None

        namespace[name] = _stub
    return type("MinimalBackend", (base,), namespace)


class TestBaseDeclaresTheMethod:
    def test_declared_on_both_bases(self):
        assert hasattr(StorageBackend, "get_current_schema")
        assert hasattr(AsyncStorageBackend, "get_current_schema")

    def test_declared_but_not_abstract(self):
        assert "get_current_schema" not in StorageBackend.__abstractmethods__
        assert "get_current_schema" not in AsyncStorageBackend.__abstractmethods__


class TestDefaultImplementation:
    def test_sync_default_raises_unsupported(self):
        backend = _minimal_backend(StorageBackend, is_async=False)()
        with pytest.raises(UnsupportedFeatureError) as excinfo:
            backend.get_current_schema()

        assert excinfo.value.feature_name == "get_current_schema"
        assert "get_current_schema" in str(excinfo.value)

    async def test_async_default_raises_unsupported(self):
        backend = _minimal_backend(AsyncStorageBackend, is_async=True)()
        with pytest.raises(UnsupportedFeatureError) as excinfo:
            await backend.get_current_schema()

        assert excinfo.value.feature_name == "get_current_schema"
        assert "get_current_schema" in str(excinfo.value)

    def test_override_is_what_replaces_it(self):
        """The default is only a floor; an override has to be reachable.

        Without this the tests above would still pass if some later change made
        the base method ignore a subclass that answers properly.
        """

        class Answering(_minimal_backend(StorageBackend, is_async=False)):
            def get_current_schema(self):
                return "reporting"

        assert Answering().get_current_schema() == "reporting"