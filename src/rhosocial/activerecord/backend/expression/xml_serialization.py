# src/rhosocial/activerecord/backend/expression/xml_serialization.py
"""
Expression spec <-> XML serialization.

The expression instance is first converted to a spec dict (the ``{type, params}``
structure produced by ``ExpressionSerializer.serialize``, with the reserved keys
``__expr__`` / ``__tuple__`` / ``__value__`` / ``__cast__``). This module encodes
that spec dict into an XML document and decodes an XML document back into the
identical spec dict, so ``deserialize()`` and the value codecs are reused
unchanged.

Mapping (symmetric, unambiguous wrapping):
    <expression>
      <type>module.Class</type>
      <params>
        <field name="arg">…</field>
      </params>
    </expression>

…value… within a <field> is one of:
    scalar                  -> text + optional type attribute (int/float/bool)
    null                    -> <null/>
    list                    -> <list><item>…</item>…</list>
    tuple                   -> <tuple><item>…</item>…</tuple>
    plain dict              -> <map><field name=…>…</field>…</map>
    {"__expr__": spec}      -> <expr><type>…</type><params>…</params></expr>
    {"__value__": [tag, payload]} -> <value tag=…>…</value>
    {"__cast__": [...]}     -> <cast><item>…</item>…</cast>

Every distinct Python container/type maps to a distinct element tag, so
decode is lossless and symmetric with encode. All encoding/parsing is handled
by the standard library ``xml.etree.ElementTree``.
"""

from typing import Any, Dict, Optional
from xml.etree import ElementTree as ET

ROOT = "expression"
FIELD = "field"
MAP = "map"
LIST = "list"
TUPLE_NODE = "tuple"
TYPE_EL = "type"
PARAMS_EL = "params"
EXPR_NODE = "expr"
VALUE_NODE = "value"
CAST_NODE = "cast"
NULL = "null"
ITEM = "item"


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
        if "__expr__" in value:
            spec = value["__expr__"]
            node = ET.SubElement(parent, EXPR_NODE)
            t = ET.SubElement(node, TYPE_EL)
            t.text = spec.get("type", "")
            _fill_dict(ET.SubElement(node, PARAMS_EL), spec.get("params", {}))
        elif "__tuple__" in value:
            node = ET.SubElement(parent, TUPLE_NODE)
            for item in value["__tuple__"]:
                _fill_value(node, item)
        elif "__value__" in value:
            payload = value["__value__"]
            node = ET.SubElement(parent, VALUE_NODE)
            node.set("tag", payload[0])
            _fill_payload(node, payload[1])
        elif "__cast__" in value:
            node = ET.SubElement(parent, CAST_NODE)
            for item in value["__cast__"]:
                ET.SubElement(node, ITEM).text = _scalar_to_text(item)
        else:
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
    """Encode a __value__ payload directly into the value node (scalar leaf or container)."""
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
    t = ET.SubElement(root, TYPE_EL)
    t.text = spec.get("type", "")
    _fill_dict(ET.SubElement(root, PARAMS_EL), spec.get("params", {}))
    return ET.tostring(root, encoding="utf-8")


# ---------- decode ----------

def _text(el: ET.Element) -> str:
    return (el.text or "").strip()


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
    if tag not in (LIST, TUPLE_NODE, MAP, EXPR_NODE, VALUE_NODE, CAST_NODE, "s"):
        # unknown tag fallback
        return None
    if tag == "s":
        return _scalar_from(_text(el), el.get("type") or "str")
    if tag == LIST:
        return [_decode_value(c) for c in el]
    if tag == TUPLE_NODE:
        return tuple(_decode_value(c) for c in el)
    if tag == MAP:
        return _decode_dict(el)
    if tag == EXPR_NODE:
        return {"__expr__": _decode_expr_spec(el)}
    if tag == VALUE_NODE:
        return {"__value__": [el.get("tag") or "", _decode_payload(el)]}
    if tag == CAST_NODE:
        return {"__cast__": [_text(c) for c in el]}
    return None


def _decode_payload(el: ET.Element) -> Any:
    """Decode the payload of a <value> node (scalar or container)."""
    children = list(el)
    if not children:
        return _scalar_from(_text(el), el.get("type") or "str")
    return [_decode_value(c) for c in children]


def _decode_expr_spec(el: ET.Element) -> Dict[str, Any]:
    spec: Dict[str, Any] = {"type": "", "params": {}}
    for c in el:
        if c.tag == TYPE_EL:
            spec["type"] = _text(c)
        elif c.tag == PARAMS_EL:
            spec["params"] = _decode_dict(c)
    return spec


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
    spec: Dict[str, Any] = {"type": "", "params": {}}
    for c in root:
        if c.tag == TYPE_EL:
            spec["type"] = _text(c)
        elif c.tag == PARAMS_EL:
            spec["params"] = _decode_dict(c)
    return spec