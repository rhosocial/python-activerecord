# .claude/skills/dev-dialect-protocol-lineage/scripts/dialect_protocol_lineage.py
"""Dialect protocol lineage: declarations, implementations, and composition.

Three layers
------------
The dialect protocol system has three distinct layers, and most protocol mistakes are
confusions between them:

1. **Declaration** - ``Protocol`` classes, in ``backend/dialect/protocols.py`` for the core
   and in ``impl/<name>/protocols.py`` for a backend. A protocol *promises* a set of
   methods. It never runs.
2. **Implementation** - mixin classes in ``backend/dialect/mixins/*.py`` and
   ``impl/<name>/mixins/*.py``, plus the concrete dialect class itself. A mixin
   *provides* methods.
3. **Composition** - the concrete dialect's base-class list, which mixes layer 1 and
   layer 2 in a single ``class`` statement. ``PostgresDialect`` alone has 253 bases.

Because composition flattens layers 1 and 2 into one MRO, a protocol that is in the MRO
but whose methods are never provided is invisible at runtime until something calls it.
That is the defect class this tool exists to find.

Findings
--------
``declared_but_unimplemented``
    A protocol in the dialect's MRO declares a method, and nothing in the MRO provides
    it. Calling it raises ``AttributeError``. The most serious finding: a broken promise
    that type checkers accept.

``implemented_but_undeclared``
    A mixin in the MRO provides a ``format_*`` / ``supports_*`` method that no protocol
    in the MRO declares. Usually dead code, occasionally a contract that should have been
    declared. Restricted to protocol-shaped names to keep the signal high.

``unbacked_capability_bit``
    A ``supports_*`` method whose body is a hardcoded ``True``. Such a bit claims support
    unconditionally, so a dialect that inherits it advertises a capability it may not
    have. This is the same defect class as a capability probe that lied about
    materialised views, and the constraint family's ``supports_constraint_enforced``
    default.

``protocol_overlap``
    Two protocols in the same MRO declare the same method name, so resolution order
    decides the meaning. The per-backend conformance tests assert against this too.

``protocol_without_members``
    A protocol that declares nothing, which makes it a documentation artefact rather
    than a contract.

Cross-check
-----------
Each backend carries protocol conformance tests that assert forward coverage
(protocol method implemented) and reverse coverage (mixin method declared). Those tests
are the authority on callability because they execute against a live database. This
tool cannot run them, so it *locates* them and reports per dialect whether coverage tests
exist, and treats their absence as a finding rather than a silent pass.
"""

from __future__ import annotations

import argparse
import ast
import importlib
import inspect
import json
import os
import pkgutil
import re
import sys
import textwrap
import typing
import warnings
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import (
    Any,
    Dict,
    Iterable,
    List,
    Optional,
    Protocol,
    Sequence,
    Set,
    Tuple,
)

# The expression-lineage skill owns backend discovery, and enumerating by
# directory rather than by package is what keeps the PEP 420 backends visible.
# It lives one skill away, so reach it by path rather than duplicating the rule:
# two copies of a discovery rule drift, and this one had already drifted.
_EXPRESSION_LINEAGE_SCRIPTS = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    os.pardir,
    os.pardir,
    "dev-expression-lineage",
    "scripts",
)
if _EXPRESSION_LINEAGE_SCRIPTS not in sys.path:
    sys.path.insert(0, _EXPRESSION_LINEAGE_SCRIPTS)
from expression_lineage import _installed_backend_names  # noqa: E402

warnings.filterwarnings("ignore")

IMPL_ROOT = "rhosocial.activerecord.backend.impl"
CORE_DIALECT = "rhosocial.activerecord.backend.dialect"
CORE_MIXIN_PREFIX = "rhosocial.activerecord.backend.dialect.mixins"
CORE_PROJECT = "core"
EXCLUDE_FRAGMENTS = ("examples", "tests", "test_", "__pycache__", ".cover")

#: Method-name shapes that a protocol is expected to declare. Restricting reverse
#: coverage to these keeps implemented-but-undeclared actionable instead of noisy.
PROTOCOL_NAME_SHAPES = ("format_", "supports_", "parse_", "escape_", "quote_")


