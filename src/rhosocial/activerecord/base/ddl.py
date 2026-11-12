# src/rhosocial/activerecord/base/ddl.py
"""ActiveRecord-facing DDL parameter declarations and source protocol."""

from __future__ import annotations

import typing
import warnings
from dataclasses import dataclass
from enum import Enum
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

from rhosocial.activerecord.backend.expression.statements import (
    ColumnGeneratedConstraint,
    ColumnNotNullConstraint,
    ColumnNullableConstraint,
    ColumnPrimaryKeyConstraint,
    TablePrimaryKeyConstraint,
)
from .fields import (
    DDLAnnotation,
    UseColumn,
    UseColumnAttributes,
    UseComment,
    UseConstraint,
    UseColumnType,
    UseGeneratedColumn,
    UseIndex,
    UsePartitionKey,
    UseSqlType,
)
from rhosocial.activerecord.backend.expression.statements.ddl_table import (
    ColumnConstraint,
    ColumnDefinition,
    CreateTableStatement,
    CreateTableOptions,
    DropTableStatement,
    IndexDefinition,
    StorageOptionsExpression,
    TableConstraint,
)
from rhosocial.activerecord.backend.expression.statements.ddl_partition import PartitionClause
from rhosocial.activerecord.backend.expression.statements.ddl_index import CreateIndexStatement, DropIndexStatement

try:
    from typing import Annotated
except ImportError:  # Python 3.8
    from typing_extensions import Annotated

try:
    # PEP 604's ``int | str``. Present from 3.10; the spelling is the module's
    # own attribute rather than a ``getattr``, so a reader and a checker both
    # see which name is being asked for (``python-hazards.md`` §11.2).
    from types import UnionType
except ImportError:  # Python 3.8 / 3.9
    UnionType = None


if TYPE_CHECKING:  # pragma: no cover
    from rhosocial.activerecord.backend.dialect import SQLDialectBase
    from rhosocial.activerecord.backend.expression.column_types import ColumnBase
    from rhosocial.activerecord.backend.expression.types import DataType


DDLColumnDataType = Union["UseSqlType", "DataType", Sequence["DataType"]]
DDLColumnType = Union["UseColumnType", Type["ColumnBase"], Sequence[Type["ColumnBase"]]]
DDLGeneratedColumn = Union[
    Callable[["SQLDialectBase"], ColumnGeneratedConstraint],
]


class ObjectDeclaration(Enum):
    """Which kind of database object a :class:`DDLSource` describes.

    A declaration, never a runtime probe: a source answers this from its own
    class definition, and a caller that needs to know whether a database
    actually holds a view of that name must ask introspection instead.

    ``TABLE``
        The default. Anything declared through the column/constraint/index
        methods below.
    ``VIEW``
        A plain view -- a stored query with no entity behind it. Prefer
        expressing those as an encapsulated query rather than a model; this
        member exists so a non-model :class:`DDLSource` can declare one for
        migration purposes.
    ``MATERIALIZED_VIEW``
        A stored result set with a refresh cycle. Unlike a view this *is* an
        entity, so a model may map one.
    """

    TABLE = "table"
    VIEW = "view"
    MATERIALIZED_VIEW = "materialized_view"


