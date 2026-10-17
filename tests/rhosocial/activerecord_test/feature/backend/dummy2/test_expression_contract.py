# tests/rhosocial/activerecord_test/feature/backend/dummy2/test_expression_contract.py
"""
Contract test: every built-in expression class must satisfy the
"__init__ parameter ↔ stored attribute" convention that powers the
introspection-based default implementation of BaseExpression.get_params().

For each registered expression class, an instance is constructed with
heuristic placeholder arguments, then get_params() is required to return
a value for every __init__ parameter (excluding self/dialect/**kwargs)
without emitting the "cannot find attribute" warning.

Classes that cannot be auto-constructed must be listed explicitly in
KNOWN_NON_AUTO_CONSTRUCTIBLE with a reason, so new violations fail loudly.
"""

import inspect
import warnings

from rhosocial.activerecord.backend.expression.core import Literal
from rhosocial.activerecord.backend.expression.serialization import (
    auto_register_builtins,
    registered_expression_classes,
)

from rhosocial.activerecord.testsuite.utils.expression import (
    _try_construct,
    special_constructors,
)


# Classes that legitimately cannot be auto-constructed with heuristic
# fillers (e.g. require real backend objects). Any new entry must carry
# a justification.
KNOWN_NON_AUTO_CONSTRUCTIBLE = {
    # class FQN suffix : reason
    "types.enum_.EnumType": "requires non-empty `values` (structural "
                            "construction check raises ValueError on None/[])",
    "statements.ddl_alter.AlterConstraint": "requires a non-empty constraint name",
    "statements.ddl_alter.ValidateConstraint": "requires a non-empty constraint name",
"statements.ddl_domain.AddDomainCheckAction": "requires a concrete DomainCheckConstraint",
    "statements.ddl_domain.DomainCheckConstraint": "requires a concrete check condition",
    # The XML constructors take a sequence of their own item types, and an
    # empty one is structurally meaningless -- there is no value to check and
    # nothing to render.
    "expression.xml.XMLAttributesExpression": "requires a non-empty attribute list",
    "expression.xml.XMLForestExpression": "requires a non-empty forest item list",
    "expression.xml.XMLConcatExpression": "requires a non-empty part list",
    "expression.xml.XMLTableExpression": "requires a row-specifying context item",
    "expression.uuid.UUIDConstantExpression": "requires `which` to name a "
        "constant kind ('nil' / 'max'); __init__ rejects anything else, and a "
        "heuristic filler has no way to guess a valid one",
    "types.custom.CustomType": "requires `raw`, the backend's own spelling of "
        "the type. It is the escape hatch for a type name this library does "
        "not model -- DOUBLE PRECISION, a vendor's domain type -- and there is "
        "nothing to guess: the name is the whole point, and it is validated as "
        "a grammar rather than accepted blindly",
    "query_sources.SetOperation": "`op` is validated against the wire word "
        "forms (union/union_all/intersect/except); the heuristic filler offers "
        "the string 'x', which the constructor refuses. The roundtrip matrix "
        "registers a real constructor for it",
    "operators.ArithmeticOperation": "`op` is validated against the wire word "
        "forms (add/sub/mul/div/mod); the heuristic filler offers the string "
        "'x', which the constructor refuses. The roundtrip matrix registers a "
        "real constructor for it",
    # Text function nodes that enforce a bound the filler cannot know about.
    "functions.string.SubstringExpression": "`start` is 1-based; the filler's "
        "value is below 1 and the node refuses it at construction",
    "functions.string.OverlayExpression": "`start` is 1-based; the filler's "
        "value is below 1 and the node refuses it at construction",
    "functions.string.LeftFunction": "`count` must be >= 0 and the filler's "
        "is negative",
    "functions.string.RightFunction": "`count` must be >= 0 and the filler's "
        "is negative",
    "functions.string.SpaceFunction": "`count` is a number of spaces and the "
        "filler's is negative",
    "functions.string.ChrFunction": "`code` is a character code; the filler's "
        "text is not a whole number and the node refuses it",
    # The two extract nodes, and the typed value nodes, for the reasons the
    # roundtrip matrix records: a field and a spelling that must agree, and a
    # host value whose conceptual type only the caller knows.
    "functions.window._WindowRank": "the shared base of the three ranking "
        "window functions; it declares no function name of its own, so it is "
        "not a node",
    "datetime._ExtractBase": "holds the field, the source and the spelling; it "
        "is not itself rendered, so there is no answer type to construct",
    "datetime.ExtractFieldExpression": "`field` and `spelling` must agree, "
        "which is one fact stated twice and not something a filler can hold",
    "values.BinaryValue": "takes bytes; no filler value is both bytes and not "
        "a guess at the caller's intent",
    "values.BooleanValue": "takes a bool, and a filler's string is refused",
    "values.DateValue": "takes a datetime.date; the filler's string is refused",
    "values.DecimalValue": "takes a Decimal; the filler's string is refused",
    "values.IntervalValue": "takes a timedelta; the filler's string is refused",
    "values.StringValue": "takes a str, and an int filler is refused",
    "values.TimeValue": "takes a datetime.time; the filler's string is refused",
    "values.TimestampValue": "takes a datetime; the filler's string is refused",
    "values.UUIDValue": "takes a UUID; the filler's string is refused",
    "functions.array.ArrayAggregateFunction": "gathers into an array, which the "
        "filler cannot supply; the result type is carried by the mixins",
    "functions.json.JSONObjectAggregateFunction": "gathers into a JSON document, "
        "which the filler cannot supply",
}




