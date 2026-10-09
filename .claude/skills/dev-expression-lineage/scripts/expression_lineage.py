# .claude/skills/dev-expression-lineage/scripts/expression_lineage.py
"""Expression lineage data model across the core package and every backend.

Modelling premises
------------------
1. **An expression is a subclass of ``BaseExpression`` and nothing else.**
   ``rhosocial.activerecord.backend.expression.mixins`` holds six mixins
   (``ComparisonMixin``, ``StringMixin``, ``TypeCastingMixin`` and friends) that
   derive from ``object`` only. They are ingredients, not expressions, so they
   never become lineage nodes; they are recorded per node under
   :attr:`LineageNode.mixins` instead. Treating them as nodes was an earlier bug
   that inflated the graph with non-pedigree edges.

2. **Lineage is a DAG, not a tree.** Expression classes multiply inherit from
   several expression bases at once, so the adjacency structure is a directed
   multigraph with cycle guards on every traversal.

3. **Identity is ``(project, qualname)``, never the bare class name.** Duplicate
   names across packages are the norm, so a class name cannot address a node.

4. **Layering must be decidable from the data.** The core package is layer 0 and
   each backend is layer 1. The repository's iron rule forbids a backend from
   inheriting from a *sibling* backend, so a cross-backend edge is a violation
   signal the model can answer, not something a human eyeballs in a diagram.

5. **The expected package layout is a guarantee, not a convention.** Expressions
   live under ``backend.expression`` and ``impl.<name>.expression``. This used to
   be a convention with known exceptions: introspection expressions sat in
   ``impl.<name>.show.expressions`` and ``PostgresEnumType`` in
   ``impl.<name>.types``. Those have been relocated, so
   :meth:`LineageGraph.misplaced` is now an enforceable invariant that should
   report zero, and no exemption list exists.

6. **Weak references are not inheritance.** Module-level ``if TYPE_CHECKING:``
   imports exist only for annotations, are not lineage edges, and rot silently —
   the historical case being Firebird's ``mixins/window.py`` importing
   ``WindowFunctionCallExpression`` while the core defined
   ``WindowFunctionCall``, both since unified into ``FunctionCall``. They live in
   :attr:`LineageGraph.typecheck_imports`, parallel to the DAG.

Layering of concerns
--------------------
This module models only. Derived queries live in the analysis section of
:class:`LineageGraph`; Mermaid rendering is a separate downstream consumer, so
the model can be cached, serialised and diffed while the renderer stays
replaceable.
"""

from __future__ import annotations

import ast
import importlib
import importlib.util
import inspect
import json
import os
import pkgutil
import subprocess
import sys
import textwrap
import types
import warnings
from collections import defaultdict
import dataclasses
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional, Sequence, Set, Tuple

warnings.filterwarnings("ignore")

#: The lineage root. Every node in the graph is a subclass of this class.
DEFAULT_ROOT = "rhosocial.activerecord.backend.expression.bases.BaseExpression"

#: Namespace roots used for runtime discovery.
IMPL_ROOT = "rhosocial.activerecord.backend.impl"
CORE_EXPRESSION = "rhosocial.activerecord.backend.expression"

CORE_PROJECT = "core"
EXTERNAL_PROJECT = "external"
CORE_LAYER = 0
BACKEND_LAYER = 1

#: Module-name fragments skipped while scanning (examples, tests, caches).
EXCLUDE_FRAGMENTS = ("examples", "tests", "test_", "__pycache__", ".cover")

#: Package segment that marks the home of expression classes. There is no
#: exemption list: an expression defined anywhere else is a defect.
#:
#: This tool used to carry a secondary-home allowlist of ``("show", "types")``.
#: The backends kept introspection expressions in ``impl.<name>.show.expressions``
#: (20 classes each in ClickHouse, MySQL and MariaDB, 9 in Oracle) and
#: ``PostgresEnumType`` in ``impl.<name>.types``, and the allowlist existed only to
#: stop :meth:`LineageGraph.misplaced` reporting those 70 classes. They were
#: drift, not intent; all have since moved into the expression namespace
#: (``expression/show.py`` and ``expression/enum_.py``) and the top-level ``types``
#: package has been renamed ``type_values`` to free the name for DataType
#: expressions. The allowlist is gone rather than emptied, because an empty one
#: would only invite the next exemption.
EXPRESSION_SEGMENT = "expression"

NodeId = str


def make_id(project: str, qualname: str) -> NodeId:
    """Build the stable node identifier ``project::qualname``."""
    return "{}::{}".format(project, qualname)


def split_id(node_id: NodeId) -> Tuple[str, str]:
    """Split ``project::qualname`` into ``(project, qualname)``."""
    project, _, qualname = node_id.partition("::")
    return project, qualname


