# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_type_protocol_contracts.py
"""Layered correspondence contracts for the data-type protocol.

Verifies the namespace rules and the naming-family discipline that the
``DataType`` / ``DataTypeSupport`` contracts formalize:

* ``format_data_type_*`` / ``supports_data_type_*`` 1:1 correspondence,
  checked against **every** dialect this package can import rather than one
  hand-picked pair;
* ``supports_data_types()`` mapping shape — ``{generic name: concrete
  DataType class}`` with ``value.name == key``;
* **every core type is rendered or explicitly substituted** — a dialect must
  take a position on each concept, and silence is not one;
* core-defined types own **pure** generic names;
* backend-defined types (SQLite impl) own **backend-prefixed** names;
* honest-unsupported semantics: rendering a type the dialect does not
  implement raises ``TypeError`` — the dialect never fakes support.

Expression ⇔ dialect correspondence (D9)
-----------------------------------------
The framework's model is an *expression* per SQL concept; each backend's
*dialect* decides how that concept is spelled in its own DDL. That pairing has
to be total, and in one of two ways:

* **Rendered** — the dialect implements ``format_data_type_<name>`` and
  ``supports_data_type_<name>``. This is the normal case.
* **Substituted** — the dialect cannot spell the concept, but it can say what
  it stores instead, via ``suggested_data_types()[name] = SomeType``. This is
  the honest answer for e.g. XML on SQLite (stored as text) and is *not* a
  failure to implement.

What is not allowed is a third state: a concept the dialect has never heard of,
where a caller who asks for it is told only that it is unsupported, with nothing
to go on. The two tests below close that gap — one checks the dialect's own
declarations are self-consistent, the other checks no core concept goes
undeclared.
"""

import importlib
import inspect
import re

import pytest

from rhosocial.activerecord.backend.expression.types import DataType
import rhosocial.activerecord.backend.expression.types as core_types  # noqa: F401
import rhosocial.activerecord.backend.impl.sqlite.expression.types as sqlite_types  # noqa: F401
from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect

_CORE_TYPES_PREFIX = "rhosocial.activerecord.backend.expression.types"
_SQLITE_TYPES_PREFIX = "rhosocial.activerecord.backend.impl.sqlite"

_NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")
_FORMAT_RE = re.compile(r"^format_data_type_([a-z][a-z0-9_]*)$")
_SUPPORTS_RE = re.compile(r"^supports_data_type_([a-z][a-z0-9_]*)$")

#: Dialects this package can import without a live database connection, as
#: ``(id, "module.path", class name)``. A backend that is not installed is
#: skipped rather than failed: this package must stay runnable on its own.
_DIALECT_MODULES = (
    ("dummy", "rhosocial.activerecord.backend.impl.dummy.dialect", "DummyDialect"),
    ("sqlite", "rhosocial.activerecord.backend.impl.sqlite.dialect", "SQLiteDialect"),
)


def _dialects():
    """Import each known dialect class, skipping the ones not installed."""
    found = []
    for dialect_id, module_path, class_name in _DIALECT_MODULES:
        try:
            module = importlib.import_module(module_path)
        except ImportError:
            continue
        dialect_class = getattr(module, class_name, None)
        if dialect_class is not None:
            found.append((dialect_id, dialect_class))
    return found


def _concrete_subclasses():
    """All concrete ``DataType`` subclasses currently loaded."""
    seen = set()
    stack = [DataType]
    while stack:
        klass = stack.pop()
        if klass in seen:
            continue
        seen.add(klass)
        stack.extend(klass.__subclasses__())
    return [klass for klass in seen if not inspect.isabstract(klass)]


def _core_type_classes():
    """Every concrete core ``DataType`` — the concepts the framework models."""
    return sorted(
        (
            klass for klass in _concrete_subclasses()
            if klass is not DataType
            and klass.__module__.startswith(_CORE_TYPES_PREFIX)
        ),
        key=lambda klass: klass.name or "",
    )


@pytest.mark.parametrize("dialect_id,dialect_class", _dialects(),
                         ids=[d[0] for d in _dialects()])
