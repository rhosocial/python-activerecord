# tests/rhosocial/activerecord_test/feature/rules/test_shared_defaults.py
"""The defaults that more than one signature has to agree on.

``.claude/rules/constants.md`` settles what a value read from several places
owes: a module-level constant, and a test that pins it. The second check in
``test_constant_discipline.py`` enforces the first half mechanically -- a
value one name answers in two places is a finding -- but it reads the AST
alone, so it cannot know that two sites agreeing is *required*. That knowledge
lives here.

Three things are pinned, one per shape the twenty-one groups fell into.

Signatures that must agree
    A sync method and its async twin answer one question, and the parity rule
    (``dev-sync-async-parity``) requires them to answer it the same way. The
    default is part of that answer. These tests assert the twins still share
    one default *object* -- not merely an equal one -- so a change to one
    without the other fails here rather than drifting silently.

Declarations that are each class's own
    A class's ``KIND_RESERVED`` or ``PARAMETERS`` is its statement of what it
    is, and the repetition across classes is identity rather than a fact
    written twice. These tests walk the classes and assert the shape, so a
    new class joining a family with a misspelling fails the suite instead of
    quietly deriving a wrong kind or comparing unequal to its siblings.

Definitions and their readers
    A default hoisted out of a signature is read by the signature and, often,
    by a caller that used to spell the literal. These tests assert the reader
    sees the definition, so deleting the definition -- or pointing a reader
    at a second copy -- fails here.

The tests read ``inspect.signature`` rather than the AST because a default
that has been replaced by a *name* is what is being asserted: the AST check
sees no literal and is satisfied, and only a signature comparison can say
whether the twins still hold the same value.
"""

import ast
import inspect
from pathlib import Path

import pytest

from rhosocial.activerecord.backend.expression.introspection import (
    VALUE_SAMPLE_LIMIT,
)
from rhosocial.activerecord.backend.impl.sqlite.expression.fts5 import (
    HIGHLIGHT_PREFIX_MARKER,
    HIGHLIGHT_SUFFIX_MARKER,
)

pytestmark = [pytest.mark.feature]


def _default_of(func, name):
    """The default *object* a signature offers for parameter *name*."""
    parameter = inspect.signature(func).parameters[name]
    assert parameter.default is not inspect.Parameter.empty, (
        f"{func.__qualname__} no longer offers a default for {name!r}"
    )
    return parameter.default


# ---------------------------------------------------------------------------
# Signatures that must agree: the sync and async twins
# ---------------------------------------------------------------------------


def test_the_value_sample_twins_share_one_limit():
    """Four signatures ask the value-sample question and must answer alike.

    The statement owns the number (its dialect formatter renders ``LIMIT``),
    and the manager's statement factory and its sync and async sampling
    methods forward it. Identity rather than equality is asserted: a second
    copy would pass an ``==`` and fail here.
    """
    from rhosocial.activerecord.backend.expression.introspection import (
        ColumnValueSampleQueryStatement,
    )
    from rhosocial.activerecord.backend.introspection.base import (
        AbstractIntrospector,
        AsyncAbstractIntrospector,
    )

    statement = _default_of(ColumnValueSampleQueryStatement.__init__, "limit")
    factory = _default_of(AbstractIntrospector.column_value_sample_statement, "limit")
    sync = _default_of(AbstractIntrospector.sample_column_values, "limit")
    async_ = _default_of(AsyncAbstractIntrospector.sample_column_values, "limit")

    for name, value in (
        ("statement factory", factory),
        ("sync sample_column_values", sync),
        ("async sample_column_values", async_),
    ):
        assert value is statement, (
            f"{name} no longer reads VALUE_SAMPLE_LIMIT: it now defaults to "
            f"{value!r} while the statement defaults to {statement!r}"
        )
    assert statement == VALUE_SAMPLE_LIMIT


