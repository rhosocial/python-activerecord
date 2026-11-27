# tests/rhosocial/activerecord_test/feature/rules/test_init_raise_sites_never_grow.py
"""Monotonic guard: no new constructor validation may land in core.

The expression migration moves refusals out of ``__init__`` and into public
``validate_*()`` methods that each backend formatter may call on its own terms.
While that migration is in progress, this guard freezes the census: a new
``raise`` inside an ``__init__`` under ``backend/expression`` fails the build.
Existing sites may be removed (the migration does exactly that), so this is an
allowlist of known sites, not an assertion that today's count is permanent.

The key is deliberately free of line numbers: moving a check from the
constructor to a validator shifts every line below it, and a line-keyed
allowlist would fail on the refactor it is meant to protect. Interpolations in
f-string messages are normalised to ``{}`` so the key stays independent of the
interpreter's ``ast`` details. Files this interpreter cannot parse are named in
a warning (and are a coverage hole on 3.12+, whose grammar is as new as the
sources), following ``test_constant_discipline.py``: the grammar's age must not
turn into a rule failure on an older CI leg.
"""

from __future__ import annotations

import ast
import sys
import warnings
from collections import Counter
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import pytest

pytestmark = [pytest.mark.feature]

_SRC = (
    Path(__file__).resolve().parents[5]
    / "src"
    / "rhosocial"
    / "activerecord"
    / "backend"
    / "expression"
)

#: PEP 695 class headers in fixtures need 3.12; below that an unreadable file
#: is the reader's age, at or above it an unreadable file is a coverage hole.
_PEP695 = (3, 12)

Key = Tuple[str, str, str, str]

