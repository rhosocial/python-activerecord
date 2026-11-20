# src/rhosocial/activerecord/base/migration_mixin.py
"""Opt-in DDL actions on a model.

The mixin exposes mechanism only: build a statement or execute one DDL
action against the model's configured backend.  It does not order actions,
decide inline-vs-separate policy, or manage transactions; callers compose
those themselves.
"""

from __future__ import annotations

from typing import Any, Optional, Sequence

__all__ = ["MigrationMixin", "AsyncMigrationMixin"]


class _MigrationStatementsMixin:
    """Statement builders shared by sync and async models."""

    @classmethod
    def _ddl_backend(cls, backend: Any = None) -> Any:
        selected = backend if backend is not None else cls.backend()
        if selected is None:
            raise RuntimeError(
                f"{cls.__name__} has no backend configured; call "
                f"{cls.__name__}.configure(...) first or pass backend=..."
            )
        return selected

    @classmethod
    def create_table_statement(
        cls,
        *,
        column_order: Optional[Sequence[str]] = None,
        include_indexes: bool = False,
        include_comments: bool = False,
        backend: Any = None,
    ) -> Any:
        from .derivation import build_create_table_statement

        return build_create_table_statement(
            cls,
            cls._ddl_backend(backend).dialect,
            column_order=column_order,
            include_indexes=include_indexes,
            include_comments=include_comments,
        )

    @classmethod
    def drop_table_statement(
        cls,
        *,
        if_exists: bool = False,
        backend: Any = None,
    ) -> Any:
        from .derivation import build_drop_table_statement

        return build_drop_table_statement(
            cls,
            cls._ddl_backend(backend).dialect,
            if_exists=if_exists,
        )

    @classmethod
    def create_index_statements(
        cls,
        *,
        backend: Any = None,
    ) -> tuple:
        from .derivation import build_create_index_statements

        return build_create_index_statements(
            cls, cls._ddl_backend(backend).dialect
        )

    @classmethod
    def drop_index_statements(
        cls,
        *,
        if_exists: bool = False,
        backend: Any = None,
    ) -> tuple:
        from .derivation import build_drop_index_statements

        return build_drop_index_statements(
            cls,
            cls._ddl_backend(backend).dialect,
            if_exists=if_exists,
        )

    @classmethod
    def comment_statements(
        cls,
        *,
        backend: Any = None,
    ) -> tuple:
        from .derivation import build_comment_statements

        return build_comment_statements(
            cls, cls._ddl_backend(backend).dialect
        )


class MigrationMixin(_MigrationStatementsMixin):
    """Synchronous DDL actions for a model."""

    @classmethod
    def _execute(cls, backend: Any, expressions: Sequence[Any]) -> None:
        from ..backend.options import ExecutionOptions
        from ..backend.schema import StatementType

        options = ExecutionOptions(stmt_type=StatementType.DDL)
        for expression in expressions:
            sql, params = expression.to_sql()
            backend.execute(sql, params, options=options)

    @classmethod
    def create_table(
        cls,
        *,
        column_order: Optional[Sequence[str]] = None,
        include_indexes: bool = False,
        include_comments: bool = False,
        backend: Any = None,
    ) -> None:
        cls._execute(
            cls._ddl_backend(backend),
            (
                cls.create_table_statement(
                    column_order=column_order,
                    include_indexes=include_indexes,
                    include_comments=include_comments,
                    backend=backend,
                ),
            ),
        )

    @classmethod
    def drop_table(cls, *, if_exists: bool = False, backend: Any = None) -> None:
        cls._execute(
            cls._ddl_backend(backend),
            (cls.drop_table_statement(if_exists=if_exists, backend=backend),),
        )

    @classmethod
    def create_indexes(cls, *, backend: Any = None) -> None:
        cls._execute(
            cls._ddl_backend(backend),
            cls.create_index_statements(backend=backend),
        )

    @classmethod
    def drop_indexes(cls, *, if_exists: bool = False, backend: Any = None) -> None:
        cls._execute(
            cls._ddl_backend(backend),
            cls.drop_index_statements(if_exists=if_exists, backend=backend),
        )

    @classmethod
    def add_comments(cls, *, backend: Any = None) -> None:
        cls._execute(
            cls._ddl_backend(backend),
            cls.comment_statements(backend=backend),
        )


class AsyncMigrationMixin(_MigrationStatementsMixin):
    """Asynchronous DDL actions for a model."""

    @classmethod
    async def _execute(cls, backend: Any, expressions: Sequence[Any]) -> None:
        from ..backend.options import ExecutionOptions
        from ..backend.schema import StatementType

        options = ExecutionOptions(stmt_type=StatementType.DDL)
        for expression in expressions:
            sql, params = expression.to_sql()
            await backend.execute(sql, params, options=options)

    @classmethod
    async def create_table(
        cls,
        *,
        column_order: Optional[Sequence[str]] = None,
        include_indexes: bool = False,
        include_comments: bool = False,
        backend: Any = None,
    ) -> None:
        await cls._execute(
            cls._ddl_backend(backend),
            (
                cls.create_table_statement(
                    column_order=column_order,
                    include_indexes=include_indexes,
                    include_comments=include_comments,
                    backend=backend,
                ),
            ),
        )

    @classmethod
    async def drop_table(
        cls, *, if_exists: bool = False, backend: Any = None
    ) -> None:
        await cls._execute(
            cls._ddl_backend(backend),
            (cls.drop_table_statement(if_exists=if_exists, backend=backend),),
        )

    @classmethod
    async def create_indexes(cls, *, backend: Any = None) -> None:
        await cls._execute(
            cls._ddl_backend(backend),
            cls.create_index_statements(backend=backend),
        )

    @classmethod
    async def drop_indexes(
        cls, *, if_exists: bool = False, backend: Any = None
    ) -> None:
        await cls._execute(
            cls._ddl_backend(backend),
            cls.drop_index_statements(if_exists=if_exists, backend=backend),
        )

    @classmethod
    async def add_comments(cls, *, backend: Any = None) -> None:
        await cls._execute(
            cls._ddl_backend(backend),
            cls.comment_statements(backend=backend),
        )
