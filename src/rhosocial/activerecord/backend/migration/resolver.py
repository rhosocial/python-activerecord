# src/rhosocial/activerecord/backend/migration/resolver.py
from __future__ import annotations

import importlib

from .core import NamedMigration


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
