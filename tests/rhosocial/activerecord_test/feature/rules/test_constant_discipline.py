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
* a value spelled more than once where every spelling claims a name. The
  count asks whether a *name* is read, and the pragma table was read
  everywhere; that half is the second check below, which reads values.

The second check is the count's blind spot made mechanical. ``limit: int
= 100`` on four signatures, or one table written twice under one name,
passes every count: every copy is read, so the name looks used and the
value looks agreed. Nothing says the copies agree, which is the defect.
The second check therefore collects the literal values written under
``src/`` where they claim a name -- the default of a parameter, or the
value of a constant -- and reports a value one name answers in more than
one place. It is deliberately not "one value anywhere twice": a literal
in neither position claims nothing, so a collision with one is
indistinguishable from a coincidence, and a check that reports those
teaches its reader to ignore it.

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
        """The file's ``ast`` tree, or ``None`` when this grammar cannot
        read it; see :func:`_parse`."""
        return _parse(path)

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


# ---- the value, not the name ------------------------------------------- #

#: Values that are the language's own letters for "nothing", so that a
#: second copy of one is not a decision anybody made twice. An empty
#: container and ``...`` are here for the same reason: they say "nothing
#: is specified", not "this much". ``-1`` is here because a count below
#: zero is how a program spells "no limit" rather than a limit it chose.
_TRIVIAL = frozenset(
    {
        ("s", "NoneType", None),
        ("s", "bool", True),
        ("s", "bool", False),
        ("s", "int", 0),
        ("s", "int", 1),
        ("s", "int", -1),
        ("s", "str", ""),
        ("s", "ellipsis", Ellipsis),
        ("list", ()),
        ("tuple", ()),
        ("set", ()),
        ("dict", ()),
    }
)

#: Base names that make a class body a closed set of values rather than a
#: set of claims. A member is the word it carries -- two enums that spell
#: a member the same way are two vocabularies agreeing on a word, which is
#: consistency rather than a fact written twice -- and
#: ``python-hazards.md`` §11.3 already settled where that spelling goes.
_ENUM_BASES = frozenset({"Enum", "IntEnum", "StrEnum", "Flag", "IntFlag"})

#: What a site is, for a reader who has to act on the finding.
_PARAMETER = "parameter default"
_MODULE = "module constant"
_CLASS = "class constant"


def _literal(node):
    """A hashable key for a literal expression, or ``None``.

    A table is one value. The key for ``{"a": 1}`` describes the whole
    table, and the ``1`` inside it is the table's content rather than a
    number anybody wrote on its own -- which is what keeps a catalogue's
    vocabulary out of the findings, since a word inside a table repeats
    because the table holds it, not because two places decided it.

    Anything not written out in full has no key: a name, a call, a
    comprehension, an interpolated string. A value computed at run time is
    not a value two places can be caught disagreeing about.
    """
    if isinstance(node, ast.Constant):
        return ("s", type(node.value).__name__, node.value)
    if isinstance(node, (ast.List, ast.Tuple, ast.Set)):
        elements = tuple(_literal(element) for element in node.elts)
        if any(element is None for element in elements):
            return None
        kind = {ast.List: "list", ast.Tuple: "tuple", ast.Set: "set"}[type(node)]
        return (kind, elements)
    if isinstance(node, ast.Dict):
        pairs = tuple(
            (_literal(key), _literal(value))
            for key, value in zip(node.keys, node.values)
            if key is not None
        )
        if any(key is None or value is None for key, value in pairs):
            return None
        return ("dict", pairs)
    return None


def _enum_bodies(tree):
    """The ``ClassDef`` nodes this module declares as an Enum, by identity.

    Wider than :func:`_enum_classes` on purpose: that one asks which
    classes hold tables keyed by an enum member, this one asks which
    class bodies hold members. ``IntEnum`` and ``str, Enum`` are both
    closed sets, and the members inside them are exempt here for the
    reason above.
    """
    found = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        for base in node.bases:
            name = base.attr if isinstance(base, ast.Attribute) else getattr(base, "id", None)
            if name in _ENUM_BASES:
                found.add(id(node))
                break
    return found


