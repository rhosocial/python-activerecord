# src/rhosocial/activerecord/backend/introspection/cache.py
"""The introspection result cache: the only mutable state in this path.

Introspection asks the database for the same metadata over and over -- a
table's columns are wanted by the column list, by the schema diff and by
the migration planner, all within one logical operation. The results are
therefore cached, and the cache is a component with a lifetime of its own
rather than borrowed fields on a mixin.

The contract is :class:`IntrospectionCache`. What ships here is
:class:`InMemoryIntrospectionCache`, which is only a local in-memory
implementation with an expiry -- a backend that wants something else
supplies its own.

Three responsibilities, and nothing else:

* **key policy** -- :meth:`IntrospectionCache.key`. The key *is* the
  correctness contract: two callers asking about the same thing must agree
  on a key, and two callers asking about different things must not
  collide. The method is on the interface so that policy has exactly one
  home; a caller that invented its own string format would be free to
  drift.
* **storage** -- :meth:`set` stores, :meth:`get` returns.
* **invalidation** -- :meth:`invalidate` drops by scope, by scope plus a
  name, or everything. Schema-changing operations invalidate; the cache
  does not know what those operations are.

Thread safety, where an implementation needs it, is the cache's own
problem: the lock is taken and released inside each method, so a caller
never composes it with its own lock.
"""

import threading
import time
from typing import Any, Dict, Optional, Protocol, Tuple, runtime_checkable

from .types import IntrospectionScope


@runtime_checkable
class IntrospectionCache(Protocol):
    """What an introspection manager needs from a result cache.

    An interface, so a backend can put its own implementation behind the
    manager instead of inheriting this package's expiry policy. What a
    cache does about expiry, about sharing, or about reaching beyond this
    process is that implementation's business.

    :meth:`key` is the part that is not optional: it is how two callers
    asking the same question reach the same entry, and how a caller
    asking a different question does not.
    """

    #: Seconds an entry stays fresh. An implementation that never expires
    #: reports 0.
    ttl: int

    def key(
        self,
        scope: IntrospectionScope,
        *args: str,
        schema: Optional[str] = None,
        extra: Optional[str] = None,
    ) -> str:
        """Build the cache key for one introspection result.

        Args:
            scope: What is being asked about. Two scopes never share a key.
            *args: Further discriminators, usually an object name.
            schema: The schema, when the backend has more than one.
            extra: A namespace for results that share a scope but are not
                the same thing. Materialized views share
                ``IntrospectionScope.VIEW`` with ordinary views, so a
                caller asking about them passes an ``extra`` to keep the
                two families from answering each other's questions.

        Returns:
            The key, as a string.
        """
        ...

    def get(self, key: str) -> Optional[Any]:
        """Return the cached value for *key*, or ``None``."""
        ...

    def set(self, key: str, data: Any) -> None:
        """Store *data* under *key*."""
        ...

    def invalidate(
        self,
        scope: Optional[IntrospectionScope] = None,
        name: Optional[str] = None,
    ) -> None:
        """Drop entries, from everything down to one object in one scope.

        Args:
            scope: Scope to invalidate; ``None`` invalidates everything.
            name: Object name within the scope; ``None`` invalidates every
                entry of the scope.
        """
        ...

    def clear(self) -> None:
        """Drop every entry, whatever its scope."""
        ...

    def __len__(self) -> int:
        """How many entries are held. For diagnostics and for tests."""
        ...


class InMemoryIntrospectionCache(IntrospectionCache):
    """Cache results in this process's memory, expiring them after a TTL.

    The default because it is the least surprising: metadata changes
    rarely, an answer beats a round trip, and an answer that has outlived
    its usefulness is dropped the moment somebody looks at it rather than
    by a background sweeper.

    The lock is an ``RLock`` so that a subclass may invalidate from inside
    a :meth:`get` it has overridden without deadlocking itself.
    """

    #: Seconds an entry stays fresh unless the owner says otherwise.
    DEFAULT_TTL: int = 300

    def __init__(self, ttl: int = DEFAULT_TTL) -> None:
        self._entries: Dict[str, Tuple[Any, float]] = {}
        self._lock = threading.RLock()
        self._ttl = ttl

    # ------------------------------------------------------------------ #
    # Key policy
    # ------------------------------------------------------------------ #

    def key(
        self,
        scope: IntrospectionScope,
        *args: str,
        schema: Optional[str] = None,
        extra: Optional[str] = None,
    ) -> str:
        parts = [scope.value]
        if schema:
            parts.append(f"schema:{schema}")
        parts.extend(str(a) for a in args)
        if extra:
            parts.append(extra)
        return ":".join(parts)

    # ------------------------------------------------------------------ #
    # Storage
    # ------------------------------------------------------------------ #

    def get(self, key: str) -> Optional[Any]:
        """Return the cached value for *key*, or ``None``.

        An entry past its TTL is dropped rather than returned: the expiry
        is enforced on read, so nothing needs a background sweeper.
        """
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return None
            data, stored_at = entry
            if time.time() - stored_at > self._ttl:
                del self._entries[key]
                return None
            return data

    def set(self, key: str, data: Any) -> None:
        """Store *data* under *key*, stamped with the current time."""
        with self._lock:
            self._entries[key] = (data, time.time())

    # ------------------------------------------------------------------ #
    # Invalidation
    # ------------------------------------------------------------------ #

    def invalidate(
        self,
        scope: Optional[IntrospectionScope] = None,
        name: Optional[str] = None,
    ) -> None:
        """Drop entries, from everything down to one object in one scope.

        When *name* is given, an entry is dropped if the name appears
        anywhere in its key, which is what makes a table's column list and
        its index list both go when the table is named.
        """
        with self._lock:
            if scope is None:
                self._entries.clear()
                return
            scope_value = scope.value
            prefix = f"{scope_value}:"
            for key in list(self._entries):
                in_scope = key == scope_value or key.startswith(prefix)
                if not in_scope:
                    continue
                if name is None or name in key:
                    del self._entries[key]

    def clear(self) -> None:
        """Drop every entry, whatever its scope."""
        with self._lock:
            self._entries.clear()

    def __len__(self) -> int:
        """How many entries are held. For diagnostics and for tests."""
        with self._lock:
            return len(self._entries)

    # ------------------------------------------------------------------ #
    # TTL
    # ------------------------------------------------------------------ #

    @property
    def ttl(self) -> int:
        """Seconds an entry stays fresh."""
        return self._ttl

    @ttl.setter
    def ttl(self, value: int) -> None:
        self._ttl = value
