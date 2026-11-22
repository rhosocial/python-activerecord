# tests/rhosocial/activerecord_test/feature/backend/adapters/test_type_adaption.py
"""The two-level adapter scheme, and the mixin that applies it.

``base/type_adaption.py`` holds four things under test here:

1. **The core base table** (``CORE_DEFAULT_TYPE_MAPPINGS``): what a
   backend-agnostic driver is expected to accept for the common Python types.
2. **The backend layer** (``merge_adapter_suggestions``): a backend merges its
   own pairs onto that base, resolved through *its* registry, so a pair it did
   not register is never suggested.
3. **The lookup contract** (``prepare_parameters`` / ``adapt_row_types``): the
   pair ``(adapter, driver type)`` is what a caller passes in, and both
   directions honour it -- including ``None`` and the absent-adapter case.
4. **The inventory** (``get_type_adapters``): what exists, deduplicated and
   ordered, with no suggestion semantics attached.

No backend instance is needed: a minimal host supplies the two attributes the
mixin reads (``adapter_registry`` and ``logger``), so the tests exercise the
generic layer on its own.
"""
from rhosocial.activerecord.backend.suggestion.definitions import DataAdapterSuggestion  # noqa: E402


import datetime
import logging
import uuid
from decimal import Decimal
from enum import Enum

import pytest

from rhosocial.activerecord.backend.adapters.portable import PORTABLE_TYPE_MAPPINGS as CORE_DEFAULT_TYPE_MAPPINGS
from rhosocial.activerecord.backend.suggestion.definitions import DataAdapterSuggestion  # noqa: E402
from rhosocial.activerecord.backend.base.type_adaption import (
    TypeAdaptionMixin,
    merge_adapter_suggestions,
    sort_and_deduplicate_adapters,
)
from rhosocial.activerecord.backend.type_adapter import (
    BooleanAdapter,
    DateTimeAdapter,
    DecimalAdapter,
    EnumAdapter,
    JSONAdapter,
    SQLTypeAdapter,
    UUIDAdapter,
)
from rhosocial.activerecord.backend.type_registry import TypeRegistry


class _Host(TypeAdaptionMixin):
    """A minimal backend host; reuses the portable helper for its suggestions."""

    def __init__(self):
        self.adapter_registry = TypeRegistry()
        self.logger = logging.getLogger("rhosocial.activerecord.tests.type_adaption")

    def suggest_data_adapters(self):
        from rhosocial.activerecord.backend.adapters.portable import PORTABLE_TYPE_MAPPINGS
        return DataAdapterSuggestion(table=merge_adapter_suggestions({}, PORTABLE_TYPE_MAPPINGS, self.adapter_registry))


def _registered(*adapters: SQLTypeAdapter) -> TypeRegistry:
    """A registry holding every pair the given adapters claim."""
    registry = TypeRegistry()
    for adapter in adapters:
        for py_type, db_types in adapter.supported_types.items():
            for db_type in db_types:
                registry.register(adapter, py_type, db_type)
    return registry


def _keys(adapters) -> list:
    """The identity the inventory sorts and deduplicates by."""
    return [(type(adapter).__module__, type(adapter).__qualname__) for adapter in adapters]


# ---------------------------------------------------------------------------
# 1. The core base table
# ---------------------------------------------------------------------------


def test_the_core_table_names_the_common_types_and_their_driver_targets():
    """Written out rather than read back, because this table *is* the
    framework's claim about a generic driver: a change to it is a change to
    what every backend starts from."""
    assert CORE_DEFAULT_TYPE_MAPPINGS == (
        (bool, int),
        (datetime.datetime, str),
        (datetime.date, str),
        (datetime.time, str),
        (Decimal, float),
        (uuid.UUID, str),
        (dict, str),
        (list, str),
        (Enum, str),
    )


def test_the_core_table_leaves_the_driver_native_types_out():
    """``str`` / ``int`` / ``float`` / ``bytes`` are absent on purpose: their
    absence means "pass through untouched", which is not a pairing to declare."""
    py_types = {py_type for py_type, _ in CORE_DEFAULT_TYPE_MAPPINGS}
    assert {str, int, float, bytes}.isdisjoint(py_types)


# ---------------------------------------------------------------------------
# 2. The backend layer: merging onto the base
# ---------------------------------------------------------------------------


