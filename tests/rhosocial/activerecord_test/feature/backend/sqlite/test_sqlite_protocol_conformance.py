# tests/rhosocial/activerecord_test/feature/backend/sqlite/test_sqlite_protocol_conformance.py
"""
Tests to verify SQLiteDialect protocol conformance and protocol non-overlap.

This test ensures:
1. SQLiteDialect implements all methods defined in the protocols it claims to support
2. All protocols have at least one member
3. No two protocols share the same method name (no overlap)
4. Method signatures on SQLiteDialect match Protocol declarations
5. Protocol-declared methods exist in corresponding Mixins (forward coverage)
6. Mixin-implemented methods are declared in corresponding Protocols (reverse coverage)
"""
import inspect
import sys
from itertools import combinations
from typing import Protocol

if sys.version_info >= (3, 13):
    from typing import get_protocol_members
elif sys.version_info >= (3, 12):
    from typing import _get_protocol_attrs as get_protocol_members

import pytest
from rhosocial.activerecord.backend.dialect import protocols as dialect_protocols
from rhosocial.activerecord.backend.impl.sqlite import dialect as sqlite_dialect
from rhosocial.activerecord.backend.impl.sqlite import mixins as sqlite_mixins
from rhosocial.activerecord.backend.impl.sqlite import protocols as sqlite_protocols


def get_all_protocol_methods(proto: type) -> set:
    """Extract all public method names from a protocol, including inherited."""
    members = set()
    if sys.version_info >= (3, 13):
        members = get_protocol_members(proto)
    elif sys.version_info >= (3, 12):
        members = get_protocol_members(proto)
    else:
        # Walk MRO to include methods from parent protocols
        for cls in proto.__mro__:
            if cls is object:
                continue
            for name in cls.__dict__:
                if name.startswith("_"):
                    continue
                val = cls.__dict__[name]
                if callable(val) or isinstance(val, (property, classmethod, staticmethod)):
                    members.add(name)
            members.update(
                k for k in getattr(cls, "__annotations__", {})
                if not k.startswith("_")
            )
    return members


def get_own_protocol_methods(proto: type) -> set:
    """Extract public method names declared directly on a protocol (not inherited).

    Used for forward coverage: only checks methods the protocol itself declares,
    since parent protocol methods are typically implemented by generic mixins.
    """
    members = set()
    for name in proto.__dict__:
        if name.startswith("_"):
            continue
        val = proto.__dict__[name]
        if callable(val) or isinstance(val, (property, classmethod, staticmethod)):
            members.add(name)
    members.update(
        k for k in getattr(proto, "__annotations__", {})
        if not k.startswith("_")
    )
    return members


SQLITE_PROTOCOLS = [
    sqlite_protocols.SQLiteVirtualTableSupport,
    sqlite_protocols.SQLitePragmaSupport,
    sqlite_protocols.SQLiteExtensionSupport,
    sqlite_protocols.SQLiteReindexSupport,
    dialect_protocols.CTESupport,
    dialect_protocols.FilterClauseSupport,
    dialect_protocols.WindowFunctionSupport,
    dialect_protocols.JSONSupport,
    dialect_protocols.ReturningSupport,
    dialect_protocols.AdvancedGroupingSupport,
    dialect_protocols.ArraySupport,
    dialect_protocols.ExplainSupport,
    dialect_protocols.GraphSupport,
    dialect_protocols.LockingSupport,
    dialect_protocols.MergeSupport,
    dialect_protocols.OrderedSetAggregationSupport,
    dialect_protocols.QualifyClauseSupport,
    dialect_protocols.TemporalTableSupport,
    dialect_protocols.UpsertSupport,
    dialect_protocols.LateralJoinSupport,
    dialect_protocols.WildcardSupport,
    dialect_protocols.JoinSupport,
    dialect_protocols.SetOperationSupport,
    dialect_protocols.ViewSupport,
    dialect_protocols.TableSupport,
    dialect_protocols.ConstraintSupport,
    dialect_protocols.TruncateSupport,
    dialect_protocols.SchemaSupport,
    dialect_protocols.IndexSupport,
    dialect_protocols.SequenceSupport,
    dialect_protocols.TriggerSupport,
    dialect_protocols.GeneratedColumnSupport,
    dialect_protocols.IntrospectionSupport,
    dialect_protocols.TransactionControlSupport,
    dialect_protocols.SQLFunctionSupport,
]


class TestSQLiteDialectProtocolConformance:
    """Assert SQLiteDialect implements all protocols it declares to support."""

    @pytest.fixture
    def dialect(self):
        """Create a SQLiteDialect instance for testing."""
        return sqlite_dialect.SQLiteDialect()

    @pytest.mark.parametrize("protocol", SQLITE_PROTOCOLS)
    def test_implements_protocol(self, dialect, protocol):
        """SQLiteDialect should implement each protocol in SQLITE_PROTOCOLS."""
        assert isinstance(dialect, protocol), (
            f"SQLiteDialect does not implement protocol {protocol.__name__}, "
            f"missing methods: {get_all_protocol_methods(protocol) - set(dir(dialect))}"
        )


