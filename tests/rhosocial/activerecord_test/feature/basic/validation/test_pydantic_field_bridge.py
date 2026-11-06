# tests/rhosocial/activerecord_test/feature/basic/validation/test_pydantic_field_bridge.py
"""The pydantic bridge's deliberate decisions are decisions, not leftovers.

``PYDANTIC_FIELD_NOT_MAPPED`` records the pydantic field types this project has
decided *not* to map onto a plain value type, each with a reason written above
it. It is read once -- by ``is_pydantic_field_name`` -- so nothing but these
assertions says the record is still true, in either of the two ways it can stop
being true: pydantic renames or removes one of the types, which turns a recorded
decision into a decision about something that no longer exists; or a name ends
up in both tables, and the mapped one wins, which makes the unmapped entry and
its reason dead text.

The behavioural half is the promise the module makes about these types: a field
annotated with one of them resolves to nothing here, exactly as it did before
the bridge existed, and ``UseColumnType`` remains the route forward.
"""

import pydantic.networks
import pydantic.types
import pytest

from rhosocial.activerecord.base.pydantic_fields import (
    PYDANTIC_FIELD_NOT_MAPPED,
    PYDANTIC_FIELD_TO_ENTRY,
    normalize_pydantic_annotation,
)

pytestmark = [pytest.mark.feature]


def _pydantic_field_class(name):
    """The class *name* in pydantic's field-type namespaces, or ``None``."""
    for module in (pydantic.types, pydantic.networks):
        candidate = getattr(module, name, None)
        if candidate is not None:
            return candidate
    return None


@pytest.mark.parametrize("name", sorted(PYDANTIC_FIELD_NOT_MAPPED))
def test_every_unmapped_name_is_a_field_type_pydantic_still_ships(name):
    """A rename upstream would leave the record describing something absent.

    The classes are reached by name rather than by import path, so a name
    pydantic has dropped resolves to nothing and the bridge's answer for it
    silently becomes "not ours at all" instead of the recorded decision.
    """
    assert _pydantic_field_class(name) is not None, (
        f"{name} is recorded as a deliberately unmapped pydantic field type, but "
        f"neither pydantic.types nor pydantic.networks declares it"
    )


def test_nothing_is_both_mapped_and_deliberately_unmapped():
    """The mapped table is consulted first, so an overlap is a dead entry."""
    both = set(PYDANTIC_FIELD_NOT_MAPPED) & set(PYDANTIC_FIELD_TO_ENTRY)
    assert not both, (
        f"recorded as unmapped but also mapped, and the mapping wins: "
        f"{sorted(both)}"
    )


@pytest.mark.parametrize("name", sorted(PYDANTIC_FIELD_NOT_MAPPED))
def test_an_unmapped_field_type_resolves_to_nothing(name):
    """A field annotated with one of these fails exactly as it did before.

    ``None`` is what the protocol's normaliser treats as an unclassifiable
    annotation, which is the behaviour this table is a record of -- not a gap to
    be filled, but a place where a mapping would be a decision the table is not
    entitled to make.
    """
    field_class = _pydantic_field_class(name)
    if field_class is None:
        pytest.skip(f"{name} is not shipped by this pydantic any more")
    assert normalize_pydantic_annotation(field_class) is None, (
        f"{name} is recorded as deliberately unmapped, but the bridge resolved "
        f"it to {normalize_pydantic_annotation(field_class)!r}"
    )
