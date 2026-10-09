# tests/rhosocial/activerecord_test/feature/query/test_column_suggestion_protocol.py
"""The column-type suggestion protocol: entry list, backend authority, failures.

Three questions, and nothing here needs a database to answer them:

1. **Is the entry list closed and complete?** Every common Python type resolves,
   so a backend is never asked to suggest for something the framework does not
   model.
2. **Whose answer is it?** The dialect's table when a dialect is in hand, core's
   neutral table otherwise. A fake dialect overriding one entry must change
   exactly that entry and nothing else — otherwise the backend has no authority
   and the whole protocol is decoration.
3. **What fails, and does it fail loudly?** ``Any``, a bare ``Union``, an
   unregistered custom class and ``UNSUPPORTED`` all raise. There is no
   permissive column left to absorb them, so the failure arrives where the field
   is declared.

Plus the boolean algebra surface and its literal discipline: ``TRUE``/``FALSE``
as keywords, never ``1``/``0``, which PostgreSQL rejects outright
(``operator does not exist: boolean = integer``).
"""

# tests/rhosocial/activerecord_test/feature/query/test_column_suggestion_protocol.py
import datetime
import decimal
import enum
import typing
import uuid
from typing import Any, Dict, List, Optional, Type, Union

import pytest

from rhosocial.activerecord.backend.dialect.mixins import ColumnSuggestionMixin
from rhosocial.activerecord.backend.expression.column_suggestions import (
    COLUMN_TYPE_ENTRIES,
    NEUTRAL_COLUMN_TYPE_SUGGESTIONS,
    UNSUPPORTED,
)
from rhosocial.activerecord.backend.expression.column_types import (
    ColumnBase,
    DateTimeColumn,
    FloatColumn,
    IntegerColumn,
    JSONColumn,
    NumericColumn,
    StringColumn,
)
from rhosocial.activerecord.backend.expression.column_suggestions import (
    ColumnTypeResolutionError,
)
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
from rhosocial.activerecord.backend.impl.sqlite.mixins.column_suggestion import (
    SQLITE_COLUMN_TYPE_SUGGESTIONS,
)
from rhosocial.activerecord.base.fields import UseColumnType

from column_helpers import build_column


def sqlite_dialect():
    """A version-adapted SQLite dialect (see test_typed_columns for why)."""
    dialect = SQLiteDialect()
    dialect._version = (3, 46, 1)
    return dialect


def column_class_for(annotation, dialect=None, column_type=None):
    """Resolve *annotation* the way the model layer does: through a dialect.

    Resolution is the dialect's method, so a test that wants to know "which
    column class does this annotation mean" has to say which backend's answer it
    is asking for. The default is SQLite, whose table is core's.
    """
    if dialect is None:
        dialect = sqlite_dialect()
    return dialect.column_class_for(annotation, column_type)


class NarrowingDialect(SQLiteDialect, ColumnSuggestionMixin):
    """A backend that disagrees with its parent backend about exactly one entry.

    Subclasses SQLite rather than the mixin alone so that the column *expression*
    layer still renders: this is about who answers the suggestion, not about
    being able to format SQL. Its table is **SQLite's own table** with one entry
    replaced, not the neutral baseline -- so "the seventeen other answers are
    untouched" is a statement about this dialect versus the backend it extends,
    which stays true however either table is filled in. ``str`` answers with a
    class neither would have picked, which is what makes the authority
    observable: if the framework consulted its own table first, this would be
    ignored.
    """

    COLUMN_TYPE_SUGGESTIONS: Dict[Any, Type[ColumnBase]] = {
        **SQLITE_COLUMN_TYPE_SUGGESTIONS,
        str: FloatColumn,
    }


class RefusingDialect(SQLiteDialect, ColumnSuggestionMixin):
    """A backend with no default column class for one entry.

    The honest "this backend has none", which is what MySQL 5.6 and Firebird
    have to say about JSON. It must reach the caller as a failure rather than as
    a fallback to core's guess — that is the difference between a backend
    declaring a limit and the framework papering over one. Built on the same
    table the other fake dialect uses, so the refusal is the only difference.
    """

    COLUMN_TYPE_SUGGESTIONS: Dict[Any, Type[ColumnBase]] = {
        **SQLITE_COLUMN_TYPE_SUGGESTIONS,
        dict: UNSUPPORTED,
    }


