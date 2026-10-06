# src/rhosocial/activerecord/backend/dialect/protocols/altertablemodifiersupport.py
"""AlterTableModifierSupport protocol.

Re-exported from :mod:`rhosocial.activerecord.backend.dialect.protocols`;
see that package for the full protocol surface and the rules the conformance
tests enforce.
"""

from typing import Protocol, runtime_checkable

@runtime_checkable
class AlterTableModifierSupport(Protocol):
    """
    Protocol for ALTER TABLE ``IF [NOT] EXISTS`` modifier support.

    These modifiers make ALTER TABLE actions re-runnable:
    - ``ADD COLUMN IF NOT EXISTS``
    - ``DROP COLUMN IF EXISTS``
    - ``DROP CONSTRAINT IF EXISTS``

    Backends that support a given modifier advertise it via the matching
    ``supports_*`` switch returning ``True``; backends that reject it (raising
    ``UnsupportedFeatureError``) return ``False``. Generic testsuite tests use
    ``@requires_protocol`` markers against this protocol to skip unsupported
    backends.
    """

    def supports_add_column_if_not_exists(self) -> bool:
        """Whether ``ALTER TABLE ADD COLUMN IF NOT EXISTS`` is supported."""
        ...  # pragma: no cover

    def supports_drop_column_if_exists(self) -> bool:
        """Whether ``ALTER TABLE DROP COLUMN IF EXISTS`` is supported."""
        ...  # pragma: no cover

    def supports_drop_constraint_if_exists(self) -> bool:
        """Whether ``ALTER TABLE DROP CONSTRAINT IF EXISTS`` is supported."""
        ...  # pragma: no cover