def test_the_batch_twins_share_one_batch_size_and_page_size():
    """The sync and async executors batch and page the same amounts.

    A batch is a transaction-shape decision and a page is a memory decision;
    neither may differ between the two executors, because a caller that
    swapped executors would silently change how much work sits in one commit.
    """
    from rhosocial.activerecord.backend.base.batch_execution import (
        DEFAULT_BATCH_SIZE,
        DEFAULT_PAGE_SIZE,
    )

    for cls_name, module_name in (
        ("BatchExecutionMixin", "sync"),
        ("AsyncBatchExecutionMixin", "async"),
    ):
        module = __import__(
            "rhosocial.activerecord.backend.base.batch_execution",
            fromlist=[cls_name],
        )
        cls = getattr(module, cls_name)
        assert _default_of(cls.execute_batch_dml, "batch_size") is DEFAULT_BATCH_SIZE, (
            f"{module_name} execute_batch_dml no longer reads DEFAULT_BATCH_SIZE"
        )
        assert _default_of(cls.execute_batch_dql, "page_size") is DEFAULT_PAGE_SIZE, (
            f"{module_name} execute_batch_dql no longer reads DEFAULT_PAGE_SIZE"
        )

    assert DEFAULT_BATCH_SIZE == 100
    assert DEFAULT_PAGE_SIZE == 1000


def test_the_pragma_twins_share_one_checkpoint_mode():
    """Both checkpoint introspectors run the same PRAGMA the same way.

    ``PASSIVE`` is the only mode that never blocks, so it is what a caller
    who named nothing wants; the async twin must not choose differently.
    """
    from rhosocial.activerecord.backend.impl.sqlite.introspection.pragma_introspector import (
        WAL_CHECKPOINT_DEFAULT_MODE,
        AsyncPragmaIntrospector,
        PragmaIntrospector,
    )

    sync = _default_of(PragmaIntrospector.wal_checkpoint, "mode")
    async_ = _default_of(AsyncPragmaIntrospector.wal_checkpoint, "mode")

    assert sync is WAL_CHECKPOINT_DEFAULT_MODE
    assert async_ is WAL_CHECKPOINT_DEFAULT_MODE
    assert WAL_CHECKPOINT_DEFAULT_MODE == "PASSIVE"


def test_the_count_twins_share_one_wildcard_column():
    """Both ``count()`` methods count every row when the caller names none.

    ``COUNT(*)`` and ``COUNT(column)`` are different questions, and the
    wildcard is what tells them apart, so the two twins must offer the same
    default. Identity is asserted: a second copy would pass ``==`` and fail
    here.
    """
    from rhosocial.activerecord.query.aggregate import (
        COUNT_ALL_COLUMNS,
        AggregateQueryMixin,
        AsyncAggregateQueryMixin,
    )

    sync = _default_of(AggregateQueryMixin.count, "column")
    async_ = _default_of(AsyncAggregateQueryMixin.count, "column")

    assert sync is COUNT_ALL_COLUMNS
    assert async_ is COUNT_ALL_COLUMNS
    assert COUNT_ALL_COLUMNS == "*"


# ---------------------------------------------------------------------------
# Signatures that must agree
# ---------------------------------------------------------------------------


def test_the_trim_entry_points_share_one_default_direction():
    """The node, its factory and the mixin all trim the same way by default.

    ``BOTH`` is what SQL itself defaults to: ``TRIM(x)`` strips both ends. The
    node owns the question -- the dialect renders what it holds -- so the
    factory and the mixin forward their callers' choices to it, and all three
    offer the same direction when the caller names none. Identity is asserted,
    because a second copy of the string would pass ``==`` and fail here.
    """
    from rhosocial.activerecord.backend.expression.advanced_functions import (
        TRIM_DEFAULT_DIRECTION,
        TrimExpression,
    )
    from rhosocial.activerecord.backend.expression.functions.string import trim
    from rhosocial.activerecord.backend.expression.mixins import StringValueMixin

    node = _default_of(TrimExpression.__init__, "direction")
    factory = _default_of(trim, "direction")
    mixin = _default_of(StringValueMixin.trim, "direction")

    for name, value in (("the trim() factory", factory), ("the mixin", mixin)):
        assert value is node, (
            f"{name} no longer reads TRIM_DEFAULT_DIRECTION: it defaults to "
            f"{value!r} while the node defaults to {node!r}"
        )
    assert node is TRIM_DEFAULT_DIRECTION


