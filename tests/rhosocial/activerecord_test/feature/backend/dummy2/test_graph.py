# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_graph.py
"""
Tests for the SQL Graph Query (MATCH) expression building blocks in graph.py
according to SQL 2023 (ISO/IEC 9075-16) standard.
"""
import pytest
from rhosocial.activerecord.backend.expression.graph import (
    GraphVertex, GraphEdge, GraphEdgeDirection, MatchClause
)
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect


class TestGraphVertex:
    """Tests for GraphVertex class."""

    def test_vertex_creation(self, dummy_dialect: DummyDialect):
        """Test creating a GraphVertex object."""
        vertex = GraphVertex(dummy_dialect, "n", "Person")
        assert vertex.variable == "n"
        assert vertex.table == "Person"
        assert vertex.dialect is dummy_dialect

    def test_vertex_to_sql_basic(self, dummy_dialect: DummyDialect):
        """Test generating SQL for a basic vertex."""
        vertex = GraphVertex(dummy_dialect, "n", "Person")
        sql, params = vertex.to_sql()
        assert sql == '(n IS "Person")'
        assert params == ()

    def test_vertex_to_sql_with_different_variable_and_table(self, dummy_dialect: DummyDialect):
        """Test generating SQL with different variable and table names."""
        vertex = GraphVertex(dummy_dialect, "customer", "Customer")
        sql, params = vertex.to_sql()
        assert sql == '(customer IS "Customer")'
        assert params == ()

    def test_vertex_to_sql_with_special_characters(self, dummy_dialect: DummyDialect):
        """Test generating SQL with special characters that need escaping."""
        vertex = GraphVertex(dummy_dialect, "v1", "My Table")
        sql, params = vertex.to_sql()
        # The exact escaping depends on the dialect's format_identifier method
        assert "v1 IS" in sql
        assert params == ()


class TestGraphEdge:
    """Tests for GraphEdge class."""

    def test_edge_creation(self, dummy_dialect: DummyDialect):
        """Test creating a GraphEdge object."""
        edge = GraphEdge(dummy_dialect, "e", "KNOWS", GraphEdgeDirection.RIGHT)
        assert edge.variable == "e"
        assert edge.table == "KNOWS"
        assert edge.direction == GraphEdgeDirection.RIGHT
        assert edge.dialect is dummy_dialect

    def test_edge_to_sql_right_direction(self, dummy_dialect: DummyDialect):
        """Test generating SQL for a right-directed edge."""
        edge = GraphEdge(dummy_dialect, "e", "KNOWS", GraphEdgeDirection.RIGHT)
        sql, params = edge.to_sql()
        assert sql == '-[e IS "KNOWS"]->'

    def test_edge_to_sql_left_direction(self, dummy_dialect: DummyDialect):
        """Test generating SQL for a left-directed edge."""
        edge = GraphEdge(dummy_dialect, "e", "KNOWS", GraphEdgeDirection.LEFT)
        sql, params = edge.to_sql()
        assert sql == '<-[e IS "KNOWS"]-'

    def test_edge_to_sql_any_direction(self, dummy_dialect: DummyDialect):
        """Test generating SQL for a bidirectional edge."""
        edge = GraphEdge(dummy_dialect, "e", "KNOWS", GraphEdgeDirection.ANY)
        sql, params = edge.to_sql()
        assert sql == '<-[e IS "KNOWS"]->'

    def test_edge_to_sql_none_direction(self, dummy_dialect: DummyDialect):
        """Test generating SQL for an undirected edge."""
        edge = GraphEdge(dummy_dialect, "e", "KNOWS", GraphEdgeDirection.NONE)
        sql, params = edge.to_sql()
        assert sql == '-[e IS "KNOWS"]-'

    def test_edge_with_different_variables_and_tables(self, dummy_dialect: DummyDialect):
        """Test generating SQL with different variable and table names."""
        edge = GraphEdge(dummy_dialect, "rel", "Follows", GraphEdgeDirection.RIGHT)
        sql, params = edge.to_sql()
        assert sql == '-[rel IS "Follows"]->'


