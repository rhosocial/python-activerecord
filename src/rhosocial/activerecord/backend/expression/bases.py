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
from contextvars import ContextVar
from enum import Enum
from typing import Dict, Any, Optional, Tuple, Protocol, TYPE_CHECKING, Union, List
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

#: The dialect a render is running under, when the caller supplied one.
#:
#: Expressions built for a declaration carry no dialect: at that moment no
#: backend has been opened, so nobody knows which dialect will render them.
#: The environment fixture binds one at render time instead, and the nodes
#: below the rendered root resolve it from here. Symbolically this is the
#: caller's argument threaded down the tree without every formatter having to
#: pass it along.
_RENDER_DIALECT: ContextVar[Any] = ContextVar("expression_render_dialect", default=None)


def _camel_to_words(name: str) -> List[str]:
    """Split *name* into the words its capitals mark off.

    Two boundaries divide a camel-case name: between a run of capitals and
    the capital that starts a lowercase word (``JSONValue`` -> ``JSON``,
    ``Value``), and between a lowercase letter or digit and a following
    capital (``SQLDialect`` -> ``SQL``, ``Dialect``). The scan inserts a
    break at those positions and returns the pieces; lowering and joining
    them with underscores is the caller's job.
    """
    words = []
    piece_start = 0
    for index, char in enumerate(name):
        if index == 0 or not ("A" <= char <= "Z"):
            continue
        previous = name[index - 1]
        following = name[index + 1] if index + 1 < len(name) else ""
        runs_into_lower = "A" <= previous <= "Z" and "a" <= following <= "z"
        follows_lower = "a" <= previous <= "z" or "0" <= previous <= "9"
        if runs_into_lower or follows_lower:
            words.append(name[piece_start:index])
            piece_start = index
    words.append(name[piece_start:])
    return words


def current_dialect() -> Optional[Any]:
    """The dialect of the render in progress, or ``None``."""
    return _RENDER_DIALECT.get()


