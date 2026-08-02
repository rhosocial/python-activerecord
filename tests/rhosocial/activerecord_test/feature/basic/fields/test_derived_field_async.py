# src/rhosocial/activerecord/testsuite/feature/basic/fields/test_derived_field_async.py
import pytest
from typing import ClassVar, Optional
from typing_extensions import Annotated

from rhosocial.activerecord.base import DerivedField, UseColumn
from rhosocial.activerecord.model import ActiveRecord
from rhosocial.activerecord.backend.expression import Column, Literal


class TestAsyncDerivedFieldDeclaration:

    async def test_derived_fields_registered(self, async_product_class):
        assert "discounted_price" in async_product_class.__derived_fields__
        assert "total_value" in async_product_class.__derived_fields__

    async def test_descriptor_class_access(self, async_product_class):
        assert isinstance(async_product_class.discounted_price, DerivedField)

    async def test_derived_field_with_static_expression(self, async_product_class):
        """Test DerivedField constructed with a pre-built expression object (non-callable path)."""
        dialect = async_product_class.backend().dialect
        static_expr = Column(dialect, "price") * Literal(dialect, 2)
        df = DerivedField(static_expr)
        resolved = df.resolve(dialect)
        assert resolved is static_expr

    async def test_descriptor_instance_default_none(self, async_product_class):
        p = async_product_class(name="x", price=10.0, quantity=1)
        assert p.discounted_price is None
        assert p.total_value is None

    async def test_derived_field_names_mapping(self, async_product_class):
        names = async_product_class.__derived_field_names__
        df = async_product_class.__derived_fields__["discounted_price"]
        assert names[id(df)] == "discounted_price"


class TestAsyncDerivedFieldQuery:

    async def _insert(self, Model, name, price, quantity):
        p = Model(name=name, price=price, quantity=quantity)
        await p.save()
        return p

    async def test_find_all_derived_true(self, async_product_class):
        await self._insert(async_product_class, "A", 100.0, 5)
        results = await async_product_class.find_all(derived=True)
        assert len(results) == 1
        assert results[0].discounted_price == pytest.approx(90.0)
        assert results[0].total_value == pytest.approx(500.0)

    async def test_find_all_derived_list_by_name(self, async_product_class):
        await self._insert(async_product_class, "B", 50.0, 3)
        results = await async_product_class.find_all(derived=["total_value"])
        assert len(results) == 1
        assert results[0].total_value == pytest.approx(150.0)
        assert results[0].discounted_price is None

    async def test_find_all_derived_list_all(self, async_product_class):
        await self._insert(async_product_class, "C", 200.0, 2)
        results = await async_product_class.find_all(derived=["discounted_price", "total_value"])
        assert results[0].discounted_price == pytest.approx(180.0)
        assert results[0].total_value == pytest.approx(400.0)

    async def test_find_one_derived(self, async_product_class):
        p = await self._insert(async_product_class, "D", 80.0, 4)
        result = await async_product_class.find_one(p.id, derived=True)
        assert result.discounted_price == pytest.approx(72.0)

    async def test_find_one_or_fail_derived(self, async_product_class):
        p = await self._insert(async_product_class, "D2", 80.0, 4)
        result = await async_product_class.find_one_or_fail(p.id, derived=True)
        assert result.discounted_price == pytest.approx(72.0)
        assert result.total_value == pytest.approx(320.0)

    async def test_find_one_or_fail_derived_list(self, async_product_class):
        p = await self._insert(async_product_class, "D3", 80.0, 4)
        result = await async_product_class.find_one_or_fail(p.id, derived=["discounted_price", "total_value"])
        assert result.discounted_price == pytest.approx(72.0)
        assert result.total_value == pytest.approx(320.0)

    async def test_find_all_derived_false_default(self, async_product_class):
        await self._insert(async_product_class, "E", 60.0, 1)
        results = await async_product_class.find_all()
        assert results[0].discounted_price is None
        assert results[0].total_value is None

    async def test_find_all_derived_all(self, async_product_class):
        await self._insert(async_product_class, "F", 100.0, 5)
        results = await async_product_class.find_all(derived="all")
        assert len(results) == 1
        assert results[0].discounted_price == pytest.approx(90.0)
        assert results[0].total_value == pytest.approx(500.0)

    async def test_find_one_derived_all(self, async_product_class):
        p = await self._insert(async_product_class, "G", 80.0, 4)
        result = await async_product_class.find_one(p.id, derived="all")
        assert result.discounted_price == pytest.approx(72.0)
        assert result.total_value == pytest.approx(320.0)

    async def test_find_one_or_fail_derived_all(self, async_product_class):
        p = await self._insert(async_product_class, "H", 60.0, 3)
        result = await async_product_class.find_one_or_fail(p.id, derived="all")
        assert result.discounted_price == pytest.approx(54.0)
        assert result.total_value == pytest.approx(180.0)


