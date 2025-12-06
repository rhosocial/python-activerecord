# src/rhosocial/activerecord/base/fields.py
"""
This module provides classes and functions related to field definitions and annotations.
"""
from typing import Type

from ..backend.type_adapter import SQLTypeAdapter


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


class UseColumn:
    """
    A marker class used within `typing.Annotated` to specify the exact
    database column name for a model field.

    This allows the model's field name to differ from the actual column name
    in the database, providing flexibility for naming conventions or integration
    with existing schemas.

    Example:
        class User(ActiveRecord):
            user_name: Annotated[str, UseColumn("name")]
    """
    def __init__(self, name: str):
        """
        Initializes the UseColumn marker.

        Args:
            name: The exact name of the column in the database table that this
                  model field maps to.
        """
        if not isinstance(name, str) or not name:
            raise ValueError("Column name must be a non-empty string.")
        self.name = name

