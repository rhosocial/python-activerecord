import pytest
from decimal import Decimal
from typing import ClassVar, Optional, Dict, Type

from rhosocial.activerecord.model import ActiveRecord, AsyncActiveRecord
from rhosocial.activerecord.field import CompositePKMixin, IntegerPKMixin, TimestampMixin
from rhosocial.activerecord.base.field_proxy import FieldProxy
from rhosocial.activerecord.relation import HasMany, BelongsTo, HasOne
from rhosocial.activerecord.backend.impl.sqlite import SQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.backend.async_backend import AsyncSQLiteBackend
from rhosocial.activerecord.backend.impl.sqlite.config import SQLiteConnectionConfig


class OrderItem(CompositePKMixin, ActiveRecord):
    __table_name__ = "order_items"
    __primary_key__ = ("order_id", "product_id")
    c: ClassVar[FieldProxy] = FieldProxy()

    order_id: int
    product_id: int
    quantity: int
    price: Decimal = Decimal("0.00")


class AsyncOrderItem(CompositePKMixin, AsyncActiveRecord):
    __table_name__ = "order_items"
    __primary_key__ = ("order_id", "product_id")
    c: ClassVar[FieldProxy] = FieldProxy()

    order_id: int
    product_id: int
    quantity: int
    price: Decimal = Decimal("0.00")


class Order(IntegerPKMixin, TimestampMixin, ActiveRecord):
    __table_name__ = "orders"

    id: Optional[int] = None
    user_id: int
    total: Decimal = Decimal("0.00")


class AsyncOrder(IntegerPKMixin, TimestampMixin, AsyncActiveRecord):
    __table_name__ = "orders"

    id: Optional[int] = None
    user_id: int
    total: Decimal = Decimal("0.00")


CREATE_TABLES_SQL = """
CREATE TABLE IF NOT EXISTS order_items (
    order_id INTEGER NOT NULL,
    product_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL DEFAULT 1,
    price DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    PRIMARY KEY (order_id, product_id)
);
CREATE TABLE IF NOT EXISTS orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    total DECIMAL(10,2) NOT NULL DEFAULT 0.00,
    created_at TEXT,
    updated_at TEXT
);
"""


@pytest.fixture(scope="function")
def backend_config():
    return SQLiteConnectionConfig(database=":memory:")


@pytest.fixture(scope="function")
def setup_database(backend_config):
    OrderItem.configure(backend_config, SQLiteBackend)
    backend = OrderItem.backend()
    for stmt in CREATE_TABLES_SQL.strip().split(";"):
        s = stmt.strip()
        if s:
            backend.execute(s + ";")
    return backend


@pytest.fixture(scope="function")
def order_item_class(setup_database):
    return OrderItem


@pytest.fixture(scope="function")
async def async_order_item_class(backend_config):
    await AsyncOrderItem.configure(backend_config, AsyncSQLiteBackend)
    backend = AsyncOrderItem.backend()
    for stmt in CREATE_TABLES_SQL.strip().split(";"):
        s = stmt.strip()
        if s:
            await backend.execute(s + ";")
    yield AsyncOrderItem
    await backend.disconnect()


@pytest.fixture(scope="function")
def seeded_items(order_item_class):
    items = [
        order_item_class(order_id=1, product_id=1, quantity=2, price=Decimal("10.00")),
        order_item_class(order_id=1, product_id=2, quantity=1, price=Decimal("20.00")),
        order_item_class(order_id=2, product_id=1, quantity=5, price=Decimal("15.00")),
    ]
    order_item_class.bulk_create(items)
    return items