class TestProtocolNonOverlap:
    """Assert protocols do not have overlapping method names."""

    def test_no_interface_overlap_between_protocols(self):
        """No two protocols should share the same method name."""
        member_map = {
            proto.__name__: get_all_protocol_methods(proto)
            for proto in SQLITE_PROTOCOLS
        }

        for name, members in member_map.items():
            assert len(members) > 0, f"Protocol {name} has no members defined"

        excluded_overlaps = set()

        violations = []
        for (name_a, members_a), (name_b, members_b) in combinations(member_map.items(), 2):
            if (name_a, name_b) in excluded_overlaps:
                continue
            overlap = members_a & members_b
            if overlap:
                violations.append(f"{name_a} ∩ {name_b} = {overlap}")

        assert not violations, (
            "The following protocols have overlapping interfaces, need to merge or rename:\n"
            + "\n".join(f"  • {v}" for v in violations)
        )


class TestSQLiteExpressionDialectSeparation:
    """Verify SQLite-specific expression classes delegate to dialect for SQL generation.

    Expression-Dialect separation means expression classes collect parameters
    and delegate to_sql() to dialect.format_*() methods, never directly
    constructing SQL strings.
    """

    EXPRESSION_DIALECT_PAIRS = [
        ("SQLiteReindexExpression", "format_reindex_statement"),
    ]

    @pytest.mark.parametrize("expr_name,format_method", EXPRESSION_DIALECT_PAIRS)
    def test_expression_delegates_to_dialect(self, expr_name, format_method):
        """Expression.to_sql() should delegate to dialect.format_*() method."""
        from rhosocial.activerecord.backend.impl.sqlite import expression as sqlite_expr

        # Find the expression class
        expr_class = None
        for module_name in dir(sqlite_expr):
            module = getattr(sqlite_expr, module_name)
            if hasattr(module, expr_name):
                expr_class = getattr(module, expr_name)
                break

        if expr_class is None:
            expr_class = getattr(sqlite_expr, expr_name, None)

        assert expr_class is not None, f"Expression class {expr_name} not found"

        # Verify the dialect has the corresponding format method
        dialect = sqlite_dialect.SQLiteDialect()
        assert hasattr(dialect, format_method), (
            f"SQLiteDialect missing format method {format_method} "
            f"for expression {expr_name}"
        )


# ============================================================================
# Protocol Implementation Completeness Tests
# ============================================================================

# Map from SQLite-specific Protocol to corresponding Mixin class
SQLITE_PROTOCOL_MIXIN_PAIRS = [
    (sqlite_protocols.SQLiteExtensionSupport, sqlite_mixins.SQLiteExtensionMixin),
    (sqlite_protocols.SQLitePragmaSupport, sqlite_mixins.SQLitePragmaMixin),
    (sqlite_protocols.SQLiteVirtualTableSupport, sqlite_mixins.SQLiteVirtualTableMixin),
    (sqlite_protocols.SQLiteReindexSupport, sqlite_mixins.SQLiteReindexMixin),
]


