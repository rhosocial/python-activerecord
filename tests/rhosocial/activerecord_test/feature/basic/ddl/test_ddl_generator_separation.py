# tests/rhosocial/activerecord_test/feature/basic/ddl/test_ddl_generator_separation.py
"""Architecture guard: the DDL generator must stay behaviour-agnostic.

Plan: version-real-field-refactor (2026-08-31).  The optimistic-lock column
used to be special-cased in ``ModelSchemaGenerator._version_column``; it is
now a real field declared by ``OptimisticLockMixin``.  These tests pin the
separation of concerns so no behaviour-specific branch can creep back in.
"""

import ast
import inspect
import pathlib

from rhosocial.activerecord.base import ddl_generator

GENERATOR_PATH = pathlib.Path(inspect.getsourcefile(ddl_generator))


def test_no_version_or_optimistic_references():
    """No behaviour-specific tokens in the generator source."""
    src = GENERATOR_PATH.read_text(encoding="utf-8")
    lowered = src.lower()
    assert "optimistic" not in lowered
    assert "_ddl_extra_columns" not in lowered
    # Reading behaviour state off the *model* class is the coupling this
    # plan removed; the dialect's own server-version lookup is legitimate.
    assert 'getattr(model_class, "_version"' not in src
    assert 'getattr(cls, "_version"' not in src
    assert "_version_column" not in src


def test_no_private_attr_reads_from_model_classes():
    """The generator never reads behaviour state off the model class."""
    tree = ast.parse(GENERATOR_PATH.read_text(encoding="utf-8"))
    forbidden = {"_version", "_deleted", "_extra_columns"}
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and node.attr in forbidden:
            raise AssertionError(f"generator reads behaviour state: .{node.attr}")


def test_extensibility_is_protocol_based():
    """Any extension point must be a documented generic hook, not a name check.

    The generator may only consult protocols/annotations that any behaviour
    can implement equally (e.g. ``__table_field_constraints__``), never
    behaviour-specific names.
    """
    src = GENERATOR_PATH.read_text(encoding="utf-8")
    for name in ("optimisticlock", "softdelete", "timestampmixin"):
        assert name not in src.lower(), f"behaviour-specific name leaked: {name}"
