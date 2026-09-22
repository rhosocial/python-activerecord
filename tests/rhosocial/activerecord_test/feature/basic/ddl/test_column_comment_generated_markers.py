# tests/rhosocial/activerecord_test/feature/basic/ddl/test_column_comment_generated_markers.py
"""Declarative markers for column comments and generated columns (A5)."""

try:
    from typing import Annotated
except ImportError:  # Python 3.8
    from typing_extensions import Annotated

import pytest

from rhosocial.activerecord.base import UseComment, UseGeneratedColumn
from rhosocial.activerecord.base.ddl import TableDDLDeriver
from rhosocial.activerecord.backend.expression.core import Column
from rhosocial.activerecord.backend.expression.statements import (
    GeneratedColumnExpression,
    GeneratedColumnType,
)
from rhosocial.activerecord.backend.impl.dummy import DummyDialect
from rhosocial.activerecord.model import ActiveRecord


class Product(ActiveRecord):
    __table_name__ = "products"

    id: int
    price: float
    quantity: int
    total: Annotated[
        float,
        UseGeneratedColumn(
            lambda d: GeneratedColumnExpression(
                d,
                Column(d, "price") * Column(d, "quantity"),
                GeneratedColumnType.STORED,
            )
        ),
    ]
    note: Annotated[str, UseComment("a note")]


def test_comment_interface_reads_marker():
    assert Product.column_comment("note") == "a note"
    assert Product.column_comment("price") is None


def test_generated_interface_reads_marker():
    factory = Product.generated_column("total")
    assert callable(factory)
    assert Product.generated_column("price") is None


def test_create_table_renders_comment_and_generated_column():
    sql, _ = TableDDLDeriver(Product, DummyDialect()).create_table().to_sql()
    assert "COMMENT 'a note'" in sql
    assert 'GENERATED ALWAYS AS ("price" * "quantity") STORED' in sql


def test_comment_marker_validation():
    with pytest.raises(TypeError):
        UseComment(123)
    with pytest.raises(ValueError):
        UseComment("   ")


def test_generated_marker_validation():
    with pytest.raises(TypeError):
        UseGeneratedColumn(123)
