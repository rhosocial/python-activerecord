# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_statements_create_table.py
import inspect
from typing import List, Set, Tuple

import pytest
from rhosocial.activerecord.backend.dialect import SQLDialectBase
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.dialect import protocols as dialect_protocols
from rhosocial.activerecord.backend.expression import (
    Literal,
    Column,
    FunctionCall,
    CreateTableExpression,
    CreateTableAsExpression,
    CreateTableLikeExpression,
    CreateTableCloneExpression,
    CreateTableFromTemplateExpression,
    CreateTableCloneMode,
    CreateTableOptions,
    ColumnDefinition,
    ColumnCommentClause,
    TableCommentClause,
    IndexDefinition,
)
from rhosocial.activerecord.backend.expression.statements import (
    TableConstraint,
    TableConstraintType,
    ReferentialAction,
    ForeignKeyConstraint,
    ColumnConstraint,
    ColumnConstraintType,
    PartitionClause,
    PartitionStrategy,
    QueryExpression,
    StorageOptionsExpression,
)
from rhosocial.activerecord.backend.expression.query_parts import WhereClause
from rhosocial.activerecord.backend.expression.core import TableExpression
from rhosocial.activerecord.backend.dialect.mixins import PartitionMixin, DDLColumnMixin, TableMixin, ExpressionMixin, DataTypeMixin
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect
from rhosocial.activerecord.backend.expression.types import CustomType, DateType, DecimalType, IntegerType, SmallIntType, TextType, TimestampType, VarCharType


