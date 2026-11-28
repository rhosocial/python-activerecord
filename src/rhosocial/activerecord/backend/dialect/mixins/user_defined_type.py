# .../user_defined_type.py
"""Composition base for UserDefinedTypeMixin. No own members."""

from typing import Tuple, Type as TypingType, TYPE_CHECKING
from rhosocial.activerecord.backend.dialect.exceptions import UnsupportedFeatureError
from rhosocial.activerecord.backend.expression.objects import Type
from rhosocial.activerecord.backend.expression.statements import TypeAlterAction, TypeDefinition
from .create_type_mixin import CreateTypeMixin
from .alter_type_mixin import AlterTypeMixin
from .drop_type_mixin import DropTypeMixin

class UserDefinedTypeMixin(CreateTypeMixin, AlterTypeMixin, DropTypeMixin):
    pass


