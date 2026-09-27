# .claude/skills/dev-expression-lineage/scripts/expression_lineage_mermaid.py
"""Render the expression lineage graph as Mermaid diagrams, plus a text report.

Why these diagram types
-----------------------
Two shapes are emitted, because neither alone covers the job:

``flowchart`` (default)
    ``flowchart LR`` with one ``subgraph`` per project. Subgraphs are what make
    the core-to-backend layering legible, ``id["label"]`` syntax is stable across
    every Mermaid renderer, and it survives the hundreds of nodes a full backend
    scan produces. Inheritance is drawn parent to child with ``-->`` so that
    reading left to right follows "generic base becomes backend specialisation".

``classDiagram`` (opt-in)
    Semantically the correct diagram for inheritance, and nicer to read for a
    focused family of a few dozen classes. It degrades on very large graphs, so
    it is offered explicitly rather than by default.

Usage
-----
    python expression_lineage_mermaid.py --scope family:ddl_domain --style auto
    python expression_lineage_mermaid.py --scope backend:postgres
    python expression_lineage_mermaid.py --scope consumers --min-consumers 2
    python expression_lineage_mermaid.py --scope violations
    python expression_lineage_mermaid.py --report
    python expression_lineage_mermaid.py --scope backend:mysql --out /tmp/x.mmd

Every scope also prints the provenance of the run, so a diagram pasted into a
document can be traced back to the revision it was measured on.
"""

from __future__ import annotations

import argparse
import os
import sys
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from expression_lineage import (  # noqa: E402
    _importable,
    LineageGraph,
    LineageNode,
    NodeId,
    ProjectSpec,
    build_graph,
    discover_projects,
    provenance,
)

#: Above this node count ``classDiagram`` becomes unreadable, so ``flowchart`` wins.
AUTO_STYLE_THRESHOLD = 40

PROJECT_ORDER_HINT = [
    "core",
    "sqlite",
    "postgres",
    "mysql",
    "mariadb",
    "sqlserver",
    "oracle",
    "snowflake",
    "clickhouse",
    "firebird",
]

#: Node classes are styled by role rather than by project, so the eye lands on
#: the generic/backend split first.
STYLE_CORE = "fill:#e8f0fe,stroke:#4a6fa5,stroke-width:1px"
STYLE_BACKEND = "fill:#fdf3e3,stroke:#b07d2b,stroke-width:1px"
STYLE_ABSTRACT = "fill:#f0f0f0,stroke:#8a8a8a,stroke-width:1px,stroke-dasharray:3 3"
STYLE_EXTERNAL = "fill:#ffffff,stroke:#bbbbbb,stroke-width:1px,stroke-dasharray:2 2"
STYLE_AGGREGATE = "fill:#eef7ee,stroke:#4f8a4f,stroke-width:1px"


def _escape_label(text: str) -> str:
    """Make a string safe inside a Mermaid quoted label."""
    text = text.replace('"', "#quot;").replace("`", "'")
    return text.replace("\r", " ").replace("\n", " ")


class _Ids:
    """Deterministic Mermaid-safe identifiers for node ids.

    Class names collide across projects, so the project label is part of the id.
    A monotonic counter keeps ids unique and stable for a given graph.
    """

    def __init__(self) -> None:
        self._by_node: Dict[NodeId, str] = {}
        self._counter = 0

    def of(self, node: LineageNode) -> str:
        if node.id not in self._by_node:
            self._counter += 1
            self._by_node[node.id] = "n{}".format(self._counter)
        return self._by_node[node.id]

    def subgraph(self, label: str) -> str:
        return "pg_{}".format(label.replace("-", "_"))


def _ordered_projects(present: Sequence[str]) -> List[str]:
    """Sort projects so the core comes first and backends follow a stable order."""
    known = [p for p in PROJECT_ORDER_HINT if p in present]
    extra = sorted(p for p in present if p not in PROJECT_ORDER_HINT)
    return known + extra


def _label_of(node: LineageNode) -> str:
    text = node.name
    if node.format_method:
        text = "{}\n{}".format(text, node.format_method)
    return _escape_label(text)


def _style_of(node: LineageNode) -> str:
    if node.is_external:
        return STYLE_EXTERNAL
    if node.is_abstract:
        return STYLE_ABSTRACT
    return STYLE_CORE if node.is_core else STYLE_BACKEND


# ── Selection ────────────────────────────────────────────────────────────────

