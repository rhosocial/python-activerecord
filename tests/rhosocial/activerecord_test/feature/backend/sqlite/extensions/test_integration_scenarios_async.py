# tests/rhosocial/activerecord_test/feature/backend/sqlite/extensions/test_integration_scenarios_async.py
"""Async twin of test_integration_scenarios.py: multi-extension integration scenarios run on AsyncSQLiteBackend."""
import json

import pytest
import pytest_asyncio
from rhosocial.activerecord.testsuite.utils import (
    requires_functions,
    requires_protocol,
)

from rhosocial.activerecord.backend.impl.sqlite import AsyncSQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.protocols import (
    SQLiteFTS5Support,
    SQLiteRTreeSupport,
)
from rhosocial.activerecord.backend.impl.sqlite.expression import (
    SQLiteFTS5CreateVirtualTable,
    SQLiteMatchPredicate,
    SQLiteRTreeCreateVirtualTable,
    SQLiteRTreeRangeQuery,
    SQLiteGeopolyCreateVirtualTable,
    SQLiteGeopolyContainsExpression,
    SQLiteGeopolyAreaExpression,
)
from rhosocial.activerecord.backend.expression import (
    Column,
    ColumnConstraint,
    ColumnConstraintType,
    ColumnDefinition,
    CreateTableExpression,
    FunctionCall,
    InsertExpression,
    JoinExpression,
    Literal,
    QueryExpression,
    SelectSource,
    Subquery,
    TableExpression,
    ValuesSource,
)
from rhosocial.activerecord.backend.expression.functions import (
    json_extract_text,
)
from rhosocial.activerecord.backend.impl.sqlite.functions import (
    json_extract as json_extract_func,
)
from rhosocial.activerecord.backend.options import ExecutionOptions
from rhosocial.activerecord.backend.schema import StatementType
from rhosocial.activerecord.backend.impl.sqlite.expression.types import SQLiteIntegerType, SQLiteTextType


# =============================================================================
# Scenario 1: Geo-tagged Document Management System
# =============================================================================

