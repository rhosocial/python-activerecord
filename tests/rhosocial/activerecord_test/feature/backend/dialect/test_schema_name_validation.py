# tests/rhosocial/activerecord_test/feature/backend/dialect/test_schema_name_validation.py

"""``SchemaSupport.validate_schema_name`` -- the one place a namespace is judged.

An expression only collects parameters. At construction its parameters may still
be incomplete and its dialect may not be settled, so the value is stored as
given; strict checking belongs to the dialect and runs while rendering, which is
the first moment the schema is actually used.

So this module tests the dialect method once, rather than repeating the same four
cases for each of the forty-odd expressions that carry a ``schema_name``. What
varies between expressions is which formatter reaches the check, and that is
covered by asserting each rendering path rejects a bad value -- one case per
path, not per expression.
"""

import pytest

from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.dialect.mixins.ddl_schema import SchemaMixin
from rhosocial.activerecord.backend.dialect.protocols import SchemaSupport
from rhosocial.activerecord.backend.expression.core import (
    Column,
    TableExpression,
    WildcardExpression,
)
from rhosocial.activerecord.backend.expression.statements.ddl_view import (
    DropViewExpression,
)
from rhosocial.activerecord.backend.impl.sqlite.dialect import SQLiteDialect


class Namespaced(SQLiteDialect):
    """SQLite that claims a namespace, so the accepts path can be exercised.

    Everything else about the dialect is unchanged; only ``supports_schema``
    differs, which is the single switch the validation consults.
    """

    def supports_schema(self) -> bool:
        return True


@pytest.fixture
def plain():
    return SQLiteDialect()


@pytest.fixture
def namespaced():
    return Namespaced()


class TestProtocolAndImplementationPair:
    def test_mixin_implements_the_protocol(self, plain):
        assert isinstance(plain, SchemaSupport)

    def test_the_method_is_part_of_the_protocol(self):
        # Checked through the public surface on purpose. Protocol internals
        # differ across the versions this suite runs on -- __protocol_attrs__
        # only exists from 3.12 -- so asserting on them would fail on 3.8 to
        # 3.11 for a reason that has nothing to do with the dialect.
        assert hasattr(SchemaSupport, "validate_schema_name")
        assert hasattr(SchemaMixin, "validate_schema_name")

    def test_returns_true_rather_than_false(self, namespaced):
        expr = TableExpression(namespaced, "users", schema_name="app")
        assert namespaced.validate_schema_name(expr) is True

    def test_none_is_unqualified_and_accepted(self, namespaced, plain):
        assert namespaced.validate_schema_name(
            TableExpression(namespaced, "users")
        ) is True
        assert plain.validate_schema_name(TableExpression(plain, "users")) is True


class TestRejectedValues:
    @pytest.mark.parametrize("value", ["", "   ", "\t\n"])
    def test_blank_is_a_mistake_not_a_spelling_of_unqualified(
        self, namespaced, value
    ):
        expr = TableExpression(namespaced, "users", schema_name=value)
        with pytest.raises(ValueError) as exc:
            expr.to_sql()
        assert "non-empty" in str(exc.value)
        assert "use None" in str(exc.value), (
            "the message has to say what to write instead, or the caller "
            f"reaches for the empty string again: {exc.value}"
        )

    @pytest.mark.parametrize("value", [123, 1.5, [], object()])
    def test_non_string_is_rejected_before_quoting(self, namespaced, value):
        expr = TableExpression(namespaced, "users", schema_name=value)
        with pytest.raises(ValueError) as exc:
            expr.to_sql()
        assert "must be a string or None" in str(exc.value)

    def test_a_dialect_without_namespaces_refuses_the_value(self, plain):
        expr = TableExpression(plain, "users", schema_name="app")
        with pytest.raises(UnsupportedFeatureError) as exc:
            expr.to_sql()
        assert "no namespace" in str(exc.value)


