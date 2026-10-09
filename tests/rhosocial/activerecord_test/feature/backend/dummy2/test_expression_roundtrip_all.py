# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_expression_roundtrip_all.py
"""
Functional serialization coverage: every registered expression class must
round-trip losslessly through all three encodings (dict / JSON string / XML).

For each expression class that can be constructed:
  1. dict round-trip   : deserialize(serialize(e)).get_params() == e.get_params()
  2. JSON round-trip   : deserialize_json(serialize_json(e)).get_params() == ...
  3. XML round-trip    : deserialize_xml(serialize_xml(e)).get_params() == ...
  4. SQL consistency   : classified, never swallowed -- see below.

Why ``to_sql()`` is classified rather than caught
=================================================

This matrix used to wrap the first render in ``try/except Exception: return``,
which made every render failure a green tick: the three SQL comparisons never
ran, so a formatter reading a field that no longer existed was indistinguishable
from a formatter for a feature the dialect does not support. That is the same
vacuity that let a namespace test pass while the formatter ignored the namespace
it claimed to be testing.

Each outcome is now named and asserted:

* **renders** -- all three encodings must restore byte-identical SQL *and*
  byte-identical bind parameters.
* ``UnsupportedFeatureError`` -- this dialect does not model the feature.
  Asserted as exactly that type, so a different error cannot hide behind it.
* a member of :data:`LEGITIMATE_NON_RENDERS` -- a class that cannot render for a
  reason belonging to its own tree. Each entry pins the exception type *and* a
  message fragment, so a class that started failing for a different reason fails
  here instead of staying quietly green.
* **anything else** -- a failure naming the class and the exception.

And what happens when a class cannot be constructed
==================================================

``make_instance(...) is None`` becomes a skip, but only for a class named in
:data:`UNCONSTRUCTIBLE`, and :func:`test_unconstructible_list_is_exact` pins that
tuple. A class that starts needing an exemption fails CI instead of turning into
a skip, and a stale entry fails too.
"""

import inspect
from typing import Dict

import pytest

from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.expression import graph as graph_mod
from rhosocial.activerecord.backend.expression.advanced_functions import (
    CaseExpression,
    WindowClause,
    WindowDefinition,
    WindowSpecification,
)
from rhosocial.activerecord.backend.expression.bases import BaseExpression
from rhosocial.activerecord.backend.expression.core import Column, Literal
from rhosocial.activerecord.backend.expression.datetime import (
    TemporalOptionsExpression,
)
from rhosocial.activerecord.backend.expression.objects import (
    Database,
    Domain,
    EdgeTable as EdgeTableObject,
    Function,
    Index,
    MaterializedView,
    NodeTable,
    PropertyGraph,
    Sequence,
    Schema,
    Table,
    Trigger,
    Type,
    View,
)
from rhosocial.activerecord.backend.expression.predicates import ComparisonPredicate
from rhosocial.activerecord.backend.expression.query_parts import JoinClause
from rhosocial.activerecord.backend.expression.serialization import (
    ExpressionRegistry,
    deserialize,
    deserialize_json,
    deserialize_xml,
    serialize,
    serialize_json,
    serialize_xml,
)
from rhosocial.activerecord.backend.expression.sources import NamedRelationRef
from rhosocial.activerecord.backend.expression.statements import (
    ddl_alter,
    ddl_comment,
    ddl_database,
    ddl_domain,
    ddl_function,
    ddl_index,
    ddl_schema,
    ddl_sequence,
    ddl_table,
    ddl_trigger,
    ddl_truncate,
    ddl_type,
    ddl_view,
    dml,
)
from rhosocial.activerecord.backend.expression.statements.ddl_database import (
    AlterDatabaseAction,
)
from rhosocial.activerecord.backend.expression.statements.ddl_domain import (
    DomainCheckConstraint,
    RenameDomainAction,
)
from rhosocial.activerecord.backend.expression.statements.ddl_table import (
    ColumnConstraint,
    ColumnConstraintType,
    ForeignKeyConstraint,
    IndexDefinition,
    ReferencesClause,
    TableConstraint,
    TableConstraintType,
)
from rhosocial.activerecord.backend.expression.statements.ddl_trigger import (
    TriggerEvent,
    TriggerTiming,
)
from rhosocial.activerecord.backend.expression.statements.dql import QueryExpression
from rhosocial.activerecord.backend.expression.statements.dml import (
    MergeAction,
    MergeActionType,
)
from rhosocial.activerecord.backend.expression.types import (
    ArrayType,
    IntegerType,
    VarCharType,
)
from rhosocial.activerecord.backend.expression.xml import (
    XMLAttribute,
    XMLAttributesExpression,
    XMLConcatExpression,
    XMLForestExpression,
    XMLForestItem,
)
from rhosocial.activerecord.backend.impl.dummy.expression import (
    _DummyTypeAlterAction,
    _DummyTypeDefinition,
)
from rhosocial.activerecord.testsuite.utils.expression import (
    collect_expression_classes,
    make_instance,
    register_special_constructor,
)