def family_of(module: str) -> str:
    """Derive a family label from a module path, used to scope diagrams.

    The inventory runs to well over a thousand classes and cannot fit one
    diagram, so families are the natural unit of selection. The label is the
    module path below the project's expression package, because the two halves of
    the repository disagree on layout: the core keeps modules at
    ``expression/statements/ddl_domain.py`` while the backends use
    ``expression/ddl/domain.py``. Taking the segment after ``expression`` would
    therefore yield the useless labels ``statements`` and ``ddl``; the tail keeps
    the distinguishing part in both cases.

    ``...expression.statements.ddl_domain`` -> ``statements.ddl_domain``
    ``...impl.postgres.expression.ddl.domain`` -> ``ddl.domain``
    ``...impl.mysql.expression.partition``   -> ``partition``
    ``...impl.postgres.expression.enum_``    -> ``enum_``
    """
    parts = module.split(".")
    if EXPRESSION_SEGMENT in parts:
        idx = len(parts) - 1 - parts[::-1].index(EXPRESSION_SEGMENT)
        tail = parts[idx + 1 :]
        return ".".join(tail) if tail else EXPRESSION_SEGMENT
    if IMPL_ROOT.split(".")[-1] in parts:
        idx = len(parts) - 1 - parts[::-1].index(IMPL_ROOT.split(".")[-1])
        tail = parts[idx + 2 :]
        return ".".join(tail) if tail else parts[-1]
    return parts[-1] if parts else "?"


def load_root_class(dotted: str = DEFAULT_ROOT) -> type:
    """Import and return the lineage root class."""
    module_name, _, attr = dotted.rpartition(".")
    return getattr(importlib.import_module(module_name), attr)


def provenance(repo_root: Optional[str] = None) -> Dict[str, Any]:
    """Describe the code revision a baseline or diagram was produced from."""
    root = repo_root or os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "..")
    )

    def git(*args: str) -> str:
        try:
            return subprocess.run(
                ["git", *args], cwd=root, capture_output=True, text=True
            ).stdout.strip()
        except Exception:
            return ""

    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "repo_root": root,
        "core_revision": git("rev-parse", "HEAD"),
        "core_branch": git("rev-parse", "--abbrev-ref", "HEAD"),
        "core_describe": git("describe", "--tags", "--always"),
        "note": (
            "Projects are discovered from the active interpreter; nodes are "
            "subclasses of the lineage root only."
        ),
    }


# ── Project scope ────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class TypecheckImport:
    """A module-level ``if TYPE_CHECKING:`` import, i.e. an annotation-only reference.

    These are not inheritance edges. They are tracked separately because they rot
    silently — Firebird's ``mixins/window.py`` used to import
    ``WindowFunctionCallExpression`` while the core defined ``WindowFunctionCall``,
    until both were unified into ``FunctionCall``. The source location is retained
    so a fixer can rewrite the offending line without re-deriving it.

    Attributes:
        project: Project label the importing module belongs to.
        module: Dotted name of the importing module.
        imported_module: Dotted name of the module the import resolves to, after
            relative levels are made absolute.
        name: The attribute looked up in ``imported_module``. For
            ``from m import X as Y`` this is ``X``, because ``m`` is what has to
            define the attribute.
        local_name: The name bound in the importing module, i.e. ``Y`` for an
            aliased import and equal to :attr:`name` otherwise.
        path: Filesystem path of the importing module, when known.
        lineno: 1-based line of the import statement, when known.
        written_level: Number of leading dots as authored.
        written_module: The module exactly as authored, before resolution. The
            fixer needs the author's intent, because the *resolved* module of a
            broken import is not an ancestor of the importing package and so
            carries no usable information about the correct dot count.
    """

    project: str
    module: str
    imported_module: str
    name: str
    local_name: str = ""
    path: Optional[str] = None
    lineno: Optional[int] = None
    written_level: int = 0
    written_module: str = ""

    def __post_init__(self) -> None:
        # Backwards compatible for payloads written before the alias split.
        if not self.local_name:
            object.__setattr__(self, "local_name", self.name)

    def describe(self) -> str:
        location = "{}:{}".format(self.module, self.lineno or "?")
        return "[{}] {} -> {} ({})".format(
            self.project, location, self.name, self.imported_module
        )


@dataclass(frozen=True)
class ProjectSpec:
    """One analysable project: a label plus the packages to walk.

    Attributes:
        label: Short project label used in ids and subgraphs.
        scan_packages: Packages walked for expression classes. A backend scans its
            whole ``impl.<name>`` package, because introspection expressions sit
            outside ``impl.<name>.expression``.
        home_package: Where expressions are expected to live, used only to report
            misplaced classes.
        in_tree: False for third-party namespaces, which the stats keep separate
            so they are never mistaken for repository backends.
    """

    label: str
    scan_packages: Tuple[str, ...]
    home_package: str
    in_tree: bool = True

    @classmethod
    def backend(cls, label: str, in_tree: bool = True) -> "ProjectSpec":
        """Build a spec for a backend rooted at ``impl.<label>``.

        The home is ``impl.<label>.expression`` and there are no exemptions:
        every expression class defined in the backend must live there.
        """
        root = "{}.{}".format(IMPL_ROOT, label)
        return cls(
            label=label,
            scan_packages=(root,),
            home_package="{}.{}".format(root, EXPRESSION_SEGMENT),
            in_tree=in_tree,
        )

    @classmethod
    def custom(
        cls, label: str, scan_package: str, home_package: Optional[str] = None
    ) -> "ProjectSpec":
        """Build a spec for a third-party namespace outside ``IMPL_ROOT``."""
        return cls(
            label=label,
            scan_packages=(scan_package,),
            home_package=home_package or scan_package,
            in_tree=False,
        )

    @property
    def annotation_root(self) -> str:
        """Root used when scanning for ``TYPE_CHECKING`` imports."""
        return self.scan_packages[0]