def test_a_merge_returns_a_new_mapping_and_leaves_the_base_alone():
    base_adapter = BooleanAdapter()
    base = {bool: (base_adapter, int)}
    registry = _registered(UUIDAdapter())

    merged = merge_adapter_suggestions(base, [(uuid.UUID, str)], registry)

    assert merged is not base
    assert base == {bool: (base_adapter, int)}
    assert set(merged) == {bool, uuid.UUID}


def test_an_override_wins_for_the_same_python_type():
    """The backend decides what its driver accepts; the core row for the same
    Python type is replaced, not kept beside it."""
    core = JSONAdapter()
    base = {dict: (core, str)}
    backend = JSONAdapter()
    registry = _registered(backend)

    merged = merge_adapter_suggestions(base, [(dict, str)], registry)

    assert merged[dict] == (backend, str)
    assert merged[dict][0] is not core


def test_an_override_with_no_registered_adapter_changes_nothing():
    """Resolving through *this* backend's registry is the point: a pair the
    backend never registered cannot be suggested."""
    base_adapter = DateTimeAdapter()
    base = {datetime.datetime: (base_adapter, str)}
    registry = _registered()

    merged = merge_adapter_suggestions(base, [(datetime.datetime, str)], registry)

    assert merged == base
    assert merged is not base


# ---------------------------------------------------------------------------
# 3. The registration the mixin performs for itself
# ---------------------------------------------------------------------------


def test_the_default_registration_covers_the_core_pairs_it_has_adapters_for():
    host = _Host()
    host._register_default_adapters()
    registry = host.adapter_registry

    assert isinstance(registry.get_adapter(bool, int), BooleanAdapter)
    assert isinstance(registry.get_adapter(datetime.datetime, str), DateTimeAdapter)
    assert isinstance(registry.get_adapter(datetime.date, str), DateTimeAdapter)
    assert isinstance(registry.get_adapter(datetime.time, str), DateTimeAdapter)
    assert isinstance(registry.get_adapter(Decimal, float), DecimalAdapter)
    assert isinstance(registry.get_adapter(uuid.UUID, str), UUIDAdapter)
    assert isinstance(registry.get_adapter(dict, str), JSONAdapter)
    assert isinstance(registry.get_adapter(list, str), JSONAdapter)
    assert isinstance(registry.get_adapter(Enum, str), EnumAdapter)


def test_the_enum_pair_is_core_owned_and_backends_override_it():
    """**The declaration and the implementation agree.** ``CORE_DEFAULT_TYPE_MAPPINGS``
    lists ``(Enum, str)``, so ``EnumAdapter`` claims the pair and the generic
    layer resolves it; a backend whose server spells enums differently
    registers its own adapter over the pair (PostgreSQL, MySQL, MariaDB, Oracle
    and ClickHouse all do, with ``allow_override=True``).

    If the generic claim is ever withdrawn, this test fails on purpose.
    """
    host = _Host()
    host._register_default_adapters()

    assert EnumAdapter().supported_types == {Enum: {str, int}}
    assert isinstance(host.adapter_registry.get_adapter(Enum, str), EnumAdapter)
    assert isinstance(host.adapter_registry.get_adapter(Enum, int), EnumAdapter)


def test_the_suggestions_resolve_exactly_what_the_registry_holds():
    host = _Host()
    host._register_default_adapters()

    suggestions = host.suggest_data_adapters().table

    # The core table has nine rows and every one of them resolves.
    assert set(suggestions) == {
        bool,
        datetime.datetime,
        datetime.date,
        datetime.time,
        Decimal,
        uuid.UUID,
        dict,
        list,
        Enum,
    }
    assert isinstance(suggestions[bool][0], BooleanAdapter)
    assert suggestions[bool][1] is int
    assert suggestions[Decimal][1] is float


def test_a_backend_with_an_empty_registry_suggests_nothing():
    """No adapter is not an error: it is a backend that declined every core
    pairing, and the lookup returns an empty mapping rather than raising."""
    assert _Host().suggest_data_adapters().table == {}


# ---------------------------------------------------------------------------
# 4. The inventory
# ---------------------------------------------------------------------------