def assert_params_equal(a, b, path="params"):
    """Deep compare two get_params() dicts, treating nested BaseExpression
    instances as structurally equal when their get_params() match."""
    if isinstance(a, BaseExpression) and isinstance(b, BaseExpression):
        assert_params_equal(a.get_params(), b.get_params(), path + ".<expr>")
        return
    assert type(a) is type(b) or (
        isinstance(a, (list, tuple, dict)) and isinstance(b, (list, tuple, dict))
    ), f"{path}: type mismatch {type(a).__name__} vs {type(b).__name__}"
    if isinstance(a, dict):
        assert set(a) == set(b), f"{path}: keys differ {set(a) ^ set(b)}"
        for k in a:
            assert_params_equal(a[k], b[k], f"{path}.{k}")
        return
    if isinstance(a, (list, tuple)):
        assert len(a) == len(b), f"{path}: length differ"
        for i, (x, y) in enumerate(zip(a, b)):
            assert_params_equal(x, y, f"{path}[{i}]")
        return
    assert a == b, f"{path}: {a!r} != {b!r}"


CORE_EXPR_PKG = "rhosocial.activerecord.backend.expression"


def _collect_matrix_classes():
    """Every concrete expression class the core package defines.

    Collected by walking the package, not by reading ``ExpressionRegistry``:
    the registry is process-global and *grows* as other test modules import
    their own backends, so reading it makes this matrix's contents depend on
    which files pytest happened to import first. Several sqlite backend
    classes appear in the registry once ``impl.sqlite.expression`` is loaded,
    and they would then be rendered with the Dummy dialect -- which is not a
    meaningful thing to assert. Walking the package is deterministic.

    ``ddl_alter`` exports four aliases of two classes (``AlterConstraint`` and
    ``ValidateConstraint`` each have two spellings). They are the same objects,
    so the first name wins and the matrix does not test a class four times.
    """
    ExpressionRegistry._auto_register_builtins()
    collected = collect_expression_classes(CORE_EXPR_PKG)
    by_identity: Dict[int, str] = {}
    for fqn, cls in sorted(collected.items()):
        by_identity.setdefault(id(cls), fqn)
    return {
        fqn: cls
        for cls in collected.values()
        if not inspect.isabstract(cls)
        for fqn in [by_identity[id(cls)]]
    }


REGISTERED = _collect_matrix_classes()


# ---------------------------------------------------------------------------
# Special constructors: a real value where the introspective guess is a lie
# ---------------------------------------------------------------------------
#
# ``make_instance`` reads each required parameter's annotation and guesses:
# ``"x"`` for a string, ``[]`` for a list, ``IntegerType()`` for a type. That is
# right for a name and wrong for every parameter that wants a catalogue object --
# a Table, an Index, a PropertyGraph -- because a bare ``"x"`` is not one, and the
# formatter now refuses it by name. It is also wrong for the containers that
# require at least one member (CASE, WINDOW, JOIN, temporal options) and for the
# predicates that must render without bind parameters.
#
# Every registration below replaces a guess that would otherwise have produced an
# instance the dialect cannot render. Suffixes are spelled relative to the
# expression package because ``make_instance`` matches with ``str.endswith`` and
# several modules export identically named classes.


def _table_obj(dialect, name="t"):
    """A table with a bare name and no namespace."""
    return Table(dialect, name)


def _column_predicate(dialect):
    """A predicate comparing two columns, so it renders with no bind parameters."""
    return ComparisonPredicate(dialect, "=", Column(dialect, "a"), Column(dialect, "b"))


def _one_column_query(dialect):
    """A single-column ``SELECT`` over a table."""
    return QueryExpression(
        dialect, select=[Column(dialect, "id")], from_=_table_obj(dialect)
    )


def _integer_column(dialect, name="col"):
    """A column definition carrying a *dialect-bound* type.

    The binding is load-bearing, not cosmetic: ``to_sql()`` dispatches on the
    type through its own dialect, so an unbound ``IntegerType()`` raises
    ``ValueError: ... has no dialect bound`` the moment anything renders it.
    """
    return ddl_table.ColumnDefinition(dialect, name, IntegerType(dialect))


