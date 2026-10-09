# src/rhosocial/activerecord/backend/expression/types/_defaults.py
"""What a server supplies for a parameter that a declaration leaves out.

``length=None`` is not one thing, and that is the whole reason this module
exists.  On PostgreSQL a bare ``VARCHAR`` **is** unbounded: the catalog reports
``atttypmod = -1``, hands back the same bare word, and ``None`` says "no limit
at all".  On Oracle the same ``None`` means 4000 — not because the framework
chose 4000 but because Oracle cannot create an unsized ``VARCHAR2`` at all, so
the only ``VARCHAR2`` that can exist is a sized one.  Firebird's 255, SQL
Server's 255 and Snowflake's 16777216 are three more answers.  **No number is
right for more than one of them**, so a value written into the expression here
in core would be a claim about some other server.

The knowledge belongs to whoever knows the server's rules, and the only object
here that knows them is the dialect the concept already carries.  A dialect
therefore *declares* what it supplies, per concept and per parameter, through
:meth:`~...dialect.mixins.data_type.DataTypeMixin.type_parameter_defaults` —
and **declaring nothing is the majority answer, not a missing one.**  A backend
is never asked for a number it does not have: the empty mapping *is* the
statement "this server supplies no width for this concept", which is what
PostgreSQL says, and it says it by having nothing to say.  There is no list
anywhere of which concepts a backend is allowed to be silent about, because
silence is the default and a list of permissions to be silent would be a list
of permissions to be wrong.

Why the lookup is keyed by the class's own ``name``
--------------------------------------------------

``name`` is already the dispatch key: ``format_data_type_<name>`` routes on it,
``supports_data_type_<name>`` answers on it, and the supported-types mapping is
keyed by it.  Keying the declaration the same way means no second identity for
a type to be filed under, and it decides two cases that a bare ``varchar`` key
would get wrong:

* A backend type that is **the same concept through its own entry point** —
  SQL Server's ``NVARCHAR``, Snowflake's ``snowflake_varchar`` — has its own
  ``name`` and so declares its own key.  Two names, one concept, two
  declarations: neither has to guess what the other meant.
* A type that uses ``None`` to mean **unbounded** rather than **undeclared** —
  ``NVARCHAR(MAX)``, which is unbounded because ``MAX`` lifted a cap — declares
  nothing and keeps its ``None``.  That is not an exemption from a rule; it is
  the ordinary answer for a concept whose bare form has no width, and it falls
  out of keying on ``name`` with nothing else required.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from ...dialect import SQLDialectBase


def declared_parameter(
    concept: str,
    parameter: str,
    dialect: Optional["SQLDialectBase"],
) -> Optional[Any]:
    """The value *dialect* supplies for *concept* declared without *parameter*.

    ``None`` is the answer for a dialect that declares no default **and** for no
    dialect at all.  A type with no bound server has no width to resolve, and
    that has to stay answerable rather than raising: ``VarCharType()`` is built
    and compared all over the codebase with no dialect in hand, and an equality
    that raised because a width could not be looked up would be a far worse
    defect than the one this fixes.  So nothing here can fail — the lookup finds
    the hook or it does not, and both answers are a value.

    The hook is read through :func:`getattr` rather than demanded of every
    dialect because it is deliberately **not** a member of
    :class:`~...dialect.protocols.DataTypeSupport`: adding it there would make
    every dialect implement it to keep passing ``isinstance``, which is exactly
    the "every backend must supply a number" shape this design refuses.  A
    dialect that mixes in ``DataTypeMixin`` inherits the empty answer; one that
    does not is treated as supplying nothing, which is what it says by not
    having said otherwise.
    """
    if dialect is None:
        return None
    type_parameter_defaults = getattr(dialect, "type_parameter_defaults", None)
    if type_parameter_defaults is None:
        return None
    declared: Dict[str, Dict[str, Any]] = type_parameter_defaults()
    return declared.get(concept, {}).get(parameter)


__all__ = ["declared_parameter"]
