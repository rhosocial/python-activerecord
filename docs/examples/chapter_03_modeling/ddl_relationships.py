"""Chapter 3: Modeling Data - DDL with Relationships

Demonstrates DDL operations for tables with foreign key relationships:
1. Create parent table (Author)
2. Create child table (Post) with foreign key constraint
3. Create many-to-many junction table (PostTag)
"""

from typing import ClassVar

from rhosocial.activerecord.backend.expression import (
    ColumnConstraint,
    ColumnDefinition,
    CreateTableStatement,
)
from rhosocial.activerecord.backend.expression.objects import Table
from rhosocial.activerecord.backend.expression.statements import (
    ColumnNotNullConstraint,
    ColumnPrimaryKeyConstraint,
    ColumnUniqueConstraint,
    ForeignKeyConstraint,
    ReferentialAction,
    TableConstraint,
    TablePrimaryKeyConstraint,
)
from rhosocial.activerecord.backend.expression.types import IntegerType, TextType, VarCharType
from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.base import FieldProxy
from rhosocial.activerecord.model import ActiveRecord


class Author(ActiveRecord):
    """Author Model for DDL relationship demo"""

    __table_name__ = "authors"

    name: str
    email: str

    c: ClassVar[FieldProxy] = FieldProxy()


class Post(ActiveRecord):
    """Post Model for DDL relationship demo"""

    __table_name__ = "posts"

    title: str
    content: str
    author_id: int

    c: ClassVar[FieldProxy] = FieldProxy()


class Tag(ActiveRecord):
    """Tag Model for DDL relationship demo"""

    __table_name__ = "tags"

    name: str

    c: ClassVar[FieldProxy] = FieldProxy()


class PostTag(ActiveRecord):
    """Junction table for many-to-many relationship"""

    __table_name__ = "post_tags"

    post_id: int
    tag_id: int

    c: ClassVar[FieldProxy] = FieldProxy()