# ---------------------------------------------------------------------------
# 1. The entry list
# ---------------------------------------------------------------------------

_ENTRY_IDS = [getattr(entry, "__name__", str(entry)) for entry in COLUMN_TYPE_ENTRIES]


def test_entry_list_is_the_closed_set_in_declared_order():
    """Order is the protocol's reading order, and a backend enumerates it."""
    assert _ENTRY_IDS == [
        "bool",
        "int",
        "float",
        "Decimal",
        "str",
        "bytes",
        "bytearray",
        "date",
        "time",
        "datetime",
        "timedelta",
        "UUID",
        "dict",
        "list",
        "tuple",
        "set",
        "frozenset",
        "Enum",
    ]


def test_entry_list_has_no_duplicates():
    """A duplicate would make 'answer every entry' ambiguous."""
    assert len(set(COLUMN_TYPE_ENTRIES)) == len(COLUMN_TYPE_ENTRIES)


def test_neutral_table_answers_every_entry():
    """The dialect-less baseline is complete; a hole would be a silent gap."""
    missing = [e for e in COLUMN_TYPE_ENTRIES if e not in NEUTRAL_COLUMN_TYPE_SUGGESTIONS]
    assert missing == []


def test_unsupported_is_not_a_column_class():
    """The sentinel is a refusal, not a column. This is the whole point of it.

    A universal column that answers for everything is what this protocol
    replaced: it offers ``.like()`` on an integer and only the database finds
    out. So the answer for "no column class here" has to be a value that cannot
    be mistaken for one.
    """
    assert UNSUPPORTED not in [cls for cls in NEUTRAL_COLUMN_TYPE_SUGGESTIONS.values()]
    assert not isinstance(UNSUPPORTED, type)
    assert not issubclass(type(UNSUPPORTED), ColumnBase)


# ---------------------------------------------------------------------------
# 2. Every entry resolves
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("entry", COLUMN_TYPE_ENTRIES, ids=_ENTRY_IDS)
def test_every_entry_has_a_class_in_the_neutral_table(entry):
    """Core's static view answers for every entry — a hole would be a lie to a checker."""
    assert isinstance(NEUTRAL_COLUMN_TYPE_SUGGESTIONS[entry], type)
    assert issubclass(NEUTRAL_COLUMN_TYPE_SUGGESTIONS[entry], ColumnBase)


@pytest.mark.parametrize("entry", COLUMN_TYPE_ENTRIES, ids=_ENTRY_IDS)
def test_every_entry_resolves_through_the_dialect(entry):
    assert issubclass(column_class_for(entry, sqlite_dialect()), ColumnBase)


@pytest.mark.parametrize("entry", COLUMN_TYPE_ENTRIES, ids=_ENTRY_IDS)
def test_the_sqlite_table_answers_every_entry(entry):
    """A backend's own table is complete; that is the contract, checked here.

    Not audited from core across all backends -- they differ too much for one
    shared sweep to say anything -- but SQLite lives in core, so core can hold
    its table to the rule the other nine will be held to in Phase 3.
    """
    assert entry in sqlite_dialect().suggested_column_types()


def test_date_and_time_are_separate_entries_sharing_a_column_class():
    """They are distinct entries because the framework asks about each of them.

    They answer the same column class today, which is a modelling gap the entry
    list is what will eventually close (splitting ``DateTimeColumn`` by operation
    set). Asserting the shared answer keeps that gap visible: when one of them
    splits, this test is what notices.
    """
    assert column_class_for(datetime.date) is DateTimeColumn
    assert column_class_for(datetime.time) is DateTimeColumn


def test_boolean_is_its_own_entry_not_an_integer():
    """``bool`` is an ``int`` subclass; the entry order is what keeps them apart.

    Without the order, ``bool`` would walk to ``int`` and a truth-value field
    would offer integer arithmetic — which MySQL and SQLite would happily
    execute on a column holding 0/1.
    """
    assert COLUMN_TYPE_ENTRIES.index(bool) < COLUMN_TYPE_ENTRIES.index(int)
    assert column_class_for(bool, sqlite_dialect()) is not column_class_for(int, sqlite_dialect())