def test_format_supports_correspondence(dialect_id, dialect_class):
    """Every ``format_data_type_X`` has a ``supports_data_type_X`` and vice versa.

    A format method with no support check is undeclared behaviour: the dialect
    claims it can render the type and then answers a question about support by
    raising. A support check with no format method promises something that
    cannot be delivered.
    """
    format_names = {
        _FORMAT_RE.match(member).group(1)
        for member in dir(dialect_class) if _FORMAT_RE.match(member)
    }
    supports_names = {
        _SUPPORTS_RE.match(member).group(1)
        for member in dir(dialect_class) if _SUPPORTS_RE.match(member)
    }
    assert format_names, f"{dialect_id}: must implement the format family"
    assert supports_names, f"{dialect_id}: must implement the supports family"
    assert format_names == supports_names, (
        f"{dialect_id}: format-only: {sorted(format_names - supports_names)}, "
        f"supports-only: {sorted(supports_names - format_names)}"
    )


@pytest.mark.parametrize("dialect_id,dialect_class", _dialects(),
                         ids=[d[0] for d in _dialects()])
def test_supports_data_types_mapping_shape(dialect_id, dialect_class):
    """``supports_data_types()`` is ``{generic name: concrete DataType class}``.

    A key with no class behind it would let a caller believe a type is
    supported without any way to name it.
    """
    dialect = dialect_class()
    mapping = dialect.supports_data_types()
    assert isinstance(mapping, dict)
    assert mapping, f"{dialect_id}: must support at least one type"
    for key, value in mapping.items():
        assert _NAME_RE.match(key), f"{dialect_id}: key {key!r} is not a valid name"
        assert isinstance(value, type) and issubclass(value, DataType), \
            f"{dialect_id}: value for {key!r} must be a DataType subclass"
        assert value.name == key, \
            f"{dialect_id}: {value.__name__}.name={value.name!r} != key {key!r}"
    format_names = {
        _FORMAT_RE.match(member).group(1)
        for member in dir(dialect_class) if _FORMAT_RE.match(member)
    }
    assert set(mapping) == format_names, (
        f"{dialect_id}: mapping and the format family disagree"
    )


@pytest.mark.parametrize("dialect_id,dialect_class", _dialects(),
                         ids=[d[0] for d in _dialects()])
def test_every_core_type_is_rendered_or_suggested(dialect_id, dialect_class):
    """No core concept goes undeclared by a dialect (D9).

    Each of the framework's modelled concepts must be either rendered by this
    dialect or explicitly substituted by it. A concept the dialect has never
    heard of leaves a caller with "unsupported" and nothing else — which is
    indistinguishable from not having thought about it.
    """
    dialect = dialect_class()
    rendered = set(dialect.supports_data_types())
    suggested = dialect.suggested_data_types()
    undeclared = [
        klass.name for klass in _core_type_classes()
        if klass.name not in rendered and klass.name not in suggested
    ]
    assert not undeclared, (
        f"{dialect_id}: 这些核心类型既未渲染也未给出替代，必须显式表态: "
        f"{sorted(undeclared)}"
    )


@pytest.mark.parametrize("dialect_id,dialect_class", _dialects(),
                         ids=[d[0] for d in _dialects()])
def test_the_default_spelling_always_renders(dialect_id, dialect_class):
    """A type constructed the ordinary way must work on every dialect.

    ``BlobType(d)`` carries the default spelling ``"blob"``. If a dialect's
    spelling check rejected it — because PostgreSQL writes ``BYTEA`` and has no
    ``BLOB`` — then the type would be unconstructible on that backend and the
    refusal would tell the caller nothing about how to proceed. So the rule is:

      * the concept's default spelling is always accepted;
      * a dialect may *normalise* it to its own name, but not refuse it;
      * a dialect may refuse the *other* spellings when the backend genuinely
        does not write them.

    This is the difference between "I have no CLOB, here is why" and "your
    request was malformed". Only the former is a useful answer.
    """
    dialect = dialect_class()
    for klass in _core_type_classes():
        spellings = klass.SPELLINGS
        if not spellings:
            continue
        default = klass(dialect)
        assert default.spelling == spellings[0], (
            f"{dialect_id}: {klass.__name__} default spelling "
            f"{default.spelling!r} is not the first of SPELLINGS {spellings!r}"
        )
        sql, _ = dialect.format_data_type(default)
        assert sql, f"{dialect_id}: {klass.__name__} renders empty by default"


@pytest.mark.parametrize("dialect_id,dialect_class", _dialects(),
                         ids=[d[0] for d in _dialects()])