def main():
    # Configure Database
    config = SQLiteConnectionConfig(database=":memory:")
    Author.configure(config, SQLiteBackend)

    # Share backend with other models
    Post.__backend__ = Author.__backend__
    Tag.__backend__ = Author.__backend__
    PostTag.__backend__ = Author.__backend__

    # Get dialect from backend
    dialect = Author.__backend__.dialect
    backend = Author.__backend__

    # ============================================================
    # Example 1: Create parent table (Author)
    # ============================================================
    author_columns = [
        ColumnDefinition(
            dialect,
            "id",
            IntegerType(dialect),
            constraints=[
                ColumnConstraint(
                    dialect,
                    branch=ColumnPrimaryKeyConstraint(dialect, is_auto_increment=True),
                )
            ],
        ),
        ColumnDefinition(
            dialect,
            "name",
            VarCharType(dialect, length=100),
            constraints=[ColumnConstraint(dialect, branch=ColumnNotNullConstraint(dialect))],
        ),
        ColumnDefinition(
            dialect,
            "email",
            VarCharType(dialect, length=255),
            constraints=[
                ColumnConstraint(dialect, branch=ColumnNotNullConstraint(dialect)),
                ColumnConstraint(dialect, branch=ColumnUniqueConstraint(dialect)),
            ],
        ),
    ]

    create_authors = CreateTableStatement(
        dialect,
        Table(dialect, "authors"),
        columns=author_columns,
        if_not_exists=True,
    )

    sql, params = create_authors.to_sql()
    print("=== Create Authors Table ===")
    print(f"SQL: {sql}")
    print()

    backend.execute(sql, params)

    # ============================================================
    # Example 2: Create child table (Post) with foreign key
    # ============================================================
    post_columns = [
        ColumnDefinition(
            dialect,
            "id",
            IntegerType(dialect),
            constraints=[
                ColumnConstraint(
                    dialect,
                    branch=ColumnPrimaryKeyConstraint(dialect, is_auto_increment=True),
                )
            ],
        ),
        ColumnDefinition(
            dialect,
            "title",
            VarCharType(dialect, length=200),
            constraints=[ColumnConstraint(dialect, branch=ColumnNotNullConstraint(dialect))],
        ),
        ColumnDefinition(dialect, "content", TextType(dialect)),
        ColumnDefinition(
            dialect,
            "author_id",
            IntegerType(dialect),
            constraints=[ColumnConstraint(dialect, branch=ColumnNotNullConstraint(dialect))],
        ),
    ]

    # Use table_constraints for foreign key at table level.
    # The referenced table is a Table object, not a bare string.
    post_constraints = [
        ForeignKeyConstraint(
            dialect,
            columns=["author_id"],
            foreign_key_table=Table(dialect, "authors"),
            foreign_key_columns=["id"],
            on_delete=ReferentialAction.CASCADE,
            on_update=ReferentialAction.CASCADE,
        )
    ]

    create_posts = CreateTableStatement(
        dialect,
        Table(dialect, "posts"),
        columns=post_columns,
        table_constraints=post_constraints,
        if_not_exists=True,
    )

    sql, params = create_posts.to_sql()
    print("=== Create Posts Table (with FK) ===")
    print(f"SQL: {sql}")
    print()

    backend.execute(sql, params)

    # ============================================================
    # Example 3: Create Tag table
    # ============================================================
    tag_columns = [
        ColumnDefinition(
            dialect,
            "id",
            IntegerType(dialect),
            constraints=[
                ColumnConstraint(
                    dialect,
                    branch=ColumnPrimaryKeyConstraint(dialect, is_auto_increment=True),
                )
            ],
        ),
        ColumnDefinition(
            dialect,
            "name",
            VarCharType(dialect, length=50),
            constraints=[
                ColumnConstraint(dialect, branch=ColumnNotNullConstraint(dialect)),
                ColumnConstraint(dialect, branch=ColumnUniqueConstraint(dialect)),
            ],
        ),
    ]

    create_tags = CreateTableStatement(
        dialect,
        Table(dialect, "tags"),
        columns=tag_columns,
        if_not_exists=True,
    )

    sql, params = create_tags.to_sql()
    print("=== Create Tags Table ===")
    print(f"SQL: {sql}")
    print()

    backend.execute(sql, params)

    # ============================================================
    # Example 4: Create junction table (PostTag) for many-to-many
    # ============================================================
    post_tag_columns = [
        ColumnDefinition(
            dialect,
            "post_id",
            IntegerType(dialect),
            constraints=[ColumnConstraint(dialect, branch=ColumnNotNullConstraint(dialect))],
        ),
        ColumnDefinition(
            dialect,
            "tag_id",
            IntegerType(dialect),
            constraints=[ColumnConstraint(dialect, branch=ColumnNotNullConstraint(dialect))],
        ),
    ]

    # Table-level constraints for composite PK and foreign keys
    post_tag_constraints = [
        # Composite primary key
        TableConstraint(
            dialect,
            branch=TablePrimaryKeyConstraint(dialect, ["post_id", "tag_id"]),
        ),
        # Foreign key to posts table
        ForeignKeyConstraint(
            dialect,
            columns=["post_id"],
            foreign_key_table=Table(dialect, "posts"),
            foreign_key_columns=["id"],
            on_delete=ReferentialAction.CASCADE,
        ),
        # Foreign key to tags table
        ForeignKeyConstraint(
            dialect,
            columns=["tag_id"],
            foreign_key_table=Table(dialect, "tags"),
            foreign_key_columns=["id"],
            on_delete=ReferentialAction.CASCADE,
        ),
    ]

    create_post_tags = CreateTableStatement(
        dialect,
        Table(dialect, "post_tags"),
        columns=post_tag_columns,
        table_constraints=post_tag_constraints,
        if_not_exists=True,
    )

    sql, params = create_post_tags.to_sql()
    print("=== Create PostTags Junction Table ===")
    print(f"SQL: {sql}")
    print()

    backend.execute(sql, params)

    # Introspection: Verify tables and foreign keys
    print("=== Introspection Results ===")
    print()
    tables = backend.introspector.list_tables()
    print("Tables created:")
    for t in tables:
        if t.table_type.name == "BASE_TABLE" and not t.name.startswith("sqlite"):
            print(f"  - {t.name}")

    print()
    print("Foreign keys in 'posts' table:")
    fks = backend.introspector.list_foreign_keys("posts")
    for fk in fks:
        print(f"  - {fk.columns} -> {fk.referenced_table}.{fk.referenced_columns}")

    print()
    print("Foreign keys in 'post_tags' table:")
    fks = backend.introspector.list_foreign_keys("post_tags")
    for fk in fks:
        print(f"  - {fk.columns} -> {fk.referenced_table}.{fk.referenced_columns}")

    print()
    print("=== All relationship DDL operations completed successfully! ===")
    print()
    print("NOTE: This example uses SQLite backend. Different backends (MySQL, PostgreSQL, etc.)")
    print("may have different introspection APIs and DDL support. Refer to specific backend documentation.")


if __name__ == "__main__":
    main()
