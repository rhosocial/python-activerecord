# src/rhosocial/activerecord/base/fields.py
"""
This module provides classes and functions related to field definitions and annotations.
"""
from typing import Type

from ..backend.type_adapter import SQLTypeAdapter


class UseColumn:
    """
    A marker class used within `typing.Annotated` to specify a custom column name
    for a model field that differs from the Python field name.

    Example:
        from typing import Annotated

        class User(ActiveRecord):
            # Python field name is 'user_id', but database column is 'id'
            user_id: Annotated[int, UseColumn("id")]

            # Python field name is 'email_address', database column is 'email'
            email_address: Annotated[str, UseColumn("email")]

    Notes:
        - Each field can have at most one UseColumn annotation
        - Column name validation happens at metaclass time for single field
        - Cross-field uniqueness validation happens at model initialization
    """

    def __init__(self, column_name: str):
        """
        Initializes the UseColumn marker.

        Args:
            column_name: The database column name to use for this field.
                        Must be a non-empty string.

        Raises:
            TypeError: If column_name is not a string.
            ValueError: If column_name is empty.
        """
        if not isinstance(column_name, str):
            raise TypeError(
                f"Invalid type for column_name. Expected str, "
                f"but received type {type(column_name).__name__}."
            )
        if not column_name.strip():
            raise ValueError("Column name cannot be empty.")
        self.column_name = column_name.strip()


class UseAdapter:
    """
    A marker class used within `typing.Annotated` to specify a concrete
    SQLTypeAdapter and its target driver-compatible type for a model field.

    Example:
        from datetime import datetime
        
        class User(ActiveRecord):
            # This field will use MyCustomAdapter to convert datetime to str
            custom_field: Annotated[
                datetime,
                UseAdapter(MyCustomAdapter(), str)
            ]
    """
    def __init__(self, adapter: SQLTypeAdapter, target_db_type: Type):
        """
        Initializes the UseAdapter marker.

        Args:
            adapter: An instance of a class that inherits from SQLTypeAdapter.
            target_db_type: The Python type that the adapter will convert the value to,
                          which must be compatible with the database driver.

        Raises:
            TypeError: If the provided adapter is not an instance of SQLTypeAdapter.
        """
        if not isinstance(adapter, SQLTypeAdapter):
            raise TypeError(
                f"Invalid type for adapter. Expected an instance of SQLTypeAdapter, "
                f"but received type {type(adapter).__name__}."
            )
        self.adapter = adapter
        self.target_db_type = target_db_type
