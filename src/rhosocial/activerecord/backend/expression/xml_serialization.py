# src/rhosocial/activerecord/backend/expression/xml_serialization.py
"""
XML rendering of an expression artifact.

The artifact is produced by the JSON codec first and rendered here, then parsed
back into the identical dict, so ``deserialize()`` is reused unchanged and the
two renderings cannot disagree about what a node is.

    <expression>
      <kind>query_statement</kind>
      <params>
        <field name="select">…</field>
      </params>
    </expression>

…a value within a ``<field>`` is one of:
    scalar                  -> text + optional type attribute (int/float/bool)
    null                    -> ``<null/>``
    list                    -> ``<list>`` with one child per element
    tuple                   -> ``<tuple>`` with one child per element
    plain dict              -> ``<map><field name=…>…</field>…</map>``
    a nested node           -> also a ``<map>``: it *is* ``{kind, params}``, and
                               the reader recognises it by that shape

There are no reserved keys and no wrapper elements for values. A value JSON
cannot spell -- bytes, a timedelta, a Decimal -- travels as the text its kind
names, and the same ``<s>`` element carries it with the kind recorded in the
node around it. A per-language dispatch would have to be reimplemented here to
survive the round-trip, which is exactly what the format refuses to ask of any
reader.

Decoding is lossless and symmetric with encoding. All encoding/parsing is
handled by the standard library ``xml.etree.ElementTree``.
"""

from typing import Any, Dict, Optional
from xml.etree import ElementTree as ET

ROOT = "expression"
FIELD = "field"
MAP = "map"
LIST = "list"
TUPLE_NODE = "tuple"
# The node's *kind*, not its class's FQN. Read by kind is why no import path
# ever crosses the wire (§7.2). Distinct from the ``type="int"`` attribute
# that tags a scalar's textual form -- that one is a lexical marker, not an
# identity, and keeps its name.
KIND_EL = "kind"
PARAMS_EL = "params"
NULL = "null"


# ---------- encode ----------

def _scalar_type(value: Any) -> str:
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int):
        return "int"
    if isinstance(value, float):
        return "float"
    return "str"


def _scalar_to_text(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _fill_value(parent: ET.Element, value: Any) -> None:
    """Append a child element to ``parent`` encoding ``value``."""
    if value is None:
        ET.SubElement(parent, NULL)
        return
    if isinstance(value, dict):
        # A nested node is a plain map here too -- it *is* ``{kind, params}``,
        # and the reader recognises it by that shape, so wrapping it would say
        # the same thing a second and weaker way. Any other object is a mapping
        # parameter.
        node = ET.SubElement(parent, MAP)
        _fill_dict(node, value)
    elif isinstance(value, (list, tuple)):
        node = ET.SubElement(parent, TUPLE_NODE if isinstance(value, tuple) else LIST)
        for item in value:
            _fill_value(node, item)
    else:
        node = ET.SubElement(parent, "s")
        node.text = _scalar_to_text(value)
        t = _scalar_type(value)
        if t != "str":
            node.set("type", t)


def _fill_payload(node: ET.Element, payload: Any) -> None:
    """Encode a reserved wrapper's payload into the value node (scalar or container)."""
    if isinstance(payload, (list, tuple)):
        for item in payload:
            _fill_value(node, item)
    elif payload is None:
        ET.SubElement(node, NULL)
    else:
        node.text = _scalar_to_text(payload)
        t = _scalar_type(payload)
        if t != "str":
            node.set("type", t)


def _fill_dict(parent: ET.Element, d: Dict[str, Any]) -> None:
    for key, val in d.items():
        child = ET.SubElement(parent, FIELD)
        child.set("name", key)
        _fill_value(child, val)


def serialize_xml(spec: Dict[str, Any]) -> bytes:
    """Encode an expression spec dict into an XML document (bytes)."""
    root = ET.Element(ROOT)
    t = ET.SubElement(root, KIND_EL)
    t.text = spec.get("kind", "")
    _fill_dict(ET.SubElement(root, PARAMS_EL), spec.get("params", {}))
    return ET.tostring(root, encoding="utf-8")


# ---------- decode ----------

def _text(el: ET.Element) -> str:
    # ElementTree preserves text exactly as written by _scalar_to_text; do NOT
    # strip, otherwise string values with leading/trailing whitespace (e.g.
    # SUBSTR(' .+*#', ...)) are corrupted by the round-trip.
    return el.text or ""


def _scalar_from(text: str, type_attr: Optional[str]) -> Any:
    if type_attr == "bool":
        return text == "true"
    if type_attr == "int":
        return int(text)
    if type_attr == "float":
        return float(text)
    return text


def _decode_value(el: ET.Element) -> Any:
    """Decode a child-of-field element (produced by _fill_value) into a Python value."""
    tag = el.tag
    if tag == NULL:
        return None
    if tag not in (LIST, TUPLE_NODE, MAP, "s"):
        # unknown tag fallback
        return None
    if tag == "s":
        return _scalar_from(_text(el), el.get("type") or "str")
    if tag == LIST:
        return [_decode_value(c) for c in el]
    if tag == TUPLE_NODE:
        return tuple(_decode_value(c) for c in el)
    return _decode_dict(el)


def _decode_dict(el: ET.Element) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    for c in el:
        if c.tag != FIELD:
            continue
        name = c.get("name") or ""
        children = list(c)
        if children:
            result[name] = _decode_value(children[0])
        else:
            result[name] = None
    return result


def deserialize_xml(payload: bytes) -> Dict[str, Any]:
    """Decode an XML document into an expression spec dict."""
    root = ET.fromstring(payload)
    spec: Dict[str, Any] = {"kind": "", "params": {}}
    for c in root:
        if c.tag == KIND_EL:
            spec["kind"] = _text(c)
        elif c.tag == PARAMS_EL:
            spec["params"] = _decode_dict(c)
    return spec