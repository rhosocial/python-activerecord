"""Data definition statements, one protocol per statement expression.

Each protocol here corresponds to one statement expression: the ``format_*``
methods it declares are the counterparts of the ``format_method`` those
expressions name. An engine that supports one form of a statement but not
another implements the protocol for the form it has, so ``CREATE TABLE ... LIKE``
being unavailable is expressed by leaving out CreateTableLikeSupport rather than
by a switch inside CreateTableSupport.

Naming an object is a separate capability and lives in
:mod:`~rhosocial.activerecord.backend.dialect.protocols.object`. The two are
independent: an engine may name a table without being able to create one.
"""

from .table.alter_table import AlterTableSupport
from .table.create_table import CreateTableSupport
from .table.create_table_as import CreateTableAsSupport
from .table.create_table_clone import CreateTableCloneSupport
from .table.create_table_like import CreateTableLikeSupport
from .table.create_table_using_template import CreateTableUsingTemplateSupport
from .table.drop_table import DropTableSupport
from .view.create_view import CreateViewSupport
from .view.drop_view import DropViewSupport
from .view.materialized_view import MaterializedViewSupport
from .index.create_index import CreateIndexSupport
from .index.drop_index import DropIndexSupport
from .index.fulltext import FulltextIndexSupport
from .sequence.alter_sequence import AlterSequenceSupport
from .sequence.create_sequence import CreateSequenceSupport
from .sequence.drop_sequence import DropSequenceSupport
from .trigger.create_trigger import CreateTriggerSupport
from .trigger.drop_trigger import DropTriggerSupport
from .routine.create_function import CreateRoutineSupport
from .routine.drop_function import DropRoutineSupport
from .type_.alter_type import AlterTypeSupport
from .type_.create_type import CreateTypeSupport
from .type_.drop_type import DropTypeSupport
from .domain.alter_domain import AlterDomainSupport
from .domain.create_domain import CreateDomainSupport
from .domain.drop_domain import DropDomainSupport
from .database.alter_database import AlterDatabaseSupport
from .database.create_database import CreateDatabaseSupport
from .database.drop_database import DropDatabaseSupport
from .schema.create_schema import CreateSchemaSupport
from .schema.drop_schema import DropSchemaSupport
from .alter_table_modifier import AlterTableModifierSupport
from .auto_increment import AutoIncrementSupport
from .column_attribute import ColumnAttributeSupport
from .comment import CommentSupport
from .constraint import ConstraintSupport
from .generated_column import GeneratedColumnSupport
from .partition import PartitionSupport
from .truncate import TruncateSupport

__all__ = [
    "AlterDatabaseSupport",
    "AlterDomainSupport",
    "AlterSequenceSupport",
    "AlterTableModifierSupport",
    "AlterTableSupport",
    "AlterTypeSupport",
    "AutoIncrementSupport",
    "ColumnAttributeSupport",
    "CommentSupport",
    "ConstraintSupport",
    "CreateDatabaseSupport",
    "CreateDomainSupport",
    "CreateIndexSupport",
    "CreateRoutineSupport",
    "CreateSchemaSupport",
    "CreateSequenceSupport",
    "CreateTableAsSupport",
    "CreateTableCloneSupport",
    "CreateTableLikeSupport",
    "CreateTableSupport",
    "CreateTableUsingTemplateSupport",
    "CreateTriggerSupport",
    "CreateTypeSupport",
    "CreateViewSupport",
    "DropDatabaseSupport",
    "DropDomainSupport",
    "DropIndexSupport",
    "DropRoutineSupport",
    "DropSchemaSupport",
    "DropSequenceSupport",
    "DropTableSupport",
    "DropTriggerSupport",
    "DropTypeSupport",
    "DropViewSupport",
    "FulltextIndexSupport",
    "GeneratedColumnSupport",
    "MaterializedViewSupport",
    "PartitionSupport",
    "TruncateSupport",
]