# ---------------------------------------------------------------------------
# 3. The backend is the authority
# ---------------------------------------------------------------------------


def test_backend_override_changes_only_its_own_entry():
    """One overridden entry, one changed answer, seventeen untouched."""
    dialect = NarrowingDialect()
    dialect._version = (3, 46, 1)

    assert column_class_for(str, dialect) is FloatColumn
    assert column_class_for(str, sqlite_dialect()) is StringColumn

    for entry in COLUMN_TYPE_ENTRIES:
        if entry is str:
            continue
        assert column_class_for(entry, dialect) is column_class_for(entry, sqlite_dialect())


def test_the_neutral_table_is_the_static_view_and_says_so():
    """Core's table is what a checker reads, not what a dialect is handed.

    It is the answer for ``str``, and it is not the *authority*: SQLite reads it
    through its own table, and a backend that disagrees is not overruled. Keeping
    the two apart is the whole point of the table having moved off the
    resolution path -- a core table consulted at runtime would be answering for
    backends it knows nothing about.
    """
    assert NEUTRAL_COLUMN_TYPE_SUGGESTIONS[str] is StringColumn
    assert sqlite_dialect().suggested_column_types()[str] is StringColumn


def test_resolution_without_a_dialect_is_not_a_path_there_is():
    """A class has to answer; the bare ``column_class_for(str)`` shape is gone.

    There is no free function any more, and that is the ruling rather than an
    omission: a module-level one would have to invent a dialect or fall back to
    core's table, and both of those are the core-side answer that was removed.
    The dialect method is the entry point, and the model layer always has a
    dialect because ActiveRecord injects it before building an expression.
    """
    import rhosocial.activerecord.base as base_package

    assert not hasattr(base_package, "build_column")
    assert not hasattr(base_package, "column_class_for")
    assert not hasattr(base_package, "column_dispatch")


def test_a_dialect_without_the_hook_raises_rather_than_defaulting():
    """A backend that never declared a table has no answer, not a default one.

    Silently handing such a dialect core's table would make the protocol
    unfalsifiable: every model would work, and nothing would ever notice that a
    backend had not answered.
    """

    class BareDialect(SQLiteDialect):
        suggested_column_types = None

    with pytest.raises(TypeError):
        # Not a ColumnTypeResolutionError: the dialect has no suggestion
        # machinery at all, so calling it is a programming error rather than a
        # resolution failure.
        BareDialect().column_class_for(str)


def test_a_dialect_whose_table_is_incomplete_is_told_so():
    """The missing-entry error names the gap rather than silently defaulting."""

    class PartialDialect(SQLiteDialect, ColumnSuggestionMixin):
        COLUMN_TYPE_SUGGESTIONS = {str: StringColumn}

    with pytest.raises(ColumnTypeResolutionError, match="does not answer for"):
        column_class_for(int, PartialDialect())


def test_a_table_entry_that_is_not_a_column_class_raises():
    """A malformed table is a backend bug, caught where it is written down."""

    class WrongDialect(SQLiteDialect, ColumnSuggestionMixin):
        COLUMN_TYPE_SUGGESTIONS = {**NEUTRAL_COLUMN_TYPE_SUGGESTIONS, str: "StringColumn"}

    with pytest.raises(ColumnTypeResolutionError, match="neither a ColumnBase subclass"):
        column_class_for(str, WrongDialect())


def test_a_backend_may_extend_the_table_with_an_entry_of_its_own():
    """The extension path for a Python type the framework does not model."""

    class Complex(complex):
        pass

    class ExtendingDialect(SQLiteDialect, ColumnSuggestionMixin):
        COLUMN_TYPE_SUGGESTIONS = {
            **NEUTRAL_COLUMN_TYPE_SUGGESTIONS,
            Complex: JSONColumn,
        }

    dialect = ExtendingDialect()
    assert column_class_for(Complex, dialect) is JSONColumn
    # ...and core entries keep working alongside it.
    assert column_class_for(int, dialect) is IntegerColumn


