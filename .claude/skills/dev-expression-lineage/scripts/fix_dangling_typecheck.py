# .claude/skills/dev-expression-lineage/scripts/fix_dangling_typecheck.py
"""Repair dangling ``if TYPE_CHECKING:`` imports reported by the lineage model.

A dangling reference is an annotation-only import whose target module does not
expose the attribute. These are inert at runtime because ``TYPE_CHECKING`` is never
executed, but they break mypy, IDE resolution and every static tool, and they rot
silently.

Repair strategy
---------------
For each dangling import the fixer keeps the *target module* the author intended and
only corrects the number of leading dots, because the mistake is almost always a
mis-counted relative level:

    from .dialect import MySQLDialect        # in impl/mysql/functions/  -> wrong
    from ..dialect import MySQLDialect       # impl/mysql/dialect       -> right

The correct level is derived, not guessed: the fixer walks candidate levels and keeps
the first whose resolved module both imports cleanly and exposes the attribute. If no
level works, the import is left untouched and reported, because in that case the
*module* is wrong rather than the level and guessing would silently repoint a symbol.

Usage
-----
    python fix_dangling_typecheck.py --list
    python fix_dangling_typecheck.py --apply
    python fix_dangling_typecheck.py --apply --repo ../python-activerecord-mysql

``--list`` is the default and changes nothing. ``--apply`` rewrites files in place;
every rewrite is re-verified afterwards by re-running the dangling check.
"""

from __future__ import annotations

import argparse
import importlib
import os
import sys
from typing import List, Optional, Sequence, Tuple

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from expression_lineage import (  # noqa: E402
    TypecheckImport,
    _resolves,
    build_graph,
    discover_projects,
)

#: Never rewrite inside these; they are generated or vendored.
SKIP_PATH_PARTS = ("__pycache__", "examples", "tests", "migrations")

#: Cases where the dot count is right but the *module* or the *name* is wrong, so no
#: level can rescue them. Each entry was confirmed against the definition site.
#:
#: Keyed by ``(importing module suffix, imported name)`` so the table stays readable.
#: The value is ``(replacement "from ... import" prefix, new name or None)``: a few
#: cases also renamed the symbol, so the name has to travel with the module.
#:
#: The corrections fall into three groups:
#:   - the symbol moved package (``transaction`` -> ``expression.transaction``);
#:   - the import needs a deeper tail than the author wrote
#:     (``async_backend`` -> ``backend.async_backend``, and
#:     ``expression.partition`` -> ``expression.partition_lifecycle``);
#:   - the name itself was renamed. The last entry of this kind
#:     (``WindowFunctionCallExpression`` -> ``WindowFunctionCall``) is gone: the
#:     node was unified into ``FunctionCall`` and Firebird's stale importer was
#:     deleted with it.
#:
#: One case needed a **split** rather than a redirect and therefore has no entry
#: here: ``impl.mysql.mixins.partition`` imported 25 names from
#: ``expression.partition`` together with 5 ``*Helper`` names that actually live in
#: ``expression.partition_lifecycle``. Redirecting the whole statement, as this
#: table would, silently breaks the 25 names that were already correct. The file
#: now carries two separate import statements, one per defining module.
MANUAL_OVERRIDES = {
    ("impl.sqlite.expression.predicates", "SQLQueryAndParams"):     (
        "from ....expression.bases import",
        None,
    ),
    ("impl.sqlite.introspection.status_introspector", "AsyncSQLiteBackend"):     (
        "from ..backend.async_backend import",
        None,
    ),
    ("impl.firebird.mixins.transaction", "BeginTransactionExpression"):     (
        "from rhosocial.activerecord.backend.expression.transaction import",
        None,
    ),
    ("impl.firebird.mixins.transaction", "SetTransactionExpression"):     (
        "from rhosocial.activerecord.backend.expression.transaction import",
        None,
    ),
    ("impl.mysql.async_transaction", "AsyncMySQLBackend"):     (
        "from .async_backend import",
        None,
    ),
    ("impl.mysql.mixins.partition", "MySQLAddPartitionHelper"):     (
        "from rhosocial.activerecord.backend.impl.mysql.expression."
        "partition_lifecycle import",
        None,
    ),
    ("impl.mysql.mixins.partition", "MySQLCoalescePartitionHelper"):     (
        "from rhosocial.activerecord.backend.impl.mysql.expression."
        "partition_lifecycle import",
        None,
    ),
    ("impl.mysql.mixins.partition", "MySQLDropOldestPartitionHelper"):     (
        "from rhosocial.activerecord.backend.impl.mysql.expression."
        "partition_lifecycle import",
        None,
    ),
    ("impl.mysql.mixins.partition", "MySQLReorganizePartitionHelper"):     (
        "from rhosocial.activerecord.backend.impl.mysql.expression."
        "partition_lifecycle import",
        None,
    ),
    ("impl.mysql.mixins.partition", "MySQLAddSubpartitionHelper"):     (
        "from rhosocial.activerecord.backend.impl.mysql.expression."
        "partition_lifecycle import",
        None,
    ),
    ("impl.postgres.transaction", "AsyncPostgresBackend"):     (
        "from .backend.async_backend import",
        None,
    ),
    ("impl.postgres.protocols.extension", "SQLQueryAndParams"):     (
        "from rhosocial.activerecord.backend.expression.bases import",
        None,
    ),
}


def _override_for(ref: TypecheckImport) -> Optional[Tuple[str, Optional[str]]]:
    """Look up a manual override by module suffix and imported name."""
    for (suffix, name), value in MANUAL_OVERRIDES.items():
        if ref.name == name and ref.module.endswith(suffix):
            return value
    return None