class TestAsyncDerivedFieldFormA:
    """Tests for Form A declaration: ClassVar[DerivedField] = DerivedField(...)."""

    async def test_form_a_fields_registered(self, async_product_form_a_class):
        assert "discounted_price" in async_product_form_a_class.__derived_fields__
        assert "total_value" in async_product_form_a_class.__derived_fields__

    async def test_form_a_query(self, async_product_form_a_class):
        p = async_product_form_a_class(name="FA", price=100.0, quantity=3)
        await p.save()
        results = await async_product_form_a_class.find_all(derived=True)
        assert results[0].discounted_price == pytest.approx(90.0)
        assert results[0].total_value == pytest.approx(300.0)

    async def test_form_a_source_id_mapping(self, async_product_form_a_class):
        df = async_product_form_a_class.__derived_fields__["discounted_price"]
        assert df._source_id is not None
        assert async_product_form_a_class.__derived_field_names__[df._source_id] == "discounted_price"


class TestAsyncDerivedFieldDictForm:
    """Tests for derived=dict form."""

    async def _insert(self, Model, name, price, quantity):
        p = Model(name=name, price=price, quantity=quantity)
        await p.save()
        return p

    async def test_derived_dict_with_lambda(self, async_product_class):
        await self._insert(async_product_class, "D1", 100.0, 4)
        results = await async_product_class.find_all(
            derived={"my_discount": lambda d: Column(d, "price") * Literal(d, 0.8)}
        )
        assert results[0].__dict__["my_discount"] == pytest.approx(80.0)

    async def test_derived_dict_with_derived_field_instance(self, async_product_class):
        await self._insert(async_product_class, "D2", 50.0, 2)
        df = async_product_class.__derived_fields__["total_value"]
        results = await async_product_class.find_all(
            derived={"tv": df}
        )
        assert results[0].__dict__["tv"] == pytest.approx(100.0)


    async def test_derived_dict_with_expression_object(self, async_product_class):
        await self._insert(async_product_class, "D3", 80.0, 5)
        dialect = async_product_class.backend().dialect
        expr = Column(dialect, "price") * Literal(dialect, 0.5)
        results = await async_product_class.find_all(
            derived={"half_price": expr}
        )
        assert results[0].__dict__["half_price"] == pytest.approx(40.0)


class TestAsyncDerivedFieldLookupByInstance:
    """Tests for derived=[DerivedField instance] form."""

    async def _insert(self, Model, name, price, quantity):
        p = Model(name=name, price=price, quantity=quantity)
        await p.save()
        return p

    async def test_lookup_by_derived_field_instance(self, async_product_class):
        await self._insert(async_product_class, "L1", 200.0, 1)
        df = async_product_class.__derived_fields__["discounted_price"]
        results = await async_product_class.find_all(derived=[df])
        assert results[0].discounted_price == pytest.approx(180.0)


class TestAsyncExtraDerived:

    async def _insert(self, Model, name, price, quantity):
        p = Model(name=name, price=price, quantity=quantity)
        await p.save()
        return p

    async def test_extra_derived_basic(self, async_product_class):
        await self._insert(async_product_class, "F", 100.0, 10)
        results = await async_product_class.find_all(
            extra_derived={"triple_price": lambda d: Column(d, "price") * Literal(d, 3)}
        )
        assert len(results) == 1
        assert results[0].__dict__["triple_price"] == pytest.approx(300.0)

    async def test_extra_derived_conflict_raises(self, async_product_class):
        await self._insert(async_product_class, "G", 50.0, 2)
        with pytest.raises(ValueError, match="conflicts with a declared derived field"):
            await async_product_class.find_all(
                extra_derived={"discounted_price": lambda d: Column(d, "price") * Literal(d, 0.5)}
            )

    async def test_derived_and_extra_derived_together(self, async_product_class):
        await self._insert(async_product_class, "H", 40.0, 5)
        results = await async_product_class.find_all(
            derived=True,
            extra_derived={"double_qty": lambda d: Column(d, "quantity") * Literal(d, 2)}
        )
        assert results[0].discounted_price == pytest.approx(36.0)
        assert results[0].total_value == pytest.approx(200.0)
        assert results[0].__dict__["double_qty"] == pytest.approx(10.0)