#: (relative path, class name, exception type, normalised message) -> how many
#: direct raises of that shape are currently allowed inside ``__init__``.
ALLOWED: Dict[Key, int] = {
    ("advanced_functions.py", "ExistsPredicate", "TypeError", "subquery must be Subquery or BaseExpression, got {}"): 1,
    ("advanced_functions.py", "OrderedSetAggregation", "TypeError", "order_by must be OrderByClause or str, got {}"): 1,
    ("advanced_functions.py", "WindowSpecification", "TypeError", "order_by must be OrderByClause or str, got {}"): 1,
    ("core.py", "CastExpression", "TypeError",
     "cast() takes a DataType instance, not {}. Use IntegerType(dialect) rather "
     "than a string: the type position cannot be bound, so a string is rendered "
     "into the SQL. A user-defined type is a DataType subclass, registered so "
     "dialects can render it."): 1,
    ("datetime.py", "_ExtractBase", "ValueError", "spelling {} extracts {}, not {}"): 1,
    ("datetime.py", "_ExtractBase", "ValueError", "unknown extract spelling {}: the spellings are {}"): 1,
    ("functions/aggregate.py", "AggregateFunction", "TypeError", "distinct must be a bool, got {}"): 1,
    ("functions/aggregate.py", "AggregateFunction", "ValueError",
     "COUNT(DISTINCT *) is not valid SQL: the row-count wildcard counts rows, "
     "which have no duplicates."): 1,
    ("functions/aggregate.py", "AggregateFunction", "ValueError",
     "{} does not accept a row-count wildcard: the bare * counts rows, and "
     "COUNT is the only aggregate whose contract admits it."): 1,
    ("functions/aggregate.py", "AggregateFunction", "ValueError",
     "{} takes a value expression, not the all-columns wildcard: '*' expands "
     "columns and belongs to a select list or RETURNING clause."): 1,
    ("functions/string.py", "CharLengthFunction", "ValueError", "unknown length unit {}: the units are {}"): 1,
    ("functions/string.py", "LeftFunction", "ValueError", "left(): n must be >= 0, got {}"): 1,
    ("functions/string.py", "PositionExpression", "ValueError",
     "unknown position spelling {}: the spellings are {}"): 1,
    ("functions/string.py", "RightFunction", "ValueError", "right(): n must be >= 0, got {}"): 1,
    ("functions/string.py", "SubstringExpression", "ValueError", "substring(): length must be >= 0, got {}"): 1,
    ("functions/string.py", "SubstringExpression", "ValueError",
     "substring(): start must be >= 1 (positions are 1-based), got {}"): 1,
    ("objects/base.py", "SchemaObject", "ValueError", "catalog_name must be a non-empty string or None"): 1,
    ("objects/base.py", "SchemaObject", "ValueError", "name must be a non-empty string"): 1,
    ("objects/base.py", "SchemaObject", "ValueError", "schema_name must be a non-empty string or None"): 1,
    ("operators.py", "ArithmeticOperation", "ValueError",
     "unknown arithmetic operation {}: the operation words are {}"): 1,
    ("pivot.py", "Unpivot", "ValueError", "include_nulls and exclude_nulls are mutually exclusive options"): 1,
    ("query_parts.py", "GroupByHavingClause", "ValueError", "HAVING clause requires GROUP BY clause"): 1,
    ("query_parts.py", "JoinClause", "ValueError",
     "Cannot specify both 'condition' (ON) and 'using' (USING) clauses in a JOIN"): 1,
    ("query_sources.py", "CTEClause", "ValueError",
     "materialized and not_materialized are mutually exclusive options"): 1,
    ("query_sources.py", "TableFunctionExpression", "ValueError", "column_types requires column_names"): 1,
    ("serialization.py", "ExpressionSerializer", "ValueError", "max_depth must be a positive integer"): 1,
    ("serialization.py", "ExpressionSerializer", "ValueError", "warn_threshold must be between 0 and 1"): 1,
    ("statements/ddl_alter.py", "ValidateConstraintAction", "ValueError",
     "constraint_name must be a non-empty string"): 1,
    ("statements/ddl_alter.py", "ValidateConstraintAction", "ValueError", "name and constraint_name must match"): 1,
    ("statements/ddl_comment.py", "CommentOnStatement", "ValueError", "column must be a non-empty string or None"): 1,
    ("statements/ddl_domain.py", "CreateDomainStatement", "TypeError",
     "data_type must be a DataType instance, got {}"): 1,
    ("statements/ddl_domain.py", "CreateDomainStatement", "TypeError",
     "nullability must be a DomainNullability instance, got {}"): 1,
    ("statements/ddl_domain.py", "CreateDomainStatement", "ValueError", "Invalid domain nullability: {}"): 1,
    ("statements/ddl_domain.py", "CreateDomainStatement", "ValueError",
     "collation must contain non-empty identifier segments"): 1,
    ("statements/ddl_domain.py", "DomainCheckConstraint", "TypeError",
     "condition must be a SQLPredicate instance, got {}"): 1,
    ("statements/ddl_partition.py", "PartitionDefinitionExpression", "ValueError",
     "less_than and in_values are mutually exclusive"): 1,
    ("statements/ddl_partition.py", "PartitionDefinitionExpression", "ValueError",
     "partition name must be a non-empty string"): 1,
    ("statements/ddl_partition.py", "SubpartitionDefinitionExpression", "ValueError",
     "subpartition name must be a non-empty string"): 1,
    ("statements/ddl_sequence.py", "AlterSequenceStatement", "ValueError",
     "cache and no_cache are mutually exclusive options"): 1,
    ("statements/ddl_sequence.py", "AlterSequenceStatement", "ValueError",
     "cache must be a positive integer; use no_cache=True to spell NO CACHE"): 1,
    ("statements/ddl_sequence.py", "AlterSequenceStatement", "ValueError",
     "cycle and no_cycle are mutually exclusive options"): 1,
    ("statements/ddl_sequence.py", "AlterSequenceStatement", "ValueError",
     "order and no_order are mutually exclusive options"): 1,
    ("statements/ddl_sequence.py", "CreateSequenceStatement", "ValueError",
     "cache and no_cache are mutually exclusive options"): 1,
    ("statements/ddl_sequence.py", "CreateSequenceStatement", "ValueError",
     "cache must be a positive integer; use no_cache=True to spell NO CACHE"): 1,
    ("statements/ddl_sequence.py", "CreateSequenceStatement", "ValueError",
     "cycle and no_cycle are mutually exclusive options"): 1,
    ("statements/ddl_sequence.py", "CreateSequenceStatement", "ValueError",
     "order and no_order are mutually exclusive options"): 1,
    ("statements/ddl_table.py", "CharacterSetClause", "ValueError",
     "CHARACTER SET requires a character set name"): 1,
    ("statements/ddl_table.py", "CollationClause", "ValueError", "COLLATE requires a collation name"): 1,
    ("statements/ddl_table.py", "ColumnCheckConstraint", "ValueError",
     "ColumnCheckConstraint needs a condition: CHECK without one states nothing."): 1,
    ("statements/ddl_table.py", "ColumnConstraint", "TypeError",
     "ColumnConstraint.branch must be a ColumnConstraintBranch, got {}"): 1,
    ("statements/ddl_table.py", "ColumnDefaultConstraint", "ValueError",
     "ColumnDefaultConstraint needs a value: DEFAULT without one states nothing. "
     "The refusal is here rather than at render time because a clause with no "
     "value cannot be rendered at all."): 1,
    ("statements/ddl_table.py", "ColumnDefinition", "TypeError", "comment must be a ColumnCommentClause, got {}"): 1,
    ("statements/ddl_table.py", "ColumnDefinition", "TypeError",
     "data_type must be a DataType instance, got {}"): 1,
    ("statements/ddl_table.py", "ColumnForeignKeyConstraint", "TypeError",
     "ColumnForeignKeyConstraint.references must pair a Table with its columns, got {}"): 1,
    ("statements/ddl_table.py", "ColumnForeignKeyConstraint", "ValueError",
     "ColumnForeignKeyConstraint needs references: the (Table, [columns]) it "
     "points at. A foreign key without one points nowhere."): 1,
    ("statements/ddl_table.py", "CreateTableAsStatement", "ValueError",
     "as_query is required for CreateTableAsStatement"): 1,
    ("statements/ddl_table.py", "CreateTableCloneStatement", "TypeError",
     "mode must be a CreateTableCloneMode, got {}"): 1,
    ("statements/ddl_table.py", "CreateTableFromTemplateStatement", "ValueError",
     "template is required for CreateTableFromTemplateStatement"): 1,
    ("statements/ddl_table.py", "CreateTableOptions", "TypeError",
     "comment must be a TableCommentClause, got {}"): 1,
    ("statements/ddl_table.py", "CreateTableStatement", "TypeError",
     "partition must be a PartitionClause instance, got {}"): 1,
    ("statements/ddl_table.py", "IdentityClause", "ValueError",
     "cache and no_cache are mutually exclusive options"): 1,
    ("statements/ddl_table.py", "IdentityClause", "ValueError",
     "cache must be a positive integer; use no_cache=True to spell NO CACHE"): 1,
    ("statements/ddl_table.py", "IdentityClause", "ValueError",
     "order and no_order are mutually exclusive options"): 1,
    ("statements/ddl_table.py", "TableCheckConstraint", "ValueError",
     "TableCheckConstraint needs a condition: CHECK without one states nothing."): 1,
    ("statements/ddl_table.py", "TableConstraint", "TypeError",
     "TableConstraint.branch must be a TableConstraintBranch, got {}"): 1,
    ("statements/ddl_table.py", "TableConstraint", "ValueError",
     "DEFERRABLE / INITIALLY cannot ride a {}; the SQL:2016 kinds are PRIMARY "
     "KEY, UNIQUE and FOREIGN KEY"): 1,
    ("statements/ddl_table.py", "TableConstraint", "ValueError",
     "ENFORCED/NOT ENFORCED cannot ride a {}; the SQL:2016 kinds are PRIMARY "
     "KEY, UNIQUE, FOREIGN KEY and CHECK"): 1,
    ("statements/ddl_table.py", "TableForeignKeyConstraint", "ValueError",
     "TableForeignKeyConstraint needs references: the (Table, [columns]) it points at."): 1,
    ("statements/ddl_type.py", "CreateTypeStatement", "ValueError",
     "CREATE TYPE IF NOT EXISTS and OR REPLACE are mutually exclusive"): 1,
    ("statements/dml.py", "DeleteStatement", "ValueError",
     "Table list cannot be empty for a DELETE statement."): 1,
    ("statements/dml.py", "InsertStatement", "ValueError",
     "'DEFAULT VALUES' source cannot be used with 'columns'."): 1,
    ("statements/dml.py", "InsertStatement", "ValueError",
     "'on_conflict' is only supported for 'VALUES' or 'SELECT' sources."): 1,
    ("statements/dml.py", "InsertStatement", "ValueError",
     "Cannot specify both 'or_replace' and 'or_ignore'."): 1,
    ("statements/dml.py", "InsertStatement", "ValueError",
     "Cannot use 'or_replace'/'or_ignore' together with 'on_conflict'. Use "
     "either the SQLite-specific OR REPLACE/IGNORE syntax or the standard ON "
     "CONFLICT clause, but not both."): 1,
    ("statements/dml.py", "OnConflictClause", "ValueError",
     "Cannot specify both 'do_nothing=True' and 'update_assignments' for ON CONFLICT."): 1,
    ("statements/dml.py", "OnConflictClause", "ValueError",
     "Must specify either 'do_nothing=True' or 'update_assignments' for ON CONFLICT."): 1,
    ("statements/dml.py", "UpdateStatement", "ValueError",
     "Assignments cannot be empty for an UPDATE statement."): 1,
    ("statements/dml.py", "ValuesSource", "ValueError",
     "'values_list' must be a non-empty list of lists."): 1,
    ("statements/dml.py", "ValuesSource", "ValueError",
     "All rows in 'values_list' must have the same number of columns."): 1,
    ("types/array.py", "ArrayType", "TypeError",
     "ArrayType requires an element_type: T[] is a property of T, and an array "
     "with no element type is not a type. For a type the framework does not "
     "model, use CustomType(raw)."): 1,
    ("types/array.py", "ArrayType", "TypeError",
     "element_type must be a DataType instance, got {}."): 1,
    ("types/array.py", "ArrayType", "ValueError", "dimensions must be an int >= 1, got {}."): 1,
    ("types/enum_.py", "EnumType", "ValueError", "EnumType requires at least one value"): 1,
    ("types/enum_.py", "EnumType", "ValueError", "EnumType requires values"): 1,
}


