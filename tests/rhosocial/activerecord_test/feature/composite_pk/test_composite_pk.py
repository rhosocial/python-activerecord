import pytest
from decimal import Decimal

from rhosocial.activerecord.backend.errors import RecordNotFound

pytestmark = [pytest.mark.feature, pytest.mark.basic]


class TestCompositePKModel:
    def test_is_composite_pk(self, order_item_class):
        assert order_item_class.is_composite_pk() is True

    def test_primary_key_columns(self, order_item_class):
        assert order_item_class.primary_key_columns() == ("order_id", "product_id")

    def test_primary_key_field(self, order_item_class):
        result = order_item_class.primary_key_field()
        assert result == ("order_id", "product_id")

    def test_primary_key_fields(self, order_item_class):
        assert order_item_class.primary_key_fields() == ("order_id", "product_id")

    def test_primary_key(self, order_item_class):
        assert order_item_class.primary_key() == ("order_id", "product_id")

    def test_pk_auto_generated(self, order_item_class):
        assert order_item_class.__pk_auto_generated__ is False


class TestCompositePKCRUD:
    def test_create(self, order_item_class):
        item = order_item_class(order_id=1, product_id=42, quantity=3, price=Decimal("19.99"))
        rows = item.save()
        assert rows == 1
        assert item.is_new_record is False

    def test_find_one_by_dict(self, order_item_class):
        order_item_class(order_id=1, product_id=42, quantity=3, price=Decimal("19.99")).save()
        found = order_item_class.find_one({"order_id": 1, "product_id": 42})
        assert found is not None
        assert found.order_id == 1
        assert found.product_id == 42
        assert found.quantity == 3

    def test_find_one_by_tuple(self, order_item_class):
        order_item_class(order_id=1, product_id=42, quantity=3, price=Decimal("19.99")).save()
        found = order_item_class.find_one((1, 42))
        assert found is not None
        assert found.order_id == 1
        assert found.product_id == 42

    def test_find_one_not_found(self, order_item_class):
        result = order_item_class.find_one({"order_id": 999, "product_id": 999})
        assert result is None

    def test_find_one_or_fail(self, order_item_class):
        order_item_class(order_id=1, product_id=1, quantity=1).save()
        found = order_item_class.find_one_or_fail({"order_id": 1, "product_id": 1})
        assert found is not None
        with pytest.raises(RecordNotFound):
            order_item_class.find_one_or_fail({"order_id": 999, "product_id": 999})

    def test_update(self, order_item_class):
        item = order_item_class(order_id=1, product_id=42, quantity=3, price=Decimal("19.99"))
        item.save()
        item.quantity = 5
        rows = item.save()
        assert rows == 1
        item.refresh()
        assert item.quantity == 5

    def test_delete(self, order_item_class):
        item = order_item_class(order_id=1, product_id=42, quantity=3)
        item.save()
        rows = item.delete()
        assert rows == 1
        assert order_item_class.find_one({"order_id": 1, "product_id": 42}) is None

    def test_refresh(self, order_item_class):
        item = order_item_class(order_id=1, product_id=42, quantity=3, price=Decimal("10.00"))
        item.save()
        item.quantity = 999
        item.refresh()
        assert item.quantity == 3
        assert item.price == Decimal("10.00")

    def test_is_new_record(self, order_item_class):
        item = order_item_class(order_id=1, product_id=42, quantity=3)
        assert item.is_new_record is True
        item.save()
        assert item.is_new_record is False

    def test_create_missing_pk_raises(self, order_item_class):
        from pydantic import ValidationError
        with pytest.raises(ValidationError):
            order_item_class(order_id=1, quantity=3)