def register_specials():
    """Replace every introspective guess that would cost a real assertion."""
    # -- the FROM side ------------------------------------------------------
    register_special_constructor(
        "sources.relation.NamedRelationRef",
        lambda d: NamedRelationRef(d, _table_obj(d)),
    )
    register_special_constructor(
        "query_parts.JoinClause",
        lambda d: JoinClause(
            d,
            left_table=NamedRelationRef(d, _table_obj(d)),
            right_table=NamedRelationRef(d, Table(d, "other")),
            condition=_column_predicate(d),
        ),
    )

    # -- tables -------------------------------------------------------------
    register_special_constructor(
        "statements.ddl_table.CreateTableExpression",
        lambda d: ddl_table.CreateTableExpression(d, _table_obj(d), [_integer_column(d)]),
    )
    register_special_constructor(
        "statements.ddl_table.DropTableExpression",
        lambda d: ddl_table.DropTableExpression(d, _table_obj(d)),
    )
    register_special_constructor(
        "statements.ddl_table.CreateTableLikeExpression",
        lambda d: ddl_table.CreateTableLikeExpression(
            d, _table_obj(d), Table(d, "other")
        ),
    )
    register_special_constructor(
        "statements.ddl_table.CreateTableCloneExpression",
        lambda d: ddl_table.CreateTableCloneExpression(
            d, _table_obj(d), Table(d, "other")
        ),
    )
    register_special_constructor(
        "statements.ddl_table.CreateTableAsExpression",
        lambda d: ddl_table.CreateTableAsExpression(d, _table_obj(d), _one_column_query(d)),
    )
    register_special_constructor(
        "statements.ddl_table.CreateTableFromTemplateExpression",
        lambda d: ddl_table.CreateTableFromTemplateExpression(
            d, _table_obj(d), _one_column_query(d)
        ),
    )
    register_special_constructor(
        "statements.ddl_truncate.TruncateExpression",
        lambda d: ddl_truncate.TruncateExpression(d, _table_obj(d)),
    )
    # Overrides the shared testsuite factory, which binds no dialect to its type.
    register_special_constructor(
        "statements.ddl_table.ColumnDefinition", _integer_column
    )

    # -- indexes ------------------------------------------------------------
    register_special_constructor(
        "statements.ddl_index.CreateIndexExpression",
        lambda d: ddl_index.CreateIndexExpression(
            d, index=Index(d, "i"), table=_table_obj(d), columns=["a"]
        ),
    )
    register_special_constructor(
        "statements.ddl_index.DropIndexExpression",
        lambda d: ddl_index.DropIndexExpression(d, index=Index(d, "i")),
    )
    register_special_constructor(
        "statements.ddl_index.CreateFulltextIndexExpression",
        lambda d: ddl_index.CreateFulltextIndexExpression(
            d, index=Index(d, "i"), table=_table_obj(d), columns=["a"]
        ),
    )
    register_special_constructor(
        "statements.ddl_index.DropFulltextIndexExpression",
        lambda d: ddl_index.DropFulltextIndexExpression(
            d, index=Index(d, "i"), table=_table_obj(d)
        ),
    )
    register_special_constructor(
        "statements.ddl_alter.DropIndex",
        lambda d: ddl_alter.DropIndex(d, Index(d, "i")),
    )

    # -- schemas, sequences, databases, domains, types ---------------------
    register_special_constructor(
        "statements.ddl_schema.CreateSchemaExpression",
        lambda d: ddl_schema.CreateSchemaExpression(d, Schema(d, "s")),
    )
    register_special_constructor(
        "statements.ddl_schema.DropSchemaExpression",
        lambda d: ddl_schema.DropSchemaExpression(d, Schema(d, "s")),
    )
    register_special_constructor(
        "statements.ddl_sequence.CreateSequenceExpression",
        lambda d: ddl_sequence.CreateSequenceExpression(d, Sequence(d, "s")),
    )
    register_special_constructor(
        "statements.ddl_sequence.AlterSequenceExpression",
        lambda d: ddl_sequence.AlterSequenceExpression(d, Sequence(d, "s"), restart=1),
    )
    register_special_constructor(
        "statements.ddl_sequence.DropSequenceExpression",
        lambda d: ddl_sequence.DropSequenceExpression(d, Sequence(d, "s")),
    )
    register_special_constructor(
        "statements.ddl_database.CreateDatabaseExpression",
        lambda d: ddl_database.CreateDatabaseExpression(d, Database(d, "db")),
    )
    register_special_constructor(
        "statements.ddl_database.DropDatabaseExpression",
        lambda d: ddl_database.DropDatabaseExpression(d, Database(d, "db")),
    )
    register_special_constructor(
        "statements.ddl_database.AlterDatabaseExpression",
        lambda d: ddl_database.AlterDatabaseExpression(
            d,
            Database(d, "db"),
            action=AlterDatabaseAction.RENAME_TO,
            target="renamed_db",
        ),
    )
    register_special_constructor(
        "statements.ddl_domain.CreateDomainExpression",
        lambda d: ddl_domain.CreateDomainExpression(d, Domain(d, "dom"), IntegerType(d)),
    )
    register_special_constructor(
        "statements.ddl_domain.DropDomainExpression",
        lambda d: ddl_domain.DropDomainExpression(d, Domain(d, "dom")),
    )
    register_special_constructor(
        "statements.ddl_domain.AlterDomainExpression",
        lambda d: ddl_domain.AlterDomainExpression(
            d, Domain(d, "dom"), [RenameDomainAction(d, "other")]
        ),
    )
    # A DOMAIN CHECK is DDL: it must render without bind parameters, so its
    # condition compares two columns rather than a column and a literal.
    register_special_constructor(
        "statements.ddl_domain.DomainCheckConstraint",
        lambda d: DomainCheckConstraint(d, _column_predicate(d), name="chk"),
    )
    # Likewise `_DummyTypeDefinition`: its body is a type, which must be bound.
    register_special_constructor(
        "dummy.expression._DummyTypeDefinition",
        lambda d: _DummyTypeDefinition(d, IntegerType(d)),
    )
    register_special_constructor(
        "statements.ddl_type.CreateTypeExpression",
        lambda d: ddl_type.CreateTypeExpression(
            d, type=Type(d, "t"), definition=_DummyTypeDefinition(d, IntegerType(d))
        ),
    )
    register_special_constructor(
        "statements.ddl_type.AlterTypeExpression",
        lambda d: ddl_type.AlterTypeExpression(
            d, type=Type(d, "t"), actions=[_DummyTypeAlterAction(d, new_name="u")]
        ),
    )
    register_special_constructor(
        "statements.ddl_type.DropTypeExpression",
        lambda d: ddl_type.DropTypeExpression(d, type=Type(d, "t")),
    )

    # -- routines, triggers, comments --------------------------------------
    register_special_constructor(
        "statements.ddl_function.CreateFunctionExpression",
        lambda d: ddl_function.CreateFunctionExpression(
            d, Function(d, "fn"), returns="integer", body="SELECT 1"
        ),
    )
    register_special_constructor(
        "statements.ddl_function.DropFunctionExpression",
        lambda d: ddl_function.DropFunctionExpression(d, Function(d, "fn")),
    )
    register_special_constructor(
        "statements.ddl_trigger.CreateTriggerExpression",
        lambda d: ddl_trigger.CreateTriggerExpression(
            d,
            trigger=Trigger(d, "trg"),
            table=_table_obj(d),
            timing=TriggerTiming.BEFORE,
            events=[TriggerEvent.INSERT],
            function=Function(d, "fn"),
        ),
    )
    register_special_constructor(
        "statements.ddl_trigger.DropTriggerExpression",
        lambda d: ddl_trigger.DropTriggerExpression(d, trigger=Trigger(d, "trg")),
    )
    register_special_constructor(
        "statements.ddl_comment.CommentOnExpression",
        lambda d: ddl_comment.CommentOnExpression(d, "table", _table_obj(d), comment="c"),
    )

    # -- views --------------------------------------------------------------
    register_special_constructor(
        "statements.ddl_view.DropViewExpression",
        lambda d: ddl_view.DropViewExpression(d, View(d, "v")),
    )
    register_special_constructor(
        "statements.ddl_view.CreateMaterializedViewExpression",
        lambda d: ddl_view.CreateMaterializedViewExpression(
            d, MaterializedView(d, "mv"), _one_column_query(d)
        ),
    )
    register_special_constructor(
        "statements.ddl_view.DropMaterializedViewExpression",
        lambda d: ddl_view.DropMaterializedViewExpression(d, MaterializedView(d, "mv")),
    )
    register_special_constructor(
        "statements.ddl_view.RefreshMaterializedViewExpression",
        lambda d: ddl_view.RefreshMaterializedViewExpression(
            d, MaterializedView(d, "mv")
        ),
    )

    # -- DML ----------------------------------------------------------------
    register_special_constructor(
        "statements.dml.InsertExpression",
        lambda d: dml.InsertExpression(
            d, into=_table_obj(d), source=dml.ValuesSource(d, [[Literal(d, 1)]])
        ),
    )
    register_special_constructor(
        "statements.dml.DeleteExpression",
        lambda d: dml.DeleteExpression(d, _table_obj(d)),
    )
    register_special_constructor(
        "statements.dml.MergeExpression",
        lambda d: dml.MergeExpression(
            d,
            target_table=_table_obj(d),
            source=NamedRelationRef(d, Table(d, "src")),
            on_condition=_column_predicate(d),
            when_matched=[
                MergeAction(
                    d,
                    MergeActionType.UPDATE,
                    {"a": Literal(d, 1)},
                    _column_predicate(d),
                    "matched",
                )
            ],
        ),
    )
    register_special_constructor(
        "statements.dml.MergeAction",
        lambda d: MergeAction(
            d,
            MergeActionType.UPDATE,
            {"a": Literal(d, 1)},
            _column_predicate(d),
            "matched",
        ),
    )

    # -- constraints and column pieces --------------------------------------
    register_special_constructor(
        "statements.ddl_table.ColumnConstraint",
        lambda d: ColumnConstraint(d, ColumnConstraintType.NOT_NULL, name="c"),
    )
    register_special_constructor(
        "statements.ddl_table.TableConstraint",
        lambda d: TableConstraint(
            d, TableConstraintType.PRIMARY_KEY, name="c", columns=["a"]
        ),
    )
    register_special_constructor(
        "statements.ddl_table.ForeignKeyConstraint",
        lambda d: ForeignKeyConstraint(
            d,
            columns=["a"],
            foreign_key_table=Table(d, "other"),
            foreign_key_columns=["b"],
            name="fk",
        ),
    )
    register_special_constructor(
        "statements.ddl_table.ReferencesClause",
        lambda d: ReferencesClause(d, Table(d, "other"), ["b"]),
    )
    register_special_constructor(
        "statements.ddl_alter.AddColumn",
        lambda d: ddl_alter.AddColumn(d, _integer_column(d)),
    )
    register_special_constructor(
        "statements.ddl_alter.AddIndex",
        lambda d: ddl_alter.AddIndex(d, IndexDefinition(d, "i", ["a"])),
    )
    register_special_constructor(
        "statements.ddl_alter.AddTableConstraint",
        lambda d: ddl_alter.AddTableConstraint(
            d,
            TableConstraint(
                d, TableConstraintType.PRIMARY_KEY, name="c", columns=["a"]
            ),
        ),
    )

    # -- expressions that need at least one member --------------------------
    register_special_constructor(
        "advanced_functions.CaseExpression",
        lambda d: CaseExpression(
            d,
            cases=[(_column_predicate(d), Literal(d, 1))],
            else_result=Literal(d, 0),
        ),
    )
    register_special_constructor(
        "advanced_functions.WindowSpecification",
        lambda d: WindowSpecification(d, partition_by=["a"]),
    )
    register_special_constructor(
        "advanced_functions.WindowDefinition",
        lambda d: WindowDefinition(d, "w", WindowSpecification(d, partition_by=["a"])),
    )
    register_special_constructor(
        "advanced_functions.WindowClause",
        lambda d: WindowClause(
            d, [WindowDefinition(d, "w", WindowSpecification(d, partition_by=["a"]))]
        ),
    )
    # An empty options dict is refused by the formatter, so a time-travel clause
    # needs an actual option.
    register_special_constructor(
        "datetime.TemporalOptionsExpression",
        lambda d: TemporalOptionsExpression(d, {"as_of": "2020-01-01"}),
    )

    # -- property graphs ----------------------------------------------------
    def node_table(d):
        return NodeTable(d, "people")

    def edge_table(d):
        return EdgeTableObject(d, "knows")

    def path_pattern(d):
        return graph_mod.PathPattern(
            d, graph_mod.GraphVertex(d, "n", node_table(d))
        )

    register_special_constructor(
        "graph.GraphVertex", lambda d: graph_mod.GraphVertex(d, "n", node_table(d))
    )
    register_special_constructor(
        "graph.GraphEdge", lambda d: graph_mod.GraphEdge(d, "e", edge_table(d))
    )
    register_special_constructor(
        "graph.VertexTable",
        lambda d: graph_mod.VertexTable(d, node_table(d), key_columns=["id"]),
    )
    register_special_constructor(
        "graph.EdgeTable",
        lambda d: graph_mod.EdgeTable(d, edge_table(d), ["src"], ["dst"]),
    )
    register_special_constructor(
        "graph.QuantifiedPath",
        lambda d: graph_mod.QuantifiedPath(
            d, graph_mod.GraphEdge(d, "e", edge_table(d)), min_repeats=1, max_repeats=3
        ),
    )
    register_special_constructor("graph.PathPattern", path_pattern)
    register_special_constructor(
        "graph.MatchClause", lambda d: graph_mod.MatchClause(d, path_pattern(d))
    )
    register_special_constructor(
        "graph.ColumnsClause",
        lambda d: graph_mod.ColumnsClause(d, graph_mod.GraphColumn("n", "id")),
    )
    register_special_constructor(
        "graph.GraphTableExpression",
        lambda d: graph_mod.GraphTableExpression(
            d,
            graph=PropertyGraph(d, "g"),
            match=graph_mod.MatchClause(d, path_pattern(d)),
            columns=graph_mod.ColumnsClause(d, graph_mod.GraphColumn("n", "id")),
        ),
    )
    register_special_constructor(
        "graph.CreatePropertyGraphExpression",
        lambda d: graph_mod.CreatePropertyGraphExpression(
            d, graph=PropertyGraph(d, "g"),
            vertex_tables=[graph_mod.VertexTable(d, node_table(d))],
        ),
    )
    # The formatter accepts "add"/"drop" against "vertex tables"/"edge tables"/
    # "tables"; anything else is refused.
    register_special_constructor(
        "graph.AlterPropertyGraphExpression",
        lambda d: graph_mod.AlterPropertyGraphExpression(
            d,
            graph=PropertyGraph(d, "g"),
            action="add",
            target="vertex tables",
            vertex_tables=[graph_mod.VertexTable(d, node_table(d))],
        ),
    )
    register_special_constructor(
        "graph.DropPropertyGraphExpression",
        lambda d: graph_mod.DropPropertyGraphExpression(d, graph=PropertyGraph(d, "g")),
    )

    # -- SQL/XML and types --------------------------------------------------
    register_special_constructor(
        "xml.XMLAttributesExpression",
        lambda d: XMLAttributesExpression(d, [XMLAttribute(Literal(d, "v"), "a")]),
    )
    register_special_constructor(
        "xml.XMLForestExpression",
        lambda d: XMLForestExpression(d, [XMLForestItem(Literal(d, "v"), "a")]),
    )
    register_special_constructor(
        "xml.XMLConcatExpression",
        lambda d: XMLConcatExpression(d, [Literal(d, "a"), Literal(d, "b")]),
    )
    register_special_constructor(
        "types.array.ArrayType", lambda d: ArrayType(d, VarCharType(d, 10))
    )