def test_the_join_entry_points_share_one_default_join_type():
    """Four signatures answer "what join does an unnamed caller get" alike.

    The join clause owns the question -- it is the node the dialect renders,
    and the phrase table beside it already decides how every join type is
    spelled -- so the clause's own ``join()`` and the query layer's sync and
    async ``natural_join`` read the default off that table rather than writing
    the phrase down again.
    """
    from rhosocial.activerecord.backend.expression.query_parts import (
        DEFAULT_JOIN_TYPE,
        JoinClause,
    )
    from rhosocial.activerecord.query.async_join import AsyncJoinQueryMixin
    from rhosocial.activerecord.query.join import JoinQueryMixin

    constructor = _default_of(JoinClause.__init__, "join_type")
    chained = _default_of(JoinClause.join, "join_type")
    sync = _default_of(JoinQueryMixin.natural_join, "join_type")
    async_ = _default_of(AsyncJoinQueryMixin.natural_join, "join_type")

    for name, value in (
        ("JoinClause.join", chained),
        ("sync natural_join", sync),
        ("async natural_join", async_),
    ):
        assert value is constructor, (
            f"{name} no longer reads DEFAULT_JOIN_TYPE: it defaults to "
            f"{value!r} while JoinClause.__init__ defaults to {constructor!r}"
        )
    assert constructor is DEFAULT_JOIN_TYPE
    assert DEFAULT_JOIN_TYPE == "JOIN"


def test_the_diagram_and_log_entry_points_share_one_default_kind():
    """Four signatures render the same diagram shape when none is named.

    ``to_mermaid()`` is the method whose branch decides what a kind means, so
    it owns the default; the procedure result's ``diagram()`` and the sync and
    async ``static_diagram()`` forward their callers' choices to it.
    """
    from rhosocial.activerecord.backend.named_expression.defaults import (
        DEFAULT_DIAGRAM_KIND,
    )
    from rhosocial.activerecord.backend.named_expression.diagram import (
        ProcedureDiagram,
    )
    from rhosocial.activerecord.backend.named_expression.procedure import (
        AsyncProcedure,
        Procedure,
        ProcedureResult,
    )

    renderer = _default_of(ProcedureDiagram.to_mermaid, "kind")
    from_result = _default_of(ProcedureResult.diagram, "kind")
    static = _default_of(Procedure.static_diagram, "kind")
    static_async = _default_of(AsyncProcedure.static_diagram, "kind")

    for name, value in (
        ("ProcedureResult.diagram", from_result),
        ("sync static_diagram", static),
        ("async static_diagram", static_async),
    ):
        assert value is renderer, (
            f"{name} no longer reads DEFAULT_DIAGRAM_KIND: it defaults to "
            f"{value!r} while to_mermaid defaults to {renderer!r}"
        )
    assert renderer is DEFAULT_DIAGRAM_KIND
    assert DEFAULT_DIAGRAM_KIND == "flowchart"


def test_the_log_methods_share_one_default_level():
    """Every procedure context logs at the same level by default.

    A procedure's ``log()`` is the one that records an entry, and the diagram
    renderer's dry-run contexts mirror it so a procedure behaves the same
    whether or not it is really running. All four read one definition.
    """
    from rhosocial.activerecord.backend.named_expression.defaults import (
        DEFAULT_LOG_LEVEL,
    )
    from rhosocial.activerecord.backend.named_expression.diagram import (
        _AsyncDryRunContext,
        _DryRunContext,
    )
    from rhosocial.activerecord.backend.named_expression.procedure import (
        AsyncProcedureContext,
        ProcedureContext,
    )

    contexts = (
        ("ProcedureContext", ProcedureContext.log),
        ("AsyncProcedureContext", AsyncProcedureContext.log),
        ("_DryRunContext", _DryRunContext.log),
        ("_AsyncDryRunContext", _AsyncDryRunContext.log),
    )
    for name, method in contexts:
        assert _default_of(method, "level") is DEFAULT_LOG_LEVEL, (
            f"{name}.log no longer reads DEFAULT_LOG_LEVEL"
        )
    assert DEFAULT_LOG_LEVEL == "INFO"


