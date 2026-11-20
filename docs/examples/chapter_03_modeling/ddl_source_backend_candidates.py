"""Chapter 3: Modeling Data - UseSqlType Candidates on SQLite

Executable companion to docs/en_US/modeling/ddl_source.md
("Backend Expression Integration") and definition.md Section 1.1.

A UseSqlType marker carries ordered DataType candidates. DDLSource preserves
all of them; a consumer holding a concrete dialect selects the first one it can
render ("first renderable wins"). Only core/generic types are used here -- the
built-in SQLite backend is the only backend involved.

Demonstrated:
1. column_data_type() preserves every candidate and its order.
2. Rendering with a real SQLite dialect picks the first renderable candidate.
3. A candidate the dialect cannot render is skipped, and a field whose only
   candidate is incompatible is refused by the consumer.
"""

from copy import copy
from typing import Annotated

from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedDataTypeError
from rhosocial.activerecord.backend.expression.statements import ColumnDefinition
from rhosocial.activerecord.backend.expression.types import IntegerType, TextType, VarCharType, XmlType
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
from rhosocial.activerecord.base import UseSqlType
from rhosocial.activerecord.base.derivation import build_create_table_statement
from rhosocial.activerecord.model import ActiveRecord


class Candidates(ActiveRecord):
    """Two generic candidates in priority order."""

    @classmethod
    def table_name(cls):
        return "candidates"

    __primary_key__ = "id"

    id: Annotated[int, UseSqlType(IntegerType())]
    identifier: Annotated[str, UseSqlType(TextType(), VarCharType(length=64))]


class SkippingFirst(ActiveRecord):
    """The first candidate is a generic type SQLite cannot render."""

    @classmethod
    def table_name(cls):
        return "skipping_first"

    __primary_key__ = "id"

    id: Annotated[int, UseSqlType(IntegerType())]
    identifier: Annotated[str, UseSqlType(XmlType(), TextType(), VarCharType(length=64))]


class IncompatibleOnly(ActiveRecord):
    """No candidate SQLite can render -- refusal surfaces at consumption."""

    @classmethod
    def table_name(cls):
        return "incompatible_only"

    __primary_key__ = "id"

    id: Annotated[int, UseSqlType(IntegerType())]
    value: Annotated[str, UseSqlType(XmlType())]


def render_candidate(dialect, candidate):
    """Render one candidate through the dialect, on a copy (never the model)."""
    bound = copy(candidate)
    bound.dialect = dialect
    return ColumnDefinition(dialect, "identifier", bound).to_sql()[0]


def rule(title: str):
    print()
    print(title)
    print("-" * len(title))


def main():
    dialect = SQLiteDialect(version=(3, 53, 0))

    rule("1. The source keeps every candidate, in order")
    marker = Candidates.column_data_type("identifier")
    print("  column_data_type('identifier') ->", marker)
    print("  candidates:", [type(t).__name__ for t in marker.data_types])
    print("  marker.data_type (first)     :", type(marker.data_type).__name__)

    rule("2. First renderable wins, per candidate")
    for candidate in marker.data_types:
        try:
            print(f"  {type(candidate).__name__:<12} -> {render_candidate(dialect, candidate)}")
        except (UnsupportedDataTypeError, TypeError) as exc:
            print(f"  {type(candidate).__name__:<12} -> refused: {exc}")
    print("  The deriver would stop at the first one that renders: TextType.")
    print(
        "  SQL:",
        build_create_table_statement(Candidates, dialect).to_sql()[0],
    )

    rule("3. An incompatible candidate is skipped, not rewritten")
    skipped = SkippingFirst.column_data_type("identifier")
    print("  candidates:", [type(t).__name__ for t in skipped.data_types])
    sql = build_create_table_statement(SkippingFirst, dialect).to_sql()[0]
    print("  SQL:", sql)
    print("  XmlType has no SQLite formatter, so the next renderable candidate won.")

    rule("4. An incompatible-only field is refused at consumption")
    print("  declaration still reads:", IncompatibleOnly.column_data_type("value"))
    try:
        build_create_table_statement(IncompatibleOnly, dialect)
    except (ValueError, UnsupportedDataTypeError, TypeError) as exc:
        print("  refused:", str(exc).splitlines()[0])
        print("           ", str(exc).splitlines()[1].strip() if len(str(exc).splitlines()) > 1 else "")
    print("  Source collection succeeded; the consumer reported why each candidate")
    print("  failed instead of silently falling back to TEXT.")
    print()


if __name__ == "__main__":
    main()