register_specials()


# ---------------------------------------------------------------------------
# Lists that cannot grow or shrink silently
# ---------------------------------------------------------------------------

#: Classes the generic introspective constructor cannot build.
#:
#: Each is a real coverage gap, named here so it is visible rather than lost.
#: ``test_unconstructible_list_is_exact`` pins the tuple, so a class that gains a
#: constructor fails here until this entry is removed, and a class that starts
#: failing to build fails here too -- neither can become a quiet skip.
#:
#: The registered constructors in this module bring this down to four. What
#: remains is either a shape the introspective guess cannot satisfy -- keyword-only
#: parameters hidden behind defaulted positionals -- or a class that needs a
#: renderable member to exist at all. Registering a constructor for any of them
#: is the way to retire an entry.
#:
#: A second cause is a misread annotation, and that one belongs to testsuite rather
#: than here: a parameter typed ``Sequence[X]`` was read as the Sequence *object*
#: because the alias' name carries the word. That retired the XMLTABLE entry once
#: the harness was fixed, which is the better outcome -- no exemption at all.
#:
#: Sorted, because the integrity test compares this against a sorted tuple of what
#: it observes. The reasons below are grouped by cause, not by module.
UNCONSTRUCTIBLE = (
    # ALTER CONSTRAINT. `name` and `constraint_type` sit behind defaulted
    # positionals and are keyword-only, so the introspective constructor skips
    # them and the class refuses an incomplete action.
    "rhosocial.activerecord.backend.expression.statements.ddl_alter.AlterConstraint",
    # VALIDATE CONSTRAINT. Same shape as AlterConstraint: the required `name` is
    # keyword-only behind a defaulted positional.
    "rhosocial.activerecord.backend.expression.statements.ddl_alter.ValidateConstraint",
    # ADD DOMAIN CHECK. Widens a SQLPredicate into a DomainCheckConstraint and
    # needs one; the guess supplies a bare comparison whose literal would have to
    # render as a bind parameter, which DDL cannot carry.
    "rhosocial.activerecord.backend.expression.statements.ddl_domain.AddDomainCheckAction",
    # ENUM type. Its `values` list is keyword-only behind a defaulted positional,
    # so the introspective constructor skips it and the type declares no members.
    "rhosocial.activerecord.backend.expression.types.enum_.EnumType",
    # CUSTOM type. `raw` names the SQL type string and carries a default, so the
    # introspective constructor skips it and builds a type with no spelling. The
    # default cannot help: the class declares `dialect` first and `raw` after it,
    # so a required `raw` behind that default is not expressible as a signature.
    "rhosocial.activerecord.backend.expression.types.custom.CustomType",
    # UUID constant. `which` must name a constant kind -- 'nil' or 'max' -- and
    # __init__ rejects anything else, so the guess's "x" is refused at
    # construction. There is no value the filler could offer that is both a valid
    # constant and not a guess about which one the caller wanted.
    "rhosocial.activerecord.backend.expression.uuid.UUIDConstantExpression",
)
# XMLTABLE used to be a fifth entry, needing a row source document, a COLUMNS list
# of typed projections and a pass-through clause. Its `columns` and `passing`
# parameters are annotated `Sequence[XMLTableColumn]` / `Sequence[XMLAttribute]`,
# and the introspective constructor read that alias' own name -- "Sequence" -- as
# the catalogue object Sequence, handing a directory object to a parameter asking
# for a list of columns. testsuite now decides a parameterised alias before it
# tests for a relation name, so the constructor gets [] and builds the class.
# Retiring the entry is what the pin demands: it names a gap that no longer exists.