class QueryWithParams:
    """The shape of a SQL string together with its parameters.

    ``SQLQueryAndParams`` stays a type alias: it appears in annotations and in
    pydantic models, where a class would change the field's schema rather than
    describe it. This class owns the *check* instead, so the shape is stated
    once, beside the alias that names it, and callers reach it as a member
    rather than as a free function.

    The five places that ask the question are in three unrelated families --
    the model bases, the expression tree, and the query protocols -- and they
    share no ancestor, so there is no base class to hang this on.
    """

    @classmethod
    def holds(cls, obj: Any) -> bool:
        """Whether *obj* has the shape of a query with its parameters.

        Args:
            obj: The object to check

        Returns:
            bool: True if the object is a SQLQueryAndParams tuple, False
            otherwise
        """
        return (
            isinstance(obj, tuple)
            and len(obj) == 2
            and isinstance(obj[0], str)
            and (isinstance(obj[1], tuple) or obj[1] is None)
        )


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

    @classmethod
    def quote_flag(cls, value: Any, name: str) -> bool:
        """A quoting flag, or a failure naming where it came from.

        These flags are ``bool`` with no third state. There is no "unspecified" to
        represent, because the formatter never meets an absent one -- the value is
        settled at construction and carried on the artifact (§10.1). So the only way
        a flag goes wrong is a caller passing something that is not a bool, and
        ``None`` is the one that arrives by accident: it reads as "I did not think
        about it" and lands on the branch that writes the identifier out with
        nothing escaped.

        The annotation already says ``bool``. Python does not enforce annotations,
        so this is where the type is actually checked.
        """
        if not isinstance(value, bool):
            raise TypeError(
                f"{cls.__name__}.{name} must be a bool, got {type(value).__name__}. "
                "Quoting is decided per position and has no 'unspecified' state: "
                "pass True to quote, False to write the identifier as it stands."
            )
        return value

    @staticmethod
    def require_exclusive_options(flag_a: bool, flag_b: bool, name_a: str, name_b: str) -> None:
        """Refuse a clause whose two spellings were both requested.

        A two-spelling clause (``CASCADE`` / ``RESTRICT``, ``DEFERRABLE`` /
        ``NOT DEFERRABLE``) is two parameters, not one option with three values.
        Asking for both is API misuse, and the refusal is worded once here so
        every clause reports it the same way instead of each restating the
        sentence.

        This is an internal-consistency question, not a dialect-capability one:
        no backend can render ``CASCADE RESTRICT``, so the answer does not
        depend on which formatter will later render the expression. It
        therefore stays at construction time rather than moving into the
        formatter.

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

    """
    Shared protocol-attribute implementation for every SQL expression.

    Satisfies the :class:`ToSQLProtocol` contract **structurally** — explicit
    inheritance is neither required nor used (a protocol is structural; this
    base is the shared implementation of its members):

    - :attr:`dialect` property — validated binding (constructor-optional,
      late binding via the setter; **per-node only, no propagation**);

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

        Reading it **validates** that a dialect is available: rendering requires
        one, so access with no binding and no active render raises
        ``ValueError``.  Three sources are honoured, most specific first:

        1. the dialect bound to this node (constructor or setter);
        2. the dialect of the render in progress (:func:`current_dialect`),
           which is how a tree built for a declaration renders without every
           node being bound by hand;
        3. nothing -- raise.

        Construction-time state flows through ``self._dialect`` instead
        (operators inherit the honest binding state, ``None`` included).
        """
        if self._dialect is not None:
            return self._dialect
        active = current_dialect()
        if active is not None:
            return active
        raise ValueError(
            f"{type(self).__name__} has no dialect bound. Provide one at "
            f"construction time (first argument), through the dialect property, "
            f"or render it with to_sql(dialect)."
        )

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

    def to_sql(self, dialect: Optional["SQLDialectBase"] = None) -> "SQLQueryAndParams":
        """Render this expression, optionally binding the dialect for the tree.

        A dialect reaches a node two ways, both valid:

        * bound at construction or through the setter, per node;
        * passed here once.  That is how a tree assembled for a declaration
          renders: at assembly time no backend exists, so no node could be
          bound.  The argument becomes the render's active dialect and the
          nodes below resolve it from there, instead of every node having to
          be bound one by one.
        """
        if dialect is None:
            return self._render()
        token = _RENDER_DIALECT.set(dialect)
        try:
            return self._render()
        finally:
            _RENDER_DIALECT.reset(token)

    def check_dialect(self, dialect: "SQLDialectBase") -> None:
        """Hook: refuse a dialect this node cannot be rendered against.

        Called on every render, and at construction when a dialect is
        supplied, so a node whose correctness depends on the grammar it renders
        with states that in one place rather than at every construction site.
        """
        return None

    def _render(self) -> "SQLQueryAndParams":
        """Unified rendering entry point for every expression.

        Implemented **once, here** — expression subclasses never override it.

        Rendering is **stateless and allocation-free**: the tree being
        rendered is responsible for its own dialect binding (every node is
        bound at construction time, or individually re-bound by the caller /
        ActiveRecord's DDL derivation before rendering). No reconstruction,
        no propagation, no copies.

        A node carrying non-empty ``hints`` (an optional optimizer-directive
        payload on the statement classes) is refused here unless the dialect
        answers ``supports_statement_hints()`` truthy, because a dialect that
        does not spell them must refuse rather than silently drop them. The
        check sits on this single rendering entry point, so a backend that
        overrides a statement formatter still gets the refusal.

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

        self._check_required_present()
        self.check_renderable()
        dialect = self.dialect
        self.check_dialect(dialect)
        hints = getattr(self, "hints", ())
        if hints and not dialect.supports_statement_hints():
            raise UnsupportedFeatureError(
                dialect_name=dialect.name,
                feature_name="optimizer hints",
                suggestion=(
                    f"{dialect.name} does not spell optimizer-directive "
                    f"comments (/*+ ... */) attached to a statement; install "
                    f"and enable the hint extension for this backend, or drop "
                    f"the hints from the statement"
                ),
            )
        formatter_name = self.format_method
        formatter = getattr(dialect, formatter_name, None)
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

    def _check_required_present(self) -> None:
        """Refuse a render whose payload is incomplete, naming the field.

        The constructor signature says which parameters are required, but a
        signature is only a *hint*: Python does not enforce annotations, and
        two paths reach a node without the constructor ever seeing them.

        * an explicit ``None`` passed for a required parameter;
        * an artifact rebuilt from ``{"kind", "params"}`` whose ``params``
          simply omit the field.

        A formatter that rendered such a node would emit SQL for an expression
        the caller never expressed, and the missing field would surface later
        as an unrelated failure deep inside the formatter. So the check is
        made here, once, before dispatch:

        * a required parameter is one without a default in ``__init__``;
          ``dialect`` is excluded because rendering binds it;
        * "present" means not ``None``. Falsy values (``0``, ``False``,
          ``""``) are real payloads and are not missing.

        A missing field is a caller/artifact defect, so the error is
        ``TypeError``. A dialect that cannot render the feature is a different
        answer and must never be impersonated: that is
        :class:`UnsupportedFeatureError`, raised by the formatter.
        """
        sig = inspect.signature(self.__class__.__init__)
        nullable = type(self).NULLABLE_REQUIRED
        missing: List[str] = []
        for name, param in sig.parameters.items():
            if name in ("self", "dialect") or name in nullable:
                continue
            if param.kind in (
                inspect.Parameter.VAR_POSITIONAL,
                inspect.Parameter.VAR_KEYWORD,
            ):
                continue
            if param.default is not inspect.Parameter.empty:
                continue
            if getattr(self, name, None) is None:
                missing.append(name)
        if missing:
            raise TypeError(
                f"{type(self).__name__} cannot render: required parameter(s) "
                f"{', '.join(sorted(missing))} are None. A required parameter "
                f"is present by construction but may be None — passed "
                f"explicitly, or absent from the artifact's params. Supply the "
                f"value; do not expect the formatter to invent one."
            )

    def check_renderable(self) -> None:
        """Hook: refuse a node whose collected payload cannot be rendered.

        Called on every render, after the required-parameter check and before
        the formatter is looked up. A node overrides it when a payload
        constraint cannot be expressed as "the parameter is absent": an empty
        key list, two mutually exclusive flags, a value of the wrong shape.

        This is a rendering-phase check on purpose. The constructor only
        collects (a node must always build, or no stored artifact could be
        read back), while the answer "this payload is not renderable" is a
        caller error and belongs to the moment the SQL is asked for. It raises
        :class:`TypeError`, never
        :class:`~..dialect.exceptions.UnsupportedFeatureError`: a malformed
        payload is not a missing dialect feature.
        """
        return None

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


    #: Tokens at the head of a class name that are a single word and must not
    #: be split when the kind is derived (§4.9.4). Empty on the core.
    #:
    #: The general rule — a run of capitals is one word — disagrees with the
    #: backend identifier table for several backends: applied naively it
    #: yields ``sq_lite_json_extract_function`` for ``SQLiteJsonExtractFunction``
    #: and ``my_sql_upsert_clause`` for ``MySQLUpsertClause``. Since the kind is
    #: part of the wire contract (§4.11.1), a backend whose identifier is a
    #: compound word declares it here and its own expressions keep it whole.
    #:
    #: A backend owns this list: it is the backend's naming, not the core's, and
    #: adding a backend must not require editing the core. What a subclass may
    #: override is this list, never :meth:`kind` — the kind is always computed
    #: from the class name, never stored, so the two cannot drift apart (§4.11.1:
    #: an independent identifier table "would drift from the class names, and
    #: that drift directly breaks existing artifacts").
    KIND_RESERVED: Tuple[str, ...] = ()

    #: Whether an assembled registry admits this node by default (§7).
    #:
    #: Set it ``False`` for a node whose rendered SQL is text the caller vouched
    #: for. The artifact is untrusted input (§10), so admitting such a kind into
    #: the table a reader resolves against would let the artifact choose raw SQL:
    #: the reader would rebuild a node whose ``to_sql()`` emits whatever the
    #: payload said. Excluding it keeps that out of reach by default.
    #:
    #: This is a *default*, not a prohibition. Nothing stops a caller who trusts
    #: its artifacts from registering the class itself — the registry is
    #: assembled from the expressions a distribution ships, and which ones those
    #: are is the distribution's call. Deciding it per class, next to the class,
    #: is what keeps the framework from carrying a list of names it would then
    #: have to keep in step.
    REGISTER_BY_DEFAULT: bool = True

    #: Required parameters whose own value may legitimately be ``None``.
    #:
    #: "Required" answers whether the parameter must be *supplied*; it does not
    #: answer whether ``None`` is a legal value. ``Literal(dialect, None)`` is
    #: the SQL ``NULL``, ``DEFAULT NULL`` is a real declaration, and
    #: ``SET DEFAULT NULL`` is a real action, so a render-time existence check
    #: that refused every ``None`` would refuse valid SQL.
    #:
    #: A class that carries such a position declares it here, by parameter name.
    #: It is a statement about the node's own vocabulary, made next to the class,
    #: so the framework never has to keep a list of exceptions in step.
    NULLABLE_REQUIRED: "frozenset" = frozenset()


    @classmethod
    def kind(cls) -> str:
        """Derive this expression's kind from its class name (§4.11.1).

        The kind is the class name's snake_case form, with a run of consecutive
        capitals counted as one word (``JSONValue`` → ``json_value``,
        ``SQLDialect`` → ``sql_dialect``), except that any token named in
        :attr:`KIND_RESERVED` that starts the name is kept whole
        (``SQLiteTopClause`` → ``sqlite_top_clause``).

        Computed, never stored: a class carries no kind field, so a kind can
        never disagree with the class that produced it.
        """
        name = cls.__name__
        for token in cls.KIND_RESERVED:
            if name.startswith(token) and len(name) > len(token):
                rest = "_".join(word.lower() for word in _camel_to_words(name[len(token):]))
                return token.lower() + "_" + rest
        return "_".join(word.lower() for word in _camel_to_words(name))

    def get_params(self) -> Dict[str, Any]:
        """Introspection-based default implementation.

        Iterates the class __init__ signature (excluding `self` and `dialect`),
        and reads each parameter off the attribute of the same name: param `foo`
        is read from `self.foo`. One spelling, no probing -- a parameter the
        class did not store raises `AttributeError` naming the class and the
        parameter, which is the defect this method exists to surface.

        VAR_POSITIONAL (*args) parameters are returned as a list.
        VAR_KEYWORD (**kwargs) parameters are read from a dict stored under the
        parameter's own name and merged into the top level, so that
        reconstruction `cls(..., **value)` re-expands them. Expressions should
        not declare **kwargs at all: an artifact names its parameters, and a
        catch-all accepts names no artifact can ever carry.
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
                # after the parameter (e.g. self.kwargs).
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
        schema: Optional[str] = None,
    ) -> "CollateFunction":
        """
        Apply an explicit SQL COLLATE clause to this value expression.

        This method only guarantees syntactically valid COLLATE expression
        generation. It does not validate whether the underlying database value
        type supports collation. Callers must apply it only to expressions that
        are valid for the target backend, typically text/string expressions.
        """
        from .collation import CollateFunction

        return CollateFunction(self.dialect, self, collation, schema=schema)
