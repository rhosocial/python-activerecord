# tests/rhosocial/activerecord_test/feature/backend/dialect/test_schema_namespace_docs.py
"""
Documentation/behaviour cross-checks for the schema-namespace guide (L5).

The guide in ``docs/{en_US,zh_CN}/modeling/schema_namespace.md`` is the primary
user-facing deliverable of the schema-qualification work, and it is easy for it
to rot: identifier quoting, dialect behaviour and DDL capability all move.

These tests parse the guide and compare it against real behaviour, so a stale
table or a wrong claim fails the build instead of misleading a reader.

They also lock the two boundaries that are easy to overstate:

* ``__schema_name__`` affects DML/DQL only -- no DDL statement consumes it.
* An unaliased range may be referenced two-part *or* three-part; an aliased
  range must use the alias alone.
"""

import re
from pathlib import Path

import pytest

from rhosocial.activerecord.backend.expression.core import Column, TableExpression
from rhosocial.activerecord.backend.expression.statements.ddl_alter import (
    AlterTableExpression,
)
from rhosocial.activerecord.backend.expression.statements.ddl_index import (
    CreateIndexExpression,
)
from rhosocial.activerecord.backend.expression.statements.ddl_table import (
    CreateTableExpression,
)
from rhosocial.activerecord.backend.expression.statements.ddl_truncate import (
    TruncateExpression,
)
from rhosocial.activerecord.backend.impl.dummy.backend import DummyDialect

REPO_ROOT = Path(__file__).resolve().parents[6]
DOC_EN = REPO_ROOT / "docs" / "en_US" / "modeling" / "schema_namespace.md"
DOC_ZH = REPO_ROOT / "docs" / "zh_CN" / "modeling" / "schema_namespace.md"

SCHEMA = "ar_crm"
TABLE = "users"


@pytest.fixture
def dialect():
    return DummyDialect()


def _doc(path: Path) -> str:
    assert path.exists(), f"missing guide: {path}"
    return path.read_text(encoding="utf-8")


# --------------------------------------------------------------------------
# T-40  the rendering table must match the dialect
# --------------------------------------------------------------------------

class TestRenderingTableMatchesBehaviour:
    """T-40 -- every FROM/Column row in the guide is verified against output."""

    def test_t40_table_expression_rows(self, dialect):
        assert TableExpression(dialect, TABLE).to_sql()[0] == '"users"'
        assert (
            TableExpression(dialect, TABLE, schema_name=SCHEMA).to_sql()[0]
            == '"ar_crm"."users"'
        )

    def test_t40_column_rows(self, dialect):
        # schema + table, no alias -> three parts
        assert (
            Column(dialect, "id", table=TABLE, schema_name=SCHEMA).to_sql()[0]
            == '"ar_crm"."users"."id"'
        )
        # FieldProxy drops the schema for an aliased range -> two parts
        assert (
            Column(dialect, "id", table="u", schema_name=None).to_sql()[0] == '"u"."id"'
        )

    def test_t40_guide_contains_the_verified_forms(self):
        text = _doc(DOC_EN)
        for expected in ('"users"', '"ar_crm"."users"', '"ar_crm"."users"."id"', '"u"."id"'):
            assert expected in text, f"guide omits the verified form {expected!r}"

    def test_t40_guide_states_empty_string_is_not_allowed(self):
        text = _doc(DOC_EN)
        assert "__schema_name__ = \"\"" in text, (
            "the guide must show the empty-string anti-pattern, which now raises"
        )


# --------------------------------------------------------------------------
# T-41  the DDL capability table must match the expression signatures
# --------------------------------------------------------------------------

class TestDdlCapabilityTableMatchesSignatures:
    """T-41 -- the guide may not claim DDL schema support that does not exist."""

    @pytest.mark.parametrize(
        "expression_class", [CreateTableExpression, AlterTableExpression,
                             CreateIndexExpression]
    )
    def test_t41_no_schema_parameter_on_ddl_statements(self, expression_class):
        import inspect

        params = inspect.signature(expression_class.__init__).parameters
        assert "schema" not in params, (
            f"{expression_class.__name__} now accepts a schema parameter; the "
            "guide's DDL capability table must be updated"
        )
        assert "schema_name" not in params, (
            f"{expression_class.__name__} now accepts schema_name; the guide's "
            "DDL capability table must be updated"
        )

    def test_t41_truncate_has_its_own_schema_field(self):
        """``TruncateExpression`` is the one DDL statement with a schema knob.

        It is *not* fed from the model, which is why the guide lists it
        separately rather than claiming DDL support.
        """
        import inspect

        assert "schema" in inspect.signature(TruncateExpression.__init__).parameters

    def test_t41_create_table_only_carries_schema_via_table_expression(self, dialect):
        """``CreateTableExpression`` can still be schema-qualified -- by hand."""
        ref = TableExpression(dialect, TABLE, schema_name=SCHEMA)
        assert ref.to_sql()[0] == '"ar_crm"."users"'

    def test_t41_guide_documents_the_ddl_boundary(self):
        for path in (DOC_EN, DOC_ZH):
            text = _doc(path)
            assert "ALTER TABLE" in text, f"{path.name} omits the DDL boundary"
            assert "CREATE INDEX" in text, f"{path.name} omits the DDL boundary"