def _message(node: ast.AST) -> str:
    """A version-independent rendering of a raise's message.

    Interpolations become ``{}``; only string literals are read. This never
    calls ``ast.unparse`` (absent on 3.8) and never dumps an AST (whose field
    layout differs between interpreters).
    """
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        out = []
        for part in node.values:
            if isinstance(part, ast.Constant) and isinstance(part.value, str):
                out.append(part.value)
            else:
                out.append("{}")
        return "".join(out)
    return "<expr>"


def _keys_in_source(text: str, label: str) -> List[Key]:
    tree = ast.parse(text)
    keys: List[Key] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        for item in node.body:
            if not isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            if item.name != "__init__":
                continue
            for sub in ast.walk(item):
                if not isinstance(sub, ast.Raise) or sub.exc is None:
                    continue
                exc = sub.exc
                if isinstance(exc, ast.Call):
                    func = exc.func
                    if isinstance(func, ast.Name):
                        exc_type = func.id
                    elif isinstance(func, ast.Attribute):
                        exc_type = func.attr
                    else:
                        exc_type = "<expr>"
                    message = _message(exc.args[0]) if exc.args else "<none>"
                else:
                    exc_type, message = "<bare>", "<none>"
                keys.append((label, node.name, exc_type, message))
    return keys


def _parse(path: Path) -> Optional[ast.Module]:
    """The tree, or ``None`` when this interpreter's grammar cannot read it."""
    try:
        return ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (SyntaxError, ValueError, RecursionError):
        return None


