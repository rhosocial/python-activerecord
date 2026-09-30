# src/rhosocial/activerecord/backend/impl/sqlite/examples/conftest.py
"""
Example metadata configuration.

This file defines metadata for all examples in this directory.
The inspector reads this file to get title, dialect_protocols, and priority.
"""

EXAMPLES_META = {
    "connection/quickstart.py": {
        "title": "Connect to SQLite and Execute Queries",
        "dialect_protocols": [],
        "priority": 10,
    },
    "ddl/create_table.py": {
        "title": "Create Table",
        "dialect_protocols": [],
        "priority": 10,
    },
    "ddl/create_index.py": {
        "title": "Create Index",
        "dialect_protocols": [],
        "priority": 10,
    },
    "ddl/alter_table.py": {
        "title": "Alter Table",
        "dialect_protocols": [],
        "priority": 10,
    },
    "ddl/drop_table.py": {
        "title": "DROP TABLE",
        "dialect_protocols": [],
        "priority": 10,
    },
    "ddl/unique_index.py": {
        "title": "CREATE UNIQUE INDEX",
        "dialect_protocols": [],
        "priority": 10,
    },
    "ddl/view.py": {
        "title": "CREATE VIEW",
        "dialect_protocols": [],
        "priority": 10,
    },
    "update/basic.py": {
        "title": "Update with RETURNING",
        "dialect_protocols": ["ReturningSupport"],
        "priority": 10,
    },
    "insert/with_returning.py": {
        "title": "Insert with RETURNING",
        "dialect_protocols": ["ReturningSupport"],
        "priority": 10,
    },
    "insert/batch.py": {
        "title": "Batch Insert",
        "dialect_protocols": [],
        "priority": 10,
    },
    "insert/single.py": {
        "title": "Single Row Insert",
        "dialect_protocols": [],
        "priority": 10,
    },
    "insert/upsert.py": {
        "title": "UPSERT (INSERT OR REPLACE / INSERT OR IGNORE)",
        "dialect_protocols": [],
        "priority": 10,
    },
    "delete/basic.py": {
        "title": "Delete with RETURNING",
        "dialect_protocols": ["ReturningSupport"],
        "priority": 10,
    },
    "transaction/basic.py": {
        "title": "Transaction Control",
        "dialect_protocols": [],
        "priority": 10,
    },
    "transaction/exclusive.py": {
        "title": "SQLite Transaction Modes",
        "dialect_protocols": [],
        "priority": 10,
    },
    "transaction/for_update.py": {
        "title": "FOR UPDATE Row Locking",
        "dialect_protocols": [],
        "priority": 10,
    },
    "query/basic.py": {
        "title": "Basic SELECT Query",
        "dialect_protocols": [],
        "priority": 10,
    },
    "query/join.py": {
        "title": "JOIN Query",
        "dialect_protocols": [],
        "priority": 10,
    },
    "query/aggregate.py": {
        "title": "Aggregate Query",
        "dialect_protocols": [],
        "priority": 10,
    },
    "query/subquery.py": {
        "title": "Subquery",
        "dialect_protocols": [],
        "priority": 10,
    },
    "query/window.py": {
        "title": "Window Functions",
        "dialect_protocols": ["WindowFunctionSupport"],
        "priority": 10,
    },
    "query/predicate.py": {
        "title": "Complex Predicates",
        "dialect_protocols": [],
        "priority": 10,
    },
    "query/distinct.py": {
        "title": "SELECT DISTINCT",
        "dialect_protocols": [],
        "priority": 10,
    },
    "query/union.py": {
        "title": "UNION using SetOperationExpression",
        "dialect_protocols": [],
        "priority": 10,
    },
    "query/cte.py": {
        "title": "CTE (Common Table Expressions)",
        "dialect_protocols": ["CTESupport"],
        "priority": 10,
    },
    "query/pagination.py": {
        "title": "Pagination with LIMIT/OFFSET",
        "dialect_protocols": [],
        "priority": 10,
    },
    "query/fulltext.py": {
        "title": "Full-Text Search (FTS5)",
        "dialect_protocols": [],
        "priority": 10,
    },
    "query/explain.py": {
        "title": "EXPLAIN Query Plan",
        "dialect_protocols": [],
        "priority": 10,
    },
    "types/json_basic.py": {
        "title": "JSON Operations",
        "dialect_protocols": ["JSONSupport"],
        "priority": 10,
    },
    "schema_diff/add_table.py": {
        "title": "Schema Diff — Detect New Table",
        "dialect_protocols": [],
        "priority": 10,
    },
    "schema_diff/add_column.py": {
        "title": "Schema Diff — Detect Column Changes",
        "dialect_protocols": [],
        "priority": 10,
    },
    "schema_diff/index_change.py": {
        "title": "Schema Diff — Detect Index Changes",
        "dialect_protocols": [],
        "priority": 10,
    },
    "schema_diff/serialization_roundtrip.py": {
        "title": "Schema Diff — Snapshot Serialization Roundtrip",
        "dialect_protocols": [],
        "priority": 10,
    },

    "cli/named_connection_demo.py": {
        "title": "CLI — named-connection Subcommand",
        "dialect_protocols": [],
        "priority": 10,
    },
    "cli/named_procedure_demo.py": {
        "title": "CLI — named-procedure Subcommand",
        "dialect_protocols": [],
        "priority": 10,
    },
    "cli/named_query_demo.py": {
        "title": "CLI — named-expression Subcommand",
        "dialect_protocols": [],
        "priority": 10,
    },
    "concurrency.py": {
        "title": "ConcurrencyAware Protocol",
        "dialect_protocols": [],
        "priority": 10,
    },
    "extensions/fts3_4_basic.py": {
        "title": "FTS3/FTS4 Full-Text Search (deprecated)",
        "dialect_protocols": [],
        "priority": 10,
    },
    "extensions/fts5_basic.py": {
        "title": "FTS5 Full-Text Search",
        "dialect_protocols": [],
        "priority": 10,
    },
    "extensions/version_353_features.py": {
        "title": "SQLite 3.53.0 Feature Detection",
        "dialect_protocols": [],
        "priority": 10,
    },
    "named_connections/file.py": {
        "title": "Named Connection — File-Based Database",
        "dialect_protocols": [],
        "priority": 10,
    },
    "named_connections/memory.py": {
        "title": "Named Connection — In-Memory Database",
        "dialect_protocols": [],
        "priority": 10,
    },
    "named_expressions/order_clauses.py": {
        "title": "Named Expressions — Clause Builders (WHERE / JOIN / GROUP BY / ORDER BY / LIMIT)",
        "dialect_protocols": [],
        "priority": 10,
    },
    "named_expressions/order_ddl.py": {
        "title": "Named Expressions — DDL Builders",
        "dialect_protocols": [],
        "priority": 10,
    },
    "named_expressions/order_dml.py": {
        "title": "Named Expressions — DML Builders",
        "dialect_protocols": [],
        "priority": 10,
    },
    "named_expressions/order_expressions.py": {
        "title": "Named Expressions — Order Queries",
        "dialect_protocols": [],
        "priority": 10,
    },
    "named_expressions/order_version_compare.py": {
        "title": "Named Expressions — Version-Dependent (json_array_insert, SQLite 3.53+)",
        "dialect_protocols": [],
        "priority": 10,
    },
    "named_migrations/expressions.py": {
        "title": "Named Expressions — DDL Builders for Migrations",
        "dialect_protocols": [],
        "priority": 10,
    },
    "named_migrations/migrations.py": {
        "title": "Named Migrations — Versioned Schema Changes",
        "dialect_protocols": [],
        "priority": 10,
    },
    "named_procedure_graph/monthly_report.py": {
        "title": "Named Procedure Graph — Monthly Sales Report",
        "dialect_protocols": [],
        "priority": 10,
    },
    "named_procedure_graph/q.py": {
        "title": "Named Expressions — Queries Supporting monthly_report_graph",
        "dialect_protocols": [],
        "priority": 10,
    },
    "named_procedures/diagram_demo.py": {
        "title": "Named Procedure — Static and Instance Diagrams",
        "dialect_protocols": [],
        "priority": 10,
    },
    "named_procedures/order_workflow.py": {
        "title": "Named Procedure — Order Processing Workflow",
        "dialect_protocols": [],
        "priority": 10,
    },
}
