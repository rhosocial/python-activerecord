# src/rhosocial/activerecord/base/ddl.py
"""ActiveRecord-facing DDL parameter declarations and source protocol."""

from __future__ import annotations

import types
import typing
from dataclasses import dataclass
from typing import (
    Any,
    Callable,
    ClassVar,
    Dict,
    List,
    Optional,
    Protocol,
    Sequence,
    Set,
    Tuple,
    Type,
    Union,
    cast,
    runtime_checkable,
    TYPE_CHECKING,
)

try:
    from typing import Annotated
except ImportError:  # Python 3.8
    from typing_extensions import Annotated

from rhosocial.activerecord.backend.expression.statements.ddl_index import CreateIndexExpression, DropIndexExpression
from rhosocial.activerecord.backend.expression.statements.ddl_partition import PartitionClause
from rhosocial.activerecord.backend.expression.statements.ddl_table import (
    ColumnConstraint,
    ColumnConstraintType,
    ColumnDefinition,
    CreateTableExpression,
    CreateTableOptions,
    DropTableExpression,
    GeneratedColumnExpression,
    IndexDefinition,
    StorageOptionsExpression,
    TableConstraint,
    TableConstraintType,
)
from .fields import (
    DDLAnnotation,
    UseColumnAttributes,
    UseComment,
    UseConstraint,
    UseGeneratedColumn,
    UseIndex,
    UseSqlType,
)

if TYPE_CHECKING:  # pragma: no cover
    from rhosocial.activerecord.backend.dialect import SQLDialectBase
    from rhosocial.activerecord.backend.expression.types import DataType


DDLColumnType = Union["UseSqlType", "DataType", Sequence["DataType"]]
DDLGeneratedColumn = Union[
    GeneratedColumnExpression,
    Callable[["SQLDialectBase"], GeneratedColumnExpression],
]

PEP604_UNION_TYPE = getattr(types, "UnionType", None)
MARKER_REGISTRY: Dict[Type[Any], Tuple[str, bool]] = {
    UseSqlType: ("use_sql_type", True),
    UseConstraint: ("constraints", False),
    UseIndex: ("indexes", False),
    UseColumnAttributes: ("column_attributes", False),
    UseComment: ("column_comment", True),
    UseGeneratedColumn: ("generated_column", True),
}


class ColumnAttribute:
    """Base class for dialect-free column attribute declarations."""

    kind: ClassVar[str] = "attribute"


@dataclass(frozen=True)
class IdentityAttribute(ColumnAttribute):
    """Identity-column declaration."""

    kind: ClassVar[str] = "identity"

    generation: str = "BY DEFAULT"
    start: Optional[int] = None
    increment: Optional[int] = None
    minvalue: Optional[int] = None
    maxvalue: Optional[int] = None
    cycle: Optional[bool] = None

    def __post_init__(self) -> None:
        normalized = self.generation.upper()
        if normalized not in ("ALWAYS", "BY DEFAULT"):
            raise ValueError(
                f"identity generation must be 'ALWAYS' or 'BY DEFAULT', got {self.generation!r}"
            )


@dataclass(frozen=True)
class CollationAttribute(ColumnAttribute):
    """Column-level collation declaration."""

    kind: ClassVar[str] = "collation"

    name: str = ""

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("collation attribute requires a non-empty name")


@dataclass(frozen=True)
class CharacterSetAttribute(ColumnAttribute):
    """Column-level character-set declaration."""

    kind: ClassVar[str] = "character_set"

    name: str = ""

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("character set attribute requires a non-empty name")


class ColumnOptions:
    """Dialect-free declaration for backend-specific column options."""

    def column_definition_class(self) -> Type["ColumnDefinition"]:
        from rhosocial.activerecord.backend.expression.statements import ColumnDefinition

        return ColumnDefinition

    def apply_to(self, column: "ColumnDefinition") -> None:
        """Transfer backend-specific fields onto *column*."""