def test_an_unsupported_spelling_is_refused_and_named(dialect_id, dialect_class):
    """A spelling the backend does not write is an error, not a silent rewrite.

    The check has to happen in the formatter: a caller who asked for ``CLOB`` on
    PostgreSQL should be told PostgreSQL has no CLOB, rather than handed a
    ``TEXT`` and finding out later.
    """
    dialect = dialect_class()
    for klass in _core_type_classes():
        if klass.name not in dialect.supports_data_types():
            continue
        for spelling in klass.SPELLINGS:
            try:
                dialect.format_data_type(klass(dialect, spelling=spelling))
            except TypeError as exc:
                assert spelling in str(exc), (
                    f"{dialect_id}: refusing {klass.__name__} spelling "
                    f"{spelling!r} must name the spelling, got: {exc}"
                )
            except Exception:
                # A limit (precision out of range, say) is a different failure.
                pass


@pytest.mark.parametrize("dialect_id,dialect_class", _dialects(),
                         ids=[d[0] for d in _dialects()])
def test_suggested_types_are_declared_and_disjoint(dialect_id, dialect_class):
    """A suggested substitute must be a type this dialect really renders.

    Suggesting a class the backend has no formatter for would trade a clear
    "not supported" for a worse "not supported" — one whose advice does not
    work. Rendered and suggested keys are also disjoint by contract: a type
    that is rendered needs no substitute, and listing both makes the intent
    ambiguous.

    What is *not* required is that the substitute be constructible with no
    arguments: PostgreSQL's stand-in for the generic ``EnumType`` is a named
    type created by ``CREATE TYPE``, and that is precisely the information the
    generic type does not carry. Such a substitute answers "which class on this
    backend means the same thing", which is the question being asked.
    """
    dialect = dialect_class()
    supported = dialect.supports_data_types()
    suggested = dialect.suggested_data_types()

    overlap = set(supported) & set(suggested)
    assert not overlap, (
        f"{dialect_id}: 这些类型既渲染又建议替代: {sorted(overlap)}"
    )

    for key, substitute in sorted(suggested.items()):
        assert isinstance(substitute, type) and issubclass(substitute, DataType), \
            f"{dialect_id}: suggested[{key!r}] must be a DataType subclass"
        assert substitute.name in supported, (
            f"{dialect_id}: suggested[{key!r}] is {substitute.__name__}, "
            f"whose name {substitute.name!r} this dialect does not render"
        )


def test_sqlite_supports_data_types_mapping_merges_namespaces():
    """SQLite mapping covers both generic and sqlite_-namespaced entries."""
    from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect
    mapping = SQLiteDialect().supports_data_types()
    assert "varchar" in mapping and "json" in mapping
    assert any(key.startswith("sqlite_") for key in mapping), (
        "backend dialect must merge its namespaced types into the mapping"
    )
    for key, value in mapping.items():
        assert value.name == key


def test_core_type_names_are_pure():
    """Concrete core types declare pure generic names (no backend prefix)."""
    core_types_found = _core_type_classes()
    assert core_types_found, "core type classes must be loaded"
    for klass in core_types_found:
        assert klass.name is not None, \
            f"{klass.__module__}.{klass.__name__} must declare a name"
        assert _NAME_RE.match(klass.name), \
            f"core type {klass.__name__} has non-pure name {klass.name!r}"


def test_backend_type_names_are_prefixed():
    """Concrete SQLite impl types declare ``sqlite_``-prefixed names."""
    sqlite_types_found = [
        klass for klass in _concrete_subclasses()
        if klass.__module__.startswith(_SQLITE_TYPES_PREFIX)
    ]
    assert sqlite_types_found, "SQLite type classes must be loaded"
    for klass in sqlite_types_found:
        assert klass.name.startswith("sqlite_"), \
            f"backend type {klass.__name__} name {klass.name!r} " \
            f"must start with 'sqlite_'"


def test_unsupported_type_raises():
    """A type the dialect does not implement raises on render (no fake support).

    The throwaway type is defined through ``type()`` with a backend
    namespaced module path and a ``dummy_`` prefixed name so it satisfies
    the namespace enforcement while remaining unimplemented by the dummy
    dialect.
    """
    namespace = {
        "name": "dummy_nosuchtype",
        "__module__": "rhosocial.activerecord.backend.impl.dummy.expression.types",
        "__qualname__": "FakeZzzType",
        "__doc__": "Throwaway type no dialect implements.",
    }
    FakeZzzType = type("FakeZzzType", (DataType,), namespace)
    assert not hasattr(DummyDialect, "format_data_type_dummy_nosuchtype")
    assert not hasattr(DummyDialect, "supports_data_type_dummy_nosuchtype")
    dialect = DummyDialect()
    with pytest.raises(TypeError):
        FakeZzzType(dialect).to_sql()


