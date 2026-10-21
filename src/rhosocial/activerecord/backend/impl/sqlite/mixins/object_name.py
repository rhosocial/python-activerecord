# src/rhosocial/activerecord/backend/impl/sqlite/mixins/object_name.py
"""Naming objects SQLite can name, including the ones core namespaces refuse.

:class:`.NamespaceMixin` answers whether a namespace level may appear on a name
by asking the dialect's capability probes. Those probes answer a *DDL* question
-- whether the engine has schemas and catalogues it can create -- and SQLite
answers them ``False`` truthfully and keeps answering that way.

Object *naming* is a different question, and SQLite's answer differs from its
DDL answer: the engine will resolve ``main.sqlite_master`` and
``attached_name.table`` without complaint. So this mixin overrides naming without
touching the probes, and the difference is read off the node's identity:

* a core object carrying ``schema_name`` is refused, unchanged, because SQLite
  has no schema of that kind;
* a :class:`~...expression.table.SQLiteTable` carrying ``schema_name`` renders,
  because it stands for an attached database, which SQLite does have;
* ``catalog_name`` stays refused either way -- SQLite has no level above the
  attached-database name.

This is why the two questions are kept apart rather than answered by one flag.
Answering naming with the DDL flag would make ``main.sqlite_master``
inexpressible; answering DDL with a naming flag would make SQLite look as though
it had schemas it could create.
"""

from typing import Tuple

from rhosocial.activerecord.backend.dialect.mixins.schema_namespace import (
    NamespaceMixin,
)
from rhosocial.activerecord.backend.expression.objects import RelationObject
from rhosocial.activerecord.backend.impl.sqlite.expression.table import SQLiteTable

__all__ = ["SQLiteObjectNameMixin"]


class SQLiteObjectNameMixin(NamespaceMixin):
    """Renders a table name, accepting SQLite's own schema level."""

    def format_table_object(self, expr: "RelationObject") -> Tuple[str, tuple]:
        """Render *expr* as a table name.

        Args:
            expr: The table being named.

        Returns:
            A ``(sql, params)`` tuple; ``params`` is empty, because an
            identifier is never a bind parameter.

        Raises:
            UnsupportedFeatureError: A namespace level the dialect cannot
                express -- for a core object, exactly as before; for a
                ``SQLiteTable``, the catalogue level, which SQLite still lacks.
        """
        if type(expr) is SQLiteTable and expr.schema_name and not expr.catalog_name:
            parts = [
                self.format_identifier(expr.schema_name, expr.schema_need_quote),
                self.format_identifier(expr.name, expr.name_need_quote),
            ]
            return self.separator.join(parts), ()

        if type(expr) is SQLiteTable and expr.catalog_name:
            from rhosocial.activerecord.backend.dialect.exceptions import (
                UnsupportedFeatureError,
            )

            raise UnsupportedFeatureError(
                self.name,
                "catalog-qualified names",
                suggestion=(
                    f"SQLiteTable carries catalog_name={expr.catalog_name!r}, and "
                    f"SQLite has no level above the attached-database name; the "
                    f"database belongs in schema_name"
                ),
            )

        return super().format_table_object(expr)
