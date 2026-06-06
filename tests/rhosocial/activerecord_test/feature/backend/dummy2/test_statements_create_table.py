# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_statements_create_table.py
import pytest
from rhosocial.activerecord.backend.expression import (
    Literal,
    Column,
    FunctionCall,
    CreateTableExpression,
    ColumnDefinition,
    IndexDefinition,
)
from rhosocial.activerecord.backend.expression.statements import (
    TableConstraint,
    TableConstraintType,
    ReferentialAction,
    ForeignKeyConstraint,
    ColumnConstraint,
    ColumnConstraintType,
    PartitionKey,
    PartitionClause,
    PartitionStrategy,
    QueryExpression,
)
from rhosocial.activerecord.backend.expression.query_parts import WhereClause
from rhosocial.activerecord.backend.expression.core import TableExpression
from rhosocial.activerecord.backend.dialect.mixins import PartitionMixin
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect


class TestCreateTableStatements:
    """Tests for CreateTableExpression with various configurations and options."""

    def test_basic_create_table(self, dummy_dialect: DummyDialect):
        """Tests a basic CREATE TABLE statement."""
        columns = [
            ColumnDefinition(
                "id",
                "INTEGER",
                constraints=[
                    ColumnConstraint(ColumnConstraintType.PRIMARY_KEY),
                    ColumnConstraint(ColumnConstraintType.NOT_NULL),
                ],
            ),
            ColumnDefinition("name", "VARCHAR(255)", constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("email", "TEXT"),
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
        columns = [ColumnDefinition("id", "INTEGER", constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY)])]

        create_table_expr = CreateTableExpression(dummy_dialect, table="products", columns=columns, if_not_exists=True)
        sql, params = create_table_expr.to_sql()

        assert "CREATE TABLE IF NOT EXISTS" in sql
        assert '"products"' in sql
        assert params == ()

    def test_create_temporary_table(self, dummy_dialect: DummyDialect):
        """Tests CREATE TEMPORARY TABLE statement."""
        columns = [
            ColumnDefinition(
                "session_id", "VARCHAR(50)", constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]
            ),
            ColumnDefinition("data", "TEXT"),
        ]

        create_table_expr = CreateTableExpression(dummy_dialect, table="temp_sessions", columns=columns, temporary=True)
        sql, params = create_table_expr.to_sql()

        assert "CREATE TEMPORARY TABLE" in sql
        assert '"temp_sessions"' in sql
        assert params == ()

    def test_create_table_with_unique_constraint(self, dummy_dialect: DummyDialect):
        """Tests CREATE TABLE with UNIQUE column constraint."""
        columns = [
            ColumnDefinition("id", "INTEGER", constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY)]),
            ColumnDefinition("username", "VARCHAR(50)", constraints=[ColumnConstraint(ColumnConstraintType.UNIQUE)]),
            ColumnDefinition("email", "VARCHAR(100)", constraints=[ColumnConstraint(ColumnConstraintType.UNIQUE)]),
        ]

        create_table_expr = CreateTableExpression(dummy_dialect, table="users", columns=columns)
        sql, params = create_table_expr.to_sql()

        assert '"username" VARCHAR(50) UNIQUE' in sql
        assert '"email" VARCHAR(100) UNIQUE' in sql
        assert params == ()

    def test_create_table_with_default_constraint(self, dummy_dialect: DummyDialect):
        """Tests CREATE TABLE with DEFAULT column constraints."""
        columns = [
            ColumnDefinition("id", "INTEGER", constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY)]),
            ColumnDefinition("name", "VARCHAR(100)"),
            ColumnDefinition(
                "status",
                "VARCHAR(20)",
                constraints=[ColumnConstraint(ColumnConstraintType.DEFAULT, default_value="active")],
            ),
            ColumnDefinition(
                "created_at",
                "TIMESTAMP",
                constraints=[
                    ColumnConstraint(ColumnConstraintType.DEFAULT, default_value=FunctionCall(dummy_dialect, "NOW"))
                ],
            ),
        ]

        create_table_expr = CreateTableExpression(dummy_dialect, table="users", columns=columns)
        sql, params = create_table_expr.to_sql()

        assert '"status" VARCHAR(20) DEFAULT ?' in sql
        assert '"created_at" TIMESTAMP DEFAULT NOW()' in sql
        assert params == ("active",)

    def test_create_table_with_check_constraint(self, dummy_dialect: DummyDialect):
        """Tests CREATE TABLE with CHECK column constraints."""
        # Create a check predicate for age > 0
        age_check = Column(dummy_dialect, "age") > Literal(dummy_dialect, 0)

        columns = [
            ColumnDefinition("id", "INTEGER", constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY)]),
            ColumnDefinition("name", "VARCHAR(100)"),
            ColumnDefinition(
                "age", "INTEGER", constraints=[ColumnConstraint(ColumnConstraintType.CHECK, check_condition=age_check)]
            ),
        ]

        create_table_expr = CreateTableExpression(dummy_dialect, table="people", columns=columns)
        sql, params = create_table_expr.to_sql()

        assert '"age" INTEGER CHECK ("age" > ?)' in sql
        assert params == (0,)

    def test_create_table_with_foreign_key_constraint(self, dummy_dialect: DummyDialect):
        """Tests CREATE TABLE with FOREIGN KEY column constraints."""
        columns = [
            ColumnDefinition("id", "INTEGER", constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY)]),
            ColumnDefinition(
                "user_id",
                "INTEGER",
                constraints=[
                    ColumnConstraint(ColumnConstraintType.FOREIGN_KEY, foreign_key_reference=("users", ["id"]))
                ],
            ),
            ColumnDefinition("product_name", "VARCHAR(100)"),
        ]

        create_table_expr = CreateTableExpression(dummy_dialect, table="orders", columns=columns)
        sql, params = create_table_expr.to_sql()

        assert '"user_id" INTEGER REFERENCES "users"("id")' in sql
        assert params == ()

    def test_create_table_with_table_level_constraints(self, dummy_dialect: DummyDialect):
        """Tests CREATE TABLE with table-level constraints."""
        columns = [
            ColumnDefinition("id", "INTEGER"),
            ColumnDefinition("name", "VARCHAR(100)"),
            ColumnDefinition("category_id", "INTEGER"),
        ]

        table_constraints = [
            TableConstraint(constraint_type=TableConstraintType.PRIMARY_KEY, columns=["id"]),
            TableConstraint(constraint_type=TableConstraintType.UNIQUE, columns=["name"]),
            ForeignKeyConstraint(
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
            ColumnDefinition("id", "INTEGER", constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY)]),
            ColumnDefinition("data", "TEXT"),
        ]

        storage_opts = {"engine": "InnoDB", "charset": "utf8mb4", "page_size": 8192}

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
            ColumnDefinition("id", "INTEGER", constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY)]),
            ColumnDefinition("name", "VARCHAR(100)"),
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
        """Tests CREATE TABLE AS with a query result."""
        where_clause = WhereClause(
            dummy_dialect, condition=Column(dummy_dialect, "status") == Literal(dummy_dialect, "active")
        )
        query = QueryExpression(
            dummy_dialect,
            select=[Column(dummy_dialect, "id"), Column(dummy_dialect, "name")],
            from_=TableExpression(dummy_dialect, "users"),
            where=where_clause,
        )

        columns = [  # For CREATE TABLE AS, columns list may be empty since they're defined by the query
            # Note: In a real CREATE TABLE AS, column definitions come from the query results
        ]

        create_table_expr = CreateTableExpression(dummy_dialect, table="active_users", columns=columns, as_query=query)
        sql, params = create_table_expr.to_sql()

        # Should have AS subquery part
        assert "AS (" in sql
        assert 'SELECT "id", "name" FROM "users"' in sql
        assert 'WHERE "status" = ?' in sql
        assert params == ("active",)

    def test_create_table_with_indexes(self, dummy_dialect: DummyDialect):
        """Tests CREATE TABLE with indexes."""
        columns = [
            ColumnDefinition("id", "INTEGER", constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY)]),
            ColumnDefinition("email", "VARCHAR(100)"),
            ColumnDefinition("created_at", "TIMESTAMP"),
        ]

        indexes = [
            IndexDefinition("idx_users_email", ["email"], unique=True),
            IndexDefinition("idx_users_created", ["created_at"], unique=False),
        ]

        create_table_expr = CreateTableExpression(dummy_dialect, table="users", columns=columns, indexes=indexes)
        sql, params = create_table_expr.to_sql()

        # The base implementation in DummyDialect should support column constraints
        # but may not fully implement index creation in the main CREATE TABLE statement
        # Indexes might be created separately in real implementations
        assert '"users"' in sql
        assert params == ()

    def test_create_table_with_nullable_setting(self, dummy_dialect: DummyDialect):
        """Tests CREATE TABLE with nullable settings."""
        columns = [
            ColumnDefinition("id", "INTEGER", constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY)]),
            ColumnDefinition(
                "name", "VARCHAR(100)", constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]
            ),  # Explicitly NOT NULL using constraint
            ColumnDefinition(
                "description", "TEXT", constraints=[ColumnConstraint(ColumnConstraintType.NULL)]
            ),  # Explicitly allow NULLs using constraint
            ColumnDefinition("age", "INTEGER"),  # No constraints - uses database default
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
            ColumnDefinition(
                "id",
                "INTEGER",
                constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY)],
                comment="Primary identifier",
            ),
            ColumnDefinition("name", "VARCHAR(100)", comment="User's display name"),
        ]

        create_table_expr = CreateTableExpression(dummy_dialect, table="users_with_comments", columns=columns)
        sql, params = create_table_expr.to_sql()

        assert '"users_with_comments"' in sql
        assert "COMMENT 'Primary identifier'" in sql
        assert "COMMENT 'User's display name'" in sql
        assert params == ()

    def test_create_table_partition_by(self, dummy_dialect: DummyDialect):
        """Tests CREATE TABLE with partitioning via PartitionClause."""
        columns = [
            ColumnDefinition("id", "INTEGER"),
            ColumnDefinition("name", "VARCHAR(100)"),
            ColumnDefinition("created_date", "DATE"),
        ]

        create_table_expr = CreateTableExpression(
            dummy_dialect,
            table="log_entries",
            columns=columns,
            partition=PartitionClause(
                dialect=dummy_dialect,
                strategy=PartitionStrategy.RANGE,
                key=PartitionKey(columns=["created_date"]),
            ),
        )
        sql, params = create_table_expr.to_sql()

        assert '"log_entries"' in sql
        assert "PARTITION BY RANGE" in sql
        assert '("created_date")' in sql
        assert params == ()

    def test_create_table_with_partition_spec(self, dummy_dialect: DummyDialect):
        """Tests CREATE TABLE with structured partition specification."""
        columns = [
            ColumnDefinition("id", "INTEGER"),
            ColumnDefinition("name", "VARCHAR(100)"),
            ColumnDefinition("created_date", "DATE"),
        ]

        create_table_expr = CreateTableExpression(
            dummy_dialect,
            table="log_entries",
            columns=columns,
            partition=PartitionClause(
                dialect=dummy_dialect,
                strategy=PartitionStrategy.RANGE,
                key=PartitionKey(columns=["created_date"]),
            ),
        )
        sql, params = create_table_expr.to_sql()

        assert '"log_entries"' in sql
        assert "PARTITION BY RANGE" in sql
        assert '("created_date")' in sql
        assert params == ()

    def test_create_table_with_multi_column_partition_spec(self, dummy_dialect: DummyDialect):
        """Tests CREATE TABLE partition key with multiple columns."""
        columns = [
            ColumnDefinition("tenant_id", "INTEGER"),
            ColumnDefinition("created_date", "DATE"),
        ]

        create_table_expr = CreateTableExpression(
            dummy_dialect,
            table="tenant_events",
            columns=columns,
            partition=PartitionClause(
                dialect=dummy_dialect,
                strategy=PartitionStrategy.HASH,
                key=PartitionKey(columns=["tenant_id", "created_date"]),
            ),
        )
        sql, params = create_table_expr.to_sql()

        assert "PARTITION BY HASH" in sql
        assert '("tenant_id", "created_date")' in sql
        assert params == ()

    def test_create_table_partition_requires_partition_clause(self, dummy_dialect: DummyDialect):
        """Tests partition parameter must be a PartitionClause instance."""
        columns = [ColumnDefinition("id", "INTEGER")]

        with pytest.raises(TypeError, match="partition must be a PartitionClause"):
            CreateTableExpression(
                dummy_dialect,
                table="invalid_partition",
                columns=columns,
                partition="RANGE",
            )

    def test_create_table_partition_spec_requires_key(self, dummy_dialect: DummyDialect):
        """Tests structured partition spec requires columns or expression."""
        columns = [ColumnDefinition("id", "INTEGER")]
        create_table_expr = CreateTableExpression(
            dummy_dialect,
            table="invalid_partition",
            columns=columns,
            partition=PartitionClause(
                dialect=dummy_dialect,
                strategy=PartitionStrategy.RANGE,
                key=PartitionKey(),
            ),
        )

        with pytest.raises(ValueError, match="Partition key must specify"):
            create_table_expr.to_sql()

    def test_partition_support_methods_are_enabled_for_dummy(self, dummy_dialect: DummyDialect):
        """Tests dummy dialect exposes partition support through PartitionMixin."""
        assert dummy_dialect.supports_table_partitioning() is True
        assert dummy_dialect.supports_partitioned_table_creation() is True
        assert dummy_dialect.supports_range_table_partitioning() is True
        assert dummy_dialect.supports_list_table_partitioning() is True
        assert dummy_dialect.supports_hash_table_partitioning() is True
        assert dummy_dialect.supports_key_table_partitioning() is True
        assert dummy_dialect.supports_subpartitioning() is True
        assert dummy_dialect.supports_partition_metadata_introspection() is False

    def test_partition_mixin_default_support_methods_are_disabled(self):
        """Tests base PartitionMixin defaults all partition capabilities to disabled."""
        mixin = PartitionMixin()

        assert mixin.supports_table_partitioning() is False
        assert mixin.supports_partitioned_table_creation() is False
        assert mixin.supports_range_table_partitioning() is False
        assert mixin.supports_list_table_partitioning() is False
        assert mixin.supports_hash_table_partitioning() is False
        assert mixin.supports_key_table_partitioning() is False
        assert mixin.supports_subpartitioning() is False
        assert mixin.supports_partition_metadata_introspection() is False

    def test_partition_clause_rejects_invalid_strategy(self, dummy_dialect: DummyDialect):
        """Tests invalid partition strategies are rejected."""
        partition = PartitionClause(
            dialect=dummy_dialect,
            strategy="INVALID",
            key=PartitionKey(columns=["created_date"]),
        )

        with pytest.raises(ValueError, match="Invalid partition strategy"):
            partition.to_sql()

    def test_partition_clause_accepts_dialect_extra_strategy(self, dummy_dialect: DummyDialect):
        """Tests dialect-specific partition strategies can be enabled per expression."""
        partition = PartitionClause(
            dialect=dummy_dialect,
            strategy="KEY",
            key=PartitionKey(columns=["tenant_id"]),
            dialect_options={"extra_strategies": {"KEY"}},
        )

        sql, params = partition.to_sql()

        assert sql == ' PARTITION BY KEY ("tenant_id")'
        assert params == ()

    def test_partition_clause_rejects_columns_and_expression(self, dummy_dialect: DummyDialect):
        """Tests partition key rejects ambiguous columns plus expression."""
        partition = PartitionClause(
            dialect=dummy_dialect,
            strategy=PartitionStrategy.RANGE,
            key=PartitionKey(
                columns=["created_date"],
                expression=FunctionCall(dummy_dialect, "date", Column(dummy_dialect, "created_at")),
            ),
        )

        with pytest.raises(ValueError, match="cannot specify both columns and expression"):
            partition.to_sql()

    def test_partition_clause_formats_expression_key(self, dummy_dialect: DummyDialect):
        """Tests expression-based partition keys delegate to expression SQL."""
        partition = PartitionClause(
            dialect=dummy_dialect,
            strategy=PartitionStrategy.RANGE,
            key=PartitionKey(
                expression=FunctionCall(dummy_dialect, "date", Column(dummy_dialect, "created_at")),
            ),
        )

        sql, params = partition.to_sql()

        assert sql == ' PARTITION BY RANGE (DATE("created_at"))'
        assert params == ()

    def test_partition_clause_unsupported_by_default_mixin(self, dummy_dialect: DummyDialect):
        """Tests base PartitionMixin rejects partition SQL when support is disabled."""
        class UnsupportedPartitionDialect(DummyDialect):
            def supports_table_partitioning(self) -> bool:
                return False

        dialect = UnsupportedPartitionDialect()
        partition = PartitionClause(
            dialect=dialect,
            strategy=PartitionStrategy.RANGE,
            key=PartitionKey(columns=["created_date"]),
        )

        with pytest.raises(Exception, match="does not support table partitioning"):
            partition.to_sql()

    def test_create_table_with_inherits(self, dummy_dialect: DummyDialect):
        """Tests CREATE TABLE with INHERITS clause (PostgreSQL specific)."""
        columns = [ColumnDefinition("id", "INTEGER"), ColumnDefinition("extra_field", "VARCHAR(50)")]

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
            ColumnDefinition(
                "id",
                "SERIAL",
                constraints=[
                    ColumnConstraint(ColumnConstraintType.PRIMARY_KEY),
                    ColumnConstraint(ColumnConstraintType.NOT_NULL),
                ],
            ),
            ColumnDefinition(
                "user_id",
                "INTEGER",
                constraints=[
                    ColumnConstraint(ColumnConstraintType.FOREIGN_KEY, foreign_key_reference=("users", ["id"]))
                ],
                comment="Reference to users table",
            ),
            ColumnDefinition(
                "amount",
                "DECIMAL(10,2)",
                constraints=[
                    ColumnConstraint(ColumnConstraintType.NOT_NULL),
                    ColumnConstraint(
                        ColumnConstraintType.CHECK,
                        check_condition=Column(dummy_dialect, "amount") >= Literal(dummy_dialect, 0),
                    ),
                ],
            ),
            ColumnDefinition(
                "status",
                "VARCHAR(20)",
                constraints=[
                    ColumnConstraint(ColumnConstraintType.DEFAULT, default_value="pending"),
                    ColumnConstraint(ColumnConstraintType.NOT_NULL),  # Use constraint instead of nullable flag
                ],
            ),
            ColumnDefinition(
                "created_at",
                "TIMESTAMP",
                constraints=[
                    ColumnConstraint(ColumnConstraintType.DEFAULT, default_value=FunctionCall(dummy_dialect, "NOW"))
                ],
            ),
        ]

        table_constraints = [
            TableConstraint(constraint_type=TableConstraintType.UNIQUE, columns=["user_id", "created_at"])
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
        assert '"amount" DECIMAL(10,2) NOT NULL CHECK ("amount" >= ?)' in sql
        assert '"status" VARCHAR(20) DEFAULT ? NOT NULL' in sql
        assert 'UNIQUE ("user_id", "created_at")' in sql
        assert params == (0, "pending")

    def test_create_table_with_default_constraint_missing_value_raises_error(self, dummy_dialect: DummyDialect):
        """Tests that CREATE TABLE with DEFAULT constraint but no value raises ValueError."""
        from rhosocial.activerecord.backend.expression.statements import (
            ColumnDefinition,
            ColumnConstraint,
            ColumnConstraintType,
        )

        columns = [
            ColumnDefinition(
                "status",
                "VARCHAR(20)",
                constraints=[ColumnConstraint(ColumnConstraintType.DEFAULT)],  # No default value provided
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
            ColumnDefinition(
                "age",
                "INTEGER",
                constraints=[ColumnConstraint(ColumnConstraintType.CHECK)],  # No check condition provided
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
            ColumnDefinition(
                "user_id",
                "INTEGER",
                constraints=[ColumnConstraint(ColumnConstraintType.FOREIGN_KEY)],  # No foreign key reference provided
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
            TableConstraint(
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
            TableConstraint(
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
            TableConstraint(
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
            TableConstraint(
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
            TableConstraint(
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
            TableConstraint(
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
