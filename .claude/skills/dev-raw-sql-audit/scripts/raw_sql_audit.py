# .claude/skills/dev-raw-sql-audit/scripts/raw_sql_audit.py
"""Audit every reference to ``RawSQLExpression`` and ``RawSQLPredicate``.

Why this exists
---------------
``RawSQLExpression`` and ``RawSQLPredicate`` were introduced as a *temporary* shortcut
for validating an expression while the real typed expression did not exist yet. They
are not a sanctioned production construct. Both bypass the expression pipeline: the
SQL text is carried verbatim and handed to the driver, so nothing validates it,
nothing formats it, and nothing owns it.

That makes them dangerous in a way a normal defect is not. An expression that a
dialect formats, parameterises and rejects is a *checked* string; a raw SQL string is
only as safe as the code that built it. Wherever one of these classes appears in
``src/`` it is standing in for a construct that was never written, and it will keep
working long after the reason it was added has been forgotten.

The audit is deliberately **pure AST** -- it parses, imports nothing, and touches no
interpreter state -- so it runs under any Python, needs no virtualenv, and cannot be
fooled by a module that fails to import. Contrast ``dev-expression-lineage``, which
reflects over live classes and therefore needs the venv with every backend installed.

Modelling premises
------------------
1. **A reference is classified by its syntactic role, not by grep.** ``grep RawSQL``
   cannot tell a construction from a docstring; the difference between the two is
   the entire question, so every reference is resolved through the AST.
2. **Import binding is resolved.** The class is reachable as a bare name
   (``RawSQLExpression``), as an alias (``as Raw``), or through a module
   (``operators.RawSQLExpression``). All three are counted; none is guessed.
3. **``src/`` and ``tests/`` are not the same thing.** Constructing a raw expression
   in a test is the shortcut working as designed. Constructing one in ``src/`` is the
   debt this skill exists to surface. The area is part of the finding, so the report
   separates them instead of blending 24 production sites into 240 lines of noise.
4. **A construction whose SQL is computed at runtime is worse than one whose SQL is
   a literal.** ``RawSQLExpression(d, "*")`` is ugly but inert.
   ``RawSQLExpression(d, formatted_sql, all_params)`` is a SQL injection surface, and
   is ranked above the literal case rather than beside it.
5. **Imports that reference nothing are findings.** A dangling ``RawSQLExpression``
   import is the residue of a shortcut that was already removed.

Usage
-----
    python raw_sql_audit.py                       # core project + sibling backends
    python raw_sql_audit.py --repo /path/to/repo
    python raw_sql_audit.py --area src            # production only
    python raw_sql_audit.py --fail-on review      # tighten the gate in CI
    python raw_sql_audit.py --json                # machine-readable

Exit codes: 0 clean at the requested ``--fail-on`` level, 1 findings at or above it,
2 bad usage (unreadable project, parse error in a scanned file).
"""

from __future__ import annotations

import argparse
import ast
import json
import os
import sys
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

#: The two classes under audit. The class *names* are the contract; a project that
#: renames one of them silently drops it from the audit, so the names are asserted
#: against the definition site rather than discovered dynamically.
TARGETS: Tuple[str, ...] = ("RawSQLExpression", "RawSQLPredicate")

#: Severity ladder, weakest last. ``critical`` outranks ``violation`` because a
#: runtime-built SQL string is an injection surface, not merely unfinished design.
SEVERITIES: Tuple[str, ...] = ("info", "review", "violation", "critical")

SEVERITY_RANK: Dict[str, int] = {name: index for index, name in enumerate(SEVERITIES)}

#: Directories never walked. Virtualenvs and build trees ship their own copies of the
#: source, so walking them buries the real findings under thousands of files.
SKIP_DIRS: Set[str] = {
    "__pycache__",
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    "node_modules",
    "site-packages",
    "build",
    "dist",
    ".venv",
    "venv",
    ".eggs",
}

#: Directory prefixes of a workspace-relative virtualenv, e.g. ``.venv3.14-ubuntu26.04``.
SKIP_DIR_PREFIXES: Tuple[str, ...] = (".venv",)

#: Callables whose argument naming a class is a *type query*, not a construction.
#: ``isinstance(x, RawSQLExpression)`` asks a question; ``RawSQLExpression(d, s)``
#: builds a thing, and only the second one creates debt.
TYPECHECK_CALLS: Set[str] = {
    "isinstance",
    "issubclass",
    "type",
    "cast",
    "issubclass_safe",
    "is_subclass_of",
}

