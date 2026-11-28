# src/rhosocial/activerecord/backend/dialect/protocols/introspect/ddl_extraction.py
"""DDL extraction: the text that would recreate an object.

No catalogue of structure can reconstruct this: CHECK expressions,
generated-column expressions, storage parameters and trigger bodies exist only
in the engine's own retained text. ``native`` on the answer says whether that
text came from the engine or was assembled here, and assembly is lossy -- the
caller decides which to trust.

The async twin declares the same members in the same order; the formatter
stays synchronous because it performs no I/O.
"""

from typing import Tuple, Protocol, runtime_checkable, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from ....expression.introspection.introspection import DDLStatementQueryStatement


@runtime_checkable
class DdlExtractionIntrospectionSupport(Protocol):
    """Protocol for DDL extraction capability declaration.

    No catalogue of structure can reconstruct this: CHECK expressions,
    generated-column expressions, storage parameters and trigger bodies
    exist only in the engine's own retained text. ``native`` on the answer
    says whether that text came from the engine or was assembled here, and
    assembly is lossy -- the caller decides which to trust.
    """

    # ========== Capability Detection ==========

    def supports_ddl_extraction(self) -> bool:
        """Whether the DDL that recreates an object is answerable."""
        ...  # pragma: no cover

    def supports_ddl_extraction_native(self) -> bool:
        """Whether native DDL extraction is supported (False means assembly required)."""
        ...  # pragma: no cover

    # ========== Query Formatting ==========

    def format_ddl_statement_query_statement(
        self, expr: "DDLStatementQueryStatement"
    ) -> Tuple[str, tuple]:
        """Format a DDL retrieval for one object.

        The contract: the DDL text, and whether it is the engine's own or an
        assembly. An engine without native retrieval answers
        ``UnsupportedFeatureError`` here rather than assembling something that
        looks authoritative -- a reconstruction is not the same fact as the
        engine's text, and the two must not be confused.

        Args:
            expr: DDL statement expression with parameters.

        Returns:
            Tuple of (SQL string, parameters tuple).
        """
        ...  # pragma: no cover


@runtime_checkable
class AsyncDdlExtractionIntrospectionSupport(Protocol):
    """Async twin of :class:`DdlExtractionIntrospectionSupport`."""

    def supports_ddl_extraction(self) -> bool:
        ...  # pragma: no cover

    def supports_ddl_extraction_native(self) -> bool:
        ...  # pragma: no cover

    def format_ddl_statement_query_statement(
        self, expr: "DDLStatementQueryStatement"
    ) -> Tuple[str, tuple]:
        ...  # pragma: no cover
