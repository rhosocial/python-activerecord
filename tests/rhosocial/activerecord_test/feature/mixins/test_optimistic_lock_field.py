# tests/rhosocial/activerecord_test/feature/mixins/test_optimistic_lock_field.py
"""Optimistic-lock real-field behaviour (plan: version-real-field-refactor).

Covers the framework-managed column contract:

* ``version`` is a real pydantic field — DDL, ``model_dump`` and validation
  flow through the generic paths with no generator special-casing;
* manual writes are rejected (BEFORE_UPDATE) and never enter dirty data;
* the UPDATE WHERE clause uses the committed-value snapshot, so tampering
  can neither break nor bypass the lock;
* customisation knobs: ``__version_column__`` (wired through the standard
  column-resolution protocol), ``__version_field__`` rename,
  ``__version_increment_by__``.
"""

import sys
import warnings

if sys.version_info >= (3, 9):
    from typing import Annotated
else:  # pragma: no cover - 3.8 compatibility
    from typing_extensions import Annotated

from typing import Optional

import pytest

from rhosocial.activerecord.backend.errors import DatabaseError
from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig
from rhosocial.activerecord.base.ddl_generator import ModelSchemaGenerator
from rhosocial.activerecord.field import (
    DefaultOptimisticLockMixin,
    IntegerPKMixin,
    OptimisticLockMixin,
)
from rhosocial.activerecord.model import ActiveRecord
from pydantic import Field

from rhosocial.activerecord.backend.expression.statements.ddl_table import (
    ColumnConstraintType,
)
from rhosocial.activerecord.base.fields import UseColumn, UseConstraint


def _make_backend():
    backend = SQLiteBackend(connection_config=SQLiteConnectionConfig(database=":memory:"))
    backend.connect()
    backend.introspect_and_adapt()
    return backend


def _register(model_class, backend, create: bool = True):
    sql, _ = ModelSchemaGenerator.generate(model_class, backend.dialect).to_sql()
    if create:
        backend.execute(sql)


def _fresh_model(backend, **class_kwargs):
    """Build a fresh model class per test to avoid cross-test state."""

    class Model(IntegerPKMixin, DefaultOptimisticLockMixin, ActiveRecord):
        __table_name__ = "lock_items"
        __backend__ = backend
        id: Optional[int] = None
        name: str

    Model.__name__ = f"LockModel_{id(Model)}"
    return Model


@pytest.fixture
def lock_backend():
    backend = _make_backend()
    yield backend
    backend.disconnect()


def test_version_flows_through_generic_paths(lock_backend):
    model = _fresh_model(lock_backend)
    _register(model, lock_backend)

    e = ModelSchemaGenerator.generate(model, lock_backend.dialect)
    names = [c.name for c in e.columns]
    assert "version" in names
    sql, _ = e.to_sql()
    assert '"version" INTEGER NOT NULL' in sql

    item = model(name="a")
    assert item.save() == 1
    assert item.version == 1
    assert "version" in item.model_dump()

    item.name = "b"
    assert item.save() == 1
    assert item.version == 2
    fresh = model.find_one(item.id)
    assert fresh.version == 2


def test_manual_version_write_rejected(lock_backend):
    model = _fresh_model(lock_backend)
    _register(model, lock_backend)

    item = model(name="a")
    item.save()

    item.version = 999
    with pytest.raises(DatabaseError, match="managed by OptimisticLockMixin"):
        item.save()

    # Database untouched by the rejected attempt.
    fresh = model.find_one(item.id)
    assert fresh.version == 1


def test_stale_snapshot_conflicts(lock_backend):
    model = _fresh_model(lock_backend)
    _register(model, lock_backend)

    item = model(name="a")
    item.save()

    other = model.find_one(item.id)
    other.name = "edited-elsewhere"
    other.save()  # version -> 2 in DB

    item.name = "edited-stale"
    with pytest.raises(DatabaseError, match="updated by another process"):
        item.save()


def test_insert_normalises_seeded_version(lock_backend):
    model = _fresh_model(lock_backend)
    _register(model, lock_backend)

    item = model(name="a", version=999)
    item.save()
    assert item.version == 1
    assert model.find_one(item.id).version == 1


def test_base_mixin_requires_declared_field(lock_backend):
    """Base OptimisticLockMixin declares no field — missing one fails fast."""
    class NoField(IntegerPKMixin, OptimisticLockMixin, ActiveRecord):
        __table_name__ = "no_field"
        __backend__ = lock_backend
        id: Optional[int] = None
        name: str

    with pytest.raises(TypeError, match="__version_field__"):
        NoField(name="x")


def test_base_mixin_with_custom_field_name(lock_backend):
    """Base mixin + self-declared field: no redeclaration, no shadow warning."""
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")

        class Article(OptimisticLockMixin, ActiveRecord):
            __table_name__ = "articles"
            __backend__ = lock_backend
            __version_field__ = "row_version"
            __version_increment_by__ = 2
            id: Optional[int] = None
            name: str
            row_version: Annotated[
                int, UseColumn("row_ver"), UseConstraint(ColumnConstraintType.NOT_NULL)
            ] = Field(default=1, ge=1)

    shadow = [w for w in caught if "shadow" in str(w.message).lower()]
    assert not shadow

    sql, _ = ModelSchemaGenerator.generate(Article, lock_backend.dialect).to_sql()
    assert '"row_ver" INTEGER NOT NULL' in sql
    lock_backend.execute(sql)

    article = Article(name="a")
    article.save()
    assert article.row_version == 1
    article.name = "b"
    article.save()
    assert article.row_version == 3

    # The old name is gone: pydantic rejects writes to unknown attributes.
    with pytest.raises(ValueError, match='no field "version"'):
        article.version = 99
    article.name = "c"
    article.save()
    assert Article.find_one(article.id).row_version == 5
