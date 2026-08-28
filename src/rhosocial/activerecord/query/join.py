# src/rhosocial/activerecord/query/join.py
"""JoinQueryMixin implementation for building JOIN clauses using a chained expression model."""

from typing import List, Union, Type, Optional, Iterable

from ..interface import IQuery, IActiveRecord
from ..backend.expression import SQLPredicate, TableExpression, RawSQLPredicate, JoinExpression
from .utils import convert_qmark_placeholder


class JoinQueryMixin:
    """
    Provides a fluent API for building complex JOIN clauses on a query.
    This mixin is designed to be used by a query builder class. It manages
    a chainable `join_clause` expression that represents the entire FROM and JOIN
    part of a SQL query.

    Note: The availability and specific behavior of certain JOIN types (e.g., NATURAL JOIN,
    RIGHT JOIN, FULL JOIN) can vary significantly across different database backends.
    Always consult your specific database's documentation for full compatibility details.
    """

    # The `join_clause` stores the constructed JoinExpression tree (or None if no joins).
    join_clause: Optional[JoinExpression]

    def _resolve_right_table(
        self, right: Union[str, Type["IActiveRecord"], TableExpression], alias: Optional[str]
    ) -> Union[TableExpression, JoinExpression]:
        """Helper method to resolve the right-hand side of a join into a TableExpression."""
        dialect = self.backend().dialect
        if isinstance(right, str):
            return TableExpression(dialect, right, alias=alias)
        # Check if it's a model class (an actual class object, not an instance)
        if isinstance(right, type) and issubclass(right, IActiveRecord):
            table_name = right.table_name()
            # Only alias when explicitly requested. Forced aliases would turn
            # every range into an aliased one, breaking schema-qualified column
            # references emitted from plain field accessors.
            return TableExpression(dialect, table_name, schema_name=right.schema_name(), alias=alias)
        if isinstance(right, (TableExpression, JoinExpression)):
            # If an alias is provided, apply it to the expression
            if alias:
                return right.as_(alias)
            return right
        raise TypeError(f"Unsupported type for 'right' join argument: {type(right)}")

    def _resolve_on_condition(
        self,
        on: Optional[Union[str, SQLPredicate]],
        on_params: Optional[Iterable] = None,
    ) -> Optional[SQLPredicate]:
        """Helper method to resolve the ON condition into a predicate."""
        if on is None:
            return None
        dialect = self.backend().dialect
        if isinstance(on, str):
            converted = convert_qmark_placeholder(dialect, on)
            return RawSQLPredicate(dialect, converted, params=tuple(on_params) if on_params else ())
        if isinstance(on, SQLPredicate):
            return on
        raise TypeError(f"Unsupported type for 'on' condition: {type(on)}")

    def _perform_join(
        self,
        join_type: str,
        right: Union[str, Type["IActiveRecord"], TableExpression],
        on: Optional[Union[str, SQLPredicate]],
        alias: Optional[str],
        natural: bool = False,
        on_params: Optional[Iterable] = None,
        using: Optional[List[str]] = None,
    ) -> "IQuery[IActiveRecord]":
        """Internal helper to construct and chain join expressions."""
        dialect = self.backend().dialect
        right_table = self._resolve_right_table(right, alias)
        condition = self._resolve_on_condition(on, on_params)

        if self.join_clause is None:
            # First join. The left table is the main model's table.
            # No implicit alias: plain (schema-qualified) column references in
            # ON/WHERE predicates must stay resolvable against this range.
            left_table = TableExpression(
                dialect,
                self.model_class.table_name(),
                schema_name=self.model_class.schema_name(),
            )
            self.join_clause = JoinExpression(
                dialect=dialect,
                left_table=left_table,  # Use the model's table as the left table
                right_table=right_table,
                join_type=join_type,
                condition=condition,
                using=using,
                natural=natural,
            )
        else:
            # Subsequent join. Chain onto the existing JoinExpression.
            self.join_clause = self.join_clause.join(
                right_table=right_table, join_type=join_type, condition=condition,
                using=using, natural=natural,
            )
        return self

    def join(
        self,
        right: Union[str, Type["IActiveRecord"], TableExpression],
        on: Optional[Union[str, SQLPredicate]] = None,
        alias: Optional[str] = None,
        on_params: Optional[Iterable] = None,
        using: Optional[List[str]] = None,
    ) -> "IQuery[IActiveRecord]":
        """
        Adds a JOIN clause to the query (defaults to INNER JOIN).

        Notes:
            - Each side keeps its own schema/table qualifiers (columns from
              ``Model.c.*`` are fully qualified), so joining models that live
              in different schemas works directly — e.g. PostgreSQL renders
              ``FROM "shop"."orders" JOIN "crm"."customers" ON ...``.
            - For self-joins pass an explicit ``alias`` and address the joined
              copy through ``Model.c.with_table_alias(alias)``; see FieldProxy.
            - Unqualified hand-written columns follow standard SQL resolution;
              genuinely ambiguous references raise a database error rather
              than being silently attributed to either side.
        """
        return self._perform_join("JOIN", right, on, alias, on_params=on_params, using=using)

    def inner_join(
        self,
        right: Union[str, Type["IActiveRecord"], TableExpression],
        on: Optional[Union[str, SQLPredicate]] = None,
        alias: Optional[str] = None,
        on_params: Optional[Iterable] = None,
        using: Optional[List[str]] = None,
    ) -> "IQuery[IActiveRecord]":
        """
        Adds an INNER JOIN clause to the query.
        """
        return self._perform_join("INNER JOIN", right, on, alias, on_params=on_params, using=using)

    def left_join(
        self,
        right: Union[str, Type["IActiveRecord"], TableExpression],
        on: Optional[Union[str, SQLPredicate]] = None,
        alias: Optional[str] = None,
        on_params: Optional[Iterable] = None,
        using: Optional[List[str]] = None,
    ) -> "IQuery[IActiveRecord]":
        """
        Adds a LEFT JOIN clause to the query.
        """
        return self._perform_join("LEFT JOIN", right, on, alias, on_params=on_params, using=using)

    def right_join(
        self,
        right: Union[str, Type["IActiveRecord"], TableExpression],
        on: Optional[Union[str, SQLPredicate]] = None,
        alias: Optional[str] = None,
        on_params: Optional[Iterable] = None,
        using: Optional[List[str]] = None,
    ) -> "IQuery[IActiveRecord]":
        """
        Adds a RIGHT JOIN clause to the query.
        """
        return self._perform_join("RIGHT JOIN", right, on, alias, on_params=on_params, using=using)

    def full_join(
        self,
        right: Union[str, Type["IActiveRecord"], TableExpression],
        on: Optional[Union[str, SQLPredicate]] = None,
        alias: Optional[str] = None,
        on_params: Optional[Iterable] = None,
        using: Optional[List[str]] = None,
    ) -> "IQuery[IActiveRecord]":
        """
        Adds a FULL OUTER JOIN clause to the query.
        """
        return self._perform_join("FULL JOIN", right, on, alias, on_params=on_params, using=using)

    def straight_join(
        self,
        right: Union[str, Type["IActiveRecord"], TableExpression],
        on: Optional[Union[str, SQLPredicate]] = None,
        alias: Optional[str] = None,
        on_params: Optional[Iterable] = None,
    ) -> "IQuery[IActiveRecord]":
        """
        Adds a MySQL STRAIGHT_JOIN clause (forces the optimizer's join order).

        Only supported by backends whose dialect declares
        ``supports_straight_join()``; gate tests with
        ``requires_protocol("JoinSupport", "supports_straight_join")``.
        """
        return self._perform_join("STRAIGHT_JOIN", right, on, alias, on_params=on_params)

    def cross_join(
        self, right: Union[str, Type["IActiveRecord"], TableExpression], alias: Optional[str] = None
    ) -> "IQuery[IActiveRecord]":
        """
        Adds a CROSS JOIN clause to the query.
        """
        return self._perform_join("CROSS JOIN", right, None, alias)

    def natural_join(
        self,
        right: Union[str, Type["IActiveRecord"], TableExpression],
        join_type: str = "JOIN",
        alias: Optional[str] = None,
    ) -> "IQuery[IActiveRecord]":
        """
        Adds a NATURAL JOIN clause to the query.

        Note:
            NATURAL JOIN implicitly joins tables on all columns that have the same name in both tables.
            This can lead to unexpected results if column names change or do not align as expected.
            It is generally recommended to use explicit `ON` or `USING` clauses for clarity and safety.
            Support for NATURAL JOIN may also vary across different database backends.

        Args:
            right: The right-hand side of the join. Can be a table name (str), a IActiveRecord class,
                   or a TableExpression.
            join_type: The type of join to perform (e.g., "JOIN", "INNER JOIN"). Defaults to "JOIN".
            alias: An optional alias for the joined result.

        Returns:
            Query instance for method chaining.
        """
        return self._perform_join(join_type, right, None, alias, natural=True)