def _census(paths: Iterable[Path]) -> Tuple[Counter, List[Path]]:
    found: Counter = Counter()
    skipped: List[Path] = []
    for path in paths:
        tree = _parse(path)
        if tree is None:
            skipped.append(path)
            continue
        label = path.relative_to(_SRC).as_posix()
        for node in ast.walk(tree):
            if not isinstance(node, ast.ClassDef):
                continue
            for item in node.body:
                if not isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                if item.name != "__init__":
                    continue
                for sub in ast.walk(item):
                    if not isinstance(sub, ast.Raise) or sub.exc is None:
                        continue
                    exc = sub.exc
                    if isinstance(exc, ast.Call):
                        func = exc.func
                        name = getattr(func, "id", getattr(func, "attr", "<expr>"))
                        message = _message(exc.args[0]) if exc.args else "<none>"
                    else:
                        name, message = "<bare>", "<none>"
                    found[(label, node.name, name, message)] += 1
    return found, skipped


def _source_files() -> List[Path]:
    return [p for p in sorted(_SRC.rglob("*.py")) if "__pycache__" not in p.parts]


def _warn_on_skipped(skipped: List[Path]) -> None:
    if not skipped:
        return
    names = "\n".join(f"  {p.relative_to(_SRC)}" for p in skipped)
    if sys.version_info >= _PEP695:
        pytest.fail(
            "every expression source should be readable by this grammar; "
            "these were skipped, so nothing checked them:\n" + names
        )
    warnings.warn(
        "not checked, because this interpreter's grammar cannot read them "
        "(PEP 695 needs 3.12):\n" + names,
        stacklevel=1,
    )


