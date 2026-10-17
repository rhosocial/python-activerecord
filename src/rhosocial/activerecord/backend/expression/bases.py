# src/rhosocial/activerecord/backend/expression/bases.py
"""
Core abstract base classes for the SQL expression engine.

This module forms the foundation of the expression hierarchy and should
have no dependencies on other modules within the `expression` package
to prevent circular imports.
"""

import inspect
import sys
import warnings
from enum import Enum
from typing import Dict, Any, Optional, Tuple, Protocol, TYPE_CHECKING, Union
from typing import runtime_checkable

if sys.version_info >= (3, 10):
    from typing import TypeAlias  # pragma: no cover
else:
    from typing_extensions import TypeAlias  # pragma: no cover

from .mixins import AliasableMixin, LogicalMixin

# Type alias for the return type of to_sql() method
# This alias represents the standard return format for all SQL expression objects:
# a tuple containing the SQL string and a tuple of parameters for prepared statements.
# Using this alias improves code readability and maintainability by providing
# a consistent type definition across the entire expression system.
SQLQueryAndParams: TypeAlias = Tuple[str, tuple]
# TypeAlias annotation is for static type checkers; at runtime, the object's
# __module__ attribute still points to 'typing'. We explicitly set it here
# so introspection tools can correctly identify the defining module.
SQLQueryAndParams.__module__ = __name__


def is_sql_query_and_params(obj):
    """Check if an object is of type SQLQueryAndParams (Tuple[str, tuple]).

    Args:
        obj: The object to check

    Returns:
        bool: True if the object is a SQLQueryAndParams tuple, False otherwise
    """
    return (
        isinstance(obj, tuple)
        and len(obj) == 2
        and isinstance(obj[0], str)
        and (isinstance(obj[1], tuple) or obj[1] is None)
    )


def require_exclusive_options(flag_a: bool, flag_b: bool, name_a: str, name_b: str) -> None:
    """Refuse a clause whose two spellings were both requested.

    A two-spelling clause (``CASCADE`` / ``RESTRICT``, ``DEFERRABLE`` /
    ``NOT DEFERRABLE``) is two parameters, not one option with three values.
    Asking for both is API misuse, and the refusal is worded once here so
    every clause reports it the same way instead of each restating the
    sentence.

    This is an internal-consistency question, not a dialect-capability one: no
    backend can render ``CASCADE RESTRICT``, so the answer does not depend on
    which formatter will later render the expression. It therefore stays at
    construction time rather than moving into the formatter.

    Args:
        flag_a: whether the first spelling was requested
        flag_b: whether the second spelling was requested
        name_a: parameter name of the first spelling
        name_b: parameter name of the second spelling

    Raises:
        ValueError: if both spellings were requested
    """
    if flag_a and flag_b:
        raise ValueError(f"{name_a} and {name_b} are mutually exclusive options")


if TYPE_CHECKING:  # pragma: no cover
    from ..dialect import SQLDialectBase
    from .collation import CollateFunction


@runtime_checkable
class ToSQLProtocol(Protocol):
    """
    Protocol for objects that can be converted into a SQL string and a tuple of parameters.

    This protocol follows the DB-API 2.0 specification (PEP 249) requirement for separating
    SQL statements from parameters to prevent SQL injection attacks.
    See: https://peps.python.org/pep-0249/

    Security Notice:
    1. For backend developers: Any code involving database interfaces or SQL formatting
       must strictly follow this protocol by separating SQL fragments and parameters
       to prevent SQL injection attacks.
    2. For application developers: When interacting with the database, always pass
       query parameters through the designated parameter mechanisms rather than
       directly concatenating values into SQL strings to prevent SQL injection.
    """

    def to_sql(self) -> "SQLQueryAndParams":  # pragma: no cover
        """
        Converts the object into a SQL string and a tuple of parameters.
        """
        ...

    inline_params: bool  # pragma: no cover
    """
    Whether this expression class renders its literal values **inline** (as
    SQL text) instead of as bind parameters.

    This is a **class-level rendering strategy**, decided once when the class
    is defined — never per instance and never per call site. DDL syntax
    positions (``DEFAULT`` / ``CHECK`` / partition boundaries / index
    expressions) accept no bind parameters, so the classes that belong to
    those positions declare ``True``; DQL/DML data positions keep ``False``
    (bind parameters, the injection-safe default). See ``BaseExpression``.
    """