class TestGeoDocumentScenario:
    """Scenario: Geo-tagged document management with FTS5 + R-Tree + JSON1 (async)."""

    @pytest_asyncio.fixture
    async def backend(self):
        b = AsyncSQLiteBackend(database=":memory:")
        await b.connect()
        await b.introspect_and_adapt()
        yield b
        await b.disconnect()

    @requires_protocol(SQLiteFTS5Support, 'supports_fts5')
    @requires_protocol(SQLiteRTreeSupport, 'supports_rtree')
    @requires_functions('json_extract_text')
    @pytest.mark.asyncio
    async def test_full_scenario(self, backend):
        dialect = backend.dialect
        ddl = ExecutionOptions(stmt_type=StatementType.DDL)
        insert = ExecutionOptions(stmt_type=StatementType.INSERT)

        # --- Setup: FTS5 virtual table ---
        await backend.execute(
            *SQLiteFTS5CreateVirtualTable(
                dialect, table="docs_fts",
                columns=["title", "body", "author"]
            ).to_sql(),
            options=ddl
        )

        # --- Setup: R-Tree virtual table ---
        await backend.execute(
            *SQLiteRTreeCreateVirtualTable(
                dialect, table="doc_locations"
            ).to_sql(),
            options=ddl
        )

        # --- Setup: JSON metadata table ---
        await backend.execute(
            *CreateTableExpression(
                dialect, table="doc_meta",
                columns=[
                    ColumnDefinition("doc_id", SQLiteIntegerType(), constraints=[
                        ColumnConstraint(ColumnConstraintType.PRIMARY_KEY)
                    ]),
                    ColumnDefinition("extra", SQLiteTextType()),
                ]
            ).to_sql(),
            options=ddl
        )

        # --- Insert data into FTS + R-Tree + metadata ---
        docs = [
            (1, "Office Plans", "New office layout for downtown branch", "Alice",
             json.dumps({"floor": 5, "building": "Tower A"})),
            (2, "Park Proposal", "City park renovation proposal", "Bob",
             json.dumps({"budget": 500000})),
            (3, "Warehouse Report", "Quarterly warehouse inventory report", "Alice",
             json.dumps({"capacity": 10000})),
            (4, "Garden Notes", "Community garden planting schedule", "Carol",
             json.dumps({"season": "spring"})),
        ]

        await backend.execute(
            *InsertExpression(
                dialect, into="docs_fts",
                columns=["rowid", "title", "body", "author"],
                source=ValuesSource(dialect, [
                    [Literal(dialect, d[0]), Literal(dialect, d[1]),
                     Literal(dialect, d[2]), Literal(dialect, d[3])] for d in docs
                ])
            ).to_sql(),
            options=insert
        )
        await backend.execute(
            *InsertExpression(
                dialect, into="doc_locations",
                source=ValuesSource(dialect, [
                    [Literal(dialect, d[0]), Literal(dialect, 0),
                     Literal(dialect, 100), Literal(dialect, 0),
                     Literal(dialect, 100)] for d in docs
                ])
            ).to_sql(),
            options=insert
        )
        await backend.execute(
            *InsertExpression(
                dialect, into="doc_meta",
                columns=["doc_id", "extra"],
                source=ValuesSource(dialect, [
                    [Literal(dialect, d[0]), Literal(dialect, d[4])] for d in docs
                ])
            ).to_sql(),
            options=insert
        )

        # --- Text search via expression ---
        rows = await backend.fetch_all(
            *QueryExpression(
                dialect,
                select=[Column(dialect, "rowid"), Column(dialect, "title")],
                from_=TableExpression(dialect, "docs_fts"),
                where=(
                    SQLiteMatchPredicate(dialect, table="docs_fts", query="office")
                    & (Column(dialect, "author") == "Alice")
                )
            ).to_sql()
        )
        assert len(rows) == 1
        assert rows[0]["title"] == "Office Plans"

        # --- Spatial search via expression ---
        rows = await backend.fetch_all(
            *SQLiteRTreeRangeQuery(
                dialect, table="doc_locations",
                ranges=[(10, 50), (10, 50)]
            ).to_sql()
        )
        assert len(rows) == 4

        # --- Combined text + spatial search via expressions ---
        rows = await backend.fetch_all(
            *QueryExpression(
                dialect,
                select=[
                    Column(dialect, "rowid", table="docs_fts"),
                    Column(dialect, "title"),
                ],
                from_=[JoinExpression(
                    dialect,
                    left_table=TableExpression(dialect, "docs_fts"),
                    right_table=Subquery(
                        dialect,
                        SQLiteRTreeRangeQuery(
                            dialect, table="doc_locations",
                            ranges=[(0, 50), (0, 50)]
                        ),
                        alias="loc"
                    ),
                    condition=Column(dialect, "rowid", table="docs_fts")
                             == Column(dialect, "id", table="loc")
                )],
                where=SQLiteMatchPredicate(dialect, table="docs_fts", query="report")
            ).to_sql()
        )
        assert len(rows) >= 1

        # --- JSON metadata query via expression ---
        rows = await backend.fetch_all(
            *QueryExpression(
                dialect,
                select=[Column(dialect, "doc_id")],
                from_=TableExpression(dialect, "doc_meta"),
                where=json_extract_text(
                    dialect, Column(dialect, "extra"), "$.floor"
                ).is_not_null()
            ).to_sql()
        )
        assert len(rows) == 1
        assert rows[0]["doc_id"] == 1

        # --- Cleanup ---
        await backend.execute(
            *dialect.format_drop_virtual_table("docs_fts"), options=ddl
        )
        await backend.execute(
            *dialect.format_drop_virtual_table("doc_locations"), options=ddl
        )


# =============================================================================
# Scenario 2: Geofencing Alert System
# =============================================================================

