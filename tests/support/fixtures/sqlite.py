# tests/support/sqlite_definitions.py
"""The schema the SQLite backend's introspection fixtures build.

The tables, indexes, foreign keys, the view and the trigger are expression
definitions: a definition class receives only a ``dialect`` and builds the DDL
it needs.  The two conftests that use this module (``feature/backend/sqlite``
and its ``introspection`` subdirectory) only execute the definitions.

The trigger body is a statement list (``UPDATE ... WHERE id = NEW.id``), and
``CreateTriggerStatement`` carries it as ``body`` expressions; the view is a
``CreateViewStatement`` over a query.  No SQL text is written or parsed here.
"""

from rhosocial.activerecord.backend.expression import (
    Column as ColumnRef,
    ColumnConstraint as Constraint,
    ColumnDefinition as Column,
    CreateTableStatement as CreateTable,
    DropTableStatement as DropTable,
    GroupByHavingClause,
    TableConstraint,
)
from rhosocial.activerecord.backend.expression.core import FunctionCall
from rhosocial.activerecord.backend.expression.datetime import CurrentTimestampFunction
from rhosocial.activerecord.backend.expression.objects import Index, Table, Trigger, View
from rhosocial.activerecord.backend.expression.predicates import ComparisonPredicate
from rhosocial.activerecord.backend.expression.query_parts import JoinClause, JoinType
from rhosocial.activerecord.backend.expression.sources.relation import NamedRelationRef
from rhosocial.activerecord.backend.expression.statements import (
    ColumnDefaultConstraint as Default,
    ColumnNotNullConstraint as NotNull,
    ColumnPrimaryKeyConstraint as PrimaryKey,
    ColumnUniqueConstraint as Unique,
    CreateIndexStatement as CreateIndex,
    CreateTriggerStatement,
    CreateViewStatement,
    QueryStatement,
    ReferentialAction,
    TableForeignKeyConstraint as ForeignKey,
    TablePrimaryKeyConstraint as TablePrimaryKey,
    TriggerEvent,
    TriggerTiming,
    UpdateStatement,
)
from rhosocial.activerecord.backend.expression.types import (
    IntegerType as Int,
    TextType as Text,
)


class Definition:
    """Base class for this schema's table definitions."""

    table_name = ""

    def __init__(self, dialect):
        self.dialect = dialect
        self.create_table = CreateTable(
            dialect,
            table=Table(dialect, self.table_name),
            columns=self.columns(),
            table_constraints=self.table_constraints(),
        )
        self.drop_table = DropTable(dialect, table=Table(dialect, self.table_name), if_exists=True)

    def columns(self):
        raise NotImplementedError

    def table_constraints(self):
        return []

    def column(self, name, sql_type, constraints=None):
        return Column(self.dialect, name, sql_type, constraints=constraints or [])

    def auto_pk(self, name="id"):
        return self.column(
            name,
            Int(self.dialect),
            [
                Constraint(
                    self.dialect,
                    branch=PrimaryKey(self.dialect, is_auto_increment=True),
                )
            ],
        )

    def not_null(self, name, sql_type):
        return self.column(
            name,
            sql_type,
            [Constraint(self.dialect, branch=NotNull(self.dialect))],
        )

    def unique_not_null(self, name, sql_type):
        return self.column(
            name,
            sql_type,
            [
                Constraint(self.dialect, branch=Unique(self.dialect)),
                Constraint(self.dialect, branch=NotNull(self.dialect)),
            ],
        )

    def current_timestamp(self, name, sql_type):
        return self.column(
            name,
            sql_type,
            [
                Constraint(
                    self.dialect,
                    branch=Default(self.dialect, CurrentTimestampFunction(self.dialect)),
                )
            ],
        )

    def foreign_key(
        self, columns, table_name, referenced_columns, *, on_delete=None, on_update=None
    ):
        return TableConstraint(
            self.dialect,
            branch=ForeignKey(
                self.dialect,
                columns,
                references=(Table(self.dialect, table_name), referenced_columns),
                on_delete=on_delete,
                on_update=on_update,
            ),
        )


class UsersDefinition(Definition):
    table_name = "users"

    def columns(self):
        return [
            self.auto_pk(),
            self.not_null("name", Text(self.dialect)),
            self.unique_not_null("email", Text(self.dialect)),
            self.column("age", Int(self.dialect)),
            self.current_timestamp("created_at", Text(self.dialect)),
        ]


class PostsDefinition(Definition):
    table_name = "posts"

    def columns(self):
        return [
            self.auto_pk(),
            self.not_null("user_id", Int(self.dialect)),
            self.not_null("title", Text(self.dialect)),
            self.column("content", Text(self.dialect)),
            self.column(
                "status",
                Text(self.dialect),
                [Constraint(self.dialect, branch=Default(self.dialect, "draft"))],
            ),
            self.current_timestamp("created_at", Text(self.dialect)),
        ]

    def table_constraints(self):
        return [
            self.foreign_key(
                ["user_id"],
                "users",
                ["id"],
                on_delete=ReferentialAction.CASCADE,
                on_update=ReferentialAction.NO_ACTION,
            )
        ]


