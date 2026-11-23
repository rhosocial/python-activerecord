# tests/rhosocial/activerecord_test/feature/backend/adapters/test_aware_datetime.py
"""DB-free tests for the AwareDatetime framework-committed type."""

import datetime

from pydantic import BaseModel

from rhosocial.activerecord.backend.adapters import AwareDatetime, UtcDatetime
from rhosocial.activerecord.base.framework_types import FRAMEWORK_PYTHON_TYPES


class _Model(BaseModel):
    when: AwareDatetime


def test_aware_datetime_is_a_datetime_subclass():
    assert issubclass(AwareDatetime, datetime.datetime)
    assert issubclass(UtcDatetime, AwareDatetime)


def test_aware_datetime_precedes_datetime_in_framework_types():
    # table_entry_for's exact-match step must see AwareDatetime before the walk
    # would land on datetime.datetime for a subclass.
    aware_index = FRAMEWORK_PYTHON_TYPES.index(AwareDatetime)
    naive_index = FRAMEWORK_PYTHON_TYPES.index(datetime.datetime)
    assert aware_index < naive_index


def test_naive_input_gets_utc_attached():
    model = _Model(when=datetime.datetime(2026, 1, 1, 12, 0, 0))
    assert model.when.tzinfo is datetime.timezone.utc


def test_aware_input_keeps_its_offset():
    offset = datetime.timezone(datetime.timedelta(hours=8))
    model = _Model(when=datetime.datetime(2026, 1, 1, 12, 0, 0, tzinfo=offset))
    assert model.when.utcoffset() == datetime.timedelta(hours=8)


def test_string_input_becomes_aware():
    # The core contract is that the validated value is always an instant. DDL
    # derivation and adapter selection read the field's annotation type, not the
    # runtime value type, so a plain datetime input resolving to the base class
    # is fine -- what matters is that tzinfo is attached.
    model = _Model(when="2026-01-01T12:00:00")
    assert isinstance(model.when, datetime.datetime)
    assert model.when.tzinfo is datetime.timezone.utc


def test_every_input_form_is_aware():
    for value in (
        datetime.datetime(2026, 1, 1),
        datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc),
        "2026-01-01T12:00:00",
    ):
        assert _Model(when=value).when.tzinfo is not None