class DDLFieldMetadata:
    """Annotation-derived DDL metadata for one model field.

    ``annotations`` retains every inline and Pydantic metadata object so an
    explicitly registered backend handler can consume its own
    :class:`DDLAnnotation` values.  Core marker values are extracted into the
    typed attributes below; handler-produced column options are exposed through
    :meth:`add_column_options`.
    """

    def __init__(self, field_info: Any):
        annotation, inline_markers = self.strip_annotated(field_info.annotation)
        markers = list(inline_markers)
        markers.extend(getattr(field_info, "metadata", ()) or ())
        self.annotations = tuple(markers)
        self.handled_annotation_ids: Set[int] = set()
        self.column_options: List[ColumnOptions] = []
        self.is_optional = self.detect_optional(annotation, getattr(field_info, "default", None))
        self.python_type = self.unwrap_optional(annotation)
        for marker_class, (attr_name, singular) in MARKER_REGISTRY.items():
            if singular:
                setattr(
                    self,
                    attr_name,
                    next((marker for marker in markers if isinstance(marker, marker_class)), None),
                )
            else:
                setattr(
                    self,
                    attr_name,
                    tuple(marker for marker in markers if isinstance(marker, marker_class)),
                )

    @staticmethod
    def union_arguments(annotation: Any) -> Optional[tuple]:
        origin = typing.get_origin(annotation)
        if origin is typing.Union or origin is PEP604_UNION_TYPE:
            return typing.get_args(annotation)
        return None

    @staticmethod
    def strip_annotated(annotation: Any) -> Tuple[Any, list]:
        markers: list = []
        while typing.get_origin(annotation) is Annotated:
            args = typing.get_args(annotation)
            annotation = args[0]
            markers.extend(args[1:])
        return annotation, markers

    @staticmethod
    def detect_optional(annotation: Any, default: Any) -> bool:
        arguments = DDLFieldMetadata.union_arguments(annotation)
        if arguments and any(argument is type(None) for argument in arguments):
            return True
        return default is None

    @staticmethod
    def unwrap_optional(annotation: Any) -> Any:
        arguments = DDLFieldMetadata.union_arguments(annotation)
        if arguments:
            non_none = [argument for argument in arguments if argument is not type(None)]
            if len(non_none) == 1:
                return non_none[0]
        return annotation

    def mark_handled(self, annotation: Any) -> None:
        """Mark one annotation as consumed by an explicit DDL handler."""
        self.handled_annotation_ids.add(id(annotation))

    def add_column_options(self, *options: ColumnOptions) -> None:
        """Attach backend-owned column options to this field metadata."""
        for option in options:
            if not isinstance(option, ColumnOptions):
                raise TypeError(
                    "DDL column options must be ColumnOptions instances, "
                    f"got {type(option).__name__}"
                )
            self.column_options.append(option)

    def unhandled_annotations(self) -> Tuple[Any, ...]:
        """Return DDL annotations that no registered handler consumed."""
        return tuple(
            annotation
            for annotation in self.annotations
            if isinstance(annotation, DDLAnnotation)
            and id(annotation) not in self.handled_annotation_ids
        )

    def require_handled(self) -> None:
        """Fail when a DDL annotation has no explicit processor.

        Raises:
            TypeError: If one or more backend/core DDL annotations remain
                unhandled.
        """
        unhandled = self.unhandled_annotations()
        if not unhandled:
            return
        names = ", ".join(type(annotation).__name__ for annotation in unhandled)
        raise TypeError(
            "DDL annotation(s) require an explicit handler: "
            f"{names}. Register the backend handler in _feature_handlers."
        )


