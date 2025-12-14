# src/rhosocial/activerecord/backend/field.py
"""
Defines typed SQL field representations, including the base `SQLField` class
and its subclasses, which act as typed column expressions in queries.
"""
from typing import Any, Type, Generic, TypeVar, Tuple, Optional, Union

from .expression import SQLExpression
from .dialect import SQLDialectBase

T = TypeVar("T")


class SQLField(SQLExpression, Generic[T]):
    """
    Abstract base class for all SQL field types. It represents a typed column
    in a SQL query expression.
    """
    python_type: Type[T] = Any

    def __init__(self, name: Optional[str] = None, table: Optional[str] = None, **kwargs):
        self.name = name
        self.table = table

    def to_sql(self, dialect: SQLDialectBase) -> Tuple[str, tuple]:
        """Converts the column representation to a SQL string."""
        if self.name is None:
            raise TypeError(f"Cannot render a '{self.__class__.__name__}' type definition directly to SQL. "
                            "It must be instantiated as a column representation via the model proxy (e.g., Model.c.field).")
        
        name = dialect.format_identifier(self.name)
        if self.table:
            table = dialect.format_identifier(self.table)
            return f"{table}.{name}", ()
        return name, ()

    def __repr__(self) -> str:
        if self.name:
            return f"{self.__class__.__name__}({self.name!r})"
        return f"{self.__class__.__name__}()"


# --- Generic Field Types ---

class StringField(SQLField[str]):
    python_type = str


class IntegerField(SQLField[int]):
    python_type = int


class FloatField(SQLField[float]):
    python_type = float


class BooleanField(SQLField[bool]):
    python_type = bool


class BytesField(SQLField[bytes]):
    python_type = bytes


# --- Specialized Field Types (Convenience) ---

class TextField(StringField):
    """Represents a TEXT type."""
    pass


class BigInt(IntegerField):
    """Represents a BIGINT type."""
    pass


class SmallInt(IntegerField):
    """Represents a SMALLINT type."""
    pass


# --- PostgreSQL Specific Types ---

class PGInetField(StringField):
    """Represents PostgreSQL's INET type."""
    pass


class PGJSONField(SQLField[Union[dict, list]]):
    """Represents PostgreSQL's JSON type."""
    pass


class PGJSONBField(PGJSONField):
    """Represents PostgreSQL's JSONB type."""
    pass


class PGArrayField(SQLField[list]):
    """
    Represents PostgreSQL's ARRAY type. This class serves a dual purpose:
    1. As a column expression: `PGArrayField(name='my_col', table='my_table')`
    2. As a type annotation: `PGArrayField(item_type=IntegerField)`
    """

    def __init__(self, name: Optional[str] = None, table: Optional[str] = None, *, item_type: Optional[Union[SQLField, Type[SQLField]]] = None):
        super().__init__(name=name, table=table)
        
        if name is None and item_type is None:
            # Allow empty constructor for type resolution purposes
            pass

        if item_type:
            if isinstance(item_type, type):
                self.item_type = item_type()
            else:
                self.item_type = item_type
        else:
            self.item_type = None

    def __repr__(self) -> str:
        if self.name:
            return super().__repr__()
        if self.item_type:
            return f"{self.__class__.__name__}(item_type={self.item_type!r})"
        return f"{self.__class__.__name__}()"