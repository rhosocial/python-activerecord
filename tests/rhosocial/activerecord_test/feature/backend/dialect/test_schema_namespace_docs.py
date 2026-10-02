# tests/rhosocial/activerecord_test/feature/backend/dialect/test_schema_namespace_docs.py
"""
Documentation/behaviour cross-checks for the schema-namespace guide.

The guide in ``docs/{en_US,zh_CN}/modeling/schema_namespace.md`` is the primary
user-facing deliverable of the schema-qualification work, and it is easy for it
to rot: identifier quoting, dialect behaviour and DDL capability all move.

These tests parse the guide and compare it against real behaviour, so a stale
table or a wrong claim fails the build instead of misleading a reader.

They also lock the two boundaries that are easy to overstate:

* An unaliased range may be referenced two-part *or* three-part; an aliased
  range must use the alias alone.

The DDL boundary has moved: it used to be asserted that no DDL statement
consumed a schema, which left index, sequence, domain, function and trigger
names qualified only by hand. This now requires the opposite -- every
statement naming a schema-bearing object accepts ``schema_name``, defaulting
to None.
"""

import re
from pathlib import Path

import pytest

from rhosocial.activerecord.backend.expression.core import Column, TableExpression
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
# The guide's rendering table must match what the dialect actually produces
# --------------------------------------------------------------------------

class TestRenderingTableMatchesBehaviour:
    """Every FROM/Column row in the guide is verified against real output."""

    def test_table_expression_rows(self, dialect):
        assert TableExpression(dialect, TABLE).to_sql()[0] == '"users"'
        assert (
            TableExpression(dialect, TABLE, schema_name=SCHEMA).to_sql()[0]
            == '"ar_crm"."users"'
        )

    def test_column_rows(self, dialect):
        # schema + table, no alias -> three parts
        assert (
            Column(dialect, "id", table=TABLE, schema_name=SCHEMA).to_sql()[0]
            == '"ar_crm"."users"."id"'
        )
        # FieldProxy drops the schema for an aliased range -> two parts
        assert (
            Column(dialect, "id", table="u", schema_name=None).to_sql()[0] == '"u"."id"'
        )

    def test_guide_contains_the_verified_forms(self):
        text = _doc(DOC_EN)
        for expected in ('"users"', '"ar_crm"."users"', '"ar_crm"."users"."id"', '"u"."id"'):
            assert expected in text, f"guide omits the verified form {expected!r}"

    def test_guide_states_empty_string_is_not_allowed(self):
        text = _doc(DOC_EN)
        assert "__schema_name__ = \"\"" in text, (
            "the guide must show the empty-string anti-pattern, which now raises"
        )


# --------------------------------------------------------------------------
# Every named-object DDL statement must be able to carry a schema
# --------------------------------------------------------------------------

#: DDL statements that name a schema-bearing object through their own
#: ``schema_name`` parameter. This used to assert the opposite -- that no DDL
#: statement took a schema -- which left index, sequence, domain, function and
#: trigger names qualified only by hand and silently unqualified when a dialect
#: had no namespace to put them in.
#:
#: Table statements are deliberately absent: ``CreateTableExpression`` and
#: friends take ``table: Union[str, TableExpression]``, and ``TruncateExpression``
#: names the field ``schema``. Both qualify, and are covered below.
NAMED_OBJECT_DDL = [
    ("ddl_view", "CreateViewExpression"),
    ("ddl_view", "DropViewExpression"),
    ("ddl_view", "CreateMaterializedViewExpression"),
    ("ddl_view", "DropMaterializedViewExpression"),
    ("ddl_view", "RefreshMaterializedViewExpression"),
    ("ddl_type", "CreateTypeExpression"),
    ("ddl_type", "AlterTypeExpression"),
    ("ddl_type", "DropTypeExpression"),
    ("ddl_index", "CreateIndexExpression"),
    ("ddl_index", "DropIndexExpression"),
    ("ddl_index", "CreateFulltextIndexExpression"),
    ("ddl_index", "DropFulltextIndexExpression"),
    ("ddl_sequence", "CreateSequenceExpression"),
    ("ddl_sequence", "DropSequenceExpression"),
    ("ddl_sequence", "AlterSequenceExpression"),
    ("ddl_domain", "CreateDomainExpression"),
    ("ddl_domain", "DropDomainExpression"),
    ("ddl_domain", "AlterDomainExpression"),
    ("ddl_function", "CreateFunctionExpression"),
    ("ddl_function", "DropFunctionExpression"),
    ("ddl_trigger", "CreateTriggerExpression"),
    ("ddl_trigger", "DropTriggerExpression"),
]

#: Table statements qualify through a TableExpression rather than a scalar.
TABLE_OBJECT_DDL = [
    ("ddl_table", "CreateTableExpression"),
    ("ddl_table", "CreateTableAsExpression"),
    ("ddl_table", "CreateTableCloneExpression"),
    ("ddl_table", "CreateTableFromTemplateExpression"),
    ("ddl_table", "CreateTableLikeExpression"),
    ("ddl_table", "DropTableExpression"),
]