def test_the_returned_table_is_a_copy():
    """A caller walking the table must not mutate what the next field reads."""
    dialect = sqlite_dialect()
    table = dialect.suggested_column_types()
    table.clear()
    assert dialect.suggested_column_types() == table | dialect.suggested_column_types()


# ---------------------------------------------------------------------------
# 4. Unsupported entries and unclassifiable annotations
# ---------------------------------------------------------------------------


def test_unsupported_entry_fails_and_names_the_declaration_that_fixes_it():
    with pytest.raises(ColumnTypeResolutionError) as excinfo:
        column_class_for(dict, RefusingDialect())
    message = str(excinfo.value)
    assert "UNSUPPORTED" in message
    assert "UseColumnType" in message


def test_unsupported_does_not_leak_into_other_entries():
    """One refusal must not make the whole backend unusable."""
    dialect = RefusingDialect()
    assert column_class_for(str, dialect) is StringColumn
    assert column_class_for(int, dialect) is IntegerColumn


@pytest.mark.parametrize(
    "annotation",
    [Any, Union[int, str], List[int], Dict[str, int]],
    ids=["Any", "bare-union", "parameterised-list", "parameterised-dict"],
)
def test_unclassifiable_annotations_fail(annotation):
    """``Any``, a bare ``Union``, a parameterised container: no entry, no answer.

    Each of these used to become the permissive ``Column``. Now it is a
    definition-time failure naming what to write instead, which is the change
    the ruling asked for: a field the framework cannot type is a mistake in the
    model, and a silent fallback hides it until the database complains.
    """
    with pytest.raises(ColumnTypeResolutionError) as excinfo:
        column_class_for(annotation, sqlite_dialect())
    assert "UseColumnType" in str(excinfo.value)


def test_an_unregistered_custom_class_fails():
    """A class the framework does not model is unclassifiable, not a string."""

    class Money:
        pass

    with pytest.raises(ColumnTypeResolutionError, match="Cannot choose a column class"):
        column_class_for(Money, sqlite_dialect())


def test_a_subclass_of_an_entry_resolves_through_the_walk():
    """``class MyStr(str)`` is a string; the walk is what says so."""
    assert column_class_for(type("Code", (str,), {}), sqlite_dialect()) is StringColumn


def test_an_enum_subclass_resolves_to_the_enum_entry():
    """Before the subclass walk, so a ``(int, Enum)`` is not filed as an int."""
    assert column_class_for(enum.Enum, sqlite_dialect()) is StringColumn

    class Weekday(enum.IntEnum):
        MONDAY = 1

    assert column_class_for(Weekday, sqlite_dialect()) is StringColumn


def test_optional_and_annotated_still_resolve():
    Annotated = getattr(typing, "Annotated", None)
    if Annotated is None:
        pytest.skip("typing.Annotated requires Python 3.9+")

    assert column_class_for(Optional[dict], sqlite_dialect()).__name__ == "JSONColumn"
    # An unrelated marker is simply not a UseColumnType; the dialect resolves
    # from the peeled annotation and the marker is read by the model layer.
    assert column_class_for(Annotated[str, "marker"], sqlite_dialect()) is StringColumn


# ---------------------------------------------------------------------------
# 5. UseColumnType: the explicit escape hatch
# ---------------------------------------------------------------------------


def test_use_column_type_overrides_the_suggestion():
    """Naming a class bypasses the recommendation, and only the recommendation."""
    declared = UseColumnType(StringColumn)
    assert column_class_for(int, sqlite_dialect(), declared) is StringColumn


def test_the_marker_reader_finds_the_declaration_and_returns_none_without():
    """``declared_column_type`` is the read; the dialect call is the dispatch.

    Kept apart on purpose. The marker reader knows where pydantic puts things
    and nothing else, and the dialect knows how to choose a class and nothing
    else -- so neither has the other's reason to change.
    """
    from rhosocial.activerecord.base.fields import declared_column_type

    assert declared_column_type([]) is None
    assert declared_column_type(None) is None
    assert declared_column_type([UseColumnType(StringColumn)]).column_class is StringColumn


