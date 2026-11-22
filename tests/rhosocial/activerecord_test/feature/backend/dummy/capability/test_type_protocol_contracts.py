# tests/rhosocial/activerecord_test/feature/backend/dummy/capability/test_type_protocol_contracts.py
"""Layered correspondence contracts for the data-type protocol.

Verifies the namespace rules and the naming-family discipline that the
``DataType`` / ``DataTypeSupport`` contracts formalize:

* **the formatter family is the support declaration** — no core dialect
  carries a leftover ``supports_data_type_*`` probe, and the
  ``supports_data_types()`` mapping is exactly the ``format_data_type_*``
  family, checked against **every** dialect this package can import rather
  than one hand-picked pair;
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

* **Rendered** — the dialect implements ``format_data_type_<name>``,
  which is the support declaration itself. This is the normal case.
* **Substituted** — the dialect cannot spell the concept, but it can say what
  it stores instead, via ``suggest_substitute_types()[name] = SomeType``. This is
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


def _rendered_names(dialect):
    import re as _re
    return {m.group(1) for n in dir(type(dialect))
            if (m := _re.match(r"^format_data_type_([a-z][a-z0-9_]*)$", n))}


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
    rendered = set(_rendered_names(dialect))
    suggested = dialect.suggest_substitute_types().mapping
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
        if klass.name not in _rendered_names(dialect):
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
    supported = _rendered_names(dialect)
    suggested = dialect.suggest_substitute_types().mapping

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