#: Classes that construct but cannot render, for a reason belonging to their own
#: tree rather than to a defect. Each entry pins the exception type and a message
#: fragment, so a class that starts failing for a *different* reason fails here.
_NO_FORMATTER = "does not declare its dialect formatting method name"

LEGITIMATE_NON_RENDERS = {
    # ---- bases that name an expression category, not a renderable thing ----
    # Each of these is a base class that deliberately declares no `format_method`,
    # so `to_sql()` reports that there is nothing to dispatch. They are not
    # `inspect.isabstract` -- they are concrete enough to construct -- so the
    # registry keeps them, and each is pinned to its exact message so a base that
    # started rendering fails here instead of passing quietly.
    "rhosocial.activerecord.backend.expression.bases.SQLPredicate": (
        NotImplementedError, _NO_FORMATTER
    ),
    "rhosocial.activerecord.backend.expression.bases.SQLValueExpression": (
        NotImplementedError, _NO_FORMATTER
    ),
    # The roots of the object tree. Each concrete object overrides `format_method`
    # with its own `format_*_object`; the base names only what every catalogue
    # object has in common.
    "rhosocial.activerecord.backend.expression.objects.base.SchemaObject": (
        NotImplementedError, _NO_FORMATTER
    ),
    "rhosocial.activerecord.backend.expression.objects.relation.RelationObject": (
        NotImplementedError, _NO_FORMATTER
    ),
    "rhosocial.activerecord.backend.expression.objects.routine.RoutineObject": (
        NotImplementedError, _NO_FORMATTER
    ),
    "rhosocial.activerecord.backend.expression.objects.type_.TypeObject": (
        NotImplementedError, _NO_FORMATTER
    ),
    # Expression-category bases whose concrete members each name their own
    # formatter: an ALTER TABLE action, an INSERT row source, a transaction
    # step, a temporal value, an introspection query.
    "rhosocial.activerecord.backend.expression.statements.ddl_alter.AlterTableAction": (
        NotImplementedError, _NO_FORMATTER
    ),
    "rhosocial.activerecord.backend.expression.statements.dml.InsertDataSource": (
        NotImplementedError, _NO_FORMATTER
    ),
    "rhosocial.activerecord.backend.expression.transaction.TransactionExpression": (
        NotImplementedError, _NO_FORMATTER
    ),
    "rhosocial.activerecord.backend.expression.datetime._TemporalValueExpression": (
        NotImplementedError, _NO_FORMATTER
    ),
    "rhosocial.activerecord.backend.expression.introspection.IntrospectionExpression": (
        NotImplementedError, _NO_FORMATTER
    ),

    # ---- roots whose incompleteness is structural ----
    # The root of the row-source tree. No concrete source renders through
    # `format_table_source`; each overrides `format_method`. Rendering the base
    # would mean inventing SQL for an object that carries nothing but an alias.
    # UnsupportedFeatureError rather than AttributeError: a dialect with no such
    # formatter is reporting a capability gap, which is what every other probe in
    # the tree reports, and to_sql() now says so for the same reason.
    "rhosocial.activerecord.backend.expression.sources.base.TableSource": (
        UnsupportedFeatureError,
        "does not support the 'format_table_source' statement",
    ),
    # The root of the type tree. Every concrete type declares its own generic
    # `name`, which is what `format_data_type` dispatches on; the root declares
    # none, so there is nothing to dispatch. TypeError, not
    # UnsupportedFeatureError, because the class is incomplete rather than the
    # dialect being unable.
    "rhosocial.activerecord.backend.expression.types._base.DataType": (
        TypeError,
        "does not declare a valid generic type name",
    ),
}