class TestInitParamAttributeContract:
    """For every registered expression class, get_params() must resolve
    every __init__ parameter without emitting the fallback warning."""

    def test_all_builtin_expressions(self, dummy_dialect):
        auto_register_builtins()
        specials = special_constructors()
        skipped = []
        checked = 0
        for fqn, cls in sorted(registered_expression_classes().items()):
            if inspect.isabstract(cls):
                continue
            special = next((fn for s, fn in specials.items() if fqn.endswith(s)), None)
            if special is not None:
                instance = special(dummy_dialect)
            else:
                instance = _try_construct(cls, dummy_dialect)
            if instance is None:
                skipped.append(fqn)
                continue
            checked += 1
            with warnings.catch_warnings(record=True) as caught:
                warnings.simplefilter("always")
                params = instance.get_params()
            missing_warnings = [
                w for w in caught if "cannot find attribute" in str(w.message)
            ]
            assert not missing_warnings, (
                f"{fqn}: get_params() could not resolve attributes: "
                f"{[str(w.message) for w in missing_warnings]}"
            )
            sig = inspect.signature(cls.__init__)
            for pname, param in sig.parameters.items():
                if pname in ("self", "dialect"):
                    continue
                if param.kind == inspect.Parameter.VAR_KEYWORD:
                    continue
                if pname not in params:
                    # Round-trip safe omission: a defaulted parameter whose
                    # current value equals its default may be omitted from
                    # get_params() (the deserializer restores the default).
                    assert param.default is not inspect.Parameter.empty, (
                        f"{fqn}: required __init__ parameter '{pname}' missing "
                        "from get_params() result"
                    )
                    attr = getattr(instance, f"_{pname}", getattr(instance, pname, None))
                    assert attr == param.default, (
                        f"{fqn}: __init__ parameter '{pname}' omitted from "
                        f"get_params() but its value {attr!r} != default "
                        f"{param.default!r}; round-trip would lose state"
                    )

        unexpected_skips = [
            fqn for fqn in skipped
            if not any(fqn.endswith(suffix) for suffix in KNOWN_NON_AUTO_CONSTRUCTIBLE)
        ]
        assert checked > 0, "no expression classes were auto-constructed"
        assert not unexpected_skips, (
            "Classes could not be auto-constructed (add to "
            "KNOWN_NON_AUTO_CONSTRUCTIBLE with a reason, or fix): "
            + ", ".join(unexpected_skips)
        )

    def test_no_get_params_override(self):
        """The generic get_params() is the single serialization path.

        Every registered expression class must NOT override get_params().
        The only exception is a VAR_POSITIONAL class that performs genuine
        raw-vs-normalized round-trip rewriting (e.g. JSONArrayValue
        style) - none exist in the core registry, so the rule is absolute
        here. Adding an override reintroduces the special-casing that
        caused serialization gaps; instead fold state into __init__.
        """
        auto_register_builtins()
        import inspect as _inspect
        from rhosocial.activerecord.backend.expression.bases import BaseExpression
        offenders = []
        for fqn, cls in registered_expression_classes().items():
            if inspect.isabstract(cls):
                continue
            sig = _inspect.signature(cls.__init__)
            is_vararg = any(
                p.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
                for p in sig.parameters.values()
            )
            if cls.get_params is not BaseExpression.get_params:
                offenders.append((fqn, is_vararg))
        assert not offenders, (
            "Expression classes must not override get_params() (generic path "
            "covers __init__-params and same-name kwargs). Fold state into "
            "__init__ instead. Offenders: "
        ) + ", ".join(f"{f} (vararg={v})" for f, v in offenders)

    def test_var_keyword_resolves_same_name_attr(self, dummy_dialect):
        """VAR_KEYWORD extras must serialize as merged top-level params."""
        from rhosocial.activerecord.backend.expression.collation import CollateFunction
        expr = CollateFunction(dummy_dialect, Literal(dummy_dialect, "a"), "NOCASE",
                                 binary=True, pad="PAD")
        params = expr.get_params()
        assert params.get("binary") is True
        assert params.get("pad") == "PAD"
        assert "collation_options" not in params
