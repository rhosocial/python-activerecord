# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_type_dispatch_registry.py
"""``supports_data_types()`` must resolve every name the dialect can render.

There is no registry. The naming family **is** the registry: a dialect declares
``format_data_type_<name>`` and the class behind that name is found by lookup.
That design has one sharp edge, and this file is about it.

:meth:`~...dialect.mixins.data_type.DataTypeMixin._type_class_for` answers a
dispatch name by walking the live subclass tree of ``DataType`` — so it sees only
the classes something has already **imported**. On a cold
``import <backend>.dialect``, a name whose class lives in a module nobody has
touched resolves to ``None``, is dropped from the mapping, and the caller is left
concluding that the dialect cannot render a type it has a formatter for. There is
no error anywhere. The SQL Server backend hit exactly this and had to import its
own type module by hand to fix it.

Why these tests run in a **fresh interpreter**
----------------------------------------------
A test module that imports the type classes in its own preamble has already made
the bug invisible: by the time the assertion runs, the class is loaded and the
lookup succeeds whether or not the production code is correct. The only way to
see a load-order bug is to ask in a process where the import has not happened —
which is why the guard below runs ``python -c ...`` rather than calling the
dialect in-process, and why the reproduction builds its own throwaway backend on
disk in a temporary directory instead of defining one here.
"""

import re
import subprocess
import sys
import textwrap

import pytest

from rhosocial.activerecord.backend.dialect.mixins.data_type import DataTypeMixin
from rhosocial.activerecord.backend.expression.types import DataType

_FORMAT_RE = re.compile(r"^format_data_type_([a-z][a-z0-9_]*)$")

#: The core dialects and how to construct one, as ``(id, module, class)``.
_DIALECTS = (
    ("dummy", "rhosocial.activerecord.backend.impl.dummy.dialect",
     "DummyDialect()"),
    ("sqlite", "rhosocial.activerecord.backend.impl.sqlite.dialect",
     "SQLiteDialect(version=(3, 45, 0))"),
)

#: Asked of a fresh interpreter: import one module, nothing else, and report
#: which of the dialect's own formatter names failed to resolve.
_PROBE = textwrap.dedent("""
    import importlib, json, re, sys

    module_path, constructor = sys.argv[-2], sys.argv[-1]
    module = importlib.import_module(module_path)
    dialect = eval(constructor, vars(module))
    dialect_class = type(dialect)
    declared = sorted(
        match.group(1) for match in
        (re.fullmatch(r"format_data_type_([a-z][a-z0-9_]*)", name)
         for name in dir(dialect_class))
        if match
    )
    mapping = dialect.supports_data_types()
    print(json.dumps({
        "declared": declared,
        "resolved": sorted(mapping),
        "unresolved": [name for name in declared if name not in mapping],
        "misnamed": sorted(
            name for name, klass in mapping.items()
            if getattr(klass, "name", None) != name
        ),
        "loaded": sorted(
            klass.__module__ for klass in mapping.values()
        ),
    }))
""")


def _probe_in_fresh_interpreter(module_path, constructor):
    """Ask a cold interpreter about one dialect; returns the parsed report."""
    import json

    result = subprocess.run(
        [sys.executable, "-c", _PROBE, module_path, constructor],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, (
        f"probe failed for {module_path}:\n{result.stdout}\n{result.stderr}"
    )
    return json.loads(result.stdout.strip().splitlines()[-1])


@pytest.mark.parametrize("dialect_id,module_path,constructor", _DIALECTS,
                         ids=[d[0] for d in _DIALECTS])
def test_every_declared_formatter_resolves_on_a_cold_import(
    dialect_id, module_path, constructor,
):
    """The guard: nothing the dialect can render may vanish from the mapping.

    ``declared`` comes from the formatter family on the class and ``resolved``
    from ``supports_data_types()``. Anything in the first and not the second is a
    name the dialect can render and cannot name — which is the bug, stated as a
    test that cannot be passed by importing the missing classes first.
    """
    report = _probe_in_fresh_interpreter(module_path, constructor)
    assert report["declared"], f"{dialect_id}: must implement the format family"
    assert not report["unresolved"], (
        f"{dialect_id}: these names have a format_data_type_<name> but no "
        f"resolvable class, so supports_data_types() silently omits them: "
        f"{report['unresolved']}. The lookup found no class because nothing "
        f"imported the module it lives in."
    )
    assert not report["misnamed"], (
        f"{dialect_id}: mapped classes must declare the key as their own name: "
        f"{report['misnamed']}"
    )
    assert report["declared"] == report["resolved"], (
        f"{dialect_id}: a dialect that renders a name must list it as supported"
    )


@pytest.mark.parametrize("dialect_id,module_path,constructor", _DIALECTS,
                         ids=[d[0] for d in _DIALECTS])
def test_the_lookup_does_not_reach_into_another_backend(dialect_id, module_path,
                                                        constructor):
    """Loading one dialect must not pull in a sibling's type classes.

    The core fix derives ``impl/<backend>/expression/types.py`` from the backend
    slug, so a mistake there would show up as one dialect importing another's
    package. On a cold import of a core dialect nothing backend-specific should be
    loaded at all.
    """
    report = _probe_in_fresh_interpreter(module_path, constructor)
    foreign = sorted({
        module for module in report["loaded"]
        if ".impl." in module
        and not module.startswith(module_path.rsplit(".dialect", 1)[0])
    })
    assert not foreign, f"{dialect_id}: loaded another backend's types: {foreign}"


def test_a_backend_type_nothing_has_imported_still_resolves(tmp_path):
    """The reproduction, on a real backend-shaped package built for this test.

    ``impl/probebk/expression/types.py`` defines the class and
    ``impl/probebk/dialect.py`` defines a dialect that renders it — and
    deliberately does **not** import the type module, which is the mistake this
    whole file is about. A fresh interpreter then asks the dialect for its
    supported types.

    With the lookup walking only ``DataType.__subclasses__()``, ``probebk_widget``
    is missing from the answer and nothing says why. The fix resolves it by
    importing the module the enforced ``<backend>_`` namespace rule already points
    at, so the answer is complete without the dialect author having to remember.
    """
    backend = "probebk"
    package = tmp_path / backend
    (package / "expression").mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "expression" / "__init__.py").write_text("", encoding="utf-8")
    (package / "expression" / "types.py").write_text(textwrap.dedent("""
        from rhosocial.activerecord.backend.expression.types import DataType


        class ProbeBkWidgetType(DataType):
            \"\"\"A backend type whose module the dialect does not import.\"\"\"

            name = "probebk_widget"
    """), encoding="utf-8")
    (package / "dialect.py").write_text(textwrap.dedent("""
        from typing import Tuple

        from rhosocial.activerecord.backend.dialect.mixins.data_type import (
            DataTypeMixin,
        )


        class ProbeBkDialect(DataTypeMixin):
            \"\"\"Declares a formatter for a class nothing here imports.\"\"\"

            name = "probebk"

            def format_data_type_probebk_widget(self, data_type) -> Tuple[str, tuple]:
                return "WIDGET", ()
    """), encoding="utf-8")

    # The throwaway package has to be importable as
    # ``rhosocial.activerecord.backend.impl.probebk``, so the real ``impl``
    # package is told where to look. Done in the child process only.
    preamble = textwrap.dedent("""
        import sys
        import rhosocial.activerecord.backend.impl as impl_package
        impl_package.__path__.append(sys.argv[1])
    """)
    env_path = tmp_path
    report = _probe_with_preamble(
        preamble, env_path,
        f"rhosocial.activerecord.backend.impl.{backend}.dialect",
        "ProbeBkDialect()",
    )
    assert report["declared"] == ["probebk_widget"], report
    assert not report["unresolved"], (
        "a cold import of the dialect lost probebk_widget from "
        f"supports_data_types(): {report}"
    )
    assert report["resolved"] == ["probebk_widget"]


