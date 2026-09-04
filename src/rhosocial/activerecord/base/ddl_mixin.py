# src/rhosocial/activerecord/base/ddl_mixin.py
"""
Mixin that enables DDL-aware model declarations.

Registering ``DDLMixin`` in an ``ActiveRecord`` subclass's MRO activates the
two metaclass feature handlers defined in ``ddl_handlers``:

- ``DDLFieldAnnotationHandler``  — processes per-field ``Annotated`` DDL markers
- ``DDLModelAnnotationHandler``  — processes model-level class variables
"""

from .ddl_handlers import DDLFieldAnnotationHandler, DDLModelAnnotationHandler


class DDLMixin:
    """Adds DDL declaration support to an ActiveRecord model.

    Declare one or more of the following class variables to control DDL
    generation:

    .. code-block:: python

        from typing import Annotated
        from rhosocial.activerecord.backend.expression.types import (
            VarCharType, JsonBType, JsonType, TextType,
        )
        from rhosocial.activerecord.base.fields import (
            UseSqlType, UseIndex, UseConstraint, TableOptions,
            ColumnConstraintType,
        )
        from rhosocial.activerecord.backend.expression.statements.ddl_table import (
            IndexDefinition, TableConstraint, TableConstraintType,
        )

        class User(ActiveRecord, DDLMixin):
            __table_name__ = "users"

            # Table-level options
            __table_options__ = TableOptions(
                charset="utf8mb4",
                collation="utf8mb4_unicode_ci",
            )

            # Composite indexes
            __table_indexes__ = [
                IndexDefinition(
                    name="idx_name_email",
                    columns=["name", "email"],
                    unique=False,
                ),
            ]

            # Table-level constraints
            __table_constraints__ = [
                TableConstraint(
                    constraint_type=TableConstraintType.CHECK,
                    check_condition=...,  # SQLPredicate
                ),
            ]

            # Field-level DDL markers
            email: Annotated[str, UseSqlType(VarCharType(length=255))]
            name:  Annotated[str, UseIndex("idx_name", unique=False)]
            bio:   Annotated[str, UseConstraint(
                ColumnConstraintType.COLLATE,
                collation="utf8mb4_unicode_ci",
            )]

    Attributes:
        * ``__table_field_sql_types__``   dataclass attribute set by the metaclass
        * ``__table_field_indexes__``     dataclass attribute set by the metaclass
        * ``__table_field_constraints__`` dataclass attribute set by the metaclass
        * ``__ddl_indexes__``           dataclass attribute set by the metaclass
        * ``__ddl_table_options__``     dataclass attribute set by the metaclass
        * ``__ddl_constraints__``       dataclass attribute set by the metaclass
    """

    _feature_handlers = [
        DDLFieldAnnotationHandler,
        DDLModelAnnotationHandler,
    ]

    # ------------------------------------------------------------------
    # DDL generation entry points (Phase 2)
    # ------------------------------------------------------------------
    @classmethod
    def generate_create_table(cls, dialect=None, *, if_not_exists=False, temporary=False):
        """Generate a ``CreateTableExpression`` instance for this model.

        The generator returns an *expression instance* — it does not emit SQL
        directly. Callers decide what to do with it (e.g. ``.to_sql()``).

        By default the dialect is taken from the model's configured backend
        (``cls.backend().dialect``); callers may pass an explicit *dialect* to
        generate DDL for a specific backend without configuring one.

        Args:
            dialect: An optional ``SQLDialectBase``; when ``None`` the model's
                ``cls.backend().dialect`` is used.
            if_not_exists: Request ``IF NOT EXISTS`` (subject to backend support).
            temporary: Request a ``TEMPORARY`` table.

        Returns:
            A ``CreateTableExpression`` instance.
        """
        from .ddl_generator import ModelSchemaGenerator

        if dialect is None:
            dialect = cls.backend().dialect
        return ModelSchemaGenerator.generate_create_table(
            cls, dialect, if_not_exists=if_not_exists, temporary=temporary
        )

    @classmethod
    def generate_drop_table(cls, dialect=None, *, if_exists=False, cascade=None):
        """Generate a ``DropTableExpression`` instance for this model.

        Only the model's table name is derived here — dependent-object
        behavior (``cascade``) is subject to dialect capability gating at
        render time (``UnsupportedFeatureError`` when the dialect does not
        support the requested form, e.g. SQLite / SQL Server).

        Args:
            dialect: An optional ``SQLDialectBase``; when ``None`` the model's
                ``cls.backend().dialect`` is used.
            if_exists: Request ``IF EXISTS`` (subject to backend support).
            cascade: ``None`` (dialect default), ``True`` (CASCADE or
                dialect-specific equivalent), ``False`` (RESTRICT).

        Returns:
            A ``DropTableExpression`` instance.
        """
        from .ddl_generator import ModelSchemaGenerator

        if dialect is None:
            dialect = cls.backend().dialect
        return ModelSchemaGenerator.generate_drop_table(
            cls, dialect, if_exists=if_exists, cascade=cascade
        )