class TestGeofencingScenario:
    """Scenario: Geofencing alert system with Geopoly + FTS5 + JSON1 (async)."""

    @pytest_asyncio.fixture
    async def backend(self):
        b = AsyncSQLiteBackend(database=":memory:")
        await b.connect()
        await b.introspect_and_adapt()
        yield b
        await b.disconnect()

    @pytest.mark.asyncio
    async def test_full_scenario(self, backend):
        dialect = backend.dialect
        if not dialect.supports_geopoly() or not dialect.supports_fts5():
            pytest.skip("Geopoly or FTS5 not available in this SQLite build")

        ddl = ExecutionOptions(stmt_type=StatementType.DDL)
        insert = ExecutionOptions(stmt_type=StatementType.INSERT)

        # --- Setup geopoly zones with extra columns ---
        await backend.execute(
            *SQLiteGeopolyCreateVirtualTable(
                dialect, table="zones",
                extra_columns=["name", "category", "config"]
            ).to_sql(),
            options=ddl
        )

        # Regular hexagon centered at (0,0) radius 3
        await backend.execute(
            *InsertExpression(
                dialect, into="zones",
                columns=["name", "category", "config", "_shape"],
                source=ValuesSource(dialect, [[
                    Literal(dialect, "central_park"),
                    Literal(dialect, "park"),
                    Literal(dialect, json.dumps({"alert": True, "priority": 1})),
                    FunctionCall(dialect, "geopoly_regular",
                        Literal(dialect, 0.0), Literal(dialect, 0.0),
                        Literal(dialect, 3.0), Literal(dialect, 6)),
                ]])
            ).to_sql(),
            options=insert
        )
        await backend.execute(
            *InsertExpression(
                dialect, into="zones",
                columns=["name", "category", "config", "_shape"],
                source=ValuesSource(dialect, [[
                    Literal(dialect, "north_zone"),
                    Literal(dialect, "industrial"),
                    Literal(dialect, json.dumps({"alert": False, "priority": 3})),
                    FunctionCall(dialect, "geopoly_regular",
                        Literal(dialect, 5.0), Literal(dialect, 5.0),
                        Literal(dialect, 2.0), Literal(dialect, 6)),
                ]])
            ).to_sql(),
            options=insert
        )

        # --- FTS5 for zone name search ---
        await backend.execute(
            *SQLiteFTS5CreateVirtualTable(
                dialect, table="zone_fts", columns=["name", "category"]
            ).to_sql(),
            options=ddl
        )

        # Sync content from zones to FTS (real app uses triggers)
        await backend.execute(
            *InsertExpression(
                dialect, into="zone_fts",
                columns=["rowid", "name", "category"],
                source=SelectSource(dialect, QueryExpression(
                    dialect,
                    select=[
                        Column(dialect, "rowid"),
                        Column(dialect, "name"),
                        Column(dialect, "category"),
                    ],
                    from_=TableExpression(dialect, "zones")
                ))
            ).to_sql(),
            options=insert
        )

        # --- Geofencing query: check if device at (1, 1) is inside any zone ---
        rows = await backend.fetch_all(
            *SQLiteGeopolyContainsExpression(
                dialect, table="zones", longitude=1.0, latitude=1.0
            ).to_sql()
        )
        assert len(rows) >= 1
        assert rows[0]["name"] == "central_park"

        # --- Point outside all zones ---
        rows = await backend.fetch_all(
            *SQLiteGeopolyContainsExpression(
                dialect, table="zones", longitude=100.0, latitude=100.0
            ).to_sql()
        )
        assert len(rows) == 0

        # --- Search zones with FTS5 ---
        rows = await backend.fetch_all(
            *QueryExpression(
                dialect,
                select=[Column(dialect, "name")],
                from_=TableExpression(dialect, "zone_fts"),
                where=SQLiteMatchPredicate(dialect, table="zone_fts", query="park")
            ).to_sql()
        )
        assert len(rows) == 1
        assert rows[0]["name"] == "central_park"

        # --- Combined: search zone by text + geofence check ---
        rows = await backend.fetch_all(
            *QueryExpression(
                dialect,
                select=[
                    Column(dialect, "name", table="z"),
                    Column(dialect, "category", table="z"),
                ],
                from_=[JoinExpression(
                    dialect,
                    left_table=TableExpression(dialect, "zones", alias="z"),
                    right_table=TableExpression(dialect, "zone_fts", alias="f"),
                    condition=Column(dialect, "rowid", table="z")
                             == Column(dialect, "rowid", table="f")
                )],
                where=(
                    SQLiteMatchPredicate(dialect, table="zone_fts", query="park")
                    & (FunctionCall(dialect, "geopoly_contains_point",
                        Column(dialect, "_shape", table="z"),
                        Literal(dialect, 1.0), Literal(dialect, 1.0)
                      ) != 0)
                )
            ).to_sql()
        )
        assert len(rows) == 1
        assert rows[0]["name"] == "central_park"

        # --- Area calculation via expression ---
        rows = await backend.fetch_all(
            *SQLiteGeopolyAreaExpression(
                dialect, table="zones"
            ).to_sql()
        )
        assert len(rows) == 2
        for row in rows:
            assert row["area"] > 0

        # --- Cleanup ---
        await backend.execute(
            *dialect.format_drop_virtual_table("zones"), options=ddl
        )
        await backend.execute(
            *dialect.format_drop_virtual_table("zone_fts"), options=ddl
        )