class TestCompositePKBulk:
    def test_bulk_create(self, order_item_class):
        items = [
            order_item_class(order_id=1, product_id=1, quantity=2, price=Decimal("10.00")),
            order_item_class(order_id=1, product_id=2, quantity=1, price=Decimal("20.00")),
            order_item_class(order_id=2, product_id=1, quantity=5, price=Decimal("15.00")),
        ]
        created = order_item_class.bulk_create(items)
        assert len(created) == 3
        assert created[0].order_id == 1
        assert created[0].product_id == 1

    def test_find_all(self, seeded_items, order_item_class):
        all_items = order_item_class.find_all()
        assert len(all_items) == 3

    def test_find_all_with_list(self, seeded_items, order_item_class):
        items = order_item_class.find_all([{"order_id": 1, "product_id": 1}, (1, 2)])
        assert len(items) == 2

    def test_find_all_empty_list(self, order_item_class):
        items = order_item_class.find_all([])
        assert items == []

    def test_bulk_delete(self, seeded_items, order_item_class):
        items = order_item_class.find_all([{"order_id": 1, "product_id": 1}, (1, 2)])
        order_item_class.bulk_delete(items)
        remaining = order_item_class.find_all()
        assert len(remaining) == 1

    def test_bulk_update(self, seeded_items, order_item_class):
        items = order_item_class.find_all([{"order_id": 1, "product_id": 1}, (1, 2)])
        for item in items:
            item.quantity = 99
        order_item_class.bulk_update(items, fields=["quantity"])
        refreshed = order_item_class.find_all([{"order_id": 1, "product_id": 1}, (1, 2)])
        for r in refreshed:
            assert r.quantity == 99


class TestCompositePKQuery:
    def test_query_where_dict(self, seeded_items, order_item_class):
        results = order_item_class.query().where(
            order_item_class.c.order_id == 1
        ).all()
        assert len(results) == 2

    def test_query_where_chain(self, seeded_items, order_item_class):
        from rhosocial.activerecord.backend.expression.core import Column
        backend = order_item_class.backend()
        results = order_item_class.query().where(
            Column(backend.dialect, "order_id") == 1
        ).where(
            Column(backend.dialect, "quantity") > 1
        ).all()
        assert len(results) == 1
        assert results[0].product_id == 1


class TestCompositePKRelation:
    def test_belongs_to(self, order_item_class):
        pass


class TestAsyncCompositePKCRUD:
    @pytest.mark.asyncio
    async def test_async_create(self, async_order_item_class):
        item = async_order_item_class(order_id=1, product_id=42, quantity=3, price=Decimal("19.99"))
        rows = await item.save()
        assert rows == 1
        assert item.is_new_record is False

    @pytest.mark.asyncio
    async def test_async_find_one(self, async_order_item_class):
        item = async_order_item_class(order_id=1, product_id=42, quantity=3, price=Decimal("19.99"))
        await item.save()
        found = await async_order_item_class.find_one({"order_id": 1, "product_id": 42})
        assert found is not None
        assert found.order_id == 1
        assert found.product_id == 42

    @pytest.mark.asyncio
    async def test_async_find_one_tuple(self, async_order_item_class):
        item = async_order_item_class(order_id=1, product_id=42, quantity=3)
        await item.save()
        found = await async_order_item_class.find_one((1, 42))
        assert found is not None

    @pytest.mark.asyncio
    async def test_async_update(self, async_order_item_class):
        item = async_order_item_class(order_id=1, product_id=42, quantity=3)
        await item.save()
        item.quantity = 5
        rows = await item.save()
        assert rows == 1
        await item.refresh()
        assert item.quantity == 5

    @pytest.mark.asyncio
    async def test_async_delete(self, async_order_item_class):
        item = async_order_item_class(order_id=1, product_id=42, quantity=3)
        await item.save()
        rows = await item.delete()
        assert rows == 1

    @pytest.mark.asyncio
    async def test_async_find_all(self, async_order_item_class):
        items = [
            async_order_item_class(order_id=1, product_id=1, quantity=2),
            async_order_item_class(order_id=1, product_id=2, quantity=1),
        ]
        await async_order_item_class.bulk_create(items)
        all_items = await async_order_item_class.find_all()
        assert len(all_items) == 2
