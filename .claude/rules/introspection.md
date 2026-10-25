# Introspection

Four rules decide how introspection is built. They are judgements, not style
preferences: when an implementation disagrees with one of them, the
implementation changes.

## 1. Nobody spells SQL. This is absolute.

Production code contains no whole SQL statement and no SQL fragment built with
an f-string or `+`. Table names, column names, values, conditions and joins go
through the expression nodes (`column`, `relation`, `literal`, `compare`,
`join`, `select_sql`, ...). SQL text lives in one place only: the dialect's
`format_*` methods.

Unit tests may write SQL by hand, to build a fixture or to check what the
database actually returns. That exemption stops at the test boundary: a query
that a test spelled may not become the production path, and it may not be
"factored out" into a shared helper later.

When the expression layer cannot express an introspection question, the answer
is to add what is missing -- a node, a statement class, a formatter -- not to
fall back to a string inside the formatter. A gap is a missing class, not a
licence to spell SQL.

## 2. Core keeps the smallest set, and does not arbitrate capability.

Core carries only the families an ActiveRecord layer generally cares about and
most engines can answer: database information, tables, views, columns, indexes,
foreign keys, triggers. Partitions and schemas/catalogs are optional.

Core maintains no capability list. `supports_*` is a backend stating a fact
about itself; anything not declared is treated as unsupported. A backend that
cannot answer a question says so (`UnsupportedFeatureError`) and its CLI does
not offer the type -- it never returns a successful-looking answer about the
wrong objects.

## 3. Every backend completes its own semantics.

An introspection class derives from core, and that derivation is the floor, not
the ceiling. The backend is responsible for asking *its* catalogue everything
its own model can answer.

Objects a given engine has and core does not -- Firebird generators and
domains, Oracle sequences, synonyms and packages, ClickHouse partitions and
storage definitions, BigQuery datasets, SQL Server schemas, extended
properties, procedures and functions -- get the backend's own statement
classes, formatters, manager factories and parsers. They are not squeezed into
core, and they are not hidden inside private helpers.

"Complete" means the engine can answer every question it is capable of
answering. It does not mean copying another backend, and it does not mean
deleting a fact that only this engine has in order to match core.

## 4. Every backend CLI can introspect, on one connection.

Each backend CLI has an `introspect` subcommand covering every question that
makes sense for the connection it was given.

That qualifier is the real difference: the connection arguments already name a
database (a file, a server, a port, a database), so cross-database and
cross-schema questions usually have no meaning from a CLI. A backend exposing
`list_tables(schema=...)` does not imply a `--schema` flag. Conversely, a type
listed by the CLI must actually be answerable -- never an option that ends in
`NotImplementedError`.

The type list is therefore owned by each backend (`INTROSPECT_TYPES` beside its
`introspect` command). It is a subset or a reshaping of the backend's
capability for the single-connection case, not a mirror of it, and core does
not arbitrate it.

## What follows for the code

- A statement collects all of its parameters at construction. There are no
  chained setters (`with_schema`, `for_table`, ...): a chain hides the final
  parameters from the IDE and from static analysis, which is exactly what
  one-shot construction exists to prevent.
- A question is three existing things, never a fourth: a statement class, a
  dialect `format_*_query_statement`, and a public manager method pair
  (`<family>_statement` / `parse_<family>`).
- Names carry no underscore. A method that would be private is either a
  public contract or a class that has not been written yet.

## Checking it

Three mechanical checks belong in the shared test suite, one call per
repository:

1. no `def _name` inside the introspection packages (`__init__` and other
   dunders excepted);
2. no string literal that starts a statement (`SELECT`, `INSERT`, `UPDATE`,
   `DELETE`, `WITH`) and no f-string containing one;
3. every family declared by `supports_*_introspection()` has a matching
   `format_*_query_statement` that renders non-empty SQL.
