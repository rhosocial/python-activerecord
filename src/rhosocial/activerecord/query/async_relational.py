# src/rhosocial/activerecord/query/async_relational.py
"""Async relational query mixin — async I/O execution for eager loading.

ASYNC-ONLY CODE: This file MUST NOT contain synchronous eager loading logic.
Sync/async parity means the two variants are separate and never mixed."""

import logging
from typing import List, Callable

from ..interface import IActiveRecord
from .relational import RelationalQueryMixinBase


class AsyncRelationalQueryMixin(RelationalQueryMixinBase):
    """
    Async query mixin providing eager loading execution for model relationships.

    Inherits non-I/O logic (relation path parsing, validation, config storage)
    from RelationalQueryMixinBase.  Async execution methods await
    AsyncRelationDescriptor.batch_load() for I/O.
    """

    async def _execute_eager_loading_for(
        self,
        records: List[IActiveRecord],
        loader: Callable,
    ) -> None:
        """Async traversal over _eager_loads — awaits *loader*."""
        if not records or not self._eager_loads:
            return

        for path, config in self._eager_loads.items():
            parts = config.name.split('.')
            base_rel_name = parts[0]
            nested = '.'.join(parts[1:]) if len(parts) > 1 else None

            relation = self.model_class.get_relation(base_rel_name)
            if relation is None:
                self._log(logging.WARNING,
                          f"Relation '{base_rel_name}' not found on "
                          f"{self.model_class.__name__}, skipping eager load")
                continue

            base_query = None
            if config.query_modifier is not None:
                related_model = relation.get_related_model(self.model_class)
                if related_model is not None:
                    base_query = config.query_modifier(related_model.query())

            loaded = await loader(relation, records, base_query)

            if nested and loaded:
                all_related = self._collect_unique_records(loaded)
                if all_related:
                    await self._execute_nested_eager_loading_for(
                        all_related, nested, relation, loader,
                    )

    async def _execute_nested_eager_loading_for(
        self,
        related_records: List[IActiveRecord],
        nested_path: str,
        parent_descriptor: object,
        loader: Callable,
    ) -> None:
        """Async recursive traversal for nested relation paths."""
        if not related_records or not nested_path:
            return

        parts = nested_path.split('.')
        base_rel_name = parts[0]
        remaining = '.'.join(parts[1:]) if len(parts) > 1 else None

        related_model = parent_descriptor.get_related_model(type(related_records[0]))
        if related_model is None:
            return

        nested_relation = related_model.get_relation(base_rel_name)
        if nested_relation is None:
            return

        loaded = await loader(nested_relation, related_records, None)

        if remaining and loaded:
            all_related = self._collect_unique_records(loaded)
            if all_related:
                await self._execute_nested_eager_loading_for(
                    all_related, remaining, nested_relation, loader,
                )
