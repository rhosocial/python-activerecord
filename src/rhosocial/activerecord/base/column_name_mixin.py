# src/rhosocial/activerecord/base/column_name_mixin.py
"""
This module provides a mixin for handling custom column names for model fields.
"""
from typing import ClassVar, Dict, Optional, Type, Any
from functools import lru_cache

from .fields import UseColumn


class ColumnNameAnnotationHandler:
    """
    A feature handler for processing `UseColumn` annotations on model fields.

    This handler validates that:
    1. Each field has at most one UseColumn annotation
    2. Column names are properly formatted

    Cross-field uniqueness validation is deferred to model initialization
    because it requires access to model_fields which is not available at
    metaclass time.
    """

    @staticmethod
    def handle(new_class: Type[Any]):
        """
        Parses annotations and attaches the `__field_column_names__` dictionary.

        Args:
            new_class: The class being created by the metaclass
        """
        field_column_names: Dict[str, str] = {}

        if hasattr(new_class, '__annotations__'):
            for field_name, field_type in new_class.__annotations__.items():
                column_name = ColumnNameAnnotationHandler._extract_and_validate_column_name(
                    field_name,
                    field_type
                )
                if column_name:
                    field_column_names[field_name] = column_name

        setattr(new_class, '__field_column_names__', field_column_names)

    @staticmethod
    def _extract_and_validate_column_name(field_name: str, field_type: Any) -> Optional[str]:
        """
        Extracts column name from a field's type annotation if UseColumn is used.

        Validates that at most one UseColumn is specified per field.

        Args:
            field_name: The name of the field being processed
            field_type: The type annotation of the field

        Returns:
            Optional[str]: The custom column name if UseColumn is used, None otherwise

        Raises:
            TypeError: If more than one UseColumn is found on a single field
        """
        # Check if this is an Annotated type with metadata
        if not (hasattr(field_type, '__origin__') and
                hasattr(field_type, '__args__') and
                hasattr(field_type, '__metadata__')):
            return None

        # Extract UseColumn instances from __metadata__
        use_columns_found = [
            arg for arg in field_type.__metadata__
            if isinstance(arg, UseColumn)
        ]

        if len(use_columns_found) > 1:
            raise TypeError(
                f"Invalid column name definition on field '{field_name}'. "
                f"A field can have at most one UseColumn specified, "
                f"but {len(use_columns_found)} were found."
            )

        if use_columns_found:
            use_column_instance = use_columns_found[0]
            return use_column_instance.column_name

        return None


