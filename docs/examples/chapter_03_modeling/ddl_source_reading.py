"""Chapter 3: Modeling Data - Reading DDLSource Declarations

Executable companion to docs/en_US/modeling/ddl_source.md ("Reading Example").

DDLSource reads what a model *declares*. It is dialect-free: it never binds a
backend, never chooses a candidate, never renders SQL, and never touches a
database. This example therefore opens no connection at all.

Demonstrated:
1. isinstance(Model, DDLSource)
2. table-level accessors (table_name, primary_key_columns, table_indexes, ...)
3. field-level accessors (python type, optionality, column name, declared type,
   column class, constraints, attributes, annotations, indexes, comment,
   generated column)
4. batch helpers (columns_name, columns_data_type, ...)
"""

from typing import Annotated, Optional

from rhosocial.activerecord.backend.expression import Column, Literal
from rhosocial.activerecord.backend.expression.statements import (
    ColumnGeneratedConstraint,
    ColumnNotNullConstraint,
    TableConstraint,
    TableUniqueConstraint,
)
from rhosocial.activerecord.backend.expression.types import IntegerType, TextType, VarCharType
from rhosocial.activerecord.base import (
    CollationAttribute,
    DDLSource,
    UseColumn,
    UseColumnAttributes,
    UseComment,
    UseConstraint,
    UseGeneratedColumn,
    UseIndex,
    UseSqlType,
)
from rhosocial.activerecord.model import ActiveRecord


class Account(ActiveRecord):
    """Declarations only -- no backend is configured for this model."""

    @classmethod
    def table_name(cls):
        return "accounts"

    # Primary keys name the *physical* column (UseColumn("id") below).
    __primary_key__ = "id"

    # A table-level declaration is returned as written, not synthesized.
    __table_constraints__ = [
        TableConstraint(None, branch=TableUniqueConstraint(None, ["status"])),
    ]

    account_id: Annotated[int, UseColumn("id"), UseSqlType(IntegerType())]
    display_name: Annotated[
        str,
        UseSqlType(VarCharType(length=120)),
        UseIndex("idx_accounts_display_name"),
        UseColumnAttributes(CollationAttribute(name="und:ci")),
        UseComment("display name"),
    ]
    status: Annotated[str, UseConstraint(ColumnNotNullConstraint), UseSqlType(TextType())] = "active"
    note: Optional[str] = None
    computed: Annotated[
        str,
        UseSqlType(TextType()),
        UseGeneratedColumn(lambda d: ColumnGeneratedConstraint(d, Literal(d, "X", inline=True))),
    ]


def rule(title: str):
    print()
    print(title)
    print("-" * len(title))


def show(label: str, value):
    print(f"{label:<32} {value!r}")


def main():
    rule("0. Protocol")
    show("isinstance(Account, DDLSource)", isinstance(Account, DDLSource))

    rule("1. Table-level accessors")
    show("table_name()", Account.table_name())
    show("schema_name()", Account.schema_name())
    show("primary_key_columns()", Account.primary_key_columns())
    show("is_composite_pk()", Account.is_composite_pk())
    show("partition_key_columns()", Account.partition_key_columns())
    show("object_type()", Account.object_type())
    show("table_options()", Account.table_options())
    show("table_storage_options()", Account.table_storage_options())
    show("table_partition()", Account.table_partition())
    show("table_indexes()", [idx.name for idx in Account.table_indexes()])
    show("table_constraints()", [type(c.branch).__name__ for c in Account.table_constraints()])
    show("table_inherits()", Account.table_inherits())
    show("table_tablespace()", Account.table_tablespace())

    rule("2. Field enumeration and Python facts")
    show("ddl_field_names()", Account.ddl_field_names())
    show("is_derived_field('display_name')", Account.is_derived_field("display_name"))
    for field in ("account_id", "display_name", "status", "note"):
        show(f"field_python_type({field!r})", Account.field_python_type(field).__name__)
        show(f"field_is_optional({field!r})", Account.field_is_optional(field))

    rule("3. Field-level DDL accessors")
    for field in Account.ddl_field_names():
        marker = Account.column_data_type(field)
        data_types = [type(t).__name__ for t in marker.data_types] if marker is not None else None
        show(f"column_name({field!r})", Account.column_name(field))
        show(f"column_data_type({field!r})", data_types)
        show(f"column_type({field!r})", Account.column_type(field))
        show(
            f"column_constraints({field!r})",
            [type(c.branch).__name__ for c in Account.column_constraints(field)],
        )
        show(f"column_attributes({field!r})", Account.column_attributes(field))
        show(
            f"column_annotations({field!r})",
            [type(a).__name__ for a in Account.column_annotations(field)],
        )
        show(
            f"column_indexes({field!r})",
            [(idx.name, idx.columns) for idx in Account.column_indexes(field)],
        )
        show(f"column_comment({field!r})", Account.column_comment(field))
        generated = Account.generated_column(field)
        show(f"generated_column({field!r})", type(generated).__name__ if generated else None)

    rule("4. Batch helpers ({field: value})")
    show("columns_name()", Account.columns_name())
    show(
        "columns_data_type()",
        {
            field: [type(t).__name__ for t in marker.data_types] if marker else None
            for field, marker in Account.columns_data_type().items()
        },
    )
    show(
        "columns_constraints()",
        {f: [type(c.branch).__name__ for c in cs] for f, cs in Account.columns_constraints().items()},
    )
    show("columns_attributes()", Account.columns_attributes())
    show(
        "columns_indexes()",
        {f: [idx.name for idx in idxs] for f, idxs in Account.columns_indexes().items()},
    )
    show("columns_comment()", Account.columns_comment())
    show("columns_generated()", {f: type(v).__name__ if v else None for f, v in Account.columns_generated().items()})
    show("columns_options()", Account.columns_options())

    rule("5. Observation")
    print("Every value above is a declaration read from the model class. No dialect")
    print("was bound and no SQL was rendered -- UseSqlType candidates, constraints,")
    print("indexes and the generated-column factory stay exactly as declared.")
    print()


if __name__ == "__main__":
    main()