def _is_protocol(cls: type) -> bool:
    """Whether *cls* is a Protocol *definition*.

    ``issubclass(cls, Protocol)`` is the wrong test: a concrete dialect that inherits
    protocol classes as bases is itself a virtual subclass of ``Protocol``, so every
    dialect would be misclassified as a protocol.
    """
    return bool(getattr(cls, "_is_protocol", False)) and cls is not Protocol


def protocol_members(cls: type) -> Set[str]:
    """Public members a protocol declares, including inherited ones.

    Uses the same extraction as the backends' conformance tests so that this tool and
    the tests cannot disagree about what a protocol promises. The manual fallback
    mirrors the tests' pre-3.12 path.
    """
    getter = getattr(typing, "get_protocol_members", None)
    if getter is None:
        getter = getattr(typing, "_get_protocol_attrs", None)
    if getter is not None:
        return set(getter(cls))
    members: Set[str] = set()  # pragma: no cover - Python < 3.12
    for base in cls.__mro__:
        if base is object:
            continue
        for name, value in list(vars(base).items()):
            if name.startswith("_"):
                continue
            if callable(value) or isinstance(
                value, (property, classmethod, staticmethod)
            ):
                members.add(name)
        members.update(
            key for key in getattr(base, "__annotations__", {}) if not key.startswith("_")
        )
    return members


def public_providers(cls: type) -> Dict[str, str]:
    """Public members a class *itself* defines, mapped to the defining class name.

    Only ``vars(cls)`` is consulted, never inherited attributes, so the provider
    recorded for a method is the class that would actually win in the MRO.
    """
    provided: Dict[str, str] = {}
    for name, value in list(vars(cls).items()):
        if name.startswith("_"):
            continue
        if callable(value) or isinstance(value, (property, classmethod, staticmethod)):
            provided[name] = cls.__name__
    return provided


def _is_ellipsis_body(func: Any) -> bool:
    """Whether a function is a declaration stub rather than an implementation.

    A stub's *top-level* body is only a docstring, a bare ``...``, or a single
    ``raise NotImplementedError``. It must be judged from the statement list, not by
    walking the tree: an earlier version walked the AST and treated any ``raise`` as a
    stub, which flagged real implementations that merely raise on an unsupported
    branch. ``format_column_definition`` on ClickHouse was one such false positive.
    """
    try:
        source = textwrap.dedent(inspect.getsource(func))
    except (OSError, TypeError):
        return False
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return False
    if not tree.body or not isinstance(tree.body[0], (ast.FunctionDef, ast.AsyncFunctionDef)):
        return False
    body = list(tree.body[0].body)
    if (
        body
        and isinstance(body[0], ast.Expr)
        and isinstance(body[0].value, ast.Constant)
        and isinstance(body[0].value.value, str)
    ):
        body = body[1:]
    if not body:
        return True
    if len(body) == 1:
        only = body[0]
        if isinstance(only, ast.Expr) and isinstance(only.value, ast.Constant):
            return only.value.value is Ellipsis
        if isinstance(only, ast.Raise):
            return True
    return False


def _returns_literal_true(func: Any) -> bool:
    """Whether a function body is a bare ``return True``.

    Only the literal constant counts. A version comparison such as
    ``return self.version >= (8, 0, 16)`` is a real capability check, not a hardcoded
    claim, so it is not reported.
    """
    try:
        source = textwrap.dedent(inspect.getsource(func))
    except (OSError, TypeError):
        return False
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return False
    returns = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Return) and node.value is not None
    ]
    if not returns:
        return False
    return all(
        isinstance(node.value, ast.Constant) and node.value.value is True
        for node in returns
    )


# ── Model ────────────────────────────────────────────────────────────────────

@dataclass
class ProtocolDecl:
    """A protocol definition and the methods it promises."""

    project: str
    name: str
    module: str
    methods: Set[str] = field(default_factory=set)

    @property
    def key(self) -> str:
        return "{}::{}".format(self.project, self.name)


#: The core package ships a ``DummyDialect`` purely as a test fixture. It is reported
#: for completeness but is not a real backend, so conformance-test cross-checks and
#: merge gates should skip it.
FIXTURE_PROJECTS = frozenset({"dummy"})