class ColumnNameMixin:
    """
    Provides custom column name functionality for ActiveRecord models.

    This mixin allows fields to specify custom database column names that
    differ from their Python field names using the UseColumn annotation.

    Example:
        from typing import Annotated
        from rhosocial.activerecord.model import ActiveRecord
        from rhosocial.activerecord.base.fields import UseColumn

        class User(ActiveRecord):
            __table_name__ = "users"

            # Python: user_id, Database: id
            user_id: Annotated[int, UseColumn("id")]

            # Python: email_address, Database: email
            email_address: Annotated[str, UseColumn("email")]

    The mixin provides:
    - Field-to-column name mapping
    - Column-to-field name reverse mapping
    - Automatic column name resolution in CRUD operations
    """

    _feature_handlers = [ColumnNameAnnotationHandler]

    __field_column_names__: ClassVar[Dict[str, str]] = {}

    @classmethod
    def _get_column_name(cls, field_name: str) -> str:
        """
        Get the database column name for a given field.

        If the field has a UseColumn annotation, returns the custom column name.
        Otherwise, returns the field name itself.

        Args:
            field_name: The Python field name

        Returns:
            str: The database column name
        """
        return cls.__field_column_names__.get(field_name, field_name)

    @classmethod
    def _get_field_name(cls, column_name: str) -> str:
        """
        Get the Python field name for a given database column name.

        This is the reverse mapping of _get_column_name().

        Args:
            column_name: The database column name

        Returns:
            str: The Python field name
        """
        # Use the pre-computed column-to-field map for efficiency
        column_to_field_map = cls.get_column_to_field_map()
        return column_to_field_map.get(column_name, column_name)

    @classmethod
    def get_field_to_column_map(cls) -> Dict[str, str]:
        """
        Get complete field-to-column name mapping.

        Returns a dictionary where:
        - Keys are Python field names
        - Values are database column names

        For fields without UseColumn, the field name is used as column name.

        Returns:
            Dict[str, str]: Complete field-to-column mapping
        """
        from pydantic.fields import FieldInfo

        mapping: Dict[str, str] = {}
        model_fields: Dict[str, FieldInfo] = dict(cls.model_fields)

        for field_name in model_fields.keys():
            mapping[field_name] = cls._get_column_name(field_name)

        return mapping

    @classmethod
    @lru_cache(maxsize=None)
    def get_column_to_field_map(cls) -> Dict[str, str]:
        """
        Get complete column-to-field name mapping, giving precedence to
        explicit `UseColumn` annotations to allow overriding mixin fields.

        Returns a dictionary where:
        - Keys are database column names
        - Values are Python field names

        This method uses a two-pass approach:
        1. It first processes all fields with an explicit `UseColumn` annotation.
           This ensures that user-defined mappings are prioritized.
        2. It then processes all remaining fields, only adding them if their
           implicit column name hasn't already been claimed by an explicit mapping.
           This allows a model to define a field like `creation_date: ... UseColumn("created_at")`
           which takes precedence over the `created_at` field inherited from `TimestampMixin`,
           resolving the "duplicate column name" error.

        Raises:
            ValueError: If duplicate explicit column names are detected.
        """
        from pydantic.fields import FieldInfo

        reverse_mapping: Dict[str, str] = {}
        model_fields: Dict[str, FieldInfo] = dict(cls.model_fields)

        # Separate fields into those with explicit mappings and those with implicit ones
        explicit_mappers = {
            field_name: cls.__field_column_names__[field_name]
            for field_name in model_fields.keys()
            if field_name in cls.__field_column_names__
        }
        
        implicit_mappers = [
            field_name
            for field_name in model_fields.keys()
            if field_name not in cls.__field_column_names__
        ]

        # First pass: Process explicit mappings, raising an error for duplicates among them.
        for field_name, column_name in explicit_mappers.items():
            if column_name in reverse_mapping:
                existing_field = reverse_mapping[column_name]
                raise ValueError(
                    f"Duplicate explicit column name '{column_name}' found. "
                    f"Both fields '{existing_field}' and '{field_name}' "
                    f"explicitly map to the same database column."
                )
            reverse_mapping[column_name] = field_name

        # Second pass: Process implicit mappings, skipping any that conflict with explicit ones.
        for field_name in implicit_mappers:
            # For implicit mappers, the column name is the same as the field name.
            column_name = field_name
            if column_name not in reverse_mapping:
                reverse_mapping[column_name] = field_name
        
        return reverse_mapping

    @classmethod
    def validate_column_names(cls) -> None:
        """
        Validate column name configuration for this model.

        Checks:
        1. No duplicate column names across fields
        2. All UseColumn annotations are valid

        This method is called during model initialization to catch
        configuration errors early.

        Raises:
            ValueError: If duplicate column names or other validation errors are found
        """
        # This will raise ValueError if duplicates are found
        cls.get_column_to_field_map()

    @classmethod
    def primary_key_field(cls) -> str:
        """
        Get the Python field name that maps to the primary key column.

        Since __primary_key__ stores the DATABASE COLUMN NAME, this method
        reverse-maps it to find the corresponding Python field name.

        Returns:
            str: Python field name for the primary key

        Example:
            class User(ActiveRecord):
                __primary_key__ = "id"  # Column name (database)
                user_id: Annotated[int, UseColumn("id")]  # Field name (Python)

            User.primary_key()       # "id" (column name)
            User.primary_key_field() # "user_id" (field name)

        Note:
            For models without UseColumn, the field name equals the column name:

            class SimpleUser(ActiveRecord):
                __primary_key__ = "id"
                id: int

            SimpleUser.primary_key()       # "id"
            SimpleUser.primary_key_field() # "id" (same)
        """
        pk_column = cls.primary_key()  # Get column name from __primary_key__
        return cls._get_field_name(pk_column)  # Reverse-map to field name

    @classmethod
    def _map_fields_to_columns(cls, field_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map field names in a data dictionary to column names.

        This is used when sending data to the database - we need to convert
        Python field names to database column names.

        Args:
            field_data: Dictionary with field names as keys

        Returns:
            Dict[str, Any]: Dictionary with column names as keys

        Example:
            field_data = {"user_id": 1, "user_name": "Alice"}
            result = User._map_fields_to_columns(field_data)
            # Returns: {"id": 1, "name": "Alice"}
        """
        return {
            cls._get_column_name(field): value
            for field, value in field_data.items()
        }

    @classmethod
    def _map_columns_to_fields(cls, column_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Map column names in a data dictionary back to field names.

        This is used when receiving data from the database - we need to convert
        database column names to Python field names.

        Args:
            column_data: Dictionary with column names as keys

        Returns:
            Dict[str, Any]: Dictionary with field names as keys

        Example:
            column_data = {"id": 1, "name": "Alice"}
            result = User._map_columns_to_fields(column_data)
            # Returns: {"user_id": 1, "user_name": "Alice"}
        """
        return {
            cls._get_field_name(column): value
            for column, value in column_data.items()
        }
