"""Chapter 3: Modeling Data - Model Declaration Capabilities

Executable companion to docs/en_US/modeling/definition.md (Sections 1 and 2.1).

Demonstrated:
1. UseSqlType takes multiple ordered DataType candidates (first renderable wins
   *later*, during derivation); UseColumnType takes exactly one column class.
2. column_data_type() and column_type() are dialect-free declaration accessors.
   The framework never reconciles them against each other.
3. A derived field is excluded from ddl_field_names().
4. A semantics-only mixin (TimestampMixin) injects no field; DefaultTimestampMixin
   injects created_at / updated_at.

No database connection and no dialect are needed: everything here is read from
the model declarations themselves.
"""

from datetime import datetime
from typing import Annotated, ClassVar

from rhosocial.activerecord.backend.expression import Column, IntegerColumn, StringColumn
from rhosocial.activerecord.backend.expression.types import IntegerType, TextType, VarCharType
from rhosocial.activerecord.base import DerivedField, UseColumnType, UseSqlType
from rhosocial.activerecord.field import DefaultTimestampMixin, TimestampMixin
from rhosocial.activerecord.model import ActiveRecord


class DeclarationDemo(ActiveRecord):
    """Each field exercises a different corner of the declaration surface."""

    @classmethod
    def table_name(cls):
        return "declaration_demo"

    __primary_key__ = "id"

    id: Annotated[int, UseSqlType(IntegerType())]

    # Storage only: DDL DataType, no column class for Model.c.<field>.
    stored_only: Annotated[str, UseSqlType(VarCharType(length=50))]

    # Operations only: a column class, no DDL DataType.
    ops_only: Annotated[str, UseColumnType(StringColumn)]

    # Both, deliberately mismatched: storing TEXT while offering integer
    # operations is allowed because the two declarations are independent.
    both: Annotated[str, UseSqlType(TextType()), UseColumnType(IntegerColumn)]

    # Neither: a plain Python annotation declares nothing for either accessor.
    plain: int

    # A computed, read-only query field -- not a column.
    total: ClassVar[Annotated[int, DerivedField(lambda d: Column(d, "plain"))]]


class SemanticTimes(TimestampMixin, ActiveRecord):
    """TimestampMixin maintains behavior but injects no fields.

    The model itself must declare created_at / updated_at; the mixin finds them
    by name via created_at_field() / updated_at_field().
    """

    @classmethod
    def table_name(cls):
        return "events_semantic"

    __primary_key__ = "id"

    id: Annotated[int, UseSqlType(IntegerType())]
    created_at: datetime
    updated_at: datetime


class DefaultTimes(DefaultTimestampMixin, ActiveRecord):
    """DefaultTimestampMixin supplies created_at / updated_at by inheritance."""

    @classmethod
    def table_name(cls):
        return "events_default"

    __primary_key__ = "id"

    id: Annotated[int, UseSqlType(IntegerType())]


def rule(title: str):
    print()
    print(title)
    print("-" * len(title))


def show(label: str, value):
    print(f"{label:<34} {value!r}")


def main():
    rule("1. UseSqlType: ordered candidates")
    marker = UseSqlType(VarCharType(length=64), TextType(), VarCharType(length=64))
    show("declared candidates", [type(t).__name__ for t in marker.data_types])
    print("  (duplicates are dropped by value; declaration order is preserved)")

    rule("2. UseColumnType: exactly one column class")
    show("single class accepted", UseColumnType(StringColumn).column_class.__name__)
    try:
        UseColumnType(StringColumn, IntegerColumn)
    except TypeError as exc:
        print("  two classes refused:", str(exc)[:110], "...")

    rule("3. The two accessors are dialect-free and NOT reconciled")
    for field in ("stored_only", "ops_only", "both", "plain"):
        storage = DeclarationDemo.column_data_type(field)
        operations = DeclarationDemo.column_type(field)
        show(f"column_data_type({field!r})", [type(t).__name__ for t in storage.data_types] if storage else None)
        show(f"column_type({field!r})", operations)
    print("  'both' stores TEXT yet offers IntegerColumn operations: no cross-check.")
    print("  Neither accessor binds a dialect or picks a winner -- that happens")
    print("  later, in base/derivation.py (storage) and FieldProxy (operations).")

    rule("4. Derived field is excluded from DDL")
    show("'total' in model_fields", "total" in DeclarationDemo.model_fields)
    show("is_derived_field('total')", DeclarationDemo.is_derived_field("total"))
    show("ddl_field_names()", DeclarationDemo.ddl_field_names())
    print("  'total' is a query-time computed value, not a column.")

    rule("5. Semantics-only mixin vs Default* mixin")
    show("SemanticTimes.ddl_field_names()", SemanticTimes.ddl_field_names())
    show("DefaultTimes.ddl_field_names()", DefaultTimes.ddl_field_names())
    print("  SemanticTimes declares created_at/updated_at itself; the mixin adds no")
    print("  field. DefaultTimes declares only id and still gains the two columns.")
    print("  Field order is presentation only, not a contract.")
    print()


if __name__ == "__main__":
    main()
