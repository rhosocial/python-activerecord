# src/rhosocial/activerecord/backend/impl/sqlite/examples/named_procedure_graph/__init__.py
"""
Named Procedure Graph examples.

This package contains examples of ProcedureGraph definitions
that can be executed via CLI or Python code.

Example:
    >>> from rhosocial.activerecord.backend.named_query import resolve_named_procedure_graph
    >>> graph, resolver = resolve_named_procedure_graph(
    ...     "rhosocial.activerecord.backend.impl.sqlite.examples.named_procedure_graph.monthly_report",
    ...     dialect,
    ...     {"month": "2026-04"}
    ... )
    >>> waves = graph.waves()
"""