# tests/rhosocial/activerecord_test/feature/backend/core/test_capability_report.py
"""The shared capability/suggestion report helper.

Covers the three-way origin classification (reuse/override/proprietary),
support checking, and suggestion-protocol detection, all with synthetic
dialects so no backend is required.
"""
from typing import Protocol, runtime_checkable

from rhosocial.activerecord.backend.dialect import capabilities as cap


# synthetic hierarchy mimicking core mixins / backend overrides
class _CoreMixin:
    """Pretend to live in rhosocial.activerecord.backend.dialect.mixins."""
    __module__ = "rhosocial.activerecord.backend.dialect.mixins.fake"

    def supports_reused(self) -> bool:
        return True

    def supports_overridden(self) -> bool:
        return True


class _BackendMixin:
    """Pretend to live in a backend impl."""
    __module__ = "rhosocial.activerecord.backend.impl.fake.mixins"

    def supports_overridden(self) -> bool:
        return True

    def supports_proprietary(self) -> bool:
        return True


class _Dialect(_BackendMixin, _CoreMixin):
    pass


@runtime_checkable
class _SuggestionProto(Protocol):
    def suggest_something(self): ...


class _Implementor:
    __module__ = "rhosocial.activerecord.backend.impl.fake.suggestion"

    def suggest_something(self):
        return 1


def test_classify_origin_reuse():
    assert cap.classify_origin(_Dialect(), "supports_reused") == "reuse"


def test_classify_origin_override():
    assert cap.classify_origin(_Dialect(), "supports_overridden") == "override"


def test_classify_origin_proprietary():
    assert cap.classify_origin(_Dialect(), "supports_proprietary") == "proprietary"


def test_classify_origin_absent():
    assert cap.classify_origin(_Dialect(), "supports_never") == "absent"


def test_own_annotations_not_inherited():
    """Owner discovery must skip Protocol classes themselves."""

    class BaseProto(Protocol):
        separator: str

    class ChildProto(BaseProto, Protocol):
        def supports_child(self) -> bool: ...

    # separator is declared by a Protocol -> not a real implementation owner
    assert cap._owner_of(ChildProto, "separator") is None


def test_check_protocol_support_zero_arg():
    class Proto(Protocol):
        def supports_reused(self) -> bool: ...

    results = cap.check_protocol_support(_Dialect(), Proto)
    assert results["supports_reused"] is True


def test_check_protocol_support_parameterised():
    class Proto(Protocol):
        def supports_fmt(self, fmt) -> bool: ...

    class D:
        def supports_fmt(self, fmt):
            return fmt == "TEXT"

    results = cap.check_protocol_support(D(), Proto, {"supports_fmt": ["TEXT", "JSON"]})
    assert results["supports_fmt"] == {"supported": 1, "total": 2, "args": {"TEXT": True, "JSON": False}}


def test_capability_report_has_origin():
    @runtime_checkable
    class Proto(Protocol):
        __module__ = "rhosocial.activerecord.backend.dialect.protocols.fake"
        def supports_reused(self) -> bool: ...

    report = cap.build_capability_report(
        _Dialect(), {"G": [Proto]}, dialect_specific_groups=set()
    )
    entry = report["G"]["Proto"]
    assert entry["supported"] == 1 and entry["total"] == 1
    assert entry["origin"] in ("reuse", "override", "proprietary")


def test_capability_report_dialect_specific_group_is_proprietary():
    @runtime_checkable
    class Proto(Protocol):
        __module__ = "rhosocial.activerecord.backend.dialect.protocols.fake"
        def supports_reused(self) -> bool: ...

    report = cap.build_capability_report(
        _Dialect(), {"Native": [Proto]}, dialect_specific_groups={"Native"}
    )
    assert report["Native"]["Proto"]["origin"] == "proprietary"


def test_suggestion_report_detection():
    # monkeypatch the protocol list to a single synthetic protocol
    original = cap.suggestion_protocols
    try:
        cap.suggestion_protocols = lambda: [_SuggestionProto]
        report = cap.build_suggestion_report(_Implementor())
        assert report["_SuggestionProto"]["supported"] is True
        report2 = cap.build_suggestion_report(_Dialect())
        assert report2["_SuggestionProto"]["supported"] is False
    finally:
        cap.suggestion_protocols = original


def test_iter_protocols_deduplicates():
    class P(Protocol): ...
    mod = type("M", (), {})()
    mod.P = P
    mod.PAlias = P
    assert cap.iter_protocols(mod) == [P]