def test_no_new_constructor_raise_sites():
    files = _source_files()
    assert files, f"no source files found under {_SRC}"
    found, skipped = _census(files)
    _warn_on_skipped(skipped)
    new = found - Counter(ALLOWED)
    assert not new, (
        "new constructor validation; move the check into a public validate_*() "
        "method and let the backend formatter opt in:\n"
        + "\n".join(f"  {key}: {count}" for key, count in sorted(new.items()))
    )


def test_the_scan_reaches_the_constructors():
    found, skipped = _census(_source_files())
    _warn_on_skipped(skipped)
    # The census must not pass by looking at nothing. 84 today; migrations may
    # only reduce it, so a loose floor is deliberate.
    assert sum(found.values()) > 50, f"only {sum(found.values())} constructor raises were seen"


def test_a_planted_new_site_is_detected(tmp_path: Path):
    label = "planted.py"
    planted = _keys_in_source(
        "class P:\n"
        "    def __init__(self, flag):\n"
        "        if flag:\n"
        "            raise ValueError('a brand new refusal')\n",
        label,
    )
    assert planted == [(label, "P", "ValueError", "a brand new refusal")]
    assert Counter(planted) - Counter(ALLOWED), "the planted offender must count as new"


def test_a_migrated_site_is_tolerated():
    """Removing known sites (the migration's direction) never fails the guard."""
    remaining = Counter({key: 1 for key in list(ALLOWED)[:5]})
    assert not remaining - Counter(ALLOWED)


def test_line_numbers_do_not_change_the_key():
    before = _keys_in_source(
        "class P:\n    def __init__(self, x):\n        raise ValueError('boom')\n",
        "moved.py",
    )
    after = _keys_in_source(
        "\n\n\nclass P:\n    def __init__(self, x):\n        raise ValueError('boom')\n",
        "moved.py",
    )
    assert before == after
