# tests/rhosocial/activerecord_test/feature/backend/core/test_protocol_mixin_strict_pairing.py
"""Strict Support(Protocol) <-> Mixin 1:1 conformance for the generic dialect layer.

This is the executable form of the rule in the formal description:
  - naming.md §5 / backend-expression-dialect.md §6: naming injectivity
    (one entity, one name; no aliases, no duplicate names).
  - backend-expression-dialect.md §7 (Python form, non-contract):
    each feature group is a same-stem pair XxxSupport / XxxMixin whose
    members, declaration order and signatures are identical.

After the Phase 0–6 refactoring every assertion passes (feature-group pairs strict 1:1; pure-interface
protocols are exempt).
The zero-member composition bases are aggregation helpers, not feature groups,
and are excluded from the pairing check (per the design plan).
"""

import inspect
import re
from collections import defaultdict

import pytest
from rhosocial.activerecord.backend.dialect import mixins, protocols

# Pure-interface protocols: the core declares the contract, but ships no
# default mixin -- a backend either implements it itself or exposes no
# suggestion. These are not feature groups and are excluded from 1:1.
INTERFACE_ONLY_STEMS = {
    "stringconcatenationsuggestion",
    "asyncintrospectionsuggestion",
    "introspectionsuggestion",
    "upsertsuggestion",
    "jsonsuggestion",
    "tablesuggestion",
    "indexsuggestion",
    "datatypesuggestion",
    "integerautoincrementcolumnsuggestion",
    "partitionaddsuggestion",
    "partitionbuildsuggestion",
    "partitiondropsuggestion",
    "partitionmergesuggestion",
    "partitionretentionsuggestion",
    "partitionsplitsuggestion",
    "partitiontablealtersuggestion",
    "partitiontabledropsuggestion",
}


def _owned(mod):
    return {
        n: o for n, o in vars(mod).items()
        if isinstance(o, type) and o.__module__.startswith(mod.__name__)
    }


def _stem(name):
    for suffix in ("Support", "Mixin", "Protocol"):
        name = name.replace(suffix, "")
    return name.lower()


def _own_annotations(cls):
    """Annotations declared on cls itself, minus ones inherited from a base.

    Python 3.8/3.9's typing.Protocol copies a base protocol's annotations into
    the subclass' __annotations__; 3.10+ do not. Subtracting annotations that
    also appear on any MRO base makes member extraction version-stable.
    """
    own = dict(getattr(cls, "__annotations__", {}))
    for base in getattr(cls, "__mro__", ())[1:]:
        for key in getattr(base, "__annotations__", {}):
            own.pop(key, None)
    return own


def _members(cls):
    """Public member names in declaration order."""
    out = []
    for name, val in cls.__dict__.items():
        if name.startswith("_"):
            continue
        if callable(val) or isinstance(val, (property, classmethod, staticmethod)):
            out.append(name)
    for name in _own_annotations(cls):
        if not name.startswith("_") and name not in out:
            out.append(name)
    return out


def _norm_annotation(ann):
    """Normalize an annotation so import style / PEP 563 / future-annotations
    differences do not matter (kept in sync with the formal-description audit)."""
    if isinstance(ann, type):
        return ann.__name__
    s = str(ann)
    s = s.replace("typing.", "")
    s = s.replace("Tuple", "tuple").replace("List", "list").replace("Dict", "dict")
    s = s.replace("'", "").replace('"', "")
    s = s.replace(" ", "")
    s = re.sub(r"Optional\[([^\[\]]+)\]", r"\1|None", s)
    s = re.sub(r"Union\[([^\[\]]+?),None\]", r"\1|None", s)
    return s


def _sig(cls, name):
    """Canonical signature descriptor with normalized annotations."""
    val = getattr(cls, name, None)
    inner = val
    prefix = "callable:"
    if isinstance(val, (property, classmethod, staticmethod)):
        prefix = type(val).__name__ + ":"
        inner = val.fget if isinstance(val, property) else val.__func__
    if callable(inner):
        try:
            sig = inspect.signature(inner)
        except (TypeError, ValueError):
            return prefix + "<unsignable>"
        parts = []
        for p in sig.parameters.values():
            if p.name == "self":
                continue
            parts.append(
                f"{p.name}|{p.kind.name}|{_norm_annotation(p.annotation)}"
                + ("" if p.default is inspect.Parameter.empty else f"={p.default!r}")
            )
        return prefix + ",".join(parts) + "->" + _norm_annotation(sig.return_annotation)
    return "value:" + repr(val)


