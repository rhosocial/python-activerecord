# src/rhosocial/activerecord/backend/impl/sqlite/examples/defaults.py
"""The defaults the SQLite examples share, in a module neither of them owns.

A default is a fact of the question the parameter's name asks, and the
signature that offers it is where that fact is written. When several
signatures ask one question, each of them writing the value down is a second
place that has to stay in step with the first, and nothing keeps it in step.
So a value several of them answer lives here, once, and they reference the
name.

This module is deliberately a leaf, and the reason is a dependency direction
rather than a style. ``DEFAULT_ORDER_STATUS`` was declared in
``named_expressions/order_dml.py`` and read by ``named_expressions/order_
clauses.py`` and ``named_migrations/migrations.py`` read
``DEFAULT_CUSTOM_TABLE_NAME`` out of its own sibling ``expressions.py`` -- so
a clause example depended on the DML example module, and a migration class
depended on the expressions module, for nothing but a string. Neither module
is the honest owner: the DML module owns the INSERT shape, the clause module
owns the WHERE shape, and the migration class owns the version ordering.
Declaring the value in any one of them puts whoever happens to have typed it
first in charge of what the others read, and the next reader has to know
which of the three to look in. A module both can import and neither has to be
ordered against is the answer, and it is the same shape as
``introspection/defaults.py``, ``expression/defaults.py`` and
``named_expression/defaults.py``: the shared values sit beside the layer they
serve and import nothing from it.

These are facts of the *fixtures the examples run against*, not facts of the
library: ``"pending"`` is the status the demo ``orders`` table is seeded with,
and ``"custom_table"`` is the one table the custom-table migration builds and
drops. No library module reads either of them, and putting them in the
library would give the library a demo default with no reader -- a capital
name nothing earns.

The rule that requires this is ``.claude/rules/constants.md``: a value read
from more than one function, where the readings must agree, takes a
module-level constant *and* a test that pins it. The test that pins these is
``tests/rhosocial/activerecord_test/feature/rules/test_shared_defaults.py``.
"""

#: The status a new order carries in the demo schema when the caller names
#: none.
#:
#: The order examples run against one fixture table whose first row is a
#: pending order, and three of the write and clause examples default to it.
#: Writing ``"pending"`` down three times would be three places that have to
#: stay in step: change one and the others would insert or filter on a status
#: the fixture does not hold, which is a silent mismatch rather than an error.
DEFAULT_ORDER_STATUS: str = "pending"

#: The table the custom-table migration creates when the caller names none.
#:
#: ``create_custom_table`` and ``drop_custom_table`` are the two halves of one
#: migration: the second has to drop the table the first built. Writing the
#: name down twice would be two places that have to stay in step with nothing
#: keeping them in step, and a migration that created a table its ``down()``
#: could not drop is a silent failure rather than an error.
DEFAULT_CUSTOM_TABLE_NAME: str = "custom_table"