# ---------------------------------------------------------------------------
# The local SQL assertion: classify the outcome instead of swallowing it
# ---------------------------------------------------------------------------

def assert_sql_roundtrip_classified(fqn, instance, dialect):
    """Assert an expression's SQL survives the round-trip, or say precisely why not.

    Four outcomes, each asserted:

    * **renders** -- all three encodings must restore byte-identical SQL *and*
      byte-identical bind parameters.
    * ``UnsupportedFeatureError`` -- the dialect does not model the feature.
      Asserted as exactly that type, so a formatter raising it for an unrelated
      reason is still visible as that type rather than as a pass.
    * a member of :data:`LEGITIMATE_NON_RENDERS` -- unrenderable by design,
      asserted as its exact type *and* message fragment.
    * **anything else** -- a failure naming the class and the exception.

    Returns a short string naming the branch taken, so a caller can report the
    classification distribution if it wants to.

    Raises:
        AssertionError: On a round-trip mismatch, on an unexpected exception
            type, or when a class's rendering outcome changed.
    """
    try:
        expected_sql, expected_params = instance.to_sql()
    except UnsupportedFeatureError as exc:
        assert type(exc) is UnsupportedFeatureError, fqn
        return "unsupported"
    except Exception as exc:
        if fqn not in LEGITIMATE_NON_RENDERS:
            raise AssertionError(
                f"{fqn}: to_sql() raised {type(exc).__name__}, which is neither a "
                f"render nor a classified non-render, and this is a defect.\n"
                f"  UnsupportedFeatureError means the dialect lacks the feature and "
                f"is always allowed.\n"
                f"  A class that cannot render for a reason belonging to its own "
                f"tree belongs in LEGITIMATE_NON_RENDERS.\n"
                f"  Exception: {exc}"
            ) from exc
        expected_type, fragment = LEGITIMATE_NON_RENDERS[fqn]
        assert type(exc) is expected_type, (
            f"{fqn}: LEGITIMATE_NON_RENDERS pins this class as a legitimate "
            f"non-render raising {expected_type.__name__}, but it raised "
            f"{type(exc).__name__}: {exc}"
        )
        assert fragment in str(exc), (
            f"{fqn}: expected {expected_type.__name__} and was expected to say "
            f"{fragment!r}, but it said: {exc}"
        )
        return "non-render"

    for channel, decoded in (
        ("dict", deserialize(serialize(instance), dialect)),
        ("json", deserialize_json(serialize_json(instance), dialect)),
        ("xml", deserialize_xml(serialize_xml(instance), dialect)),
    ):
        decoded_sql, decoded_params = decoded.to_sql()
        assert decoded_sql == expected_sql, (
            f"{fqn}: {channel} round-trip changed the SQL.\n"
            f"  original: {expected_sql!r}\n"
            f"  {channel}: {decoded_sql!r}"
        )
        assert decoded_params == expected_params, (
            f"{fqn}: {channel} round-trip changed the bind parameters.\n"
            f"  original: {expected_params!r}\n"
            f"  {channel}: {decoded_params!r}"
        )
    return "rendered"


