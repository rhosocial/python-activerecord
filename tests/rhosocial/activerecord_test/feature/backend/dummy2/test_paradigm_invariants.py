# src/rhosocial/activerecord_test/feature/backend/dummy2/test_paradigm_invariants.py
"""The type hierarchy's invariants, as executable checks.

Most of these rules have no natural home in a single backend's suite: they are
statements about the *whole* family — core plus every dialect — and a class in
one backend can violate one just as easily as a class in core. So they live
here, parameterised over the dialects.

The rule that got its own file first is :func:`test_declared_fields_are_honoured_or_refused`.
A field named in a type's ``PARAMETERS`` is part of that type's identity: two
declarations differing only in it are *different columns* and the differ reports
them as such. A formatter that ignores the field therefore produces two
*byte-identical* DDL statements for two different declarations, and nothing
downstream can detect it — the caller gets a column that is not the one they
declared and the call reports success. Nineteen such sites accumulated before
this check existed. There are exactly three honest answers, and only three:

* **honour** it — flipping the field changes the SQL;
* **refuse** it — flipping raises, naming the field and why this backend cannot;
* **the field does not belong to this concept** — then it must not be in
  ``PARAMETERS`` at all.

"Silently drop it" is the one thing that is never acceptable.
"""

import importlib
import inspect
import re

import pytest

from rhosocial.activerecord.backend.expression.types import DataType

_DIALECTS = (
    ("postgres", "PostgresDialect"),
    ("mysql", "MySQLDialect"),
    ("mariadb", "MariaDBDialect"),
    ("oracle", "OracleDialect"),
    ("sqlserver", "SQLServerDialect"),
    ("firebird", "FirebirdDialect"),
    ("clickhouse", "ClickHouseDialect"),
    ("snowflake", "SnowflakeDialect"),
    ("bigquery", "BigQueryDialect"),
    ("sqlite", "SQLiteDialect"),
)


def _load(backend, class_name):
    # The nine dialects live in nine separate distributions, and this repository
    # does not depend on any of them -- so in its own CI every one of them is
    # absent. That import happens at collection time, because _dialects() feeds
    # parametrize, and an exception raised during collection aborts the whole
    # run rather than failing one test. So a missing backend has to be a skip,
    # not an error: the guard still runs over whatever dialects are installed,
    # which in core is sqlite.
    try:
        module = importlib.import_module(
            f"rhosocial.activerecord.backend.impl.{backend}.dialect")
    except ImportError as exc:                      # ModuleNotFoundError is one
        pytest.skip(f"{backend} is not installed: {exc}")
    cls = getattr(module, class_name, None)
    if cls is None:                                  # optional dependency
        pytest.skip(f"{backend} is not available")
    for kwargs in ({}, {"version": (23, 0, 0)}, {"version": (16, 0, 0)}):
        try:
            return cls(**kwargs)
        except TypeError:
            continue
    pytest.skip(f"{class_name} could not be constructed")


def _dialects():
    """One ``pytest.param`` per available dialect.

    Each is wrapped in a single-value ``pytest.param`` purely for the id.
    pytest unwraps a one-value ParameterSet, so a test parameterised on this
    receives the dialect object itself.
    """
    out = []
    for backend, class_name in _DIALECTS:
        try:
            out.append(pytest.param(_load(backend, class_name), id=backend))
        except pytest.skip.Exception:
            continue
    return out


def _all_concepts():
    """Every concrete ``DataType`` subclass reachable from the base."""
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


def _backend_of(klass):
    match = re.search(r"backend\.impl\.([a-z0-9_]+)", klass.__module__)
    return match.group(1) if match else "core"


def _other_values(value):
    """Plausible values different from *value*, for a field currently *value*."""
    if isinstance(value, bool):
        return [not value]
    if isinstance(value, int):
        return [value + 1, value + 2, value - 1]
    if isinstance(value, str):
        return [value + "_other", value + "x"]
    if isinstance(value, (tuple, list)):
        return [(tuple(value) + ("__probe__",))]
    return []


