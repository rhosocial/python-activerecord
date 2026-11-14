# tests/rhosocial/activerecord_test/feature/backend/sqlite/core/test_json_adapter_hooks.py
"""SQLite JSON adapter hooks for neutral-type codecs (DB-free)."""
from typing import Any

from rhosocial.activerecord.backend.adapters.json_codec import AdapterJSONCodec, register_type
from rhosocial.activerecord.backend.impl.sqlite.adapters import SQLiteJSONAdapter


class _Demo:
    json_type_tag = "sqlite_json_demo"

    def __init__(self, number: int):
        self.number = number

    def to_json_value(self) -> Any:
        return {"number": self.number}

    @classmethod
    def from_json_value(cls, value: Any) -> "_Demo":
        return cls(int(value["number"]))

    def __eq__(self, other: object) -> bool:
        return isinstance(other, _Demo) and self.number == other.number


def test_sqlite_json_adapter_defaults_preserve_extended_serializer():
    adapter = SQLiteJSONAdapter()
    text = adapter.to_database({"a": 1}, str)
    assert text == '{"a": 1}'
    assert adapter.from_database(text, dict) == {"a": 1}


def test_sqlite_json_adapter_forwards_hooks():
    register_type("sqlite_json_demo", _Demo)
    codec = AdapterJSONCodec(tagged=True)
    adapter = SQLiteJSONAdapter(default=codec.default, object_hook=codec.object_hook)

    text = adapter.to_database({"d": _Demo(9)}, str)
    assert '"__type__": "sqlite_json_demo"' in text

    decoded = adapter.from_database(text, dict)
    assert isinstance(decoded["d"], _Demo)
    assert decoded["d"].number == 9
