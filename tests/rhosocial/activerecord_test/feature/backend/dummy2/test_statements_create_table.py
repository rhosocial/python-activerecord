# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_statements_create_table.py
import inspect

import pytest
from rhosocial.activerecord.backend.expression.statements import (
    ColumnCheckConstraint,
    ColumnDefaultConstraint,
    ColumnForeignKeyConstraint,
    ColumnNotNullConstraint,
    ColumnNullableConstraint,
    ColumnPrimaryKeyConstraint,
    ColumnUniqueConstraint,
    TablePrimaryKeyConstraint,
    TableUniqueConstraint,
)
from rhosocial.activerecord.backend.expression.statements import (
    ColumnDefinition,
    ColumnConstraint,
    CreateTableStatement,
    TableConstraint,
)
from rhosocial.activerecord.backend.expression.types import CustomType
from rhosocial.activerecord.backend.expression.types import DateType, DecimalType, IntegerType, SmallIntType, TextType, TimestampType, VarCharType
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect
from rhosocial.activerecord.backend.dialect.mixins import (
    PartitionMixin,
    DDLColumnMixin,
    TableNameMixin,
    NamespaceMixin,
    TableMixin,
    ExpressionMixin,
    DataTypeMixin,
)
from rhosocial.activerecord.backend.expression.sources import NamedRelationRef
from rhosocial.activerecord.backend.expression.query_parts import WhereClause
from rhosocial.activerecord.backend.expression.objects import Table
from rhosocial.activerecord.backend.dialect import protocols as dialect_protocols
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.dialect import SQLDialectBase
from typing import Set, Tuple
from rhosocial.activerecord.backend.expression import (
    Literal,
    Column,
    ComparisonPredicate,
    FunctionCall,
    CreateTableStatement,
    CreateTableAsStatement,
    CreateTableLikeStatement,
    CreateTableCloneStatement,
    CreateTableFromTemplateStatement,
    CreateTableCloneMode,
    CreateTableOptions,
    ColumnDefinition,
    ColumnCommentClause,
    TableCommentClause,
    IndexDefinition,
)
from rhosocial.activerecord.backend.expression.statements import (
    TableConstraint,
    ReferentialAction,
    ForeignKeyConstraint,
    ColumnConstraint,
    PartitionClause,
    PartitionStrategy,
    QueryStatement,
    StorageOptionsExpression,
)


class PartitionTestDialect(
    SQLDialectBase,
    ExpressionMixin,
    DDLColumnMixin,
    DataTypeMixin,
    PartitionMixin,
    TableNameMixin,
    NamespaceMixin,
    TableMixin,
):
    """Minimal dialect for core PartitionClause success-path tests."""

    def supports_table_partitioning(self) -> bool:
        return True

    def supports_partitioned_table_creation(self) -> bool:
        return True

    def supports_range_table_partitioning(self) -> bool:
        return True

    def supports_hash_table_partitioning(self) -> bool:
        return True

    def format_partition_clause(self, expr: PartitionClause) -> Tuple[str, tuple]:
        self.check_feature_support(
            "supports_partitioned_table_creation",
            "PARTITION BY clause",
            "Use a dialect that supports partitioned table creation.",
        )
        method_checks = {
            "RANGE": "supports_range_table_partitioning",
            "HASH": "supports_hash_table_partitioning",
        }
        check_method = method_checks.get(expr.method)
        if check_method is None:
            raise ValueError("Unsupported test partition method")
        self.check_feature_support(check_method, f"{expr.method} partitioning")

        parts = []
        params = []
        for key in expr.keys:
            key_sql, key_params = key.to_sql()
            parts.append(key_sql)
            params.extend(key_params)
        return f" PARTITION BY {expr.method} ({', '.join(parts)})", tuple(params)

    def format_data_type_integer(self, data_type: IntegerType) -> Tuple[str, tuple]:
        return "INTEGER", ()

    def format_data_type_text(self, data_type: TextType) -> Tuple[str, tuple]:
        return "TEXT", ()

    def format_data_type_varchar(self, data_type: VarCharType) -> Tuple[str, tuple]:
        return (f"VARCHAR({data_type.length})" if data_type.length is not None else "VARCHAR"), ()

    def format_data_type_smallint(self, data_type: SmallIntType) -> Tuple[str, tuple]:
        return "SMALLINT", ()

    def format_data_type_decimal(self, data_type: DecimalType) -> Tuple[str, tuple]:
        if data_type.precision is not None and data_type.scale is not None:
            return f"DECIMAL({data_type.precision},{data_type.scale})", ()
        if data_type.precision is not None:
            return f"DECIMAL({data_type.precision})", ()
        return "DECIMAL", ()

    def format_data_type_date(self, data_type: DateType) -> Tuple[str, tuple]:
        return "DATE", ()

    def format_data_type_timestamp(self, data_type: TimestampType) -> Tuple[str, tuple]:
        return (f"TIMESTAMP({data_type.precision})" if data_type.precision is not None else "TIMESTAMP"), ()

    def format_data_type_custom(self, data_type: CustomType) -> Tuple[str, tuple]:
        return data_type.raw, ()