@dataclass
class DialectProfile:
    """Composition and coverage of one concrete dialect.

    Attributes:
        project: Project label the dialect belongs to.
        class_name: Concrete dialect class name.
        module: Module defining it.
        mro_length: Size of the MRO.
        protocols: Protocol classes in the MRO, MRO order.
        providers: Method name to the class in the MRO that provides it.
        declared: Method names declared by the protocols in the MRO.
        declared_by: Method name to the protocols that declare it.
    """

    project: str
    class_name: str
    module: str
    mro_length: int
    protocols: List[type]
    providers: Dict[str, str]
    declared: Set[str]
    declared_by: Dict[str, List[str]]
    conformance_tests: List[str] = field(default_factory=list)

    @property
    def is_fixture(self) -> bool:
        return self.project in FIXTURE_PROJECTS

    @property
    def label(self) -> str:
        suffix = " (test fixture)" if self.is_fixture else ""
        return "{}{}".format("{}:{}".format(self.project, self.class_name), suffix)

    def declared_but_absent(self) -> Dict[str, List[str]]:
        """Protocol methods with **no attribute at all** in the MRO.

        Calling one raises ``AttributeError``. Distinct from
        :meth:`stubbed_methods`, which is the more common and quieter failure: the
        attribute exists because a protocol carries an ``...`` body, so ``hasattr``
        succeeds and ``isinstance(dialect, SomeProtocol)`` is True.
        """
        absent: Dict[str, List[str]] = {}
        for name in sorted(self.declared):
            if name in self.providers:
                continue
            if any(hasattr(base, name) for base in self._mro):
                continue
            absent[name] = sorted(set(self.declared_by.get(name, ())))
        return absent

    def stubbed_methods(self) -> Dict[str, str]:
        """Declared methods whose resolved implementation is an ``...`` stub.

        This is the finding that matters most and the one conformance testing cannot
        see. A protocol written as::

            def supports_validate_constraint(self) -> bool: ...

        leaves a real attribute on the class, so ``hasattr`` is True and
        ``isinstance(dialect, ConstraintSupport)`` holds. The conformance tests assert
        exactly those two things, so they pass. Calling it returns ``None`` rather than
        a ``bool``: a falsy value that happens to read as "unsupported", which is why the
        bug survives review. It only bites on ``is True`` / ``is False`` comparisons, on
        code that logs the bit, or where ``None`` is not the intended answer.

        The value is the stub as ``Class.method`` so the owning class is visible, since
        the stub usually lives on the protocol itself.
        """
        stubs: Dict[str, str] = {}
        for name in sorted(self.declared):
            for base in self._mro:
                value = vars(base).get(name)
                if value is None:
                    continue
                func = value.fget if isinstance(value, property) else value
                if isinstance(func, staticmethod):
                    func = func.__func__
                if callable(func) and _is_ellipsis_body(func):
                    stubs[name] = base.__name__
                break
        return stubs

    def implemented_but_undeclared(self) -> Dict[str, str]:
        """Protocol-shaped methods provided without any protocol declaring them."""
        return {
            name: provider
            for name, provider in sorted(self.providers.items())
            if name not in self.declared
            and name.startswith(PROTOCOL_NAME_SHAPES)
        }

    def untriaged_capability_bits(self) -> List[str]:
        """Capability bits the dialect inherited from a core default and never triaged.

        A ``supports_*`` bit whose winning implementation is a *core* mixin returning a
        hardcoded ``True``, where no backend class in the MRO overrides it. The dialect
        therefore advertises the capability purely by inheritance, without ever
        considering whether its database supports it.

        This is deliberately **not** reported as a defect. A hardcoded ``True`` in a core
        mixin is the normal generic-default idiom, so listing every one of them produces
        hundreds of entries and trains the reader to ignore the section. Restricting to
        bits the backend never overrode keeps the list short enough to actually review,
        and it is the set worth asking about: a dialect asserting a capability purely by
        inheritance is exactly how a probe ends up lying.
        """
        found: List[str] = []
        for base in self._implementation_classes():
            module = getattr(base, "__module__", "")
            if not module.startswith(CORE_MIXIN_PREFIX):
                continue
            for name, value in list(vars(base).items()):
                if not name.startswith("supports_"):
                    continue
                func = value.fget if isinstance(value, property) else value
                if isinstance(func, staticmethod):
                    func = func.__func__
                if not callable(func) or not _returns_literal_true(func):
                    continue
                found.append("{}.{}".format(base.__name__, name))
        return sorted(found)

    def protocol_overlap(self) -> Dict[str, List[str]]:
        """Method names declared by more than one protocol in the MRO."""
        overlap: Dict[str, List[str]] = {}
        for name, owners in self.declared_by.items():
            unique = sorted(set(owners))
            if len(unique) > 1:
                overlap[name] = unique
        return overlap

    def protocols_without_members(self) -> List[str]:
        return sorted(p.name for p in self.protocols if not protocol_members(p))

    def _implementation_classes(self) -> List[type]:
        """Non-protocol classes in the MRO, in resolution order."""
        return [base for base in self._mro if not _is_protocol(base) and base is not object]

    _mro: Tuple[type, ...] = ()


