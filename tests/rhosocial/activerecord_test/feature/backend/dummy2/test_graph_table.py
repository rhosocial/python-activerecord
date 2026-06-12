# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_graph_table.py
"""
Tests for GRAPH_TABLE query and PGQ DDL expression building blocks.

Tests expression construction using DummyDialect; actual SQL execution
requires a database with PGQ support (PostgreSQL 19+ or Oracle 23c+).
"""
import pytest
from rhosocial.activerecord.backend.dialect.protocols import GraphTableSupport
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.expression.graph import (
    GraphVertex, GraphEdge, GraphEdgeDirection, MatchClause,
    GraphColumn, ColumnsClause, GraphTableExpression,
    TablePropertiesClause, VertexTable, EdgeTable,
    CreatePropertyGraphExpression, DropPropertyGraphExpression,
    AlterPropertyGraphExpression,
)
from rhosocial.activerecord.backend.expression.query_parts import WhereClause
from rhosocial.activerecord.backend.expression.core import Column, Literal
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect


class TestGraphColumn:
    """Tests for GraphColumn (individual column in COLUMNS clause)."""

    def test_creation(self):
        col = GraphColumn("p", "name")
        assert col.variable == "p"
        assert col.property_name == "name"
        assert col.alias is None

    def test_creation_with_alias(self):
        col = GraphColumn("p", "name", "person_name")
        assert col.alias == "person_name"


class TestColumnsClause:
    """Tests for ColumnsClause."""

    def test_empty(self, dummy_dialect: DummyDialect):
        clause = ColumnsClause(dummy_dialect)
        sql, params = clause.to_sql()
        assert sql == "COLUMNS ()"

    def test_single_column(self, dummy_dialect: DummyDialect):
        clause = ColumnsClause(dummy_dialect, GraphColumn("p", "name"))
        sql, params = clause.to_sql()
        assert "COLUMNS" in sql
        assert "p" in sql and "name" in sql

    def test_multiple_columns(self, dummy_dialect: DummyDialect):
        clause = ColumnsClause(dummy_dialect,
                               GraphColumn("p", "name", "person_name"),
                               GraphColumn("p", "age"))
        sql, params = clause.to_sql()
        assert "AS" in sql
        assert "person_name" in sql


class TestGraphTableExpression:
    """Tests for GraphTableExpression."""

    def test_basic(self, dummy_dialect: DummyDialect):
        v = GraphVertex(dummy_dialect, "p", "person")
        cols = ColumnsClause(dummy_dialect, GraphColumn("p", "name"))
        match = MatchClause(dummy_dialect, v)
        gt = GraphTableExpression(dummy_dialect, "my_graph", match, cols)
        sql, params = gt.to_sql()
        assert "GRAPH_TABLE" in sql
        assert "my_graph" in sql
        assert "MATCH" in sql
        assert "COLUMNS" in sql

    def test_with_pattern(self, dummy_dialect: DummyDialect):
        a = GraphVertex(dummy_dialect, "a", "person")
        e = GraphEdge(dummy_dialect, "e", "knows", GraphEdgeDirection.RIGHT)
        b = GraphVertex(dummy_dialect, "b", "person")
        cols = ColumnsClause(dummy_dialect,
                             GraphColumn("a", "name", "person_a"),
                             GraphColumn("b", "name", "person_b"))
        match = MatchClause(dummy_dialect, a, e, b)
        gt = GraphTableExpression(dummy_dialect, "g", match, cols)
        sql, params = gt.to_sql()
        assert "GRAPH_TABLE" in sql
        assert "MATCH" in sql
        assert "COLUMNS" in sql

    def test_with_where(self, dummy_dialect: DummyDialect):
        where = WhereClause(dummy_dialect,
                            condition=Column(dummy_dialect, "age") > Literal(dummy_dialect, 18))
        v = GraphVertex(dummy_dialect, "p", "person", where=where)
        cols = ColumnsClause(dummy_dialect, GraphColumn("p", "name"))
        match = MatchClause(dummy_dialect, v)
        gt = GraphTableExpression(dummy_dialect, "g", match, cols)
        sql, params = gt.to_sql()
        assert "WHERE" in sql
        assert "age" in sql