def test_the_diagram_entry_points_share_one_default_procedure_name():
    """A diagram labels an unnamed procedure the same way wherever it is built.

    ``ProcedureDiagram`` owns the question -- it is the object that carries the
    name -- so the factory that builds one and the procedure result that asks
    for a diagram both read the same default.
    """
    from rhosocial.activerecord.backend.named_expression.defaults import (
        DEFAULT_PROCEDURE_NAME,
    )
    from rhosocial.activerecord.backend.named_expression.diagram import (
        ProcedureDiagram,
    )
    from rhosocial.activerecord.backend.named_expression.procedure import (
        ProcedureResult,
    )

    constructor = _default_of(ProcedureDiagram.__init__, "procedure_name")
    from_result = _default_of(ProcedureDiagram.from_result, "procedure_name")
    from_result_of = _default_of(ProcedureResult.diagram, "procedure_name")

    for name, value in (
        ("ProcedureDiagram.from_result", from_result),
        ("ProcedureResult.diagram", from_result_of),
    ):
        assert value is constructor, (
            f"{name} no longer reads DEFAULT_PROCEDURE_NAME: it defaults to "
            f"{value!r} while ProcedureDiagram.__init__ defaults to {constructor!r}"
        )
    assert constructor is DEFAULT_PROCEDURE_NAME
    assert DEFAULT_PROCEDURE_NAME == "Procedure"


def test_the_length_entry_points_share_one_default_unit():
    """The node and the factory that wraps it ask for the same unit by default.

    ``char`` is the unit SQL's ``CHAR_LENGTH`` means, and the node owns the
    question: it is the one that validates the unit against the closed set and
    records it. The factory forwards the caller's choice, so a caller who
    never named one gets the unit the node would have applied anyway.
    """
    from rhosocial.activerecord.backend.expression.functions.string import (
        CHAR_LENGTH_DEFAULT_UNIT,
        CharLengthFunction,
        length,
    )

    node = _default_of(CharLengthFunction.__init__, "unit")
    factory = _default_of(length, "unit")

    assert factory is node, (
        f"length() no longer reads CHAR_LENGTH_DEFAULT_UNIT: it defaults to "
        f"{factory!r} while CharLengthFunction defaults to {node!r}"
    )
    assert node is CHAR_LENGTH_DEFAULT_UNIT
    assert CHAR_LENGTH_DEFAULT_UNIT == "char"


def test_the_example_migrations_agree_on_the_table_they_create_and_drop():
    """The custom-table migration's two halves name the same table.

    ``create_custom_table`` builds it and ``drop_custom_table`` drops it, and
    the migration class that drives them both carries the name too. A name
    that drifted between them would leave a table the ``down()`` could not
    drop, which is a silent failure rather than an error.

    The definition lives in the examples' leaf module rather than in
    ``expressions.py``, and the class in ``migrations.py`` reads it from there:
    that module is what removes the edge a migration class had to the
    expressions module for nothing but a string.
    """
    from rhosocial.activerecord.backend.impl.sqlite.examples import defaults
    from rhosocial.activerecord.backend.impl.sqlite.examples.named_migrations import (
        expressions,
        migrations,
    )

    created = _default_of(expressions.create_custom_table, "table_name")
    dropped = _default_of(expressions.drop_custom_table, "table_name")
    driven = migrations.V003CreateCustomTable.table_name

    assert dropped is created, (
        "drop_custom_table no longer reads the same table name as "
        "create_custom_table"
    )
    assert driven is created, (
        "V003CreateCustomTable.table_name no longer reads the same name as "
        "create_custom_table"
    )
    assert created is defaults.DEFAULT_CUSTOM_TABLE_NAME
    assert created == "custom_table"


