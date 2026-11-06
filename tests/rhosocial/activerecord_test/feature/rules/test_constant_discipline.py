# tests/rhosocial/activerecord_test/feature/rules/test_constant_discipline.py
"""The mechanical half of ``.claude/rules/constants.md``.

A module-level name written in capitals claims that the value is a fact of the
domain and that everyone who reads it sees the same one. This is where that
claim is checked rather than trusted: every module-level all-caps assignment
under ``src/`` is parsed, its readers are counted across ``src/`` and
``tests/``, and a name read exactly once -- and named by no test assertion --
is reported with its file and line.

What is *not* a read: an ``import`` statement. Importing a name nobody reads
is the defect, not the exoneration, so ``from x import Y`` does not count
towards Y's readers. What is also not reported: a name nobody reads at all.
That is the "never referenced" case, which the rule settles as a deletion and
which is a different finding from "one reader".

What this cannot see, and the rule says so:

* the other nine repositories, so the cross-repository clause -- same name,
  same shape, same meaning -- is unenforced here and belongs in
  ``python-activerecord-testsuite``;
* any reader outside the AST: a ``getattr``, a name in a config file, a
  script, a benchmark or a document;
* a value spelled three times with each copy read once. The count asks
  whether a *name* is read; it cannot ask whether a *value* is one thing.

The reader of these sources is the ``ast`` of whichever interpreter is
running the check, and that grammar is not the same grammar everywhere:
the PEP 695 class headers the fixtures write cannot be read by anything
below 3.12. So what a run tells you about unreadable files depends on the
interpreter it ran under. On 3.12 and above the grammar is as new as the
sources are, every file is read, and a file that still refuses is a hole in
the coverage and fails. Below 3.12 the files this grammar rejects are
recorded in a warning and the assertion is taken over what could be read --
a failure there would be this check reporting the age of its own reader
instead of anything about the source, and it would take four CI legs down
with it. Either way a skipped file is never passed over in silence: a file
nobody is told about is a file nobody is checking.

The exemptions are ``python-hazards.md`` §11.3's, applied so this check does
not re-litigate what that rule already settled: compiled regexes and the
fragments composed into them, numeric defaults, tables keyed by an Enum
member, and lazily built caches.
"""

import ast
import os
import re
import sys
import warnings
from pathlib import Path

import pytest

pytestmark = [pytest.mark.feature]

#: The repository root: this file sits at
#: ``tests/rhosocial/activerecord_test/feature/rules/``.
_REPO_ROOT = Path(__file__).resolve().parents[5]

#: Where a definition comes from, and where its readers are counted.
_SOURCE_DIRS = ("src", "tests")

#: Directories holding neither library source nor tests.
_SKIPPED = frozenset(
    {
        "__pycache__",
        ".git",
        ".pytest_cache",
        ".ruff_cache",
        ".mypy_cache",
        ".benchmarks",
        "build",
        "dist",
        ".venv3.14",
        ".venv3.15",
    }
)

#: A module-level name in capitals, with or without the leading underscore:
#: ``INTROSPECT_TYPES`` and ``_SUGGESTION_QUALIFY`` make the same claim.
_NAME = re.compile(r"^_{0,1}[A-Z][A-Z0-9_]*$")

#: Where the grammar the sources are written in arrived. PEP 695's
#: ``class C[T]:`` is used by the py312 fixtures, and 3.12 is the first
#: interpreter that can read it, which is what makes a skip below this line
#: the grammar's age and a skip at or above it a gap in the coverage.
_PEP695 = (3, 12)

#: Typing roots that make an assignment a type alias rather than a value.
_TYPING_ROOTS = frozenset(
    {
        "Any",
        "Callable",
        "Dict",
        "FrozenSet",
        "Iterable",
        "List",
        "Literal",
        "Mapping",
        "NewType",
        "Optional",
        "Protocol",
        "Sequence",
        "Set",
        "Tuple",
        "Type",
        "TypeAlias",
        "TypeVar",
        "Union",
    }
)


def _python_files():
    """Every ``.py`` under the source and test trees, caches excluded."""
    for directory in _SOURCE_DIRS:
        base = _REPO_ROOT / directory
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = sorted(d for d in dirnames if d not in _SKIPPED)
            for filename in sorted(filenames):
                if filename.endswith(".py"):
                    yield Path(dirpath) / filename


def _target_names(node):
    """The ``Name`` targets of an assignment node."""
    if isinstance(node, ast.Assign):
        return [t for t in node.targets if isinstance(t, ast.Name)]
    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        return [node.target]
    return []


def _assigned_value(node):
    """The value an assignment node writes, or ``None``."""
    if isinstance(node, ast.Assign):
        return node.value
    if isinstance(node, ast.AnnAssign):
        return node.value
    return None


def _called_name(call):
    """``re`` for ``re.compile``, ``TypeVar`` for ``TypeVar(...)``."""
    func = call.func
    if isinstance(func, ast.Attribute):
        return func.value.id if isinstance(func.value, ast.Name) else None
    if isinstance(func, ast.Name):
        return func.id
    return None