class TestTablePropertiesClause:
    """Tests for TablePropertiesClause."""

    def test_all_columns(self, dummy_dialect: DummyDialect):
        clause = TablePropertiesClause(dummy_dialect)
        sql, params = clause.to_sql()
        assert sql == "PROPERTIES ALL COLUMNS"

    def test_none(self, dummy_dialect: DummyDialect):
        clause = TablePropertiesClause(dummy_dialect, columns=[])
        sql, params = clause.to_sql()
        assert sql == "PROPERTIES NONE"

    def test_specific(self, dummy_dialect: DummyDialect):
        clause = TablePropertiesClause(dummy_dialect, columns=["id", "name"])
        sql, params = clause.to_sql()
        assert sql == 'PROPERTIES ("id", "name")'


class TestVertexTable:
    """Tests for VertexTable."""

    def test_minimal(self, dummy_dialect: DummyDialect):
        vt = VertexTable(dummy_dialect, "person")
        sql, params = vt.to_sql()
        assert sql == '"person"'

    def test_with_labels(self, dummy_dialect: DummyDialect):
        vt = VertexTable(dummy_dialect, "person", labels=["Person"])
        sql, params = vt.to_sql()
        assert "LABEL" in sql

    def test_with_keys(self, dummy_dialect: DummyDialect):
        vt = VertexTable(dummy_dialect, "person", key_columns=["id"])
        sql, params = vt.to_sql()
        assert "KEY" in sql

    def test_with_properties(self, dummy_dialect: DummyDialect):
        props = TablePropertiesClause(dummy_dialect, columns=["id", "name"])
        vt = VertexTable(dummy_dialect, "person", properties=props)
        sql, params = vt.to_sql()
        assert "PROPERTIES" in sql


class TestEdgeTable:
    """Tests for EdgeTable."""

    def test_minimal(self, dummy_dialect: DummyDialect):
        et = EdgeTable(dummy_dialect, "knows", ["pid"], ["fid"])
        sql, params = et.to_sql()
        assert "SOURCE KEY" in sql
        assert "DESTINATION KEY" in sql

    def test_with_references(self, dummy_dialect: DummyDialect):
        et = EdgeTable(dummy_dialect, "knows", ["pid"], ["fid"],
                       references_source=("people", ["id"]),
                       references_destination=("people", ["id"]))
        sql, params = et.to_sql()
        assert "REFERENCES" in sql

    def test_with_labels(self, dummy_dialect: DummyDialect):
        et = EdgeTable(dummy_dialect, "knows", ["pid"], ["fid"], labels=["Knows"])
        sql, params = et.to_sql()
        assert "LABEL" in sql

    def test_with_properties(self, dummy_dialect: DummyDialect):
        props = TablePropertiesClause(dummy_dialect, columns=["since"])
        et = EdgeTable(dummy_dialect, "knows", ["pid"], ["fid"], properties=props)
        sql, params = et.to_sql()
        assert "PROPERTIES" in sql


class TestCreatePropertyGraphExpression:
    """Tests for CreatePropertyGraphExpression."""

    def test_basic(self, dummy_dialect: DummyDialect):
        vt = VertexTable(dummy_dialect, "person", labels=["Person"])
        et = EdgeTable(dummy_dialect, "knows", ["pid"], ["fid"], labels=["Knows"])
        expr = CreatePropertyGraphExpression(dummy_dialect, "g", [vt], [et])
        sql, params = expr.to_sql()
        assert "CREATE PROPERTY GRAPH" in sql
        assert "VERTEX" not in sql  # default format uses parentheses
        assert "EDGE" not in sql

    def test_if_not_exists(self, dummy_dialect: DummyDialect):
        vt = VertexTable(dummy_dialect, "person")
        expr = CreatePropertyGraphExpression(dummy_dialect, "g", [vt], if_not_exists=True)
        sql, params = expr.to_sql()
        assert "IF NOT EXISTS" in sql

    def test_no_edges(self, dummy_dialect: DummyDialect):
        vt = VertexTable(dummy_dialect, "person")
        expr = CreatePropertyGraphExpression(dummy_dialect, "g", [vt])
        sql, params = expr.to_sql()
        assert "CREATE PROPERTY GRAPH" in sql