class PartitionTestDialect(SQLDialectBase, ExpressionMixin, DDLColumnMixin, DataTypeMixin, TableMixin, PartitionMixin):
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
    """Tests for CreateTableExpression with various configurations and options."""

    def test_basic_create_table(self, dummy_dialect: DummyDialect):
        """Tests a basic CREATE TABLE statement."""
        columns = [
            ColumnDefinition(dummy_dialect, 
                "id",
                IntegerType(dummy_dialect),
                constraints=[
                    ColumnConstraint(dummy_dialect, ColumnConstraintType.PRIMARY_KEY),
                    ColumnConstraint(dummy_dialect, ColumnConstraintType.NOT_NULL),
                ],
            ),
            ColumnDefinition(dummy_dialect, "name", VarCharType(dummy_dialect, 255), constraints=[ColumnConstraint(dummy_dialect, ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition(dummy_dialect, "email", TextType(dummy_dialect)),
        ]

        create_table_expr = CreateTableExpression(dummy_dialect, table="users", columns=columns)
        sql, params = create_table_expr.to_sql()

        assert sql.startswith('CREATE TABLE "users"')
        assert '"id" INTEGER PRIMARY KEY NOT NULL' in sql
        assert '"name" VARCHAR(255) NOT NULL' in sql
        assert '"email" TEXT' in sql
        assert params == ()

    def test_create_table_with_if_not_exists(self, dummy_dialect: DummyDialect):
        """Tests CREATE TABLE with IF NOT EXISTS flag."""
        columns = [ColumnDefinition(dummy_dialect, "id", IntegerType(dummy_dialect), constraints=[ColumnConstraint(dummy_dialect, ColumnConstraintType.PRIMARY_KEY)])]

        create_table_expr = CreateTableExpression(dummy_dialect, table="products", columns=columns, if_not_exists=True)
        sql, params = create_table_expr.to_sql()

        assert "CREATE TABLE IF NOT EXISTS" in sql
        assert '"products"' in sql
        assert params == ()

    def test_create_temporary_table(self, dummy_dialect: DummyDialect):
        """Tests CREATE TEMPORARY TABLE statement."""
        columns = [
            ColumnDefinition(dummy_dialect, 
                "session_id", VarCharType(dummy_dialect, 50), constraints=[ColumnConstraint(dummy_dialect, ColumnConstraintType.NOT_NULL)]
            ),
            ColumnDefinition(dummy_dialect, "data", TextType(dummy_dialect)),
        ]

        create_table_expr = CreateTableExpression(dummy_dialect, table="temp_sessions", columns=columns, temporary=True)
        sql, params = create_table_expr.to_sql()

        assert "CREATE TEMPORARY TABLE" in sql
        assert '"temp_sessions"' in sql
        assert params == ()

    def test_create_table_with_unique_constraint(self, dummy_dialect: DummyDialect):
        """Tests CREATE TABLE with UNIQUE column constraint."""
        columns = [
            ColumnDefinition(dummy_dialect, "id", IntegerType(dummy_dialect), constraints=[ColumnConstraint(dummy_dialect, ColumnConstraintType.PRIMARY_KEY)]),
            ColumnDefinition(dummy_dialect, "username", VarCharType(dummy_dialect, 50), constraints=[ColumnConstraint(dummy_dialect, ColumnConstraintType.UNIQUE)]),
            ColumnDefinition(dummy_dialect, "email", VarCharType(dummy_dialect, 100), constraints=[ColumnConstraint(dummy_dialect, ColumnConstraintType.UNIQUE)]),
        ]

        create_table_expr = CreateTableExpression(dummy_dialect, table="users", columns=columns)
        sql, params = create_table_expr.to_sql()

        assert '"username" VARCHAR(50) UNIQUE' in sql
        assert '"email" VARCHAR(100) UNIQUE' in sql
        assert params == ()

    def test_create_table_with_default_constraint(self, dummy_dialect: DummyDialect):
        """Tests CREATE TABLE with DEFAULT column constraints."""
        columns = [
            ColumnDefinition(dummy_dialect, "id", IntegerType(dummy_dialect), constraints=[ColumnConstraint(dummy_dialect, ColumnConstraintType.PRIMARY_KEY)]),
            ColumnDefinition(dummy_dialect, "name", VarCharType(dummy_dialect, 100)),
            ColumnDefinition(dummy_dialect,
                "status",
                VarCharType(dummy_dialect, 20),
                constraints=[ColumnConstraint(dummy_dialect, ColumnConstraintType.DEFAULT, default_value="active")],
            ),
            ColumnDefinition(dummy_dialect, 
                "created_at",
                TimestampType(dummy_dialect),
                constraints=[
                    ColumnConstraint(dummy_dialect, ColumnConstraintType.DEFAULT, default_value=FunctionCall(dummy_dialect, "NOW"))
                ],
            ),
        ]

        create_table_expr = CreateTableExpression(dummy_dialect, table="users", columns=columns)
        sql, params = create_table_expr.to_sql()

        # DDL clauses accept no bind parameters: DEFAULT literal values are
        # rendered inline.
        assert '"status" VARCHAR(20) DEFAULT \'active\'' in sql
        assert '"created_at" TIMESTAMP DEFAULT NOW()' in sql
        assert params == ()

    def test_create_table_with_check_constraint(self, dummy_dialect: DummyDialect):
        """Tests CREATE TABLE with CHECK column constraints."""
        # Create a check predicate for age > 0 (inline literal for DDL)
        age_check = Column(dummy_dialect, "age") > Literal(dummy_dialect, 0, inline_literals=True)

        columns = [
            ColumnDefinition(dummy_dialect, "id", IntegerType(dummy_dialect), constraints=[ColumnConstraint(dummy_dialect, ColumnConstraintType.PRIMARY_KEY)]),
            ColumnDefinition(dummy_dialect, "name", VarCharType(dummy_dialect, 100)),
            ColumnDefinition(dummy_dialect, 
                "age", IntegerType(dummy_dialect), constraints=[ColumnConstraint(dummy_dialect, ColumnConstraintType.CHECK, check_condition=age_check)]
            ),
        ]

        create_table_expr = CreateTableExpression(dummy_dialect, table="people", columns=columns)
        sql, params = create_table_expr.to_sql()

        assert '"age" INTEGER CHECK ("age" > 0)' in sql
        assert params == ()

    def test_create_table_with_foreign_key_constraint(self, dummy_dialect: DummyDialect):
        """Tests CREATE TABLE with FOREIGN KEY column constraints."""
        columns = [
            ColumnDefinition(dummy_dialect, "id", IntegerType(dummy_dialect), constraints=[ColumnConstraint(dummy_dialect, ColumnConstraintType.PRIMARY_KEY)]),
            ColumnDefinition(dummy_dialect, 
                "user_id",
                IntegerType(dummy_dialect),
                constraints=[
                    ColumnConstraint(dummy_dialect, ColumnConstraintType.FOREIGN_KEY, foreign_key_reference=("users", ["id"]))
                ],
            ),
            ColumnDefinition(dummy_dialect, "product_name", VarCharType(dummy_dialect, 100)),
        ]

        create_table_expr = CreateTableExpression(dummy_dialect, table="orders", columns=columns)
        sql, params = create_table_expr.to_sql()

        assert '"user_id" INTEGER REFERENCES "users"("id")' in sql
        assert params == ()

    def test_column_definition_identity_via_attribute(self, dummy_dialect: DummyDialect):
        """Identity is declared through the column-attribute channel (§5.3)."""
        from rhosocial.activerecord.base.ddl.attributes import IdentityAttribute

        col = ColumnDefinition(dummy_dialect, "id", IntegerType(dummy_dialect))
        col.attributes = dummy_dialect.select_column_attributes(
            [IdentityAttribute(generation="BY DEFAULT", start=1, increment=1)]
        )
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
            TableConstraint(dummy_dialect, constraint_type=TableConstraintType.PRIMARY_KEY, columns=["id"]),
            TableConstraint(dummy_dialect, constraint_type=TableConstraintType.UNIQUE, columns=["name"]),
            ForeignKeyConstraint(dummy_dialect, 
                foreign_key_table="categories",
                foreign_key_columns=["id"],
                columns=["category_id"],
                on_delete=ReferentialAction.CASCADE,
            ),
        ]

        create_table_expr = CreateTableExpression(
            dummy_dialect, table="products", columns=columns, table_constraints=table_constraints
        )
        sql, params = create_table_expr.to_sql()

        assert 'PRIMARY KEY ("id")' in sql
        assert 'UNIQUE ("name")' in sql
        assert 'FOREIGN KEY ("category_id") REFERENCES "categories"("id")' in sql
        assert params == ()

    def test_create_table_with_storage_options(self, dummy_dialect: DummyDialect):
        """Tests CREATE TABLE with storage options."""
        columns = [
            ColumnDefinition(dummy_dialect, "id", IntegerType(dummy_dialect), constraints=[ColumnConstraint(dummy_dialect, ColumnConstraintType.PRIMARY_KEY)]),
            ColumnDefinition(dummy_dialect, "data", TextType(dummy_dialect)),
        ]

        storage_opts = StorageOptionsExpression(
            dummy_dialect, {"engine": "InnoDB", "charset": "utf8mb4", "page_size": 8192}
        )

        create_table_expr = CreateTableExpression(
            dummy_dialect, table="documents", columns=columns, storage_options=storage_opts
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
            ColumnDefinition(dummy_dialect, "id", IntegerType(dummy_dialect), constraints=[ColumnConstraint(dummy_dialect, ColumnConstraintType.PRIMARY_KEY)]),
            ColumnDefinition(dummy_dialect, "name", VarCharType(dummy_dialect, 100)),
        ]

        create_table_expr = CreateTableExpression(
            dummy_dialect, table="large_table", columns=columns, tablespace="fast_ssd"
        )
        sql, params = create_table_expr.to_sql()

        assert '"large_table"' in sql
        assert "TABLESPACE" in sql
        assert '"fast_ssd"' in sql
        assert params == ()

    def test_create_table_as_query_result(self, dummy_dialect: DummyDialect):
        """Tests CREATE TABLE AS with a query result (CTAS)."""
        where_clause = WhereClause(
            dummy_dialect, condition=Column(dummy_dialect, "status") == Literal(dummy_dialect, "active")
        )
        query = QueryExpression(
            dummy_dialect,
            select=[Column(dummy_dialect, "id"), Column(dummy_dialect, "name")],
            from_=TableExpression(dummy_dialect, "users"),
            where=where_clause,
        )

        create_table_expr = CreateTableAsExpression(dummy_dialect, table="active_users", as_query=query)
        sql, params = create_table_expr.to_sql()

        # Query is rendered without parentheses (portable form).
        assert "AS SELECT" in sql
        assert "AS (" not in sql
        assert 'SELECT "id", "name" FROM "users"' in sql
        assert 'WHERE "status" = ?' in sql
        assert params == ("active",)

    def test_create_table_as_with_no_data(self, dummy_dialect: DummyDialect):
        """Tests CREATE TABLE AS ... WITH NO DATA."""
        query = QueryExpression(
            dummy_dialect,
            select=[Literal(dummy_dialect, 1)],
        )
        expr = CreateTableAsExpression(dummy_dialect, table="t", as_query=query, with_data=False)
        sql, params = expr.to_sql()
        assert sql.endswith("WITH NO DATA")
        assert params == (1,)

    def test_create_table_like_generic_render(self, dummy_dialect: DummyDialect):
        """Dummy advertises LIKE, so the generic reusable renderer is exercised."""
        expr = CreateTableLikeExpression(dummy_dialect, table="copy", like_table="users")
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
        expr = CreateTableLikeExpression(dialect, table="copy", like_table="users")
        with pytest.raises(UnsupportedFeatureError):
            expr.to_sql()

    def test_create_table_like_normalizes_references(self, dummy_dialect: DummyDialect):
        """Source may be a str, TableExpression, or (schema, table) tuple."""
        expr = CreateTableLikeExpression(
            dummy_dialect, table="copy", like_table=("sales", "users")
        )
        assert expr.table_name == "copy"
        assert expr.like_table.schema_name == "sales"
        assert expr.like_table.name == "users"

    def test_create_table_clone_generic_render(self, dummy_dialect: DummyDialect):
        expr = CreateTableCloneExpression(
            dummy_dialect, table="clone_t", source_table="src", copy_grants=True
        )
        sql, params = expr.to_sql()
        assert "CLONE" in sql
        assert "COPY GRANTS" in sql
        assert params == ()

    def test_create_table_clone_unsupported_raises(self):
        from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect

        dialect = SQLiteDialect()
        assert dialect.supports_create_table_clone() is False
        expr = CreateTableCloneExpression(dialect, table="clone_t", source_table="src")
        with pytest.raises(UnsupportedFeatureError):
            expr.to_sql()

    def test_create_table_clone_mode_selects_copy(self, dummy_dialect: DummyDialect):
        expr = CreateTableCloneExpression(
            dummy_dialect,
            table="copy_t",
            source_table="src",
            mode=CreateTableCloneMode.COPY,
        )
        sql, _ = expr.to_sql()
        assert "COPY" in sql
        assert "CLONE" not in sql

    def test_create_table_from_template_generic_render(self, dummy_dialect: DummyDialect):
        query = QueryExpression(dummy_dialect, select=[Literal(dummy_dialect, 1)])
        expr = CreateTableFromTemplateExpression(dummy_dialect, table="t", template=query)
        sql, params = expr.to_sql()
        assert "USING TEMPLATE" in sql
        assert params == (1,)

    def test_create_table_from_template_unsupported_raises(self):
        from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect

        dialect = SQLiteDialect()
        assert dialect.supports_create_table_using_template() is False
        query = QueryExpression(dialect, select=[Literal(dialect, 1)])
        expr = CreateTableFromTemplateExpression(dialect, table="t", template=query)
        with pytest.raises(UnsupportedFeatureError):
            expr.to_sql()

    def test_create_table_clone_mode_requires_type(self, dummy_dialect: DummyDialect):
        with pytest.raises(TypeError):
            CreateTableCloneExpression(
                dummy_dialect, table="t", source_table="src", mode="CLONE"
            )

    def test_create_table_options_or_replace(self, dummy_dialect: DummyDialect):
        expr = CreateTableExpression(
            dummy_dialect,
            table="t",
            columns=[],
            table_options=CreateTableOptions(dummy_dialect, or_replace=True),
        )
        sql, _ = expr.to_sql()
        assert sql.startswith("CREATE OR REPLACE TABLE")

    def test_create_table_options_or_replace(self, dummy_dialect: DummyDialect):
        expr = CreateTableExpression(
            dummy_dialect,
            table="t",
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
        expr = CreateTableExpression(
            dialect,
            table="t",
            columns=[],
            table_options=CreateTableOptions(dialect, or_replace=True),
        )
        with pytest.raises(UnsupportedFeatureError):
            expr.to_sql()

    def test_create_table_with_indexes(self, dummy_dialect: DummyDialect):
        """Tests CREATE TABLE with indexes."""
        columns = [
            ColumnDefinition(dummy_dialect, "id", IntegerType(dummy_dialect), constraints=[ColumnConstraint(dummy_dialect, ColumnConstraintType.PRIMARY_KEY)]),
            ColumnDefinition(dummy_dialect, "email", VarCharType(dummy_dialect, 100)),
            ColumnDefinition(dummy_dialect, "created_at", TimestampType(dummy_dialect)),
        ]

        indexes = [
            IndexDefinition(dummy_dialect, "idx_users_email", ["email"], unique=True),
            IndexDefinition(dummy_dialect, "idx_users_created", ["created_at"], unique=False),
        ]

        create_table_expr = CreateTableExpression(dummy_dialect, table="users", columns=columns, indexes=indexes)

        # Inline indexes are a dialect convenience (MySQL/MariaDB/ClickHouse);
        # the SQL-standard behavior is a standalone CREATE INDEX, so the generic
        # renderer rejects inline indexes instead of silently dropping them.
        with pytest.raises(UnsupportedFeatureError):
            create_table_expr.to_sql()

    def test_create_table_with_nullable_setting(self, dummy_dialect: DummyDialect):
        """Tests CREATE TABLE with nullable settings."""
        columns = [
            ColumnDefinition(dummy_dialect, "id", IntegerType(dummy_dialect), constraints=[ColumnConstraint(dummy_dialect, ColumnConstraintType.PRIMARY_KEY)]),
            ColumnDefinition(dummy_dialect, 
                "name", VarCharType(dummy_dialect, 100), constraints=[ColumnConstraint(dummy_dialect, ColumnConstraintType.NOT_NULL)]
            ),  # Explicitly NOT NULL using constraint
            ColumnDefinition(dummy_dialect, 
                "description", TextType(dummy_dialect), constraints=[ColumnConstraint(dummy_dialect, ColumnConstraintType.NULL)]
            ),  # Explicitly allow NULLs using constraint
            ColumnDefinition(dummy_dialect, "age", IntegerType(dummy_dialect)),  # No constraints - uses database default
        ]

        create_table_expr = CreateTableExpression(dummy_dialect, table="profiles", columns=columns)
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
                constraints=[ColumnConstraint(dummy_dialect, ColumnConstraintType.PRIMARY_KEY)],
                comment=ColumnCommentClause(dummy_dialect, "Primary identifier"),
            ),
            ColumnDefinition(dummy_dialect, "name", VarCharType(dummy_dialect, 100), comment=ColumnCommentClause(dummy_dialect, "User's display name")),
        ]

        create_table_expr = CreateTableExpression(dummy_dialect, table="users_with_comments", columns=columns)
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

        create_table_expr = CreateTableExpression(
            dummy_dialect,
            table="log_entries",
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
        """Tests CreateTableExpression appends PartitionClause SQL and params."""
        dialect = PartitionTestDialect()
        partition = PartitionClause(
            dialect=dialect,
            method=PartitionStrategy.HASH,
            keys=[FunctionCall(dialect, "bucket", Literal(dialect, "tenant"))],
        )
        create_table_expr = CreateTableExpression(
            dialect,
            table="events",
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
            CreateTableExpression(
                dummy_dialect,
                table="invalid_partition",
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
        assert mixin.supports_add_partition() is False
        assert mixin.supports_drop_partition() is False
        assert mixin.supports_truncate_partition() is False
        assert mixin.supports_reorganize_partition() is False
        assert mixin.supports_attach_partition() is False
        assert mixin.supports_detach_partition() is False

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

        create_table_expr = CreateTableExpression(
            dummy_dialect, table="child_table", columns=columns, inherits=["parent_table", "audit_table"]
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
                CustomType(dummy_dialect, "SERIAL"),
                constraints=[
                    ColumnConstraint(dummy_dialect, ColumnConstraintType.PRIMARY_KEY),
                    ColumnConstraint(dummy_dialect, ColumnConstraintType.NOT_NULL),
                ],
            ),
            ColumnDefinition(dummy_dialect, 
                "user_id",
                IntegerType(dummy_dialect),
                constraints=[
                    ColumnConstraint(dummy_dialect, ColumnConstraintType.FOREIGN_KEY, foreign_key_reference=("users", ["id"]))
                ],
                comment=ColumnCommentClause(dummy_dialect, "Reference to users table"),
            ),
            ColumnDefinition(dummy_dialect, 
                "amount",
                DecimalType(dummy_dialect, precision=10, scale=2),
                constraints=[
                    ColumnConstraint(dummy_dialect, ColumnConstraintType.NOT_NULL),
                    ColumnConstraint(dummy_dialect, 
                        ColumnConstraintType.CHECK,
                        check_condition=Column(dummy_dialect, "amount")
                        >= Literal(dummy_dialect, 0, inline_literals=True),
                    ),
                ],
            ),
            ColumnDefinition(dummy_dialect, 
                "status",
                VarCharType(dummy_dialect, 20),
                constraints=[
                    ColumnConstraint(dummy_dialect, ColumnConstraintType.DEFAULT, default_value="pending"),
                    ColumnConstraint(dummy_dialect, ColumnConstraintType.NOT_NULL),  # Use constraint instead of nullable flag
                ],
            ),
            ColumnDefinition(dummy_dialect, 
                "created_at",
                TimestampType(dummy_dialect),
                constraints=[
                    ColumnConstraint(dummy_dialect, ColumnConstraintType.DEFAULT, default_value=FunctionCall(dummy_dialect, "NOW"))
                ],
            ),
        ]

        table_constraints = [
            TableConstraint(dummy_dialect, constraint_type=TableConstraintType.UNIQUE, columns=["user_id", "created_at"])
        ]

        create_table_expr = CreateTableExpression(
            dummy_dialect,
            table="orders",
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

    def test_create_table_with_default_constraint_missing_value_raises_error(self, dummy_dialect: DummyDialect):
        """Tests that CREATE TABLE with DEFAULT constraint but no value raises ValueError."""
        from rhosocial.activerecord.backend.expression.statements import (
            ColumnDefinition,
            ColumnConstraint,
            ColumnConstraintType,
        )

        columns = [
            ColumnDefinition(dummy_dialect, 
                "status",
                VarCharType(dummy_dialect, 20),
                constraints=[ColumnConstraint(dummy_dialect, ColumnConstraintType.DEFAULT)],  # No default value provided
            )
        ]

        create_table_expr = CreateTableExpression(dummy_dialect, table="test_table", columns=columns)

        with pytest.raises(ValueError, match=r"DEFAULT constraint must have a default value specified."):
            create_table_expr.to_sql()

    def test_create_table_with_check_constraint_missing_condition_raises_error(self, dummy_dialect: DummyDialect):
        """Tests that CREATE TABLE with CHECK constraint but no condition raises ValueError."""
        from rhosocial.activerecord.backend.expression.statements import (
            ColumnDefinition,
            ColumnConstraint,
            ColumnConstraintType,
        )

        columns = [
            ColumnDefinition(dummy_dialect, 
                "age",
                IntegerType(dummy_dialect),
                constraints=[ColumnConstraint(dummy_dialect, ColumnConstraintType.CHECK)],  # No check condition provided
            )
        ]

        create_table_expr = CreateTableExpression(dummy_dialect, table="test_table", columns=columns)

        with pytest.raises(ValueError, match=r"CHECK constraint must have a check condition specified."):
            create_table_expr.to_sql()

    def test_create_table_with_foreign_key_constraint_missing_reference_raises_error(self, dummy_dialect: DummyDialect):
        """Tests that CREATE TABLE with FOREIGN KEY constraint but no reference raises ValueError."""
        from rhosocial.activerecord.backend.expression.statements import (
            ColumnDefinition,
            ColumnConstraint,
            ColumnConstraintType,
        )

        columns = [
            ColumnDefinition(dummy_dialect, 
                "user_id",
                IntegerType(dummy_dialect),
                constraints=[ColumnConstraint(dummy_dialect, ColumnConstraintType.FOREIGN_KEY)],  # No foreign key reference provided
            )
        ]

        create_table_expr = CreateTableExpression(dummy_dialect, table="orders", columns=columns)

        with pytest.raises(ValueError, match=r"FOREIGN KEY constraint must have a foreign key reference specified."):
            create_table_expr.to_sql()

    def test_create_table_with_primary_key_table_constraint_missing_columns_raises_error(
        self, dummy_dialect: DummyDialect
    ):
        """Tests that CREATE TABLE with PRIMARY KEY table constraint but no columns raises ValueError."""
        from rhosocial.activerecord.backend.expression.statements import TableConstraint, TableConstraintType

        table_constraints = [
            TableConstraint(dummy_dialect, 
                constraint_type=TableConstraintType.PRIMARY_KEY,
                # Missing columns parameter
            )
        ]

        create_table_expr = CreateTableExpression(
            dummy_dialect, table="test_table", columns=[], table_constraints=table_constraints
        )

        with pytest.raises(ValueError, match=r"PRIMARY KEY constraint must have at least one column specified."):
            create_table_expr.to_sql()

    def test_create_table_with_unique_table_constraint_missing_columns_raises_error(self, dummy_dialect: DummyDialect):
        """Tests that CREATE TABLE with UNIQUE table constraint but no columns raises ValueError."""
        from rhosocial.activerecord.backend.expression.statements import TableConstraint, TableConstraintType

        table_constraints = [
            TableConstraint(dummy_dialect, 
                constraint_type=TableConstraintType.UNIQUE,
                # Missing columns parameter
            )
        ]

        create_table_expr = CreateTableExpression(
            dummy_dialect, table="test_table", columns=[], table_constraints=table_constraints
        )

        with pytest.raises(ValueError, match=r"UNIQUE constraint must have at least one column specified."):
            create_table_expr.to_sql()

    def test_create_table_with_check_table_constraint_missing_condition_raises_error(self, dummy_dialect: DummyDialect):
        """Tests that CREATE TABLE with CHECK table constraint but no condition raises ValueError."""
        from rhosocial.activerecord.backend.expression.statements import TableConstraint, TableConstraintType

        table_constraints = [
            TableConstraint(dummy_dialect, 
                constraint_type=TableConstraintType.CHECK,
                # Missing check_condition parameter
            )
        ]

        create_table_expr = CreateTableExpression(
            dummy_dialect, table="test_table", columns=[], table_constraints=table_constraints
        )

        with pytest.raises(ValueError, match=r"CHECK constraint must have a check condition specified."):
            create_table_expr.to_sql()

    def test_create_table_with_foreign_key_table_constraint_missing_local_columns_raises_error(
        self, dummy_dialect: DummyDialect
    ):
        """Tests that CREATE TABLE with FOREIGN KEY table constraint but no local columns raises ValueError."""
        from rhosocial.activerecord.backend.expression.statements import TableConstraint, TableConstraintType

        table_constraints = [
            TableConstraint(dummy_dialect, 
                constraint_type=TableConstraintType.FOREIGN_KEY,
                foreign_key_table="users",
                foreign_key_columns=["id"],
                # Missing local columns (columns parameter)
            )
        ]

        create_table_expr = CreateTableExpression(
            dummy_dialect, table="orders", columns=[], table_constraints=table_constraints
        )

        with pytest.raises(ValueError, match=r"FOREIGN KEY constraint must have at least one local column specified."):
            create_table_expr.to_sql()

    def test_create_table_with_foreign_key_table_constraint_missing_foreign_columns_raises_error(
        self, dummy_dialect: DummyDialect
    ):
        """Tests that CREATE TABLE with FOREIGN KEY table constraint but no foreign columns raises ValueError."""
        from rhosocial.activerecord.backend.expression.statements import TableConstraint, TableConstraintType

        table_constraints = [
            TableConstraint(dummy_dialect, 
                constraint_type=TableConstraintType.FOREIGN_KEY,
                columns=["user_id"],
                foreign_key_table="users",
                # Missing foreign_key_columns parameter
            )
        ]

        create_table_expr = CreateTableExpression(
            dummy_dialect, table="orders", columns=[], table_constraints=table_constraints
        )

        with pytest.raises(
            ValueError, match=r"FOREIGN KEY constraint must have at least one foreign key column specified."
        ):
            create_table_expr.to_sql()

    def test_create_table_with_foreign_key_table_constraint_missing_foreign_table_raises_error(
        self, dummy_dialect: DummyDialect
    ):
        """Tests that CREATE TABLE with FOREIGN KEY table constraint but no foreign table raises ValueError."""
        from rhosocial.activerecord.backend.expression.statements import TableConstraint, TableConstraintType

        table_constraints = [
            TableConstraint(dummy_dialect, 
                constraint_type=TableConstraintType.FOREIGN_KEY,
                columns=["user_id"],
                foreign_key_columns=["id"],
                # Missing foreign_key_table parameter
            )
        ]

        create_table_expr = CreateTableExpression(
            dummy_dialect, table="orders", columns=[], table_constraints=table_constraints
        )

        with pytest.raises(ValueError, match=r"FOREIGN KEY constraint must have a foreign key table specified."):
            create_table_expr.to_sql()