class TestDdlStatementsAcceptSchema:
    """A named-object DDL statement must be able to name its schema."""

    @pytest.mark.parametrize("module_name,class_name", NAMED_OBJECT_DDL,
                             ids=[c for _, c in NAMED_OBJECT_DDL])
    def test_ddl_statement_accepts_schema_name(self, module_name, class_name):
        import importlib
        import inspect

        module = importlib.import_module(
            f"rhosocial.activerecord.backend.expression.statements.{module_name}"
        )
        cls = getattr(module, class_name)
        params = inspect.signature(cls.__init__).parameters
        assert "schema_name" in params, (
            f"{class_name} names a schema-bearing object but takes no "
            f"schema_name, so callers cannot qualify it"
        )
        assert params["schema_name"].default is None, (
            f"{class_name} defaults schema_name to something other than None; "
            f"None is what means 'unqualified'"
        )

    @pytest.mark.parametrize("module_name,class_name", TABLE_OBJECT_DDL,
                             ids=[c for _, c in TABLE_OBJECT_DDL])
    def test_table_statement_qualifies_via_table_expression(
        self, module_name, class_name, dialect
    ):
        """Table DDL qualifies through a TableExpression, not a scalar field.

        The name may be given as a bare string, which is unqualified, or as a
        TableExpression, which may carry a schema. Either way the statement
        formatter resolves it, so a schema supplied here is never dropped.
        """
        import importlib
        import inspect

        module = importlib.import_module(
            f"rhosocial.activerecord.backend.expression.statements.{module_name}"
        )
        cls = getattr(module, class_name)
        params = inspect.signature(cls.__init__).parameters
        assert "table" in params, f"{class_name} no longer takes a table"
        # A qualified reference reaches the statement as a TableExpression and
        # must render qualified.
        ref = TableExpression(dialect, TABLE, schema_name=SCHEMA)
        assert ref.to_sql()[0] == f'"{SCHEMA}"."{TABLE}"'

    def test_truncate_names_the_field_schema_name(self):
        """``TruncateExpression`` uses ``schema_name`` like every other statement.

        It used to be the one object statement carrying the namespace in a field
        called ``schema``, and it did not validate it -- an empty string was
        caught during rendering by the TableExpression the formatter built, so
        the error named that object rather than the one the caller constructed.
        """
        import inspect

        params = inspect.signature(TruncateExpression.__init__).parameters
        assert "schema_name" in params
        assert params["schema_name"].default is None
        assert "schema" not in params, (
            "the old name must be gone rather than kept as an alias: an alias "
            "would be accepted and ignored, which is the silent version of the "
            "defect the rename fixes"
        )

    def test_create_table_only_carries_schema_via_table_expression(self, dialect):
        """``CreateTableExpression`` can still be schema-qualified -- by hand."""
        ref = TableExpression(dialect, TABLE, schema_name=SCHEMA)
        assert ref.to_sql()[0] == '"ar_crm"."users"'

    def test_guide_documents_the_ddl_boundary(self):
        for path in (DOC_EN, DOC_ZH):
            text = _doc(path)
            assert "ALTER TABLE" in text, f"{path.name} omits the DDL boundary"
            assert "CREATE INDEX" in text, f"{path.name} omits the DDL boundary"


# --------------------------------------------------------------------------
# Both locales must exist and cover the same sections
# --------------------------------------------------------------------------

class TestBothLocalesPresent:
    def test_files_exist(self):
        _doc(DOC_EN)
        _doc(DOC_ZH)

    def test_same_numbered_sections(self):
        en = re.findall(r"^## (\d+)\.", _doc(DOC_EN), re.M)
        zh = re.findall(r"^## (\d+)\.", _doc(DOC_ZH), re.M)
        assert en, "English guide has no numbered sections"
        assert en == zh, f"section mismatch: en={en} zh={zh}"

    def test_zh_is_not_an_english_copy(self):
        zh = _doc(DOC_ZH)
        # A cheap but effective check: the Chinese guide must contain CJK.
        assert re.search(r"[\u4e00-\u9fff]", zh), "zh_CN guide has no Chinese content"


# --------------------------------------------------------------------------
# ddl_source.md must state the schema boundary accurately
# --------------------------------------------------------------------------

class TestDdlSourceDocBoundary:
    @pytest.mark.parametrize("locale", ["en_US", "zh_CN"])
    def test_ddl_source_states_ml_only(self, locale):
        path = REPO_ROOT / "docs" / locale / "modeling" / "ddl_source.md"
        text = _doc(path)
        assert re.search(r"DML|DQL|SELECT|INSERT", text), (
            f"{locale}/ddl_source.md must state that schema_name affects DML/DQL"
        )


# --------------------------------------------------------------------------
# No unqualified absolute claims
# --------------------------------------------------------------------------

class TestNoAbsoluteClaims:
    """The guide must not overstate: DDL does *not* pick the schema up."""

    @pytest.mark.parametrize("path", [DOC_EN, DOC_ZH], ids=["en", "zh"])
    def test_avoids_overstatement(self, path):
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

    def test_explicitly_states_ddl_is_manual(self):
        text = _doc(DOC_EN)
        assert re.search(r"DDL.{0,120}(not|never|manual|independently)", text, re.I | re.S), (
            "the guide must explicitly say DDL schema selection is independent"
        )


# --------------------------------------------------------------------------
# The backend matrix must list every schema-capable backend
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
    def test_matrix_lists_backend(self, backend):
        text = _doc(DOC_EN).lower()
        # Tolerate the "SQL Server" / "sqlserver" spelling difference.
        assert backend.lower() in text or backend.lower().replace("sql", "sql ") in text, (
            f"{backend} declares supports_schema() but the guide's matrix omits it"
        )

    def test_distinguishes_native_from_substitute(self):
        text = _doc(DOC_EN)
        # mariadb's "schema" is a database synonym; snowflake is three-level.
        assert re.search(r"mariadb", text, re.I)
        assert re.search(r"snowflake", text, re.I)
        assert re.search(r"three[- ]level|database", text, re.I), (
            "the matrix must explain that mariadb/snowflake use a substitute "
            "namespace, not a native schema"
        )