def test_the_inventory_deduplicates_by_class_and_orders_deterministically():
    host = _Host()
    host._register_default_adapters()

    inventory = host.get_type_adapters()
    keys = _keys(inventory)

    assert keys == sorted(set(keys))
    assert {qualname for _, qualname in keys} == {
        "BooleanAdapter",
        "DateTimeAdapter",
        "DecimalAdapter",
        "EnumAdapter",
        "JSONAdapter",
        "UUIDAdapter",
    }


def test_each_inventory_call_is_a_new_list():
    host = _Host()
    host._register_default_adapters()

    first = host.get_type_adapters()
    second = host.get_type_adapters()

    assert first is not second
    first.append(object())
    # Adding to the first copy must not change what the host answers next.
    assert _keys(host.get_type_adapters()) == _keys(second)


def test_the_sort_helper_keeps_the_first_instance_of_a_class():
    first_json = JSONAdapter()
    second_json = JSONAdapter()
    uuid_adapter = UUIDAdapter()

    result = sort_and_deduplicate_adapters([first_json, second_json, uuid_adapter])

    assert len(result) == 2
    assert result[0] is first_json  # first seen wins, and JSON sorts before UUID
    assert result[1] is uuid_adapter


# ---------------------------------------------------------------------------
# 5. prepare_parameters: the write direction
# ---------------------------------------------------------------------------


def test_a_mapping_is_converted_key_by_key():
    host = _Host()
    params = {"amount": Decimal("1.5"), "note": "x", "absent": None}
    adapters = {
        "amount": (DecimalAdapter(), str),
        "note": None,  # no pairing declared: pass through
        "absent": (DecimalAdapter(), str),
    }

    converted = host.prepare_parameters(params, adapters)

    assert converted == {"amount": "1.5", "note": "x", "absent": None}
    assert isinstance(converted, dict)
    # The caller's mapping is not consumed.
    assert params["amount"] == Decimal("1.5")


def test_a_pairing_for_a_key_the_mapping_does_not_hold_is_ignored():
    host = _Host()

    converted = host.prepare_parameters({"a": 1}, {"b": (DecimalAdapter(), str)})

    assert converted == {"a": 1}


def test_a_sequence_is_converted_position_by_position_into_a_tuple():
    host = _Host()

    converted = host.prepare_parameters(
        [Decimal("1.5"), None, "plain"],
        [(DecimalAdapter(), str), None, None],
    )

    assert converted == ("1.5", None, "plain")
    assert isinstance(converted, tuple)


def test_a_sequence_and_its_pairings_must_have_the_same_length():
    host = _Host()

    with pytest.raises(ValueError, match="must match"):
        host.prepare_parameters([1, 2], [(None, None)])


def test_empty_inputs_come_back_in_the_shape_the_caller_used():
    host = _Host()

    # No values: nothing to convert, and a sequence is normalised to a tuple.
    assert host.prepare_parameters([], [(None, None)]) == ()
    assert host.prepare_parameters({"a": 1}, {}) == {"a": 1}


def test_mismatched_shapes_are_refused_rather_than_guessed():
    host = _Host()

    with pytest.raises(TypeError, match="Unsupported types"):
        host.prepare_parameters({"a": 1}, [(None, None)])


# ---------------------------------------------------------------------------
# 6. adapt_row_types: the read direction
# ---------------------------------------------------------------------------


def test_a_column_is_converted_through_its_pairing():
    host = _Host()

    converted = host.adapt_row_types({"amount": "1.5"}, {"amount": (DecimalAdapter(), Decimal)})

    assert converted == {"amount": Decimal("1.5")}


def test_a_null_column_goes_through_the_adapter_so_it_can_answer_for_absence():
    """The adapter sees ``None`` too: an adapter may have a default for a
    non-optional column, and skipping it here would hide that."""
    host = _Host()

    converted = host.adapt_row_types({"amount": None}, {"amount": (DecimalAdapter(), Decimal)})

    assert converted == {"amount": None}


def test_a_column_with_no_pairing_is_carried_untouched():
    host = _Host()

    converted = host.adapt_row_types({"name": "x", "missing": None}, {})

    assert converted == {"name": "x", "missing": None}


def test_the_row_is_a_new_mapping():
    host = _Host()
    row = {"name": "x"}

    converted = host.adapt_row_types(row, {})
    converted["name"] = "y"

    assert row == {"name": "x"}