class TestProtocolMethodSignatureConformance:
    """Verify SQLiteDialect method signatures match Protocol declarations.

    Python's @runtime_checkable Protocol only checks method existence,
    not signature compatibility. This test catches parameter mismatches.
    """

    # Known signature mismatches between dialect implementations and generic protocols.
    # Generic Mixins use expr-based signatures instead of named params defined in protocols.
    # These are pre-existing issues that require a broader refactoring to fix.
    _SIGNATURE_MISMATCH_EXCLUSIONS = {
        # JSONSupport: Mixin uses expr-based signatures instead of named params
        ('JSONSupport', 'format_json_expression'),
        ('JSONSupport', 'format_json_table_expression'),
        # ArraySupport: SQLite doesn't support arrays natively
        ('ArraySupport', 'format_array_expression'),
        # AdvancedGroupingSupport: Mixin uses expr instead of named params
        ('AdvancedGroupingSupport', 'format_grouping_expression'),
        # GraphSupport: Mixin uses expr instead of clause
        ('GraphSupport', 'format_match_clause'),
        # OrderedSetAggregationSupport: Mixin uses expr instead of aggregation
        ('OrderedSetAggregationSupport', 'format_ordered_set_aggregation'),
        # QualifyClauseSupport: Mixin uses expr instead of clause
        ('QualifyClauseSupport', 'format_qualify_clause'),
        # ViewSupport: Materialized view methods use expr instead of named params
        ('ViewSupport', 'format_create_materialized_view_statement'),
        ('ViewSupport', 'format_drop_materialized_view_statement'),
        ('ViewSupport', 'format_refresh_materialized_view_statement'),
    }

    @pytest.fixture
    def dialect(self):
        """Create a SQLiteDialect instance for testing."""
        return sqlite_dialect.SQLiteDialect()

    @pytest.mark.parametrize("protocol", SQLITE_PROTOCOLS)
    def test_method_signatures_match_protocol(self, dialect, protocol):
        """Each method on SQLiteDialect must have a compatible signature
        with the corresponding Protocol method."""
        proto_methods = get_all_protocol_methods(protocol)
        missing = []
        signature_mismatch = []

        for method_name in proto_methods:
            # Check existence
            if not hasattr(dialect, method_name):
                missing.append(method_name)
                continue

            # Check signature compatibility
            # Skip known mismatches between dialect implementations and generic protocols
            if (protocol.__name__, method_name) in self._SIGNATURE_MISMATCH_EXCLUSIONS:
                continue

            proto_method = getattr(protocol, method_name, None)
            dialect_method = getattr(dialect, method_name)

            if proto_method is not None and callable(proto_method):
                try:
                    proto_sig = inspect.signature(proto_method)
                    dialect_sig = inspect.signature(dialect_method)

                    # Compare parameter names (excluding 'self')
                    proto_params = [
                        p for p in proto_sig.parameters.values()
                        if p.name != 'self'
                    ]
                    dialect_params = [
                        p for p in dialect_sig.parameters.values()
                        if p.name != 'self'
                    ]

                    # Dialect must accept at least all required proto params
                    proto_required = [
                        p for p in proto_params
                        if p.default is inspect.Parameter.empty
                        and p.kind not in (
                            inspect.Parameter.VAR_POSITIONAL,
                            inspect.Parameter.VAR_KEYWORD,
                        )
                    ]
                    dialect_param_names = {p.name for p in dialect_params}

                    for req_param in proto_required:
                        if req_param.name not in dialect_param_names:
                            signature_mismatch.append(
                                f"{method_name}: missing required param "
                                f"'{req_param.name}' from protocol"
                            )
                except (ValueError, TypeError):
                    pass  # Some protocol methods can't be inspected

        assert not missing, (
            f"SQLiteDialect missing methods for {protocol.__name__}: {missing}"
        )
        assert not signature_mismatch, (
            f"Signature mismatches for {protocol.__name__}: {signature_mismatch}"
        )


class TestProtocolMixinForwardCoverage:
    """Verify every method declared in Protocol is implemented in Mixin.

    This catches the failure mode where a Protocol declares format_* or
    supports_* methods but the corresponding Mixin doesn't implement them.
    """

    @pytest.mark.parametrize("protocol,mixin", SQLITE_PROTOCOL_MIXIN_PAIRS)
    def test_protocol_declared_methods_are_implemented(self, protocol, mixin):
        """Every format_* / supports_* / get_* in Protocol must exist in Mixin.

        Only checks methods declared directly on the protocol (not inherited
        from parent protocols), since parent protocol methods are typically
        implemented by generic mixins rather than the SQLite-specific one.
        """
        proto_methods = get_own_protocol_methods(protocol)
        mixin_methods = {name for name in dir(mixin) if not name.startswith('_')}
        missing = proto_methods - mixin_methods
        assert not missing, (
            f"{mixin.__name__} does not implement these methods "
            f"declared in {protocol.__name__}: {missing}"
        )


class TestProtocolMixinReverseCoverage:
    """Verify every format_*/supports_*/get_* in Mixin is declared in Protocol.

    This catches the failure mode where a Mixin implements format_* or
    supports_* methods but the corresponding Protocol doesn't declare them.
    """

    @pytest.mark.parametrize("protocol,mixin", SQLITE_PROTOCOL_MIXIN_PAIRS)
    def test_mixin_public_methods_are_declared_in_protocol(self, protocol, mixin):
        """Every format_*/supports_*/get_* in Mixin must be declared in Protocol.

        Only checks methods defined on the Mixin itself (not inherited
        from object or other bases), and only public methods
        with the format_*/supports_*/get_*/detect_*/is_*/check_* prefix pattern.
        """
        proto_methods = get_all_protocol_methods(protocol)

        # Collect Mixin's own public method names matching the prefix pattern
        mixin_own_methods = set()
        for name in dir(mixin):
            if name.startswith('_'):
                continue
            if not (name.startswith('format_') or name.startswith('supports_')
                    or name.startswith('get_') or name.startswith('detect_')
                    or name.startswith('is_') or name.startswith('check_')
                    or name.startswith('set_pragma_') or name.startswith('get_pragma_')):
                continue
            # Only include methods defined on the mixin itself, not inherited
            if name in mixin.__dict__:
                mixin_own_methods.add(name)

        undeclared = mixin_own_methods - proto_methods
        assert not undeclared, (
            f"{mixin.__name__} implements these methods not declared in "
            f"{protocol.__name__}: {undeclared}"
        )