# src/rhosocial/activerecord/backend/migration/functions.py
"""Function-based migrations and their resolver.

A migration is a function carrying :func:`migration` metadata, not a class.
The metadata names the version and the prerequisite versions; the function
itself receives one :class:`MigrationContext` argument and decides what to do
for ``ctx.direction``.  Functions may be:

* a ``classmethod`` or ``staticmethod`` on an ActiveRecord model, in which
case the model supplies the connection and the statement builders;
* a module-level function decorated with :func:`migration`, in which case the
caller supplies the connection explicitly.

The CLI resolves only function FQNs.  ``NamedMigration`` classes keep their
existing meaning and are still run by the backend ``named-migration`` command;
the two entry points never substitute for one another.
"""

from __future__ import annotations

import importlib
import inspect
from dataclasses import dataclass
from typing import Any, Callable, Optional, Sequence, Tuple

from rhosocial.activerecord.interface import IActiveRecord, IAsyncActiveRecord

__all__ = [
    "MigrationInfo",
    "MigrationFunctionRef",
    "MigrationFunctionError",
    "migration",
    "resolve_migration_function",
]


class MigrationFunctionError(Exception):
    """Raised when a function FQN is not a usable migration function."""


@dataclass(frozen=True)
class MigrationInfo:
    """Metadata attached to a migration function."""

    version: str
    dependencies: Tuple[str, ...] = ()
    description: str = ""
    async_variant: str = ""


@dataclass(frozen=True)
class MigrationFunctionRef:
    """A resolved migration function and its declaration context."""

    fqn: str
    function: Callable[..., Any]
    info: MigrationInfo
    owner: Optional[type] = None
    is_async: bool = False


def migration(
    version: str = "",
    *,
    dependencies: Sequence[str] = (),
    description: str = "",
    async_variant: str = "",
):
    """Mark a function as a migration.

    Usage::

        class User(ActiveRecord):
            @classmethod
            @migration("v001_create_user_table")
            def create_user_table(cls, ctx):
                if ctx.direction is MigrationDirection.UP:
                    ctx.apply(cls.create_table_statement(backend=ctx.backend))
                else:
                    ctx.apply(cls.drop_table_statement(backend=ctx.backend))

    ``@migration`` without a version falls back to the function name, which is
    allowed but rarely unique enough to record reliably; pass a version.

    The decorator only attaches metadata.  Signature, ownership, and duplicate
    version checks happen when the CLI resolves the FQN, so the same function
    may be imported without an available backend.
    """

    def decorate(target: Any) -> Any:
        function = target.__func__ if isinstance(target, (classmethod, staticmethod)) else target
        if not inspect.isfunction(function):
            raise TypeError("@migration must decorate a function; " f"got {type(target).__name__}")
        resolved_version = version or function.__name__
        if not isinstance(resolved_version, str) or not resolved_version.strip():
            raise ValueError("@migration requires a non-empty version")
        if isinstance(dependencies, str) or not all(
            isinstance(item, str) and item.strip() for item in dependencies
        ):
            raise ValueError("@migration dependencies must be a sequence of non-empty strings")
        if not isinstance(async_variant, str):
            raise ValueError("@migration async_variant must be a function FQN string")
        if async_variant and not async_variant.strip():
            raise ValueError("@migration async_variant cannot be blank")
        info = MigrationInfo(
            version=resolved_version,
            dependencies=tuple(dependencies),
            description=description,
            async_variant=async_variant,
        )
        function.__migration__ = info
        return target

    return decorate


def _split_reference(reference: str) -> Tuple[str, str]:
    """Split ``module:attr`` or ``module.attr`` into module and attribute."""
    if ":" in reference:
        module_path, attribute = reference.rsplit(":", 1)
        if not module_path or not attribute:
            raise MigrationFunctionError(
                f'Invalid migration function reference "{reference}": '
                "expected the form module:function or module.Class.method"
            )
        return module_path, attribute

    parts = reference.split(".")
    if len(parts) < 2:
        raise MigrationFunctionError(
            f'Invalid migration function reference "{reference}": '
            "expected the form module:function or module.Class.method"
        )
    for index in range(len(parts) - 1, 0, -1):
        module_path = ".".join(parts[:index])
        attribute = ".".join(parts[index:])
        try:
            importlib.import_module(module_path)
        except ImportError:
            continue
        return module_path, attribute
    raise MigrationFunctionError(
        f'Cannot import a module from migration function reference "{reference}"'
    )


def _is_model_class(candidate: Any) -> bool:
    if not isinstance(candidate, type):
        return False
    try:
        return issubclass(candidate, (IActiveRecord, IAsyncActiveRecord))
    except TypeError:  # pragma: no cover - defensive
        return False


