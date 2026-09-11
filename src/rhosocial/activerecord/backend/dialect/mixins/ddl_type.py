# src/rhosocial/activerecord/backend/dialect/mixins/ddl_type.py
"""``DDLTypeMixin`` — naming-convention type formatting dispatch.

The data-type protocol has exactly four members, implemented by each
backend dialect according to its real capabilities:

- ``supports_data_types()`` — mapping ``{<name>: concrete type class}``
  of every type this dialect supports (the FQN of each class is
  self-describing);
- ``supports_data_type_<name>()`` — whether the type ``<name>`` is
  supported (truthful);
- ``format_data_type(data_type)`` — the single entry point: validates the
  instance and dispatches by the instance's ``name`` to
  ``format_data_type_<name>``;
- ``format_data_type_<name>(data_type)`` — renders the type; raises on
  malformed expression parameters (e.g. non-positive ``DECIMAL`` m/n) or
  unsupported usage.

There is no registry: the methods a dialect defines **are** the set of
types it supports. The base mixin here provides only the dispatch of
``format_data_type`` by the instance's ``name``.
"""

from __future__ import annotations

import re
from typing import Dict, Tuple, TYPE_CHECKING

if TYPE_CHECKING:
    from ...expression.types._base import DataType


SQLQueryAndParams = Tuple[str, tuple]

# A <name> must be a valid identifier suffix (lowercase letters/digits).
_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")


class DDLTypeMixin:
    """Mixin providing naming-convention ``format_data_type()`` dispatch.

    A backend declares per-type formatters as methods named
    ``format_data_type_<name>`` (the suffix is the type's generic name,
    e.g. ``format_data_type_uuid``).  Together with
    ``supports_data_type_<name>()`` / ``supports_data_types()`` these
    methods **are** the dialect's supported-type surface — no registry.

    The base mixin provides only the dispatch of ``format_data_type`` by
    the instance's ``name``; it registers no types itself.
    """

    def format_data_type(self, data_type: DataType) -> SQLQueryAndParams:
        # ① entry validation: a DataType instance is required
        from ...expression.types._base import DataType

        if not isinstance(data_type, DataType):
            raise TypeError(
                f"{type(self).__name__}.format_data_type() expects a "
                f"DataType instance, got {type(data_type).__name__}."
            )
        name = getattr(data_type, "name", None)
        if not name or not _NAME_RE.match(name):
            raise TypeError(
                f"{type(data_type).__name__} does not declare a valid "
                f"generic type name (name={name!r}); cannot dispatch."
            )
        # ② dispatch by <name>
        formatter = getattr(self, f"format_data_type_{name}", None)
        if formatter is None:
            raise TypeError(
                f"{type(self).__name__} does not support the generic type "
                f"{name!r} (no format_data_type_{name}). Use a type this "
                f"backend supports."
            )
        # ③ the per-type formatter validates its own parameters
        return formatter(data_type)

    def supports_data_types(self) -> Dict[str, type]:
        """Mapping ``{<name>: concrete type class}`` of every generic type
        this dialect supports — discovered from the dialect's own
        ``format_data_type_<name>`` / ``supports_data_type_<name>`` methods.
        """
        from ...expression.types._base import DataType

        result = {}
        for member_name in dir(type(self)):
            match = re.match(r"^format_data_type_([a-z][a-z0-9_]*)$", member_name)
            if not match:
                continue
            name = match.group(1)
            supports = getattr(self, f"supports_data_type_{name}", None)
            if supports is not None and supports():
                # Locate the concrete class for this generic name.
                result[name] = self._type_class_for(name)
        return result

    def _type_class_for(self, name: str):
        """Resolve the concrete ``DataType`` class for a generic type name.

        Scans the ``DataType`` subclass hierarchy for a class whose
        :attr:`name` matches.
        """
        from ...expression.types._base import DataType

        seen = set()
        stack = [DataType]
        while stack:
            klass = stack.pop()
            if klass in seen:
                continue
            seen.add(klass)
            stack.extend(klass.__subclasses__())
            if getattr(klass, "name", None) == name:
                return klass
        return None

    def suggested_data_types(self) -> Dict[str, type]:
        """Cross-backend type-consistency suggestion map (empty by default).

        Backends override this to suggest, for generic types they do not
        natively support, a replacement ``DataType`` **class** (same value
        type as :meth:`supports_data_types`). Honesty principle: return an
        empty
        dict when there is nothing to suggest — never fake a suggestion.
        """
        return {}