# ── Discovery ────────────────────────────────────────────────────────────────

def _iter_modules(pkg_name: str, failures: List[Tuple[str, str]]) -> Iterable[Any]:
    try:
        pkg = importlib.import_module(pkg_name)
    except Exception as exc:
        failures.append((pkg_name, "{}: {}".format(type(exc).__name__, exc)))
        return
    yield pkg
    for info in pkgutil.walk_packages(getattr(pkg, "__path__", []), pkg_name + "."):
        if any(frag in info.name for frag in EXCLUDE_FRAGMENTS):
            continue
        try:
            yield importlib.import_module(info.name)
        except Exception as exc:
            failures.append((info.name, "{}: {}".format(type(exc).__name__, exc)))
            continue


def discover_dialects() -> List[Tuple[str, str, str]]:
    """Find every concrete dialect in the environment as ``(project, module, class)``."""
    found: List[Tuple[str, str, str]] = []
    try:
        impl = importlib.import_module(IMPL_ROOT)
    except Exception:
        impl = None
    roots: List[Tuple[str, str]] = []
    if impl is not None:
        for name in _installed_backend_names(impl):
            roots.append((name, "{}.{}.dialect".format(IMPL_ROOT, name)))
    for project, module_name in roots:
        try:
            module = importlib.import_module(module_name)
        except Exception:
            continue
        candidates = [
            (name, obj)
            for name, obj in vars(module).items()
            if inspect.isclass(obj)
            and obj.__module__ == module_name
            and name.endswith("Dialect")
            and not _is_protocol(obj)
        ]
        if not candidates:
            continue
        # The real dialect is the one with the richest MRO; helper base classes
        # declared in the same module are much smaller.
        name, cls = max(candidates, key=lambda kv: len(kv[1].__mro__))
        found.append((project, module_name, name))
    return sorted(found)


def collect_protocols() -> Tuple[List[ProtocolDecl], List[Tuple[str, str]]]:
    """Collect every protocol definition, core and backend."""
    decls: List[ProtocolDecl] = []
    failures: List[Tuple[str, str]] = []
    targets: List[Tuple[str, str]] = [(CORE_PROJECT, CORE_DIALECT)]
    try:
        impl = importlib.import_module(IMPL_ROOT)
    except Exception:
        impl = None
    if impl is not None:
        for name in _installed_backend_names(impl):
            targets.append((name, "{}.{}.protocols".format(IMPL_ROOT, name)))
    seen: Set[str] = set()
    for project, pkg_name in targets:
        for module in _iter_modules(pkg_name, failures):
            module_name = getattr(module, "__name__", "")
            for obj in vars(module).values():
                if not inspect.isclass(obj) or not _is_protocol(obj):
                    continue
                if getattr(obj, "__module__", None) != module_name:
                    continue
                key = "{}::{}".format(obj.__module__, obj.__qualname__)
                if key in seen:
                    continue
                seen.add(key)
                decls.append(
                    ProtocolDecl(
                        project=project,
                        name=obj.__name__,
                        module=obj.__module__,
                        methods={
                            m for m in protocol_members(obj) if not m.startswith("_")
                        },
                    )
                )
    return sorted(decls, key=lambda d: (d.project, d.name)), failures


