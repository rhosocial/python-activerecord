# src/rhosocial/activerecord/backend/migration/resolver.py
from __future__ import annotations

import importlib
from typing import List, Optional

from .core import AsyncNamedMigration, NamedMigration
from ..named_expression.exceptions import NamedExpressionModuleNotAllowedError
from ..named_expression.resolver import _module_allowed


class NamedMigrationResolver:
    """Resolves a Python FQN string to a ``NamedMigration`` subclass.

    Usage::

        cls = NamedMigrationResolver.resolve("myapp.migrations.v001.CreateUsersTable")
        migration = cls()
    """

    @staticmethod
    def resolve(fqn: str, *, allowed_modules: Optional[List[str]] = None) -> type[NamedMigration]:
        """Resolve the FQN.

        Args:
            fqn: Fully qualified name of the migration class.
            allowed_modules: Optional allowlist of module prefixes. When provided,
                only migrations whose module matches the allowlist are imported.
                ``None`` (default) preserves legacy unrestricted behavior.
        """
        module_path, class_name = fqn.rsplit(".", 1)
        if not _module_allowed(module_path, allowed_modules):
            raise NamedExpressionModuleNotAllowedError(module_path, allowed_modules or [])
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
    def resolve(fqn: str, *, allowed_modules: Optional[List[str]] = None) -> type[AsyncNamedMigration]:
        """Resolve the FQN.

        Args:
            fqn: Fully qualified name of the migration class.
            allowed_modules: Optional allowlist of module prefixes.
        """
        module_path, class_name = fqn.rsplit(".", 1)
        if not _module_allowed(module_path, allowed_modules):
            raise NamedExpressionModuleNotAllowedError(module_path, allowed_modules or [])
        module = importlib.import_module(module_path)
        cls = getattr(module, class_name)
        if not (isinstance(cls, type) and issubclass(cls, AsyncNamedMigration)):
            raise TypeError(
                f"{fqn} is not an AsyncNamedMigration subclass. "
                f"For synchronous NamedMigration use MigrationRunner instead."
            )
        return cls