def test_the_order_examples_default_to_one_pending_status():
    """The write and clause examples agree on a new order's status.

    Three examples over the same fixture table default to ``pending``, and a
    status that drifted between them would insert or filter on a status the
    fixture does not hold -- a silent mismatch rather than an error.

    The definition lives in the examples' leaf module rather than in
    ``order_dml.py``, which is what removes the edge the clause examples had
    to the DML examples for nothing but a string.
    """
    from rhosocial.activerecord.backend.impl.sqlite.examples import defaults
    from rhosocial.activerecord.backend.impl.sqlite.examples.named_expressions import (
        order_clauses,
        order_dml,
    )

    defaults_of = (
        _default_of(order_dml.add_order, "status"),
        _default_of(order_dml.add_payment, "status"),
        _default_of(order_clauses.compound_example, "status"),
    )
    for value in defaults_of:
        assert value is defaults.DEFAULT_ORDER_STATUS, (
            "an order example no longer reads DEFAULT_ORDER_STATUS"
        )
    assert defaults.DEFAULT_ORDER_STATUS == "pending"


def _relative_imports(module):
    """Every module *module* reaches for inside its own package, resolved.

    ``from ..defaults import X`` in a module of ``...examples.named_expressions``
    names ``...examples.defaults``. The resolution is written out because a
    level is not a module name, and what is being asserted here is a direction
    -- which module a reader took a name from -- that only the resolved name
    can state.
    """
    path = Path(inspect.getsourcefile(module))
    package = module.__name__.rsplit(".", 1)[0]
    parts = package.split(".")
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    found = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom) or not node.module:
            continue
        # One dot is this module's own package, two its parent, and so on
        # outward -- so ``level`` climbs ``level - 1`` packages up.
        keep = len(parts) - (node.level - 1)
        if keep <= 0:
            continue
        found.add(".".join(parts[:keep] + [node.module]))
    return found


def test_no_example_module_reads_a_default_out_of_a_sibling_example():
    """The leaf module is where an example module takes a shared default from.

    The defect this fixes was a direction, not a count: ``order_clauses``
    imported ``order_dml`` and ``migrations`` imported ``expressions`` for
    nothing but a string, so whichever module happened to declare it first
    owned what the others read, and the next reader had to know which of the
    three to look in. Both spellings are an import, so no count or AST check
    can tell a default from a registry table -- the direction is pinned here
    instead, on the two edges that were actually walked the wrong way, and on
    the leaf remaining reachable from both sides.
    """
    from rhosocial.activerecord.backend.impl.sqlite.examples import defaults
    from rhosocial.activerecord.backend.impl.sqlite.examples.named_expressions import (
        order_clauses,
        order_dml,
    )
    from rhosocial.activerecord.backend.impl.sqlite.examples.named_migrations import (
        expressions,
        migrations,
    )

    for reader, sibling in ((order_clauses, order_dml), (migrations, expressions)):
        reached = _relative_imports(reader)
        assert sibling.__name__ not in reached, (
            f"{reader.__name__} reads a default out of {sibling.__name__} again"
        )
        assert defaults.__name__ in reached, (
            f"{reader.__name__} no longer reads the examples' leaf module"
        )


def test_the_count_caller_no_longer_spells_the_wildcard_it_gets_for_free():
    """The dialect formatter does not restate the count's own default.

    ``count(dialect, "*")`` and ``count(dialect)`` are the same question, so
    the dialect that builds a table count asks it the short way. This is the
    one behavioural difference in the change: a call site lost an argument
    that restated the default it was already getting, and nothing else.
    """
    from rhosocial.activerecord.backend.expression import count

    assert _default_of(count, "expr") == "*", (
        "count() no longer defaults to counting every row"
    )


# ---------------------------------------------------------------------------
# Declarations that are each class's own
# ---------------------------------------------------------------------------


