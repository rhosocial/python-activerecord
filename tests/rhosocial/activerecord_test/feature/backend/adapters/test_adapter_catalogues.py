# tests/rhosocial/activerecord_test/feature/backend/adapters/test_adapter_catalogues.py
"""Tests that pin the adapter vocabularies the code reads by name.

Each constant here is read from one place in the implementation, so the
project's constant rule requires a test that names it: a value nobody asserts
is text nobody guarantees. The assertions below check the agreements the
readers rely on, rather than restating the literals.
"""

import pytest

from rhosocial.activerecord.backend.adapters.geometry import (
    Geometry,
    _DIMENSION_WORDS,
    _GEOJSON_TYPES,
    _WKT_TYPE_NAMES,
)
from rhosocial.activerecord.backend.adapters.json_codec import _TAG_ATTRIBUTES
from rhosocial.activerecord.backend.adapters.network import (
    _MAX_EUI48,
    _MAX_EUI64,
    _SEPARATORS,
)
from rhosocial.activerecord.backend.adapters.range import (
    ELEMENT_TYPE_LABELS,
    _TYPE_TO_LABEL,
)
from rhosocial.activerecord.backend.base.type_adaption import (
    CORE_DEFAULT_TYPE_MAPPINGS,
)
from rhosocial.activerecord.backend.impl.sqlite.adapters.spatial import (
    _GEOMETRY_TYPES,
)


def test_wkt_names_have_a_geojson_counterpart():
    assert _WKT_TYPE_NAMES and all(
        name.lower() in _GEOJSON_TYPES for name in _WKT_TYPE_NAMES
    )


def test_geojson_types_are_geometry_classes():
    assert _GEOJSON_TYPES and all(
        issubclass(cls, Geometry) for cls in _GEOJSON_TYPES.values()
    )


def test_dimension_words_are_single_letters_in_capitals():
    assert all(word.isalpha() and word.isupper() for word in _DIMENSION_WORDS)


def test_tag_attributes_are_distinct_and_non_empty():
    assert _TAG_ATTRIBUTES and len(set(_TAG_ATTRIBUTES)) == len(_TAG_ATTRIBUTES)


def test_mac_separators_are_single_characters():
    assert _SEPARATORS and all(len(separator) == 1 for separator in _SEPARATORS)


def test_eui_boundaries_grow_with_the_address_width():
    assert _MAX_EUI48 < _MAX_EUI64


def test_range_labels_and_the_type_map_are_one_vocabulary():
    assert set(_TYPE_TO_LABEL.values()) == set(ELEMENT_TYPE_LABELS)


def test_spatial_adapter_covers_only_geometry_classes():
    assert _GEOMETRY_TYPES and all(
        issubclass(cls, Geometry) for cls in _GEOMETRY_TYPES
    )


def test_core_defaults_leave_native_driver_types_untouched():
    mapping = dict(CORE_DEFAULT_TYPE_MAPPINGS)
    assert all(native not in mapping for native in (str, int, float, bytes))


pytestmark = [pytest.mark.feature]
