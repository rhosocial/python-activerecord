# src/rhosocial/activerecord/base/ddl_mixin.py
"""Model mixins for creating source-bound DDL expression factories."""

from __future__ import annotations

from typing import Any, ClassVar, Optional, Type, cast

from rhosocial.activerecord.interface import IActiveRecord, IAsyncActiveRecord


class DDLMethodMixin(IActiveRecord):
    """Provide the synchronous ``ddl()`` model entry point."""

    __ddl_class__: ClassVar[Optional[Type[Any]]] = None

    @classmethod
    def ddl(cls) -> Any:
        from rhosocial.activerecord.ddl import ActiveDDL

        ddl_class = cls.__ddl_class__ or ActiveDDL
        return ddl_class(source=cast(Any, cls), backend=cls.backend())


class AsyncDDLMethodMixin(IAsyncActiveRecord):
    """Provide the asynchronous ``ddl()`` model entry point."""

    __ddl_class__: ClassVar[Optional[Type[Any]]] = None

    @classmethod
    def ddl(cls) -> Any:
        from rhosocial.activerecord.ddl import AsyncActiveDDL

        ddl_class = cls.__ddl_class__ or AsyncActiveDDL
        return ddl_class(source=cast(Any, cls), backend=cls.backend())


__all__ = ["AsyncDDLMethodMixin", "DDLMethodMixin"]
