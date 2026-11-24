# src/rhosocial/activerecord/base/field_generation.py
"""Apply ActiveRecord-side field generators to a write payload.

A generator is declared on a field with ``UseFieldGenerator``. It is a Python
callable that runs before the write and supplies the value; a field with no
generator for the current operation is *filtered out* of that operation's
write set. This module is deliberately backend-agnostic -- the generated value
is an ordinary Python value and the existing adapter/type machinery handles it.
"""

from typing import Any, Dict, Optional, TYPE_CHECKING

from ..types import WriteOperation
from .fields import UseFieldGenerator

if TYPE_CHECKING:  # pragma: no cover
    from .ddl import ModelDDLDeclaration


def generator_annotation(source: "ModelDDLDeclaration", field: str) -> Optional[UseFieldGenerator]:
    """The field's generator, from its annotation or a mixin declaration.

    A field-level ``UseFieldGenerator`` annotation wins over a mixin's
    ``field_generators()`` entry, so a model can override inherited behaviour
    simply by annotating the field.
    """
    declared = dict(source.field_generators())
    for annotation in source.column_annotations(field):
        if isinstance(annotation, UseFieldGenerator):
            return annotation
    return declared.get(field)


def apply_field_generators(
    source: "ModelDDLDeclaration",
    instance: Any,
    operation: WriteOperation,
    data: Dict[str, Any],
    *,
    only: Optional[Any] = None,
) -> Dict[str, Any]:
    """Run every declared generator for *operation* and filter ungenerated fields.

    ``source`` is the model class (a ``ModelDDLDeclaration``); ``instance`` receives the
    generated values via ``setattr``. ``data`` is the write payload being built.
    ``only``, when given, restricts which fields are considered (used by the
    soft-delete path, which writes a single field).
    """
    fields = tuple(only) if only is not None else tuple(source.model_fields)
    for field in fields:
        annotation = generator_annotation(source, field)
        if annotation is None:
            continue
        generator = annotation.generator_for(operation)
        if generator is None:
            # No generator for this operation: keep the field out of the write
            # set so a database default or the existing column value survives.
            data.pop(field, None)
            continue
        value = generator(instance)
        setattr(instance, field, value)
        data[field] = value
    return data
