# src/rhosocial/activerecord/base/derived_field_mixin.py
"""
Mixin that registers DerivedFieldHandler and provides derived field resolution logic.
"""

from typing import Any, ClassVar, Dict, List, Optional

from .derived_field_handler import DerivedFieldHandler
from .fields import DerivedField


class DerivedFieldMixin:
    _feature_handlers = [DerivedFieldHandler]

    __derived_fields__: ClassVar[Dict[str, DerivedField]] = {}
    __derived_field_names__: ClassVar[Dict[int, str]] = {}

    @classmethod
    def _apply_derived_to_query(cls, query, derived, extra_derived):
        exprs = cls._resolve_derived(derived, extra_derived)
        if exprs:
            from ..backend.expression.core import WildcardExpression
            dialect = cls.backend().dialect
            if query.select_columns is None:
                query.select(WildcardExpression(dialect))
            query.select(*exprs, append=True)

    @classmethod
    def _resolve_derived(cls, derived, extra_derived=None) -> List:
        derived_fields = cls.__derived_fields__
        derived_field_names = cls.__derived_field_names__
        if not derived and not extra_derived:
            return []

        dialect = cls.backend().dialect
        exprs: List = []

        def _to_aliased_expr(alias, val):
            if isinstance(val, DerivedField):
                return val.resolve(dialect).as_(alias)
            if callable(val) and not hasattr(val, "to_sql"):
                return val(dialect).as_(alias)
            return val.as_(alias)

        def _lookup(item):
            if isinstance(item, str):
                return item, derived_fields[item]
            if isinstance(item, DerivedField):
                name = derived_field_names.get(id(item))
                if name:
                    return name, derived_fields[name]
                raise ValueError(f"DerivedField not registered on {cls.__name__}")
            if hasattr(item, "__metadata__"):
                for meta in item.__metadata__:
                    if isinstance(meta, DerivedField):
                        name = derived_field_names.get(id(meta))
                        if name:
                            return name, derived_fields[name]
                raise ValueError(f"Annotated alias not registered on {cls.__name__}")
            raise TypeError(f"Expected str/DerivedField/TypeAlias, got {type(item)}")

        if derived is True:
            for name, df in derived_fields.items():
                if df.default_included:
                    exprs.append(df.resolve(dialect).as_(name))
        elif isinstance(derived, list):
            for item in derived:
                name, df = _lookup(item)
                exprs.append(df.resolve(dialect).as_(name))
        elif isinstance(derived, dict):
            for alias, val in derived.items():
                exprs.append(_to_aliased_expr(alias, val))

        if extra_derived:
            fixed_names = set(derived_fields.keys())
            for alias, val in extra_derived.items():
                if alias in fixed_names:
                    raise ValueError(
                        f"extra_derived alias '{alias}' conflicts with a declared derived field. "
                        f"Use derived={{'{alias}': expr}} to override instead."
                    )
                exprs.append(_to_aliased_expr(alias, val))

        return exprs