#: DB driver modules that must never be required in order to analyse expression
#: lineage.
#:
#: Lineage is computed by reflection alone: no connection is opened, no query is
#: issued, no driver is exercised. Yet every backend's ``__init__`` imports its
#: driver eagerly, so a driver that cannot be loaded silently removes the whole
#: backend from the graph. That is how ``pyodbc`` -- a C extension that needs the
#: OS ``libodbc.so``, not just the wheel -- used to cost sqlserver its entire
#: placement audit.
#:
#: Each name is stubbed *only if importing it fails*. A driver that loads
#: normally is left alone, so this never masks a real environment problem with a
#: package that would have imported fine.
#:
#: Every name must be the module the backend actually imports. ``firebird-driver``
#: 2.x is imported as ``firebird.driver`` and aliased to ``fdb`` at the call
#: site, so listing ``fdb`` stubbed a name nothing imports and reported a
#: misleading failure for a working driver. ``psycopg2`` was likewise listed but
#: unused: the postgres backend depends on psycopg 3. Both entries made the
#: stubbed list unreadable as a signal about driver health.
DRIVER_STUB_MODULES = (
    "pyodbc",
    "clickhouse_connect",
    "mysql.connector",
    "mariadb",
    "oracledb",
    "psycopg",
    "snowflake.connector",
    "firebird.driver",
)


def _make_driver_stub(name: str) -> Any:
    """Build an inert stand-in for a DB driver module.

    Attribute access yields a fresh ``Exception`` subclass, which is enough for
    the three things a backend does with its driver at import time: subclass it,
    raise it in an ``except`` clause, and call it. Nothing here is ever meant to
    reach a database.
    """

    module = types.ModuleType(name)
    module.__path__ = []  # type: ignore[attr-defined]
    module.__doc__ = "Inert stub installed by dev-expression-lineage."

    def __getattr__(attr: str) -> Any:  # PEP 562
        if attr.startswith("__") and attr.endswith("__"):
            raise AttributeError(attr)
        stub = type(attr, (Exception,), {"__module__": name})
        setattr(module, attr, stub)
        return stub

    module.__getattr__ = __getattr__  # type: ignore[attr-defined]
    return module


def install_driver_stubs(
    names: Sequence[str] = DRIVER_STUB_MODULES,
) -> List[str]:
    """Stub any listed driver that cannot be imported. Returns the names stubbed.

    Safe to call repeatedly. Must run before :func:`discover_projects`, which is
    the first step that imports a backend package.
    """
    stubbed: List[str] = []
    for name in names:
        root = name.split(".")[0]
        if name in sys.modules:
            continue
        try:
            importlib.import_module(name)
            continue
        except Exception:
            pass
        try:
            importlib.import_module(root)
            continue  # the top-level package loads; only the leaf is absent
        except Exception:
            pass
        sys.modules[name] = _make_driver_stub(name)
        stubbed.append(name)
    return stubbed


def _importable(pkg_name: str) -> bool:
    try:
        importlib.import_module(pkg_name)
        return True
    except Exception:
        return False


def _installed_backend_names(impl_pkg: types.ModuleType) -> List[str]:
    """List the backend directories visible under ``impl.<root>``.

    ``pkgutil.iter_modules`` reports a directory as a package only when it holds
    an ``__init__.py``. The backends are PEP 420 namespace portions, so they have
    none, and enumeration silently returned an empty list: the audit then covered
    the core alone and reported ``0 misplaced`` across a graph of 227 nodes while
    every backend was absent from it.

    A backend is therefore identified by being a directory on ``impl``'s search
    path, which is what the enummeration was always trying to approximate. The
    same ``__path__`` already lists the backends contributed by editable installs
    of the separate backend repositories, so this keeps picking them up.

    Args:
        impl_pkg: The imported ``impl`` namespace package.

    Returns:
        Sorted backend directory names, excluding examples, tests and caches.
    """
    names = set()
    for entry in getattr(impl_pkg, "__path__", ()):
        try:
            children = os.listdir(entry)
        except OSError:
            # A stale path entry from an uninstalled backend, or a path we cannot
            # read. Skipping is right: there is nothing to audit there.
            continue
        for child in children:
            if child.startswith(".") or any(f in child for f in EXCLUDE_FRAGMENTS):
                continue
            if os.path.isdir(os.path.join(entry, child)):
                names.add(child)
    return sorted(names)