class TagsDefinition(Definition):
    table_name = "tags"

    def columns(self):
        return [
            self.auto_pk(),
            self.unique_not_null("name", Text(self.dialect)),
        ]


class PostTagsDefinition(Definition):
    table_name = "post_tags"

    def columns(self):
        return [
            self.not_null("post_id", Int(self.dialect)),
            self.not_null("tag_id", Int(self.dialect)),
        ]

    def table_constraints(self):
        return [
            TableConstraint(
                self.dialect,
                branch=TablePrimaryKey(self.dialect, ["post_id", "tag_id"]),
            ),
            self.foreign_key(["post_id"], "posts", ["id"], on_delete=ReferentialAction.CASCADE),
            self.foreign_key(["tag_id"], "tags", ["id"], on_delete=ReferentialAction.CASCADE),
        ]


#: The tables the introspection fixtures create, in dependency order.
TABLE_DEFINITIONS = (
    UsersDefinition,
    PostsDefinition,
    TagsDefinition,
    PostTagsDefinition,
)


class IndexesDefinition:
    """The four standalone indexes the original schema declared."""

    def __init__(self, dialect):
        self.dialect = dialect
        table_users = Table(dialect, "users")
        table_posts = Table(dialect, "posts")
        self.create_statements = [
            CreateIndex(
                dialect,
                index=Index(dialect, "idx_users_email"),
                table=table_users,
                columns=["email"],
            ),
            CreateIndex(
                dialect,
                index=Index(dialect, "idx_users_name_age"),
                table=table_users,
                columns=["name", "age"],
            ),
            CreateIndex(
                dialect,
                index=Index(dialect, "idx_posts_user_id"),
                table=table_posts,
                columns=["user_id"],
            ),
            CreateIndex(
                dialect,
                index=Index(dialect, "idx_posts_status"),
                table=table_posts,
                columns=["status"],
            ),
        ]


class TriggerDefinition:
    """The ``AFTER UPDATE`` trigger, expressed as a statement body.

    SQLite's trigger body is a statement list rather than a function call, so
    the body is an expression: ``UPDATE users SET created_at = CURRENT_TIMESTAMP
    WHERE id = NEW.id``.
    """

    def __init__(self, dialect):
        self.dialect = dialect
        self.create_trigger = CreateTriggerStatement(
            dialect,
            trigger=Trigger(dialect, "update_user_timestamp"),
            table=Table(dialect, "users"),
            timing=TriggerTiming.AFTER,
            events=[TriggerEvent.UPDATE],
            body=[
                UpdateStatement(
                    dialect,
                    table=Table(dialect, "users"),
                    assignments={"created_at": CurrentTimestampFunction(dialect)},
                    where=ComparisonPredicate(
                        dialect,
                        "=",
                        ColumnRef(dialect, "id"),
                        ColumnRef(
                            dialect,
                            "id",
                            table="NEW",
                            table_need_quote=False,
                            name_need_quote=False,
                        ),
                    ),
                )
            ],
        )


class ViewDefinition:
    """The ``user_posts_summary`` view, expressed as a query.

    ``SELECT u.id AS user_id, u.name AS user_name, COUNT(p.id) AS post_count
    FROM users u LEFT JOIN posts p ON u.id = p.user_id GROUP BY u.id``.
    """

    def __init__(self, dialect):
        self.dialect = dialect
        users = NamedRelationRef(dialect, Table(dialect, "users"), alias="u")
        posts = NamedRelationRef(dialect, Table(dialect, "posts"), alias="p")
        join = JoinClause(
            dialect,
            left_table=users,
            right_table=posts,
            join_type=JoinType.LEFT,
            condition=ComparisonPredicate(
                dialect,
                "=",
                ColumnRef(dialect, "id", table="u"),
                ColumnRef(dialect, "user_id", table="p"),
            ),
        )
        query = QueryStatement(
            dialect,
            select=[
                ColumnRef(dialect, "id", table="u").as_("user_id"),
                ColumnRef(dialect, "name", table="u").as_("user_name"),
                FunctionCall(dialect, "COUNT", ColumnRef(dialect, "id", table="p")).as_(
                    "post_count"
                ),
            ],
            from_=join,
            group_by_having=GroupByHavingClause(
                dialect, group_by=[ColumnRef(dialect, "id", table="u")]
            ),
        )
        self.create_view = CreateViewStatement(
            dialect,
            view=View(dialect, "user_posts_summary"),
            query=query,
        )


#: The trigger and the view the introspection fixtures add on top of the tables.
TRIGGER_DEFINITION = TriggerDefinition
VIEW_DEFINITION = ViewDefinition