class DDLAnnotationHandler:
    """Process explicitly registered field-level DDL annotations.

    The default handler collects core DDL markers into ``DDLFieldMetadata``.
    Backend packages may subclass it, declare the annotation types they own,
    and override :meth:`apply` to add backend-specific metadata such as
    column options.  A backend handler is active only when its model mixin is
    explicitly included in ``_feature_handlers``.
    """

    annotation_types: ClassVar[Tuple[Type[Any], ...]] = (
        UseSqlType,
        UseConstraint,
        UseIndex,
        UseColumnAttributes,
        UseComment,
        UseGeneratedColumn,
    )

    @classmethod
    def apply(
        cls,
        new_class: Type[Any],
        field_name: str,
        annotation: DDLAnnotation,
        metadata: DDLFieldMetadata,
    ) -> None:
        """Consume one matching annotation.

        The default implementation is intentionally a no-op because core
        marker values are extracted by :class:`DDLFieldMetadata`.  Backend
        subclasses override this method to attach backend-owned metadata.
        """
        return None

    @classmethod
    def handle(cls, new_class: Type[Any]) -> None:
        """Collect core metadata and dispatch registered annotation types."""
        metadata_by_field = new_class.__dict__.get("__table_ddl_fields__")
        if metadata_by_field is None:
            fields = getattr(new_class, "model_fields", None) or {}
            metadata_by_field = {
                field_name: DDLFieldMetadata(field_info)
                for field_name, field_info in fields.items()
            }
            new_class.__table_ddl_fields__ = metadata_by_field
        for field_name, metadata in metadata_by_field.items():
            for annotation in metadata.annotations:
                if id(annotation) in metadata.handled_annotation_ids:
                    continue
                if isinstance(annotation, cls.annotation_types):
                    cls.apply(new_class, field_name, annotation, metadata)
                    metadata.mark_handled(annotation)


@runtime_checkable
class DDLSource(Protocol):
    """Structural contract for an ActiveRecord DDL parameter source.

    ``DDLSource`` exposes declarations only: table and field metadata, column
    constraints and attributes, indexes, generated columns, and table-level
    options.  ``ActiveDDL`` consumes this contract to build backend-bound DDL
    expressions; the source itself never creates, renders, or executes SQL.

    The protocol is intentionally structural.  ``ActiveRecord`` satisfies it
    through :class:`DDLSourceMixin`, while integrations may provide their own
    source implementation without inheriting from ActiveRecord.  Returned
    values are dialect-free declarations or ordered candidates, allowing the
    DDL layer to apply the active backend dialect and capability gates.

    This contract deliberately excludes the ``ddl()`` factory, backend and
    dialect objects, expression generation, statement plans, rendering, and
    execution.  ``@runtime_checkable`` verifies the presence of the protocol
    methods, not their complete signatures.
    """

    def table_name(self) -> str:
        ...

    def schema_name(self) -> Optional[str]:
        ...

    def primary_key_columns(self) -> Tuple[str, ...]:
        ...

    def is_composite_pk(self) -> bool:
        ...

    def ddl_field_names(self) -> Tuple[str, ...]:
        ...

    def is_derived_field(self, field: str) -> bool:
        ...

    def field_python_type(self, field: str) -> Type[Any]:
        ...

    def field_is_optional(self, field: str) -> bool:
        ...

    def column_name(self, field: str) -> str:
        ...

    def column_type(self, field: str) -> Optional[DDLColumnType]:
        ...

    def column_constraints(self, field: str) -> Sequence[ColumnConstraint]:
        ...

    def column_attributes(self, field: str) -> Sequence[ColumnAttribute]:
        ...

    def column_indexes(self, field: str) -> Sequence[IndexDefinition]:
        ...

    def column_comment(self, field: str) -> Optional[str]:
        ...

    def generated_column(self, field: str) -> Optional[DDLGeneratedColumn]:
        ...

    def column_options(
        self, field: str
    ) -> Optional[Union[ColumnOptions, Sequence[ColumnOptions]]]:
        ...

    def table_options(
        self,
    ) -> Optional[Union[CreateTableOptions, Sequence[CreateTableOptions]]]:
        ...

    def table_storage_options(
        self,
    ) -> Optional[Union[StorageOptionsExpression, Sequence[StorageOptionsExpression]]]:
        ...

    def table_partition(
        self,
    ) -> Optional[Union[PartitionClause, Sequence[PartitionClause]]]:
        ...

    def table_indexes(self) -> Sequence[IndexDefinition]:
        ...

    def create_table_statement_classes(
        self,
    ) -> Optional[Union[Type[CreateTableExpression], Sequence[Type[CreateTableExpression]]]]:
        ...

    def table_constraints(self) -> Sequence[TableConstraint]:
        ...

    def table_inherits(self) -> Optional[List[str]]:
        ...

    def table_tablespace(self) -> Optional[str]:
        ...