def discover_projects(
    extra: Sequence[ProjectSpec] = (),
    impl_root: str = IMPL_ROOT,
    core_expression: str = CORE_EXPRESSION,
) -> List[ProjectSpec]:
    """Discover analysable projects from the runtime environment.

    Enumerates ``rhosocial.activerecord.backend.impl.*`` in the active
    interpreter and keeps every installed backend, plus the core expression
    package. A newly installed backend is picked up without editing this file.
    Backends are recognised as directories rather than as packages, since they
    are PEP 420 namespace portions and carry no ``__init__.py``; see
    :func:`_installed_backend_names`. Third-party namespaces are appended from
    ``extra`` and analysed alongside the in-tree ones.

    DB drivers that cannot be loaded are stubbed first, via
    :func:`install_driver_stubs`. Importing a backend runs its ``__init__``,
    which imports the driver, but the expression classes never use it, so a
    missing driver should not cost a backend its audit.

    Args:
        extra: Third-party :class:`ProjectSpec` entries.
        impl_root: Namespace root that holds the backends.
        core_expression: The core expression package.
    """
    install_driver_stubs()
    specs: List[ProjectSpec] = [
        ProjectSpec(
            label=CORE_PROJECT,
            scan_packages=(core_expression,),
            home_package=core_expression,
            in_tree=True,
        )
    ]
    try:
        impl_pkg = importlib.import_module(impl_root)
    except Exception:
        impl_pkg = None
    if impl_pkg is not None:
        for name in sorted(_installed_backend_names(impl_pkg)):
            specs.append(ProjectSpec.backend(name))
    specs.extend(extra)
    return specs


# ── Node ─────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class LineageNode:
    """One expression class in the lineage graph (immutable).

    Attributes:
        id: ``project::qualname``.
        project: Owning project label; ``external`` marks an out-of-range parent.
        qualname: Reflected qualified class name.
        module: Module that defines the class.
        family: Family label derived from the module path.
        bases: Direct parents **that are expressions**, i.e. the lineage edges.
        mixins: Direct bases that are *not* expressions. Ingredients rather than
            pedigree, kept for diagnostics and never drawn as lineage.
        is_abstract: Declares abstract methods or descends from ABC.
        format_method: The corresponding ``format_*`` method name, when derivable.
        has_render_entry: Whether a render entry point is registered.
    """

    id: NodeId
    project: str
    qualname: str
    module: str
    family: str
    bases: Tuple[NodeId, ...] = ()
    mixins: Tuple[str, ...] = ()
    is_abstract: bool = False
    format_method: Optional[str] = None
    has_render_entry: bool = False

    @property
    def name(self) -> str:
        return self.qualname.rsplit(".", 1)[-1]

    @property
    def is_external(self) -> bool:
        return self.project == EXTERNAL_PROJECT

    @property
    def is_core(self) -> bool:
        return self.project == CORE_PROJECT

    @property
    def is_backend(self) -> bool:
        return self.project not in (CORE_PROJECT, EXTERNAL_PROJECT)

    @property
    def layer(self) -> Optional[int]:
        """0 for the core package, 1 for a backend, None when out of range."""
        if self.is_external:
            return None
        return CORE_LAYER if self.is_core else BACKEND_LAYER

    def replace(self, **changes: Any) -> "LineageNode":
        """Return a copy with the given fields replaced (frozen dataclass)."""
        merged: Dict[str, Any] = {
            "id": self.id,
            "project": self.project,
            "qualname": self.qualname,
            "module": self.module,
            "family": self.family,
            "bases": self.bases,
            "mixins": self.mixins,
            "is_abstract": self.is_abstract,
            "format_method": self.format_method,
            "has_render_entry": self.has_render_entry,
        }
        merged.update(changes)
        return LineageNode(**merged)  # type: ignore[arg-type]


# ── Graph ────────────────────────────────────────────────────────────────────