def test_two_declarations_on_one_field_are_refused():
    """A field says once what its column class is; two markers would need a pick."""
    from rhosocial.activerecord.base.fields import declared_column_type

    with pytest.raises(TypeError, match="UseColumnType declarations"):
        declared_column_type([UseColumnType(StringColumn), UseColumnType(JSONColumn)])


def test_use_column_type_saves_an_annotation_no_table_could_classify():
    """The escape hatch is what makes every other failure actionable."""
    assert column_class_for(Any, sqlite_dialect(), UseColumnType(StringColumn)) is StringColumn


def test_use_column_type_with_several_classes_is_refused():
    """Multi-candidate selection needs the capability declaration, which is not here.

    Declaring two classes is a request to negotiate with the backend, and there
    is nothing to ask yet. Taking the first silently would make the declaration
    a lie the caller cannot see.
    """
    with pytest.raises(TypeError, match="capability"):
        UseColumnType(StringColumn, JSONColumn)


def test_use_column_type_with_no_classes_is_refused():
    with pytest.raises(TypeError, match="at least one"):
        UseColumnType()


@pytest.mark.parametrize(
    "bad_factory, why",
    [
        (str, "builtin"),
        (lambda: "StringColumn", "name"),
        (lambda: StringColumn(sqlite_dialect(), "x"), "instance"),
    ],
    ids=["builtin", "string", "instance"],
)
def test_use_column_type_rejects_non_column_classes(bad_factory, why):
    """A column class is a type, never an instance — an instance carries state.

    Built through factories because a column instance needs a dialect, and
    constructing one at collection time would put a database-free object in the
    module preamble.
    """
    with pytest.raises(TypeError, match="ColumnBase"):
        UseColumnType(bad_factory())


def test_use_column_type_is_not_a_ddl_annotation():
    """Strict independence: the DDL collector must never see it.

    ``UseSqlType`` is a ``DDLAnnotation``; this one deliberately is not. If it
    were, the DDL layer would be one refactor away from inferring a storage type
    from a column declaration — the exact coupling the independence ruling
    forbids.
    """
    from rhosocial.activerecord.base.fields import DDLAnnotation

    assert not isinstance(UseColumnType(StringColumn), DDLAnnotation)


def test_use_column_type_is_independent_of_use_sql_type():
    """Both declared, and neither is inferred from the other."""
    Annotated = getattr(typing, "Annotated", None)
    if Annotated is None:
        pytest.skip("typing.Annotated requires Python 3.9+")

    from rhosocial.activerecord.backend.expression.types import IntegerType
    from rhosocial.activerecord.base.fields import UseSqlType

    annotation = Annotated[int, UseSqlType(IntegerType()), UseColumnType(StringColumn)]
    # The column side answers from the declaration, which the proxy passes in
    # explicitly: on an `Annotated` alias the marker is still reachable through
    # `__metadata__`, but pydantic splits the two apart on a real model field,
    # so the model layer reads it from `FieldInfo.metadata` and hands it over.
    from rhosocial.activerecord.base.fields import declared_column_type

    declared = declared_column_type(annotation.__metadata__)
    assert declared is not None
    assert column_class_for(annotation, sqlite_dialect(), declared) is StringColumn
    # The DDL side still sees only its own candidate, and neither declaration
    # is derived from the other: a column class never names a storage type and
    # a DataType never names a column class.
    declarations = [
        m for m in annotation.__metadata__ if isinstance(m, (UseSqlType, UseColumnType))
    ]
    assert [type(d).__name__ for d in declarations] == ["UseSqlType", "UseColumnType"]
    assert UseSqlType(IntegerType()).data_type.name == "integer"


def test_build_column_uses_the_declared_class():
    column = build_column(sqlite_dialect(), "x", int, column_type=UseColumnType(StringColumn))
    assert type(column) is StringColumn
    # value_type still comes from the annotation, not from the declaration: the
    # declaration chooses operations, it does not relabel the value.
    assert column.value_type == "int"


