# Expression sub-namespace layout

This directory is the reference layout for expression definitions. Concrete backends
(`backend/impl/<name>/expression/`) are **strongly encouraged** to use the same
first-level sub-namespaces. The layout is a code-organization convention only: no
kind, registry entry, rendering rule or artifact shape depends on a directory name.

## Canonical first-level names

A namespace may be a directory or a same-named module; only the first-level name
is governed. In this package all eleven are directories. `bases/` sits beside them
as infrastructure: it declares no concrete expression node and is exempt.

```
functions        objects          sources          statements       types
predicates       query_parts      operators        value_types      column_types
introspection
```

`introspection` is a cross-backend family: server/schema/catalog query nodes go
there on every backend, whatever the backend calls them (`show`, `status`,
`pg_stat`, ...).

The former `core.py` was split by family: `Parameter` and wildcards in
`value_types/`, `Column` in `column_types/`, `FunctionCall`/`CastExpression` in
`functions/`, `Subquery` in `sources/`, `QualifiedIdentifier` in `objects/`. Class
names — and therefore kinds — did not change. Deprecated aliases
`JoinExpression`/`GroupingExpression` are gone; use `JoinClause`/`GroupingClause`.

## How to place a node

- Put the node in the namespace of its **family**, not its feature: a dialect-specific
  function belongs in `functions/`, a statement in `statements/`, a clause in
  `query_parts/`, a predicate in `predicates/`, a value in `value_types/`, a column
  in `column_types/`, a row source in `sources/`, an operation in `operators/`.
- Do not invent a new top-level name for a feature (`json.py`, `partition.py`,
  `vacuum.py`, `vector.py`, `admin.py`, ...). Split the module into the family
  namespaces instead.
- Infrastructure helpers that declare no concrete expression node live in
  `bases/` (`bases.py`, `mixins.py`, `coerce.py`, `defaults.py`,
  `collect_columns.py`, `type_name.py`). They are not a family and are outside
  this convention; do not add new top-level names for them either.
- Re-export the public names from your package's `__init__.py`, so callers keep
  importing from `backend.impl.<name>.expression`.

## Why

- Cross-backend diffs line up: a behavior difference is a difference inside the
  same family namespace, not a hunt through differently named modules.
- Registry assembly walks the expression package; moving nodes between namespaces
  changes only the derived fully-qualified names, never the kind set.
- A contributor knows where a new node goes without asking.

The form rule lives in the shared rules contract
`rhosocial.activerecord.testsuite.feature.rules.contracts.layout`. Check your
backend's rule suite before publishing a new namespace name.

## How to list the expressions

The registries — not this directory tree — are the authoritative answer to
"which expressions exist". `docs/en_US/backend/expression/serialization.md`
("What Expressions Exist") shows how to print `CORE_EXPRESSIONS` and a backend's
`<NAME>_EXPRESSIONS` / `<NAME>_EXPRESSION_REGISTRY`. Those printed kinds are
also the serialization contract: exactly the nodes the codec promises to write
and read back. Moving a node between the namespaces above changes its module
path, not its kind, so the contract survives a layout change.