@pytest.fixture(params=[fqn for fqn in sorted(REGISTERED)], ids=sorted(REGISTERED))
def expr_case(request, dummy_dialect):
    fqn = request.param
    cls = REGISTERED[fqn]
    instance, source = make_instance(cls, dummy_dialect)
    if instance is None:
        assert fqn in UNCONSTRUCTIBLE, (
            f"{fqn} cannot be built by the generic constructor ({source}) and is "
            f"not in UNCONSTRUCTIBLE. Either register a special constructor for "
            f"it or add it to the tuple with a reason -- do not let it disappear "
            f"into a skip."
        )
        pytest.skip(f"{fqn}: pinned in UNCONSTRUCTIBLE, cannot be constructed ({source})")
    return fqn, instance


class TestExpressionRoundtripAll:
    """All constructible expression classes round-trip through all encodings."""

    def test_get_params_roundtrip_across_encodings(self, expr_case, dummy_dialect):
        fqn, instance = expr_case
        original = instance.get_params()

        spec_dict = serialize(instance)
        restored_d = deserialize(spec_dict, dummy_dialect)
        assert_params_equal(restored_d.get_params(), original, fqn)

        json_str = serialize_json(instance)
        restored_j = deserialize_json(json_str, dummy_dialect)
        assert_params_equal(restored_j.get_params(), original, fqn)

        xml_bytes = serialize_xml(instance)
        restored_x = deserialize_xml(xml_bytes, dummy_dialect)
        assert_params_equal(restored_x.get_params(), original, fqn)

    def test_to_sql_roundtrip_classified(self, expr_case, dummy_dialect):
        """A render must survive the round-trip; a non-render must be classified."""
        fqn, instance = expr_case
        assert_sql_roundtrip_classified(fqn, instance, dummy_dialect)