#: Roles a reference can play. ``kind`` is what the reference *is*;
#: severity is what that means for a given area.
KIND_CONSTRUCTION = "construction"
KIND_SUBCLASS = "subclass"
KIND_TYPECHECK = "typecheck"
KIND_ANNOTATION = "annotation"
KIND_UNUSED_IMPORT = "unused_import"
KIND_FORMATTER = "formatter"
KIND_DEFINITION = "definition"
KIND_MENTION = "mention"

#: Severity by (kind, area). Anything absent is ``info``, because an unclassified
#: reference should never be promoted to a blocking finding by accident.
SEVERITY_MATRIX: Dict[Tuple[str, str], str] = {
    (KIND_CONSTRUCTION, "src"): "violation",
    (KIND_SUBCLASS, "src"): "violation",
    (KIND_CONSTRUCTION, "tests"): "review",
    (KIND_SUBCLASS, "tests"): "review",
    # A type guard in production code is worth a look: it usually means the
    # surrounding code still has to cope with a raw node leaking into it.
    (KIND_TYPECHECK, "src"): "review",
    (KIND_TYPECHECK, "tests"): "info",
    # A dead import is residue of an already-removed shortcut.
    (KIND_UNUSED_IMPORT, "src"): "review",
    (KIND_UNUSED_IMPORT, "tests"): "info",
}

#: Kinds that are pure inventory: the class exists, the formatter renders it, a type
#: hint names it. None of these are debt, and all of them are collapsed out of the
#: text report so the construction sites are not buried under them.
INFORMATIVE: Set[str] = {
    KIND_ANNOTATION,
    KIND_FORMATTER,
    KIND_DEFINITION,
    KIND_MENTION,
}


# --------------------------------------------------------------------------- #
# Data model
# --------------------------------------------------------------------------- #


@dataclass
class Finding:
    """One classified reference."""

    project: str
    path: str
    line: int
    column: int
    kind: str
    symbol: str
    area: str
    severity: str = "info"
    #: True when the SQL text handed to the constructor is computed rather than a
    #: literal, which is the difference between ugly and injectable.
    dynamic_sql: bool = False
    snippet: str = ""

    @property
    def location(self) -> str:
        return "{}:{}:{}".format(self.path, self.line, self.column)

    def to_dict(self) -> Dict[str, object]:
        return {
            "project": self.project,
            "path": self.path,
            "line": self.line,
            "column": self.column,
            "kind": self.kind,
            "symbol": self.symbol,
            "area": self.area,
            "severity": self.severity,
            "dynamic_sql": self.dynamic_sql,
            "snippet": self.snippet,
        }


@dataclass
class ProjectReport:
    """Findings for one project, split by area."""

    project: str
    root: str
    findings: List[Finding] = field(default_factory=list)
    scanned_files: int = 0
    #: Symbols actually found defined in this project. A project that defines one of
    #: the targets is the owner; every other project is only a consumer.
    defines: Set[str] = field(default_factory=set)
    #: Lines whose text mentions a target class without referencing it. Counted so
    #: "109 mentions" is never mistaken for "109 uses".
    prose_mentions: int = 0
    errors: List[str] = field(default_factory=list)

    def by_severity(self) -> Dict[str, List[Finding]]:
        buckets: Dict[str, List[Finding]] = {name: [] for name in SEVERITIES}
        for finding in self.findings:
            buckets[finding.severity].append(finding)
        return buckets

    def counts(self) -> Dict[str, int]:
        counts = {name: 0 for name in SEVERITIES}
        for finding in self.findings:
            counts[finding.severity] += 1
        return counts

    def to_dict(self) -> Dict[str, object]:
        return {
            "project": self.project,
            "root": self.root,
            "scanned_files": self.scanned_files,
            "defines": sorted(self.defines),
            "prose_mentions": self.prose_mentions,
            "counts": self.counts(),
            "errors": self.errors,
            "findings": [finding.to_dict() for finding in self.findings],
        }


# --------------------------------------------------------------------------- #
# Static helpers
# --------------------------------------------------------------------------- #


def is_static_literal(node: ast.AST) -> bool:
    """Whether a node is a compile-time constant, so passing it embeds no runtime data."""
    if isinstance(node, ast.Constant):
        return True
    if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
        return all(is_static_literal(item) for item in node.elts)
    return False