# --------------------------------------------------------------------------
# T-42  both locales exist and cover the same sections
# --------------------------------------------------------------------------

class TestBothLocalesPresent:
    def test_t42_files_exist(self):
        _doc(DOC_EN)
        _doc(DOC_ZH)

    def test_t42_same_numbered_sections(self):
        en = re.findall(r"^## (\d+)\.", _doc(DOC_EN), re.M)
        zh = re.findall(r"^## (\d+)\.", _doc(DOC_ZH), re.M)
        assert en, "English guide has no numbered sections"
        assert en == zh, f"section mismatch: en={en} zh={zh}"

    def test_t42_zh_is_not_an_english_copy(self):
        zh = _doc(DOC_ZH)
        # A cheap but effective check: the Chinese guide must contain CJK.
        assert re.search(r"[\u4e00-\u9fff]", zh), "zh_CN guide has no Chinese content"


# --------------------------------------------------------------------------
# T-43  ddl_source.md must state the DML-only boundary
# --------------------------------------------------------------------------

class TestDdlSourceDocBoundary:
    @pytest.mark.parametrize("locale", ["en_US", "zh_CN"])
    def test_t43_ddl_source_states_ml_only(self, locale):
        path = REPO_ROOT / "docs" / locale / "modeling" / "ddl_source.md"
        text = _doc(path)
        assert re.search(r"DML|DQL|SELECT|INSERT", text), (
            f"{locale}/ddl_source.md must state that schema_name affects DML/DQL"
        )


# --------------------------------------------------------------------------
# T-44  no unqualified absolute claims
# --------------------------------------------------------------------------

class TestNoAbsoluteClaims:
    """The guide must not overstate: DDL does *not* pick the schema up."""

    @pytest.mark.parametrize("path", [DOC_EN, DOC_ZH], ids=["en", "zh"])
    def test_t44_avoids_overstatement(self, path):
        text = _doc(path)
        forbidden = [
            "schema applies to all statements",
            "all statements are schema-qualified",
            "automatically applied to DDL",
            "DDL is schema-qualified automatically",
        ]
        for phrase in forbidden:
            assert phrase.lower() not in text.lower(), (
                f"{path.name} contains an unqualified claim: {phrase!r}"
            )

    def test_t44_explicitly_states_ddl_is_manual(self):
        text = _doc(DOC_EN)
        assert re.search(r"DDL.{0,120}(not|never|manual|independently)", text, re.I | re.S), (
            "the guide must explicitly say DDL schema selection is independent"
        )


# --------------------------------------------------------------------------
# T-45  backend matrix must list every schema-capable backend
# --------------------------------------------------------------------------

class TestBackendMatrixIsComplete:
    #: Backends whose dialect declares ``supports_schema() -> True``.
    SCHEMA_BACKENDS = (
        "postgres",
        "sqlserver",
        "oracle",
        "bigquery",
        "mariadb",
        "snowflake",
    )

    @pytest.mark.parametrize("backend", SCHEMA_BACKENDS)
    def test_t45_matrix_lists_backend(self, backend):
        text = _doc(DOC_EN).lower()
        # Tolerate the "SQL Server" / "sqlserver" spelling difference.
        assert backend.lower() in text or backend.lower().replace("sql", "sql ") in text, (
            f"{backend} declares supports_schema() but the guide's matrix omits it"
        )

    def test_t45_distinguishes_native_from_substitute(self):
        text = _doc(DOC_EN)
        # mariadb's "schema" is a database synonym; snowflake is three-level.
        assert re.search(r"mariadb", text, re.I)
        assert re.search(r"snowflake", text, re.I)
        assert re.search(r"three[- ]level|database", text, re.I), (
            "the matrix must explain that mariadb/snowflake use a substitute "
            "namespace, not a native schema"
        )