# =============================================================================
# Scenario 3: Spatial Data Catalog
# =============================================================================

class TestSpatialCatalogScenario:
    """Scenario: Spatial data catalog with R-Tree + FTS5 + JSON1 (async)."""

    @pytest_asyncio.fixture
    async def backend(self):
        b = AsyncSQLiteBackend(database=":memory:")
        await b.connect()
        await b.introspect_and_adapt()
        yield b
        await b.disconnect()

    @pytest.mark.asyncio
    async def test_full_scenario(self, backend):
        dialect = backend.dialect
        if not dialect.supports_rtree() or not dialect.supports_fts5():
            pytest.skip("R-Tree or FTS5 not available")

        ddl = ExecutionOptions(stmt_type=StatementType.DDL)
        insert = ExecutionOptions(stmt_type=StatementType.INSERT)

        # --- Main data table ---
        await backend.execute(
            *CreateTableExpression(
                dialect, table="features",
                columns=[
                    ColumnDefinition("id", SQLiteIntegerType(), constraints=[
                        ColumnConstraint(ColumnConstraintType.PRIMARY_KEY)
                    ]),
                    ColumnDefinition("name", SQLiteTextType()),
                    ColumnDefinition("description", SQLiteTextType()),
                    ColumnDefinition("props", SQLiteTextType()),
                ]
            ).to_sql(),
            options=ddl
        )

        # --- R-Tree spatial index via expression ---
        await backend.execute(
            *SQLiteRTreeCreateVirtualTable(
                dialect, table="features_rtree"
            ).to_sql(),
            options=ddl
        )

        # --- FTS5 text index (standalone) via expression ---
        await backend.execute(
            *SQLiteFTS5CreateVirtualTable(
                dialect, table="features_fts",
                columns=["name", "description"]
            ).to_sql(),
            options=ddl
        )

        # --- Insert data ---
        features = [
            (1, "Central Hospital", "Main city hospital with emergency services",
             json.dumps({"beds": 500, "floors": 10}), 0, 100, 0, 100),
            (2, "North Library", "Public library with digital media center",
             json.dumps({"books": 50000, "computers": 30}), 200, 300, 200, 300),
            (3, "East Park", "Large urban park with sports facilities",
             json.dumps({"area_acres": 50, "has_lake": True}), 0, 100, 400, 500),
            (4, "South Market", "Farmers market open weekends",
             json.dumps({"stalls": 200, "organic": True}), 400, 500, 0, 100),
        ]

        await backend.execute(
            *InsertExpression(
                dialect, into="features_fts",
                columns=["rowid", "name", "description"],
                source=ValuesSource(dialect, [
                    [Literal(dialect, f[0]), Literal(dialect, f[1]),
                     Literal(dialect, f[2])] for f in features
                ])
            ).to_sql(),
            options=insert
        )
        await backend.execute(
            *InsertExpression(
                dialect, into="features_rtree",
                source=ValuesSource(dialect, [
                    [Literal(dialect, f[0]), Literal(dialect, f[4]),
                     Literal(dialect, f[5]), Literal(dialect, f[6]),
                     Literal(dialect, f[7])] for f in features
                ])
            ).to_sql(),
            options=insert
        )

        # --- FTS5 search: find features matching "hospital" via expression ---
        rows = await backend.fetch_all(
            *QueryExpression(
                dialect,
                select=[Column(dialect, "rowid"), Column(dialect, "name")],
                from_=TableExpression(dialect, "features_fts"),
                where=SQLiteMatchPredicate(dialect, table="features_fts", query="hospital")
            ).to_sql()
        )
        assert len(rows) == 1
        assert rows[0]["name"] == "Central Hospital"

        # --- Spatial search via expression ---
        rows = await backend.fetch_all(
            *SQLiteRTreeRangeQuery(
                dialect, table="features_rtree",
                ranges=[(10, 100), (10, 100)]
            ).to_sql()
        )
        assert len(rows) == 1
        assert rows[0]["id"] == 1

        # --- Combined FTS5 + spatial + JSON filter via expressions ---
        await backend.execute(
            *CreateTableExpression(
                dialect, table="feature_props",
                columns=[
                    ColumnDefinition("feature_id", SQLiteIntegerType(), constraints=[
                        ColumnConstraint(ColumnConstraintType.PRIMARY_KEY)
                    ]),
                    ColumnDefinition("props", SQLiteTextType()),
                ]
            ).to_sql(),
            options=ddl
        )
        await backend.execute(
            *InsertExpression(
                dialect, into="feature_props",
                columns=["feature_id", "props"],
                source=ValuesSource(dialect, [
                    [Literal(dialect, f[0]), Literal(dialect, f[3])] for f in features
                ])
            ).to_sql(),
            options=insert
        )

        rows = await backend.fetch_all(
            *QueryExpression(
                dialect,
                select=[
                    Column(dialect, "rowid", table="features_fts"),
                    Column(dialect, "name"),
                    Column(dialect, "props", table="feature_props"),
                ],
                from_=[JoinExpression(
                    dialect,
                    left_table=JoinExpression(
                        dialect,
                        left_table=TableExpression(dialect, "features_fts"),
                        right_table=Subquery(
                            dialect,
                            SQLiteRTreeRangeQuery(
                                dialect, table="features_rtree",
                                ranges=[(100, 600), (100, 600)]
                            ),
                            alias="rt"
                        ),
                        condition=Column(dialect, "rowid", table="features_fts")
                                 == Column(dialect, "id", table="rt")
                    ),
                    right_table=TableExpression(dialect, "feature_props"),
                    condition=Column(dialect, "rowid", table="features_fts")
                             == Column(dialect, "feature_id", table="feature_props")
                )],
                where=(
                    SQLiteMatchPredicate(dialect, table="features_fts", query="park")
                    & (json_extract_func(
                        dialect,
                        Column(dialect, "props", table="feature_props"),
                        "$.has_lake"
                      ) == 1)
                )
            ).to_sql()
        )
        assert len(rows) == 1
        assert rows[0]["name"] == "East Park"
        props = json.loads(rows[0]["props"])
        assert props["has_lake"] is True

        # --- Cleanup ---
        for tbl in ["features_rtree", "features_fts"]:
            await backend.execute(
                *dialect.format_drop_virtual_table(tbl), options=ddl
            )