def _select(
    graph: LineageGraph, scope: str, min_consumers: int, limit: int
) -> Tuple[List[LineageNode], str]:
    """Resolve a scope string into a node selection plus a caption.

    Returns the selected nodes and a short human-readable caption describing what
    the selection means, so the diagram is self-describing.
    """
    kind, _, argument = scope.partition(":")

    if kind == "family":
        nodes = [n for n in graph.select(family=argument)]
        nodes += [
            graph.node(a)
            for n in nodes
            for a in sorted(graph.ancestors(n.id))
            if graph.node(a).id not in {x.id for x in nodes}
        ]
        nodes = _dedupe(nodes)
        return nodes, "family {} (plus ancestors)".format(argument)

    if kind in ("backend", "project"):
        nodes = [n for n in graph.select(project=argument)]
        nodes += [
            graph.node(a)
            for n in nodes
            for a in sorted(graph.ancestors(n.id))
            if graph.node(a).id not in {x.id for x in nodes}
        ]
        return _dedupe(nodes), "backend {} (plus core ancestors)".format(argument)

    if kind == "consumers":
        rows = [r for r in graph.consumer_counts() if r[1] >= min_consumers]
        rows = rows[:limit] if limit else rows
        return (
            [graph.node(node_id) for node_id, _, _ in rows],
            "core classes with at least {} consuming backend(s)".format(min_consumers),
        )

    if kind == "roots":
        return graph.roots("core"), "core pedigree roots"

    if kind == "mixins":
        return _dedupe(graph.roots("core")), "core pedigree roots (mixins excluded)"

    if kind == "violations":
        nodes = [graph.node(c) for c, _ in graph.violations()]
        nodes += [graph.node(p) for _, p in graph.violations()]
        return _dedupe(nodes), "cross-backend inheritance (iron-rule violations)"

    raise SystemExit("unknown scope: {}".format(scope))


def _dedupe(nodes: Sequence[LineageNode]) -> List[LineageNode]:
    seen: Set[NodeId] = set()
    out: List[LineageNode] = []
    for node in nodes:
        if node.id in seen:
            continue
        seen.add(node.id)
        out.append(node)
    return out


# ── Renderers ────────────────────────────────────────────────────────────────

def render_flowchart(
    graph: LineageGraph, nodes: Sequence[LineageNode], caption: str
) -> str:
    """Render as ``flowchart LR`` with one subgraph per project."""
    ids = _Ids()
    for node in nodes:
        ids.of(node)

    lines: List[str] = ["flowchart LR"]
    lines.append("    %% {}".format(_escape_label(caption)))

    for project in _ordered_projects(sorted({n.project for n in nodes})):
        members = [n for n in nodes if n.project == project]
        if not members:
            continue
        lines.append('    subgraph {}["{}"]'.format(ids.subgraph(project), project))
        for node in members:
            lines.append(
                '        {}["{}"]'.format(ids.of(node), _label_of(node))
            )
        lines.append("    end")

    for node in nodes:
        for base_id in node.bases:
            if base_id not in ids._by_node:
                continue
            lines.append("    {} --> {}".format(ids.of(graph.node(base_id)), ids.of(node)))

    for node in nodes:
        lines.append("    classDef node{} fill:{};".format(node.project, _style_of(node)))
        lines.append("    class {} node{};".format(ids.of(node), node.project))
    return "\n".join(lines)


def render_classdiagram(
    graph: LineageGraph, nodes: Sequence[LineageNode], caption: str
) -> str:
    """Render as a Mermaid ``classDiagram`` with per-project namespaces."""
    ids = _Ids()
    for node in nodes:
        ids.of(node)

    lines: List[str] = ["classDiagram"]
    lines.append("    %% {}".format(_escape_label(caption)))
    lines.append("    direction LR")

    for project in _ordered_projects(sorted({n.project for n in nodes})):
        members = [n for n in nodes if n.project == project]
        if not members:
            continue
        lines.append("    namespace {} {{".format(project))
        for node in members:
            shape = " <<abstract>>" if node.is_abstract else ""
            lines.append('        class {}["{}"]{}'.format(ids.of(node), _label_of(node), shape))
        lines.append("    }")

    for node in nodes:
        for base_id in node.bases:
            if base_id in ids._by_node:
                lines.append("    {} <|-- {}".format(ids.of(graph.node(base_id)), ids.of(node)))
    return "\n".join(lines)