MARKER_REGISTRY: Dict[Type[Any], Tuple[str, bool]] = {
    UseSqlType: ("use_sql_type", True),
    UseConstraint: ("constraints", False),
    UseIndex: ("indexes", False),
    UseColumnAttributes: ("column_attributes", False),
    UseComment: ("column_comment", True),
    UseGeneratedColumn: ("generated_column", True),
    UsePartitionKey: ("partition_key", True),
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
        if origin is typing.Union or origin is UnionType:
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
        UsePartitionKey,
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
        cls._validate_column_group_declarations(new_class, metadata_by_field)
        cls._extract_partition_key(new_class, metadata_by_field)
        cls._validate_natural_key(new_class)

    @staticmethod
    def _field_column_names(metadata_by_field: Dict[str, Any]) -> Dict[str, str]:
        """Resolve each field's database column name at class creation.

        Reads the ``UseColumn`` markers straight from the collected metadata,
        so the mapping is complete regardless of handler ordering (the
        column-name handler may run after this one).
        """
        resolved: Dict[str, str] = {}
        for field_name, metadata in metadata_by_field.items():
            column = None
            for annotation in getattr(metadata, "annotations", ()) or ():
                if isinstance(annotation, UseColumn):
                    column = annotation.column_name
                    break
            resolved[field_name] = column or field_name
        return resolved

    @classmethod
    def _validate_column_group_declarations(
        cls,
        new_class: Type[Any],
        metadata_by_field: Dict[str, Any],
    ) -> None:
        """Validate composite ``UseIndex``/``UseConstraint`` declarations.

        Three checks, all at class creation so a bad declaration fails loudly
        instead of silently producing wrong DDL:

        - the anchor of a ``columns`` list is its first element (the
          leftmost prefix);
        - every listed column names an existing column of the model;
        - index names are unique across the field-level annotations and the
          table-level ``__table_indexes__`` declarations -- two same-named
          index declarations would each ask the DDL generator to build an
          index of that name.
        """
        column_names = cls._field_column_names(metadata_by_field)
        columns_set = set(column_names.values())
        index_name_sources: List[Tuple[str, str]] = []
        for field_name, metadata in metadata_by_field.items():
            anchor_column = column_names[field_name]
            for marker in getattr(metadata, "indexes", ()) or ():
                if marker.columns is not None:
                    cls._validate_columns_list(
                        new_class, "UseIndex", field_name, marker.name,
                        anchor_column, marker.columns, columns_set,
                    )
                index_name_sources.append(
                    (marker.name, f"field-level index on '{field_name}'")
                )
            for marker in getattr(metadata, "constraints", ()) or ():
                if marker.columns is not None:
                    cls._validate_columns_list(
                        new_class, "UseConstraint", field_name,
                        marker.table_constraint.branch.__class__.__name__,
                        anchor_column, marker.columns, columns_set,
                    )
        for index in getattr(new_class, "__table_indexes__", ()) or ():
            name = getattr(index, "name", None)
            if name is not None:
                index_name_sources.append(
                    (name, "table-level __table_indexes__ entry")
                )
        seen: Dict[str, str] = {}
        for name, origin in index_name_sources:
            if name in seen:
                raise TypeError(
                    f"{new_class.__name__}: duplicate index name {name!r} "
                    f"declared by the {seen[name]} and the {origin}. An index "
                    f"name must have a single source; declare the composite "
                    f"index once, on its first (leftmost) column."
                )
            seen[name] = origin

    @staticmethod
    def _validate_columns_list(
        new_class: Type[Any],
        marker_kind: str,
        field_name: str,
        marker_label: str,
        anchor_column: str,
        columns: Sequence[str],
        columns_set: Set[str],
    ) -> None:
        if columns[0] != anchor_column:
            raise TypeError(
                f"{new_class.__name__}: {marker_kind} {marker_label!r} on "
                f"field '{field_name}' anchors column {anchor_column!r}, but "
                f"its columns list starts with {columns[0]!r}: the anchor "
                f"must be the first (leftmost) column of the declaration."
            )
        unknown = [column for column in columns if column not in columns_set]
        if unknown:
            raise TypeError(
                f"{new_class.__name__}: {marker_kind} {marker_label!r} on "
                f"field '{field_name}' lists column(s) {unknown!r} that the "
                f"model does not define. The columns list may only name "
                f"columns of this model."
            )

    @classmethod
    def _extract_partition_key(
        cls,
        new_class: Type[Any],
        metadata_by_field: Dict[str, Any],
    ) -> None:
        """Resolve the partition key from the annotation face or the dunder.

        Four cases (§4 of the governance plan):

        - annotations only: the annotated fields, in ``model_fields``
          declaration order, become ``__partition_key__`` (column names,
          UseColumn-aware);
        - a direct ``__partition_key__`` declaration only: adopted as written,
          after validating it is a plain tuple of existing column names --
          introspection-generated models take this path;
        - both: ``TypeError`` (R3) -- one fact, one source;
        - neither: nothing is written, and the model is simply not a
          partitioned one.

        A partition key that the primary key does not contain is legal on
        engines like ClickHouse but surprises a reader expecting a covering
        key, so it is announced with a ``UserWarning`` -- a warning, not an
        error, because the declaration is not wrong.
        """
        annotated: List[str] = []
        column_names = None
        for field_name, metadata in metadata_by_field.items():
            for annotation in getattr(metadata, "annotations", ()) or ():
                if isinstance(annotation, UsePartitionKey):
                    if column_names is None:
                        column_names = cls._field_column_names(metadata_by_field)
                    annotated.append(column_names[field_name])
                    break
        declared = new_class.__dict__.get("__partition_key__")
        if annotated and declared is not None:
            raise TypeError(
                f"{new_class.__name__} declares its partition key twice: "
                f"UsePartitionKey annotations on {annotated!r} and a "
                f"__partition_key__ of {declared!r}. One fact, one source -- "
                f"keep the annotations and delete the dunder, or keep the "
                f"dunder and drop the markers."
            )
        if declared is not None:
            cls._validate_partition_key_declaration(new_class, declared)
            cls._warn_partition_key_outside_primary_key(new_class, declared)
            return
        if not annotated:
            return
        cls._warn_partition_key_outside_primary_key(new_class, tuple(annotated))
        new_class.__partition_key__ = tuple(annotated)

    @staticmethod
    def _validate_partition_key_declaration(
        new_class: Type[Any],
        declared: Any,
    ) -> None:
        """The first round accepts a plain tuple of existing column names."""
        if not isinstance(declared, tuple):
            raise TypeError(
                f"{new_class.__name__}: __partition_key__ must be a tuple of "
                f"column names, got {type(declared).__name__}. Expression "
                f"partition keys (ClickHouse toYYYYMM, BigQuery DATE, ...) "
                f"are not accepted yet; wrap the bare column in a tuple even "
                f"for a single-column key."
            )
        for entry in declared:
            if not isinstance(entry, str) or not entry:
                raise TypeError(
                    f"{new_class.__name__}: __partition_key__ entries must be "
                    f"non-empty column-name strings, got {entry!r}. An "
                    f"expression key is not accepted yet."
                )
        declared_columns = set(declared)
        model_columns = set()
        for field_name, metadata in (
            getattr(new_class, "__table_ddl_fields__", {}) or {}
        ).items():
            model_columns.add(
                DDLAnnotationHandler._resolve_field_column(field_name, metadata)
            )
        unknown = declared_columns - model_columns
        if unknown:
            raise TypeError(
                f"{new_class.__name__}: __partition_key__ names column(s) "
                f"{sorted(unknown)!r} that the model does not define. The "
                f"partition key may only name columns of this model."
            )

    @staticmethod
    def _resolve_field_column(field_name: str, metadata: Any) -> Optional[str]:
        """One field's column name, UseColumn-aware, for ad-hoc checks."""
        for annotation in getattr(metadata, "annotations", ()) or ():
            if isinstance(annotation, UseColumn):
                return annotation.column_name
        return field_name

    @staticmethod
    def _warn_partition_key_outside_primary_key(
        new_class: Type[Any],
        partition_key: Tuple[str, ...],
    ) -> None:
        if not partition_key:
            return
        pk_source = getattr(new_class, "primary_key_columns", None)
        pk_columns = set(pk_source()) if callable(pk_source) else set()
        outside = [column for column in partition_key if column not in pk_columns]
        if not outside:
            return
        warnings.warn(
            f"{new_class.__name__} declares partition key "
            f"{partition_key!r}, which the primary key does not contain "
            f"(outside: {outside!r}). Legal on engines that partition "
            f"independently of uniqueness (ClickHouse, BigQuery), but a "
            f"primary-key lookup on such a model still touches every "
            f"partition -- name the partition column(s) in lookups when "
            f"that matters.",
            UserWarning,
            stacklevel=4,
        )

    @staticmethod
    def _validate_natural_key(new_class: Type[Any]) -> None:
        """A declared natural key must name fields the model actually has.

        Runs at class creation alongside the DDL declarations: the natural
        key is a declaration, and a misspelled member would otherwise
        surface only when a lookup on it silently matched nothing.
        """
        declared = tuple(getattr(new_class, "natural_key", lambda: ())() or ())
        if not declared:
            return
        fields = getattr(new_class, "model_fields", {}) or {}
        unknown = [field for field in declared if field not in fields]
        if unknown:
            raise TypeError(
                f"{new_class.__name__}: natural_key() names field(s) {unknown!r} "
                f"that the model does not define. The natural key may only name "
                f"model fields."
            )
        if len(set(declared)) != len(declared):
            raise TypeError(
                f"{new_class.__name__}: natural_key() repeats a field: {declared!r}."
            )


@runtime_checkable
class DDLSource(Protocol):
    """Structural contract for an ActiveRecord field-fact source.

    ``DDLSource`` exposes a model's field facts and DDL declarations: the
    Python type of a field (``field_python_type``), the column class its
    expressions use (``column_type``), the declared column data type
    (``column_data_type``), table and field metadata, column constraints and
    attributes, indexes, generated columns, and table-level options.  It never
    creates, renders, or executes SQL.

    Every member is dialect-free: ``column_type`` presents the column-type
    declaration as written (a ``UseColumnType`` marker, a class, or a
    sequence) and ``column_data_type`` the declared data type, leaving the
    resolution of either against the active backend to the caller.  That
    lets the DDL layer apply the active dialect and capability gates without
    the source ever needing one.

    The protocol is intentionally structural.  ``ActiveRecord`` satisfies it
    through :class:`DDLSourceMixin`, while integrations may provide their own
    source implementation without inheriting from ActiveRecord.

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

    def partition_key_columns(self) -> Tuple[str, ...]:
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

    def column_data_type(self, field: str) -> Optional[DDLColumnDataType]:
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
        cls,
    ) -> Optional[Union[CreateTableOptions, Sequence[CreateTableOptions]]]:
        ...

    def table_storage_options(
        cls,
    ) -> Optional[Union[StorageOptionsExpression, Sequence[StorageOptionsExpression]]]:
        ...

    def table_partition(
        cls,
    ) -> Optional[Union[PartitionClause, Sequence[PartitionClause]]]:
        ...

    def table_indexes(self) -> Sequence[IndexDefinition]:
        ...

    def create_table_statement_classes(
        self,
    ) -> Optional[Union[Type[CreateTableStatement], Sequence[Type[CreateTableStatement]]]]:
        ...

    def table_constraints(self) -> Sequence[TableConstraint]:
        ...

    def table_inherits(self) -> Optional[List[str]]:
        ...

    def table_tablespace(self) -> Optional[str]:
        ...

    def object_type(self) -> ObjectDeclaration:
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

    It only presents parameters.  It does not bind a backend dialect, generate
    statements, retain DDL state, or execute SQL.  Applications may override
    any classmethod to provide a different declaration source.
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
        cls._validate_ddl_annotations()
        return list(getattr(cls, "__table_indexes__", ()) or [])

    @classmethod
    def partition_key_columns(cls) -> Tuple[str, ...]:
        """Partition key column names, or ``()`` for a non-partitioned model.

        Read from ``__partition_key__``, which the class-creation handler
        extracts from ``UsePartitionKey`` annotations or adopts from a
        direct declaration. A column-name tuple, mirroring
        ``primary_key_columns()``, because partition scoping is decided
        against WHERE trees.
        """
        return tuple(getattr(cls, "__partition_key__", ()) or ())

    @classmethod
    def table_constraints(cls) -> Sequence[TableConstraint]:
        cls._validate_ddl_annotations()
        # Multi-column ``UseConstraint`` markers declare table-level facts
        # anchored on a field; they surface here, in field order, ahead of
        # the direct-write ``__table_constraints__`` declarations.
        declarations: List[TableConstraint] = []
        for metadata in (getattr(cls, "__table_ddl_fields__", {}) or {}).values():
            for marker in getattr(metadata, "constraints", ()) or ():
                table_constraint = getattr(marker, "table_constraint", None)
                if table_constraint is not None:
                    declarations.append(table_constraint)
        declarations.extend(list(getattr(cls, "__table_constraints__", ()) or []))
        source = cast(Any, cls)
        if source.is_composite_pk():
            primary_key_columns = list(source.primary_key_columns())
            explicit_primary_keys = [
                constraint
                for constraint in declarations
                if isinstance(constraint.branch, TablePrimaryKeyConstraint)
            ]
            if explicit_primary_keys:
                matching_primary_keys = [
                    constraint
                    for constraint in explicit_primary_keys
                    if list(constraint.branch.columns or []) == primary_key_columns
                ]
                if not matching_primary_keys:
                    raise ValueError(
                        f"{cls.__name__} declares a table-level primary key that "
                        f"does not match __primary_key__ {primary_key_columns!r}"
                    )
            else:
                declarations.append(
                    TableConstraint(
                        cast(Any, None),
                        branch=TablePrimaryKeyConstraint(cast(Any, None), primary_key_columns),
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
    def object_type(cls) -> ObjectDeclaration:
        """Which kind of object this source describes. Defaults to a table.

        A declaration, not a probe: no introspection happens here. The DDL
        layer reads this value to choose which statement to build, and the
        dialect's capability gates decide whether that statement is
        expressible. Model metadata stays free of I/O, which is what lets it
        be resolved at import time.
        """
        return ObjectDeclaration.TABLE

    @classmethod
    def index_definition(cls, marker: UseIndex, column_name: str) -> IndexDefinition:
        """Build an IndexDefinition from a ``UseIndex`` marker.

        An explicit ``columns`` list on the marker is authoritative and must
        start with the anchor column (validated again here as a guard for
        direct callers; the class-creation check is the primary one).
        """
        if marker.columns is not None and marker.columns[0] != column_name:
            raise TypeError(
                f"UseIndex {marker.name!r} anchors column {column_name!r}, but "
                f"its columns list starts with {marker.columns[0]!r}: the "
                f"anchor must be the first column of the index."
            )
        columns = list(marker.columns) if marker.columns is not None else [column_name]
        return IndexDefinition(
            cast(Any, None),
            name=marker.name,
            columns=columns,
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
    ) -> Optional[Union[Type[CreateTableStatement], Sequence[Type[CreateTableStatement]]]]:
        return None

    @classmethod
    def drop_table_statement_classes(
        cls,
    ) -> Optional[Union[Type[DropTableStatement], Sequence[Type[DropTableStatement]]]]:
        return None

    @classmethod
    def create_index_statement_classes(
        cls,
    ) -> Optional[Union[Type[CreateIndexStatement], Sequence[Type[CreateIndexStatement]]]]:
        return None

    @classmethod
    def drop_index_statement_classes(
        cls,
    ) -> Optional[Union[Type[DropIndexStatement], Sequence[Type[DropIndexStatement]]]]:
        return None

    @classmethod
    def column_name(cls, field: str) -> str:
        return cast(Any, cls).get_column_name(field)

    @classmethod
    def _field_metadata(cls, field: str) -> Optional["DDLFieldMetadata"]:
        """The collected DDL metadata for *field*, or ``None`` if none declared.

        A field the model does not have is refused with ``KeyError``: ``None``
        is the answer for a real field that declares nothing, and letting a
        misspelled name produce the same answer would hide the mistake. Every
        accessor reads its metadata through this one lookup, so the rule is
        identical for all of them.
        """
        if field not in (getattr(cls, "model_fields", {}) or {}):
            raise KeyError(field)
        return (getattr(cls, "__table_ddl_fields__", {}) or {}).get(field)

    @classmethod
    def column_data_type(cls, field: str) -> Optional[DDLColumnDataType]:
        cls._validate_ddl_annotations()
        metadata = cls._field_metadata(field)
        return metadata.use_sql_type if metadata is not None else None

    @classmethod
    def column_type(cls, field: str) -> Optional[DDLColumnType]:
        """The column-type declaration for *field*, in the form declared.

        Dialect-free, like :meth:`column_data_type`: the declaration is
        presented as written -- a ``UseColumnType`` marker (its candidates
        included), a single class, or a sequence -- or ``None`` when the field
        declares none. How the declaration is consumed is the caller's
        business; the framework's own consumer is :class:`FieldProxy`, which
        selects the class a backend answers.

        Raises:
            KeyError: The model has no such field.
            TypeError: More than one ``UseColumnType`` declaration on the field.
        """
        field_info = cast(Any, cls).model_fields[field]
        found = [
            item
            for item in (getattr(field_info, "metadata", None) or ())
            if isinstance(item, UseColumnType)
        ]
        if len(found) > 1:
            raise TypeError(
                f"{len(found)} UseColumnType declarations on a single field. A "
                f"field declares the column class it uses once; a model that "
                f"wants a different one declares it on a different model."
            )
        return found[0] if found else None

    @classmethod
    def column_constraints(cls, field: str) -> Sequence[ColumnConstraint]:
        cls._validate_ddl_annotations()
        metadata = cls._field_metadata(field)
        if metadata is None:
            return []
        # Multi-column UseConstraint markers declare a table-level fact and
        # surface through table_constraints(); they are not column-level
        # clauses and must not render inside a column definition.
        constraints = [
            marker.constraint
            for marker in metadata.constraints
            if marker.constraint is not None
        ]
        declared_types = {type(constraint.branch) for constraint in constraints}
        explicit_not_null = ColumnNotNullConstraint in declared_types
        explicit_nullable = ColumnNullableConstraint in declared_types
        source = cast(Any, cls)
        pk_member = cls.column_name(field) in source.primary_key_columns()
        if pk_member and not source.is_composite_pk():
            constraints.append(
                ColumnConstraint(cast(Any, None), branch=ColumnPrimaryKeyConstraint(cast(Any, None)))
            )
        if pk_member:
            if explicit_nullable:
                constraints = [
                    constraint
                    for constraint in constraints
                    if not isinstance(constraint.branch, ColumnNullableConstraint)
                ]
            if not explicit_not_null:
                constraints.append(
                    ColumnConstraint(cast(Any, None), branch=ColumnNotNullConstraint(cast(Any, None)))
                )
        elif not explicit_not_null and not explicit_nullable and not metadata.is_optional:
            constraints.append(
                ColumnConstraint(cast(Any, None), branch=ColumnNotNullConstraint(cast(Any, None)))
            )
        return constraints

    @classmethod
    def column_attributes(cls, field: str) -> Sequence[ColumnAttribute]:
        cls._validate_ddl_annotations()
        metadata = cls._field_metadata(field)
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
        metadata = cls._field_metadata(field)
        if metadata is None:
            return []
        return [
            cls.index_definition(marker, cls.column_name(field))
            for marker in metadata.indexes
        ]

    @classmethod
    def column_comment(cls, field: str) -> Optional[str]:
        cls._validate_ddl_annotations()
        metadata = cls._field_metadata(field)
        marker = getattr(metadata, "column_comment", None) if metadata else None
        return marker.comment if marker is not None else None

    @classmethod
    def generated_column(cls, field: str) -> Optional[DDLGeneratedColumn]:
        cls._validate_ddl_annotations()
        metadata = cls._field_metadata(field)
        marker = getattr(metadata, "generated_column", None) if metadata else None
        return marker.expression if marker is not None else None

    @classmethod
    def column_options(
        cls, field: str
    ) -> Optional[Union[ColumnOptions, Sequence[ColumnOptions]]]:
        cls._validate_ddl_annotations()
        metadata = cls._field_metadata(field)
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
    def columns_data_type(
        cls, fields: Optional[List[str]] = None
    ) -> Dict[str, Optional[DDLColumnDataType]]:
        return {field: cls.column_data_type(field) for field in cls._batch_fields(fields)}

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
        """The DDL metadata for *field*; a field the model lacks raises ``KeyError``."""
        metadata = cls._field_metadata(field)
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
    "DDLColumnDataType",
    "DDLColumnType",
    "DDLFieldMetadata",
    "DDLGeneratedColumn",
    "DDLSource",
    "DDLSourceMixin",
    "ObjectDeclaration",
    "IdentityAttribute",
    "MARKER_REGISTRY",
]