class TestMatchClause:
    """Tests for MatchClause class."""

    def test_match_clause_creation(self, dummy_dialect: DummyDialect):
        """Test creating a MatchClause object."""
        vertex = GraphVertex(dummy_dialect, "n", "Person")
        edge = GraphEdge(dummy_dialect, "e", "KNOWS", GraphEdgeDirection.RIGHT)
        
        match_clause = MatchClause(dummy_dialect, vertex, edge)
        assert len(match_clause.path) == 2
        assert match_clause.path[0] is vertex
        assert match_clause.path[1] is edge
        assert match_clause.dialect is dummy_dialect

    def test_match_clause_with_single_vertex(self, dummy_dialect: DummyDialect):
        """Test generating SQL for a MATCH clause with a single vertex."""
        vertex = GraphVertex(dummy_dialect, "n", "Person")
        match_clause = MatchClause(dummy_dialect, vertex)
        sql, params = match_clause.to_sql()
        # The exact format depends on the dialect's format_match_clause implementation
        assert "MATCH" in sql.upper()
        assert "n IS" in sql
        assert params == ()

    def test_match_clause_with_vertex_and_edge(self, dummy_dialect: DummyDialect):
        """Test generating SQL for a MATCH clause with vertex and edge."""
        vertex = GraphVertex(dummy_dialect, "person", "Person")
        edge = GraphEdge(dummy_dialect, "knows", "KNOWS", GraphEdgeDirection.RIGHT)
        vertex2 = GraphVertex(dummy_dialect, "friend", "Person")
        
        match_clause = MatchClause(dummy_dialect, vertex, edge, vertex2)
        sql, params = match_clause.to_sql()
        # The exact format depends on the dialect's format_match_clause implementation
        assert "MATCH" in sql.upper()
        assert "person IS" in sql
        assert "knows IS" in sql
        assert "friend IS" in sql

    def test_match_clause_with_multiple_edges(self, dummy_dialect: DummyDialect):
        """Test generating SQL for a MATCH clause with multiple edges."""
        v1 = GraphVertex(dummy_dialect, "a", "Account")
        e1 = GraphEdge(dummy_dialect, "owns", "OWNS", GraphEdgeDirection.LEFT)
        v2 = GraphVertex(dummy_dialect, "p", "Person")
        e2 = GraphEdge(dialect=dummy_dialect, variable="transfers", table="TRANSFER", direction=GraphEdgeDirection.RIGHT)
        v3 = GraphVertex(dummy_dialect, "b", "Account")
        
        match_clause = MatchClause(dummy_dialect, v1, e1, v2, e2, v3)
        sql, params = match_clause.to_sql()
        # The exact format depends on the dialect's format_match_clause implementation
        assert "MATCH" in sql.upper()
        assert "a IS" in sql
        assert "owns IS" in sql
        assert "p IS" in sql
        assert "transfers IS" in sql
        assert "b IS" in sql