def render_consumers(
    graph: LineageGraph, min_consumers: int, limit: int
) -> str:
    """Render which backends consume each core class.

    This is the placement view: a core class with many inbound backend edges is
    doing the generic layer's job, while one with a single consumer is a candidate
    to move down into that backend.
    """
    rows = [r for r in graph.consumer_counts() if r[1] >= min_consumers]
    if limit:
        rows = rows[:limit]

    lines: List[str] = ["flowchart LR"]
    lines.append(
        "    %% core class -> consuming backend(s); thin fan-in means a candidate for moving down"
    )
    projects = _ordered_projects(
        sorted({p for _, _, consumers in rows for p in consumers})
    )
    project_ids = {p: "b_{}".format(p) for p in projects}

    for project in projects:
        lines.append('    subgraph {}["{}"]'.format(project_ids[project], project))
        lines.append('        hub_{0}["(consumers)"]'.format(project))
        lines.append("    end")

    for index, (node_id, _count, consumers) in enumerate(rows, start=1):
        node = graph.node(node_id)
        node_ref = "c{}".format(index)
        lines.append('    {}["{}"]'.format(node_ref, _escape_label(node.name)))
        lines.append("    classDef core fill:{};".format(STYLE_CORE))
        lines.append("    class {} core;".format(node_ref))
        for project in sorted(consumers):
            lines.append("    {} --> hub_{}".format(node_ref, project))
    return "\n".join(lines)


# ── Report ───────────────────────────────────────────────────────────────────

def render_report(graph: LineageGraph, prov: Dict[str, Any]) -> str:
    """Human-readable summary: the numbers that matter for review decisions."""
    stats = graph.stats()
    out: List[str] = []
    out.append("Expression lineage report")
    out.append("=" * 60)
    out.append(
        "root class    : {}".format(stats["root_class"].rsplit(".", 1)[-1])
    )
    out.append(
        "revision      : {} ({})".format(
            prov["core_revision"][:12], prov["core_branch"]
        )
    )
    out.append("generated     : {}".format(prov["generated_at"]))
    out.append("projects      : {}".format(", ".join(sorted(stats["by_project"]))))
    out.append(
        "nodes/edges   : {} / {}   (max depth {})".format(
            stats["nodes"], stats["edges"], stats["max_depth"]
        )
    )
    out.append("out-of-range  : {} external base class(es)".format(stats["external_nodes"]))
    out.append(
        "iron rule     : {} cross-backend inheritance edge(s)".format(
            stats["cross_backend_violations"]
        )
    )
    out.append(
        "mixins        : {} non-expression base(s) kept out of the DAG".format(
            stats["mixins"]
        )
    )
    out.append(
        "placement     : {} misplaced, {} in a recognised secondary home".format(
            stats["misplaced"], stats["secondary_home"]
        )
    )
    out.append(
        "annotations   : {} TYPE_CHECKING import(s) scanned".format(
            len(graph.typecheck_imports)
        )
    )
    out.append(
        "integrity     : {} unparseable file(s), {} unimportable module(s)".format(
            stats["parse_failures"], stats["unimportable"]
        )
    )
    if graph.unimportable:
        out.append("")
        out.append("Modules that could not be imported")
        out.append("(these projects are UNDER-REPORTED; fix before trusting a clean run)")
        for project, module, reason in graph.unimportable:
            out.append("  [{}] {} -> {}".format(project, module, reason))
    if graph.parse_failures:
        out.append("")
        out.append("Unparseable files")
        for _path, message in graph.parse_failures:
            out.append("  {}".format(message))
    out.append("")

    out.append("Nodes per project")
    for project, count in stats["by_project"].items():
        out.append("  {:<14} {}".format(project, count))
    out.append("")

    out.append("Top families")
    for family, count in list(stats["by_family"].items())[:10]:
        out.append("  {:<24} {}".format(family, count))
    out.append("")

    violations = graph.violations()
    out.append("Cross-backend inheritance (iron-rule violations)")
    if not violations:
        out.append("  none - backends only derive from the core")
    for child, parent in violations:
        out.append("  !! {} derives from {}".format(child, parent))
    out.append("")

    out.append("Mixins kept out of the DAG (not BaseExpression subclasses)")
    for name in graph.mixin_names():
        out.append("  {}".format(name))
    out.append("")

    secondary = graph.secondary_home_nodes()
    out.append("Expression classes in a recognised secondary home")
    out.append("(e.g. impl.<name>.show for introspection, impl.<name>.types)")
    if not secondary:
        out.append("  none")
    else:
        by_project: Dict[str, int] = {}
        for node_id in secondary:
            project = graph.node(node_id).project
            by_project[project] = by_project.get(project, 0) + 1
        for project, count in sorted(by_project.items(), key=lambda kv: -kv[1]):
            out.append("  {:<14} {}".format(project, count))
    out.append("")

    misplaced = graph.misplaced()
    out.append("Expression classes outside every accepted home (defects)")
    if not misplaced:
        out.append("  none")
    else:
        by_project = {}
        for node_id in misplaced:
            project = graph.node(node_id).project
            by_project[project] = by_project.get(project, 0) + 1
        for project, count in sorted(by_project.items(), key=lambda kv: -kv[1]):
            out.append("  !! {:<14} {}".format(project, count))
    out.append("")

    dangling = graph.dangling_typecheck_refs()
    out.append("Dangling TYPE_CHECKING imports")
    if not dangling:
        out.append("  none")
    for ref in dangling:
        out.append("  {}".format(ref.describe()))
    out.append("")

    out.append("Core classes with the fewest consuming backends")
    out.append("(candidates to inspect: should this stay generic?)")
    sparse = [r for r in graph.consumer_counts() if r[1] <= 1]
    for node_id, count, consumers in sparse[:20]:
        out.append(
            "  {:<3} {:<52} {}".format(
                count,
                graph.node(node_id).name,
                ",".join(sorted(consumers)) if consumers else "(none)",
            )
        )
    if len(sparse) > 20:
        out.append("  ... and {} more".format(len(sparse) - 20))
    return "\n".join(out)


