# src/rhosocial/activerecord/backend/impl/sqlite/introspection/pragma_introspector.py
"""
SQLite PRAGMA sub-introspectors.

Provides direct access to SQLite's PRAGMA interface. These classes do not
inherit from AbstractIntrospector — they are purpose-built "sub-introspectors"
exposed as the `.pragma` property on SyncSQLiteIntrospector and
AsyncSQLiteIntrospector.

Design principle: Sync and Async are separate and cannot coexist.
- SyncPragmaIntrospector: for synchronous backends (method names without _async suffix)
- AsyncPragmaIntrospector: for asynchronous backends (method names without _async suffix)

Usage::

    # Synchronous
    mode = backend.introspector.pragma.get("journal_mode")
    backend.introspector.pragma.set("journal_mode", "WAL")
    cols = backend.introspector.pragma.table_info("users")
    errors = backend.introspector.pragma.integrity_check()

    # Asynchronous
    mode = await backend.introspector.pragma.get("journal_mode")
    backend.introspector.pragma.set("journal_mode", "WAL")
    cols = await backend.introspector.pragma.table_info("users")
"""

from typing import Any, Dict, List, Optional, Tuple

from rhosocial.activerecord.backend.introspection.executor import (
    SyncIntrospectorExecutor,
    AsyncIntrospectorExecutor,
)


class PragmaMixin:
    """Mixin providing shared PRAGMA SQL generation helpers.

    Both SyncPragmaIntrospector and AsyncPragmaIntrospector inherit
    from this mixin to share SQL generation logic.
    """

    @staticmethod
    def _pragma_sql(
        name: str,
        argument: Optional[Any] = None,
        schema: Optional[str] = None,
    ) -> Tuple[str, tuple]:
        """Build a PRAGMA statement.

        Args:
            name:     PRAGMA name (e.g. ``"journal_mode"``).
            argument: Optional argument (e.g. a table name or a new value
                      for a read/write PRAGMA).  Passed as a literal, not
                      as a bound parameter, because SQLite does not support
                      parameterised PRAGMA values.
            schema:   Optional attached-database name (e.g. ``"temp"``).

        Returns:
            ``(sql, params)`` tuple compatible with executor.execute().
        """
        prefix = f"{schema}." if schema else ""
        if argument is not None:
            return (f"PRAGMA {prefix}{name}({argument})", ())
        return (f"PRAGMA {prefix}{name}", ())

    @staticmethod
    def _set_pragma_sql(
        name: str, value: Any, schema: Optional[str] = None
    ) -> Tuple[str, tuple]:
        """Build a ``PRAGMA name = value`` assignment statement."""
        prefix = f"{schema}." if schema else ""
        return (f"PRAGMA {prefix}{name} = {value}", ())