def _defaults_of(func):
    """``(parameter name, default node)`` for every default a signature
    offers, positional ones aligned to the parameters they belong to."""
    args = func.args
    positional = list(args.posonlyargs) + list(args.args)
    pairs = [
        (arg.arg, default)
        for arg, default in zip(positional[len(positional) - len(args.defaults) :], args.defaults)
    ]
    pairs.extend(
        (arg.arg, default)
        for arg, default in zip(args.kwonlyargs, args.kw_defaults)
        if default is not None
    )
    return pairs


def _render(key):
    """The value a key describes, written the way source writes it."""
    if key[0] == "s":
        return repr(key[2])
    if key[0] == "dict":
        return "{" + ", ".join(f"{_render(k)}: {_render(v)}" for k, v in key[1]) + "}"
    elements = [_render(element) for element in key[1]]
    if key[0] == "tuple":
        # A one-element tuple is not a tuple without the comma that says so.
        return "(" + ", ".join(elements) + (",)" if len(elements) == 1 else ")")
    if key[0] == "list":
        return "[" + ", ".join(elements) + "]"
    return "{" + ", ".join(elements) + "}"


def _shorten(text, limit=64):
    """A rendering a reader can scan, however long the value is."""
    return text if len(text) <= limit else text[: limit - 3] + "..."


class _ValueScan:
    """One parse of the source tree, with every literal that claims a name.

    A value is collected where it claims one. The default of a parameter
    answers the question that parameter's name asks; an assignment to a
    name in capitals answers the question that constant's name asks. Both
    are places that must agree with every other place answering the same
    question, and the finding is one name answered twice.

    A literal in neither position is not collected at all. The looser rule
    -- one value anywhere, twice -- was measured first and reports every
    coincidence in the tree: a serializer's warn threshold of ``0.8``
    against the price of a banana in an example, a ``0.0`` retry delay
    against a ``0.0`` sleep in a worker pool, ``100`` against every
    hundred in the codebase. A literal nobody names claims nothing, so
    nothing distinguishes its repetition from an accident, and a check
    that lists accidents is a check its reader learns to skip.

    Enum members are exempt for the reason ``python-hazards.md`` §11.3
    gives: a closed set takes an Enum, and two enums spelling one member
    the same way are agreeing, not duplicating. Constants inside a
    function body are not read as claims -- a capital on a local is the
    rule's own "a local variable, without the capital name" case, which is
    a different finding from a value written twice.

    Tests are not scanned. A twin in a test is a fixture the test needs,
    and the plan puts the cross-repository half of this rule in
    ``python-activerecord-testsuite``, where all ten repositories are
    visible; here the tree is this repository's ``src/``.
    """

    def __init__(self):
        # (path, tree) for every file this interpreter could read
        self.trees = []
        # The files this interpreter could not parse, as for _Scan above.
        self.skipped = []
        for path in _python_files():
            if _REPO_ROOT / "src" not in path.parents:
                continue
            tree = _parse(path)
            if tree is None:
                self.skipped.append(path)
            else:
                self.trees.append((path, tree))
        # (name, value key) -> {(path, lineno, kind)}
        self.writings = {}
        self._collect()

    # -- collection ----------------------------------------------------- #

    def _collect(self):
        for path, tree in self.trees:
            self._walk(tree.body, path, _enum_bodies(tree), False, False, False)

    def _walk(self, nodes, path, enums, in_class, in_enum, in_function):
        """Read the statements here, recording each literal that claims a name.

        ``in_function`` says a function body has been entered, which is
        where a capital name stops being a constant and becomes a local
        variable wearing one.
        """
        for node in nodes:
            if isinstance(node, ast.ClassDef):
                self._walk(node.body, path, enums, True, id(node) in enums, False)
                continue
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self._record_defaults(node, path)
                self._walk(node.body, path, enums, False, False, True)
                continue
            if isinstance(node, ast.Lambda):
                self._record_defaults(node, path)
                continue
            if isinstance(node, (ast.Assign, ast.AnnAssign)) and not in_enum and not in_function:
                self._record_constant(node, path, in_class)
                continue
            # Every other statement is plumbing: the value is written where
            # it claims a name, or it is a body to walk into.
            self._walk(
                list(ast.iter_child_nodes(node)), path, enums, in_class, in_enum, in_function
            )

    def _record_defaults(self, func, path):
        """The defaults a signature offers, each against its parameter's name."""
        for name, default in _defaults_of(func):
            key = _literal(default)
            if key is None or key in _TRIVIAL:
                continue
            self.writings.setdefault((name, key), set()).add((path, default.lineno, _PARAMETER))

    def _record_constant(self, node, path, in_class):
        """The value an all-caps assignment writes, against the name it writes
        it under -- at class level as well as module level, because
        ``DEFAULT_PRAGMAS`` was once a module table and a ``ClassVar``
        spelling of the same table, and the two had to agree."""
        for target in _target_names(node):
            if not _NAME.match(target.id):
                continue
            key = _literal(_assigned_value(node))
            if key is None or key in _TRIVIAL:
                continue
            kind = _CLASS if in_class else _MODULE
            self.writings.setdefault((target.id, key), set()).add((path, node.lineno, kind))

    # -- the finding ----------------------------------------------------- #

    def offenders(self):
        """Every value one name answers in more than one place, as
        ``(path, lineno, kind, name, value)`` sorted into groups."""
        found = []
        for (name, key), sites in self.writings.items():
            if len(sites) < 2:
                continue
            found.append((name, key, sorted(sites)))
        return sorted(found, key=lambda group: (group[0], str(group[1])))