# ---------------------------------------------------------------------------
# 6. supports_column_operation: default True, narrowing explicit
# ---------------------------------------------------------------------------


def test_operations_are_available_by_default():
    """The burden of proof sits with narrowing, not with declaring.

    Asked of the dummy dialect, which narrows nothing: its answer for every
    ``(column class, operation)`` pair is True. SQLite narrows, and that is the
    point -- the default is the *baseline* a backend departs from, not the answer
    every backend gives.
    """
    from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect

    dialect = DummyDialect()
    dialect._version = (3, 46, 1)
    assert dialect.supports_column_operation("StringColumn", "ilike") is True
    assert dialect.supports_column_operation("JSONColumn", "json_path") is True


def test_a_backend_narrows_one_pair_and_nothing_else():
    """SQL Server's ILIKE is the shape of this: one (column class, operation) pair.

    The granularity is the pair, not the operation — a backend that cannot
    ``ilike`` a string can still ``+`` an integer, and answering at the wider
    grain would over-refuse.
    """

    class NarrowingIlikeDialect(SQLiteDialect, ColumnSuggestionMixin):
        def supports_column_operation(self, column_name: str, op: str) -> bool:
            return not (column_name == "StringColumn" and op == "ilike")

    dialect = NarrowingIlikeDialect()
    assert dialect.supports_column_operation("StringColumn", "ilike") is False
    assert dialect.supports_column_operation("StringColumn", "like") is True
    assert dialect.supports_column_operation("IntegerColumn", "ilike") is True


def test_operation_names_are_the_public_method_names():
    """The convention that makes a capability table checkable.

    ``supports_column_operation`` is keyed by the method that provides the
    operation, so the set of operations is enumerable from the column classes
    themselves and a backend's answers can be asserted against them.
    """
    from rhosocial.activerecord.backend.expression.mixins import (
        BooleanLogicMixin,
        StringPatternPredicateMixin,
    )

    assert callable(StringPatternPredicateMixin.ilike)
    assert callable(BooleanLogicMixin.__and__)
    # SQLite narrows `ilike`, so the pair it keeps is the one it does answer for;
    # the name is still the method's own name.
    assert sqlite_dialect().supports_column_operation(
        "StringColumn", StringPatternPredicateMixin.like.__name__
    )


# ---------------------------------------------------------------------------
# 7. Boolean algebra and the literal discipline
# ---------------------------------------------------------------------------


def _flag(name="flag"):
    return build_column(sqlite_dialect(), name, bool)


def test_is_true_and_is_false_render_keywords():
    """``IS TRUE`` / ``IS FALSE``, three-valued-logic correct.

    ``= TRUE`` would match differently under three-valued logic, and ``= 1``
    is not portable at all: PostgreSQL rejects ``boolean = integer`` outright.
    """
    assert _flag().is_true().to_sql() == ('"flag" IS TRUE', ())
    assert _flag().is_false().to_sql() == ('"flag" IS FALSE', ())


def test_and_or_not_render_connectives_not_bitwise_operators():
    """``AND`` / ``OR`` / ``NOT`` — MySQL accepts bitwise ``&`` / ``|`` too, and
    on a boolean column those compute something else entirely."""
    column = _flag()
    assert (column.is_true() & column.is_false()).to_sql() == (
        '"flag" IS TRUE AND "flag" IS FALSE',
        (),
    )
    assert (column.is_true() | column.is_false()).to_sql() == (
        '"flag" IS TRUE OR "flag" IS FALSE',
        (),
    )
    assert (~column.is_true()).to_sql() == ('NOT ("flag" IS TRUE)', ())


def test_boolean_algebra_never_renders_one_or_zero():
    """The rendering discipline, asserted rather than described.

    ``1`` / ``0`` as a boolean literal is the one thing that works on SQLite and
    MySQL and fails on PostgreSQL, so a regression that renders it would pass on
    two backends and break on a third. The literal has to be the keyword.
    """
    column = _flag()
    rendered = [
        column.is_true().to_sql()[0],
        column.is_false().to_sql()[0],
        (column.is_true() & column.is_false()).to_sql()[0],
        (column.is_true() | column.is_false()).to_sql()[0],
        (~column.is_true()).to_sql()[0],
    ]
    for sql in rendered:
        assert " TRUE" in sql or "FALSE" in sql
        # No integer literal standing in for the value.
        assert " IS 1" not in sql
        assert " IS 0" not in sql
        assert "= 1" not in sql
        assert "= 0" not in sql