class TestGraphPatterns:
    """Tests for complete graph query patterns."""

    def test_simple_path_pattern(self, dummy_dialect: DummyDialect):
        """Test a simple path pattern: (a)-[e]->(b)."""
        a = GraphVertex(dummy_dialect, "a", "Account")
        e = GraphEdge(dummy_dialect, "e", "OWNS", GraphEdgeDirection.RIGHT)
        b = GraphVertex(dummy_dialect, "b", "Person")
        
        match_clause = MatchClause(dummy_dialect, a, e, b)
        sql, params = match_clause.to_sql()
        
        # Verify the structure contains expected elements
        assert "MATCH" in sql.upper()
        assert "(a IS" in sql
        assert "[e IS" in sql
        assert "(b IS" in sql

    def test_bidirectional_pattern(self, dummy_dialect: DummyDialect):
        """Test a bidirectional relationship pattern."""
        person1 = GraphVertex(dummy_dialect, "p1", "Person")
        knows_edge = GraphEdge(dummy_dialect, "k", "KNOWS", GraphEdgeDirection.ANY)
        person2 = GraphVertex(dummy_dialect, "p2", "Person")
        
        match_clause = MatchClause(dummy_dialect, person1, knows_edge, person2)
        sql, params = match_clause.to_sql()
        
        assert "MATCH" in sql.upper()
        assert "p1 IS" in sql
        assert "k IS" in sql
        assert "p2 IS" in sql
        # The edge should have bidirectional arrows <-[k IS KNOWS]->

    def test_complex_pattern_with_undirected_edge(self, dummy_dialect: DummyDialect):
        """Test a pattern with undirected edge."""
        a = GraphVertex(dummy_dialect, "a", "NodeA")
        rel = GraphEdge(dummy_dialect, "r", "RELATED", GraphEdgeDirection.NONE)
        b = GraphVertex(dummy_dialect, "b", "NodeB")
        
        match_clause = MatchClause(dummy_dialect, a, rel, b)
        sql, params = match_clause.to_sql()
        
        assert "MATCH" in sql.upper()
        assert "a IS" in sql
        assert "r IS" in sql
        assert "b IS" in sql
        # The edge should be undirected: -[r IS RELATED]-


class TestGraphDirectionCombinations:
    """Tests for different combinations of edge directions."""

    @pytest.mark.parametrize("direction,expected_pattern", [
        (GraphEdgeDirection.RIGHT, "->"),
        (GraphEdgeDirection.LEFT, "<-"),
        (GraphEdgeDirection.ANY, "<->"),  # This should match <-[e IS "REL"]-> where <- and -> both appear
        (GraphEdgeDirection.NONE, "-"),
    ])
    def test_edge_direction_output(self, dummy_dialect: DummyDialect, direction, expected_pattern):
        """Test that each direction produces the expected arrow pattern."""
        edge = GraphEdge(dummy_dialect, "e", "REL", direction)
        sql, _ = edge.to_sql()

        # For ANY direction, we expect both <- and -> in the string
        if direction == GraphEdgeDirection.ANY:
            assert "<-" in sql and "->" in sql
        else:
            # Check that the expected pattern appears in the right place
            assert expected_pattern in sql


class TestIntegration:
    """Integration tests combining multiple graph elements."""

    def test_complete_graph_query_simulation(self, dummy_dialect: DummyDialect):
        """Simulate a complete graph query similar to SQL 2023 examples."""
        # Pattern: (p1 IS person) <-[IS owner]- (a1 IS account),
        #           (a1) -[e IS transfer]-> (a2 IS account),
        #           (a2) -[IS owner]-> (p2 IS person)
        
        # First pattern: person <- owner - account
        p1 = GraphVertex(dummy_dialect, "p1", "person")
        owner_left = GraphEdge(dummy_dialect, "owner", "owner", GraphEdgeDirection.LEFT)
        a1 = GraphVertex(dummy_dialect, "a1", "account")
        
        # Second pattern: account - transfer -> account
        transfer = GraphEdge(dummy_dialect, "e", "transfer", GraphEdgeDirection.RIGHT)
        a2 = GraphVertex(dummy_dialect, "a2", "account")
        
        # Third pattern: account - owner -> person
        owner_right = GraphEdge(dummy_dialect, "owner2", "owner", GraphEdgeDirection.RIGHT)
        p2 = GraphVertex(dummy_dialect, "p2", "person")
        
        # Create match clause with all elements
        match_clause = MatchClause(dummy_dialect, p1, owner_left, a1, transfer, a2, owner_right, p2)
        sql, params = match_clause.to_sql()
        
        # Verify that the SQL contains the expected elements
        assert "MATCH" in sql.upper()
        assert "p1 IS" in sql
        assert "a1 IS" in sql
        assert "e IS" in sql
        assert "a2 IS" in sql
        assert "p2 IS" in sql
        
        # Verify that the direction patterns appear correctly
        assert "<-" in sql or "->" in sql  # Should have some directional arrows