def _get_protocol_methods(protocol: type) -> Set[str]:
    """Extract public methods declared by a protocol."""
    return {
        name
        for name, value in protocol.__dict__.items()
        if not name.startswith("_") and callable(value)
    }


class TestPartitionProtocolConformance:
    """Tests generic PartitionSupport and PartitionMixin stay aligned."""

    def test_partition_mixin_satisfies_partition_support_protocol(self):
        """PartitionMixin should structurally implement PartitionSupport."""
        assert isinstance(PartitionMixin(), dialect_protocols.PartitionSupport)

    def test_partition_protocol_methods_are_implemented_by_mixin(self):
        """Every PartitionSupport method should exist on PartitionMixin."""
        protocol_methods = _get_protocol_methods(dialect_protocols.PartitionSupport)
        mixin_methods = {name for name in dir(PartitionMixin) if not name.startswith("_")}

        assert protocol_methods - mixin_methods == set()

    def test_partition_mixin_public_methods_are_declared_in_protocol(self):
        """PartitionMixin public formatter/capability methods must be declared."""
        protocol_methods = _get_protocol_methods(dialect_protocols.PartitionSupport)
        mixin_methods = {
            name
            for name, value in PartitionMixin.__dict__.items()
            if name.startswith(("format_", "supports_", "get_")) and callable(value)
        }

        assert mixin_methods - protocol_methods == set()

    @pytest.mark.parametrize("method_name", sorted(_get_protocol_methods(dialect_protocols.PartitionSupport)))
    def test_partition_mixin_signatures_match_protocol(self, method_name: str):
        """PartitionMixin method signatures should match PartitionSupport."""
        protocol_signature = inspect.signature(getattr(dialect_protocols.PartitionSupport, method_name))
        mixin_signature = inspect.signature(getattr(PartitionMixin, method_name))

        assert list(mixin_signature.parameters) == list(protocol_signature.parameters)
        assert mixin_signature.return_annotation == protocol_signature.return_annotation