class TestAsyncDerivedFieldWithProxy:
    """Tests for DerivedField using FieldProxy in expressions."""

    async def _insert(self, Model, name, price, quantity):
        p = Model(name=name, price=price, quantity=quantity)
        await p.save()
        return p

    async def test_proxy_derived_query(self, async_product_with_proxy_class):
        await self._insert(async_product_with_proxy_class, "P1", 100.0, 4)
        results = await async_product_with_proxy_class.find_all(derived=True)
        assert results[0].discounted_price == pytest.approx(90.0)
        assert results[0].total_value == pytest.approx(400.0)

    async def test_proxy_derived_all_fields(self, async_product_with_proxy_class):
        await self._insert(async_product_with_proxy_class, "P2", 200.0, 3)
        results = await async_product_with_proxy_class.find_all(
            derived=["discounted_price", "total_value"]
        )
        assert results[0].discounted_price == pytest.approx(180.0)
        assert results[0].total_value == pytest.approx(600.0)

    async def test_proxy_derived_not_in_model_fields(self, async_product_with_proxy_class):
        assert "discounted_price" not in async_product_with_proxy_class.model_fields
        assert "total_value" not in async_product_with_proxy_class.model_fields

    async def test_proxy_derived_not_in_dirty_fields(self, async_product_with_proxy_class):
        await self._insert(async_product_with_proxy_class, "P3", 50.0, 2)
        instance = (await async_product_with_proxy_class.find_all(derived=True))[0]
        instance.__dict__["discounted_price"] = 999.0
        assert "discounted_price" not in instance.dirty_fields

    async def test_proxy_derived_read_only(self, async_product_with_proxy_class):
        await self._insert(async_product_with_proxy_class, "P4", 80.0, 1)
        instance = (await async_product_with_proxy_class.find_all(derived=True))[0]
        with pytest.raises(AttributeError):
            instance.discounted_price = 123.0

    async def test_proxy_derived_not_saved_to_db(self, async_product_with_proxy_class):
        p = await self._insert(async_product_with_proxy_class, "P5", 60.0, 2)
        instance = await async_product_with_proxy_class.find_one(p.id, derived=True)
        assert instance.discounted_price == pytest.approx(54.0)
        instance.name = "P5_modified"
        await instance.save()
        fresh = await async_product_with_proxy_class.find_one(p.id, derived=True)
        assert fresh.name == "P5_modified"
        assert fresh.discounted_price == pytest.approx(54.0)


class TestAsyncDerivedFieldWithUseColumnAndAdapter:
    """Tests for DerivedField with UseColumn and UseAdapter annotations."""

    async def _insert(self, Model, name, price, quantity):
        p = Model(name=name, price=price, quantity=quantity)
        await p.save()
        return p

    async def test_use_column_alias_in_select(self, async_product_with_column_and_adapter_class):
        """UseColumn controls the SELECT alias; result maps back to Python field name."""
        await self._insert(async_product_with_column_and_adapter_class, "UC1", 100.0, 5)
        results = await async_product_with_column_and_adapter_class.find_all(derived=True)
        # discounted_price has UseColumn("disc") — alias is "disc" in SQL,
        # but the value is accessible via the Python attribute name
        assert results[0].discounted_price == pytest.approx(90.0)
        assert results[0].total_int == 500

    async def test_use_adapter_from_database(self, async_product_with_column_and_adapter_class):
        """UseAdapter applies from_database conversion on the derived field value."""
        await self._insert(async_product_with_column_and_adapter_class, "UA1", 33.3, 3)
        results = await async_product_with_column_and_adapter_class.find_all(derived=["total_int"])
        # 33.3 * 3 = 99.9, adapter rounds to int → 100
        assert results[0].total_int == 100
        assert isinstance(results[0].total_int, int)

    async def test_use_column_field_not_in_model_fields(self, async_product_with_column_and_adapter_class):
        assert "discounted_price" not in async_product_with_column_and_adapter_class.model_fields
        assert "total_int" not in async_product_with_column_and_adapter_class.model_fields

    async def test_use_column_column_name_stored(self, async_product_with_column_and_adapter_class):
        df = async_product_with_column_and_adapter_class.__derived_fields__["discounted_price"]
        assert df.column_name == "disc"

    async def test_use_adapter_stored(self, async_product_with_column_and_adapter_class):
        df = async_product_with_column_and_adapter_class.__derived_fields__["total_int"]
        assert df.adapter is not None

    async def test_use_column_and_adapter_together(self, async_product_with_column_and_adapter_class):
        """Both UseColumn and UseAdapter can coexist on the same derived field."""
        await self._insert(async_product_with_column_and_adapter_class, "CA1", 50.0, 4)
        results = await async_product_with_column_and_adapter_class.find_all(
            derived=["discounted_price", "total_int"]
        )
        assert results[0].discounted_price == pytest.approx(45.0)
        assert results[0].total_int == 200


class TestAsyncDerivedFieldColumnConflict:
    """Tests that column name conflicts between regular and derived fields are detected."""

    async def test_use_column_conflict_raises(self):
        """UseColumn on derived field must not duplicate a regular field's column name."""
        with pytest.raises(TypeError, match="conflicts with a regular field's column name"):
            class ConflictModel(ActiveRecord):
                __table_name__ = "conflict"
                id: Optional[int] = None
                discount_rate: Annotated[float, UseColumn("disc")]
                discounted: ClassVar[Annotated[float, DerivedField(
                    lambda d: Column(d, "price") * Literal(d, 0.9),
                ), UseColumn("disc")]]

    async def test_use_column_no_conflict_different_names(self):
        """Different column names should not conflict."""
        class NoConflict(ActiveRecord):
            __table_name__ = "no_conflict"
            id: Optional[int] = None
            discount_rate: Annotated[float, UseColumn("rate")]
            discounted: ClassVar[Annotated[float, DerivedField(
                lambda d: Column(d, "price") * Literal(d, 0.9),
            ), UseColumn("disc")]]

        assert NoConflict.__derived_fields__["discounted"].column_name == "disc"
