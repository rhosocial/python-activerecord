# src/rhosocial/activerecord/base/ddl/params.py
"""Statement constructor-parameter contract (Gate 0, §5.13/§5.14).

The **canonical parameter schema** of a statement family is the ``__init__``
signature of its generic statement class (excluding ``self`` / ``dialect``) —
introspected once and cached per class, so it is the single contract source
and cannot drift from the expressions themselves.

The deriver assembles ``params`` (canonical + backend-extra) and instantiates
the selected statement class as ``selected_class(dialect, **params)`` — fully
keyword-based, with no conversion on the AR side. Before instantiation, Gate 0
verifies the selected class **accepts** every collected parameter name (its
signature declares it, or it forwards ``**kwargs`` to ``super``); an
incompatible class raises with the missing parameters listed.
"""

from __future__ import annotations

import inspect
from typing import Any, Dict, List, Type

__all__ = ["StatementParamSchema", "StatementContractError"]


class StatementContractError(TypeError):
    """Raised when a selected statement class rejects collected parameters.

    The backend subclass must accept the whole canonical parameter set of its
    statement family (forwarding ``super().__init__``); a class that drops a
    canonical parameter cannot be selected — the error lists what is missing.
    """

    def __init__(self, statement: str, selected: Type[Any], missing: List[str]):
        self.statement = statement
        self.selected = selected
        self.missing = list(missing)
        super().__init__(
            f"{statement}: selected statement class {selected.__name__} does "
            f"not accept the canonical parameter(s) {missing}. A backend "
            f"subclass must accept every canonical parameter of its statement "
            f"family (forwarding super().__init__) and may add its own extras."
        )


class StatementParamSchema:
    """Introspection-based constructor-parameter contract for statements.

    For one statement family (its generic class as the contract source):

    - :meth:`parameters` — the canonical parameter names, kinds and
      requiredness (introspected and cached per class);
    - :meth:`missing_params` — which collected names the selected class
      cannot accept (Gate 0);
    - :meth:`instantiate` — ``selected_class(dialect, **params)`` with the
      selected class's signature defaults merged under the collected values,
      fully keyword-based.
    """

    def __init__(self, base_class: Type[Any]):
        """Bind the schema to a statement family's generic class."""
        self.base_class = base_class
        self._cache: Dict[Type[Any], Dict[str, inspect.Parameter]] = {}

    def parameters(self, cls: Type[Any]) -> Dict[str, inspect.Parameter]:
        """The constructor parameters of *cls* (introspected and cached).

        ``self`` / ``dialect`` are excluded; every other parameter is recorded
        with its kind (positional-or-keyword / keyword-only / var-positional /
        var-keyword) so acceptability and defaults can be derived.
        """
        cached = self._cache.get(cls)
        if cached is None:
            signature = inspect.signature(cls.__init__)
            cached = {
                name: param
                for name, param in signature.parameters.items()
                if name not in ("self", "dialect")
            }
            self._cache[cls] = cached
        return cached

    def missing_params(self, cls: Type[Any], collected: Dict[str, Any]) -> List[str]:
        """Collected parameter names that *cls* cannot accept (Gate 0).

        A name is accepted when the signature declares it — or the class
        forwards ``**kwargs`` (VAR_KEYWORD) to ``super``. Requiredness is not
        checked here: uncollected canonical parameters keep their signature
        defaults.
        """
        params = self.parameters(cls)
        var_keyword = any(
            param.kind == inspect.Parameter.VAR_KEYWORD for param in params.values()
        )
        return [
            name
            for name in collected
            if name not in params and not var_keyword
        ]

    def defaults(self, cls: Type[Any]) -> Dict[str, Any]:
        """Signature defaults of *cls*'s constructor parameters."""
        return {
            name: param.default
            for name, param in self.parameters(cls).items()
            if param.default is not inspect.Parameter.empty
            and param.kind
            in (
                inspect.Parameter.POSITIONAL_OR_KEYWORD,
                inspect.Parameter.KEYWORD_ONLY,
            )
        }

    def instantiate(self, cls: Type[Any], dialect: Any, collected: Dict[str, Any]) -> Any:
        """Instantiate *cls* as ``cls(dialect, **params)`` — no conversion.

        Gate 0 runs first (missing canonical parameters raise); the params
        are the selected class's signature defaults overridden by the
        collected values, passed fully keyword-based (§5.13).
        """
        missing = self.missing_params(cls, collected)
        if missing:
            raise StatementContractError(self.base_class.__name__, cls, missing)
        params = self.defaults(cls)
        params.update(collected)
        return cls(dialect, **params)
