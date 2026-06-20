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
    PartitionClause,
    PartitionStrategy,
    QueryExpression,
)
from rhosocial.activerecord.backend.expression.query_parts import WhereClause
from rhosocial.activerecord.backend.expression.core import TableExpression
from rhosocial.activerecord.backend.dialect.mixins import PartitionMixin, IdentifierMixin, DDLColumnMixin, TableMixin, ExpressionMixin, DDLTypeMixin
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect
from rhosocial.activerecord.backend.expression.types import CustomType, DateType, DecimalType, IntegerType, SmallIntType, TextType, TimestampType, VarCharType


class PartitionTestDialect(SQLDialectBase, IdentifierMixin, ExpressionMixin, DDLColumnMixin, DDLTypeMixin, TableMixin, PartitionMixin):
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

    @DDLTypeMixin.handles(IntegerType)
    def format_data_type_integer(self, data_type: IntegerType) -> str:
        return "INTEGER"

    @DDLTypeMixin.handles(TextType)
    def format_data_type_text(self, data_type: TextType) -> str:
        return "TEXT"

    @DDLTypeMixin.handles(VarCharType)
    def format_data_type_varchar(self, data_type: VarCharType) -> str:
        return f"VARCHAR({data_type.length})" if data_type.length is not None else "VARCHAR"

    @DDLTypeMixin.handles(SmallIntType)
    def format_data_type_smallint(self, data_type: SmallIntType) -> str:
        return "SMALLINT"

    @DDLTypeMixin.handles(DecimalType)
    def format_data_type_decimal(self, data_type: DecimalType) -> str:
        if data_type.precision is not None and data_type.scale is not None:
            return f"DECIMAL({data_type.precision},{data_type.scale})"
        if data_type.precision is not None:
            return f"DECIMAL({data_type.precision})"
        return "DECIMAL"

    @DDLTypeMixin.handles(DateType)
    def format_data_type_date(self, data_type: DateType) -> str:
        return "DATE"

    @DDLTypeMixin.handles(TimestampType)
    def format_data_type_timestamp(self, data_type: TimestampType) -> str:
        return f"TIMESTAMP({data_type.precision})" if data_type.precision is not None else "TIMESTAMP"

    @DDLTypeMixin.handles(CustomType)
    def format_data_type_custom(self, data_type: CustomType) -> str:
        return data_type.raw


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
            ColumnDefinition(
                "id",
                IntegerType(),
                constraints=[
                    ColumnConstraint(ColumnConstraintType.PRIMARY_KEY),
                    ColumnConstraint(ColumnConstraintType.NOT_NULL),
                ],
            ),
            ColumnDefinition("name", VarCharType(255), constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]),
            ColumnDefinition("email", TextType()),
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
        columns = [ColumnDefinition("id", IntegerType(), constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY)])]

        create_table_expr = CreateTableExpression(dummy_dialect, table="products", columns=columns, if_not_exists=True)
        sql, params = create_table_expr.to_sql()

        assert "CREATE TABLE IF NOT EXISTS" in sql
        assert '"products"' in sql
        assert params == ()

    def test_create_temporary_table(self, dummy_dialect: DummyDialect):
        """Tests CREATE TEMPORARY TABLE statement."""
        columns = [
            ColumnDefinition(
                "session_id", VarCharType(50), constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]
            ),
            ColumnDefinition("data", TextType()),
        ]

        create_table_expr = CreateTableExpression(dummy_dialect, table="temp_sessions", columns=columns, temporary=True)
        sql, params = create_table_expr.to_sql()

        assert "CREATE TEMPORARY TABLE" in sql
        assert '"temp_sessions"' in sql
        assert params == ()

    def test_create_table_with_unique_constraint(self, dummy_dialect: DummyDialect):
        """Tests CREATE TABLE with UNIQUE column constraint."""
        columns = [
            ColumnDefinition("id", IntegerType(), constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY)]),
            ColumnDefinition("username", VarCharType(50), constraints=[ColumnConstraint(ColumnConstraintType.UNIQUE)]),
            ColumnDefinition("email", VarCharType(100), constraints=[ColumnConstraint(ColumnConstraintType.UNIQUE)]),
        ]

        create_table_expr = CreateTableExpression(dummy_dialect, table="users", columns=columns)
        sql, params = create_table_expr.to_sql()

        assert '"username" VARCHAR(50) UNIQUE' in sql
        assert '"email" VARCHAR(100) UNIQUE' in sql
        assert params == ()

    def test_create_table_with_default_constraint(self, dummy_dialect: DummyDialect):
        """Tests CREATE TABLE with DEFAULT column constraints."""
        columns = [
            ColumnDefinition("id", IntegerType(), constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY)]),
            ColumnDefinition("name", VarCharType(100)),
            ColumnDefinition(
                "status",
                VarCharType(20),
                constraints=[ColumnConstraint(ColumnConstraintType.DEFAULT, default_value="active")],
            ),
            ColumnDefinition(
                "created_at",
                TimestampType(),
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
            ColumnDefinition("id", IntegerType(), constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY)]),
            ColumnDefinition("name", VarCharType(100)),
            ColumnDefinition(
                "age", IntegerType(), constraints=[ColumnConstraint(ColumnConstraintType.CHECK, check_condition=age_check)]
            ),
        ]

        create_table_expr = CreateTableExpression(dummy_dialect, table="people", columns=columns)
        sql, params = create_table_expr.to_sql()

        assert '"age" INTEGER CHECK ("age" > ?)' in sql
        assert params == (0,)

    def test_create_table_with_foreign_key_constraint(self, dummy_dialect: DummyDialect):
        """Tests CREATE TABLE with FOREIGN KEY column constraints."""
        columns = [
            ColumnDefinition("id", IntegerType(), constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY)]),
            ColumnDefinition(
                "user_id",
                IntegerType(),
                constraints=[
                    ColumnConstraint(ColumnConstraintType.FOREIGN_KEY, foreign_key_reference=("users", ["id"]))
                ],
            ),
            ColumnDefinition("product_name", VarCharType(100)),
        ]

        create_table_expr = CreateTableExpression(dummy_dialect, table="orders", columns=columns)
        sql, params = create_table_expr.to_sql()

        assert '"user_id" INTEGER REFERENCES "users"("id")' in sql
        assert params == ()

    def test_create_table_with_table_level_constraints(self, dummy_dialect: DummyDialect):
        """Tests CREATE TABLE with table-level constraints."""
        columns = [
            ColumnDefinition("id", IntegerType()),
            ColumnDefinition("name", VarCharType(100)),
            ColumnDefinition("category_id", IntegerType()),
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
            ColumnDefinition("id", IntegerType(), constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY)]),
            ColumnDefinition("data", TextType()),
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
            ColumnDefinition("id", IntegerType(), constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY)]),
            ColumnDefinition("name", VarCharType(100)),
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

        columns: List[ColumnDefinition] = [  # For CREATE TABLE AS, columns list may be empty since they're defined by the query
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
            ColumnDefinition("id", IntegerType(), constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY)]),
            ColumnDefinition("email", VarCharType(100)),
            ColumnDefinition("created_at", TimestampType()),
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
            ColumnDefinition("id", IntegerType(), constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY)]),
            ColumnDefinition(
                "name", VarCharType(100), constraints=[ColumnConstraint(ColumnConstraintType.NOT_NULL)]
            ),  # Explicitly NOT NULL using constraint
            ColumnDefinition(
                "description", TextType(), constraints=[ColumnConstraint(ColumnConstraintType.NULL)]
            ),  # Explicitly allow NULLs using constraint
            ColumnDefinition("age", IntegerType()),  # No constraints - uses database default
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
                IntegerType(),
                constraints=[ColumnConstraint(ColumnConstraintType.PRIMARY_KEY)],
                comment="Primary identifier",
            ),
            ColumnDefinition("name", VarCharType(100), comment="User's display name"),
        ]

        create_table_expr = CreateTableExpression(dummy_dialect, table="users_with_comments", columns=columns)
        sql, params = create_table_expr.to_sql()

        assert '"users_with_comments"' in sql
        assert "COMMENT 'Primary identifier'" in sql
        assert "COMMENT 'User's display name'" in sql
        assert params == ()

    def test_create_table_partition_unsupported_by_dummy(self, dummy_dialect: DummyDialect):
        """Tests DummyDialect intentionally does not support table partitioning."""
        columns = [
            ColumnDefinition("id", IntegerType()),
            ColumnDefinition("created_date", DateType()),
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
            columns=[ColumnDefinition("tenant", TextType())],
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
        columns = [ColumnDefinition("id", IntegerType())]

        with pytest.raises(TypeError, match="partition must be a PartitionClause"):
            CreateTableExpression(
                dummy_dialect,
                table="invalid_partition",
                columns=columns,
                partition="RANGE",
            )

    def test_partition_clause_requires_strategy_enum(self, dummy_dialect: DummyDialect):
        """Tests PartitionClause requires a PartitionStrategy enum value."""
        with pytest.raises(TypeError, match="method must be a PartitionStrategy"):
            PartitionClause(
                dialect=dummy_dialect,
                method="RANGE",
                keys=[Column(dummy_dialect, "created_date")],
            )

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

    def test_partition_clause_requires_dict_dialect_options(self, dummy_dialect: DummyDialect):
        """Tests dialect_options must remain a structured mapping."""
        with pytest.raises(TypeError, match="dialect_options must be a dict"):
            PartitionClause(
                dialect=dummy_dialect,
                method=PartitionStrategy.RANGE,
                keys=[Column(dummy_dialect, "created_date")],
                dialect_options="columns_mode",
            )

    def test_partition_clause_copies_dialect_options(self, dummy_dialect: DummyDialect):
        """Tests dialect_options are copied to avoid external mutation."""
        options = {"backend_hint": "safe"}
        partition = PartitionClause(
            dialect=dummy_dialect,
            method=PartitionStrategy.RANGE,
            keys=[Column(dummy_dialect, "created_date")],
            dialect_options=options,
        )

        options["backend_hint"] = "changed"

        assert partition.dialect_options == {"backend_hint": "safe"}

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
        partition = PartitionClause(
            dialect=dialect,
            method=PartitionStrategy.RANGE,
            keys=[Column(dummy_dialect, "created_date")],
        )

        with pytest.raises(Exception, match="PartitionClause requires a dialect"):
            partition.to_sql()

    def test_create_table_with_inherits(self, dummy_dialect: DummyDialect):
        """Tests CREATE TABLE with INHERITS clause (PostgreSQL specific)."""
        columns = [ColumnDefinition("id", IntegerType()), ColumnDefinition("extra_field", VarCharType(50))]

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
                CustomType("SERIAL"),
                constraints=[
                    ColumnConstraint(ColumnConstraintType.PRIMARY_KEY),
                    ColumnConstraint(ColumnConstraintType.NOT_NULL),
                ],
            ),
            ColumnDefinition(
                "user_id",
                IntegerType(),
                constraints=[
                    ColumnConstraint(ColumnConstraintType.FOREIGN_KEY, foreign_key_reference=("users", ["id"]))
                ],
                comment="Reference to users table",
            ),
            ColumnDefinition(
                "amount",
                DecimalType(precision=10, scale=2),
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
                VarCharType(20),
                constraints=[
                    ColumnConstraint(ColumnConstraintType.DEFAULT, default_value="pending"),
                    ColumnConstraint(ColumnConstraintType.NOT_NULL),  # Use constraint instead of nullable flag
                ],
            ),
            ColumnDefinition(
                "created_at",
                TimestampType(),
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
                VarCharType(20),
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
                IntegerType(),
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
                IntegerType(),
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
