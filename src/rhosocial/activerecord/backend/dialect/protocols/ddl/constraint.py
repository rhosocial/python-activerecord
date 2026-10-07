# src/rhosocial/activerecord/backend/dialect/protocols/constraintsupport.py
"""ConstraintSupport protocol.

Re-exported from :mod:`rhosocial.activerecord.backend.dialect.protocols`;
see that package for the full protocol surface and the rules the conformance
tests enforce.
"""

from typing import Tuple, Protocol, runtime_checkable, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from ....expression.statements import (
        AlterConstraint,
        ColumnConstraint,
        ReferencesClause,
        TableConstraint,
        ValidateConstraint,
    )


@runtime_checkable
class ConstraintSupport(Protocol):
    """
    Protocol for DDL constraint capability detection.

    Based on SQL standard constraint features. All methods represent
    capabilities defined in SQL standards (SQL-86 through SQL:2016).
    Backend-proprietary features (e.g., PostgreSQL NOT VALID, EXCLUDE)
    are defined in their own backend-specific protocols.

    SQL Standard Reference:
    - SQL-86: PRIMARY KEY, UNIQUE, NOT NULL, FOREIGN KEY
    - SQL-89: FOREIGN KEY (enhanced)
    - SQL-92: CHECK, ON DELETE/UPDATE, ADD/DROP CONSTRAINT
    - SQL:1999: MATCH (SIMPLE/PARTIAL/FULL), DEFERRABLE/INITIALLY
    - SQL:2016: ENFORCED/NOT ENFORCED
    """

    def supports_constraint_novalidate(self) -> bool:
        """Whether the engine accepts the form ``constraint_novalidate``.

        Defaults to ``False``.
        """
        ...  # pragma: no cover

    def supports_exclude_constraint(self) -> bool:
        """Whether the engine accepts the form ``exclude_constraint``.

        Defaults to ``False``.
        """
        ...  # pragma: no cover

    def supports_drop_column(self) -> bool:
        """Whether the engine accepts the form ``drop_column``.

        Defaults to ``False``.
        """
        ...  # pragma: no cover

    def supports_foreign_key_on_delete(self) -> bool:
        """Whether the engine accepts the form ``foreign_key_on_delete``.

        Defaults to ``False``.
        """
        ...  # pragma: no cover

    def supports_foreign_key_on_update(self) -> bool:
        """Whether the engine accepts the form ``foreign_key_on_update``.

        Defaults to ``False``.
        """
        ...  # pragma: no cover

    def supports_column_character_set(self) -> bool:
        """Whether the engine accepts the form ``column_character_set``.

        Defaults to ``False``.
        """
        ...  # pragma: no cover

    def supports_column_collation(self) -> bool:
        """Whether the engine accepts the form ``column_collation``.

        Defaults to ``False``.
        """
        ...  # pragma: no cover

    def supports_column_comment(self) -> bool:
        """Whether the engine accepts the form ``column_comment``.

        Defaults to ``False``.
        """
        ...  # pragma: no cover

    # Basic constraint types (SQL-86/SQL-92)

    def supports_primary_key_constraint(self) -> bool:
        """Whether PRIMARY KEY constraints are supported."""
        ...  # pragma: no cover

    def supports_unique_constraint(self) -> bool:
        """Whether UNIQUE constraints are supported."""
        ...  # pragma: no cover

    def supports_not_null_constraint(self) -> bool:
        """Whether NOT NULL constraints are supported."""
        ...  # pragma: no cover

    def supports_check_constraint(self) -> bool:
        """Whether CHECK constraints are supported and enforced."""
        ...  # pragma: no cover

    def supports_foreign_key_constraint(self) -> bool:
        """Whether FOREIGN KEY constraints are supported."""
        ...  # pragma: no cover

    # FK referential actions (SQL-92)

    def supports_fk_on_delete(self) -> bool:
        """Whether ON DELETE referential actions are supported."""
        ...  # pragma: no cover

    def supports_fk_on_update(self) -> bool:
        """Whether ON UPDATE referential actions are supported."""
        ...  # pragma: no cover

    # FK formatter methods

    def format_references_clause(self, expr: "ReferencesClause") -> Tuple[str, tuple]:
        """Format a shared ``REFERENCES`` clause (column/table foreign keys).

        Args:
            expr: The references clause carrying the referenced table/columns
                and optional actions.

        Returns:
            Tuple of (SQL fragment, empty params tuple).
        """
        ...  # pragma: no cover

    def format_foreign_key_constraint(self, t_const: "TableConstraint") -> Tuple[str, tuple]:
        """Format a table-level FOREIGN KEY constraint, including ON DELETE / ON UPDATE.

        Args:
            t_const: The table constraint to format (may be a ForeignKeyConstraint).

        Returns:
            Tuple of (SQL string, empty params tuple).
        """
        ...  # pragma: no cover

    def format_column_fk_constraint(self, constraint: "ColumnConstraint") -> Tuple[str, tuple]:
        """Format a column-level FOREIGN KEY reference clause with actions.

        Args:
            constraint: The column constraint with FK reference and actions.

        Returns:
            Tuple of (SQL fragment, empty params tuple).
        """
        ...  # pragma: no cover

    # FK match modes (SQL:1999)

    def supports_fk_match(self) -> bool:
        """Whether MATCH {SIMPLE|PARTIAL|FULL} is supported."""
        ...  # pragma: no cover

    # Constraint deferral (SQL:1999)

    def supports_deferrable_constraint(self) -> bool:
        """Whether DEFERRABLE / INITIALLY DEFERRED/IMMEDIATE is supported."""
        ...  # pragma: no cover

    # Constraint enforcement control (SQL:2016)

    def supports_constraint_enforced(self) -> bool:
        """Whether ENFORCED / NOT ENFORCED constraint control is supported."""
        ...  # pragma: no cover

    def supports_alter_constraint_enforced(self) -> bool:
        """Whether ALTER CONSTRAINT enforcement control is supported."""
        ...

    def supports_validate_constraint(self) -> bool:
        """Whether VALIDATE CONSTRAINT is supported."""
        ...

    def format_alter_constraint_action(self, action: "AlterConstraint") -> Tuple[str, tuple]:
        """Format an ALTER CONSTRAINT enforcement action."""
        ...

    def format_validate_constraint_action(self, action: "ValidateConstraint") -> Tuple[str, tuple]:
        """Format a VALIDATE CONSTRAINT action."""
        ...

    # ALTER TABLE constraint operations (SQL-92)

    def supports_add_constraint(self) -> bool:
        """Whether ALTER TABLE ADD CONSTRAINT is supported."""
        ...  # pragma: no cover

    def supports_drop_constraint(self) -> bool:
        """Whether ALTER TABLE DROP CONSTRAINT is supported."""
        ...  # pragma: no cover