class SyncPragmaIntrospector(PragmaMixin):
    """Synchronous PRAGMA introspector for SQLite backends.

    All methods are synchronous. Method names do NOT have an _async suffix.
    """

    def __init__(self, backend: Any, executor: SyncIntrospectorExecutor) -> None:
        self._backend = backend
        self._executor = executor

    # ------------------------------------------------------------------ #
    # Core PRAGMA operations
    # ------------------------------------------------------------------ #

    def get(
        self,
        name: str,
        argument: Optional[Any] = None,
        schema: Optional[str] = None,
    ) -> Optional[Any]:
        """Read a PRAGMA value.

        Returns the first row returned by the PRAGMA, or ``None`` if the
        result is empty (e.g. write-only or action PRAGMAs).
        """
        sql, params = self._pragma_sql(name, argument, schema)
        rows = self._executor.execute(sql, params)
        return rows[0] if rows else None

    def set(
        self,
        name: str,
        value: Any,
        schema: Optional[str] = None,
    ) -> None:
        """Write a PRAGMA value (for read/write PRAGMAs)."""
        sql, params = self._set_pragma_sql(name, value, schema)
        self._executor.execute(sql, params)

    def execute(
        self,
        name: str,
        argument: Optional[Any] = None,
        schema: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Execute any PRAGMA and return all result rows as dicts.

        Use this for PRAGMAs that return multiple rows (e.g.
        ``table_info``, ``index_list``, ``foreign_key_list``).
        """
        sql, params = self._pragma_sql(name, argument, schema)
        return self._executor.execute(sql, params)

    # ------------------------------------------------------------------ #
    # Commonly used structural PRAGMAs
    # ------------------------------------------------------------------ #

    def table_info(
        self, table_name: str, schema: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Return raw ``PRAGMA table_info(table_name)`` rows."""
        return self.execute("table_info", f"'{table_name}'", schema)

    def table_xinfo(
        self, table_name: str, schema: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Return raw ``PRAGMA table_xinfo(table_name)`` rows (SQLite 3.26+).

        Includes hidden columns generated by virtual tables.
        """
        return self.execute("table_xinfo", f"'{table_name}'", schema)

    def index_list(
        self, table_name: str, schema: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Return raw ``PRAGMA index_list(table_name)`` rows."""
        return self.execute("index_list", f"'{table_name}'", schema)

    def index_info(
        self, index_name: str, schema: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Return raw ``PRAGMA index_info(index_name)`` rows."""
        return self.execute("index_info", f"'{index_name}'", schema)

    def index_xinfo(
        self, index_name: str, schema: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Return raw ``PRAGMA index_xinfo(index_name)`` rows (SQLite 3.9+)."""
        return self.execute("index_xinfo", f"'{index_name}'", schema)

    def foreign_key_list(
        self, table_name: str, schema: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Return raw ``PRAGMA foreign_key_list(table_name)`` rows."""
        return self.execute("foreign_key_list", f"'{table_name}'", schema)

    def table_list(self, schema: Optional[str] = None) -> List[Dict[str, Any]]:
        """Return raw ``PRAGMA table_list`` rows (SQLite 3.37+)."""
        return self.execute("table_list", schema=schema)

    # ------------------------------------------------------------------ #
    # Configuration / maintenance PRAGMAs
    # ------------------------------------------------------------------ #

    def integrity_check(
        self, schema: Optional[str] = None
    ) -> List[str]:
        """Run ``PRAGMA integrity_check`` and return error message strings.

        Returns ``["ok"]`` if the database is intact.
        """
        rows = self.execute("integrity_check", schema=schema)
        return [list(row.values())[0] for row in rows if row]

    def foreign_key_check(
        self,
        table_name: Optional[str] = None,
        schema: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Run ``PRAGMA foreign_key_check`` (optionally for a single table).

        Returns rows describing foreign-key constraint violations.
        """
        arg = f"'{table_name}'" if table_name else None
        return self.execute("foreign_key_check", arg, schema)

    def journal_mode(
        self, schema: Optional[str] = None
    ) -> Optional[str]:
        """Return the current journal mode."""
        row = self.get("journal_mode", schema=schema)
        if row is None:
            return None
        return list(row.values())[0] if row else None

    def wal_checkpoint(
        self,
        mode: str = "PASSIVE",
        schema: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Run a WAL checkpoint.

        Args:
            mode:   One of ``PASSIVE``, ``FULL``, ``RESTART``, ``TRUNCATE``.
            schema: Attached-database name, or ``None`` for the main DB.
        """
        return self.get("wal_checkpoint", mode, schema)


class AsyncPragmaIntrospector(PragmaMixin):
    """Asynchronous PRAGMA introspector for SQLite backends.

    All methods are async. Method names do NOT have an _async suffix,
    matching the pattern of AsyncAbstractIntrospector.
    """

    def __init__(self, backend: Any, executor: AsyncIntrospectorExecutor) -> None:
        self._backend = backend
        self._executor = executor

    # ------------------------------------------------------------------ #
    # Core PRAGMA operations
    # ------------------------------------------------------------------ #

    async def get(
        self,
        name: str,
        argument: Optional[Any] = None,
        schema: Optional[str] = None,
    ) -> Optional[Any]:
        """Read a PRAGMA value.

        Returns the first row returned by the PRAGMA, or ``None`` if the
        result is empty (e.g. write-only or action PRAGMAs).
        """
        sql, params = self._pragma_sql(name, argument, schema)
        rows = await self._executor.execute(sql, params)
        return rows[0] if rows else None

    async def set(
        self,
        name: str,
        value: Any,
        schema: Optional[str] = None,
    ) -> None:
        """Write a PRAGMA value (for read/write PRAGMAs)."""
        sql, params = self._set_pragma_sql(name, value, schema)
        await self._executor.execute(sql, params)

    async def execute(
        self,
        name: str,
        argument: Optional[Any] = None,
        schema: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Execute any PRAGMA and return all result rows as dicts.

        Use this for PRAGMAs that return multiple rows (e.g.
        ``table_info``, ``index_list``, ``foreign_key_list``).
        """
        sql, params = self._pragma_sql(name, argument, schema)
        return await self._executor.execute(sql, params)

    # ------------------------------------------------------------------ #
    # Commonly used structural PRAGMAs
    # ------------------------------------------------------------------ #

    async def table_info(
        self, table_name: str, schema: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Return raw ``PRAGMA table_info(table_name)`` rows."""
        return await self.execute("table_info", f"'{table_name}'", schema)

    async def table_xinfo(
        self, table_name: str, schema: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Return raw ``PRAGMA table_xinfo(table_name)`` rows (SQLite 3.26+).

        Includes hidden columns generated by virtual tables.
        """
        return await self.execute("table_xinfo", f"'{table_name}'", schema)

    async def index_list(
        self, table_name: str, schema: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Return raw ``PRAGMA index_list(table_name)`` rows."""
        return await self.execute("index_list", f"'{table_name}'", schema)

    async def index_info(
        self, index_name: str, schema: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Return raw ``PRAGMA index_info(index_name)`` rows."""
        return await self.execute("index_info", f"'{index_name}'", schema)

    async def index_xinfo(
        self, index_name: str, schema: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Return raw ``PRAGMA index_xinfo(index_name)`` rows (SQLite 3.9+)."""
        return await self.execute("index_xinfo", f"'{index_name}'", schema)

    async def foreign_key_list(
        self, table_name: str, schema: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Return raw ``PRAGMA foreign_key_list(table_name)`` rows."""
        return await self.execute("foreign_key_list", f"'{table_name}'", schema)

    async def table_list(self, schema: Optional[str] = None) -> List[Dict[str, Any]]:
        """Return raw ``PRAGMA table_list`` rows (SQLite 3.37+)."""
        return await self.execute("table_list", schema=schema)

    # ------------------------------------------------------------------ #
    # Configuration / maintenance PRAGMAs
    # ------------------------------------------------------------------ #

    async def integrity_check(
        self, schema: Optional[str] = None
    ) -> List[str]:
        """Run ``PRAGMA integrity_check`` and return error message strings.

        Returns ``["ok"]`` if the database is intact.
        """
        rows = await self.execute("integrity_check", schema=schema)
        return [list(row.values())[0] for row in rows if row]

    async def foreign_key_check(
        self,
        table_name: Optional[str] = None,
        schema: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """Run ``PRAGMA foreign_key_check`` (optionally for a single table).

        Returns rows describing foreign-key constraint violations.
        """
        arg = f"'{table_name}'" if table_name else None
        return await self.execute("foreign_key_check", arg, schema)

    async def journal_mode(
        self, schema: Optional[str] = None
    ) -> Optional[str]:
        """Return the current journal mode."""
        row = await self.get("journal_mode", schema=schema)
        if row is None:
            return None
        return list(row.values())[0] if row else None

    async def wal_checkpoint(
        self,
        mode: str = "PASSIVE",
        schema: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Run a WAL checkpoint.

        Args:
            mode:   One of ``PASSIVE``, ``FULL``, ``RESTART``, ``TRUNCATE``.
            schema: Attached-database name, or ``None`` for the main DB.
        """
        return await self.get("wal_checkpoint", mode, schema)
