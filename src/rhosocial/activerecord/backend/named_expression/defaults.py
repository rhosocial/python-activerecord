# src/rhosocial/activerecord/backend/named_expression/defaults.py
"""Defaults the named-procedure layer answers in more than one signature.

A default is a fact of the question the parameter's name asks, and the
signature that offers it is where that fact is written. When several
signatures ask one question -- the diagram renderer and the procedure result
that asks it for a diagram, the logging entry points -- each of them writing
the value down is a second place that has to stay in step with the first, and
nothing keeps it in step. So a value several of them answer lives here, once,
and they reference the name.

This module is deliberately a leaf: it imports nothing from the package it
sits in, so both the procedure module and the diagram module can read it.
``diagram.py`` imports ``procedure.py`` at module level, so a default declared
in ``diagram.py`` would be readable by ``procedure.py`` only through a cycle --
and a default declared in ``procedure.py`` would be readable by ``diagram.py``
but would put the *reader* of a diagram question in charge of what a diagram
is. Neither is the honest owner, so the shared values sit in a module both can
import and neither has to be ordered against the other.

Which signature is the *definition* is decided by ownership rather than by
convenience. ``ProcedureDiagram.to_mermaid()`` is the method whose branch
decides what a ``kind`` means, so the diagram kind is the renderer's answer to
"which shape"; the log level is the entry a procedure's ``log()`` records when
its caller names none; and the procedure name is what a diagram labels a
procedure whose caller did not name it.

The rule that requires this is ``.claude/rules/constants.md``: a value read
from more than one function, where the readings must agree, takes a
module-level constant *and* a test that pins it. The test that pins these is
``tests/rhosocial/activerecord_test/feature/rules/test_shared_defaults.py``.

What this module deliberately does not hold:

* a value only one signature offers -- that is inlined, per the rule's
  decision table, and a capital name would not earn it;
* a literal that claims no name -- a positional argument at a call site, or a
  value inside a table's contents, is not a place answering a question, and
  repeating one of those is a coincidence rather than a duplicate;
* an enum member or a switch vocabulary -- a closed set takes an Enum and
  belongs to the one that names it, not to a table beside it.
"""

#: The diagram shape rendered when the caller names none.
#:
#: ``ProcedureDiagram.to_mermaid()`` branches on the value and raises on
#: anything else, so the closed set is that branch's; the default is its first
#: member, which is the one the module's own docstring shows.
DEFAULT_DIAGRAM_KIND: str = "flowchart"

#: The severity a log entry carries when the caller names none.
#:
#: ``INFO`` is the ordinary level: a procedure logs what it did, and a caller
#: who wants the details asks for ``DEBUG`` explicitly.
DEFAULT_LOG_LEVEL: str = "INFO"

#: The name a diagram labels a procedure whose caller did not name one.
#:
#: A diagram has to label something, and labelling it after the generic word
#: for the thing is honest where guessing a specific name would not be.
DEFAULT_PROCEDURE_NAME: str = "Procedure"