# ---------------------------------------------------------------------------
# Declared defaults: who owns the width a bare declaration means
# ---------------------------------------------------------------------------


class _DeclaresAVarcharWidth(DummyDialect):
    """A server that supplies a width for the bare form of ``VARCHAR``.

    A subclass rather than a monkeypatch so the declaration is a real dialect
    attribute, discoverable by exactly the lookup the mechanism performs.
    """

    def type_parameter_defaults(self):
        return {"varchar": {"length": 255}}


def test_a_dialect_that_declares_nothing_leaves_the_bare_width_undeclared():
    """The default is "no default", and a backend need not supply a number.

    The dummy dialect renders a bare ``VARCHAR`` and parses it back with no
    length, so the honest statement is that it supplies none — which it makes by
    inheriting the empty answer.  PostgreSQL is the case that matters: its
    ``VARCHAR`` is unbounded, the catalog says ``atttypmod = -1``, and a value
    written into core would make this claim the column is bounded.
    """
    from rhosocial.activerecord.backend.expression.types import (
        CharType,
        VarCharType,
    )
    assert DummyDialect().type_parameter_defaults() == {}
    dialect = DummyDialect()
    assert VarCharType(dialect).length is None
    assert CharType(dialect).length is None


def test_a_declared_width_lands_on_the_bare_declaration():
    """A supplied width becomes the value, so the two forms stop disagreeing.

    The defect this closes is not cosmetic: the schema differ compares a
    declaration against what the catalog reported, so a bare ``VARCHAR`` that
    renders ``VARCHAR(255)`` while carrying no length compares unequal to the
    very column it produced.
    """
    from rhosocial.activerecord.backend.expression.types import (
        CharType,
        VarCharType,
    )
    dialect = _DeclaresAVarcharWidth()
    assert VarCharType(dialect).length == 255
    # and the declared form is now the catalog's form
    assert VarCharType(dialect) == dialect.parse_type("VARCHAR(255)")
    # a concept the server says nothing about is untouched
    assert CharType(dialect).length is None


def test_a_declared_length_does_not_override_a_declared_one():
    """The server's default fills an absent width and nothing else."""
    from rhosocial.activerecord.backend.expression.types import VarCharType
    dialect = _DeclaresAVarcharWidth()
    assert VarCharType(dialect, length=50).length == 50


def test_the_width_is_resolved_when_the_dialect_is_bound_later():
    """Deferred binding resolves the same way, because the lookup is at read time.

    Model definitions are built before a dialect exists and bound afterwards, so
    resolving in ``__init__`` would silently leave every such type undeclared.
    """
    from rhosocial.activerecord.backend.expression.types import VarCharType
    dialect = _DeclaresAVarcharWidth()
    deferred = VarCharType()
    assert deferred.length is None          # no server yet: nothing to resolve
    deferred.dialect = dialect
    assert deferred.length == 255
    assert deferred == VarCharType(dialect)


def test_an_unbound_width_never_raises():
    """Resolution cannot fail, so comparing an unbound type still answers.

    ``None`` means "this server supplies nothing" for a dialect with no
    declaration and for no dialect at all.  A width that raised when it could not
    be looked up would make ordinary construction and equality raise, which is a
    worse defect than the asymmetry it was meant to fix.
    """
    from rhosocial.activerecord.backend.expression.types import VarCharType
    unbound = VarCharType()
    assert unbound == VarCharType()
    assert hash(unbound) == hash(VarCharType())
    assert repr(unbound) == "VarCharType(None,)"
    assert VarCharType(None).length is None


def test_an_object_with_no_declaration_hook_is_read_as_declaring_nothing():
    """The hook is looked up, not demanded, so a dialect without it still answers.

    This is why the hook is deliberately not a member of ``DataTypeSupport``:
    adding it there would make every dialect implement it just to keep passing
    ``isinstance``, which is the "every backend must supply a number" shape the
    design refuses.
    """
    from rhosocial.activerecord.backend.expression.types._defaults import (
        declared_parameter,
    )
    assert declared_parameter("varchar", "length", None) is None
    assert declared_parameter("varchar", "length", object()) is None
    assert declared_parameter("varchar", "length", _DeclaresAVarcharWidth()) == 255
    # a declared parameter the concept does not have is still just a lookup miss
    assert declared_parameter("varchar", "precision", _DeclaresAVarcharWidth()) is None
    assert declared_parameter("char", "length", _DeclaresAVarcharWidth()) is None


