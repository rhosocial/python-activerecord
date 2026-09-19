# src/rhosocial/activerecord/base/ddl/annotations.py
"""Field-annotation analysis for DDL derivation.

The feature handler runs at model-class creation time and records, per field,
the annotation-derived data the derivation needs: the base Python type,
nullability, and the ``UseSqlType`` / ``UseConstraint`` / ``UseIndex`` markers.
Column names and the primary key are resolved later (elsewhere), so only
annotation data is stored here.
"""

from __future__ import annotations

import types as _types
import typing
from typing import Any, Optional, Tuple, Type

from ..fields import UseConstraint, UseIndex, UseSqlType


class DDLFieldMetadata:
    """Annotation-derived DDL metadata for a single model field."""

    def __init__(self, field_info: Any):
        annotation, inline_markers = self.strip_annotated(field_info.annotation)
        markers = list(inline_markers)
        markers.extend(getattr(field_info, "metadata", ()) or ())
        self.is_optional = self.detect_optional(annotation, getattr(field_info, "default", None))
        self.python_type = self.unwrap_optional(annotation)
        self.use_sql_type = next((m for m in markers if isinstance(m, UseSqlType)), None)
        self.constraints: Tuple[UseConstraint, ...] = tuple(
            m for m in markers if isinstance(m, UseConstraint)
        )
        self.indexes: Tuple[UseIndex, ...] = tuple(m for m in markers if isinstance(m, UseIndex))

    @staticmethod
    def union_arguments(annotation: Any) -> Optional[tuple]:
        """Return the arguments when ``annotation`` is a union, else ``None``."""
        origin = typing.get_origin(annotation)
        if origin is typing.Union or origin is _types.UnionType:
            return typing.get_args(annotation)
        return None

    @staticmethod
    def strip_annotated(annotation: Any) -> Tuple[Any, list]:
        """Unwrap ``Annotated[...]`` returning the inner type and its metadata."""
        markers: list = []
        while typing.get_origin(annotation) is typing.Annotated:
            args = typing.get_args(annotation)
            annotation = args[0]
            markers.extend(args[1:])
        return annotation, markers

    @staticmethod
    def detect_optional(annotation: Any, default: Any) -> bool:
        """Whether the annotation admits ``None`` or the default is ``None``."""
        arguments = DDLFieldMetadata.union_arguments(annotation)
        if arguments and any(argument is type(None) for argument in arguments):
            return True
        return default is None

    @staticmethod
    def unwrap_optional(annotation: Any) -> Any:
        """Reduce ``Optional[T]`` / ``T | None`` to ``T`` when unambiguous."""
        arguments = DDLFieldMetadata.union_arguments(annotation)
        if arguments:
            non_none = [argument for argument in arguments if argument is not type(None)]
            if len(non_none) == 1:
                return non_none[0]
        return annotation


class DDLAnnotationHandler:
    """Populates ``cls.__table_ddl_fields__`` with :class:`DDLFieldMetadata`."""

    @staticmethod
    def handle(new_class: Type[Any]) -> None:
        """Analyze every model field into ``cls.__table_ddl_fields__``."""
        new_class.__table_ddl_fields__ = {
            field_name: DDLFieldMetadata(field_info)
            for field_name, field_info in (getattr(new_class, "model_fields", None) or {}).items()
        }