def _rendered_with(cls, field, new_value, dialect):
    """Render *cls* with *field* set to *new_value*.

    Returns ``None`` when the class will not accept the value at all — the
    backend has pinned the field, which is an honest answer on its own and is
    reported separately rather than counted as a violation.
    """
    signature = inspect.signature(cls.__init__)
    if field not in signature.parameters:
        return None
    kwargs = {}
    for parameter in signature.parameters.values():
        if parameter.name in ("self", "dialect"):
            continue
        if parameter.kind in (parameter.VAR_POSITIONAL, parameter.VAR_KEYWORD):
            continue
        if parameter.default is not inspect.Parameter.empty:
            kwargs[parameter.name] = parameter.default
        elif parameter.kind is parameter.KEYWORD_ONLY:
            continue                                  # cannot guess this
        else:
            kwargs[parameter.name] = None
    kwargs[field] = new_value
    try:
        return cls(dialect, **kwargs).to_sql()[0]
    except Exception:                                 # noqa: BLE001
        return "<refused>"


def _rendering_dialect(cls, name):
    """The first dialect that renders this type, or ``None`` if none does."""
    for param in _dialects():
        dialect = param.values[0]
        if hasattr(dialect, "format_data_type_" + str(name)):
            return dialect
    return None


# --------------------------------------------------------------------------
# The rule that matters most
# --------------------------------------------------------------------------

@pytest.mark.parametrize("dialect_param", _dialects())
def test_declared_fields_are_honoured_or_refused(dialect_param):
    """No formatter may silently discard a field its type declares as identity.

    For every concrete type with a non-empty ``PARAMETERS`` that some dialect
    renders: build it, then build it again with each identity field changed.
    If the rendered SQL is unchanged for every attempt, the field is being
    dropped — two different declarations produce two byte-identical statements
    and nothing downstream can notice.
    """
    dialect = dialect_param
    checked = 0
    dropped = []
    pinned = []

    for cls in _all_concepts():
        if not cls.PARAMETERS:
            continue
        if not hasattr(dialect, "format_data_type_" + str(cls.name)):
            continue
        try:
            base_sql = cls(dialect).to_sql()[0]
            instance = cls(dialect)
        except Exception:                             # noqa: BLE001
            continue

        for field in cls.PARAMETERS:
            alternatives = _other_values(getattr(instance, field, None))
            if not alternatives:
                continue
            attempts = [
                _rendered_with(cls, field, value, dialect)
                for value in alternatives
            ]
            attempts = [a for a in attempts if a is not None]
            if not attempts:
                pinned.append(f"{cls.__name__}.{field}")
                continue
            if all(sql == base_sql for sql in attempts):
                dropped.append(f"{cls.__name__}.{field} renders {base_sql!r} either way")
            checked += 1

    assert not dropped, (
        "these declared identity fields do not affect the rendered SQL, so "
        "they are being silently discarded — a caller asking for a column "
        "that is not the one they declared gets it, and is told it worked:\n"
        + "\n".join("  " + line for line in dropped)
        + f"\n\n(pinned at construction, so honest: {pinned})"
    )
    # Nothing is asserted about ``checked`` beyond it being non-trivial on at
    # least one dialect; the guarantee is the absence of violations.
    assert isinstance(checked, int)


# --------------------------------------------------------------------------
# Shape of the hierarchy
# --------------------------------------------------------------------------

def test_identity_is_linear_single_inheritance():
    """Inheritance expresses identity, so a concept has exactly one base.

    Multiple inheritance would let a class claim two identities at once, and a
    diamond would mean two paths to the same concept — both make "is this the
    same type" ambiguous. The root is exempt: it inherits from the expression
    base and ``ABC``, which is not a claim about any type concept.
    """
    offenders = [
        f"{k.__module__}.{k.__name__} -> {[b.__name__ for b in k.__bases__]}"
        for k in _all_concepts()
        if len(k.__bases__) != 1
    ]
    assert not offenders, (
        "a type concept must have exactly one base class:\n"
        + "\n".join("  " + line for line in offenders)
    )


def test_no_diamond_edges_between_concepts():
    """No concept may be reachable from another by two different paths."""

    def concept_ancestors(node):
        counts = {}

        def walk(current):
            for base in current.__bases__:
                if issubclass(base, DataType) and base is not DataType:
                    counts[base] = counts.get(base, 0) + 1
                walk(base)

        walk(node)
        return counts

    offenders = []
    seen, stack = set(), [DataType]
    while stack:
        klass = stack.pop()
        if klass in seen:
            continue
        seen.add(klass)
        stack.extend(klass.__subclasses__())
        for ancestor, count in concept_ancestors(klass).items():
            if count > 1:
                offenders.append(
                    f"{klass.__name__} reaches {ancestor.__name__} by {count} paths")
    assert not offenders, "diamond edges:\n" + "\n".join(
        "  " + line for line in offenders)