def _module_package(module_name: str) -> str:
    return module_name.rpartition(".")[0]


def _relative_level(package: str, target: str) -> Optional[int]:
    """Smallest number of leading dots that turns ``package`` into ``target``.

    Returns ``None`` when ``target`` is not an ancestor of ``package``, which is the
    signal that the import should be absolute rather than relative.
    """
    pkg_parts = package.split(".") if package else []
    tgt_parts = target.split(".")
    if tgt_parts == pkg_parts[: len(tgt_parts)]:
        return len(pkg_parts) - len(tgt_parts) + 1
    return None


def _iter_candidate_levels(package: str, target: str) -> List[int]:
    """Relative levels to try, nearest ancestor first."""
    level = _relative_level(package, target)
    if level is None:
        return []
    return list(range(1, level + 1))


def plan_fix(ref: TypecheckImport) -> Optional[Tuple[int, str, str]]:
    """Return ``(level, module, prefix)`` that would resolve, or ``None``.

    The *authored* module tail is the intent, and the mistake is almost always a
    mis-counted relative level. The fixer therefore keeps the tail and walks
    candidate levels outward from the importing package, taking the first whose
    resolved module imports cleanly and exposes the attribute:

        from .dialect import MySQLDialect     # in impl/mysql/functions/  -> wrong
        from ..dialect import MySQLDialect    # impl/mysql/dialect       -> right

    Returning ``None`` means the tail itself is wrong, for instance when the module
    exists but the attribute was renamed. That case is left for a human, because
    guessing would silently repoint a symbol.
    """
    if not ref.path or not ref.written_module:
        return None
    package = _module_package(ref.module)
    parts = package.split(".") if package else []

    if ref.written_level == 0:
        # Absolute import: the level cannot be the problem, so try the tail against
        # the same package walk in case the author simply missed a level.
        tail = ref.written_module
    else:
        tail = ref.written_module

    for level in range(1, len(parts) + 2):
        anchor = parts[: len(parts) - level + 1] if level <= len(parts) else []
        candidate = ".".join(anchor + tail.split("."))
        if _resolves(candidate, ref.name):
            return level, tail, "from {}{} import".format("." * level, tail)
    return None


def _rewrite_prefix(
    path: str, lineno: int, new_prefix: str, new_name: Optional[str] = None
) -> Optional[str]:
    """Replace only the ``from ... import`` prefix of one line.

    Parenthesised multi-name imports put the names on following lines, so replacing
    the whole line would silently drop the other names. Returns the old line, or
    ``None`` when the line does not look like the expected import.
    """
    with open(path, "r", encoding="utf-8") as handle:
        lines = handle.readlines()
    index = lineno - 1
    if index >= len(lines):
        return None
    line = lines[index]
    head, sep, tail = line.partition(" import ")
    if not sep or not head.lstrip().startswith("from "):
        return None
    if new_name is not None:
        if "(" in tail:
            return None
        tail = new_name + tail[len(tail.split(",")[0]) :]
    indent = line[: len(line) - len(line.lstrip())]
    lines[index] = "{}{} {}\n".format(indent, new_prefix.strip(), tail.rstrip("\n"))
    with open(path, "w", encoding="utf-8") as handle:
        handle.writelines(lines)
    return line


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Repair dangling TYPE_CHECKING imports."
    )
    parser.add_argument(
        "--list", action="store_true", help="report only (default behaviour)"
    )
    parser.add_argument("--apply", action="store_true", help="rewrite files in place")
    parser.add_argument(
        "--repo",
        help="restrict the scan to one backend repository by path label",
    )
    args = parser.parse_args(argv)

    specs = discover_projects()
    if args.repo:
        label = os.path.basename(os.path.normpath(args.repo))
        specs = [s for s in specs if s.label == label]
        if not specs:
            print("no discovered project matches {!r}".format(label))
            return 1

    graph = build_graph(specs=specs)
    dangling = graph.dangling_typecheck_refs()

    if not args.apply:
        print("{} dangling TYPE_CHECKING import(s)".format(len(dangling)))
        for ref in dangling:
            print("  {}".format(ref.describe()))
        return 0

    fixed = 0
    unfixable: List[TypecheckImport] = []
    touched: List[str] = []
    for ref in dangling:
        if not ref.path or any(part in ref.path for part in SKIP_PATH_PARTS):
            unfixable.append(ref)
            continue
        planned = plan_fix(ref)
        override = _override_for(ref)
        if override is None and planned is None:
            unfixable.append(ref)
            continue
        prefix, new_name = override if override is not None else (planned[2], None)
        if _rewrite_prefix(ref.path, ref.lineno, prefix, new_name) is not None:
            fixed += 1
            touched.append(ref.path)
        else:
            unfixable.append(ref)

    print("rewrote {} import(s) in {} file(s)".format(fixed, len(set(touched))))
    for path in sorted(set(touched)):
        print("  {}".format(path))
    if unfixable:
        print("left untouched (target module itself is wrong, needs a human):")
        for ref in unfixable:
            print("  {}".format(ref.describe()))

    if fixed == 0:
        print("nothing to do; skipping the re-verification rebuild")
        return 0

    after = build_graph(specs=specs)
    remaining = after.dangling_typecheck_refs()
    print("re-verified: {} dangling remaining".format(len(remaining)))
    for ref in remaining:
        print("  {}".format(ref.describe()))
    if after.parse_failures:
        print("unparseable files (must be zero):")
        for path, message in after.parse_failures:
            print("  {}".format(message))
    return 0 if not remaining and not after.parse_failures else 2


if __name__ == "__main__":
    raise SystemExit(main())
