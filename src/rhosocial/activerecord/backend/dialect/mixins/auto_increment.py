# src/rhosocial/activerecord/backend/dialect/mixins/auto_increment.py
class AutoIncrementMixin:
    """Mixin for AUTO_INCREMENT / IDENTITY column support.

    This is a *DDL column-definition* capability: the auto-increment attribute
    is declared on a column in CREATE TABLE and rendered by the DDLColumnMixin
    family (e.g. SQLite ``AUTOINCREMENT``, MySQL ``AUTO_INCREMENT``, SQL
    standard ``GENERATED ... AS IDENTITY``). It is orthogonal to RETURNING
    support — MySQL generates keys server-side without a RETURNING clause,
    while PostgreSQL offers both.

    The default reflects the generic behaviour: nearly all SQL databases
    provide server-side key generation, so ``supports_auto_increment()``
    returns ``True`` and composing dialects inherit it unchanged. Backends
    that deviate (e.g. ClickHouse, which has no server-side key generation
    and requires client-side ids) override this to return ``False``.
    """

    def supports_auto_increment(self) -> bool:
        """Whether AUTO_INCREMENT/IDENTITY column attributes are supported."""
        return True