class DDLSourceMixin:
    """Provide overridable DDL parameter defaults for ActiveRecord models.

    This mixin implements the :class:`DDLSource` contract using model field
    metadata and declaration markers.  It translates ``UseSqlType``,
    ``UseConstraint``, ``UseIndex``, ``UseColumnAttributes``,
    ``UseComment``, and ``UseGeneratedColumn`` markers into dialect-free
    declarations, and supplies the table-level defaults used by the DDL layer.
    Backend-owned field annotations are accepted only when an explicit
    ``DDLAnnotationHandler`` is registered by the model.

    It only presents parameters.  It does not import or construct ``ActiveDDL``,
    bind a backend dialect, generate statements, retain DDL state, or execute
    SQL.  Applications may override any classmethod to provide a different
    declaration source while keeping ``ActiveDDL`` independent of ActiveRecord.
    """

    _feature_handlers = [DDLAnnotationHandler]

    __table_ddl_fields__: ClassVar[Dict[str, DDLFieldMetadata]] = {}

    @classmethod
    def _validate_ddl_annotations(cls) -> None:
        """Require every DDL annotation to have an explicit processor."""
        for metadata in (getattr(cls, "__table_ddl_fields__", {}) or {}).values():
            metadata.require_handled()

    @classmethod
    def table_options(cls) -> Optional[Union[CreateTableOptions, Sequence[CreateTableOptions]]]:
        return None

    @classmethod
    def table_storage_options(
        cls,
    ) -> Optional[Union[StorageOptionsExpression, Sequence[StorageOptionsExpression]]]:
        return None

    @classmethod
    def table_partition(cls) -> Optional[Union[PartitionClause, Sequence[PartitionClause]]]:
        return None

    @classmethod
    def table_indexes(cls) -> Sequence[IndexDefinition]:
        return list(getattr(cls, "__table_indexes__", ()) or [])

    @classmethod
    def table_constraints(cls) -> Sequence[TableConstraint]:
        declarations = list(getattr(cls, "__table_constraints__", ()) or [])
        source = cast(Any, cls)
        if source.is_composite_pk():
            declarations.append(
                TableConstraint(
                    cast(Any, None),
                    TableConstraintType.PRIMARY_KEY,
                    columns=list(source.primary_key_columns()),
                )
            )
        return declarations

    @classmethod
    def table_inherits(cls) -> Optional[List[str]]:
        return None

    @classmethod
    def table_tablespace(cls) -> Optional[str]:
        return None

    @classmethod
    def index_definition(cls, marker: UseIndex, column_name: str) -> IndexDefinition:
        return IndexDefinition(
            cast(Any, None),
            name=marker.name,
            columns=[column_name],
            unique=marker.unique,
            type=marker.type,
            partial_condition=cast(Any, marker.partial_condition),
            include_columns=marker.include_columns,
            if_not_exists=marker.if_not_exists,
            tablespace=marker.tablespace,
            if_exists=marker.if_exists,
            concurrent=marker.concurrent,
        )

    @classmethod
    def create_table_statement_classes(
        cls,
    ) -> Optional[Union[Type[CreateTableExpression], Sequence[Type[CreateTableExpression]]]]:
        return None

    @classmethod
    def drop_table_statement_classes(
        cls,
    ) -> Optional[Union[Type[DropTableExpression], Sequence[Type[DropTableExpression]]]]:
        return None

    @classmethod
    def create_index_statement_classes(
        cls,
    ) -> Optional[Union[Type[CreateIndexExpression], Sequence[Type[CreateIndexExpression]]]]:
        return None

    @classmethod
    def drop_index_statement_classes(
        cls,
    ) -> Optional[Union[Type[DropIndexExpression], Sequence[Type[DropIndexExpression]]]]:
        return None

    @classmethod
    def column_name(cls, field: str) -> str:
        return cast(Any, cls).get_column_name(field)

    @classmethod
    def column_type(cls, field: str) -> Optional[DDLColumnType]:
        cls._validate_ddl_annotations()
        metadata = (getattr(cls, "__table_ddl_fields__", {}) or {}).get(field)
        return metadata.use_sql_type if metadata is not None else None

    @classmethod
    def column_constraints(cls, field: str) -> Sequence[ColumnConstraint]:
        cls._validate_ddl_annotations()
        metadata = (getattr(cls, "__table_ddl_fields__", {}) or {}).get(field)
        if metadata is None:
            return []
        constraints = [marker.constraint for marker in metadata.constraints]
        declared_types = {constraint.constraint_type for constraint in constraints}
        explicit_not_null = ColumnConstraintType.NOT_NULL in declared_types
        explicit_nullable = ColumnConstraintType.NULL in declared_types
        source = cast(Any, cls)
        pk_member = cls.column_name(field) in source.primary_key_columns()
        if pk_member and not source.is_composite_pk():
            constraints.append(
                ColumnConstraint(cast(Any, None), ColumnConstraintType.PRIMARY_KEY)
            )
        if pk_member:
            if explicit_nullable:
                constraints = [
                    constraint
                    for constraint in constraints
                    if constraint.constraint_type != ColumnConstraintType.NULL
                ]
            if not explicit_not_null:
                constraints.append(
                    ColumnConstraint(cast(Any, None), ColumnConstraintType.NOT_NULL)
                )
        elif not explicit_not_null and not explicit_nullable and not metadata.is_optional:
            constraints.append(
                ColumnConstraint(cast(Any, None), ColumnConstraintType.NOT_NULL)
            )
        return constraints

    @classmethod
    def column_attributes(cls, field: str) -> Sequence[ColumnAttribute]:
        cls._validate_ddl_annotations()
        metadata = (getattr(cls, "__table_ddl_fields__", {}) or {}).get(field)
        if metadata is None:
            return []
        return [
            attribute
            for marker in metadata.column_attributes
            for attribute in marker.attributes
        ]

    @classmethod
    def column_indexes(cls, field: str) -> Sequence[IndexDefinition]:
        cls._validate_ddl_annotations()
        metadata = (getattr(cls, "__table_ddl_fields__", {}) or {}).get(field)
        if metadata is None:
            return []
        return [
            cls.index_definition(marker, cls.column_name(field))
            for marker in metadata.indexes
        ]

    @classmethod
    def column_comment(cls, field: str) -> Optional[str]:
        cls._validate_ddl_annotations()
        metadata = (getattr(cls, "__table_ddl_fields__", {}) or {}).get(field)
        marker = getattr(metadata, "column_comment", None) if metadata else None
        return marker.comment if marker is not None else None

    @classmethod
    def generated_column(cls, field: str) -> Optional[DDLGeneratedColumn]:
        cls._validate_ddl_annotations()
        metadata = (getattr(cls, "__table_ddl_fields__", {}) or {}).get(field)
        marker = getattr(metadata, "generated_column", None) if metadata else None
        return marker.expression if marker is not None else None

    @classmethod
    def column_options(
        cls, field: str
    ) -> Optional[Union[ColumnOptions, Sequence[ColumnOptions]]]:
        cls._validate_ddl_annotations()
        metadata = (getattr(cls, "__table_ddl_fields__", {}) or {}).get(field)
        if metadata is None or not metadata.column_options:
            return None
        options = list(metadata.column_options)
        return options[0] if len(options) == 1 else options

    @classmethod
    def _batch_fields(cls, fields: Optional[List[str]]) -> List[str]:
        if fields is None:
            return list(cast(Any, cls).model_fields)
        return list(fields)

    @classmethod
    def columns_name(cls, fields: Optional[List[str]] = None) -> Dict[str, str]:
        return {field: cls.column_name(field) for field in cls._batch_fields(fields)}

    @classmethod
    def columns_type(
        cls, fields: Optional[List[str]] = None
    ) -> Dict[str, Optional[DDLColumnType]]:
        return {field: cls.column_type(field) for field in cls._batch_fields(fields)}

    @classmethod
    def columns_constraints(
        cls, fields: Optional[List[str]] = None
    ) -> Dict[str, Sequence[ColumnConstraint]]:
        return {field: cls.column_constraints(field) for field in cls._batch_fields(fields)}

    @classmethod
    def columns_attributes(
        cls, fields: Optional[List[str]] = None
    ) -> Dict[str, Sequence[ColumnAttribute]]:
        return {field: cls.column_attributes(field) for field in cls._batch_fields(fields)}

    @classmethod
    def columns_indexes(
        cls, fields: Optional[List[str]] = None
    ) -> Dict[str, Sequence[IndexDefinition]]:
        return {field: cls.column_indexes(field) for field in cls._batch_fields(fields)}

    @classmethod
    def columns_comment(
        cls, fields: Optional[List[str]] = None
    ) -> Dict[str, Optional[str]]:
        return {field: cls.column_comment(field) for field in cls._batch_fields(fields)}

    @classmethod
    def columns_generated(
        cls, fields: Optional[List[str]] = None
    ) -> Dict[str, Optional[DDLGeneratedColumn]]:
        return {field: cls.generated_column(field) for field in cls._batch_fields(fields)}

    @classmethod
    def columns_options(
        cls, fields: Optional[List[str]] = None
    ) -> Dict[str, Optional[Union[ColumnOptions, Sequence[ColumnOptions]]]]:
        return {field: cls.column_options(field) for field in cls._batch_fields(fields)}

    @classmethod
    def ddl_field_names(cls) -> Tuple[str, ...]:
        cls._validate_ddl_annotations()
        derived = getattr(cls, "__derived_fields__", {}) or {}
        return tuple(
            field
            for field in (getattr(cls, "model_fields", {}) or {})
            if field not in derived
        )

    @classmethod
    def is_derived_field(cls, field: str) -> bool:
        return field in (getattr(cls, "__derived_fields__", {}) or {})

    @classmethod
    def ddl_field_metadata(cls, field: str) -> DDLFieldMetadata:
        metadata = (getattr(cls, "__table_ddl_fields__", {}) or {}).get(field)
        if metadata is None:
            metadata = DDLFieldMetadata(cast(Any, cls).model_fields[field])
        metadata.require_handled()
        return metadata

    @classmethod
    def field_python_type(cls, field: str) -> type:
        return cls.ddl_field_metadata(field).python_type

    @classmethod
    def field_is_optional(cls, field: str) -> bool:
        return cls.ddl_field_metadata(field).is_optional


__all__ = [
    "CharacterSetAttribute",
    "DDLAnnotation",
    "CollationAttribute",
    "ColumnAttribute",
    "ColumnOptions",
    "DDLAnnotationHandler",
    "DDLColumnType",
    "DDLFieldMetadata",
    "DDLGeneratedColumn",
    "DDLSource",
    "DDLSourceMixin",
    "IdentityAttribute",
    "MARKER_REGISTRY",
]