def _members_compatible(proto_cls, mixin_cls, name):
    """A bare protocol annotation (e.g. ``separator: str``) is compatible with
    a concrete value on the implementation (e.g. ``separator = '.'``)."""
    pv = getattr(proto_cls, name, None)
    mv = getattr(mixin_cls, name, None)
    p_callable = callable(pv) or isinstance(pv, (property, classmethod, staticmethod))
    m_callable = callable(mv) or isinstance(mv, (property, classmethod, staticmethod))
    if p_callable and m_callable:
        return _sig(proto_cls, name) == _sig(mixin_cls, name)
    if not p_callable and not m_callable:
        anns = getattr(proto_cls, "__annotations__", {})
        if name in anns:
            return True
        return repr(pv) == repr(mv)
    return False


def _unique_by_identity(mod):
    out = {}
    for n, o in _owned(mod).items():
        out.setdefault(id(o), (n, o))
    return out


def test_no_alias_export_names():
    """[L] Each class is exported under exactly one name (no aliases)."""
    for mod, label in ((protocols, "protocols"), (mixins, "mixins")):
        by_id = defaultdict(list)
        for n, o in _owned(mod).items():
            by_id[id(o)].append(n)
        aliases = {tuple(sorted(v)) for v in by_id.values() if len(v) > 1}
        assert not aliases, f"{label} has aliased exports: {sorted(aliases)}"


def test_no_duplicate_class_names():
    """[L] No two distinct classes share a __name__."""
    for mod, label in ((protocols, "protocols"), (mixins, "mixins")):
        by_name = defaultdict(set)
        for n, o in _owned(mod).items():
            by_name[o.__name__].add(id(o))
        dup = {k for k, v in by_name.items() if len(v) > 1}
        assert not dup, f"{label} has duplicate class names: {sorted(dup)}"


def test_every_protocol_has_matching_mixin_and_vice_versa():
    """[P] Stem sets of protocols and non-composition mixins are equal.

    Mixins with zero own members are composition bases (they only aggregate
    per-statement mixins), not feature groups, and are excluded.
    """
    # Empty marker protocols and zero-member composition bases are not feature
    # groups; both are excluded from the bijection check.
    pstems = set()
    for n, o in _unique_by_identity(protocols).values():
        if len(_members(o)) == 0 or _stem(n) in INTERFACE_ONLY_STEMS:
            continue
        pstems.add(_stem(n))
    mstems = set()
    for n, o in _unique_by_identity(mixins).values():
        if len(_members(o)) == 0:
            continue
        mstems.add(_stem(n))
    assert pstems == mstems, (
        f"protocol-only stems: {sorted(pstems - mstems)}\n"
        f"mixin-only stems: {sorted(mstems - pstems)}"
    )


def test_paired_members_are_identical():
    """[P] Each pair declares the same public members."""
    pstems = {_stem(n): (n, o) for n, o in _unique_by_identity(protocols).values()}
    mstems = {_stem(n): (n, o) for n, o in _unique_by_identity(mixins).values()}
    bad = []
    for s in sorted(set(pstems) & set(mstems)):
        pn, po = pstems[s]
        mn, mo = mstems[s]
        if _members(po) != _members(mo):
            bad.append((pn, mn))
    assert not bad, f"member mismatches: {bad}"


def test_paired_member_order_is_identical():
    """[P] Each pair declares members in the same order."""
    pstems = {_stem(n): (n, o) for n, o in _unique_by_identity(protocols).values()}
    mstems = {_stem(n): (n, o) for n, o in _unique_by_identity(mixins).values()}
    bad = []
    for s in sorted(set(pstems) & set(mstems)):
        pn, po = pstems[s]
        mn, mo = mstems[s]
        pm, mm = _members(po), _members(mo)
        if sorted(pm) == sorted(mm) and pm != mm:
            bad.append((pn, mn))
    assert not bad, f"order mismatches: {bad}"


def test_paired_signatures_are_identical():
    """[P] Each paired member has an identical signature."""
    pstems = {_stem(n): (n, o) for n, o in _unique_by_identity(protocols).values()}
    mstems = {_stem(n): (n, o) for n, o in _unique_by_identity(mixins).values()}
    bad = []
    for s in sorted(set(pstems) & set(mstems)):
        pn, po = pstems[s]
        mn, mo = mstems[s]
        for name in _members(po):
            if name in _members(mo) and not _members_compatible(po, mo, name):
                bad.append(f"{pn}.{name}")
    assert not bad, f"signature mismatches: {bad}"