class LineageGraph:
    """Directed multigraph of expression inheritance with layer analysis."""

    def __init__(self, root_class_name: str = DEFAULT_ROOT) -> None:
        self._nodes: Dict[NodeId, LineageNode] = {}
        self._children: Dict[NodeId, Set[NodeId]] = defaultdict(set)
        self._by_class: Dict[int, NodeId] = {}
        self._pending: List[Tuple[NodeId, Tuple[type, ...], Tuple[str, ...]]] = []
        self._mixin_names: Set[str] = set()
        self._home: Dict[str, str] = {}
        self.typecheck_imports: List[TypecheckImport] = []
        self.parse_failures: List[Tuple[str, str]] = []
        self.unimportable: List[Tuple[str, str, str]] = []
        self.root_class_name = root_class_name

    def set_home_package(self, project: str, home_package: str) -> None:
        """Record where a project's expressions are expected to live.

        The expected package is recorded rather than reconstructed from the module
        path, because a third-party namespace may expose its expressions from a
        package this tool does not assume, and would otherwise be reported
        wholesale as misplaced.
        """
        self._home[project] = home_package

    # ── Construction ──────────────────────────────────────────────────────

    def add(self, node: LineageNode) -> None:
        self._nodes[node.id] = node
        self._children.setdefault(node.id, set())

    def register_class(self, cls: type, node_id: NodeId) -> None:
        """Record ``id(cls) -> NodeId`` so base classes can be resolved."""
        self._by_class[id(cls)] = node_id

    def add_pending(
        self, node_id: NodeId, bases: Tuple[type, ...], mixins: Tuple[str, ...]
    ) -> None:
        self._pending.append((node_id, bases, mixins))
        self._mixin_names.update(mixins)

    def add_typecheck_import(self, ref: TypecheckImport) -> None:
        self.typecheck_imports.append(ref)

    def resolve(self) -> None:
        """Resolve deferred bases into ids and build reverse edges.

        A parent that was not scanned becomes an ``external`` placeholder node so
        the truncation point stays explicit instead of vanishing.
        """
        for node_id, base_classes, mixins in self._pending:
            resolved: List[NodeId] = []
            for base in base_classes:
                base_id = self._by_class.get(id(base))
                if base_id is None:
                    qualname = "{}.{}".format(base.__module__, base.__qualname__)
                    base_id = make_id(EXTERNAL_PROJECT, qualname)
                    if base_id not in self._nodes:
                        self.add(
                            LineageNode(
                                id=base_id,
                                project=EXTERNAL_PROJECT,
                                qualname=qualname,
                                module=base.__module__,
                                family=family_of(base.__module__),
                                is_abstract=True,
                            )
                        )
                resolved.append(base_id)
            self._nodes[node_id] = self._nodes[node_id].replace(
                bases=tuple(dict.fromkeys(resolved)), mixins=mixins
            )
        self._pending.clear()
        for node in list(self._nodes.values()):
            for base_id in node.bases:
                self._children[base_id].add(node.id)
        for node_id in self._nodes:
            self._children.setdefault(node_id, set())

    # ── Access ────────────────────────────────────────────────────────────

    def __len__(self) -> int:
        return len(self._nodes)

    def __contains__(self, node_id: object) -> bool:
        return node_id in self._nodes

    def node(self, node_id: NodeId) -> LineageNode:
        return self._nodes[node_id]

    def nodes(self) -> List[LineageNode]:
        """All nodes, stably ordered by ``(project, qualname)``."""
        return [self._nodes[k] for k in sorted(self._nodes)]

    def children_of(self, node_id: NodeId) -> Set[NodeId]:
        return set(self._children.get(node_id, ()))

    def mixin_names(self) -> List[str]:
        return sorted(self._mixin_names)

    def select(
        self,
        project: Optional[str] = None,
        family: Optional[str] = None,
        include_external: bool = True,
    ) -> List[LineageNode]:
        """Filter nodes by project and/or family; the pre-render selection layer."""
        out = []
        for node in self.nodes():
            if not include_external and node.is_external:
                continue
            if project and node.project != project:
                continue
            if family and node.family != family:
                continue
            out.append(node)
        return out

    def roots(self, project: Optional[str] = None) -> List[LineageNode]:
        """Classes with no expression parent, i.e. pedigree entry points."""
        return [
            n
            for n in self.nodes()
            if not n.bases and (project is None or n.project == project)
        ]

    def leaves(self) -> List[LineageNode]:
        """Classes with no children, i.e. the most derived expressions."""
        return [n for n in self.nodes() if not self._children.get(n.id)]

    def ancestors(self, node_id: NodeId) -> Set[NodeId]:
        """All ancestors, with a cycle guard."""
        seen: Set[NodeId] = set()
        stack = list(self._nodes[node_id].bases) if node_id in self._nodes else []
        while stack:
            cur = stack.pop()
            if cur in seen:
                continue
            seen.add(cur)
            node = self._nodes.get(cur)
            if node:
                stack.extend(node.bases)
        return seen

    def descendants(self, node_id: NodeId) -> Set[NodeId]:
        """All descendants, with a cycle guard."""
        seen: Set[NodeId] = set()
        stack = [node_id]
        while stack:
            cur = stack.pop()
            for child in self._children.get(cur, ()):
                if child not in seen:
                    seen.add(child)
                    stack.append(child)
        return seen

    def depth(self, node_id: NodeId) -> int:
        """Distance to the nearest root, shortest path through diamonds."""
        memo: Dict[NodeId, int] = {}

        def walk(cur: NodeId, guard: frozenset) -> int:
            if cur in memo:
                return memo[cur]
            if cur in guard:
                return 0
            node = self._nodes.get(cur)
            if not node or not node.bases:
                memo[cur] = 0
                return 0
            memo[cur] = min(walk(b, guard | {cur}) for b in node.bases) + 1
            return memo[cur]

        return walk(node_id, frozenset())

    def max_depth(self) -> int:
        return max((self.depth(n.id) for n in self.nodes()), default=0)

    # ── Analysis ──────────────────────────────────────────────────────────

    def consumers(self, node_id: NodeId) -> Set[str]:
        """Distinct backends that directly or transitively derive this node.

        This is the metric that decides "core or backend?". The more backends
        consume a class, the more work the generic layer absorbs on their behalf,
        which is what the two-way responsibility rule asks of the core.
        """
        found: Set[str] = set()
        for child in self.descendants(node_id):
            node = self._nodes.get(child)
            if node and node.is_backend:
                found.add(node.project)
        return found

    def consumer_counts(self) -> List[Tuple[NodeId, int, Set[str]]]:
        """Every core class with its consumer count, sparsest first.

        Rows are ``(node_id, consumer_count, consumers)`` sorted by
        ``(count, node_id)`` so thinly adopted classes surface first.
        """
        rows: List[Tuple[NodeId, int, Set[str]]] = []
        for node in self.nodes():
            if not node.is_core:
                continue
            consumers = self.consumers(node.id)
            rows.append((node.id, len(consumers), consumers))
        rows.sort(key=lambda row: (row[1], row[0]))
        return rows

    def violations(self) -> List[Tuple[NodeId, NodeId]]:
        """Iron-rule violations: **cross-backend** inheritance.

        Requires ``child.project != parent.project`` with both in the backend
        layer. Inheritance *within* one backend (``MySQLPointType`` deriving from
        ``MySQLGeometryType``) is ordinary type hierarchy and is deliberately not
        listed; only MySQL reaching into Postgres, or MariaDB into MySQL, breaks
        the rule. Returns ``(child, parent)`` pairs.
        """
        bad: List[Tuple[NodeId, NodeId]] = []
        for node in self.nodes():
            if not node.is_backend:
                continue
            for base_id in node.bases:
                parent = self._nodes.get(base_id)
                if parent and parent.is_backend and parent.project != node.project:
                    bad.append((node.id, base_id))
        return sorted(bad)

    def intra_project_bases(self) -> List[Tuple[NodeId, NodeId]]:
        """Same-backend inheritance edges, used to style edges differently."""
        out: List[Tuple[NodeId, NodeId]] = []
        for node in self.nodes():
            if not node.is_backend:
                continue
            for base_id in node.bases:
                parent = self._nodes.get(base_id)
                if parent and parent.is_backend and parent.project == node.project:
                    out.append((node.id, base_id))
        return sorted(out)

    def misplaced(self) -> List[NodeId]:
        """Expression classes living outside their project's expression package.

        The rule is ``backend.expression`` for the core and
        ``impl.<name>.expression`` for a backend, with no exemptions. This was
        previously a convention carrying 70 exceptions -- the ``show``
        introspection expressions and ``PostgresEnumType`` -- which were excused
        and then relocated, so the expected result is empty and any entry is a
        genuine regression. The expected package comes from the recorded
        :class:`ProjectSpec`, so a third-party namespace is judged by the home it
        declares rather than by the in-tree convention.
        """
        out: List[NodeId] = []
        for node in self.nodes():
            if node.is_external:
                continue
            expected = self._home.get(node.project)
            if not expected:
                continue
            if not node.module.startswith(expected):
                out.append(node.id)
        return out

    def dangling_typecheck_refs(self) -> List[TypecheckImport]:
        """``TYPE_CHECKING`` imports whose attribute cannot be resolved.

        Resolution is attempted against the import's *source module*, not against
        the class inventory: names such as ``SQLDialectBase`` or
        ``ClickHouseDialect`` are dialect classes that no expression module
        exports, which is normal. Only a module that imports cleanly while the
        attribute is missing is genuinely dangling.

        Returns the unresolvable :class:`TypecheckImport` records.
        """
        return [
            ref
            for ref in self.typecheck_imports
            if not _resolves(ref.imported_module, ref.name)
        ]

    def stats(self) -> Dict[str, Any]:
        """Aggregate counts used by both the report and the diagram captions."""
        by_project: Dict[str, int] = defaultdict(int)
        by_family: Dict[str, int] = defaultdict(int)
        for node in self.nodes():
            by_project[node.project] += 1
            by_family[node.family] += 1
        return {
            "root_class": self.root_class_name,
            "nodes": len(self._nodes),
            "edges": sum(len(n.bases) for n in self._nodes.values()),
            "external_nodes": sum(1 for n in self._nodes.values() if n.is_external),
            "max_depth": self.max_depth(),
            "by_project": dict(sorted(by_project.items())),
            "by_family": dict(sorted(by_family.items(), key=lambda kv: (-kv[1], kv[0]))),
            "cross_backend_violations": len(self.violations()),
            "misplaced": len(self.misplaced()),
            "mixins": len(self._mixin_names),
            "dangling_typecheck": len(self.dangling_typecheck_refs()),
            "parse_failures": len(self.parse_failures),
            "unimportable": len(self.unimportable),
        }

    # ── Persistence ───────────────────────────────────────────────────────

    def to_dict(self) -> Dict[str, Any]:
        return {
            "root_class": self.root_class_name,
            "home_packages": dict(self._home),
            "parse_failures": [list(f) for f in self.parse_failures],
            "unimportable": [list(u) for u in self.unimportable],
            "typecheck_imports": [dataclasses.asdict(t) for t in self.typecheck_imports],
            "nodes": [
                {
                    "id": n.id,
                    "project": n.project,
                    "qualname": n.qualname,
                    "module": n.module,
                    "family": n.family,
                    "bases": list(n.bases),
                    "mixins": list(n.mixins),
                    "is_abstract": n.is_abstract,
                    "format_method": n.format_method,
                    "has_render_entry": n.has_render_entry,
                }
                for n in self.nodes()
            ],
        }

    @classmethod
    def from_dict(cls, payload: Dict[str, Any]) -> "LineageGraph":
        graph = cls(payload.get("root_class", DEFAULT_ROOT))
        graph._home.update(payload.get("home_packages", {}))
        for path, message in payload.get("parse_failures", []):
            graph.parse_failures.append((path, message))
        for project, package, reason in payload.get("unimportable", []):
            graph.unimportable.append((project, package, reason))
        for raw in payload.get("nodes", []):
            graph.add(
                LineageNode(
                    id=raw["id"],
                    project=raw["project"],
                    qualname=raw["qualname"],
                    module=raw["module"],
                    family=raw["family"],
                    bases=tuple(raw.get("bases", ())),
                    mixins=tuple(raw.get("mixins", ())),
                    is_abstract=raw.get("is_abstract", False),
                    format_method=raw.get("format_method"),
                    has_render_entry=raw.get("has_render_entry", False),
                )
            )
            graph._mixin_names.update(raw.get("mixins", ()))
        for raw in payload.get("typecheck_imports", []):
            graph.add_typecheck_import(TypecheckImport(**raw))
        for node in list(graph._nodes.values()):
            for base_id in node.bases:
                graph._children[base_id].add(node.id)
        for node_id in graph._nodes:
            graph._children.setdefault(node_id, set())
        return graph

    def save(self, path: str) -> None:
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(
                self.to_dict(), handle, ensure_ascii=False, indent=1, sort_keys=True
            )

    @classmethod
    def load(cls, path: str) -> "LineageGraph":
        with open(path, encoding="utf-8") as handle:
            return cls.from_dict(json.load(handle))


