"""Serializing an expression to JSON text and reading it back.

Run it:  .venv3.14\\Scripts\\python.exe docs\\examples\\expression_artifact.py

The point of the whole design is in the middle of ``main``: ``serialize_json``
and ``deserialize_json`` carry a bare ``{kind, params}`` node as plain JSON.
The codec uses no hook -- a node is recognised by its shape, and the reader
imports the class the caller's registry already names for the kind. Hooks are
opt-in and forwarded straight to the standard library: ``default=`` on
``serialize_json`` reaches ``json.dumps``, ``object_hook=`` on
``deserialize_json`` reaches ``json.loads``. Step 4c shows both: a ``date``
fails with no hook, and with one reads back as a string.
"""

import json
from datetime import date

from rhosocial.activerecord.backend.expression.column_types.column import Column
from rhosocial.activerecord.backend.expression.value_types.parameter import Parameter
from rhosocial.activerecord.backend.expression.objects import Table
from rhosocial.activerecord.backend.expression.predicates.predicates import ComparisonPredicate
from rhosocial.activerecord.backend.expression.query_parts.query_parts import WhereClause
from rhosocial.activerecord.backend.expression.statements.dql import QueryStatement
from rhosocial.activerecord.backend.expression_registry import (
    CORE_EXPRESSION_REGISTRY,
    ExpressionRegistry,
    deserialize,
    deserialize_json,
    serialize,
    serialize_json,
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
            # 18 is a raw value at a value position: the predicate wraps it in a
            # Parameter, so the SQL holds a placeholder and 18 travels in params.
            ComparisonPredicate(dialect, ">", Column(dialect, "age"), 18),
        ),
    )


def rule(title):
    print()
    print(title)
    print("-" * len(title))


def show(label, result):
    """Print what ``to_sql()`` gives: the statement and its bind parameters.

    Expressions never inline a value into the SQL. A raw Python value is
    wrapped in ``Parameter``, which becomes a ``?`` and whose value comes back
    alongside, so the driver can bind it and the database never sees a quoted
    string built by string concatenation.
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
    rule("3. JSON text -> artifact (json.loads; codec uses no hook)")
    loaded = json.loads(text)
    # deserialize_json(text, object_hook=...) would accept a caller hook here;
    # the codec itself needs none -- it recognises nodes by their shape.
    print("keys   :", sorted(loaded))
    print("kind   :", loaded["kind"])
    # Nothing needs decoding before the codec sees it. The artifact is plain JSON
    # end to end: a node is {kind, params}, a parameter is a scalar, an array
    # or an object. There are no markers, so there is nothing to recognise --
    # and nothing a reader in another language would have to be told about.

    # ---------------------------------------------------------------- 4. read
    rule("4. artifact -> expression instance")
    restored = deserialize(loaded)
    print("type   :", type(restored).__name__)
    rebuilt_sql, rebuilt_params = show("rebuilt", restored.to_sql(dialect))
    print("same sql   :", rebuilt_sql == built_sql)
    print("same params:", rebuilt_params == built_params)

    # The bind parameters were never stored anywhere. They are a *consequence*
    # of the payload: the value travelled as a Parameter node, so the reader
    # knows it is a parameter and offers it up for binding. An artifact that had
    # to carry "SQL text plus a parameter list" would have two things to keep in
    # step, and no way to check they agreed.
    rule("4b. where the bind value actually lives")
    # A nested expression is a bare `{kind, params}` node, with no wrapper
    # announcing it -- the shape is the whole signal. So there is nothing to
    # unwrap here, which is a large part of why an artifact stays readable.
    condition = loaded["params"]["where"]["params"]["condition"]
    parameter = condition["params"]["right"]
    print("the predicate node :", condition["kind"])
    print("its right operand  :", parameter["kind"])
    print("that node's params :", json.dumps(parameter["params"]))
    print()
    print("  The 18 in `params=(18,)` was read off that node. Nothing else")
    print("  carried it, so nothing else can disagree with it.")
    print()
    print("  A value is an ordinary node: kind `parameter`, like any class name.")
    print("  Its params are the constructor's own: value and inline. The host")
    print("  value travels unchanged -- here 18, not text and not a type name.")

    rule("4c. when json.dumps cannot write a value")
    dated = Parameter(dialect, date(2020, 1, 2))
    print("artifact in memory:", serialize(dated))
    try:
        serialize_json(dated)  # default=None -> plain json.dumps, which fails
    except TypeError as exc:
        print("serialize_json    : TypeError(%s)" % str(exc)[:64])
    # default= is forwarded to json.dumps: the caller owns the conversion.
    text_with_hook = serialize_json(dated, default=str)
    print("with default=str  :", text_with_hook)
    # object_hook= is forwarded to json.loads. The codec never uses it: a bare
    # {kind, params} node is recognised by shape, so leave values as they are.
    hook_calls = []

    def object_hook(obj):
        hook_calls.append(len(obj))
        return obj  # a JSON string stays a string: no host type on the wire

    restored = deserialize_json(text_with_hook, object_hook=object_hook)
    print("read back         :", repr(restored.value),
          "-- a str: the reader cannot infer the host type")
    print("object_hook fired :", len(hook_calls), "time(s)")

    # ------------------------------------------------- 5. the actual payoff
    rule("5. the artifact carries no dialect")
    flat = json.dumps(loaded)
    print("mentions a dialect:", any(w in flat for w in ("Dialect", "dummy", "sqlite")))
    sqlite = SQLiteDialect(version=(3, 53, 0))
    on_sqlite = deserialize(loaded)
    show("on SQLite", on_sqlite.to_sql(sqlite))
    print()
    print("  Same artifact, second dialect object, no re-serialization.")
    print("  The read rebuilt a tree; the dialect was applied afterwards.")
    print("  The SQL happens to match because DummyDialect and SQLiteDialect")
    print("  in this distribution share one set of formatters; a dialect that")
    print("  models a feature differently will differ, and it will differ here")
    print("  -- the payload was never tied to the first one.")

    # ------------------------------------------------------- 6. what a read may accept
    rule("6. the caller's registry decides which kinds a read may produce")
    narrow = ExpressionRegistry()
    narrow.register_node(Column)
    try:
        deserialize(loaded, registry=narrow)
    except Exception as exc:
        print("table with 1 kind  -> refused:", type(exc).__name__)
        print("                     ", str(exc)[:104])

    enough = ExpressionRegistry()
    for name in (
        "query_statement", "where_clause", "column",
        "comparison_predicate", "table", "parameter",
    ):
        enough.register_node(CORE_EXPRESSION_REGISTRY.resolve_node(name))
    # Values need no separate registration: CORE_EXPRESSIONS holds node kinds
    # only, and every parameter is the one `parameter` kind whatever value it
    # carries. A table that admits values admits it.
    ok = deserialize(loaded, registry=enough)
    print("table with 6 kinds -> rebuilt:", type(ok).__name__)
    print("  The reader only ever produces what the caller allowed.")

    # --------------------------------------------------------- 7. untrusted input
    rule("7. an artifact is untrusted input")
    for label, bad in (
        ("unknown kind", {"kind": "no_such_kind", "params": {}}),
        ("leftover envelope", dict(loaded, dialect="SQLiteDialect")),
        ("missing kind", {"params": {}}),
    ):
        try:
            deserialize(bad)
        except Exception as exc:
            print("%-20s -> %s" % (label, type(exc).__name__))
            print("%-20s    %s" % ("", str(exc)[:104]))


if __name__ == "__main__":
    main()