from rhosocial.activerecord.backend.expression.statements import (
    ColumnNotNullConstraint,
    ColumnPrimaryKeyConstraint,
)
from .....expression.objects import Table
from rhosocial.activerecord.backend.expression.predicates import (  # noqa: E402
    LikeOperator,
    LikePredicate,
    InPredicate,
    BetweenPredicate,
    IsNullPredicate,
    LogicalPredicate,
)
from rhosocial.activerecord.backend.expression.core import Literal
from rhosocial.activerecord.backend.expression.sources import NamedRelationRef
from rhosocial.activerecord.backend.expression import (
    QueryStatement,
    Column,
    WhereClause,
)
from rhosocial.activerecord.backend.expression.statements import ColumnDefinition, ColumnConstraint
from rhosocial.activerecord.backend.expression import (  # noqa: E402
    CreateTableStatement,
    InsertStatement,
    ValuesSource,
)
from rhosocial.activerecord.backend.schema import StatementType
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from rhosocial.activerecord.backend.expression.types import FloatType, IntegerType, TextType
"""
Complex predicates: LIKE, IN, BETWEEN, IS NULL.
"""

# ============================================================
# SECTION: Setup (necessary for execution, reference only)
# ============================================================

config = SQLiteConnectionConfig(database=":memory:")
backend = SQLiteBackend(config)
dialect = backend.dialect


create_table = CreateTableStatement(
    dialect=dialect,
    table_name="products",
    columns=[
        ColumnDefinition(dialect, 
            "id",
            IntegerType(),
            constraints=[
                ColumnConstraint(dialect, branch=ColumnPrimaryKeyConstraint(dialect, is_auto_increment=True)),
                ColumnConstraint(dialect, branch=ColumnNotNullConstraint(dialect)),
            ],
        ),
        ColumnDefinition(dialect, 
            "name",
            TextType(),
            constraints=[
                ColumnConstraint(dialect, branch=ColumnNotNullConstraint(dialect)),
            ],
        ),
        ColumnDefinition(dialect, "price", FloatType()),
        ColumnDefinition(dialect, "category", TextType()),
        ColumnDefinition(dialect, "description", TextType()),
    ],
    if_not_exists=True,
)
sql, params = create_table.to_sql()
backend.execute(sql, params)

products_data = [
    ("Apple", 1.5, "Fruit", "Fresh red apple"),
    ("Banana", 0.8, "Fruit", None),
    ("Carrot", 0.5, "Vegetable", "Organic carrot"),
    ("Orange", 2.0, "Fruit", "Sweet orange"),
    ("Broccoli", 1.2, "Vegetable", None),
]
for row in products_data:
    insert_expr = InsertStatement(
        dialect=dialect,
        into=Table(dialect, 'products'),
        columns=["name", "price", "category", "description"],
        source=ValuesSource(dialect, [[Literal(dialect, v) for v in row]]),
    )
    sql, params = insert_expr.to_sql()
    backend.execute(sql, params)

# ============================================================
# SECTION: Business Logic (the pattern to learn)
# ============================================================

# Combine multiple predicates: (LIKE pattern) AND (IN list) AND (BETWEEN range) AND (IS NOT NULL)
# The operator is the *word*, not the SQL keyword: the keyword is a spelling
# the dialect owns and never reaches the artifact.
like_pred = LikePredicate(
    dialect, LikeOperator.LIKE, Column(dialect, "name"), Literal(dialect, "%a%")
)
in_pred = InPredicate(dialect, Column(dialect, "category"), Literal(dialect, ("Fruit", "Vegetable")))
between_pred = BetweenPredicate(dialect, Column(dialect, "price"), Literal(dialect, 0.5), Literal(dialect, 2.0))
not_null_pred = IsNullPredicate(dialect, Column(dialect, "description"), is_not=True)

combined_pred = LogicalPredicate(dialect, "AND", like_pred, in_pred, between_pred, not_null_pred)

query = QueryStatement(
    dialect=dialect,
    select=[
        Column(dialect, "name"),
        Column(dialect, "price"),
        Column(dialect, "category"),
    ],
    from_=NamedRelationRef(dialect, Table(dialect, "products")),
    where=WhereClause(dialect, condition=combined_pred),
)

sql, params = query.to_sql()
print(f"SQL: {sql}")
print(f"Params: {params}")

# ============================================================
# SECTION: Execution (run the expression)
# ============================================================
options = ExecutionOptions(stmt_type=StatementType.DQL)
result = backend.execute(sql, params, options=options)
print(f"Rows returned: {len(result.data) if result.data else 0}")
for row in result.data or []:
    print(f"  {row}")

# ============================================================
# SECTION: Teardown (necessary for execution, reference only)
# ============================================================
backend.disconnect()