class TestDropPropertyGraphExpression:
    """Tests for DropPropertyGraphExpression."""

    def test_basic(self, dummy_dialect: DummyDialect):
        expr = DropPropertyGraphExpression(dummy_dialect, "g")
        sql, params = expr.to_sql()
        assert sql == 'DROP PROPERTY GRAPH "g"'

    def test_if_exists(self, dummy_dialect: DummyDialect):
        expr = DropPropertyGraphExpression(dummy_dialect, "g", if_exists=True)
        sql, params = expr.to_sql()
        assert "IF EXISTS" in sql

    def test_cascade(self, dummy_dialect: DummyDialect):
        expr = DropPropertyGraphExpression(dummy_dialect, "g", cascade=True)
        sql, params = expr.to_sql()
        assert "CASCADE" in sql


class TestAlterPropertyGraphExpression:
    """Tests for AlterPropertyGraphExpression."""

    def test_basic(self, dummy_dialect: DummyDialect):
        vt = VertexTable(dummy_dialect, "person")
        expr = AlterPropertyGraphExpression(dummy_dialect, "g", "ADD", "VERTEX TABLES",
                                            vertex_tables=[vt])
        sql, params = expr.to_sql()
        assert "ALTER PROPERTY GRAPH" in sql
        assert "ADD" in sql
        assert "VERTEX" in sql.upper()

    def test_with_edge_tables(self, dummy_dialect: DummyDialect):
        et = EdgeTable(dummy_dialect, "knows", ["pid"], ["fid"])
        expr = AlterPropertyGraphExpression(dummy_dialect, "g", "DROP", "EDGE TABLES",
                                            edge_tables=[et])
        sql, params = expr.to_sql()
        assert 'DROP' in sql
        assert 'EDGE' in sql.upper()
        assert '"knows"' in sql

    def test_with_both_tables(self, dummy_dialect: DummyDialect):
        vt = VertexTable(dummy_dialect, "person")
        et = EdgeTable(dummy_dialect, "knows", ["pid"], ["fid"])
        expr = AlterPropertyGraphExpression(dummy_dialect, "g", "ADD", "TABLES",
                                            vertex_tables=[vt], edge_tables=[et])
        sql, params = expr.to_sql()
        assert '"person"' in sql
        assert '"knows"' in sql


class TestEdgeAbbreviatedSyntax:
    """Tests for abbreviated edge syntax."""

    def test_anonymous_edge(self, dummy_dialect: DummyDialect):
        edge = GraphEdge(dummy_dialect, direction=GraphEdgeDirection.RIGHT)
        sql, params = edge.to_sql()
        assert sql == "-[]->"

    def test_variable_only_edge(self, dummy_dialect: DummyDialect):
        edge = GraphEdge(dummy_dialect, variable="e", direction=GraphEdgeDirection.RIGHT)
        sql, params = edge.to_sql()
        assert sql == "-[e]->"

    def test_full_edge(self, dummy_dialect: DummyDialect):
        edge = GraphEdge(dummy_dialect, variable="e", table="knows",
                         direction=GraphEdgeDirection.RIGHT)
        sql, params = edge.to_sql()
        assert sql == '-[e IS "knows"]->'


class TestVertexWithWhereClause:
    """Tests for vertex element WHERE."""

    def test_vertex_with_where(self, dummy_dialect: DummyDialect):
        where = WhereClause(dummy_dialect,
                            condition=Column(dummy_dialect, "status") == Literal(dummy_dialect, "active"))
        v = GraphVertex(dummy_dialect, "p", "person", where=where)
        sql, params = v.to_sql()
        assert "WHERE" in sql
        assert "status" in sql

    def test_vertex_without_where(self, dummy_dialect: DummyDialect):
        v = GraphVertex(dummy_dialect, "p", "person")
        sql, params = v.to_sql()
        assert "WHERE" not in sql


