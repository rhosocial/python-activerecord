# tests/providers/derived_field.py
import asyncio
import os
import tempfile
import uuid
from typing import Type, List

from rhosocial.activerecord.backend.expression import DropTableExpression, TableExpression
from rhosocial.activerecord.model import ActiveRecord, AsyncActiveRecord
from rhosocial.activerecord.backend.impl.sqlite.backend.async_backend import AsyncSQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.testsuite.feature.derived_field.interfaces import IDerivedFieldProvider
from rhosocial.activerecord.testsuite.feature.derived_field.fixtures.models import (
    Product,
    ProductFormA,
    ProductWithProxy,
    ProductWithColumnAndAdapter,
    AsyncProduct,
    AsyncProductWithProxy,
    AsyncProductWithColumnAndAdapter,
)
from .scenarios import get_enabled_scenarios, get_scenario


class DerivedFieldProvider(IDerivedFieldProvider):
    def __init__(self):
        self._scenario_db_files = {}
        self._active_backends = []
        self._active_async_backends = []

    def get_test_scenarios(self) -> List[str]:
        return list(get_enabled_scenarios().keys())

    def _setup_product_table(self, model_class, scenario_name):
        backend_class, config = get_scenario(scenario_name)
        if config.database != ":memory:":
            unique_filename = os.path.join(
                tempfile.gettempdir(),
                f"test_activerecord_{scenario_name}_{uuid.uuid4().hex}.sqlite",
            )
            self._scenario_db_files[scenario_name] = unique_filename
            config = SQLiteConnectionConfig(
                database=unique_filename,
                delete_on_close=config.delete_on_close,
                pragmas=config.pragmas,
            )
        model_class.configure(config, backend_class)
        backend = model_class.backend()
        backend.connect()
        backend.introspect_and_adapt()
        self._active_backends.append(backend)

        from rhosocial.activerecord.backend.options import ExecutionOptions
        from rhosocial.activerecord.backend.schema import StatementType
        from providers.fixtures.derived_field import TABLE_EXPRESSIONS

        options = ExecutionOptions(stmt_type=StatementType.DDL)
        drop_expr = DropTableExpression(
            dialect=backend.dialect,
            table=TableExpression(backend.dialect, "product"),
            if_exists=True,
        )
        backend.execute(*drop_expr.to_sql(), options=options)

        if fn := TABLE_EXPRESSIONS.get("product"):
            create_expr = fn(backend.dialect, "product")
            backend.execute(*create_expr.to_sql(), options=options)

        return model_class

    def _setup_async_product_table(self, model_class, scenario_name):
        _, config = get_scenario(scenario_name)
        if config.database != ":memory:":
            unique_filename = os.path.join(
                tempfile.gettempdir(),
                f"test_activerecord_{scenario_name}_{uuid.uuid4().hex}.sqlite",
            )
            self._scenario_db_files[scenario_name] = unique_filename
            config = SQLiteConnectionConfig(
                database=unique_filename,
                delete_on_close=config.delete_on_close,
                pragmas=config.pragmas,
            )

        async def _setup():
            await model_class.configure(config, AsyncSQLiteBackend)
            backend = model_class.backend()
            await backend.connect()
            await backend.introspect_and_adapt()
            self._active_async_backends.append(backend)

            from rhosocial.activerecord.backend.options import ExecutionOptions
            from rhosocial.activerecord.backend.schema import StatementType
            from providers.fixtures.derived_field import TABLE_EXPRESSIONS

            options = ExecutionOptions(stmt_type=StatementType.DDL)
            drop_expr = DropTableExpression(
                dialect=backend.dialect,
                table=TableExpression(backend.dialect, "product"),
                if_exists=True,
            )
            await backend.execute(*drop_expr.to_sql(), options=options)

            if fn := TABLE_EXPRESSIONS.get("product"):
                create_expr = fn(backend.dialect, "product")
                await backend.execute(*create_expr.to_sql(), options=options)

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

        if scenario_name in self._scenario_db_files:
            db_file = self._scenario_db_files.pop(scenario_name)
            if db_file and os.path.exists(db_file):
                try:
                    os.remove(db_file)
                except OSError:
                    pass