def _is_compiled_pattern(value):
    """Whether an assignment writes ``re.compile(...)``."""
    return (
        isinstance(value, ast.Call)
        and isinstance(value.func, ast.Attribute)
        and _called_name(value) == "re"
        and value.func.attr == "compile"
    )


def _enum_classes(tree):
    """The names this module declares as an Enum."""
    found = set()
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        for base in node.bases:
            name = base.attr if isinstance(base, ast.Attribute) else getattr(base, "id", None)
            if name == "Enum":
                found.add(node.name)
    return found


def _names_enum_member(value, enums):
    """Whether a table's entries name a member of an Enum declared beside it.

    The alias tables ``python-hazards.md`` §3 measured -- keyed by
    ``DateTimeField`` and ``IntervalUnit`` -- and the arithmetic symbol table
    are this shape, and that rule already settled them.
    """
    if not enums:
        return False
    for node in ast.walk(value):
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            if node.value.id in enums:
                return True
    return False


def _exemption(value, enums):
    """Why this value is not what the rule is about, or ``None``.

    ``python-hazards.md`` §11.3's exemptions, plus the two things that are not
    constants at all: a type alias and a type variable.
    """
    if isinstance(value, ast.Constant):
        # A numeric default. A sentence in quotes is not a numeric default.
        return isinstance(value.value, (int, float)) and not isinstance(value.value, bool)
    if isinstance(value, ast.Call):
        # ``re.compile`` is the compiled pattern; ``TypeVar`` / ``NewType``
        # name a type variable, not a value anyone has to keep in step.
        if _is_compiled_pattern(value):
            return True
        return _called_name(value) in {"TypeVar", "NewType"}
    if isinstance(value, (ast.Dict, ast.List, ast.Set, ast.Tuple)):
        # An empty container is a cache nobody has filled yet.
        empty = not value.keys if isinstance(value, ast.Dict) else not value.elts
        if empty:
            return True
        return _names_enum_member(value, enums)
    if isinstance(value, ast.Subscript):
        root = value.value
        return isinstance(root, ast.Name) and root.id in _TYPING_ROOTS
    return False


class _Scan:
    """One parse of the source and test trees, with the counts taken."""

    def __init__(self):
        self.trees = []
        # The files this interpreter could not parse. Recorded so the gap is
        # visible somewhere; see _unreadable.
        self.skipped = []
        for path in _python_files():
            tree = self._parse(path)
            if tree is None:
                self.skipped.append(path)
            else:
                self.trees.append((path, tree))
        # (name, path, lineno, value, enums)
        self.constants = []
        # name -> readers; name -> [statement] holding every reader
        self.loads = {}
        self.load_sites = {}
        self.pinned = set()
        self._collect_constants()
        self._collect_readers()
        self._collect_pinned()

    @staticmethod
    def _parse(path):
        """The file's ``ast`` tree, or ``None`` when this grammar cannot read it.

        A tool that reads source has to be more tolerant than the source it
        reads: one file this interpreter refuses costs the check a piece of
        the tree, never the check itself. ``feature_version`` is deliberately
        not pinned -- it asks for an *older* grammar than the running one, and
        a target ahead of the interpreter is either rejected outright or
        parsed with the grammar it already has, so syntax newer than the
        reader stays unreadable either way and the parameter would only
        suggest otherwise.

        Three ways a file refuses to be read, all survivable: a
        ``SyntaxError``, which is a grammar younger than this interpreter's;
        a ``ValueError``, which is bytes that are not UTF-8 (a
        ``UnicodeDecodeError`` *is* one) or a NUL smuggled into the text; and
        a ``RecursionError``, which is the parser giving up on the nesting
        before the check has to.
        """
        try:
            with open(path, encoding="utf-8") as handle:
                return ast.parse(handle.read(), filename=str(path))
        except (SyntaxError, ValueError, RecursionError):
            return None

    # -- collection ----------------------------------------------------- #

    def _collect_constants(self):
        for path, tree in self.trees:
            if _REPO_ROOT / "src" not in path.parents:
                continue
            enums = _enum_classes(tree)
            for node in tree.body:
                for target in _target_names(node):
                    if not _NAME.match(target.id):
                        continue
                    self.constants.append(
                        (target.id, path, node.lineno, _assigned_value(node), enums)
                    )
                    self.loads.setdefault(target.id, 0)
                    self.load_sites.setdefault(target.id, [])

    def _collect_readers(self):
        for _, tree in self.trees:
            for node in tree.body:
                self._walk_reads(node, node)

    def _walk_reads(self, node, statement):
        """Count every load of a collected name, remembering its statement."""
        for child in ast.iter_child_nodes(node):
            if isinstance(child, ast.stmt):
                self._walk_reads(child, child)
                continue
            if isinstance(child, ast.Name) and isinstance(child.ctx, ast.Load):
                if child.id in self.loads:
                    self.loads[child.id] += 1
                    self.load_sites[child.id].append(statement)
            self._walk_reads(child, statement)

    def _collect_pinned(self):
        """The assertion inventory: names an ``assert`` or a ``parametrize``
        names, anywhere in the test tree."""
        for path, tree in self.trees:
            if _REPO_ROOT / "tests" not in path.parents:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Assert):
                    self._pinned_within(node)
                elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                    if node.func.attr == "parametrize":
                        self._pinned_within(node)

    def _pinned_within(self, node):
        for sub in ast.walk(node):
            if isinstance(sub, ast.Name):
                self.pinned.add(sub.id)
            elif isinstance(sub, ast.Attribute):
                self.pinned.add(sub.attr)

    # -- what counts as a read ------------------------------------------ #

    def _sits_in_pattern_call(self, name, statement):
        """Whether this reader is an argument of a ``re`` call.

        A fragment composed into a pattern is the exemption, not the use.
        """
        for node in ast.walk(statement):
            if not (isinstance(node, ast.Call) and _called_name(node) == "re"):
                continue
            for sub in ast.walk(node):
                if isinstance(sub, ast.Name) and sub.id == name:
                    return True
        return False

    def _assigned_name(self, statement):
        """The all-caps module-level name an assignment statement writes."""
        for target in _target_names(statement):
            if _NAME.match(target.id):
                return target.id
        return None

    def _feeds_a_pattern(self, name, visited=None):
        """Whether every reading of this name composes a regex, directly or
        through another name that does."""
        visited = set() if visited is None else visited
        visited.add(name)
        for statement in self.load_sites.get(name, []):
            if self._sits_in_pattern_call(name, statement):
                continue
            assigned = self._assigned_name(statement)
            if assigned and assigned not in visited and self._feeds_a_pattern(assigned, visited):
                continue
            return False
        return True

    # -- the finding ----------------------------------------------------- #

    def offenders(self):
        """Every module-level all-caps name read exactly once and pinned
        nowhere, as ``(path, lineno, name)``."""
        found = []
        for name, path, lineno, value, enums in self.constants:
            if self.loads.get(name, 0) != 1:
                continue
            if _exemption(value, enums):
                continue
            if self._feeds_a_pattern(name):
                continue
            if name in self.pinned:
                continue
            found.append((path.relative_to(_REPO_ROOT), lineno, name))
        return sorted(found)