def test_the_fts5_expressions_share_one_marker_pair():
    """``highlight`` and ``snippet`` wrap a match the same way.

    They are not sync and async twins but two expressions asking one
    question, and the dialect has no say: the markers are literal text in
    the returned string rather than SQL. Identity is asserted so a second
    copy of either marker fails here.
    """
    from rhosocial.activerecord.backend.impl.sqlite.expression.fts5 import (
        SQLiteFTS5HighlightExpression,
        SQLiteFTS5SnippetExpression,
    )

    for cls in (SQLiteFTS5HighlightExpression, SQLiteFTS5SnippetExpression):
        assert _default_of(cls.__init__, "prefix_marker") is HIGHLIGHT_PREFIX_MARKER, (
            f"{cls.__name__} no longer reads HIGHLIGHT_PREFIX_MARKER"
        )
        assert _default_of(cls.__init__, "suffix_marker") is HIGHLIGHT_SUFFIX_MARKER, (
            f"{cls.__name__} no longer reads HIGHLIGHT_SUFFIX_MARKER"
        )

    assert HIGHLIGHT_PREFIX_MARKER == "<b>"
    assert HIGHLIGHT_SUFFIX_MARKER == "</b>"


def _concrete_data_types():
    """Every concrete ``DataType`` subclass reachable from the base."""
    from rhosocial.activerecord.backend.expression.types import DataType

    seen, stack, found = set(), [DataType], []
    while stack:
        klass = stack.pop()
        if klass in seen:
            continue
        seen.add(klass)
        stack.extend(klass.__subclasses__())
        if klass is not DataType and not inspect.isabstract(klass):
            found.append(klass)
    return found


def test_every_type_whose_identity_is_one_field_reads_the_shared_tuple():
    """``PARAMETERS`` is each class's own statement of what it is.

    A class declaring ``PARAMETERS = ("length",)`` is saying "my width is what
    makes me the column I am", and several classes say it -- which is identity
    rather than one fact written several times, because the classes that say it
    are saying it about *themselves* and adding a sixth would not need to agree
    with the first five.

    What does have to hold is that the classes saying it say the *same thing*:
    a spelling that drifted between two of them would change which two
    declarations compare equal, and ``identity()`` is what ``==`` and
    ``__hash__`` read. So the shared tuples are defined once in
    ``expression/types/_base.py`` -- beside the ``PARAMETERS`` declaration
    whose vocabulary they come from -- and this test walks the classes and
    asserts the shape.
    """
    from rhosocial.activerecord.backend.expression.types import (
        LENGTH_PARAMETERS,
        PRECISION_PARAMETERS,
        UNSIGNED_PARAMETERS,
    )

    declared = []
    for klass in _concrete_data_types():
        if not klass.PARAMETERS:
            continue
        declared.append((klass, klass.PARAMETERS))
        # ``PARAMETERS`` names attributes, never computed or transformed
        # values. A field it names must be one the constructor stores, or
        # ``identity()`` raises the moment two declarations are compared.
        signature = inspect.signature(klass.__init__)
        for field in klass.PARAMETERS:
            assert field in signature.parameters, (
                f"{klass.__name__}.PARAMETERS names {field!r}, which its "
                "__init__ does not take -- identity() would raise"
            )

    # Each one-field family reads the same object, so no two classes have
    # quietly grown separate spellings of it.
    by_parameters = {}
    for klass, parameters in declared:
        by_parameters.setdefault(parameters, []).append(klass)

    assert by_parameters.get(LENGTH_PARAMETERS), "no type declares a length identity"
    assert by_parameters.get(PRECISION_PARAMETERS), "no type declares a precision identity"
    assert by_parameters.get(UNSIGNED_PARAMETERS), "no type declares an unsigned identity"

    for parameters, classes in by_parameters.items():
        if parameters not in (LENGTH_PARAMETERS, PRECISION_PARAMETERS, UNSIGNED_PARAMETERS):
            continue
        for klass in classes:
            assert klass.PARAMETERS is parameters, (
                f"{klass.__name__}.PARAMETERS is a copy rather than the shared "
                f"{parameters!r}"
            )

    # The fields the tuples name are the vocabulary the base documents.
    assert LENGTH_PARAMETERS == ("length",)
    assert PRECISION_PARAMETERS == ("precision",)
    assert UNSIGNED_PARAMETERS == ("unsigned",)