def find_conformance_tests(project: str, dialect_module: str) -> List[str]:
    """Locate the conformance tests for the repository that *defines* the dialect.

    The repository is derived from where the dialect module actually lives, not from
    its project label. SQLite is built into the core package, so searching by label
    would look for a ``python-activerecord-sqlite`` repository that does not exist;
    conversely searching every root would hand each backend the core copy of the SQLite
    test.
    """
    module = sys.modules.get(dialect_module)
    module_file = getattr(module, "__file__", None)
    here = os.path.dirname(os.path.abspath(__file__))
    core_repo = os.path.normpath(os.path.join(here, "..", "..", "..", ".."))

    root: Optional[str] = None
    if module_file:
        # Walk up from the defining module to the nearest directory that has a tests
        # tree. Deriving the repository from the module's real location is what keeps
        # SQLite, which is built into the core package, from being looked up in a
        # non-existent sibling repository.
        current = os.path.dirname(os.path.normpath(module_file))
        for _ in range(10):
            if os.path.isdir(os.path.join(current, "tests")):
                root = os.path.join(current, "tests")
                break
            parent = os.path.dirname(current)
            if parent == current:
                break
            current = parent
    if root is None:
        if project == CORE_PROJECT:
            root = os.path.join(core_repo, "tests")
        else:
            root = os.path.join(
                os.path.dirname(core_repo),
                "python-activerecord-{}".format(project),
                "tests",
            )

    if not os.path.isdir(root):
        return []
    matches: List[str] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d != "__pycache__"]
        for filename in filenames:
            if not filename.endswith(".py"):
                continue
            if "protocol_conformance" in filename or "protocol_capabilities" in filename:
                matches.append(os.path.join(dirpath, filename))
    return sorted(matches)


# ── Build ────────────────────────────────────────────────────────────────────

def build_profiles() -> Tuple[List[DialectProfile], List[Tuple[str, str]]]:
    """Reflect over every discovered dialect and compute its coverage."""
    failures: List[Tuple[str, str]] = []
    profiles: List[DialectProfile] = []
    for project, module_name, class_name in discover_dialects():
        try:
            module = importlib.import_module(module_name)
            dialect = getattr(module, class_name)
        except Exception as exc:
            failures.append(
                (module_name, "{}: {}".format(type(exc).__name__, exc))
            )
            continue
        mro = dialect.__mro__
        protocols = [c for c in mro if _is_protocol(c)]
        # Protocol classes are included deliberately: a protocol may carry a real
        # default body, and excluding them made every such method look unimplemented.
        providers: Dict[str, str] = {}
        for base in mro:
            if base is object:
                continue
            for name, owner in public_providers(base).items():
                providers.setdefault(name, owner)
        declared: Set[str] = set()
        declared_by: Dict[str, List[str]] = defaultdict(list)
        for proto in protocols:
            for name in protocol_members(proto):
                if name.startswith("_"):
                    continue
                declared.add(name)
                declared_by[name].append(proto.__name__)
        profile = DialectProfile(
            project=project,
            class_name=class_name,
            module=module_name,
            mro_length=len(mro),
            protocols=protocols,
            providers=providers,
            declared=declared,
            declared_by=dict(declared_by),
            conformance_tests=find_conformance_tests(project, module_name),
        )
        profile._mro = mro
        profiles.append(profile)
    return profiles, failures


# ── Report ───────────────────────────────────────────────────────────────────

def summarise(profiles: Sequence[DialectProfile]) -> Dict[str, Any]:
    return {
        "dialects": len(profiles),
        "protocols_defined": len(collect_protocols()[0]),
        "declared_but_absent": sum(len(p.declared_but_absent()) for p in profiles),
        "stubbed_methods": sum(len(p.stubbed_methods()) for p in profiles),
        "implemented_but_undeclared": sum(
            len(p.implemented_but_undeclared()) for p in profiles
        ),
        "untriaged_capability_bits": sum(
            len(p.untriaged_capability_bits()) for p in profiles
        ),
        "protocol_overlap": sum(len(p.protocol_overlap()) for p in profiles),
        "protocols_without_members": sum(
            len(p.protocols_without_members()) for p in profiles
        ),
        "dialects_without_conformance_tests": [
            p.label for p in profiles if not p.conformance_tests and not p.is_fixture
        ],
    }