def test_a_backend_type_declares_under_its_own_name():
    """Keying on ``name`` keeps a concept's two classes from inheriting one answer.

    ``SQLServerNVarCharMaxType`` is a :class:`VarCharType` that means *unbounded*,
    not *undeclared*, so it must not pick up the ``varchar`` width.  Nothing
    exempts it: it declares nothing under its own ``name``, which is the ordinary
    answer for a concept whose bare form has no width.

    Both classes are built through ``type()`` with a backend-namespaced module
    path and a ``dummy_`` prefixed name, for the same reason
    ``test_unsupported_type_raises`` builds its throwaway that way: that is what
    a real backend-defined subclass looks like to the naming enforcement.
    """
    def _backend_type(class_name, generic_name):
        return type(class_name, (VarCharType,), {
            "name": generic_name,
            "__module__": "rhosocial.activerecord.backend.impl.dummy.expression.types",
            "__qualname__": class_name,
        })

    from rhosocial.activerecord.backend.expression.types import VarCharType
    bounded = _backend_type("BoundedString", "dummy_bounded_string")
    unbounded = _backend_type("UnboundedString", "dummy_unbounded_string")

    # a dialect that has said nothing about either name supplies neither
    dialect = _DeclaresAVarcharWidth()
    assert bounded(dialect).length is None

    # and says so by declaring under the backend type's own name
    class _AlsoDeclaresTheBackendType(DummyDialect):
        def type_parameter_defaults(self):
            return {"varchar": {"length": 255},
                    "dummy_bounded_string": {"length": 255}}

    # the class that means *unbounded* still declares nothing, and still says it
    # by being absent — it never inherits the bounded answer through inheritance
    assert bounded(_AlsoDeclaresTheBackendType()).length == 255
    assert unbounded(_AlsoDeclaresTheBackendType()).length is None


def test_the_declaration_is_not_a_type_and_stays_off_the_dispatch():
    """``type_parameter_defaults`` is a dialect fact, not a type, and not a hook
    the format/supports correspondence can trip over.

    The supported-types surface is the ``format_data_type_<name>`` /
    ``supports_data_type_<name>`` naming family, scanned by ``dir()``; a
    declaration must not add to it or rename a concept's dispatch key.
    """
    dialect = _DeclaresAVarcharWidth()
    mapping = dialect.supports_data_types()
    assert "type_parameter_defaults" not in mapping
    assert "varchar" in mapping
    assert not any("default" in name for name in mapping)


class _DeclaresNumericDefaults(DummyDialect):
    """A server that supplies a precision — and a scale — for the bare form.

    The pair is Snowflake's documented ``NUMBER(38, 0)`` and the precision is
    Oracle's documented ``FLOAT`` default of 126, so one stub exercises both
    shapes the mechanism has to carry: a concept with two resolvable parameters
    (:class:`DecimalType`) and a concept with one (:class:`FloatType`).  A
    subclass rather than a monkeypatch for the same reason as
    :class:`_DeclaresAVarcharWidth`.
    """

    def type_parameter_defaults(self):
        return {
            "decimal": {"precision": 38, "scale": 0},
            "float": {"precision": 126},
        }


def test_a_declared_numeric_default_lands_on_the_bare_declaration():
    """A supplied precision and scale become the values, so the two forms stop
    disagreeing.

    The same defect the width case has, one parameter over: the schema differ
    compares a declaration against what the catalog reported, so a bare
    ``DecimalType`` that renders ``NUMBER(38, 0)`` while carrying no precision
    compares unequal to the very column it produced — and on Snowflake that
    bare declaration *is* the column ``NUMBER(38, 0)``.
    """
    from rhosocial.activerecord.backend.expression.types import (
        DecimalType,
        FloatType,
    )
    dialect = _DeclaresNumericDefaults()
    assert DecimalType(dialect).precision == 38
    assert DecimalType(dialect).scale == 0
    assert FloatType(dialect).precision == 126


