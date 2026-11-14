# tests/rhosocial/activerecord_test/feature/backend/adapters/test_json_adapter_params.py
"""JSON adapter hooks for neutral-type codecs (DB-free)."""

from typing import Any

from rhosocial.activerecord.backend.adapters.json_codec import AdapterJSONCodec, register_type
from rhosocial.activerecord.backend.type_adapter import JSONAdapter


class _Demo:
    json_type_tag = "demo_json_adapter"

    def __init__(self, value: int):
        self.value = value

    def to_json_value(self) -> Any:
        return {"number": self.value}

    @classmethod
    def from_json_value(cls, value: Any) -> "_Demo":
        return cls(int(value["number"]))

    def __eq__(self, other: object) -> bool:
        return isinstance(other, _Demo) and self.value == other.value


def test_json_adapter_without_hooks_is_unchanged():
    adapter = JSONAdapter()
    text = adapter.to_database({"a": 1}, str)
    assert text == '{"a": 1}'
    assert adapter.from_database(text, dict) == {"a": 1}


def test_json_adapter_forwards_default_and_object_hook():
    register_type("demo_json_adapter", _Demo)
    codec = AdapterJSONCodec(tagged=True)
    adapter = JSONAdapter(default=codec.default, object_hook=codec.object_hook)

    text = adapter.to_database({"d": _Demo(7)}, str)
    assert '"__type__": "demo_json_adapter"' in text

    decoded = adapter.from_database(text, dict)
    assert isinstance(decoded["d"], _Demo)
    assert decoded["d"].value == 7