def _value_findings(offenders):
    """The findings as lines, grouped by the name that answers twice.

    The value alone is not actionable: ``100`` is written a hundred times
    and nobody is going to look. The name and the kind of each site are
    what make it a decision -- whose default, which constant -- and the
    locations are what make it fixable without rerunning anything.
    """
    lines = ["one value written where two places must agree, with nothing asserting it:"]
    for name, key, sites in offenders:
        lines.append(f"  {name} = {_shorten(_render(key))}")
        for kind in (_PARAMETER, _MODULE, _CLASS):
            for path, lineno, site_kind in sites:
                if site_kind == kind:
                    lines.append(f"      {kind:17} {path.relative_to(_REPO_ROOT)}:{lineno}")
    return "\n".join(lines)


def test_no_value_is_written_in_two_places_that_must_agree():
    """A default is not a fact because two places wrote it down.

    The rule's clause, made mechanical: the count in the check above asks
    whether a *name* is read, and ``DEFAULT_PRAGMAS`` was read everywhere
    it was spelled, so every copy passed. This check reads values instead,
    where they claim a name, and fails listing the ones one name answers
    twice -- ``limit`` defaulting to ``100`` on four signatures, a table
    written twice under one name -- with the name, the kind of each site
    and the file and line, so a reader can act without rerunning anything.

    What this run says about files it could not read is the same as above,
    for the same reason and with the same consequence: on 3.12 and above a
    file that refuses is a hole in the coverage and fails here naming it,
    and below 3.12 the fixtures' PEP 695 headers cannot be read at all, so
    they are recorded in a warning and the assertion runs over what could
    be read. A reader is told either way that the count was taken over
    fewer files.

    What this still cannot see: two *different* names answering one
    question -- ``limit`` in four places is caught, ``limit`` here and
    ``max_rows`` there is the same defect and no AST says so. A value
    written once under a name and once where nothing names it, which is a
    coincidence as often as it is a duplicate. A reader outside the AST,
    as above. And the other nine repositories, as above: the plan's
    ``DEFAULT_VALUE_SAMPLE_LIMIT`` is spelled in five CLIs against this
    repository's four signatures, and the half of that pair which lives
    here is what ``limit`` reports.
    """
    scan = _ValueScan()
    if sys.version_info >= _PEP695 and scan.skipped:
        # This grammar is as new as the sources are, so a file it still cannot
        # read is a file nothing checked.
        pytest.fail(
            "every file in the tree should be readable by this grammar; "
            "these were skipped, so nothing checked them:\n" + _unreadable(scan.skipped)
        )
    elif scan.skipped:
        warnings.warn(
            "not checked, because this interpreter's grammar cannot read them "
            "(PEP 695 needs 3.12):\n" + _unreadable(scan.skipped),
            stacklevel=1,
        )
    offenders = scan.offenders()
    assert not offenders, _value_findings(offenders)