def test_a_resolved_numeric_default_compares_equal_to_the_declared_form():
    """``==`` and ``__hash__`` read the properties, so resolution reaches the differ.

    "Nothing declared" and "the server's own value" are one column, and the
    value-object machinery is what says so: both spellings resolve to the same
    identity, so they compare equal and hash equal.
    """
    from rhosocial.activerecord.backend.expression.types import (
        DecimalType,
        FloatType,
    )
    dialect = _DeclaresNumericDefaults()
    assert DecimalType(dialect) == DecimalType(dialect, precision=38, scale=0)
    assert hash(DecimalType(dialect)) == hash(
        DecimalType(dialect, precision=38, scale=0)
    )
    assert FloatType(dialect) == FloatType(dialect, precision=126)
    assert hash(FloatType(dialect)) == hash(FloatType(dialect, precision=126))


def test_the_scale_resolves_even_when_the_precision_was_declared():
    """A per-parameter lookup, not an all-or-nothing pair.

    On Snowflake ``NUMBER(10)`` is ``NUMBER(10, 0)``: the scale has its own
    documented default and the server stores one whatever the declaration said.
    Filling only the precision would leave the precision-only declaration
    comparing unequal to the column it produced — the same defect one parameter
    over — which is why ``type_parameter_defaults`` is keyed per parameter.
    """
    from rhosocial.activerecord.backend.expression.types import DecimalType
    dialect = _DeclaresNumericDefaults()
    assert DecimalType(dialect, precision=10).scale == 0
    assert DecimalType(dialect, precision=10) == DecimalType(
        dialect, precision=10, scale=0
    )


def test_a_declared_numeric_value_is_not_overridden():
    """The server's default fills an absent value and nothing else."""
    from rhosocial.activerecord.backend.expression.types import (
        DecimalType,
        FloatType,
    )
    dialect = _DeclaresNumericDefaults()
    assert DecimalType(dialect, precision=10, scale=2).identity()[:2] == (10, 2)
    assert FloatType(dialect, precision=53).precision == 53


def test_a_numeric_default_is_resolved_when_the_dialect_is_bound_later():
    """Deferred binding resolves the same way, because the lookup is at read time.

    Model definitions are built before a dialect exists and bound afterwards, so
    resolving in ``__init__`` would silently leave every such type undeclared.
    """
    from rhosocial.activerecord.backend.expression.types import (
        DecimalType,
        FloatType,
    )
    dialect = _DeclaresNumericDefaults()
    deferred = DecimalType()
    assert deferred.precision is None
    assert deferred.scale is None
    deferred.dialect = dialect
    assert deferred.precision == 38
    assert deferred.scale == 0
    assert deferred == DecimalType(dialect)
    deferred_float = FloatType()
    assert deferred_float.precision is None
    deferred_float.dialect = dialect
    assert deferred_float.precision == 126
    assert deferred_float == FloatType(dialect)


def test_a_dialect_less_numeric_type_stays_undeclared():
    """There is no server to ask, so the honest answer is ``None``.

    This is the invariant the rest of the framework leans on — types are built
    and compared long before a connection exists — and it is the one
    ``test_data_types.py::test_the_other_fields_are_untouched`` pins for the
    same classes.  Resolution must not raise and must not invent a number.
    """
    from rhosocial.activerecord.backend.expression.types import (
        DecimalType,
        FloatType,
    )
    assert DecimalType().precision is None
    assert DecimalType().scale is None
    assert FloatType().precision is None
    assert DecimalType() == DecimalType()
    assert hash(FloatType()) == hash(FloatType())


def test_serialization_records_the_resolved_numeric_default():
    """``get_params`` is the one serialization surface, and it reads the property.

    For a dialect-bound bare declaration that means the recorded values are the
    ones the server supplies, not ``None``: the dialect itself is deliberately
    not serialized (it is resupplied at deserialization), so the snapshot the
    parameters carry is the declaration as this server resolved it.
    """
    from rhosocial.activerecord.backend.expression.types import (
        DecimalType,
        FloatType,
    )
    dialect = _DeclaresNumericDefaults()
    assert DecimalType(dialect).get_params()["precision"] == 38
    assert DecimalType(dialect).get_params()["scale"] == 0
    assert FloatType(dialect).get_params()["precision"] == 126
    # An unbound instance records the declaration as written, which is ``None``.
    assert DecimalType().get_params()["precision"] is None