def source_snippet(path: str, line: int) -> str:
    """The trimmed text of one source line, for report evidence."""
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            lines = handle.readlines()
    except OSError:
        return ""
    if 1 <= line <= len(lines):
        return lines[line - 1].strip()[:150]
    return ""


def iter_python_files(root: str, area: str) -> Iterable[str]:
    """Yield every ``.py`` file under ``root/area``, skipping vendored trees."""
    base = os.path.join(root, area)
    if not os.path.isdir(base):
        return
    for dirpath, dirnames, filenames in os.walk(base):
        pruned = []
        for name in dirnames:
            if name in SKIP_DIRS or name.startswith(SKIP_DIR_PREFIXES):
                continue
            pruned.append(name)
        dirnames[:] = pruned
        for filename in sorted(filenames):
            if filename.endswith(".py"):
                yield os.path.join(dirpath, filename)


# --------------------------------------------------------------------------- #
# AST classification
# --------------------------------------------------------------------------- #


class FileClassifier:
    """Classify every reference to a target symbol inside one module.

    The pass runs in three stages because none of them can be done alone:

    1. **Bindings.** Walk imports to learn which local names denote the target
       classes, including aliases. Without this, ``as Raw`` usage is invisible and
       the audit under-reports.
    2. **Positions.** Index every node that sits in a role which changes the meaning
       of a reference: an annotation, an ``__all__`` entry, a class base list, a
       call argument. Role wins over name.
    3. **References.** Walk once more and emit a finding for each reference, using
       the indexed position to decide what kind of reference it is.
    """

    def __init__(self, path: str, project: str, area: str, rel_path: str) -> None:
        self.path = path
        self.project = project
        self.area = area
        self.rel_path = rel_path
        self.findings: List[Finding] = []

        with open(path, encoding="utf-8", errors="replace") as handle:
            self.source = handle.read()
        self.tree = ast.parse(self.source, filename=path)

        #: local name -> target class name
        self.bindings: Dict[str, str] = {}
        #: local names bound to an expression module, for ``operators.RawSQL`` access
        self.module_aliases: Set[str] = set()
        #: ids of nodes used as annotations (whole annotation subtrees)
        self.annotation_nodes: Set[int] = set()
        #: ids of nodes inside a class base list
        self.base_nodes: Set[int] = set()
        #: ids of nodes passed to ``isinstance`` / ``issubclass`` / ``cast``
        self.typecheck_args: Set[int] = set()
        #: id(call) -> the call, so a name used as the callee can be resolved to
        #: its arguments. Needed because the reference node is the callee itself,
        #: not the ``Call`` that contains it.
        self.calls_by_func: Dict[int, ast.Call] = {}
        #: (line, symbol) pairs for prose mentions, counted but not emitted
        self.prose_lines: Set[Tuple[int, str]] = set()
        #: names re-exported through ``__all__``
        self.exported: Set[str] = set()

    # -- stage 1: bindings -------------------------------------------------- #

    def collect_bindings(self) -> None:
        for node in ast.walk(self.tree):
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    if alias.name in TARGETS:
                        self.bindings[alias.asname or alias.name] = alias.name
                # ``from ..expression import operators`` enables ``operators.RawSQL``
                module = node.module or ""
                if module.endswith("expression") or module.endswith("expression.operators"):
                    for alias in node.names:
                        if alias.name in ("operators", "expression", "ops"):
                            self.module_aliases.add(alias.asname or alias.name)
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.endswith("expression.operators") or alias.name.endswith(
                        ".expression"
                    ):
                        self.module_aliases.add(alias.asname or alias.name.split(".")[0])

    # -- stage 2: positions -------------------------------------------------- #

    def _mark_tree(self, node: Optional[ast.AST], bucket: Set[int]) -> None:
        """Mark every node in the subtree rooted at ``node``.

        Subtrees rather than single nodes, because an annotation can be nested
        (``Optional[RawSQLExpression]``, ``list[RawSQLPredicate]``) and only the root
        is a direct field of the enclosing definition.
        """
        if node is None:
            return
        for child in ast.walk(node):
            bucket.add(id(child))

    def _index(self, node: ast.AST) -> None:
        """Index the fields of ``node`` that change the meaning of a reference.

        Only the *specific* fields are marked. Treating every child of a
        ``FunctionDef`` or ``ClassDef`` as an annotation or a base would shadow each
        real call site with a false ``annotation``, which is how a check like this
        silently degrades into reporting nothing.
        """
        if isinstance(node, ast.arg):
            self._mark_tree(node.annotation, self.annotation_nodes)
        elif isinstance(node, ast.AnnAssign):
            self._mark_tree(node.annotation, self.annotation_nodes)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            self._mark_tree(node.returns, self.annotation_nodes)
        elif isinstance(node, ast.ClassDef):
            for base in node.bases:
                self._mark_tree(base, self.base_nodes)
        elif isinstance(node, ast.Call):
            self.calls_by_func[id(node.func)] = node
            func = node.func
            if isinstance(func, ast.Name) and func.id in TYPECHECK_CALLS:
                for argument in node.args:
                    self._mark_tree(argument, self.typecheck_args)
        elif isinstance(node, ast.Assign):
            if any(
                isinstance(target, ast.Name) and target.id == "__all__"
                for target in node.targets
            ):
                self._collect_all_strings(node.value)

    def _collect_all_strings(self, node: Optional[ast.AST]) -> None:
        """Record names exported through ``__all__``.

        A package's ``__init__.py`` imports a name purely to re-export it, and the
        re-export is expressed as a *string* in ``__all__`` rather than as a code
        reference. Treating that as an unused import reports every healthy public
        API as dead code, which is how a check like this loses its credibility.
        """
        if node is None:
            return
        for child in ast.walk(node):
            if isinstance(child, ast.Constant) and isinstance(child.value, str):
                self.exported.add(child.value)

    def collect_positions(self) -> None:
        for node in ast.walk(self.tree):
            self._index(node)

    # -- stage 3: references ------------------------------------------------- #

    def _emit(
        self,
        kind: str,
        symbol: str,
        node: ast.AST,
        *,
        dynamic_sql: bool = False,
    ) -> None:
        severity = SEVERITY_MATRIX.get((kind, self.area), "info")
        if kind in INFORMATIVE:
            severity = "info"
        if dynamic_sql and self.area == "src":
            severity = "critical"
        self.findings.append(
            Finding(
                project=self.project,
                path=self.rel_path,
                line=getattr(node, "lineno", 0),
                column=getattr(node, "col_offset", 0) + 1,
                kind=kind,
                symbol=symbol,
                area=self.area,
                severity=severity,
                dynamic_sql=dynamic_sql,
                snippet=source_snippet(self.path, getattr(node, "lineno", 0)),
            )
        )

    def _is_typecheck_arg(self, node: ast.AST) -> bool:
        return id(node) in self.typecheck_args

    def _construction_is_dynamic(self, call: ast.Call) -> bool:
        """Whether any argument past the dialect is computed at runtime.

        ``args[0]`` is the dialect by the constructor signature. Anything after it is
        either the SQL text or its parameters, and a non-literal in either position
        means the string being embedded was assembled from live values.
        """
        for argument in call.args[1:]:
            if not is_static_literal(argument):
                return True
        for keyword in call.keywords:
            if keyword.arg is None:  # ``**kwargs``
                return True
            if not is_static_literal(keyword.value):
                return True
        return False

    def collect_references(self) -> None:
        used: Set[str] = set()

        for node in ast.walk(self.tree):
            if isinstance(node, ast.ClassDef) and node.name in TARGETS:
                self._emit(KIND_DEFINITION, node.name, node)
                continue
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == (
                "format_raw_sql"
            ):
                self._emit(KIND_FORMATTER, TARGETS[0], node)
                continue

            symbol: Optional[str] = None
            local: Optional[str] = None
            if isinstance(node, ast.Name) and node.id in self.bindings:
                local = node.id
                symbol = self.bindings[node.id]
            elif (
                isinstance(node, ast.Attribute)
                and node.attr in TARGETS
                and isinstance(node.value, ast.Name)
                and node.value.id in self.module_aliases
            ):
                local = node.value.id
                symbol = node.attr
            elif id(node) in self.base_nodes and isinstance(node, ast.Name) and node.id in TARGETS:
                # A base list naming a target the module never imported. This is a
                # ``NameError`` waiting to happen, and it is unambiguously an attempt
                # to subclass the class, so match it on the bare name rather than
                # letting the missing import hide it.
                symbol = node.id
            if symbol is None:
                continue

            if local is not None:
                used.add(local)
                if symbol in self.exported:
                    used.add(local)

            if id(node) in self.annotation_nodes:
                self._emit(KIND_ANNOTATION, symbol, node)
            elif id(node) in self.base_nodes:
                self._emit(KIND_SUBCLASS, symbol, node)
            elif self._is_typecheck_arg(node):
                self._emit(KIND_TYPECHECK, symbol, node)
            elif id(node) in self.calls_by_func:
                call = self.calls_by_func[id(node)]
                self._emit(
                    KIND_CONSTRUCTION,
                    symbol,
                    node,
                    dynamic_sql=self._construction_is_dynamic(call),
                )
            else:
                # A bare name with no recognised role. Either a local variable that
                # happens to share the name, or a pass-through such as
                # ``return some_list_of[RawSQLExpression]``. Neither constructs
                # anything, so neither is debt.
                self._emit(KIND_MENTION, symbol, node)

        # Imports that never got used are residue, not inventory.
        for local, symbol in self.bindings.items():
            if local not in used:
                self._emit(KIND_UNUSED_IMPORT, symbol, self._import_site(local))

    def _import_site(self, local: str) -> ast.AST:
        """Locate the import statement that bound ``local``, for reporting."""
        for node in ast.walk(self.tree):
            if isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    if (alias.asname or alias.name) == local and alias.name in TARGETS:
                        return node
        return ast.Module(body=[], type_ignores=[])

    # -- prose mentions ----------------------------------------------------- #

    def collect_string_mentions(self) -> None:
        """Record textual mentions so prose about the classes is never counted as
        use of them. These are ``info`` and collapsed in the text report.

        Docstrings and error messages name these classes constantly, which is
        legitimate and even desirable -- the guidance against them has to be
        readable at the call site. Emitting one finding per sentence would bury the
        construction sites that matter, so the count is reported and the detail is
        not.
        """
        for node in ast.walk(self.tree):
            if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
                continue
            for target in TARGETS:
                if target in node.value:
                    self.prose_lines.add((node.lineno, target))
                    break

    # -- driver -------------------------------------------------------------- #

    def run(self) -> Tuple[List[Finding], Set[str], int]:
        self.collect_bindings()
        self.collect_positions()
        self.collect_references()
        self.collect_string_mentions()
        defines = {
            node.name
            for node in ast.walk(self.tree)
            if isinstance(node, ast.ClassDef) and node.name in TARGETS
        }
        return self.findings, defines, len(self.prose_lines)


