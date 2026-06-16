# tests/providers/composite_pk.py
import os
import sys
import logging
from typing import Type, List

from rhosocial.activerecord.model import ActiveRecord

logger = logging.getLogger(__name__)

from rhosocial.activerecord.testsuite.feature.composite_pk.fixtures.models import (
    OrderItem as OrderItemBase,
    StoreInventory as StoreInventoryBase,
    Order as OrderBase,
)
from rhosocial.activerecord.testsuite.feature.composite_pk.fixtures.models import (
    AsyncOrderItem as AsyncOrderItemBase,
    AsyncStoreInventory as AsyncStoreInventoryBase,
    AsyncOrder as AsyncOrderBase,
)

from providers.fixtures.composite_pk import TABLE_EXPRESSIONS


class CompositePKProvider:
    def __init__(self):
        self._scenario_db_files: dict = {}
        self._active_backends: list = []

    def get_test_scenarios(self) -> List[str]:
        from providers.scenarios import get_enabled_scenarios
        return list(get_enabled_scenarios().keys())

    def _setup_model(self, model_class: Type[ActiveRecord], scenario_name: str, table_name: str) -> Type[ActiveRecord]:
        from providers.scenarios import get_scenario
        backend_class, original_config = get_scenario(scenario_name)

        import os, tempfile, uuid
        config = original_config

        if original_config.database != ":memory:":
            unique_filename = os.path.join(
                tempfile.gettempdir(), f"test_activerecord_composite_{scenario_name}_{uuid.uuid4().hex}.sqlite"
            )
            self._scenario_db_files[scenario_name] = unique_filename
            from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
            config = SQLiteConnectionConfig(
                database=unique_filename,
                delete_on_close=original_config.delete_on_close,
                pragmas=original_config.pragmas,
            )

        model_class.configure(config, backend_class)

        from rhosocial.activerecord.backend.options import ExecutionOptions
        from rhosocial.activerecord.backend.schema import StatementType
        from rhosocial.activerecord.backend.expression import DropTableExpression, TableExpression

        try:
            drop_expr = DropTableExpression(
                dialect=model_class.__backend__.dialect,
                table=TableExpression(model_class.__backend__.dialect, table_name),
                if_exists=True,
            )
            model_class.__backend__.execute(
                *drop_expr.to_sql(), options=ExecutionOptions(stmt_type=StatementType.DDL)
            )
        except Exception:
            pass

        if fn := TABLE_EXPRESSIONS.get(table_name):
            create_expr = fn(model_class.__backend__.dialect, table_name)
            model_class.__backend__.execute(
                *create_expr.to_sql(), options=ExecutionOptions(stmt_type=StatementType.DDL)
            )
        else:
            raise ValueError(f"No table expression found for {table_name}")

        if model_class.__backend__ not in self._active_backends:
            self._active_backends.append(model_class.__backend__)

        return model_class

    async def _setup_async_model(self, model_class: Type[ActiveRecord], scenario_name: str, table_name: str) -> Type[ActiveRecord]:
        from providers.scenarios import get_scenario
        from rhosocial.activerecord.backend.impl.sqlite import AsyncSQLiteBackend

        backend_class = AsyncSQLiteBackend
        _, original_config = get_scenario(scenario_name)

        import os, tempfile, uuid
        config = original_config

        if original_config.database != ":memory:":
            unique_filename = os.path.join(
                tempfile.gettempdir(), f"test_activerecord_composite_{scenario_name}_{uuid.uuid4().hex}.sqlite"
            )
            self._scenario_db_files[scenario_name] = unique_filename
            from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
            config = SQLiteConnectionConfig(
                database=unique_filename,
                delete_on_close=original_config.delete_on_close,
                pragmas=original_config.pragmas,
            )

        await model_class.configure(config, backend_class)

        from rhosocial.activerecord.backend.options import ExecutionOptions
        from rhosocial.activerecord.backend.schema import StatementType
        from rhosocial.activerecord.backend.expression import DropTableExpression, TableExpression

        try:
            drop_expr = DropTableExpression(
                dialect=model_class.__backend__.dialect,
                table=TableExpression(model_class.__backend__.dialect, table_name),
                if_exists=True,
            )
            await model_class.__backend__.execute(
                *drop_expr.to_sql(), options=ExecutionOptions(stmt_type=StatementType.DDL)
            )
        except Exception:
            pass

        if fn := TABLE_EXPRESSIONS.get(table_name):
            create_expr = fn(model_class.__backend__.dialect, table_name)
            await model_class.__backend__.execute(
                *create_expr.to_sql(), options=ExecutionOptions(stmt_type=StatementType.DDL)
            )
        else:
            raise ValueError(f"No table expression found for {table_name}")

        if model_class.__backend__ not in self._active_backends:
            self._active_backends.append(model_class.__backend__)

        return model_class

    def setup_order_item_model(self, scenario_name: str) -> Type[ActiveRecord]:
        return self._setup_model(OrderItemBase, scenario_name, "order_items")

    def setup_store_inventory_model(self, scenario_name: str) -> Type[ActiveRecord]:
        return self._setup_model(StoreInventoryBase, scenario_name, "store_inventory")

    def setup_order_model(self, scenario_name: str) -> Type[ActiveRecord]:
        return self._setup_model(OrderBase, scenario_name, "orders")

    async def setup_async_order_item_model(self, scenario_name: str) -> Type[ActiveRecord]:
        return await self._setup_async_model(AsyncOrderItemBase, scenario_name, "order_items")

    async def setup_async_store_inventory_model(self, scenario_name: str) -> Type[ActiveRecord]:
        return await self._setup_async_model(AsyncStoreInventoryBase, scenario_name, "store_inventory")

    async def setup_async_order_model(self, scenario_name: str) -> Type[ActiveRecord]:
        return await self._setup_async_model(AsyncOrderBase, scenario_name, "orders")

    def cleanup_after_test(self, scenario_name: str):
        from providers.scenarios import get_scenario
        _, config = get_scenario(scenario_name)

        for backend in self._active_backends:
            try:
                from rhosocial.activerecord.backend.options import ExecutionOptions
                from rhosocial.activerecord.backend.schema import StatementType
                from rhosocial.activerecord.backend.expression import DropTableExpression, TableExpression

                for table in ("order_items", "store_inventory", "orders"):
                    try:
                        drop_expr = DropTableExpression(
                            dialect=backend.dialect,
                            table=TableExpression(backend.dialect, table),
                            if_exists=True,
                        )
                        backend.execute(
                            *drop_expr.to_sql(), options=ExecutionOptions(stmt_type=StatementType.DDL)
                        )
                    except Exception:
                        pass
                backend.disconnect()
            except Exception:
                pass

        self._active_backends.clear()

        if config.database != ":memory:" and scenario_name in self._scenario_db_files:
            db_path = self._scenario_db_files[scenario_name]
            try:
                if os.path.exists(db_path):
                    os.remove(db_path)
            except OSError:
                pass

    async def cleanup_after_test_async(self, scenario_name: str):
        from providers.scenarios import get_scenario
        _, config = get_scenario(scenario_name)

        for backend in self._active_backends:
            try:
                from rhosocial.activerecord.backend.options import ExecutionOptions
                from rhosocial.activerecord.backend.schema import StatementType
                from rhosocial.activerecord.backend.expression import DropTableExpression, TableExpression

                for table in ("order_items", "store_inventory", "orders"):
                    try:
                        drop_expr = DropTableExpression(
                            dialect=backend.dialect,
                            table=TableExpression(backend.dialect, table),
                            if_exists=True,
                        )
                        await backend.execute(
                            *drop_expr.to_sql(), options=ExecutionOptions(stmt_type=StatementType.DDL)
                        )
                    except Exception:
                        pass
                await backend.disconnect()
            except Exception:
                pass

        self._active_backends.clear()

        if config.database != ":memory:" and scenario_name in self._scenario_db_files:
            db_path = self._scenario_db_files[scenario_name]
            try:
                if os.path.exists(db_path):
                    os.remove(db_path)
            except OSError:
                pass