# ── CLI ──────────────────────────────────────────────────────────────────────

def _parse_extra(values: Sequence[str]) -> List[ProjectSpec]:
    """Parse ``label=package[:home_package]`` third-party extras."""
    specs: List[ProjectSpec] = []
    for raw in values or ():
        label, sep, rest = raw.partition("=")
        if not sep or not rest:
            raise SystemExit(
                "--extra expects label=package[:home_package], got: " + raw
            )
        scan_package, _, home = rest.partition(":")
        specs.append(ProjectSpec.custom(label, scan_package, home or None))
    return specs


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Render the expression lineage graph as Mermaid."
    )
    parser.add_argument(
        "--scope",
        default="roots",
        help=(
            "family:<name> | backend:<name> | consumers | roots | mixins | "
            "violations (default: roots)"
        ),
    )
    parser.add_argument(
        "--style",
        default="auto",
        choices=("auto", "flowchart", "class"),
        help="Mermaid diagram type; auto picks flowchart above "
        "{} nodes".format(AUTO_STYLE_THRESHOLD),
    )
    parser.add_argument("--out", help="write Mermaid to this file instead of stdout")
    parser.add_argument("--report", action="store_true", help="print the text report only")
    parser.add_argument(
        "--list-families",
        action="store_true",
        help="list family labels with counts, for use with --scope family:<name>",
    )
    parser.add_argument("--min-consumers", type=int, default=1)
    parser.add_argument("--limit", type=int, default=0, help="cap rows for consumers scope")
    parser.add_argument(
        "--extra",
        action="append",
        default=[],
        metavar="LABEL=PKG[:HOME]",
        help="analyse a third-party namespace alongside the in-tree backends",
    )
    parser.add_argument(
        "--save-graph",
        help="also write the raw lineage graph as JSON for diffing across runs",
    )
    args = parser.parse_args(argv)

    specs = discover_projects(extra=_parse_extra(args.extra))
    for spec in specs:
        if not spec.in_tree:
            missing = [p for p in spec.scan_packages if not _importable(p)]
            for package in missing:
                print(
                    "warning: third-party package {!r} is not importable in this "
                    "interpreter; it contributes no nodes".format(package),
                    file=sys.stderr,
                )
    graph = build_graph(specs=specs)

    if args.save_graph:
        graph.save(args.save_graph)
        print("wrote {}".format(args.save_graph))

    if args.list_families:
        stats = graph.stats()
        width = max((len(f) for f in stats["by_family"]), default=10)
        for family, count in stats["by_family"].items():
            print("  {:<{w}} {}".format(family, count, w=width))
        return 0

    if args.report:
        print(render_report(graph, provenance()))
        return 0

    if args.scope.startswith("consumers"):
        text = render_consumers(graph, args.min_consumers, args.limit)
    elif args.scope == "violations":
        pairs = graph.violations()
        if not pairs:
            print(
                "no cross-backend inheritance: every backend derives only from the core"
            )
            return 0
        nodes, caption = _select(graph, args.scope, args.min_consumers, args.limit)
        style = args.style if args.style != "auto" else "flowchart"
        text = (
            render_classdiagram(graph, nodes, caption)
            if style == "class"
            else render_flowchart(graph, nodes, caption)
        )
    else:
        nodes, caption = _select(graph, args.scope, args.min_consumers, args.limit)
        if not nodes:
            print(
                "scope {!r} selected no nodes; try --list-families".format(args.scope)
            )
            return 1
        style = args.style
        if style == "auto":
            style = "class" if len(nodes) <= AUTO_STYLE_THRESHOLD else "flowchart"
        text = (
            render_classdiagram(graph, nodes, caption)
            if style == "class"
            else render_flowchart(graph, nodes, caption)
        )

    if args.out:
        with open(args.out, "w", encoding="utf-8") as handle:
            handle.write(text + "\n")
        print("wrote {}".format(args.out))
    else:
        print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