def _unreadable(skipped):
    """The files this interpreter could not parse, one line each, or ``None``.

    A file the running grammar refuses is a gap in the coverage and not an
    error in the check, so it is named rather than dropped: the point of the
    check is that its output can be trusted, and a file skipped in silence is
    a file nobody checked. What is done with the list depends on the age of
    the grammar, which is the caller's business.
    """
    if not skipped:
        return None
    return "\n".join(
        # A path the walk somehow produced from outside the tree still gets
        # named: this reports the gap, it does not raise on one.
        f"  {path.relative_to(_REPO_ROOT) if _REPO_ROOT in path.parents else path}"
        for path in skipped
    )


def test_no_module_level_constant_is_read_once_and_pinned_nowhere():
    """A name in caps has to be read in more than one place, or pinned.

    One reader and no assertion is a sentence somebody wanted to type once.
    The offenders are listed by file and line so a reader can act without
    rerunning anything; what to do about them is
    ``.claude/rules/constants.md``.

    What this run says about files it could not read, per interpreter. On
    3.12 and above the grammar is as new as the sources, so a file that
    refuses is a hole in the coverage and fails here naming the file: at
    that age the grammar has stopped being the explanation. Below 3.12 the
    fixtures' PEP 695 headers cannot be read at all, and failing on them
    would be the check reporting the age of its own reader instead of
    anything about the source -- it would take the CI leg down with it --
    so they are recorded in a warning and the assertion below runs over the
    tree that could be read. A reader of the output is told either way: the
    offender count on an old interpreter is taken over fewer files, and the
    warning names which ones.
    """
    scan = _Scan()
    if sys.version_info >= _PEP695 and scan.skipped:
        # This grammar is as new as the sources are. A file it still cannot
        # read is not the grammar's age -- it is a file nothing checked.
        pytest.fail(
            "every file in the tree should be readable by this grammar; "
            "these were skipped, so nothing checked them:\n" + _unreadable(scan.skipped)
        )
    elif scan.skipped:
        # Below 3.12 the fixtures' PEP 695 headers cannot be read at all, and
        # failing on them would be the check reporting the age of its own
        # reader instead of anything about the source. Recorded, not passed
        # over in silence.
        warnings.warn(
            "not checked, because this interpreter's grammar cannot read them "
            "(PEP 695 needs 3.12):\n" + _unreadable(scan.skipped),
            stacklevel=1,
        )
    offenders = scan.offenders()
    assert not offenders, "\n".join(
        ["module-level constants read exactly once and named by no test assertion:"]
        + [f"  {path}:{lineno}: {name}" for path, lineno, name in offenders]
    )
