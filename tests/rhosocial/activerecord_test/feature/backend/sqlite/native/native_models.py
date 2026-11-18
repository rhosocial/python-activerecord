# tests/rhosocial/activerecord_test/feature/backend/sqlite/native/native_models.py
"""Models and definitions for the SQLite affinity tests.

One model per affinity table.  The payload fields are identical across all of
them: the point of the tests is that the *same* Python value is written into a
TEXT, INTEGER, REAL, NUMERIC and BLOB affinity column and that the stored form
(and therefore what reads back) differs only because of SQLite's affinity
rules, never because of the adapter.

The declared type name is what selects the affinity, so each definition below
declares it with a type expression: ``TextType``, ``IntegerType``,
``RealType``, ``BlobType``, and ``CustomType`` for ``NUMERIC`` (the framework
has no class for that name).  No SQL text is written or parsed here.
"""

from decimal import Decimal
from typing import Optional

from pydantic import ConfigDict

from rhosocial.activerecord.backend.adapters.bitstring import BitString
from rhosocial.activerecord.backend.adapters.geometry import Geometry
from rhosocial.activerecord.backend.expression import (
    ColumnConstraint as Constraint,
    ColumnDefinition as Column,
    CreateTableStatement as CreateTable,
    DropTableStatement as DropTable,
)
from rhosocial.activerecord.backend.expression.objects import Table
from rhosocial.activerecord.backend.expression.statements import (
    ColumnPrimaryKeyConstraint as PrimaryKey,
)
from rhosocial.activerecord.backend.expression.types import (
    BlobType as Blob,
    CustomType,
    IntegerType as Int,
    RealType as Real,
    TextType as Text,
)
from rhosocial.activerecord.model import ActiveRecord

#: The payload columns, in the order the affinity tables declare them.
PAYLOAD_FIELDS = ("shape", "flags", "amount", "payload", "raw_bytes", "counter", "ratio")

#: The affinity each definition table exercises, for the tests and the fixture.
AFFINITIES = ("text", "integer", "real", "numeric", "blob")


class _AffinityModel(ActiveRecord):
    __primary_key__ = "id"
    """Common payload fields; subclasses only change the table (affinity)."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    id: Optional[int] = None
    shape: Optional[Geometry] = None
    flags: Optional[BitString] = None
    amount: Optional[Decimal] = None
    payload: Optional[dict] = None
    raw_bytes: Optional[bytes] = None
    counter: Optional[int] = None
    ratio: Optional[float] = None


class NativeAffinityText(_AffinityModel):
    @classmethod
    def table_name(cls) -> str:
        return "native_affinity_text"


class NativeAffinityInteger(_AffinityModel):
    @classmethod
    def table_name(cls) -> str:
        return "native_affinity_integer"


class NativeAffinityReal(_AffinityModel):
    @classmethod
    def table_name(cls) -> str:
        return "native_affinity_real"


class NativeAffinityNumeric(_AffinityModel):
    @classmethod
    def table_name(cls) -> str:
        return "native_affinity_numeric"


class NativeAffinityBlob(_AffinityModel):
    @classmethod
    def table_name(cls) -> str:
        return "native_affinity_blob"


# --- L1 fixture definitions ---------------------------------------------------
# A definition class receives only a ``dialect``: it holds the DDL its model
# needs and knows nothing about backends, databases, or execution.  Which
# definitions the environment creates, and when, is decided by the L2 fixtures.


class AffinityDefinition:
    """One affinity table; the declared type selects the affinity."""

    model = None
    table_name = ""

    def __init__(self, dialect):
        self.dialect = dialect
        self.create_table = CreateTable(
            dialect,
            table=Table(dialect, self.table_name),
            columns=self.columns(),
        )
        self.drop_table = DropTable(
            dialect, table=Table(dialect, self.table_name), if_exists=True
        )

    def sql_type(self):
        """The declared type expression for this table's payload columns."""
        raise NotImplementedError

    def columns(self):
        columns = [
            Column(
                self.dialect,
                "id",
                Int(self.dialect),
                constraints=[
                    Constraint(
                        self.dialect,
                        branch=PrimaryKey(self.dialect),
                    )
                ],
            )
        ]
        for name in PAYLOAD_FIELDS:
            columns.append(Column(self.dialect, name, self.sql_type()))
        return columns


class NativeAffinityTextDefinition(AffinityDefinition):
    model = NativeAffinityText
    table_name = "native_affinity_text"

    def sql_type(self):
        return Text(self.dialect)


class NativeAffinityIntegerDefinition(AffinityDefinition):
    model = NativeAffinityInteger
    table_name = "native_affinity_integer"

    def sql_type(self):
        return Int(self.dialect)


class NativeAffinityRealDefinition(AffinityDefinition):
    model = NativeAffinityReal
    table_name = "native_affinity_real"

    def sql_type(self):
        return Real(self.dialect)


class NativeAffinityNumericDefinition(AffinityDefinition):
    model = NativeAffinityNumeric
    table_name = "native_affinity_numeric"

    def sql_type(self):
        return CustomType(self.dialect, raw="NUMERIC")


class NativeAffinityBlobDefinition(AffinityDefinition):
    model = NativeAffinityBlob
    table_name = "native_affinity_blob"

    def sql_type(self):
        return Blob(self.dialect)


#: The definition classes, in the order the tables are created.
AFFINITY_DEFINITIONS = (
    NativeAffinityTextDefinition,
    NativeAffinityIntegerDefinition,
    NativeAffinityRealDefinition,
    NativeAffinityNumericDefinition,
    NativeAffinityBlobDefinition,
)