@runtime_checkable
class SQLLiteral(Protocol):
    """The literal-construction protocol (the third level of inline literal
    construction).

    A **value type definer** implements this protocol so instances of the
    type can render themselves as a complete inline SQL literal. It exists
    for user-defined and backend-specific value types that no dialect
    build-in whitelist knows (``Point``, ``inet``, an Interval wrapper, ...):
    whoever defines the type owns its literal spelling.

    The contract:

    - ``__sql_literal__(dialect)`` returns the **complete** inline literal
      text, quotes included — the dialect embeds it verbatim;
    - every string component inside that text must be escaped through the
      dialect's **public** escape helpers (:meth:`SQLDialectBase.escape_sql_string`
      or :meth:`SQLDialectBase.format_literal`); hand-concatenated quoting is
      a violation;
    - the dialect embeds the returned text as an atom, so the implementation
      must keep placeholder-looking characters inside quoted string data.

    This protocol is a **rendering** duty. It is not :class:`DataType` and
    has no relationship to DDL column-type declaration: a type may implement
    one, the other, or both, and implementing one never implies the other.
    """

    def __sql_literal__(self, dialect: "SQLDialectBase") -> str:  # pragma: no cover
        """Return the complete inline SQL literal text for this value."""
        ...


class BaseExpression:
    """
    Shared protocol-attribute implementation for every SQL expression.

    Satisfies the :class:`ToSQLProtocol` contract **structurally** — explicit
    inheritance is neither required nor used (a protocol is structural; this
    base is the shared implementation of its members):

    - :attr:`dialect` property — validated binding (constructor-optional,
      late binding via the setter; **per-node only, no propagation**);
    - :attr:`inline_params` class attribute — the inline-literal rendering
      strategy (defaults to ``False`` for injection safety).

    Rendering is **centralised** and **stateless**: :meth:`to_sql` is
    implemented once, here, and is the only rendering entry point. A concrete
    expression class participates by declaring exactly one thing — its
    dialect formatting method name, through the read-only :attr:`format_method`
    property. ``to_sql()`` resolves that name on the node's own bound dialect
    (raising if unbound or if the dialect does not provide it) and hands
    **this** expression to the formatting function. The rendered tree is
    responsible for its own per-node dialect binding; no reconstruction or
    propagation happens at render time.
    """

    def __init__(self, dialect: Optional["SQLDialectBase"] = None):
        """
        Initializes the base SQL expression with a specific dialect.

        *dialect* is the conventional first argument but **optional** — it may
        be supplied later through the :attr:`dialect` property (e.g. model
        declaration time has no dialect; DDL generation binds one).
        """
        self.dialect = dialect

    @property
    def dialect(self) -> "SQLDialectBase":
        """The dialect bound to this expression.

        Reading it **validates** that a dialect is bound: rendering requires
        one, so access before binding raises ``ValueError`` (bind via
        construction or the setter). Construction-time state flows through
        ``self._dialect`` instead (operators inherit the honest binding
        state, ``None`` included).
        """
        if self._dialect is None:
            raise ValueError(
                f"{type(self).__name__} has no dialect bound. Provide one at "
                f"construction time (first argument) or set it through the "
                f"dialect property."
            )
        return self._dialect

    @dialect.setter
    def dialect(self, dialect: Optional["SQLDialectBase"]) -> None:
        """Bind (or re-bind) the dialect used to render this expression.

        The dialect must be a :class:`SQLDialectBase` instance (``None`` is
        allowed to defer binding).

        The setter affects **only this node** — it does not propagate into
        child expressions. Binding is the constructor's/caller's per-node
        responsibility: pass the dialect to each node at construction time,
        or walk the tree and bind nodes individually (ActiveRecord's DDL
        derivation does exactly that at build time). Rendering
        (:meth:`to_sql`) requires the dialect of the node being rendered and
        raises ``ValueError`` if none is bound.
        """
        if dialect is not None:
            from ..dialect import SQLDialectBase

            if not isinstance(dialect, SQLDialectBase):
                raise TypeError(
                    f"dialect must be a SQLDialectBase instance, got "
                    f"{type(dialect).__name__}."
                )
        self._dialect = dialect

    @property
    def format_method(self) -> str:
        """Name of the dialect formatting method that renders this expression.

        **Read-only by contract.** Each concrete expression class declares —
        exactly once, for itself — the name of the single ``format_*()``
        method on the dialect that renders it, by overriding this getter
        (a plain ``@property`` returning the name string; the base has no
        setter, so the declaration cannot be mutated at runtime).

        :class:`BaseExpression.to_sql` resolves the name against the bound
        dialect and raises ``UnsupportedFeatureError`` if the dialect does not
        provide it. An expression class that does not override this getter
        is not renderable: reading it raises ``NotImplementedError``.
        """
        raise NotImplementedError(
            f"{type(self).__name__} does not declare its dialect "
            f"formatting method name. Override the `format_method` "
            f"property to return the name of the dialect's format_*() "
            f"method that renders it."
        )

    def to_sql(self) -> "SQLQueryAndParams":
        """Unified rendering entry point for every expression.

        Implemented **once, here** — expression subclasses never override it.

        Rendering is **stateless and allocation-free**: the tree being
        rendered is responsible for its own dialect binding (every node is
        bound at construction time, or individually re-bound by the caller /
        ActiveRecord's DDL derivation before rendering). No reconstruction,
        no propagation, no copies.

        1. Resolve this class's declared formatting method name
           (:attr:`format_method`; undeclared → ``NotImplementedError``) and
           look it up on the bound dialect (missing →
           ``UnsupportedFeatureError``, matching how every other capability gap
           in the tree is reported; unbound dialect → ``ValueError`` from
           :attr:`dialect`).
        2. Call the formatting function with **this** expression —
           formatting functions receive expression instances only.
        3. Check what came back. This step exists because a lookup that found
           *something* callable is not the same as finding a formatter.

        The check in step 3 is not defensive padding. A ``runtime_checkable``
        protocol is satisfied by its own ``...`` bodies, so a probe-only
        protocol sitting in a dialect's base list answers ``getattr`` and
        passes the callable test while returning ``None``. Three backends hit
        that independently -- ``CreateFunctionStatement(...).to_sql()``
        answering ``None``, ``Domain.to_sql()`` answering ``None``, a
        formatter returning a bare string instead of a pair -- and each was
        invisible because nothing inspected the result. A formatting method
        that answers with the wrong shape is not a formatting method.

        Returns:
            A tuple containing:
            - str: The SQL string
            - tuple: The parameter values for prepared statement execution

        Raises:
            UnsupportedFeatureError: The dialect has no such formatting method.
            ProtocolNotImplementedError: What answered the lookup was a
                protocol rather than a formatter, so the dialect has not
                implemented the feature.
            TypeError: A formatting method answered with something other than
                ``(sql, params)``.
        """
        from ..dialect.exceptions import (
            ProtocolNotImplementedError,
            UnsupportedFeatureError,
        )

        formatter_name = self.format_method
        formatter = getattr(self.dialect, formatter_name, None)
        if formatter is None or not callable(formatter):
            raise UnsupportedFeatureError(
                dialect_name=self.dialect.name,
                feature_name=f"the '{formatter_name}' statement",
                suggestion=(
                    f"{type(self.dialect).__name__} declares no "
                    f"'{formatter_name}', which {type(self).__name__} needs; "
                    f"mix in the mixin that provides it, or override "
                    f"format_method on {type(self).__name__} to name one this "
                    f"dialect has"
                ),
            )
        rendered = formatter(self)
        if rendered is None:
            raise ProtocolNotImplementedError(
                dialect_name=self.dialect.name,
                protocol_name=formatter_name,
                required_by=type(self).__name__,
            )
        if not (
            isinstance(rendered, tuple)
            and len(rendered) == 2
            and isinstance(rendered[0], str)
        ):
            raise TypeError(
                f"{type(self.dialect).__name__}.{formatter_name} returned "
                f"{type(rendered).__name__} for {type(self).__name__}, but a "
                f"formatting method must return (sql, params). A protocol "
                f"declaring '{formatter_name}' satisfies isinstance "
                f"structurally, so putting one in a dialect's base list can "
                f"answer a lookup that meant a formatter; and a formatter "
                f"returning a bare string silently loses its bind parameters."
            )
        return rendered

    def validate(self, strict: bool = True) -> None:
        """Validate expression parameters according to SQL standard.

        The correct usage of this function is to catch whether it raises an error.
        If no error is raised, it indicates that the validation has passed.
        Users can use this to quickly determine if the input parameters are appropriate.
        The error type is generally TypeError, but we do not enforce this,
        so users should be aware of all possible error types.

        Args:
            strict: If True, perform strict validation that may impact performance.
                   If False, skip validation for performance optimization.

        Raises:
            Exception: Subclasses may raise various exceptions to indicate validation failure
        """
        pass  # pragma: no cover

    inline_params: bool = False
    """Class-level inline-literal rendering strategy (see
    :class:`ToSQLProtocol` for the contract): **False** — bind parameters are
    the safe default, and DQL/DML data positions keep it. A class that belongs
    to a DDL syntax position (``DEFAULT`` / ``CHECK`` / partition boundaries /
    index expressions — positions that accept no bind parameters) declares
    ``True`` when it is defined, and its formatter then renders contained
    values as dialect-controlled inline literals.

    Whether inlining happens is decided by the **class**, once: the syntax
    position may not overrule it, and it may not be flipped per instance —
    formatters read ``type(expr).inline_params``, so an instance-level
    assignment has no effect on rendering."""

    def get_params(self) -> Dict[str, Any]:
        """Introspection-based default implementation.

        Iterates the class __init__ signature (excluding `self` and `dialect`),
        and resolves each parameter to its stored attribute value using the
        convention:  param `foo`  →  self._foo  (fallback: self.foo)

        VAR_POSITIONAL (*args) parameters are returned as a list.
        VAR_KEYWORD (**kwargs) parameters are resolved through the same
        convention — a class that accepts **kwargs MUST store the collected
        extras under an attribute named after the parameter (e.g. `self.kwargs`
        or `self.collation_options`) so the round-trip can reconstruct them.
        """
        sig = inspect.signature(self.__class__.__init__)
        params: Dict[str, Any] = {}

        for name, param in sig.parameters.items():
            if name in ("self", "dialect"):
                continue

            # One spelling, and it is the parameter's own name. This used to
            # probe `_{name}` then `name` and pick between them by testing
            # whether the public one was callable, because eighteen fluent
            # setters were named exactly like their constructor parameters
            # (`schema`, `table_name`, `include_columns`, `begin_type`, …) and
            # the value could not then be written as `self.schema = ...` without
            # shadowing the method. The setters are `with_*` now, so the
            # parameter owns the name and there is nothing to decide.
            #
            # Nothing is skipped when the attribute is absent: a parameter the
            # class did not store is a defect, and the AttributeError says which
            # class and which parameter. The old branch warned and carried on,
            # which put the omission in the artifact with nothing to show for it.
            value = getattr(self, name)

            if param.kind == inspect.Parameter.VAR_KEYWORD:
                # **kwargs extras must be stored as a dict on an attribute named
                # after the parameter (e.g. self.kwargs, self.collation_options).
                # They are merged into the top-level params so that
                # reconstruction `cls(..., **value)` re-expands them correctly.
                if not isinstance(value, dict):
                    warnings.warn(
                        f"{self.__class__.__name__}.get_params(): VAR_KEYWORD "
                        f"parameter '{name}' is not stored as a dict (got "
                        f"{type(value).__name__}). Store the collected kwargs "
                        "in an attribute of the same name as a dict.",
                        stacklevel=2,
                    )
                    continue
                params.update(value)
            elif param.kind == inspect.Parameter.VAR_POSITIONAL:
                params[name] = list(value)
            else:
                params[name] = value

        return params