def _probe_with_preamble(preamble, extra_argument, module_path, constructor):
    """``_probe_in_fresh_interpreter`` with a script run before the import.

    The preamble reads its argument from ``sys.argv[1]``; ``_PROBE`` reads the
    last two, so prepending one argument does not shift its own.
    """
    import json

    result = subprocess.run(
        [sys.executable, "-c", preamble + _PROBE,
         str(extra_argument), module_path, constructor],
        capture_output=True, text=True, check=False,
    )
    assert result.returncode == 0, (
        f"probe failed for {module_path}:\n{result.stdout}\n{result.stderr}"
    )
    return json.loads(result.stdout.strip().splitlines()[-1])


def test_an_unknown_name_still_resolves_to_nothing():
    """The lookup has not become a guesser.

    A name no class claims and no backend prefix implies is ``None``, which is
    what ``supports_data_types()`` uses to mean "this dialect does not render
    that".
    """
    from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect

    dialect = DummyDialect()
    assert dialect._type_class_for("nosuchtype") is None
    # A core-prefixed name is not a backend name, so no import is attempted.
    assert dialect._type_class_for("jsonb") is not None


def test_a_formatters_own_annotation_is_where_the_class_comes_from():
    """The formatter's signature is the authoritative statement of what it serves.

    A throwaway dialect declares a formatter for a class and gets that class back
    — without the lookup depending on which subclass the walk reached first, and
    without consulting any table of names.
    """
    from rhosocial.activerecord.backend.impl.dummy.dialect import DummyDialect
    from rhosocial.activerecord.backend.expression.types import JsonBType

    class AnnotatedDialect(DummyDialect):
        """Renders a core concept, annotated with the class it renders."""

        def format_data_type_annotated_widget(self, data_type: JsonBType):
            return "WIDGET", ()

    # The annotation's class does not declare the dispatch key, so it is not
    # trusted for it — the name resolves to nothing, which is the honest answer.
    assert AnnotatedDialect()._type_class_for("annotated_widget") is None

    # With the class's own name, the annotation is the answer.
    class DeclaredNameDialect(DummyDialect):
        def format_data_type_jsonb(self, data_type: JsonBType):
            return "JSONB", ()

    assert DeclaredNameDialect()._type_class_for("jsonb") is JsonBType


def test_the_mixin_is_what_provides_the_mapping():
    """Both core dialects resolve their mapping through ``DataTypeMixin``."""
    import importlib

    for _, module_path, constructor in _DIALECTS:
        module = importlib.import_module(module_path)
        dialect = eval(constructor, vars(module))
        dialect_class = type(dialect)
        assert DataTypeMixin in dialect_class.__mro__
        assert dialect_class.supports_data_types is DataTypeMixin.supports_data_types
        assert dialect_class._type_class_for is DataTypeMixin._type_class_for


def test_data_type_subclasses_are_reachable_without_a_registry():
    """The walk is still the last resort, and it is a walk, not a table."""
    # Built through ``type()`` with a namespaced module so it satisfies the
    # namespace rule; the point is only that defining a class is enough to make
    # it reachable, with nothing registering it anywhere.
    Throwaway = type(
        "Throwaway",
        (DataType,),
        {
            "name": "dummy_throwaway_for_the_walk",
            "__module__": "rhosocial.activerecord.backend.impl.dummy.expression.types",
            "__qualname__": "Throwaway",
            "__doc__": "Throwaway type for the subclass walk.",
        },
    )
    assert Throwaway.name in {klass.name for klass in DataType.__subclasses__()}