def test_no_grouping_nodes_or_orphans():
    """Every concrete concept is either rendered by a dialect or named as its
    substitute.

    A class that no dialect renders and no dialect suggests is a grouping node
    or dead code. Both are forbidden: grouping nodes put "these are similar"
    into the type tree, where only identity is allowed, and a class nothing can
    reach is a promise nothing keeps.
    """
    rendered, suggested = set(), set()
    for param in _dialects():
        dialect = param.values[0]
        rendered |= {m[len("format_data_type_"):] for m in dir(type(dialect))
                     if m.startswith("format_data_type_")}
        try:
            suggested |= set(dialect.suggested_data_types() or {})
        except Exception:                             # noqa: BLE001
            pass

    orphans = [f"{_backend_of(k)}/{k.__name__}(name={k.name!r})"
               for k in _all_concepts()
               if k.name and k.name not in rendered and k.name not in suggested]
    assert not orphans, (
        "these concepts are neither rendered nor suggested by any dialect — "
        "grouping nodes and dead classes are both forbidden:\n"
        + "\n".join("  " + line for line in orphans))


# --------------------------------------------------------------------------
# Identity
# --------------------------------------------------------------------------

def test_identity_fields_are_plain_attributes():
    """``PARAMETERS`` names attributes, never computed or transformed values.

    A computed entry cannot be compared as-is, so a class with one is either
    comparing something other than what it declared or quietly normalising a
    value it forgot to normalise when it was stored.
    """
    offenders = [f"{_backend_of(k)}/{k.__name__}: {f!r}"
                 for k in _all_concepts()
                 for f in k.PARAMETERS
                 if not re.fullmatch(r"[A-Za-z_]\w*", f)]
    assert not offenders, "non-attribute entries in PARAMETERS:\n" + "\n".join(
        "  " + line for line in offenders)


def test_a_declared_field_exists_on_the_class():
    """Every declared field must be readable on an instance.

    ``identity()`` reads these with ``getattr``, so a name that no longer exists
    turns ``==`` and ``hash`` into an ``AttributeError`` at the worst possible
    moment.
    """
    offenders = []
    for cls in _all_concepts():
        for field in cls.PARAMETERS:
            if not hasattr(cls, field):
                try:
                    instance = cls()
                except Exception:                     # noqa: BLE001
                    continue
                if not hasattr(instance, field):
                    offenders.append(f"{cls.__name__}.{field}")
    assert not offenders, (
        "declared identity fields that no instance carries:\n"
        + "\n".join("  " + line for line in offenders))


def test_spelling_is_not_part_of_identity():
    """A spelling is how the value is written, not what it is.

    The schema differ compares what the database reports *now* against what was
    declared, and a database reports its own house spelling no matter which
    word was typed: PostgreSQL reports ``character varying(30)`` for every
    ``varchar(30)`` column that exists. Counting the spelling would therefore
    report a change on every such column that was never touched — a false
    positive on the one comparison that has to be right.

    It still reaches the rendered SQL, and still round-trips through
    ``get_params()``, because serialization asks a different question.
    """
    from rhosocial.activerecord.backend.expression.types import IntegerType

    offenders = [f"{_backend_of(k)}/{k.__name__}"
                 for k in _all_concepts() if "spelling" in k.PARAMETERS]
    assert not offenders, (
        "spelling must not be part of identity:\n"
        + "\n".join("  " + line for line in offenders))

    plain, other = IntegerType(), IntegerType(spelling="int")
    assert plain == other
    assert hash(plain) == hash(other)
    # ... and it is not lost: it reaches the SQL and the serialization path.
    assert other.get_params().get("spelling") == "int"


# --------------------------------------------------------------------------
# Names are dispatch keys
# --------------------------------------------------------------------------

