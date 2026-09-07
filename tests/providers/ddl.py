# tests/providers/ddl.py
"""
Provider for the ``feature.ddl`` testsuite group.

Derivation is the feature under test: the models' declared constants and
field annotations are the single source of truth, and the provider executes
exactly what ``Model.generate_create_table(dialect)`` produces — no
hand-written schema. This exercises the model -> DDL -> live database round
trip on SQLite.
"""

from typing import List, Type

from rhosocial.activerecord.model import ActiveRecord

from rhosocial.activerecord.testsuite.feature.ddl.interfaces import (
    IDDLAsyncProvider,
    IDDLSyncProvider,
)
from rhosocial.activerecord.testsuite.feature.ddl.fixtures.models import (
    AsyncBareItem,
    AsyncCapabilityPost,
    AsyncSpecComment,
    AsyncSpecOrder,
    BareItem,
    CapabilityPost,
    SpecComment,
    SpecOrder,
)
from .scenarios import get_enabled_scenarios


class _ScenarioFileMixin:
    """Per-provider reuse of file-based scenario databases so that multiple
    models set up within one test land on the same database file."""

    def __init__(self):
        self._scenario_db_files = {}

    def _resolve_config(self, scenario_name: str):
        """Return the (possibly file-pinned) connection config."""
        _, original_config = get_scenario_pair(scenario_name)
        if original_config.database == ":memory:":
            return original_config
        from providers.pooling import resolve_database_file, should_keep_database

        # Reuse the file pinned for this scenario within the same provider
        # instance, so multiple models in one test share one database.
        unique_filename = self._scenario_db_files.get(scenario_name)
        if unique_filename is None:
            unique_filename = resolve_database_file(scenario_name)
            self._scenario_db_files[scenario_name] = unique_filename
        from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig

        return SQLiteConnectionConfig(
            database=unique_filename,
            delete_on_close=original_config.delete_on_close
            and not should_keep_database(scenario_name),
            pragmas=original_config.pragmas,
        )
class DDLSyncProvider(_ScenarioFileMixin, IDDLSyncProvider):
    """Sync provider: derive-and-execute for the ddl feature group."""

    def __init__(self):
        _ScenarioFileMixin.__init__(self)
        self._active_backends = []

    def get_test_scenarios(self) -> List[str]:
        return list(get_enabled_scenarios().keys())

    # -- internals ---------------------------------------------------------
    def _setup(self, model: Type[ActiveRecord], scenario_name: str) -> Type[ActiveRecord]:
        backend_class, config = get_scenario_pair(scenario_name)
        config = self._resolve_config(scenario_name)
        model.configure(config, backend_class)
        # Drop leftovers from previous scenarios/files first (the derived
        # CREATE TABLE is not IF NOT EXISTS — isolation is the provider's job).
        self._drop_existing(model)
        expr = model.generate_create_table()
        model.__backend__.execute(*expr.to_sql())
        for ix in expr.indexes:
            index_expr = ix.to_create_index_expression(
                model.__backend__.dialect, expr.table
            )
            model.__backend__.execute(*index_expr.to_sql())
        self._active_backends.append(model.__backend__)
        return model


    def _drop_existing(self, model: Type[ActiveRecord]):
        """Drop the model's table (and thus its indexes) if it exists."""
        from rhosocial.activerecord.backend.expression import (
            DropTableExpression, TableExpression,
        )

        drop = DropTableExpression(
            dialect=model.__backend__.dialect,
            table=TableExpression(model.__backend__.dialect, model.__table_name__),
            if_exists=True,
        )
        try:
            model.__backend__.execute(*drop.to_sql())
        except Exception:
            pass

    # -- sync interface ----------------------------------------------------
    def setup_bare_item_model(self, scenario_name: str) -> Type[ActiveRecord]:
        return self._setup(BareItem, scenario_name)

    def setup_spec_order_model(self, scenario_name: str) -> Type[ActiveRecord]:
        return self._setup(SpecOrder, scenario_name)

    def setup_capability_post_model(self, scenario_name: str) -> Type[ActiveRecord]:
        return self._setup(CapabilityPost, scenario_name)

    def setup_spec_comment_model(self, scenario_name: str) -> Type[ActiveRecord]:
        return self._setup(SpecComment, scenario_name)

    def setup_spec_comment_with_parent_models(self, scenario_name: str):
        """Set up SpecOrder (parent) then SpecComment on the same
        connection so the FK target exists where inserts happen."""
        parent = self._setup(SpecOrder, scenario_name)
        child = self._setup(SpecComment, scenario_name)
        return child, parent

    def cleanup_after_test(self, scenario_name: str):
        import os

        for backend in self._active_backends:
            try:
                backend.disconnect()
            except Exception:
                pass
        self._active_backends.clear()
        db_file = self._scenario_db_files.pop(scenario_name, None)
        if db_file and os.path.exists(db_file):
            try:
                os.remove(db_file)
            except OSError:
                pass