class TestMatrixIntegrity:
    """Guards on the matrix and its lists, so neither can quietly change."""

    def test_unconstructible_list_is_exact(self, dummy_dialect):
        """Pin the unconstructible tuple against what the constructor really skips.

        Two directions are checked. A class named here that now builds has gained
        a constructor and the entry is stale; a class that fails to build without
        being named would become a silent skip. Both fail here.
        """
        dialect = dummy_dialect
        ExpressionRegistry._auto_register_builtins()
        actual = tuple(
            sorted(
                fqn
                for fqn in REGISTERED
                if make_instance(REGISTERED[fqn], dialect)[0] is None
            )
        )
        assert actual == tuple(sorted(UNCONSTRUCTIBLE)), (
            "the set of expression classes the generic constructor cannot build "
            "changed.\n"
            f"  now skipped but not named: "
            f"{sorted(set(actual) - set(UNCONSTRUCTIBLE))}\n"
            f"  named but now built: "
            f"{sorted(set(UNCONSTRUCTIBLE) - set(actual))}\n"
            "Each new entry needs a reason in the comment above UNCONSTRUCTIBLE."
        )

    def test_unconstructible_entries_are_real_classes(self):
        """Every entry names a class that was actually collected.

        A typo in the tuple would otherwise exempt nothing while still reading as
        a deliberate decision.
        """
        unknown = set(UNCONSTRUCTIBLE) - set(REGISTERED)
        assert not unknown, (
            f"UNCONSTRUCTIBLE names classes that were not registered: {sorted(unknown)}"
        )

    def test_legitimate_non_renders_are_real_classes(self):
        """Every pinned non-render names a class that was actually collected."""
        unknown = set(LEGITIMATE_NON_RENDERS) - set(REGISTERED)
        assert not unknown, (
            f"LEGITIMATE_NON_RENDERS names classes that were not registered: "
            f"{sorted(unknown)}"
        )

    def test_pinned_non_render_really_does_not_render(self, dummy_dialect):
        """Each pinned entry still raises what it claims, for the stated reason.

        Without this, an entry could sit in the tuple for a class that renders
        perfectly well, and the matrix would be asserting nothing about it.
        """
        for fqn, (expected_type, fragment) in LEGITIMATE_NON_RENDERS.items():
            instance, source = make_instance(REGISTERED[fqn], dummy_dialect)
            assert instance is not None, (
                f"{fqn} is pinned as a non-render but could not be constructed "
                f"({source})"
            )
            with pytest.raises(expected_type) as exc_info:
                instance.to_sql()
            assert fragment in str(exc_info.value), (
                f"{fqn}: expected the message to mention {fragment!r}, got: "
                f"{exc_info.value}"
            )

    def test_matrix_covers_the_whole_core_package(self):
        """The matrix covers every concrete class the core package defines.

        Re-walked here rather than trusting the module-level collection, so a
        class that appeared after import is caught. The package walk is used
        rather than the registry because the registry also holds whatever
        backends other test modules happened to import.
        """
        ExpressionRegistry._auto_register_builtins()
        expected = set(_collect_matrix_classes())
        stray = [fqn for fqn in REGISTERED if not fqn.startswith(f"{CORE_EXPR_PKG}.")]
        assert not stray, f"classes outside the core package are in the matrix: {stray}"
        assert expected == set(REGISTERED), (
            "the set of classes the core package defines changed after "
            f"collection.\n  now defined but not covered: "
            f"{sorted(expected - set(REGISTERED))}\n"
            f"  covered but no longer defined: {sorted(set(REGISTERED) - expected)}"
        )
        assert len(REGISTERED) > 200, (
            f"only {len(REGISTERED)} classes collected; the package walk may "
            f"have stopped early"
        )

    def test_every_covered_class_is_registered_for_deserialization(self):
        """A class in the matrix can be found again when deserializing.

        Deserialization looks the class up by name, so a class the matrix
        renders but the registry cannot resolve would round-trip into the
        wrong thing or nothing at all.
        """
        ExpressionRegistry._auto_register_builtins()
        unresolved = sorted(set(REGISTERED) - set(ExpressionRegistry._registry))
        assert not unresolved, (
            f"the matrix covers classes the registry cannot resolve: {unresolved}"
        )

    def test_coverage_report(self, dummy_dialect):
        """Surface what the matrix covers, so coverage stays transparent."""
        ExpressionRegistry._auto_register_builtins()
        constructible = [fqn for fqn in REGISTERED
                         if make_instance(REGISTERED[fqn], dummy_dialect)[0] is not None]
        assert constructible
        print(
            f"\nexpression matrix: {len(constructible)} constructible, "
            f"{len(UNCONSTRUCTIBLE)} pinned-unconstructible, "
            f"{len(REGISTERED)} registered"
        )
        for fqn in UNCONSTRUCTIBLE:
            print(f"  not constructible: {fqn}")