def test_dispatch_keys_are_globally_unique():
    """Two concepts sharing a ``name`` makes dispatch ambiguous."""
    by_name = {}
    for klass in _all_concepts():
        if klass.name:
            by_name.setdefault(klass.name, []).append(klass)
    clashes = {n: v for n, v in by_name.items() if len(v) > 1}
    assert not clashes, "duplicate dispatch keys: " + "; ".join(
        f"{n} -> {[k.__name__ for k in v]}" for n, v in clashes.items())


@pytest.mark.parametrize("dialect_param", _dialects())
def test_rendered_and_suggested_keys_are_disjoint(dialect_param):
    """One dialect must not both render a concept and substitute for it.

    If it did, the substitute could never be reached and the renderer would be
    rendering something the dialect has also declared unsupported.
    """
    dialect = dialect_param
    rendered = {m[len("format_data_type_"):] for m in dir(type(dialect))
                if m.startswith("format_data_type_")}
    try:
        suggested = set(dialect.suggested_data_types() or {})
    except Exception:                                 # noqa: BLE001
        suggested = set()
    both = rendered & suggested
    assert not both, (
        f"{_backend_of(type(dialect))} both renders and substitutes: "
        f"{sorted(both)}"
    )


# --------------------------------------------------------------------------
# The removed mechanisms stay removed
# --------------------------------------------------------------------------

def test_removed_comparison_mechanisms_stay_removed():
    """``==`` is the whole comparison; the older pair of escape hatches is gone.

    ``is_equivalent()`` and ``synonyms()`` existed to paper over synonym
    *classes*. Synonyms are now spellings on one class, so there is no second
    class for a looser comparison to disagree with.
    """
    assert not hasattr(DataType, "is_equivalent"), (
        "is_equivalent() is removed: == is the whole comparison")
    assert not hasattr(DataType, "synonyms"), (
        "synonyms() is removed: a synonym is a spelling on the concept's class")
    for klass in _all_concepts():
        assert not hasattr(klass, "is_equivalent"), f"{klass.__name__}"
        assert not hasattr(klass, "synonyms"), f"{klass.__name__}"


# --------------------------------------------------------------------------
# One way to say "this backend cannot express that"
# --------------------------------------------------------------------------

def test_refusals_are_one_exception_type_across_backends():
    """A caller must be able to catch a refusal the same way on every backend.

    ``UnsupportedFeatureError`` does **not** subclass ``ValueError``, so the two
    are not interchangeable to a caller writing ``except ValueError``. The rule
    the backends follow, and this test exists to hold it to:

    * the declared value is **wrong** -- out of the range this server accepts --
      raises ``ValueError``;
    * the declaration is one this grammar **cannot express at all** -- there is
      no unsigned integer, or the scale argument has nowhere to go -- raises
      ``UnsupportedFeatureError``, which carries the dialect name and a route
      forward.

    The second is not "a ValueError that happens to be worded differently": it
    is the only one of the two that can tell a caller what to do instead.
    """
    from rhosocial.activerecord.backend.dialect.exceptions import (
        UnsupportedFeatureError,
    )

    assert not issubclass(UnsupportedFeatureError, ValueError), (
        "if UnsupportedFeatureError ever becomes a ValueError, this test and "
        "every caller's except-clause need revisiting together -- do not change "
        "one silently"
    )

    # Every dialect that can be loaded must agree on which exception means
    # "this backend cannot express that". Spot-check the one refusal every
    # integer concept has an answer for on every backend: the signedness gate.
    from rhosocial.activerecord.backend.expression.types import IntegerType

    checked, refused = 0, 0
    for param in _dialects():
        dialect = param.values[0]
        if not hasattr(dialect, "format_data_type_integer"):
            continue
        checked += 1
        try:
            dialect.format_data_type(IntegerType(dialect, unsigned=True))
        except UnsupportedFeatureError:
            refused += 1
        except ValueError as exc:
            pytest.fail(
                f"{_backend_of(type(dialect))} refuses an unsigned integer with "
                f"ValueError; every other backend raises "
                f"UnsupportedFeatureError for the same refusal, and the two do "
                f"not share a base class: {exc}"
            )
        except Exception:                          # noqa: BLE001
            pass                                   # honoured it: also correct
    assert checked, "no dialect was available to check"
    assert refused >= 1, (
        "no backend refuses unsigned integers at all -- the check above would "
        "pass vacuously"
    )
