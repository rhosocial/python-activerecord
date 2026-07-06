# src/rhosocial/activerecord/backend/migration/resolver.py
from __future__ import annotations

import importlib

from .core import AsyncNamedMigration, NamedMigration


class NamedMigrationResolver:
    """Resolves a Python FQN string to a ``NamedMigration`` subclass.

    Usage::

        cls = NamedMigrationResolver.resolve("myapp.migrations.v001.CreateUsersTable")
        migration = cls()
    """

    @staticmethod
    def resolve(fqn: str) -> type[NamedMigration]:
        module_path, class_name = fqn.rsplit(".", 1)
        module = importlib.import_module(module_path)
        cls = getattr(module, class_name)
        if not (isinstance(cls, type) and issubclass(cls, NamedMigration)):
            raise TypeError(f"{fqn} is not a NamedMigration subclass")
        return cls


class AsyncNamedMigrationResolver:
    """Resolves a Python FQN string to an ``AsyncNamedMigration`` subclass.

    Async counterpart of :class:`NamedMigrationResolver`. Only accepts
    classes that inherit from :class:`AsyncNamedMigration`; synchronous
    :class:`NamedMigration` subclasses are rejected with a hint to use
    :class:`MigrationRunner` instead.
    """

    @staticmethod
    def resolve(fqn: str) -> type[AsyncNamedMigration]:
        module_path, class_name = fqn.rsplit(".", 1)
        module = importlib.import_module(module_path)
        cls = getattr(module, class_name)
        if not (isinstance(cls, type) and issubclass(cls, AsyncNamedMigration)):
            raise TypeError(
                f"{fqn} is not an AsyncNamedMigration subclass. "
                f"For synchronous NamedMigration use MigrationRunner instead."
            )
        return cls