class TestEveryRenderingPathJudges:
    """One case per path, not one per expression.

    ``format_table`` and ``format_column`` are the chokepoints most statements
    reach, but a few render a qualified name on their own -- a wildcard and a
    bare qualified identifier both do. Each of those needs its own call to
    ``validate_schema_name``, and a path that forgot would silently accept an
    empty schema again.
    """

    @pytest.mark.parametrize(
        "build",
        [
            pytest.param(lambda d: TableExpression(d, "users", schema_name=""), id="table"),
            pytest.param(
                lambda d: Column(d, "id", table="users", schema_name=""), id="column"
            ),
            pytest.param(
                lambda d: WildcardExpression(d, table="users", schema_name=""),
                id="wildcard",
            ),
            pytest.param(
                lambda d: TableExpression(
                    d, schema_name="", name="users"
                ),
                id="qualified-identifier",
            ),
            pytest.param(
                lambda d: DropViewExpression(d, "v_users", schema_name=""),
                id="drop-view",
            ),
        ],
    )
    def test_path_rejects_an_empty_schema(self, namespaced, build):
        with pytest.raises(ValueError) as exc:
            build(namespaced).to_sql()
        assert "non-empty" in str(exc.value), exc.value


class TestConstructionDoesNotJudge:
    """The half of the contract that is easy to forget.

    If construction validated, an expression built before its parameters were
    settled would fail for a reason that has nothing to do with the statement
    the caller wanted.
    """

    @pytest.mark.parametrize("value", ["", "   ", 123])
    def test_value_is_stored_verbatim(self, plain, value):
        expr = DropViewExpression(plain, "v_users", schema_name=value)
        assert expr.schema_name == value

    def test_a_dialect_without_namespaces_still_accepts_construction(self, plain):
        expr = TableExpression(plain, "users", schema_name="app")
        assert expr.schema_name == "app"


class TestTheProtocolDecidesWhetherThereIsAnythingToJudge:
    """Three kinds of dialect, and only two of them have an opinion.

    ``SchemaSupport`` is an independent capability: a dialect mixes it in when
    it has namespaces to talk about, and the formatting functions check for it
    before validating. A dialect that does not mix it in is not being asked
    about schemas at all, so whatever the expression carries is none of its
    business -- it renders, and the schema is simply not part of the output.
    """

    @staticmethod
    def _dialect_without_schema_support():
        """A dialect that renders names but has no namespace concept.

        Built from the mixins a minimal dialect needs and pointedly not including
        SchemaMixin, which is the whole point: ``isinstance(self, SchemaSupport)``
        is False, so no validation runs.
        """
        from rhosocial.activerecord.backend.dialect import SQLDialectBase
        from rhosocial.activerecord.backend.dialect.mixins import ExpressionMixin
        from rhosocial.activerecord.backend.dialect.mixins.ddl_table import TableMixin

        class NoNamespaceDialect(SQLDialectBase, ExpressionMixin, TableMixin):
            def supports_schema(self) -> bool:
                return False

        return NoNamespaceDialect()

    def test_a_dialect_without_the_protocol_is_not_asked(self):
        from rhosocial.activerecord.backend.dialect.protocols import SchemaSupport

        dialect = self._dialect_without_schema_support()
        assert not isinstance(dialect, SchemaSupport), (
            "this dialect must not implement SchemaSupport, or the case below "
            "is not testing what it claims to"
        )

    @pytest.mark.parametrize("value", ["", "   ", 123, "app"])
    def test_it_renders_whatever_the_expression_carries(self, value):
        """No validation, and no refusal either -- just no opinion.

        This is the deliberate difference from SQLite below. Both refuse to
        render a qualified reference, but for different reasons: this dialect has
        no concept of namespaces to validate, SQLite has the concept and answers
        no.
        """
        dialect = self._dialect_without_schema_support()
        expr = TableExpression(dialect, "users", schema_name=value)
        assert dialect.supports_schema() is False
        assert expr.to_sql()[0] == '"users"', (
            "a dialect that never claimed namespaces must not start refusing "
            "them halfway through rendering"
        )

    def test_sqlite_has_the_protocol_and_says_no(self, plain):
        """The other case: capability present, switch off.

        SQLite implements SchemaSupport, so schema parameters are validated --
        and the answer is a refusal. This is what makes the two cases above and
        here different rather than two spellings of "unsupported".
        """
        from rhosocial.activerecord.backend.dialect.protocols import SchemaSupport

        assert isinstance(plain, SchemaSupport)
        assert plain.supports_schema() is False
        with pytest.raises(UnsupportedFeatureError):
            TableExpression(plain, "users", schema_name="app").to_sql()

    def test_sqlite_rejects_even_a_punny_value(self, plain):
        with pytest.raises(ValueError):
            TableExpression(plain, "users", schema_name="").to_sql()


