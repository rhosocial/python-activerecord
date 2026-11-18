# src/rhosocial/activerecord/field/composite_pk.py


class CompositePKMixin:
    """
    Composite primary key helper mixin.

    Subclasses must declare __primary_key__ as a tuple of column names. A
    composite key is always the application's to supply: ``pk_auto_generated()``
    derives False from ``identity_pk_fields()``, which excludes composite keys.

    Usage:
        class OrderItem(CompositePKMixin, BaseActiveRecord):
            @classmethod
            def primary_key(cls):
                return ("order_id", "product_id")

            order_id: int
            product_id: int
            quantity: int

    A key field the *database* generates is exempt from the "must be provided"
    check: it carries no value until the INSERT has run, and today's flag cannot
    tell such a field apart from a caller-supplied one. See
    ``identity_pk_fields`` for how the exemption is decided, and note that a
    composite key mixing a generated surrogate with a caller-supplied partition
    key is exactly the case it exists for.
    """

    def __init__(self, **data):
        super().__init__(**data)
        cls = self.__class__
        try:
            generated = set(cls.identity_pk_fields())
        except Exception:  # pragma: no cover - a model whose DDL layer is absent
            generated = set()
        for field in cls.primary_key_fields():
            if field in generated:
                continue
            if getattr(self, field, None) is None:
                raise ValueError(
                    f"Composite primary key field '{field}' must be provided "
                    f"for {cls.__name__}"
                )