# --------------------------------------------------------------------------- #
# Project scanning
# --------------------------------------------------------------------------- #


def scan_project(root: str, project: str, areas: Sequence[str]) -> ProjectReport:
    report = ProjectReport(project=project, root=root)
    for area in areas:
        for path in iter_python_files(root, area):
            report.scanned_files += 1
            rel_path = os.path.relpath(path, root)
            try:
                findings, defines, prose = FileClassifier(path, project, area, rel_path).run()
            except (SyntaxError, ValueError, UnicodeDecodeError) as exc:
                report.errors.append("{}: {}".format(rel_path, exc))
                continue
            report.findings.extend(findings)
            report.defines |= defines
            report.prose_mentions += prose
    report.findings.sort(key=lambda f: (f.area, f.path, f.line))
    return report


def discover_projects(repo: str) -> List[Tuple[str, str]]:
    """Return ``(project, root)`` for the repo and every sibling backend.

    Sibling discovery is what makes this useful: a raw expression introduced in the
    core propagates into backend packages, and a check scoped to one repository
    would report clean while the debt spreads.
    """
    repo = os.path.abspath(repo)
    projects: List[Tuple[str, str]] = [(os.path.basename(repo), repo)]
    parent = os.path.dirname(repo)
    try:
        entries = sorted(os.listdir(parent))
    except OSError:
        return projects
    for entry in entries:
        candidate = os.path.join(parent, entry)
        if not os.path.isdir(candidate) or candidate == repo:
            continue
        if not entry.startswith("python-activerecord"):
            continue
        if not os.path.isdir(os.path.join(candidate, "src")) and not os.path.isdir(
            os.path.join(candidate, "tests")
        ):
            continue
        projects.append((entry, candidate))
    return projects


