# src/rhosocial/activerecord/backend/expression/types/integer.py
"""Integer SQL type family.

``INT`` is SQL's own shorthand for ``INTEGER``, and MySQL spells the narrower
widths ``INT1`` / ``INT2`` / ``INT8``. Those are spellings of one width, so each
width is one class with a :attr:`SPELLINGS` list — not two classes.

``UNSIGNED`` is a different thing: SQL:2003 had it as an attribute and SQL:2011
removed it (feature T211), but MySQL, MariaDB and ClickHouse all still keep it,
and it changes the representable range, so it is a different **type** — a field
rather than a class, because width is already this family's class axis and a
linear chain cannot hold a (width x signedness) grid.
"""

from __future__ import annotations

from ._base import DataType


class TinyIntType(DataType):
    """TINYINT / INT1 (8-bit)."""

    name = "tinyint"

    SPELLINGS = ("tinyint", "int1")

    unsigned: bool = False

    def __init__(self, dialect=None, *, unsigned: bool = False,
                 spelling: str = "tinyint"):
        super().__init__(dialect)
        if not isinstance(unsigned, bool):
            raise TypeError(
                f"unsigned must be a bool, got {type(unsigned).__name__}; it "
                f"becomes a type modifier in the rendered DDL."
            )
        self.unsigned = unsigned
        self.spelling = spelling

    PARAMETERS = ("unsigned",)

class SmallIntType(DataType):
    """SMALLINT / INT2 (16-bit)."""

    name = "smallint"

    SPELLINGS = ("smallint", "int2")

    unsigned: bool = False

    def __init__(self, dialect=None, *, unsigned: bool = False,
                 spelling: str = "smallint"):
        super().__init__(dialect)
        if not isinstance(unsigned, bool):
            raise TypeError(
                f"unsigned must be a bool, got {type(unsigned).__name__}; it "
                f"becomes a type modifier in the rendered DDL."
            )
        self.unsigned = unsigned
        self.spelling = spelling

    PARAMETERS = ("unsigned",)

class IntegerType(DataType):
    """INTEGER / INT (32-bit).

    ``int4`` is in the closed list because it is a documented synonym on more
    than one backend -- MySQL and MariaDB each give it a page of its own -- and
    that list is the **union** across dialects, not one dialect's vocabulary.
    Its three siblings each carry their own ``INTn`` (``int1``, ``int2``,
    ``int8``); leaving this one out read as an oversight rather than a decision,
    because nothing had recorded it as one.

    Being in the list does not oblige any dialect to **write** it. PostgreSQL
    uses ``int4`` as an internal catalog name only -- it is not in the DDL
    grammar -- so that backend refuses the spelling explicitly rather than
    rendering a word the server's own ``CREATE TABLE`` does not accept.
    """

    name = "integer"

    SPELLINGS = ("integer", "int", "int4")

    unsigned: bool = False

    def __init__(self, dialect=None, *, unsigned: bool = False,
                 spelling: str = "integer"):
        super().__init__(dialect)
        if not isinstance(unsigned, bool):
            raise TypeError(
                f"unsigned must be a bool, got {type(unsigned).__name__}; it "
                f"becomes a type modifier in the rendered DDL."
            )
        self.unsigned = unsigned
        self.spelling = spelling

    PARAMETERS = ("unsigned",)

class BigIntType(DataType):
    """BIGINT / INT8 (64-bit)."""

    name = "bigint"

    SPELLINGS = ("bigint", "int8")

    unsigned: bool = False

    def __init__(self, dialect=None, *, unsigned: bool = False,
                 spelling: str = "bigint"):
        super().__init__(dialect)
        if not isinstance(unsigned, bool):
            raise TypeError(
                f"unsigned must be a bool, got {type(unsigned).__name__}; it "
                f"becomes a type modifier in the rendered DDL."
            )
        self.unsigned = unsigned
        self.spelling = spelling

    PARAMETERS = ("unsigned",)
