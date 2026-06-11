# src/rhosocial/activerecord/backend/dialect/mixins/generated_column.py
class GeneratedColumnMixin:
    """Mixin for generated column (computed column) support."""

    def supports_generated_columns(self) -> bool:
        """Whether generated columns are supported."""
        return False

    def supports_stored_generated_columns(self) -> bool:
        """Whether STORED generated columns are supported."""
        return False

    def supports_virtual_generated_columns(self) -> bool:
        """Whether VIRTUAL generated columns are supported."""
        return False