# --------------------------------------------------------------------------- #
# Reporting
# --------------------------------------------------------------------------- #


def render_text(reports: Sequence[ProjectReport], fail_on: str) -> str:
    out: List[str] = []
    threshold = SEVERITY_RANK[fail_on]

    out.append("RawSQL expression audit")
    out.append("=" * 72)

    total_files = sum(report.scanned_files for report in reports)
    out.append("scanned {} files across {} projects".format(total_files, len(reports)))
    out.append("gate: --fail-on {}".format(fail_on))
    out.append("")

    for report in reports:
        counts = report.counts()
        blocking = sum(
            count for name, count in counts.items() if SEVERITY_RANK[name] >= threshold
        )
        header = "{:<38} {:>4} files".format(report.project, report.scanned_files)
        if report.defines:
            header += "   [defines {}]".format(", ".join(sorted(report.defines)))
        out.append(header)
        out.append("-" * 72)
        if blocking == 0:
            out.append("  no findings at or above {}".format(fail_on))
        else:
            out.append(
                "  {} critical, {} violation, {} review, {} info".format(
                    counts["critical"],
                    counts["violation"],
                    counts["review"],
                    counts["info"],
                )
            )
            for severity in reversed(SEVERITIES):
                if SEVERITY_RANK[severity] < threshold:
                    continue
                for finding in report.by_severity()[severity]:
                    tag = " [dynamic-sql]" if finding.dynamic_sql else ""
                    out.append(
                        "  {:<9} {}:{} {}{}".format(
                            severity, finding.path, finding.line, finding.symbol, tag
                        )
                    )
                    if finding.snippet:
                        out.append("            | {}".format(finding.snippet))
        inventory = [finding for finding in report.findings if finding.kind in INFORMATIVE]
        if inventory:
            kinds: Dict[str, int] = {}
            for finding in inventory:
                kinds[finding.kind] = kinds.get(finding.kind, 0) + 1
            summary = ", ".join("{}={}".format(kind, kinds[kind]) for kind in sorted(kinds))
            out.append("  inventory: {}".format(summary))
        if report.prose_mentions:
            out.append(
                "  prose mentions (not uses): {}".format(report.prose_mentions)
            )
        for error in report.errors:
            out.append("  ERROR {}".format(error))
        out.append("")

    total = sum(sum(report.counts().values()) for report in reports)
    src_constructions = sum(
        1
        for report in reports
        for finding in report.findings
        if finding.kind == KIND_CONSTRUCTION and finding.area == "src"
    )
    out.append("total references: {}".format(total))
    out.append("production constructions: {}".format(src_constructions))
    out.append(
        "A production construction means the real typed expression was never written."
    )
    return "\n".join(out)