def test_the_sqlite_types_keep_their_identifier_token_whole():
    """``KIND_RESERVED`` is each SQLite type's statement of its own naming.

    ``SQLite`` is a compound word, and the general capital-run rule would split
    it into ``sq_lite_...``; the class name keeps the token whole instead. The
    backend owns that list -- the core names no backend -- so the SQLite type
    classes declare it about themselves, and the existing walk in
    ``test_kind_naming.py`` asserts they derive a ``sqlite_`` kind from it.

    The value is shared rather than re-typed per class so that a class added to
    the family cannot quietly adopt a second spelling of the same token: the
    token this package's own declarations keep whole is one fact.
    """
    from rhosocial.activerecord.backend.impl.sqlite.expression.types import (
        SQLiteBlobType,
        SQLiteIntegerType,
        SQLiteNumericType,
        SQLiteRealType,
        SQLiteTextType,
    )

    declared = (
        SQLiteIntegerType,
        SQLiteTextType,
        SQLiteRealType,
        SQLiteNumericType,
        SQLiteBlobType,
    )
    for klass in declared:
        assert klass.KIND_RESERVED == ("SQLite",), (
            f"{klass.__name__} no longer keeps the SQLite token whole"
        )
        assert klass.kind().startswith("sqlite_"), (
            f"{klass.__name__} derives {klass.kind()!r} rather than a sqlite_ kind"
        )


# ---------------------------------------------------------------------------
# Declarations and their readers
# ---------------------------------------------------------------------------


def test_every_cli_offering_an_output_reads_the_one_output_choices():
    """The three subcommands that offer an output format offer the same four.

    ``OUTPUT_CHOICES`` is presentation, and the four names are the same four
    the provider factory can build: table, json, csv and tsv. Defining the
    list once in ``cli/output.py`` -- beside the factory that has to produce
    every member -- is what keeps "offered" and "producible" from drifting
    apart, because a subcommand that added a spelling of its own would be
    advertising an output nobody can build.

    ``cli/info.py`` deliberately keeps its own two-format list: it offers a
    different question (a summary, which has no tabular form worth printing)
    and its value is not the one this test pins.
    """
    from rhosocial.activerecord.backend.impl.sqlite.cli import (
        introspect,
        output,
        query,
        status,
    )

    readers = (introspect.OUTPUT_CHOICES, query.OUTPUT_CHOICES, status.OUTPUT_CHOICES)
    for choices in readers:
        assert choices is output.OUTPUT_CHOICES, (
            "a CLI no longer reads cli.output.OUTPUT_CHOICES"
        )
    assert output.OUTPUT_CHOICES == ["table", "json", "csv", "tsv"]


def test_the_crud_example_registries_share_one_metadata_table():
    """``delete``, ``insert`` and ``update`` declare the same family.

    They are the three write operations over the same example tables, so the
    category and the priority they register under are one decision. Writing
    the table out three times would be three copies of it: renumber the CRUD
    priority in two of them and the third would silently keep the old one.

    ``insert`` owns the table because it is the write that introduces the
    family; the other two import it so the registry sees one value under one
    name. The other example families keep their own tables -- they are
    different families with different categories and priorities -- and sharing
    the mechanism is not sharing the value.
    """
    from rhosocial.activerecord.backend.impl.sqlite.examples import (
        delete,
        insert,
        update,
    )

    assert delete.META is insert.META, "delete no longer reads insert's META"
    assert update.META is insert.META, "update no longer reads insert's META"
    assert insert.META == {"category": "crud", "priority": 10}

    # The other families' tables stay their own.
    from rhosocial.activerecord.backend.impl.sqlite.examples import ddl

    assert ddl.META != insert.META, "ddl collapsed into the CRUD family"
    assert ddl.META["category"] == "ddl"


# ---------------------------------------------------------------------------
# Signatures that must agree
# ---------------------------------------------------------------------------
