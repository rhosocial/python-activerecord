# tests/providers/derived_field.py
import asyncio
from typing import Type, List

from rhosocial.activerecord.model import ActiveRecord, AsyncActiveRecord
from rhosocial.activerecord.backend.impl.sqlite.backend.async_backend import AsyncSQLiteBackend
from rhosocial.activerecord.testsuite.feature.derived_field.interfaces import IDerivedFieldProvider
from rhosocial.activerecord.testsuite.feature.derived_field.fixtures.models import (
    Product, ProductFormA, ProductWithProxy, ProductWithColumnAndAdapter,
    AsyncProduct, AsyncProductWithProxy, AsyncProductWithColumnAndAdapter,
)
from .scenarios import get_enabled_scenarios, get_scenario


PRODUCT_SCHEMA = """
    CREATE TABLE IF NOT EXISTS product (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        price REAL NOT NULL,
        quantity INTEGER NOT NULL
    );
    DELETE FROM product;
"""


class DerivedFieldProvider(IDerivedFieldProvider):

    def __init__(self):
        self._active_backends = []
        self._active_async_backends = []

    def get_test_scenarios(self) -> List[str]:
        return list(get_enabled_scenarios().keys())

    def _setup_product_table(self, model_class, scenario_name):
        backend_class, config = get_scenario(scenario_name)
        model_class.configure(config, backend_class)
        backend = model_class.backend()
        backend.connect()
        backend.introspect_and_adapt()
        self._active_backends.append(backend)
        backend.executescript(PRODUCT_SCHEMA)
        return model_class

    def _setup_async_product_table(self, model_class, scenario_name):
        _, config = get_scenario(scenario_name)

        async def _setup():
            await model_class.configure(config, AsyncSQLiteBackend)
            backend = model_class.backend()
            await backend.connect()
            await backend.introspect_and_adapt()
            self._active_async_backends.append(backend)
            await backend.executescript(PRODUCT_SCHEMA)

        asyncio.run(_setup())
        return model_class

    def setup_product_model(self, scenario_name: str) -> Type[ActiveRecord]:
        return self._setup_product_table(Product, scenario_name)

    def setup_product_form_a_model(self, scenario_name: str) -> Type[ActiveRecord]:
        return self._setup_product_table(ProductFormA, scenario_name)

    def setup_product_with_proxy_model(self, scenario_name: str) -> Type[ActiveRecord]:
        return self._setup_product_table(ProductWithProxy, scenario_name)

    def setup_product_with_column_and_adapter_model(self, scenario_name: str) -> Type[ActiveRecord]:
        return self._setup_product_table(ProductWithColumnAndAdapter, scenario_name)

    def setup_async_product_model(self, scenario_name: str) -> Type[AsyncActiveRecord]:
        return self._setup_async_product_table(AsyncProduct, scenario_name)

    def setup_async_product_with_proxy_model(self, scenario_name: str) -> Type[AsyncActiveRecord]:
        return self._setup_async_product_table(AsyncProductWithProxy, scenario_name)

    def setup_async_product_with_column_and_adapter_model(self, scenario_name: str) -> Type[AsyncActiveRecord]:
        return self._setup_async_product_table(AsyncProductWithColumnAndAdapter, scenario_name)

    def cleanup_after_test(self, scenario_name: str) -> None:
        for backend in self._active_backends:
            try:
                backend.disconnect()
            except Exception:
                pass
        self._active_backends.clear()
        for backend in self._active_async_backends:
            try:
                asyncio.run(backend.disconnect())
            except Exception:
                pass
        self._active_async_backends.clear()