class TestTableOnlyExpressionsRejectBareNames:
    """Statements that name a table take a TableExpression and nothing else.

    The namespace rides on that one object, so a bare string has nowhere to
    put it. Each of these statements used to accept a string alongside a
    parallel schema_name; they now refuse the string outright rather than
    silently dropping a qualification the caller cannot express.
    """

    @staticmethod
    def _statements(dialect):
        from rhosocial.activerecord.backend.expression.core import Literal
        from rhosocial.activerecord.backend.expression.statements.ddl_alter import (
            AlterTableExpression,
            DropColumn,
        )
        from rhosocial.activerecord.backend.expression.statements.ddl_truncate import (
            TruncateExpression,
        )
        from rhosocial.activerecord.backend.expression.statements.dml import (
            UpdateExpression,
        )

        return [
            (AlterTableExpression, "table",
             {"actions": [DropColumn(dialect, "legacy")]}),
            (TruncateExpression, "table", {}),
            (UpdateExpression, "table", {"assignments": {"name": Literal(dialect, "x")}}),
        ]

    def test_bare_string_is_rejected(self, namespaced):
        from rhosocial.activerecord.backend.expression.core import TableExpression

        for cls, param, extra in self._statements(namespaced):
            with pytest.raises(TypeError, match="must be a TableExpression"):
                cls(namespaced, **{param: "orders"}, **extra)
            # The same call is accepted once a TableExpression is supplied.
            # Rendering is not asserted here: this dialect is SQLite, whose
            # DDL surface differs, and the rendered SQL is covered elsewhere.
            built = cls(
                namespaced,
                **{param: TableExpression(namespaced, "orders")},
                **extra,
            )
            assert isinstance(getattr(built, param), TableExpression)

    def test_namespace_rides_on_the_table(self, namespaced):
        """A qualified table is the only way to say which namespace."""
        from rhosocial.activerecord.backend.expression.core import TableExpression
        from rhosocial.activerecord.backend.expression.statements.ddl_truncate import (
            TruncateExpression,
        )

        plain_table = TruncateExpression(
            namespaced, TableExpression(namespaced, "orders")
        )
        qualified = TruncateExpression(
            namespaced, TableExpression(namespaced, "orders", schema_name="app")
        )
        assert plain_table.table.schema_name is None
        assert qualified.table.schema_name == "app"
        # An empty namespace is still the caller's mistake, and it is caught
        # while rendering rather than at construction.
        blank = TruncateExpression(
            namespaced, TableExpression(namespaced, "orders", schema_name="")
        )
        assert blank.table.schema_name == ""
        with pytest.raises(ValueError, match="non-empty string"):
            blank.table.to_sql()

    def test_merge_expression_rejects_bare_string(self, namespaced):
        from rhosocial.activerecord.backend.expression.core import Literal, TableExpression
        from rhosocial.activerecord.backend.expression.predicates import ComparisonPredicate
        from rhosocial.activerecord.backend.expression.statements.dml import MergeExpression

        source = TableExpression(namespaced, "orders")
        condition = ComparisonPredicate(
            namespaced,
            "=",
            Column(namespaced, "id", table="orders"),
            Literal(namespaced, 1),
        )
        with pytest.raises(TypeError, match="target_table must be a TableExpression"):
            MergeExpression(namespaced, "orders", source, condition)
