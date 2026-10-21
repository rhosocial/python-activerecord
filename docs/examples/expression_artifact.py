"""Serializing an expression to JSON text and reading it back.

Run it:  .venv3.14\\Scripts\\python.exe docs\\examples\\expression_artifact.py

The point of the whole design is in the middle four lines: a plain
``json.dumps`` / ``json.loads`` pair, with no custom encoder, no ``object_hook``
and no class import on the reading side.
"""

import json

from rhosocial.activerecord.backend.expression.core import Column, Literal
from rhosocial.activerecord.backend.expression.objects import Table
from rhosocial.activerecord.backend.expression.predicates import ComparisonPredicate
from rhosocial.activerecord.backend.expression.query_parts import WhereClause
from rhosocial.activerecord.backend.expression.statements.dql import QueryStatement
from rhosocial.activerecord.backend.expression.registry import ExpressionRegistry
from rhosocial.activerecord.backend.expression.serialization import (
    deserialize,
    default_registry,
    serialize,
)
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect


def build_query(dialect):
    """An ordinary query. Nothing here knows about serialization."""
    users = Table(dialect, "users")
    return QueryStatement(
        dialect,
        select=[Column(dialect, "id"), Column(dialect, "name")],
        from_=users,
        where=WhereClause(
            dialect,
            ComparisonPredicate(dialect, ">", Column(dialect, "age"), Literal(dialect, 18)),
        ),
    )


def rule(title):
    print()
    print(title)
    print("-" * len(title))


def show(label, result):
    """Print what ``to_sql()`` gives: the statement and its bind parameters.

    Expressions never inline a value into the SQL. A literal becomes a
    ``?`` and its value comes back alongside, so the driver can bind it and
    the database never sees a quoted string built by string concatenation.
    """
    sql, params = result
    print("%-22s %s" % (label, sql))
    print("%-22s params=%r  (%s)" % ("", list(params), ", ".join(type(p).__name__ for p in params)))
    return sql, params


def main():
    # Whatever dialect you happen to be holding. The artifact will not carry it.
    dialect = DummyDialect()
    query = build_query(dialect)
    built_sql, built_params = show("built", query.to_sql())

    # ---------------------------------------------------------------- 1. write
    rule("1. expression instance -> artifact")
    artifact = serialize(query)
    print(json.dumps(artifact, indent=2)[:300], "...")

    # ---------------------------------------------------------------- 2. text
    rule("2. artifact -> JSON text (plain json.dumps)")
    text = json.dumps(artifact)
    print(text[:300], "...")
    print("bytes  :", len(text))

    # ---------------------------------------------------------------- 3. back
    rule("3. JSON text -> artifact (plain json.loads, no object_hook)")
    loaded = json.loads(text)
    print("keys   :", sorted(loaded))
    print("kind   :", loaded["kind"])
    # Nothing needs decoding before the codec sees it. The artifact is plain JSON
    # end to end: a node is {kind, params}, a parameter is a scalar, an array
    # or an object. There are no markers, so there is nothing to recognise --
    # and nothing a reader in another language would have to be told about.

    # ---------------------------------------------------------------- 4. read
    rule("4. artifact -> expression instance")
    restored = deserialize(loaded, dialect)
    print("type   :", type(restored).__name__)
    rebuilt_sql, rebuilt_params = show("rebuilt", restored.to_sql())
    print("same sql   :", rebuilt_sql == built_sql)
    print("same params:", rebuilt_params == built_params)

    # The bind parameters were never stored anywhere. They are a *consequence*
    # of the payload: the literal travelled as a node, so the reader knows it
    # is a literal and offers it up for binding. An artifact that had to carry
    # "SQL text plus a parameter list" would have two things to keep in step,
    # and no way to check they agreed.
    rule("4b. where the bind value actually lives")
    # A nested expression is a bare `{kind, params}` node, with no wrapper
    # announcing it -- the shape is the whole signal. So there is nothing to
    # unwrap here, which is a large part of why an artifact stays readable.
    condition = loaded["params"]["where"]["params"]["condition"]
    literal = condition["params"]["right"]
    print("the predicate node :", condition["kind"])
    print("its right operand  :", literal["kind"])
    print("that node's params :", json.dumps(literal["params"]))
    print()
    print("  The 18 in `params=(18,)` was read off that node. Nothing else")
    print("  carried it, so nothing else can disagree with it.")
    print()
    print("  A literal's kind is its *value* kind, not the node's class name.")
    print("  One node carries every value and the wire still names them apart,")
    print("  because a date's spelling and a string's are the same bytes.")

    # ------------------------------------------------- 5. the actual payoff
    rule("5. the artifact carries no dialect")
    flat = json.dumps(loaded)
    print("mentions a dialect:", any(w in flat for w in ("Dialect", "dummy", "sqlite")))
    sqlite = SQLiteDialect(version=(3, 53, 0))
    on_sqlite = deserialize(loaded, sqlite)
    show("on SQLite", on_sqlite.to_sql())
    print()
    print("  Same artifact, second dialect object, no re-serialization.")
    print("  The SQL happens to match because DummyDialect and SQLiteDialect")
    print("  in this distribution share one set of formatters; a dialect that")
    print("  models a feature differently will differ, and it will differ here")
    print("  -- the payload was never tied to the first one.")

    # ------------------------------------------------------- 6. what a read may accept
    rule("6. the caller's registry decides which kinds a read may produce")
    narrow = ExpressionRegistry()
    narrow.register_node(Column)
    try:
        deserialize(loaded, dialect, registry=narrow)
    except Exception as exc:
        print("table with 1 kind  -> refused:", type(exc).__name__)
        print("                     ", str(exc)[:104])

    enough = ExpressionRegistry()
    for name in (
        "query_statement", "where_clause", "column",
        "comparison_predicate", "table",
    ):
        enough.register_node(default_registry().resolve_node(name))
    # A value kind is admitted by its *wire name*, never by class. One node
    # carries every value, so there is no class named `integer_value` to
    # register and `register_node` could not produce the key even if you
    # handed it the class -- it would file it under `literal`, the class name.
    enough.register_value_kinds("integer_value")
    ok = deserialize(loaded, dialect, registry=enough)
    print("table with 6 kinds -> rebuilt:", type(ok).__name__)
    print("  The reader only ever produces what the caller allowed.")

    # --------------------------------------------------------- 7. untrusted input
    rule("7. an artifact is untrusted input")
    for label, bad in (
        ("unknown kind", {"kind": "no_such_kind", "params": {}}),
        ("leftover envelope", dict(loaded, type="...SelectStatement")),
        ("missing kind", {"params": {}}),
    ):
        try:
            deserialize(bad, dialect)
        except Exception as exc:
            print("%-20s -> %s" % (label, type(exc).__name__))
            print("%-20s    %s" % ("", str(exc)[:104]))


if __name__ == "__main__":
    main()