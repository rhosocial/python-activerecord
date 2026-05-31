# tests/providers/derived_field.py
from typing import Type, List

from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.testsuite.feature.derived_field.interfaces import IDerivedFieldProvider
from rhosocial.activerecord.testsuite.feature.derived_field.fixtures.models import (
    Product, ProductFormA, ProductWithProxy,
)
from .scenarios import get_enabled_scenarios, get_scenario


class DerivedFieldProvider(IDerivedFieldProvider):

    def __init__(self):
        self._active_backends = []

    def get_test_scenarios(self) -> List[str]:
        return list(get_enabled_scenarios().keys())

    def setup_product_model(self, scenario_name: str) -> Type[ActiveRecord]:
        backend_class, config = get_scenario(scenario_name)
        Product.configure(config, backend_class)
        backend = Product.backend()
        backend.connect()
        backend.introspect_and_adapt()
        self._active_backends.append(backend)
        backend.executescript("""
            CREATE TABLE IF NOT EXISTS product (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                price REAL NOT NULL,
                quantity INTEGER NOT NULL
            );
            DELETE FROM product;
        """)
        return Product

    def setup_product_form_a_model(self, scenario_name: str) -> Type[ActiveRecord]:
        backend_class, config = get_scenario(scenario_name)
        ProductFormA.configure(config, backend_class)
        backend = ProductFormA.backend()
        backend.connect()
        backend.introspect_and_adapt()
        self._active_backends.append(backend)
        backend.executescript("""
            CREATE TABLE IF NOT EXISTS product (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                price REAL NOT NULL,
                quantity INTEGER NOT NULL
            );
            DELETE FROM product;
        """)
        return ProductFormA

    def setup_product_with_proxy_model(self, scenario_name: str) -> Type[ActiveRecord]:
        backend_class, config = get_scenario(scenario_name)
        ProductWithProxy.configure(config, backend_class)
        backend = ProductWithProxy.backend()
        backend.connect()
        backend.introspect_and_adapt()
        self._active_backends.append(backend)
        backend.executescript("""
            CREATE TABLE IF NOT EXISTS product (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                price REAL NOT NULL,
                quantity INTEGER NOT NULL
            );
            DELETE FROM product;
        """)
        return ProductWithProxy

    def cleanup_after_test(self, scenario_name: str) -> None:
        for backend in self._active_backends:
            try:
                backend.disconnect()
            except Exception:
                pass
        self._active_backends.clear()
