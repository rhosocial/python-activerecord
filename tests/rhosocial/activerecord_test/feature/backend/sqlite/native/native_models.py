# tests/rhosocial/activerecord_test/feature/backend/sqlite/native/native_models.py
"""Models for the SQLite affinity tests.

One model per affinity table.  The payload fields are identical across all of
them: the point of the tests is that the *same* Python value is written into a
TEXT, INTEGER, REAL, NUMERIC and BLOB affinity column and that the stored form
(and therefore what reads back) differs only because of SQLite's affinity
rules, never because of the adapter.

Only neutral (backend-agnostic) Python types are used, so the same fixtures
would work on any backend; what makes this directory backend-specific is the
affinity column declarations in ``schema/native_types.sql``.
"""

from decimal import Decimal
from pathlib import Path
from typing import List, Optional

from pydantic import ConfigDict

from rhosocial.activerecord.backend.adapters.bitstring import BitString
from rhosocial.activerecord.backend.adapters.geometry import Geometry
from rhosocial.activerecord.model import ActiveRecord

SCHEMA_DIR = Path(__file__).parent / "schema"


class _AffinityModel(ActiveRecord):
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


# --- L1 fixture definition ----------------------------------------------------
# A definition class receives only a ``dialect``: it holds the DDL its tables
# need and knows nothing about backends, databases, or execution.  Which
# statements run, and when, is decided by the L2 fixtures in the directory.
#
# SQLite has no backend-specific column types, and what *is* backend-specific --
# the affinity -- is selected by the declared type name alone.  The neutral type
# mapping cannot express that, so these tables stay deliberate raw SQL, owned
# here and executed by the environment.


class NativeAffinityDefinition:
    """The five affinity tables, declared as deliberate raw SQL."""

    table_names = (
        "native_affinity_text",
        "native_affinity_integer",
        "native_affinity_real",
        "native_affinity_numeric",
        "native_affinity_blob",
    )

    def __init__(self, dialect):
        self.dialect = dialect
        self.create_statements = self.statements("native_types.sql")
        self.drop_statements = [
            f"DROP TABLE IF EXISTS {name}" for name in reversed(self.table_names)
        ]

    def statements(self, name: str) -> List[str]:
        """Split a raw SQL fixture file into single statements.

        Comment lines are removed first so a ``;`` inside a comment cannot start
        a bogus statement; the file must still not contain a semicolon inside a
        string literal.
        """
        text = (SCHEMA_DIR / name).read_text(encoding="utf-8")
        kept = "\n".join(line for line in text.splitlines() if not line.strip().startswith("--"))
        return [statement.strip() for statement in kept.split(";") if statement.strip()]