class SQLPredicate(LogicalMixin, AliasableMixin, BaseExpression):
    """Base class for SQL expressions that return a boolean value.

    Carries :class:`AliasableMixin` because a predicate is not confined to a
    WHERE clause. ``LIKE`` and its relatives also appear in a SELECT list
    (``SELECT name LIKE 'a%' AS is_apple``), inside ``CASE WHEN``, in a
    ``JOIN ... ON`` condition, and in DDL as a ``CHECK`` constraint or a
    partial-index predicate. In the projection case the result needs a name
    like any other column, so the alias has to survive to the formatter.
    """

    pass


class SQLValue(BaseExpression):
    """
    Abstract base class for SQL expressions that return a non-boolean value
    (e.g., integer, string, date).

    This class may define convenience factory methods for SQL value expressions.
    These methods only guarantee syntactically valid SQL expression generation.
    They do not validate whether the underlying database value type supports the
    generated operation, so the final executability may still depend on backend
    type rules.
    """

    def __init__(self, dialect: "SQLDialectBase"):
        super().__init__(dialect)

    def collate(
        self,
        collation: Union[str, Enum],
        **collation_options: Any,
    ) -> "CollateFunction":
        """
        Apply an explicit SQL COLLATE clause to this value expression.

        This method only guarantees syntactically valid COLLATE expression
        generation. It does not validate whether the underlying database value
        type supports collation. Callers must apply it only to expressions that
        are valid for the target backend, typically text/string expressions.
        """
        from .collation import CollateFunction

        return CollateFunction(self.dialect, self, collation, **collation_options)