class DDLAsyncProvider(_ScenarioFileMixin, IDDLAsyncProvider):
    """Async provider: derive-and-execute for the ddl feature group."""

    def __init__(self):
        _ScenarioFileMixin.__init__(self)
        self._active_backends = []

    def get_test_scenarios(self) -> List[str]:
        return list(get_enabled_scenarios().keys())

    # -- internals ---------------------------------------------------------
    async def _drop_existing_async(self, model):
        """Async variant: drop the model's table if it exists."""
        from rhosocial.activerecord.backend.expression import (
            DropTableExpression, TableExpression,
        )

        drop = DropTableExpression(
            dialect=model.__backend__.dialect,
            table=TableExpression(model.__backend__.dialect, model.__table_name__),
            if_exists=True,
        )
        try:
            await model.__backend__.execute(*drop.to_sql())
        except Exception:
            pass

    async def _setup(self, model, scenario_name: str):
        from rhosocial.activerecord.backend.impl.sqlite import AsyncSQLiteBackend

        # Async models need the async backend class and an awaited configure.
        _, config = get_scenario_pair(scenario_name)
        config = self._resolve_config(scenario_name)
        await model.configure(config, AsyncSQLiteBackend)
        await self._drop_existing_async(model)
        expr = model.generate_create_table()
        await model.__backend__.execute(*expr.to_sql())
        for ix in expr.indexes:
            index_expr = ix.to_create_index_expression(
                model.__backend__.dialect, expr.table
            )
            await model.__backend__.execute(*index_expr.to_sql())
        self._active_backends.append(model.__backend__)
        return model


    def _drop_existing(self, model: Type[ActiveRecord]):
        """Drop the model's table (and thus its indexes) if it exists."""
        from rhosocial.activerecord.backend.expression import (
            DropTableExpression, TableExpression,
        )

        drop = DropTableExpression(
            dialect=model.__backend__.dialect,
            table=TableExpression(model.__backend__.dialect, model.__table_name__),
            if_exists=True,
        )
        try:
            model.__backend__.execute(*drop.to_sql())
        except Exception:
            pass

    # -- async interface ----------------------------------------------------
    async def setup_bare_item_model(self, scenario_name: str):
        return await self._setup(AsyncBareItem, scenario_name)

    async def setup_spec_order_model(self, scenario_name: str):
        return await self._setup(AsyncSpecOrder, scenario_name)

    async def setup_capability_post_model(self, scenario_name: str):
        return await self._setup(AsyncCapabilityPost, scenario_name)

    async def setup_spec_comment_model(self, scenario_name: str):
        return await self._setup(AsyncSpecComment, scenario_name)

    async def setup_spec_comment_with_parent_models(self, scenario_name: str):
        parent = await self._setup(AsyncSpecOrder, scenario_name)
        child = await self._setup(AsyncSpecComment, scenario_name)
        return child, parent

    async def cleanup_after_test(self, scenario_name: str):
        import os

        for backend in self._active_backends:
            try:
                backend.disconnect()
            except Exception:
                pass
        self._active_backends.clear()
        db_file = self._scenario_db_files.pop(scenario_name, None)
        if db_file and os.path.exists(db_file):
            try:
                os.remove(db_file)
            except OSError:
                pass


def get_scenario_pair(scenario_name: str):
    """Return (backend_class, config) for a scenario name."""
    from .scenarios import get_scenario

    return get_scenario(scenario_name)


def get_scenario_pair(scenario_name: str):
    """Return (backend_class, config) for a scenario name."""
    from .scenarios import get_scenario

    return get_scenario(scenario_name)


