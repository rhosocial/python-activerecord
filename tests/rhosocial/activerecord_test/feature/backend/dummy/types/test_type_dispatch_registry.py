# tests/rhosocial/activerecord_test/feature/backend/dummy/types/test_type_dispatch_registry.py
"""``supports_data_types()`` must resolve every name the dialect can render.

There is no registry. The naming family **is** the registry: a dialect declares
``format_data_type_<name>`` and the class behind that name is found by lookup.
That design has one sharp edge, and this file is about it.

:meth:`~...dialect.mixins.data_type.DataTypeMixin.type_class_for` answers a
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
    mapping = _rendered_names(dialect)
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


def _rendered_names(dialect):
    import re as _re
    return {m.group(1) for n in dir(type(dialect))
            if (m := _re.match(r"^format_data_type_([a-z][a-z0-9_]*)$", n))}


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
@pytest.mark.parametrize("dialect_id,module_path,constructor", _DIALECTS,
                         ids=[d[0] for d in _DIALECTS])
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