def verdict(reports: Sequence[ProjectReport], fail_on: str) -> int:
    threshold = SEVERITY_RANK[fail_on]
    for report in reports:
        for finding in report.findings:
            if SEVERITY_RANK[finding.severity] >= threshold:
                return 1
    return 0


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Audit RawSQLExpression / RawSQLPredicate usage across the workspace.",
    )
    parser.add_argument(
        "--repo",
        default=".",
        help="repository to scan; sibling python-activerecord* projects are included",
    )
    parser.add_argument(
        "--project",
        action="append",
        default=None,
        help="limit to a named project (repeatable)",
    )
    parser.add_argument(
        "--area",
        action="append",
        choices=("src", "tests"),
        default=None,
        help="restrict to an area (default: both)",
    )
    parser.add_argument(
        "--fail-on",
        choices=SEVERITIES,
        default="violation",
        help="lowest severity that fails the run (default: violation)",
    )
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON")
    args = parser.parse_args(argv)

    if not os.path.isdir(args.repo):
        print("not a directory: {}".format(args.repo), file=sys.stderr)
        return 2

    areas = tuple(args.area) if args.area else ("src", "tests")
    discovered = discover_projects(args.repo)
    if args.project:
        wanted = set(args.project)
        discovered = [item for item in discovered if item[0] in wanted]
        missing = wanted - {name for name, _ in discovered}
        if missing:
            print("unknown project(s): {}".format(", ".join(sorted(missing))), file=sys.stderr)
            return 2

    reports = [scan_project(root, name, areas) for name, root in discovered]

    if args.json:
        print(
            json.dumps(
                {
                    "gate": args.fail_on,
                    "projects": [report.to_dict() for report in reports],
                    "verdict": "fail" if verdict(reports, args.fail_on) else "pass",
                },
                indent=2,
            )
        )
    else:
        print(render_text(reports, args.fail_on))

    return verdict(reports, args.fail_on)


if __name__ == "__main__":
    raise SystemExit(main())