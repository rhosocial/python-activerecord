# src/rhosocial/activerecord/relation/ordering.py
"""Ordering helpers shared by the sync and async ``HasMany`` descriptors.

The helpers in this module keep the sync and async ``HasMany(order_by=...)``
implementations byte-for-byte equivalent:

* :func:`normalize_order_by` validates and normalizes the constructor argument.
* :func:`resolve_order_specs` maps model field names to database column names
  and appends primary-key tie-breakers for stable results.
* :func:`apply_order_to_query` appends the resulting ORDER BY clauses.

Only model field names are accepted. Database column names, derived fields and
expression objects are intentionally rejected in this release; the relation
descriptor is declared before the related model exists, so expression objects
cannot be bound safely at class-definition time.
"""

from typing import Any, Optional, Tuple

from ..backend.expression.query_parts import SortDirection

#: A single ORDER BY entry: (model field name, direction or None for ASC).
OrderSpec = Tuple[str, Optional[SortDirection]]


def _normalize_order_item(item: Any) -> OrderSpec:
    """Normalize one ORDER BY entry to ``(field_name, direction)``."""
    if isinstance(item, str):
        return (item, None)
    if isinstance(item, tuple) and len(item) == 2 and isinstance(item[0], str):
        field_name, direction = item
        if direction is None:
            return (field_name, None)
        if not isinstance(direction, str):
            raise TypeError(
                "order_by direction must be a string such as 'ASC' or 'DESC', "
                f"got {type(direction).__name__}"
            )
        return (field_name, SortDirection.parse(direction))
    raise TypeError(
        "order_by entries must be a model field name or a "
        f"(field_name, direction) tuple, got {type(item).__name__}"
    )


def normalize_order_by(order_by: Any) -> Tuple[OrderSpec, ...]:
    """Validate and normalize the ``order_by`` constructor argument.

    Accepted forms:

    * ``"created_at"`` -- one field, default ASC.
    * ``("created_at", "DESC")`` -- one field with an explicit direction.
    * ``["created_at", ("updated_at", "DESC")]`` -- any number of entries.

    Args:
        order_by: The raw constructor argument.

    Returns:
        An immutable tuple of ``(field_name, direction)`` entries.
        ``direction`` is ``None`` when the caller did not specify one; the
        query builder then defaults to ASC.

    Raises:
        ValueError: If ``order_by`` is ``None``, empty, or uses an invalid
            direction.
        TypeError: If an entry is neither a string nor a two-item tuple.
    """
    if order_by is None:
        raise ValueError("order_by requires a non-empty specification; got None")

    if isinstance(order_by, str):
        return (_normalize_order_item(order_by),)

    # A two-item tuple whose first element is a string is a single entry,
    # not a sequence of entries.
    if (
        isinstance(order_by, tuple)
        and len(order_by) == 2
        and isinstance(order_by[0], str)
    ):
        return (_normalize_order_item(order_by),)

    if isinstance(order_by, (list, tuple)):
        if not order_by:
            raise ValueError(
                "order_by requires a non-empty specification; got an empty sequence"
            )
        return tuple(_normalize_order_item(item) for item in order_by)

    raise TypeError(
        "order_by must be a model field name, a (field_name, direction) tuple, "
        f"or a sequence of those, got {type(order_by).__name__}"
    )


def resolve_order_specs(
    specs: Tuple[OrderSpec, ...],
    model_class: Any,
    relation_name: str,
) -> Tuple[OrderSpec, ...]:
    """Validate fields against the related model and add primary-key tie-breakers.

    Field names are resolved to database column names later by
    :func:`apply_order_to_query`; this function only verifies that each name
    belongs to ``model_class.model_fields``. Derived fields are not in
    ``model_fields`` and are therefore rejected here as well.

    Args:
        specs: Normalized entries from :func:`normalize_order_by`.
        model_class: The resolved related model class.
        relation_name: The relation name, used in error messages.

    Returns:
        The normalized entries plus any missing primary-key fields, ordered ASC.

    Raises:
        ValueError: If a field is not a model field.
    """
    ordered_fields = set()
    for field_name, _direction in specs:
        if field_name not in model_class.model_fields:
            raise ValueError(
                f"Invalid order_by field `{field_name}` for relation "
                f"`{relation_name}` on {model_class.__name__}: only model field "
                "names are supported (not database column names, derived fields, "
                "or expression objects)."
            )
        ordered_fields.add(field_name)

    resolved = list(specs)
    for pk_field in model_class.primary_key_fields():
        if pk_field not in ordered_fields:
            # A primary key that is not a model field cannot be ordered by
            # name; skip it rather than turning a stability aid into an error.
            if pk_field in model_class.model_fields:
                resolved.append((pk_field, SortDirection.ASC))
    return tuple(resolved)


def apply_order_to_query(query: Any, model_class: Any, relation_name: str, specs: Tuple[OrderSpec, ...]) -> Any:
    """Append the resolved default ordering to *query*.

    Args:
        query: The query object to extend.
        model_class: The resolved related model class.
        relation_name: The relation name, used in error messages.
        specs: Normalized entries from :func:`normalize_order_by`.

    Returns:
        The same query object, for chaining.

    Raises:
        ValueError: If a field is not a model field.
    """
    resolved = resolve_order_specs(specs, model_class, relation_name)
    for field_name, direction in resolved:
        column_name = model_class.get_column_name(field_name)
        if direction is None:
            query = query.order_by(column_name)
        else:
            query = query.order_by((column_name, direction))
    return query
