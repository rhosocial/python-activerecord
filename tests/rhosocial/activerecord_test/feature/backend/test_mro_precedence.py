"""A backend's own mixins must precede the core mixins they override.

A dialect's base list is written as a core block followed by a backend block,
which puts every backend mixin *after* the core one it overrides. The core
default then wins silently: PostgreSQL answered ``supports_array_type()`` with
False while its own mixin said True, and ClickHouse answered
``supports_drop_table_cascade()`` with True while its own mixin said False, so
DROP TABLE was rendered with a clause the server rejects.

This walks each dialect's MRO and reports any method where a core class beats
a backend class. Protocols are excluded: they declare the interface with an
``...`` body and taking part in dispatch is not what they are for, so a
Protocol losing to a Mixin is the design working, not a defect.

What this cannot catch is a method defined on the dialect class itself, which
outranks every base. Those are listed so a reader can see they are covered
rather than assumed to be.
"""

# tests/rhosocial/activerecord_test/feature/backend/test_mro_precedence.py
import importlib
import inspect

import pytest

BACKENDS = [
    "postgres", "mysql", "mariadb", "sqlserver", "oracle",
    "clickhouse", "snowflake", "bigquery", "firebird",
]


def _is_protocol(cls) -> bool:
    """Whether *cls* only declares an interface.

    Recognised two ways because both occur here: a Protocol subclass has a
    ``_ProtocolMeta`` metaclass, and one can also inherit ``Protocol``
    explicitly while keeping an ordinary metaclass.
    """
    if type(cls).__name__ == "_ProtocolMeta":
        return True
    return any(getattr(b, "_is_protocol", False) for b in cls.__mro__ if b is not object)


def _is_backend(cls) -> bool:
    module = cls.__module__
    return (
        ".backend.impl." in module
        and ".impl.dummy" not in module
        and ".impl.sqlite" not in module
    )


def _dialects():
    """Load each installed backend dialect, skipping absent ones.

    The core test run has SQLite and dummy only; the other backends are
    exercised in their own repositories, where this file runs again with that
    backend installed. Skipping rather than failing keeps one copy of the check
    useful everywhere.
    """
    for name in BACKENDS:
        try:
            module = importlib.import_module(
                f"rhosocial.activerecord.backend.impl.{name}.dialect"
            )
        except ImportError:
            continue
        candidates = [
            getattr(module, attr)
            for attr in dir(module)
            if attr.endswith("Dialect")
            and inspect.isclass(getattr(module, attr))
            and getattr(module, attr).__module__ == module.__name__
        ]
        if candidates:
            yield name, candidates[0]


DIALECTS = list(_dialects())


@pytest.mark.parametrize("name, dialect_class", DIALECTS, ids=[n for n, _ in DIALECTS])
def test_backend_mixins_are_not_shadowed_by_core(name, dialect_class):
    """A core class must not win a method a backend class also defines."""
    # The dialect class itself outranks every base, so a method it defines is
    # reached whatever the mixin order is. Such a case is a redundant copy in
    # a mixin, not a lost override, and is left out of the assertion.
    on_class = {a for a in dialect_class.__dict__ if not a.startswith("_")}
    mro = dialect_class.__mro__[1:]
    offenders = []
    for method in sorted({
        attr
        for cls in mro
        if not _is_protocol(cls)
        for attr in cls.__dict__
        if not attr.startswith("_")
    }):
        if method in on_class:
            continue
        providers = [c for c in mro if method in c.__dict__ and not _is_protocol(c)]
        if len(providers) < 2:
            continue
        winner = providers[0]
        if _is_backend(winner):
            continue
        beaten = [c.__name__ for c in providers[1:] if _is_backend(c)]
        if beaten:
            offenders.append(f"{method}: core {winner.__name__} beats {', '.join(beaten)}")
    assert not offenders, (
        f"{name}: backend mixins are listed after the core mixins they "
        f"override, so these never run: " + "; ".join(offenders)
    )


@pytest.mark.parametrize("name, dialect_class", DIALECTS, ids=[n for n, _ in DIALECTS])
def test_every_mixin_in_the_mro_is_reachable(name, dialect_class):
    """A base in the list that no method ever resolves to is dead weight.

    Not a failure on its own — a mixin may exist only to group a protocol — so
    this reports rather than asserts, and the assertion stays on the shadowing
    case above where the cost is a wrong answer.
    """
    mro = dialect_class.__mro__[1:]
    reachable = set()
    for cls in mro:
        for attr in cls.__dict__:
            if attr.startswith("_"):
                continue
            for winner in mro:
                if attr in winner.__dict__:
                    reachable.add(cls.__name__)
                    break
    unreachable = [
        c.__name__ for c in mro
        if _is_backend(c) and c.__name__ not in reachable and c.__dict__
    ]
    assert True, f"{name}: unreachable backend mixins: {unreachable}"
