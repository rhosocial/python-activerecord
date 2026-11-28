# src/rhosocial/activerecord/backend/expression/defaults.py
"""Defaults the expression layer answers in more than one signature.

A default is a fact of the question the parameter's name asks, and the
signature that offers it is where that fact is written. When several
signatures ask one question -- a node and the factory that wraps it, a node
and the mixin method that builds one on a value -- each of them writing the
value down is a second place that has to stay in step with the first, and
nothing keeps it in step. So a value several of them answer lives here, once,
and they reference the name.

This module is deliberately a leaf: it imports nothing from the expression
package, so the modules at every level of it can read it. ``mixins.py`` sits
at the bottom and is imported by nearly everything, so it cannot import
``advanced_functions`` back -- which is why a trim-direction default declared
in ``advanced_functions.py`` would have been read by a module that could not
reach it, and the whole exercise would have failed on an ``ImportError`` at
import time.

Which signature is the *definition* is decided by ownership rather than by
convenience. ``TrimExpression`` is the node the dialect renders, so it owns
the trim direction; the ``trim()`` factory and ``StringValueMixin.trim()``
forward the caller's choice to it, and a caller that never named one gets the
direction the node would have applied anyway.

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

#: The trim direction applied when the caller names none.
#:
#: ``BOTH`` is what SQL itself defaults to: ``TRIM(x)`` strips both ends.
#: ``TrimExpression`` owns the question -- it is the node the dialect renders,
#: and the factory and the mixin method forward their callers' choices to it
#: -- so the value is defined once and all three signatures read it.
TRIM_DEFAULT_DIRECTION: str = "BOTH"