# ── Reflection build ─────────────────────────────────────────────────────────

def _iter_modules(
    pkg_name: str, failures: Optional[List[Tuple[str, str]]] = None
) -> Iterable[Any]:
    """Import a package and yield every module beneath it.

    A module that cannot be imported is recorded rather than dropped. Skipping it
    silently would under-report the graph, and for a whole package the effect is
    that the project disappears from the results with no explanation.
    """
    try:
        pkg = importlib.import_module(pkg_name)
    except Exception as exc:
        if failures is not None:
            failures.append((pkg_name, "{}: {}".format(type(exc).__name__, exc)))
        return
    yield pkg
    for info in pkgutil.walk_packages(getattr(pkg, "__path__", []), pkg_name + "."):
        if any(frag in info.name for frag in EXCLUDE_FRAGMENTS):
            continue
        try:
            yield importlib.import_module(info.name)
        except Exception as exc:
            if failures is not None:
                failures.append((info.name, "{}: {}".format(type(exc).__name__, exc)))
            continue


def _parse_typecheck_imports(
    project: str,
    path: str,
    package: str,
    module_name: str,
    parse_failures: Optional[List[Tuple[str, str]]] = None,
) -> List[TypecheckImport]:
    """Read one source file and return its ``if TYPE_CHECKING:`` imports.

    Parsing the file directly, rather than importing the module, keeps the scan
    free of import side effects and lets it cover packages never imported during
    the lineage walk.
    """
    if parse_failures is None:
        parse_failures = []
    try:
        with open(path, "r", encoding="utf-8") as handle:
            source = handle.read()
    except OSError:
        return []
    try:
        tree = ast.parse(textwrap.dedent(source))
    except SyntaxError as exc:
        # Never swallow this. An unparseable file yields no TYPE_CHECKING imports,
        # which would make a broken file look clean; the failure is recorded so the
        # report can raise it.
        parse_failures.append((path, "{}:{}: {}".format(path, exc.lineno, exc.msg)))
        return []

    def absolutize(level: int, imported: Optional[str]) -> Optional[str]:
        """Resolve ``from ..a.b import X`` to an absolute module name.

        Level 0 is already absolute and must be returned unchanged; anchoring it
        to the importing module would synthesise a path that never existed.
        """
        if not imported:
            return None
        if level == 0:
            return imported
        try:
            return importlib.util.resolve_name("." * level + imported, package)
        except Exception:
            parts = (package.split(".") if package else [])[: -(level - 1)]
            return ".".join([p for p in parts + imported.split(".") if p])

    found: List[TypecheckImport] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        test = node.test
        is_typecheck = (isinstance(test, ast.Name) and test.id == "TYPE_CHECKING") or (
            isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING"
        )
        if not is_typecheck:
            continue
        for sub in ast.walk(node):
            if isinstance(sub, ast.ImportFrom):
                source = absolutize(sub.level, sub.module)
                if not source:
                    continue
                for alias in sub.names:
                    found.append(
                        TypecheckImport(
                            project=project,
                            module=module_name,
                            imported_module=source,
                            # Resolve the *source* attribute, not the local binding.
                            # ``from m import X as Y`` is satisfied when ``m`` defines X;
                            # looking up Y would report every aliased import as dangling.
                            name=alias.name,
                            local_name=alias.asname or alias.name,
                            path=path,
                            lineno=sub.lineno,
                            written_level=sub.level,
                            written_module=sub.module or "",
                        )
                    )
            elif isinstance(sub, ast.Import):
                for alias in sub.names:
                    found.append(
                        TypecheckImport(
                            project=project,
                            module=module_name,
                            imported_module=alias.name,
                            name=alias.asname or alias.name.rsplit(".", 1)[-1],
                            path=path,
                            lineno=sub.lineno,
                            written_level=0,
                            written_module=alias.name,
                        )
                    )
    return found