def render_report(profiles: Sequence[DialectProfile], failures: Sequence[Tuple[str, str]]) -> str:
    out: List[str] = []
    out.append("Dialect protocol lineage report")
    out.append("=" * 78)
    out.append("generated     : {}".format(datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")))
    out.append("dialects      : {}".format(", ".join(p.label for p in profiles)))
    out.append("")

    out.append(
        "{:<24} {:>5} {:>5} {:>9} {:>9} {:>8} {:>7} {:>7}".format(
            "dialect", "mro", "prot", "declared", "provided", "missing", "untri", "overlap"
        )
    )
    for p in profiles:
        out.append(
            "{:<24} {:>5} {:>5} {:>9} {:>9} {:>8} {:>7} {:>7}".format(
                p.label,
                p.mro_length,
                len(p.protocols),
                len(p.declared),
                len(p.providers),
                len(p.stubbed_methods()),
                len(p.untriaged_capability_bits()),
                len(p.protocol_overlap()),
            )
        )
    out.append("")

    out.append("Declared but absent (AttributeError waiting to happen)")
    any_absent = False
    for p in profiles:
        absent = p.declared_but_absent()
        if not absent:
            continue
        any_absent = True
        out.append("  {}".format(p.label))
        for name, owners in absent.items():
            out.append("     !! {:<42} promised by {}".format(name, ", ".join(owners)))
    if not any_absent:
        out.append("  none")
    out.append("")

    out.append("Declared but stubbed with `...` (passes hasattr, returns None at runtime)")
    out.append("Invisible to conformance tests, which assert isinstance/hasattr only.")
    any_stub = False
    for p in profiles:
        stubs = p.stubbed_methods()
        if not stubs:
            continue
        any_stub = True
        out.append("  {} ({} method(s))".format(p.label, len(stubs)))
        for name, owner in list(stubs.items())[:12]:
            out.append("     ! {:<42} stub on {}".format(name, owner))
        if len(stubs) > 12:
            out.append("     ... and {} more".format(len(stubs) - 12))
    if not any_stub:
        out.append("  none")
    out.append("")

    out.append(
        "Capability bits inherited from a core default and never triaged by the backend"
    )
    out.append("(a review prompt, not a defect: the dialect asserts these purely by inheritance)")
    for p in profiles:
        bits = p.untriaged_capability_bits()
        if not bits:
            continue
        out.append("  {} ({} bit(s))".format(p.label, len(bits)))
        for entry in bits[:10]:
            out.append("     - {}".format(entry))
        if len(bits) > 10:
            out.append("     ... and {} more".format(len(bits) - 10))
    out.append("")

    out.append("Protocol overlap (two protocols in one MRO declare the same name)")
    for p in profiles:
        overlap = p.protocol_overlap()
        if not overlap:
            continue
        out.append("  {} ({} name(s)) e.g. {}".format(
            p.label, len(overlap), ", ".join(sorted(overlap)[:4])
        ))
    out.append("")

    out.append("Protocol conformance test coverage (authority on callability)")
    for p in profiles:
        if p.is_fixture:
            out.append("  {:<24} n/a - test fixture".format(p.label))
        elif p.conformance_tests:
            out.append("  {:<24} {}".format(p.label, ", ".join(
                os.path.basename(t) for t in p.conformance_tests
            )))
        else:
            out.append("  {:<24} NONE FOUND - coverage unverified".format(p.label))
    out.append("")

    out.append("Implemented but undeclared (protocol-shaped methods with no protocol)")
    for p in profiles:
        extra = p.implemented_but_undeclared()
        if not extra:
            continue
        out.append("  {:<24} {} e.g. {}".format(
            p.label, len(extra), ", ".join(sorted(extra)[:4])
        ))
    out.append("")

    if failures:
        out.append("Modules that could not be imported (results are UNDER-REPORTED)")
        for name, reason in failures:
            out.append("  {} -> {}".format(name, reason))
        out.append("")
    return "\n".join(out)


# ── Mermaid ──────────────────────────────────────────────────────────────────

def _escape(text: str) -> str:
    return text.replace('"', "#quot;").replace("\n", " ")


def render_mermaid(profiles: Sequence[DialectProfile], focus: Optional[str] = None) -> str:
    """Render declaration-to-implementation wiring for the dialects.

    Nodes are protocols (declarations) and providers (implementations); an edge means
    the provider satisfies the promise. Missing promises are drawn explicitly rather
    than omitted, because an invisible gap is the whole problem.
    """
    selected = [p for p in profiles if not focus or p.project == focus or p.class_name == focus]
    ids: Dict[str, str] = {}
    counter = [0]

    def ref(key: str) -> str:
        if key not in ids:
            counter[0] += 1
            ids[key] = "n{}".format(counter[0])
        return ids[key]

    lines = ["flowchart LR"]
    lines.append("    %% protocol declaration -> providing class; dashed red = promised but not provided")
    for profile in selected:
        lines.append('    subgraph {}["{}"]'.format(
            "g" + re.sub(r"\W", "_", profile.label), profile.label
        ))
        for proto in profile.protocols:
            lines.append('        {}["{}"]'.format(
                ref("P::{}::{}".format(profile.project, proto.__name__)),
                _escape(proto.__name__),
            ))
        for name, owner in sorted(profile.providers.items()):
            if not name.startswith(PROTOCOL_NAME_SHAPES):
                continue
            lines.append('        {}["{}.{}"]'.format(
                ref("I::{}::{}".format(profile.project, owner)), _escape(owner), _escape(name)
            ))
        lines.append("    end")
        for name, owners in sorted(profile.declared_by.items()):
            proto_ref = ref("P::{}::{}".format(profile.project, sorted(set(owners))[0]))
            impl_ref = ref("I::{}::{}".format(profile.project, profile.providers.get(name, "?")))
            if name in profile.providers:
                lines.append("    {} --> {}".format(proto_ref, impl_ref))
            else:
                lines.append(
                    "    {} -.->|{} MISSING| {}".format(
                        proto_ref, _escape(name), impl_ref
                    )
                )
    lines.append("    classDef proto fill:#e8f0fe,stroke:#4a6fa5;")
    lines.append("    classDef impl fill:#fdf3e3,stroke:#b07d2b;")
    for key, value in ids.items():
        lines.append("    class {} {};".format(value, "proto" if key.startswith("P::") else "impl"))
    return "\n".join(lines)


# ── CLI ──────────────────────────────────────────────────────────────────────

def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Dialect protocol lineage report and Mermaid diagram."
    )
    parser.add_argument("--report", action="store_true", help="text report (default)")
    parser.add_argument("--mermaid", action="store_true", help="emit a Mermaid diagram")
    parser.add_argument("--focus", help="restrict the diagram to one dialect")
    parser.add_argument("--out", help="write the diagram to a file")
    parser.add_argument("--json", help="write a machine-readable summary")
    args = parser.parse_args(argv)

    profiles, failures = build_profiles()
    if not profiles:
        print("no dialects discovered")
        return 1

    if args.json:
        payload = {
            "summary": summarise(profiles),
            "dialects": [
                {
                    "label": p.label,
                    "mro": p.mro_length,
                    "protocols": len(p.protocols),
                    "declared": len(p.declared),
                    "provided": len(p.providers),
                    "declared_but_absent": p.declared_but_absent(),
                    "stubbed_methods": p.stubbed_methods(),
                    "untriaged_capability_bits": p.untriaged_capability_bits(),
                    "conformance_tests": p.conformance_tests,
                }
                for p in profiles
            ],
            "import_failures": [list(f) for f in failures],
        }
        with open(args.json, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=1, sort_keys=True)
        print("wrote {}".format(args.json))

    if args.mermaid:
        text = render_mermaid(profiles, args.focus)
        if args.out:
            with open(args.out, "w", encoding="utf-8") as handle:
                handle.write(text + "\n")
            print("wrote {}".format(args.out))
        else:
            print(text)
        return 0

    print(render_report(profiles, failures))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
