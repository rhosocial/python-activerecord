# src/rhosocial/activerecord/field/composite_pk.py
from typing import ClassVar


class CompositePKMixin:
    """
    Composite primary key helper mixin.

    Subclasses must declare __primary_key__ as a tuple of column names and
    should set __pk_auto_generated__ = False since composite PKs are typically
    provided by the application layer.

    Usage:
        class OrderItem(CompositePKMixin, BaseActiveRecord):
            __primary_key__ = ("order_id", "product_id")
            order_id: int
            product_id: int
            quantity: int
    """
    __pk_auto_generated__: ClassVar[bool] = False

    def __init__(self, **data):
        super().__init__(**data)
        cls = self.__class__
        for field in cls.primary_key_fields():
            if getattr(self, field, None) is None:
                raise ValueError(
                    f"Composite primary key field '{field}' must be provided "
                    f"for {cls.__name__}"
                )