def _walk_typecheck_sources(spec: ProjectSpec, graph: LineageGraph) -> None:
    """Harvest ``TYPE_CHECKING`` imports from a project's scan roots.

    Files are located on disk under the installed package directory, so this needs
    no extra imports and reaches modules the lineage walk skips.
    """
    for root_package in spec.scan_packages:
        try:
            pkg = importlib.import_module(root_package)
        except Exception as exc:
            graph.unimportable.append(
                (
                    spec.label,
                    root_package,
                    "{}: {}".format(type(exc).__name__, exc),
                )
            )
            continue
        pkg_paths = getattr(pkg, "__path__", None)
        if not pkg_paths:
            continue
        for directory in pkg_paths:
            for dirpath, dirnames, filenames in os.walk(directory):
                dirnames[:] = [
                    d
                    for d in dirnames
                    if d not in ("__pycache__", "examples", "tests")
                ]
                for filename in filenames:
                    if not filename.endswith(".py"):
                        continue
                    full = os.path.join(dirpath, filename)
                    rel = os.path.relpath(full, directory)
                    module_name = ".".join(
                        [root_package] + rel[: -len(".py")].split(os.sep)
                    )
                    package = module_name.rpartition(".")[0]
                    for ref in _parse_typecheck_imports(
                        spec.label, full, package, module_name, graph.parse_failures
                    ):
                        graph.add_typecheck_import(ref)


