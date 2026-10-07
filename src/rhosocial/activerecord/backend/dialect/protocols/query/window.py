# src/rhosocial/activerecord/backend/dialect/protocols/windowfunctionsupport.py
"""WindowFunctionSupport protocol.

Re-exported from :mod:`rhosocial.activerecord.backend.dialect.protocols`;
see that package for the full protocol surface and the rules the conformance
tests enforce.
"""

from typing import Tuple, Protocol, runtime_checkable, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from ....expression import (
        WindowClause,
        WindowDefinition,
        WindowFrameSpecification,
        WindowFunctionCall,
        WindowSpecification,
    )


@runtime_checkable
class WindowFunctionSupport(Protocol):
    """Protocol for window function support."""

    def supports_window_functions(self) -> bool:
        """Whether window functions are supported."""
        ...  # pragma: no cover

    def supports_window_frame_clause(self) -> bool:
        """Whether window frame clauses (ROWS/RANGE) are supported."""
        ...  # pragma: no cover

    def format_window_function_call(self, call: "WindowFunctionCall") -> Tuple[str, tuple]:
        """Format window function call."""
        ...  # pragma: no cover

    def format_window_specification(self, spec: "WindowSpecification") -> Tuple[str, tuple]:
        """Format window specification."""
        ...  # pragma: no cover

    def format_window_frame_specification(self, spec: "WindowFrameSpecification") -> Tuple[str, tuple]:
        """Format window frame specification."""
        ...  # pragma: no cover

    def format_window_clause(self, clause: "WindowClause") -> Tuple[str, tuple]:
        """Format complete WINDOW clause."""
        ...  # pragma: no cover

    def format_window_definition(self, spec: "WindowDefinition") -> Tuple[str, tuple]:
        """Format named window definition."""
        ...  # pragma: no cover
