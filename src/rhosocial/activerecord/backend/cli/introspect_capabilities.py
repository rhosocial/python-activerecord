# src/rhosocial/activerecord/backend/cli/introspect_capabilities.py
"""Which introspection questions a backend's CLI offers, decided by the dialect.

A CLI that lists its types by hand drifts: the backend gains or loses the
ability to answer a family, the list does not follow, and a user is offered a
question the engine refuses -- or, worse, is never offered one it can answer.
ClickHouse shipped `foreign-keys` and `triggers` for an engine that declares
it has neither, and `introspect triggers` failed with a TypeError rather than
with the capability refusal it was written to produce.

So the list is derived. Each type names the capability that must answer True
for it to be offered, and the list is filtered against the dialect at parser
construction time -- the same dialect the run will use, already version-adapted
at that point, so a server that gained a family is reflected in `--help`
rather than in a later error.

Types that map to no switch are offered unconditionally: `columns` and `indexes`
are questions *about a table* rather than families of objects, and there is
no capability to consult for them beyond the table's own.
"""

from typing import Dict, Iterable, List, Optional

#: type -> the dialect capability that must answer True for it to be offered.
#: A missing entry means "no switch decides this", not "always offer it": a
#: type absent here is offered because there is nothing that could refuse it.
#:
#: The standard families use core's shared switch names. The backend-specific
#: ones use one name per family, shared across every backend that has the
#: family, so a caller asking about sequences gets the same answer from the
#: same method wherever sequences exist.
TYPE_CAPABILITIES: Dict[str, str] = {
    "tables": "supports_table_introspection",
    "views": "supports_view_introspection",
    "table": "supports_table_introspection",
    "indexes": "supports_index_introspection",
    "triggers": "supports_trigger_introspection",
    "database": "supports_database_info",

    "extensions": "supports_extension_introspection",
    "materialized-views": "supports_materialized_view_introspection",
    "sequences": "supports_sequence_introspection",
    "synonyms": "supports_synonym_introspection",
    "packages": "supports_package_introspection",
    "table-options": "supports_table_options_introspection",
    "partitions": "supports_partition_introspection",
    "table-engine": "supports_table_engine_introspection",
    "generators": "supports_generator_introspection",
    "domains": "supports_domain_introspection",
    "databases": "supports_database_introspection",
    "schemas": "supports_schema_introspection",
    "warehouses": "supports_warehouse_introspection",
    "datasets": "supports_dataset_introspection",
    "procedures": "supports_procedure_introspection",
    "functions": "supports_function_introspection",
}


def available_introspect_types(dialect, declared: Iterable[str]) -> List[str]:
    """The subset of *declared* the dialect says it can actually answer.

    Order follows *declared*, so the backend controls the order it advertises
    in ``--help`` and only the membership is derived. A type this module has
    no capability for is kept as-is; a type whose capability method does not
    exist on the dialect is **dropped**, because an absent switch is not
    evidence the family works, and the cost of guessing wrong is a user
    offered a question that fails.
    """
    out: List[str] = []
    for t in declared:
        cap = TYPE_CAPABILITIES.get(t)
        if cap is None:
            out.append(t)
            continue
        method = getattr(dialect, cap, None)
        if not callable(method):
            continue
        if method():
            out.append(t)
    return out


def capability_for(introspect_type: str) -> Optional[str]:
    """The switch that decides *introspect_type*, or ``None`` if none does."""
    return TYPE_CAPABILITIES.get(introspect_type)