def test_boolean_columns_only_carry_the_boolean_surface():
    """``str`` has no ``AND``; that is what the narrow classes are for.

    The mixin is composed into :class:`BooleanColumn` rather than inherited
    from :class:`ColumnBase` precisely so that these three operators stay off
    every other family — giving ``str`` an ``AND`` would be the guess the narrow
    classes exist to avoid.
    """
    assert hasattr(build_column(sqlite_dialect(), "f", bool), "__and__")
    assert hasattr(build_column(sqlite_dialect(), "f", bool), "__or__")
    assert hasattr(build_column(sqlite_dialect(), "f", bool), "__invert__")
    assert not hasattr(build_column(sqlite_dialect(), "s", str), "__and__")
    assert not hasattr(build_column(sqlite_dialect(), "n", int), "__invert__")


def test_negating_the_column_is_not_the_same_as_is_false():
    """``~flag`` is NOT; three-valued logic makes ``NOT NULL`` unknown.

    Callers asking "is it false?" say ``is_false()``. ``~`` is the connective.
    """
    column = _flag()
    assert column.is_false().to_sql()[0] != f"NOT ({column.to_sql()[0]})"


def test_boolean_algebra_composes_with_other_predicates():
    """The connectives are the same ones predicates use, so they interleave."""
    column = _flag()
    name = build_column(sqlite_dialect(), "name", str)
    combined = (column.is_true() & name.like("a%")) | column.is_false()
    sql, params = combined.to_sql()
    assert " AND " in sql and " OR " in sql
    assert params == ("a%",)


def test_two_dialects_agree_only_where_neither_has_deviated():
    """Two backends, two tables, one answer -- as long as neither says otherwise.

    This is where Phase 2 landed: the dummy dialect still reads core's
    dialect-less baseline while SQLite states a real table, so the two now
    differ -- and they differ in fewer places than §12's per-backend row lists,
    because two of its three SQLite cells (``dict`` and ``timedelta``) happen to
    be what the neutral table already said. What actually moves is the four
    sequence entries (no array type here) plus ``float``/``Decimal``, which the
    protocol's common baseline splits out of the baseline's ``NumericColumn``.
    Every other entry still agrees, and that is the part worth pinning: a
    backend that deviated anywhere else would be changing an answer the plan did
    not ask it to change.
    """
    from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect

    dummy = DummyDialect()
    dummy._version = (3, 46, 1)
    deviated = {list, tuple, set, frozenset, float, decimal.Decimal}
    for entry in COLUMN_TYPE_ENTRIES:
        if entry in deviated:
            continue
        assert column_class_for(entry, dummy) is column_class_for(entry, sqlite_dialect())
    assert column_class_for(str, NarrowingDialect()) is not column_class_for(str, dummy)


def test_the_permissive_column_is_still_constructible_by_hand():
    """Retiring the fallback did not retire the class.

    ``Column(dialect, "x")`` is how a caller with a bare column name gets an
    expression; what is gone is the framework deciding that an unclassifiable
    annotation becomes one.
    """
    from rhosocial.activerecord.backend.expression import Column

    column = Column(sqlite_dialect(), "anything")
    assert column.value_type is None
    assert column.to_sql() == ('"anything"', ())


def test_uuid_stays_its_own_column_family():
    """A UUID has no portable operator, but it is still not a string."""
    from rhosocial.activerecord.backend.expression import UUIDColumn

    assert column_class_for(uuid.UUID, sqlite_dialect()) is UUIDColumn
    assert column_class_for(uuid.UUID, sqlite_dialect()) is not StringColumn


def test_decimal_is_a_number_and_not_a_string():
    assert issubclass(column_class_for(decimal.Decimal, sqlite_dialect()), NumericColumn)