class TestGraphTableMixinProtocol:
    """Tests protocol-level methods that are not exercised by expression to_sql()."""

    def test_format_graph_columns_clause(self, dummy_dialect: DummyDialect):
        cols = ColumnsClause(dummy_dialect, GraphColumn("p", "name", "person_name"))
        sql, params = dummy_dialect.format_graph_columns_clause(cols)
        assert "COLUMNS" in sql
        assert "p" in sql
        assert "person_name" in sql


class TestUnsupportedDDL:
    """Tests that DDL formatting raises UnsupportedFeatureError when supports_graph_table() is False."""

    @pytest.fixture
    def unsupported_dialect(self):
        """A dialect that explicitly denies PGQ DDL support to exercise error paths."""
        class _UnsupportedDialect(DummyDialect):
            def supports_graph_table(self):
                return False
        return _UnsupportedDialect()

    def test_format_table_properties_clause_unsupported(self, unsupported_dialect):
        clause = TablePropertiesClause(unsupported_dialect, columns=["id"])
        with pytest.raises(UnsupportedFeatureError):
            clause.to_sql()

    def test_format_vertex_table_unsupported(self, unsupported_dialect):
        vt = VertexTable(unsupported_dialect, "person")
        with pytest.raises(UnsupportedFeatureError):
            vt.to_sql()

    def test_format_edge_table_unsupported(self, unsupported_dialect):
        et = EdgeTable(unsupported_dialect, "knows", ["pid"], ["fid"])
        with pytest.raises(UnsupportedFeatureError):
            et.to_sql()

    def test_edge_table_no_references(self, dummy_dialect: DummyDialect):
        """EdgeTable without REFERENCES (SOURCE/DESTINATION KEY only)."""
        et = EdgeTable(dummy_dialect, "knows", ["pid"], ["fid"])
        sql, params = et.to_sql()
        assert 'SOURCE KEY ("pid")' in sql
        assert 'DESTINATION KEY ("fid")' in sql
        assert "REFERENCES" not in sql

    def test_edge_table_with_key_columns(self, dummy_dialect: DummyDialect):
        """EdgeTable with explicit KEY."""
        et = EdgeTable(dummy_dialect, "knows", ["pid"], ["fid"],
                       key_columns=["id"],
                       references_source=("people", ["id"]),
                       references_destination=("people", ["id"]))
        sql, params = et.to_sql()
        assert 'KEY ("id")' in sql

    def test_create_property_graph_unsupported(self, unsupported_dialect):
        vt = VertexTable(unsupported_dialect, "person")
        expr = CreatePropertyGraphExpression(unsupported_dialect, "g", [vt])
        with pytest.raises(UnsupportedFeatureError):
            expr.to_sql()

    def test_drop_property_graph_unsupported(self, unsupported_dialect):
        expr = DropPropertyGraphExpression(unsupported_dialect, "g")
        with pytest.raises(UnsupportedFeatureError):
            expr.to_sql()

    def test_alter_property_graph_unsupported(self, unsupported_dialect):
        vt = VertexTable(unsupported_dialect, "person")
        expr = AlterPropertyGraphExpression(unsupported_dialect, "g", "ADD", "VERTEX TABLES",
                                            vertex_tables=[vt])
        with pytest.raises(UnsupportedFeatureError):
            expr.to_sql()

    def test_graph_table_expression_unsupported(self, unsupported_dialect):
        v = GraphVertex(unsupported_dialect, "p", "person")
        cols = ColumnsClause(unsupported_dialect, GraphColumn("p", "name"))
        m = MatchClause(unsupported_dialect, v)
        gt = GraphTableExpression(unsupported_dialect, "g", m, cols)
        with pytest.raises(UnsupportedFeatureError):
            gt.to_sql()