def _function_from_attribute(
    parent: Any, attribute: str, reference: str
) -> Tuple[Callable[..., Any], Optional[type], Callable[..., Any]]:
    """Walk one attribute; return the callable, owner, and metadata holder."""
    try:
        descriptor = inspect.getattr_static(parent, attribute)
    except AttributeError:
        raise MigrationFunctionError(
            f'Cannot resolve migration function "{reference}": ' f"no attribute {attribute!r}"
        ) from None

    if isinstance(descriptor, classmethod):
        owner = parent
        holder = descriptor.__func__
        function = getattr(parent, attribute)
    elif isinstance(descriptor, staticmethod):
        owner = parent
        holder = descriptor.__func__
        function = descriptor.__func__
    elif inspect.isfunction(descriptor):
        if _is_model_class(parent):
            raise MigrationFunctionError(
                f'Migration function "{reference}" is a plain method on '
                f"{parent.__name__}; declare it as @classmethod or @staticmethod"
            )
        owner = None
        holder = descriptor
        function = descriptor
    elif inspect.isclass(descriptor):
        raise MigrationFunctionError(
            f'"{reference}" is a class, not a migration function. '
            "NamedMigration classes are run by the backend named-migration "
            "command, not by activerecord-cli migrate"
        )
    else:
        # ``getattr`` resolves other descriptors (properties, instances) in a
        # way that can have side effects; only plain functions are accepted.
        raise MigrationFunctionError(
            f'Cannot resolve migration function "{reference}": '
            f"{attribute!r} is {type(descriptor).__name__}, not a function"
        )
    return function, owner, holder


def _check_signature(function: Callable[..., Any], reference: str) -> None:
    try:
        parameters = list(inspect.signature(function).parameters.values())
    except (TypeError, ValueError):
        raise MigrationFunctionError(
            f'Migration function "{reference}" has no inspectable signature'
        ) from None
    positional = [
        parameter
        for parameter in parameters
        if parameter.kind
        in (
            inspect.Parameter.POSITIONAL_ONLY,
            inspect.Parameter.POSITIONAL_OR_KEYWORD,
        )
    ]
    required_keyword_only = [
        parameter
        for parameter in parameters
        if parameter.kind == inspect.Parameter.KEYWORD_ONLY
        and parameter.default is inspect.Parameter.empty
    ]
    varargs = [
        parameter
        for parameter in parameters
        if parameter.kind
        in (
            inspect.Parameter.VAR_POSITIONAL,
            inspect.Parameter.VAR_KEYWORD,
        )
    ]
    if len(positional) != 1 or required_keyword_only or varargs:
        raise MigrationFunctionError(
            f'Migration function "{reference}" must accept exactly one '
            "positional argument (ctx); all other arguments need defaults"
        )


def resolve_migration_function(
    reference: str,
    *,
    allowed_modules: Optional[Sequence[str]] = None,
) -> MigrationFunctionRef:
    """Resolve an FQN to a migration-decorated function.

    Only functions are accepted.  A class FQN (including ``NamedMigration``)
    is rejected; those are run by the backend ``named-migration`` command.
    """
    module_path, attribute = _split_reference(reference)

    if allowed_modules:
        allowed = tuple(allowed_modules)
        if not any(module_path == item or module_path.startswith(item + ".") for item in allowed):
            raise MigrationFunctionError(
                f'Migration function module "{module_path}" is not in the allowed '
                f"modules ({', '.join(allowed)})"
            )

    module = importlib.import_module(module_path)

    parent: Any = module
    function: Any = None
    holder: Any = None
    owner: Optional[type] = None
    pieces = attribute.split(".")
    for index, part in enumerate(pieces):
        if isinstance(getattr(parent, part, None), type) and index < len(pieces) - 1:
            parent = getattr(parent, part)
            continue
        function, owner, holder = _function_from_attribute(parent, part, reference)
        if index < len(pieces) - 1:
            raise MigrationFunctionError(
                f'Cannot resolve migration function "{reference}": '
                f"{part!r} is a function, not a container"
            )

    if function is None or holder is None:
        raise MigrationFunctionError(f'Cannot resolve migration function "{reference}"')

    info = getattr(holder, "__migration__", None)
    if not isinstance(info, MigrationInfo):
        if isinstance(getattr(parent, pieces[-1], None), type):
            raise MigrationFunctionError(
                f'"{reference}" is a class, not a migration function. '
                "NamedMigration classes are run by the backend named-migration "
                "command, not by activerecord-cli migrate"
            )
        raise MigrationFunctionError(f'"{reference}" is not decorated with @migration')

    _check_signature(function, reference)

    if owner is not None and not _is_model_class(owner):
        raise MigrationFunctionError(
            f'Migration function "{reference}" is bound to {owner.__name__}, '
            "which is not an ActiveRecord model class"
        )

    return MigrationFunctionRef(
        fqn=reference,
        function=function,
        info=info,
        owner=owner,
        is_async=inspect.iscoroutinefunction(function),
    )