class TestCreateTableStatements:
    """Tests for CreateTableStatement with various configurations and options."""

    def test_basic_create_table(self, dummy_dialect: DummyDialect):
        """Tests a basic CREATE TABLE statement."""
        columns = [
            ColumnDefinition(dummy_dialect, 
                "id",
                IntegerType(dummy_dialect),
                constraints=[
                    ColumnConstraint(dummy_dialect, branch=ColumnPrimaryKeyConstraint(dummy_dialect)),
                    ColumnConstraint(dummy_dialect, branch=ColumnNotNullConstraint(dummy_dialect)),
                ],
            ),
            ColumnDefinition(dummy_dialect, "name", VarCharType(dummy_dialect, 255), constraints=[ColumnConstraint(dummy_dialect, branch=ColumnNotNullConstraint(dummy_dialect))]),
            ColumnDefinition(dummy_dialect, "email", TextType(dummy_dialect)),
        ]

        create_table_expr = CreateTableStatement(dummy_dialect, table=Table(dummy_dialect, 'users'), columns=columns)
        sql, params = create_table_expr.to_sql()

        assert sql.startswith('CREATE TABLE "users"')
        assert '"id" INTEGER PRIMARY KEY NOT NULL' in sql
        assert '"name" VARCHAR(255) NOT NULL' in sql
        assert '"email" TEXT' in sql
        assert params == ()

    def test_create_table_with_if_not_exists(self, dummy_dialect: DummyDialect):
        """Tests CREATE TABLE with IF NOT EXISTS flag."""
        columns = [ColumnDefinition(dummy_dialect, "id", IntegerType(dummy_dialect), constraints=[ColumnConstraint(dummy_dialect, branch=ColumnPrimaryKeyConstraint(dummy_dialect))])]

        create_table_expr = CreateTableStatement(dummy_dialect, table=Table(dummy_dialect, 'products'), columns=columns, if_not_exists=True)
        sql, params = create_table_expr.to_sql()

        assert "CREATE TABLE IF NOT EXISTS" in sql
        assert '"products"' in sql
        assert params == ()

    def test_create_temporary_table(self, dummy_dialect: DummyDialect):
        """Tests CREATE TEMPORARY TABLE statement."""
        columns = [
            ColumnDefinition(dummy_dialect, 
                "session_id", VarCharType(dummy_dialect, 50), constraints=[ColumnConstraint(dummy_dialect, branch=ColumnNotNullConstraint(dummy_dialect))]
            ),
            ColumnDefinition(dummy_dialect, "data", TextType(dummy_dialect)),
        ]

        create_table_expr = CreateTableStatement(dummy_dialect, table=Table(dummy_dialect, 'temp_sessions'), columns=columns, temporary=True)
        sql, params = create_table_expr.to_sql()

        assert "CREATE TEMPORARY TABLE" in sql
        assert '"temp_sessions"' in sql
        assert params == ()

    def test_create_table_with_unique_constraint(self, dummy_dialect: DummyDialect):
        """Tests CREATE TABLE with UNIQUE column constraint."""
        columns = [
            ColumnDefinition(dummy_dialect, "id", IntegerType(dummy_dialect), constraints=[ColumnConstraint(dummy_dialect, branch=ColumnPrimaryKeyConstraint(dummy_dialect))]),
            ColumnDefinition(dummy_dialect, "username", VarCharType(dummy_dialect, 50), constraints=[ColumnConstraint(dummy_dialect, branch=ColumnUniqueConstraint(dummy_dialect))]),
            ColumnDefinition(dummy_dialect, "email", VarCharType(dummy_dialect, 100), constraints=[ColumnConstraint(dummy_dialect, branch=ColumnUniqueConstraint(dummy_dialect))]),
        ]

        create_table_expr = CreateTableStatement(dummy_dialect, table=Table(dummy_dialect, 'users'), columns=columns)
        sql, params = create_table_expr.to_sql()

        assert '"username" VARCHAR(50) UNIQUE' in sql
        assert '"email" VARCHAR(100) UNIQUE' in sql
        assert params == ()

    def test_create_table_with_default_constraint(self, dummy_dialect: DummyDialect):
        """Tests CREATE TABLE with DEFAULT column constraints."""
        columns = [
            ColumnDefinition(dummy_dialect, "id", IntegerType(dummy_dialect), constraints=[ColumnConstraint(dummy_dialect, branch=ColumnPrimaryKeyConstraint(dummy_dialect))]),
            ColumnDefinition(dummy_dialect, "name", VarCharType(dummy_dialect, 100)),
            ColumnDefinition(dummy_dialect,
                "status",
                VarCharType(dummy_dialect, 20),
                constraints=[ColumnConstraint(dummy_dialect, branch=ColumnDefaultConstraint(dummy_dialect, "active"))],
            ),
            ColumnDefinition(dummy_dialect, 
                "created_at",
                TimestampType(dummy_dialect),
                constraints=[
                    ColumnConstraint(dummy_dialect, branch=ColumnDefaultConstraint(dummy_dialect, FunctionCall(dummy_dialect, "NOW")))
                ],
            ),
        ]

        create_table_expr = CreateTableStatement(dummy_dialect, table=Table(dummy_dialect, 'users'), columns=columns)
        sql, params = create_table_expr.to_sql()

        # DDL clauses accept no bind parameters: DEFAULT literal values are
        # rendered inline.
        assert '"status" VARCHAR(20) DEFAULT \'active\'' in sql
        assert '"created_at" TIMESTAMP DEFAULT NOW()' in sql
        assert params == ()

    def test_create_table_with_check_constraint(self, dummy_dialect: DummyDialect):
        """Tests CREATE TABLE with CHECK column constraints."""
        # Create a check predicate for age > 0 (inline literal for DDL)
        age_check = ComparisonPredicate(
            dummy_dialect, ">", Column(dummy_dialect, "age"), Literal(dummy_dialect, 0)
        )

        columns = [
            ColumnDefinition(dummy_dialect, "id", IntegerType(dummy_dialect), constraints=[ColumnConstraint(dummy_dialect, branch=ColumnPrimaryKeyConstraint(dummy_dialect))]),
            ColumnDefinition(dummy_dialect, "name", VarCharType(dummy_dialect, 100)),
            ColumnDefinition(dummy_dialect, 
                "age", IntegerType(dummy_dialect), constraints=[ColumnConstraint(dummy_dialect, branch=ColumnCheckConstraint(dummy_dialect, age_check))]
            ),
        ]

        create_table_expr = CreateTableStatement(dummy_dialect, table=Table(dummy_dialect, 'people'), columns=columns)
        sql, params = create_table_expr.to_sql()

        assert '"age" INTEGER CHECK ("age" > 0)' in sql
        assert params == ()

    def test_create_table_with_foreign_key_constraint(self, dummy_dialect: DummyDialect):
        """Tests CREATE TABLE with FOREIGN KEY column constraints."""
        columns = [
            ColumnDefinition(dummy_dialect, "id", IntegerType(dummy_dialect), constraints=[ColumnConstraint(dummy_dialect, branch=ColumnPrimaryKeyConstraint(dummy_dialect))]),
            ColumnDefinition(dummy_dialect, 
                "user_id",
                IntegerType(dummy_dialect),
                constraints=[
                    ColumnConstraint(dummy_dialect, branch=ColumnForeignKeyConstraint(dummy_dialect, (Table(dummy_dialect, "users"), ["id"])))
                ],
            ),
            ColumnDefinition(dummy_dialect, "product_name", VarCharType(dummy_dialect, 100)),
        ]

        create_table_expr = CreateTableStatement(dummy_dialect, table=Table(dummy_dialect, 'orders'), columns=columns)
        sql, params = create_table_expr.to_sql()

        assert '"user_id" INTEGER REFERENCES "users"("id")' in sql
        assert params == ()

    def test_column_definition_identity_via_attribute(self, dummy_dialect: DummyDialect):
        """Identity is declared through the column-attribute channel (§5.3)."""
        from rhosocial.activerecord.base import IdentityAttribute

        col = ColumnDefinition(dummy_dialect, "id", IntegerType(dummy_dialect))
        col.attributes = [IdentityAttribute(generation="BY DEFAULT", start=1, increment=1)]
        sql, _ = col.to_sql()
        assert "GENERATED BY DEFAULT AS IDENTITY" in sql
        assert "START WITH 1" in sql
        assert "INCREMENT BY 1" in sql

    def test_create_table_with_table_level_constraints(self, dummy_dialect: DummyDialect):
        """Tests CREATE TABLE with table-level constraints."""
        columns = [
            ColumnDefinition(dummy_dialect, "id", IntegerType(dummy_dialect)),
            ColumnDefinition(dummy_dialect, "name", VarCharType(dummy_dialect, 100)),
            ColumnDefinition(dummy_dialect, "category_id", IntegerType(dummy_dialect)),
        ]

        table_constraints = [
            TableConstraint(dummy_dialect, branch=TablePrimaryKeyConstraint(dummy_dialect, ["id"])),
            TableConstraint(dummy_dialect, branch=TableUniqueConstraint(dummy_dialect, ["name"])),
            ForeignKeyConstraint(dummy_dialect, 
                foreign_key_table=Table(dummy_dialect, "categories"),
                foreign_key_columns=["id"],
                columns=["category_id"],
                on_delete=ReferentialAction.CASCADE,
            ),
        ]

        create_table_expr = CreateTableStatement(
            dummy_dialect, table=Table(dummy_dialect, 'products'), columns=columns, table_constraints=table_constraints
        )
        sql, params = create_table_expr.to_sql()

        assert 'PRIMARY KEY ("id")' in sql
        assert 'UNIQUE ("name")' in sql
        assert 'FOREIGN KEY ("category_id") REFERENCES "categories"("id")' in sql
        assert params == ()

    def test_create_table_with_storage_options(self, dummy_dialect: DummyDialect):
        """Tests CREATE TABLE with storage options."""
        columns = [
            ColumnDefinition(dummy_dialect, "id", IntegerType(dummy_dialect), constraints=[ColumnConstraint(dummy_dialect, branch=ColumnPrimaryKeyConstraint(dummy_dialect))]),
            ColumnDefinition(dummy_dialect, "data", TextType(dummy_dialect)),
        ]

        storage_opts = StorageOptionsExpression(
            dummy_dialect, {"engine": "InnoDB", "charset": "utf8mb4", "page_size": 8192}
        )

        create_table_expr = CreateTableStatement(
            dummy_dialect, table=Table(dummy_dialect, 'documents'), columns=columns, storage_options=storage_opts
        )
        sql, params = create_table_expr.to_sql()

        assert "WITH" in sql
        assert '"engine" =' in sql
        assert '"charset" =' in sql
        assert '"page_size" =' in sql
        assert "'InnoDB'" in sql
        assert "'utf8mb4'" in sql
        assert "8192" in sql
        assert params == ()

    def test_create_table_with_tablespace(self, dummy_dialect: DummyDialect):
        """Tests CREATE TABLE with tablespace specification."""
        columns = [
            ColumnDefinition(dummy_dialect, "id", IntegerType(dummy_dialect), constraints=[ColumnConstraint(dummy_dialect, branch=ColumnPrimaryKeyConstraint(dummy_dialect))]),
            ColumnDefinition(dummy_dialect, "name", VarCharType(dummy_dialect, 100)),
        ]

        create_table_expr = CreateTableStatement(
            dummy_dialect, table=Table(dummy_dialect, 'large_table'), columns=columns, tablespace="fast_ssd"
        )
        sql, params = create_table_expr.to_sql()

        assert '"large_table"' in sql
        assert "TABLESPACE" in sql
        assert '"fast_ssd"' in sql
        assert params == ()

    def test_create_table_as_query_result(self, dummy_dialect: DummyDialect):
        """Tests CREATE TABLE AS with a query result (CTAS)."""
        where_clause = WhereClause(
            dummy_dialect,
            condition=ComparisonPredicate(
                dummy_dialect, "=", Column(dummy_dialect, "status"), Literal(dummy_dialect, "active")
            )
        )
        query = QueryStatement(
            dummy_dialect,
            select=[Column(dummy_dialect, "id"), Column(dummy_dialect, "name")],
            from_=NamedRelationRef(dummy_dialect, Table(dummy_dialect, "users")),
            where=where_clause,
        )

        create_table_expr = CreateTableAsStatement(
            dummy_dialect, table=Table(dummy_dialect, "active_users"), as_query=query
        )
        sql, params = create_table_expr.to_sql()

        # Query is rendered without parentheses (portable form).
        assert "AS SELECT" in sql
        assert "AS (" not in sql
        assert 'SELECT "id", "name" FROM "users"' in sql
        assert 'WHERE "status" = ?' in sql
        assert params == ("active",)

    def test_create_table_as_with_no_data(self, dummy_dialect: DummyDialect):
        """Tests CREATE TABLE AS ... WITH NO DATA."""
        query = QueryStatement(
            dummy_dialect,
            select=[Literal(dummy_dialect, 1)],
        )
        expr = CreateTableAsStatement(dummy_dialect, table=Table(dummy_dialect, "t"), as_query=query, no_data=True)
        sql, params = expr.to_sql()
        assert sql.endswith("WITH NO DATA")
        assert params == (1,)

    def test_create_table_like_generic_render(self, dummy_dialect: DummyDialect):
        """Dummy advertises LIKE, so the generic reusable renderer is exercised."""
        expr = CreateTableLikeStatement(
            dummy_dialect,
            table=Table(dummy_dialect, "copy"),
            like_table=Table(dummy_dialect, "users"),
        )
        sql, params = expr.to_sql()
        assert sql.startswith("CREATE TABLE")
        assert "LIKE" in sql
        assert "users" in sql
        assert params == ()

    def test_create_table_like_unsupported_raises(self):
        """A dialect with supports_create_table_like False fails fast."""
        from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect

        dialect = SQLiteDialect()
        assert dialect.supports_create_table_like() is False
        expr = CreateTableLikeStatement(dialect, table=Table(dialect, "copy"), like_table=Table(dialect, "users"))
        with pytest.raises(UnsupportedFeatureError):
            expr.to_sql()

    def test_create_table_like_carries_namespace(self, dummy_dialect: DummyDialect):
        """The Table object reaches the statement intact, namespace included."""
        expr = CreateTableLikeStatement(
            dummy_dialect,
            table=Table(dummy_dialect, "copy"),
            like_table=Table(dummy_dialect, "users", schema_name="sales"),
        )
        assert expr.table_name == "copy"
        assert expr.like_table.schema_name == "sales"
        assert expr.like_table.name == "users"

    def test_create_table_like_rejects_bare_string(self, dummy_dialect: DummyDialect):
        """A bare name is refused instead of guessed at.

        The class used to accept a str, a NamedRelationRef or a (schema, table)
        tuple and normalise between them. That polymorphism is what made the
        statement's real target unknowable at the call site; naming the object
        removes the guessing, and a str is no longer one of the accepted forms.

        The refusal comes from the formatter that renders ``LIKE <source>``,
        before it checks whether the dialect supports the form at all -- a str
        named in place of a table is wrong regardless of the dialect.
        """
        expr = CreateTableLikeStatement(
            dummy_dialect, table=Table(dummy_dialect, "copy"), like_table="users"
        )
        with pytest.raises(TypeError, match=r"like_table must be a Table, got str"):
            expr.to_sql()

    def test_create_table_clone_generic_render(self, dummy_dialect: DummyDialect):
        expr = CreateTableCloneStatement(
            dummy_dialect,
            table=Table(dummy_dialect, "clone_t"),
            source_table=Table(dummy_dialect, "src"),
            copy_grants=True,
        )
        sql, params = expr.to_sql()
        assert "CLONE" in sql
        assert "COPY GRANTS" in sql
        assert params == ()

    def test_create_table_clone_unsupported_raises(self):
        from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect

        dialect = SQLiteDialect()
        assert dialect.supports_create_table_clone() is False
        expr = CreateTableCloneStatement(dialect, table=Table(dialect, "clone_t"), source_table=Table(dialect, "src"))
        with pytest.raises(UnsupportedFeatureError):
            expr.to_sql()

    def test_create_table_clone_mode_selects_copy(self, dummy_dialect: DummyDialect):
        expr = CreateTableCloneStatement(
            dummy_dialect,
            table=Table(dummy_dialect, "copy_t"),
            source_table=Table(dummy_dialect, "src"),
            mode=CreateTableCloneMode.COPY,
        )
        sql, _ = expr.to_sql()
        assert "COPY" in sql
        assert "CLONE" not in sql

    def test_create_table_from_template_generic_render(self, dummy_dialect: DummyDialect):
        query = QueryStatement(dummy_dialect, select=[Literal(dummy_dialect, 1)])
        expr = CreateTableFromTemplateStatement(dummy_dialect, table=Table(dummy_dialect, "t"), template=query)
        sql, params = expr.to_sql()
        assert "USING TEMPLATE" in sql
        assert params == (1,)

    def test_create_table_from_template_unsupported_raises(self):
        from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect

        dialect = SQLiteDialect()
        assert dialect.supports_create_table_using_template() is False
        query = QueryStatement(dialect, select=[Literal(dialect, 1)])
        expr = CreateTableFromTemplateStatement(dialect, table=Table(dialect, "t"), template=query)
        with pytest.raises(UnsupportedFeatureError):
            expr.to_sql()

    def test_create_table_clone_mode_requires_type(self, dummy_dialect: DummyDialect):
        with pytest.raises(TypeError):
            CreateTableCloneStatement(
                dummy_dialect, table=Table(dummy_dialect, "t"), source_table=Table(dummy_dialect, "src"), mode="CLONE"
            )

    def test_create_table_options_or_replace(self, dummy_dialect: DummyDialect):
        expr = CreateTableStatement(
            dummy_dialect,
            table=Table(dummy_dialect, 't'),
            columns=[],
            table_options=CreateTableOptions(dummy_dialect, or_replace=True),
        )
        sql, _ = expr.to_sql()
        assert sql.startswith("CREATE OR REPLACE TABLE")

    def test_create_table_options_has_no_backend_fields(self, dummy_dialect: DummyDialect):
        """The generic options carry only or_replace/comment (no bag)."""
        opts = CreateTableOptions(dummy_dialect, or_replace=True, comment=TableCommentClause(dummy_dialect, "c"))
        for name in ("unlogged", "transient", "engine", "charset", "collate",
                     "memory_optimized", "durability", "dialect_options"):
            assert not hasattr(opts, name), name

    def test_create_table_options_comment(self, dummy_dialect: DummyDialect):
        opts = CreateTableOptions(dummy_dialect, comment=TableCommentClause(dummy_dialect, "my table comment"))
        assert opts.comment.comment == "my table comment"
        sql, _ = opts.to_sql()
        assert sql == ""

    def test_format_table_comment(self, dummy_dialect: DummyDialect):
        sql, params = dummy_dialect.format_table_comment("hello world")
        assert sql == "COMMENT 'hello world'"
        assert params == ()

    def test_format_table_comment_escapes_quotes(self, dummy_dialect: DummyDialect):
        sql, _ = dummy_dialect.format_table_comment("it's a test")
        assert "''" in sql

    def test_create_table_options_gated(self):
        """A dialect without the capability flag fails fast."""
        from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect

        dialect = SQLiteDialect()
        assert dialect.supports_create_or_replace_table() is False
        expr = CreateTableStatement(
            dialect,
            table=Table(dialect, 't'),
            columns=[],
            table_options=CreateTableOptions(dialect, or_replace=True),
        )
        with pytest.raises(UnsupportedFeatureError):
            expr.to_sql()

    def test_create_table_with_indexes(self, dummy_dialect: DummyDialect):
        """Tests CREATE TABLE with indexes."""
        columns = [
            ColumnDefinition(dummy_dialect, "id", IntegerType(dummy_dialect), constraints=[ColumnConstraint(dummy_dialect, branch=ColumnPrimaryKeyConstraint(dummy_dialect))]),
            ColumnDefinition(dummy_dialect, "email", VarCharType(dummy_dialect, 100)),
            ColumnDefinition(dummy_dialect, "created_at", TimestampType(dummy_dialect)),
        ]

        indexes = [
            IndexDefinition(dummy_dialect, "idx_users_email", ["email"], unique=True),
            IndexDefinition(dummy_dialect, "idx_users_created", ["created_at"], unique=False),
        ]

        create_table_expr = CreateTableStatement(dummy_dialect, table=Table(dummy_dialect, 'users'), columns=columns, indexes=indexes)

        # Inline indexes are a dialect convenience (MySQL/MariaDB/ClickHouse);
        # the SQL-standard behavior is a standalone CREATE INDEX, so the generic
        # renderer rejects inline indexes instead of silently dropping them.
        with pytest.raises(UnsupportedFeatureError):
            create_table_expr.to_sql()

    def test_create_table_with_nullable_setting(self, dummy_dialect: DummyDialect):
        """Tests CREATE TABLE with nullable settings."""
        columns = [
            ColumnDefinition(dummy_dialect, "id", IntegerType(dummy_dialect), constraints=[ColumnConstraint(dummy_dialect, branch=ColumnPrimaryKeyConstraint(dummy_dialect))]),
            ColumnDefinition(dummy_dialect, 
                "name", VarCharType(dummy_dialect, 100), constraints=[ColumnConstraint(dummy_dialect, branch=ColumnNotNullConstraint(dummy_dialect))]
            ),  # Explicitly NOT NULL using constraint
            ColumnDefinition(dummy_dialect, 
                "description", TextType(dummy_dialect), constraints=[ColumnConstraint(dummy_dialect, branch=ColumnNullableConstraint(dummy_dialect))]
            ),  # Explicitly allow NULLs using constraint
            ColumnDefinition(dummy_dialect, "age", IntegerType(dummy_dialect)),  # No constraints - uses database default
        ]

        create_table_expr = CreateTableStatement(dummy_dialect, table=Table(dummy_dialect, 'profiles'), columns=columns)
        sql, params = create_table_expr.to_sql()

        assert '"profiles"' in sql
        assert "NOT NULL" in sql  # Should have NOT NULL from NOT_NULL constraint
        assert " NULL" in sql  # Should have explicit NULL from NULL constraint
        assert params == ()

    def test_create_table_with_comment(self, dummy_dialect: DummyDialect):
        """Tests CREATE TABLE with column comments."""
        columns = [
            ColumnDefinition(dummy_dialect, 
                "id",
                IntegerType(dummy_dialect),
                constraints=[ColumnConstraint(dummy_dialect, branch=ColumnPrimaryKeyConstraint(dummy_dialect))],
                comment=ColumnCommentClause(dummy_dialect, "Primary identifier"),
            ),
            ColumnDefinition(dummy_dialect, "name", VarCharType(dummy_dialect, 100), comment=ColumnCommentClause(dummy_dialect, "User's display name")),
        ]

        create_table_expr = CreateTableStatement(dummy_dialect, table=Table(dummy_dialect, 'users_with_comments'), columns=columns)
        sql, params = create_table_expr.to_sql()

        assert '"users_with_comments"' in sql
        assert "COMMENT 'Primary identifier'" in sql
        assert "COMMENT 'User''s display name'" in sql
        assert params == ()

    def test_create_table_partition_unsupported_by_dummy(self, dummy_dialect: DummyDialect):
        """Tests DummyDialect intentionally does not support table partitioning."""
        columns = [
            ColumnDefinition(dummy_dialect, "id", IntegerType(dummy_dialect)),
            ColumnDefinition(dummy_dialect, "created_date", DateType(dummy_dialect)),
        ]

        create_table_expr = CreateTableStatement(
            dummy_dialect,
            table=Table(dummy_dialect, 'log_entries'),
            columns=columns,
            partition=PartitionClause(
                dialect=dummy_dialect,
                method=PartitionStrategy.RANGE,
                keys=[Column(dummy_dialect, "created_date")],
            ),
        )

        with pytest.raises(UnsupportedFeatureError, match="PARTITION BY clause"):
            create_table_expr.to_sql()

    def test_create_table_partition_success_path_uses_partition_protocol(self):
        """Tests CreateTableStatement appends PartitionClause SQL and params."""
        dialect = PartitionTestDialect()
        partition = PartitionClause(
            dialect=dialect,
            method=PartitionStrategy.HASH,
            keys=[FunctionCall(dialect, "bucket", Literal(dialect, "tenant"))],
        )
        create_table_expr = CreateTableStatement(
            dialect,
            table=Table(dialect, 'events'),
            columns=[ColumnDefinition(dialect, "tenant", TextType(dialect))],
            partition=partition,
        )

        sql, params = create_table_expr.to_sql()

        assert sql == 'CREATE TABLE "events" ("tenant" TEXT) PARTITION BY HASH (BUCKET(?))'
        assert params == ("tenant",)

    def test_partition_clause_delegates_to_partition_support(self):
        """Tests PartitionClause delegates to dialect.format_partition_clause()."""
        dialect = PartitionTestDialect()
        partition = PartitionClause(dialect=dialect, method=PartitionStrategy.RANGE, keys=[Column(dialect, "created_at")])

        sql, params = partition.to_sql()

        assert sql == ' PARTITION BY RANGE ("created_at")'
        assert params == ()

    def test_create_table_partition_requires_partition_clause(self, dummy_dialect: DummyDialect):
        """Tests partition parameter must be a PartitionClause instance."""
        columns = [ColumnDefinition(dummy_dialect, "id", IntegerType(dummy_dialect))]

        with pytest.raises(TypeError, match="partition must be a PartitionClause"):
            CreateTableStatement(
                dummy_dialect,
                table=Table(dummy_dialect, 'invalid_partition'),
                columns=columns,
                partition="RANGE",
            )

    def test_partition_clause_requires_strategy_enum(self, dummy_dialect: DummyDialect):
        """Tests PartitionClause rejects non-enum method values.

        PartitionClause accepts both the PartitionStrategy enum and its string
        value (so deserialization round-trips), but arbitrary strings are
        rejected.
        """
        with pytest.raises(TypeError, match="method must be a"):
            PartitionClause(
                dialect=dummy_dialect,
                method="NOT_A_STRATEGY",
                keys=[Column(dummy_dialect, "created_date")],
            )

    def test_partition_clause_accepts_enum_string_value(self, dummy_dialect: DummyDialect):
        """Tests PartitionClause accepts the string form of a strategy value."""
        expr = PartitionClause(
            dialect=dummy_dialect,
            method="RANGE",
            keys=[Column(dummy_dialect, "created_date")],
        )
        assert expr.method == "RANGE"

    def test_partition_clause_rejects_malicious_method_without_logging_value(self, dummy_dialect: DummyDialect):
        """Tests malicious method values are rejected without echoing the value."""
        malicious_method = "RANGE); DROP TABLE users; --"

        with pytest.raises(TypeError) as exc_info:
            PartitionClause(
                dialect=dummy_dialect,
                method=malicious_method,
                keys=[Column(dummy_dialect, "created_date")],
            )

        message = str(exc_info.value)
        assert "method must be a PartitionStrategy" in message
        assert malicious_method not in message

    def test_partition_clause_requires_keys(self, dummy_dialect: DummyDialect):
        """Tests PartitionClause requires at least one key expression."""
        with pytest.raises(ValueError, match="keys are required"):
            PartitionClause(dialect=dummy_dialect, method=PartitionStrategy.RANGE, keys=[])

    def test_partition_clause_rejects_dialect_options_kwarg(self, dummy_dialect: DummyDialect):
        """Tests PartitionClause no longer accepts a dialect_options bag."""
        with pytest.raises(TypeError):
            PartitionClause(
                dialect=dummy_dialect,
                method=PartitionStrategy.RANGE,
                keys=[Column(dummy_dialect, "created_date")],
                dialect_options="columns_mode",
            )

    def test_partition_clause_requires_expression_keys(self, dummy_dialect: DummyDialect):
        """Tests PartitionClause keys must be expressions."""
        with pytest.raises(TypeError, match="BaseExpression"):
            PartitionClause(dialect=dummy_dialect, method=PartitionStrategy.RANGE, keys=["created_date"])

    def test_partition_support_methods_are_disabled_by_dummy(self, dummy_dialect: DummyDialect):
        """Tests DummyDialect exposes PartitionSupport with disabled capabilities."""
        assert dummy_dialect.supports_table_partitioning() is False
        assert dummy_dialect.supports_partitioned_table_creation() is False
        assert dummy_dialect.supports_range_table_partitioning() is False
        assert dummy_dialect.supports_hash_table_partitioning() is False

    def test_partition_mixin_default_support_methods_are_disabled(self):
        """Tests base PartitionMixin defaults generic partition capabilities to disabled."""
        mixin = PartitionMixin()

        assert mixin.supports_table_partitioning() is False
        assert mixin.supports_partitioned_table_creation() is False
        assert mixin.supports_partition_metadata_introspection() is False
        assert mixin.supports_range_table_partitioning() is False
        assert mixin.supports_list_table_partitioning() is False
        assert mixin.supports_hash_table_partitioning() is False
        assert mixin.supports_subpartitioning() is False

    def test_partition_clause_unsupported_by_default_mixin(self, dummy_dialect: DummyDialect):
        """Tests base PartitionMixin rejects partition SQL by default."""
        class UnsupportedPartitionDialect(PartitionMixin):
            name = "unsupported"

        dialect = UnsupportedPartitionDialect()
        # The dialect property validates the binding: a non-SQLDialectBase
        # object is rejected at construction time (before any rendering).
        with pytest.raises(TypeError, match="SQLDialectBase instance"):
            PartitionClause(
                dialect=dialect,
                method=PartitionStrategy.RANGE,
                keys=[Column(dummy_dialect, "created_date")],
            )

    def test_create_table_with_inherits(self, dummy_dialect: DummyDialect):
        """Tests CREATE TABLE with INHERITS clause (PostgreSQL specific)."""
        columns = [ColumnDefinition(dummy_dialect, "id", IntegerType(dummy_dialect)), ColumnDefinition(dummy_dialect, "extra_field", VarCharType(dummy_dialect, 50))]

        create_table_expr = CreateTableStatement(
            dummy_dialect, table=Table(dummy_dialect, 'child_table'), columns=columns, inherits=["parent_table", "audit_table"]
        )
        sql, params = create_table_expr.to_sql()

        assert '"child_table"' in sql
        assert "INHERITS" in sql
        assert '("parent_table", "audit_table")' in sql
        assert params == ()

    def test_create_table_complex_example(self, dummy_dialect: DummyDialect):
        """Tests a complex CREATE TABLE with multiple features."""
        columns = [
            ColumnDefinition(dummy_dialect, 
                "id",
                CustomType(dummy_dialect, raw="SERIAL"),
                constraints=[
                    ColumnConstraint(dummy_dialect, branch=ColumnPrimaryKeyConstraint(dummy_dialect)),
                    ColumnConstraint(dummy_dialect, branch=ColumnNotNullConstraint(dummy_dialect)),
                ],
            ),
            ColumnDefinition(dummy_dialect, 
                "user_id",
                IntegerType(dummy_dialect),
                constraints=[
                    ColumnConstraint(dummy_dialect, branch=ColumnForeignKeyConstraint(dummy_dialect, (Table(dummy_dialect, "users"), ["id"])))
                ],
                comment=ColumnCommentClause(dummy_dialect, "Reference to users table"),
            ),
            ColumnDefinition(dummy_dialect, 
                "amount",
                DecimalType(dummy_dialect, precision=10, scale=2),
                constraints=[
                    ColumnConstraint(dummy_dialect, branch=ColumnNotNullConstraint(dummy_dialect)),
                    ColumnConstraint(dummy_dialect, branch=ColumnCheckConstraint(dummy_dialect, ComparisonPredicate(
                            dummy_dialect,
                            ">=",
                            Column(dummy_dialect, "amount"),
                            Literal(dummy_dialect, 0),
                        ))),
                ],
            ),
            ColumnDefinition(dummy_dialect, 
                "status",
                VarCharType(dummy_dialect, 20),
                constraints=[
                    ColumnConstraint(dummy_dialect, branch=ColumnDefaultConstraint(dummy_dialect, "pending")),
                    ColumnConstraint(dummy_dialect, branch=ColumnNotNullConstraint(dummy_dialect)),  # Use constraint instead of nullable flag
                ],
            ),
            ColumnDefinition(dummy_dialect, 
                "created_at",
                TimestampType(dummy_dialect),
                constraints=[
                    ColumnConstraint(dummy_dialect, branch=ColumnDefaultConstraint(dummy_dialect, FunctionCall(dummy_dialect, "NOW")))
                ],
            ),
        ]

        table_constraints = [
            TableConstraint(dummy_dialect, branch=TableUniqueConstraint(dummy_dialect, ["user_id", "created_at"]))
        ]

        create_table_expr = CreateTableStatement(
            dummy_dialect,
            table=Table(dummy_dialect, 'orders'),
            columns=columns,
            table_constraints=table_constraints,
            if_not_exists=True,
            temporary=False,
        )
        sql, params = create_table_expr.to_sql()

        assert "CREATE TABLE IF NOT EXISTS" in sql
        assert '"orders"' in sql
        assert '"id" SERIAL PRIMARY KEY NOT NULL' in sql
        assert '"user_id" INTEGER REFERENCES "users"("id")' in sql
        assert "COMMENT 'Reference to users table'" in sql
        assert '"amount" DECIMAL(10,2) NOT NULL CHECK ("amount" >= 0)' in sql
        assert '"status" VARCHAR(20) DEFAULT \'pending\' NOT NULL' in sql
        assert 'UNIQUE ("user_id", "created_at")' in sql
        assert params == ()

