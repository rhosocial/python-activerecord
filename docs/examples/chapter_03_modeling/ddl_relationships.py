"""
Chapter 3: Modeling Data - DDL with Relationships
Demonstrates DDL operations for tables with foreign key relationships:
1. Create parent table (Author)
2. Create child table (Post) with foreign key constraint
3. Create many-to-many junction table (PostTag)
"""

from typing import ClassVar
from pydantic import Field
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.base import FieldProxy
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend, SQLiteConnectionConfig
from rhosocial.activerecord.backend.expression import ColumnDefinition, CreateTableExpression
from rhosocial.activerecord.backend.expression.statements import (
    ColumnConstraint,
    ColumnConstraintType,
    TableConstraint,
    TableConstraintType,
    ForeignKeyConstraint,
    ReferentialAction,
)


class Author(ActiveRecord):
    """Author Model for DDL relationship demo"""
    name: str
    email: str

    c: ClassVar[FieldProxy] = FieldProxy()

    @classmethod
    def table_name(cls) -> str:
        return "authors"


class Post(ActiveRecord):
    """Post Model for DDL relationship demo"""
    title: str
    content: str
    author_id: int

    c: ClassVar[FieldProxy] = FieldProxy()

    @classmethod
    def table_name(cls) -> str:
        return "posts"


class Tag(ActiveRecord):
    """Tag Model for DDL relationship demo"""
    name: str = Field(..., max_length=50)

    c: ClassVar[FieldProxy] = FieldProxy()

    @classmethod
    def table_name(cls) -> str:
        return "tags"


class PostTag(ActiveRecord):
    """Junction table for many-to-many relationship"""
    post_id: int
    tag_id: int

    c: ClassVar[FieldProxy] = FieldProxy()

    @classmethod
    def table_name(cls) -> str:
        return "post_tags"


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
            "id",
            "INTEGER",
            constraints=[
                ColumnConstraint(ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)
            ]
        ),
        ColumnDefinition(
            "name",
            "VARCHAR(100)",
            constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]
        ),
        ColumnDefinition(
            "email",
            "VARCHAR(255)",
            constraints=[
                ColumnConstraint(ColumnConstraintType.NOT_NULL),
                ColumnConstraint(ColumnConstraintType.UNIQUE)
            ]
        )
    ]

    create_authors = CreateTableExpression(
        dialect=dialect,
        table_name="authors",
        columns=author_columns,
        if_not_exists=True
    )

    sql, params = create_authors.to_sql()
    print("=== Create Authors Table ===")
    print(f"SQL: {sql}")
    print()

    sql_str, params_str = create_authors.to_sql()
    backend.execute(sql_str, params_str)

    # ============================================================
    # Example 2: Create child table (Post) with foreign key
    # ============================================================
    post_columns = [
        ColumnDefinition(
            "id",
            "INTEGER",
            constraints=[
                ColumnConstraint(ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)
            ]
        ),
        ColumnDefinition(
            "title",
            "VARCHAR(200)",
            constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]
        ),
        ColumnDefinition("content", "TEXT"),
        ColumnDefinition(
            "author_id",
            "INTEGER",
            constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]
        )
    ]

    # Use table_constraints for foreign key at table level
    post_constraints = [
        ForeignKeyConstraint(
            constraint_type=TableConstraintType.FOREIGN_KEY,
            columns=["author_id"],
            foreign_key_table="authors",
            foreign_key_columns=["id"],
            on_delete=ReferentialAction.CASCADE,
            on_update=ReferentialAction.CASCADE
        )
    ]

    create_posts = CreateTableExpression(
        dialect=dialect,
        table_name="posts",
        columns=post_columns,
        table_constraints=post_constraints,
        if_not_exists=True
    )

    sql, params = create_posts.to_sql()
    print("=== Create Posts Table (with FK) ===")
    print(f"SQL: {sql}")
    print()

    sql_str, params_str = create_posts.to_sql()
    backend.execute(sql_str, params_str)

    # ============================================================
    # Example 3: Create Tag table
    # ============================================================
    tag_columns = [
        ColumnDefinition(
            "id",
            "INTEGER",
            constraints=[
                ColumnConstraint(ColumnConstraintType.PRIMARY_KEY, is_auto_increment=True)
            ]
        ),
        ColumnDefinition(
            "name",
            "VARCHAR(50)",
            constraints=[
                ColumnConstraint(ColumnConstraintType.NOT_NULL),
                ColumnConstraint(ColumnConstraintType.UNIQUE)
            ]
        )
    ]

    create_tags = CreateTableExpression(
        dialect=dialect,
        table_name="tags",
        columns=tag_columns,
        if_not_exists=True
    )

    sql, params = create_tags.to_sql()
    print("=== Create Tags Table ===")
    print(f"SQL: {sql}")
    print()

    sql_str, params_str = create_tags.to_sql()
    backend.execute(sql_str, params_str)

    # ============================================================
    # Example 4: Create junction table (PostTag) for many-to-many
    # ============================================================
    post_tag_columns = [
        ColumnDefinition(
            "post_id",
            "INTEGER",
            constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]
        ),
        ColumnDefinition(
            "tag_id",
            "INTEGER",
            constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]
        )
    ]

    # Table-level constraints for composite PK and foreign keys
    post_tag_constraints = [
        # Composite primary key
        TableConstraint(
            constraint_type=TableConstraintType.PRIMARY_KEY,
            columns=["post_id", "tag_id"]
        ),
        # Foreign key to posts table
        ForeignKeyConstraint(
            constraint_type=TableConstraintType.FOREIGN_KEY,
            columns=["post_id"],
            foreign_key_table="posts",
            foreign_key_columns=["id"],
            on_delete=ReferentialAction.CASCADE
        ),
        # Foreign key to tags table
        ForeignKeyConstraint(
            constraint_type=TableConstraintType.FOREIGN_KEY,
            columns=["tag_id"],
            foreign_key_table="tags",
            foreign_key_columns=["id"],
            on_delete=ReferentialAction.CASCADE
        )
    ]

    create_post_tags = CreateTableExpression(
        dialect=dialect,
        table_name="post_tags",
        columns=post_tag_columns,
        table_constraints=post_tag_constraints,
        if_not_exists=True
    )

    sql, params = create_post_tags.to_sql()
    print("=== Create PostTags Junction Table ===")
    print(f"SQL: {sql}")
    print()

    sql_str, params_str = create_post_tags.to_sql()
    backend.execute(sql_str, params_str)

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