def _resolves(imported_module: str, name: str) -> bool:
    """Whether ``imported_module`` exposes ``name``.

    A module that will not import proves nothing either way, so it counts as
    resolved. The shortfall is already reported under ``unimportable``, and
    counting it again here would blame a source file for a missing DB driver:
    ``impl.sqlserver.backend`` cannot be imported without ``libodbc``, which says
    nothing about whether ``SQLServerBackend`` is correctly declared.
    """
    try:
        module = importlib.import_module(imported_module)
    except Exception:
        return True
    return hasattr(module, name)


def _format_method_of(cls: type) -> Optional[str]:
    """Derive the ``format_*`` method name an expression maps to."""
    for attr in ("format_method", "_format_method"):
        value = getattr(cls, attr, None)
        if isinstance(value, str):
            return value
    name = cls.__name__
    for suffix in ("Expression", "Clause", "Action", "Definition", "Statement", ""):
        if name.endswith(suffix):
            stem = name[: -len(suffix)] if suffix else name
            if stem:
                return "format_{}".format(_snake(stem))
    return None


def _snake(name: str) -> str:
    out: List[str] = []
    for i, ch in enumerate(name):
        if ch.isupper():
            if i and not name[i - 1].isupper():
                out.append("_")
            out.append(ch.lower())
        else:
            out.append(ch)
    return "".join(out)


def _has_render_entry(cls: type) -> bool:
    return any(
        hasattr(cls, attr) for attr in ("statement_type", "render_entry", "to_sql")
    )


def build_graph(
    specs: Optional[Sequence[ProjectSpec]] = None,
    extra_specs: Sequence[ProjectSpec] = (),
    scan_annotations: bool = True,
    root_class: str = DEFAULT_ROOT,
) -> LineageGraph:
    """Reflect over the environment and build the lineage DAG.

    Only subclasses of ``root_class`` become nodes. Among a node's direct bases,
    those that are themselves expressions become lineage edges; the rest are
    recorded as mixins.

    Args:
        specs: Projects to analyse. Defaults to :func:`discover_projects`.
        extra_specs: Third-party projects appended to the discovered set.
        scan_annotations: Harvest ``TYPE_CHECKING`` imports from the scan roots.
        root_class: Dotted path of the lineage root class.
    """
    graph = LineageGraph(root_class)
    projects = list(specs) if specs is not None else discover_projects(extra_specs)
    root = load_root_class(root_class)

    for spec in projects:
        graph.set_home_package(
            spec.label, spec.home_package
        )

    if scan_annotations:
        for spec in projects:
            _walk_typecheck_sources(spec, graph)

    for spec in projects:
        for scan_root in spec.scan_packages:
            module_failures: List[Tuple[str, str]] = []
            for module in _iter_modules(scan_root, module_failures):
                module_name = getattr(module, "__name__", "")
                for obj in vars(module).values():
                    if not inspect.isclass(obj):
                        continue
                    if getattr(obj, "__module__", None) != module_name:
                        continue
                    if obj is root or not issubclass(obj, root):
                        continue
                    node_id = make_id(spec.label, obj.__qualname__)
                    if node_id in graph:
                        continue
                    graph.register_class(obj, node_id)
                    bases = tuple(
                        b for b in obj.__bases__ if b is not root and issubclass(b, root)
                    )
                    mixins = tuple(
                        "{}.{}".format(b.__module__, b.__qualname__)
                        for b in obj.__bases__
                        if not issubclass(b, root)
                    )
                    graph.add(
                        LineageNode(
                            id=node_id,
                            project=spec.label,
                            qualname=obj.__qualname__,
                            module=obj.__module__,
                            family=family_of(obj.__module__),
                            is_abstract=bool(getattr(obj, "__abstractmethods__", ())),
                            format_method=_format_method_of(obj),
                            has_render_entry=_has_render_entry(obj),
                        )
                    )
                    graph.add_pending(node_id, bases, mixins)
            for name, reason in module_failures:
                graph.unimportable.append((spec.label, name, reason))

    graph.resolve()
    return graph
