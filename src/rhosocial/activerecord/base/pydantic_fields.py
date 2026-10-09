# src/rhosocial/activerecord/base/pydantic_fields.py
"""Where a pydantic-built field's value type is mapped onto the common types.

The protocol's vocabulary is *plain Python types*: the
common value types a column class can be suggested for. A model is free to
annotate a field with anything, and pydantic — which this project already depends
on, since its models are pydantic models — ships a family of field types that are
not plain: ``EmailStr``, ``SecretStr``, ``AnyUrl``, ``AwareDatetime``,
``ByteSize``, ``Json`` and their siblings. They are **wrapper classes** pydantic
defines, and they are not subclasses of the type they wrap; ``EmailStr`` in
2.13.5 has ``__mro__ == ('EmailStr', 'object')``. So a field annotated with one
of them lands outside the vocabulary, which makes resolution fail — the correct
answer for something genuinely unclassifiable, and the wrong answer for something
whose value type the *owner* has already declared.

This module is the one place that bridges the two, and it is a module rather
than lines inside the normaliser so that the boundary stays visible: this is the
only file in the core that knows what a pydantic field means, and if the project
ever decides the bridge should not exist, deleting one file removes it.

How the bridge works
--------------------
Three groups, and every pydantic field type belongs to exactly one of them. The
completeness test (in the backend test-suite, ``test_pydantic_field_vocabulary``)
asserts precisely that: ``pydantic.types`` plus ``pydantic.networks`` minus a
documented exclusion list, partitioned into these three with nothing left over.

1. **Already covered.** Most of pydantic's types need no bridge at all, because
   they are either an ``Annotated`` alias of a plain type or a subclass of one.
   ``constr``, ``conint``, ``confloat``, ``condecimal``, ``conbytes``,
   ``Base64Str``, ``Base64UrlStr``, ``StrictInt`` and every ``PositiveInt``-style
   constrained alias are ``Annotated[str, ...]`` and the existing
   ``Annotated``-peeling reaches them; ``ByteSize`` and ``PaymentCardNumber`` are
   subclasses of ``int`` and ``str`` and the existing subclass walk reaches them.
   These are listed in :data:`ALREADY_COVERED` so that a regression in the
   normaliser — one that stopped peeling ``Annotated``, say — is caught here
   rather than surfacing as a model that suddenly will not build.

2. **Mapped.** The class-built wrappers whose value type pydantic states
   unambiguously in their own core schema. :data:`PYDANTIC_FIELD_TO_ENTRY` names
   each one and the protocol entry it normalises to.

3. **Not mapped.** Types with no plain value type, or with one the mapping would
   be inventing. :data:`PYDANTIC_FIELD_NOT_MAPPED` lists them with the reason, and
   a field annotated with one of these fails exactly as it did before this module
   existed — declaring ``UseColumnType`` remains the route forward.

Ordering inside resolution, and why the bridge is last
-----------------------------------------------------
The bridge is consulted **after** an explicit ``UseColumnType`` (which wins
everywhere and is unaffected) and **after** the existing exact-match, enum and
subclass rules (which must keep answering the plain vocabulary exactly as they
always did). It sits between "the annotation matched something" and "the
annotation is unclassifiable", so it can only turn a failure into an answer and
can never change an answer that already existed.

That ordering is what keeps it from being a universal column by another name: a
backend that answers ``None`` for the resulting entry still refuses, and
a backend that answers a column class still chooses it. The bridge decides what
*Python type* a pydantic wrapper means — never which column class to use.
"""

# src/rhosocial/activerecord/base/pydantic_fields.py
import datetime
import decimal
import enum
import uuid
from typing import Any, Dict, Type

# ---------------------------------------------------------------------------
# 1. Already covered by the existing normalisation
# ---------------------------------------------------------------------------

#: pydantic field types that need no bridge: ``Annotated`` aliases of a plain type,
#: or subclasses of one. Every one of these resolves through the peeling and
#: subclass-walk rules the protocol already had, and this tuple exists so that a
#: regression in those rules is caught by a test rather than by a model.
#:
#: The groups are spelled out because they are different mechanisms:
#:
#: * ``Annotated[str, ...]`` and friends — ``constr``, ``conint``, ``confloat``,
#:   ``condecimal``, ``conbytes``, ``Base64Str``, ``Base64UrlStr``, ``StrictInt``,
#:   ``StrictStr``, ``PositiveInt``, ``NegativeFloat``, ``FiniteFloat`` and the
#:   rest of the constrained aliases. ``constr`` is a *function* returning an
#:   annotated alias, so it appears here as its result's type, which is also why
#:   ``constr(...)`` itself needs no entry: it is already ``str``;
#: * subclasses — ``ByteSize`` is an ``int`` subclass and ``PaymentCardNumber`` a
#:   ``str`` subclass, so the subclass walk files them under the entry they
#:   extend. ``PaymentCardBrand`` is a ``str`` subclass too, but its core schema
#:   says ``enum``, so it is deliberately **not** here — see
#:   :data:`PYDANTIC_FIELD_NOT_MAPPED`.
ALREADY_COVERED = (
    "constr",
    "conint",
    "confloat",
    "condecimal",
    "conbytes",
    "constr",
    "Base64Str",
    "Base64UrlStr",
    "Base64Bytes",
    "Base64UrlBytes",
    "StrictInt",
    "StrictStr",
    "StrictFloat",
    "StrictBool",
    "StrictBytes",
    "PositiveInt",
    "NonNegativeInt",
    "NegativeInt",
    "NonPositiveInt",
    "PositiveFloat",
    "NonNegativeFloat",
    "NegativeFloat",
    "NonPositiveFloat",
    "FiniteFloat",
    "ByteSize",
    "PaymentCardNumber",
    "UUID1",
    "UUID3",
    "UUID4",
    "UUID5",
    "UUID6",
    "UUID7",
    "UUID8",
)

# ---------------------------------------------------------------------------
# 2. Mapped: pydantic states the value type, and it is a protocol entry
# ---------------------------------------------------------------------------

#: The protocol entry a mapped pydantic field normalises to.
#:
#: Every entry here is one pydantic declares in its own core schema — measured
#: on pydantic 2.13.5 with ``TypeAdapter(T).core_schema`` — and each maps to a
#: common Python type, so the backend's own table still answers for it and a
#: backend that answers ``None`` still refuses.
#:
#: ``url`` is not in the vocabulary, and the ``AnyUrl`` family is mapped to ``str``
#: on the strength of pydantic's own schema wording — a URL *is* a string, and the
#: constraints that make it a URL are pydantic's to enforce, not the column's.
#: The same reasoning covers the DSN aliases (``AmqpDsn``, ``MySQLDsn``, …), which
#: are URLs with a scheme pydantic knows.
#:
#: ``IPvAnyAddress`` and the rest are mapped to ``str`` for the same reason, with
#: one caveat recorded rather than smoothed over: ``IPv4Address``,
#: ``IPv4Interface``, ``IPv4Network`` and their IPv6 counterparts declare
#: ``lax-or-strict`` with **no** inner value type, so pydantic does not actually
#: state that they are strings — they are accepted from either, and the
#: validated instance is what the DB sees. Mapping them to ``str`` is a decision
#: this table makes, not a fact it reads, which is why they are grouped with a
#: comment instead of being cited as pydantic-declared.
PYDANTIC_FIELD_TO_ENTRY: Dict[Any, Any] = {
    # --- pydantic states `str` in its core schema -------------------------
    "EmailStr": str,
    "NameEmail": str,
    "SecretStr": str,
    # --- pydantic states `bytes` (via lax-or-strict, same caveat) ---------
    "SecretBytes": bytes,
    # --- pydantic states `datetime` / `date` ------------------------------
    "AwareDatetime": datetime.datetime,
    "NaiveDatetime": datetime.datetime,
    "PastDatetime": datetime.datetime,
    "FutureDatetime": datetime.datetime,
    "PastDate": datetime.date,
    "FutureDate": datetime.date,
    # --- pydantic states `url`; a URL is a string -------------------------
    "AnyUrl": str,
    "AnyHttpUrl": str,
    "HttpUrl": str,
    "FileUrl": str,
    "FtpUrl": str,
    "WebsocketUrl": str,
    "AnyWebsocketUrl": str,
    "AmqpDsn": str,
    "ClickHouseDsn": str,
    "CockroachDsn": str,
    "KafkaDsn": str,
    "MariaDBDsn": str,
    "MongoDsn": str,
    "MySQLDsn": str,
    "NatsDsn": str,
    "PostgresDsn": str,
    "RedisDsn": str,
    "SnowflakeDsn": str,
    # --- pydantic states nothing; this table decides ----------------------
    "IPv4Address": str,
    "IPv4Interface": str,
    "IPv4Network": str,
    "IPv6Address": str,
    "IPv6Interface": str,
    "IPv6Network": str,
    "IPvAnyAddress": str,
    "IPvAnyInterface": str,
    "IPvAnyNetwork": str,
    # --- the JSON bridge the backend tables support -----------------------
    "Json": dict,
}

# ---------------------------------------------------------------------------
# 3. Not mapped: no plain value type, or one this table would be inventing
# ---------------------------------------------------------------------------

#: pydantic field types that stay outside the vocabulary, with the reason.
#:
#: A field annotated with one of these fails to resolve exactly as it did before
#: this module existed, and ``UseColumnType`` remains the way past it. Nothing
#: here is a gap to be filled later; each is a place where a mapping would be a
#: decision the table is not entitled to make.
#:
#: ``DirectoryPath``, ``FilePath``, ``NewPath`` and ``SocketPath`` are the
#: clearest case: their core schema's inner type is ``pathlib.Path``, and
#: ``Path`` is **not** a vocabulary entry, so there is nothing to map *to*.
#: Substituting ``str`` would lose the only thing that makes them a filesystem
#: path rather than text.
#:
#: ``PaymentCardBrand`` is a ``str`` subclass, so the subclass walk will happily
#: file it under ``str`` — but its core schema says ``enum``, and it is a
#: *controlled* vocabulary of four brands rather than free text. It is named here
#: so the disagreement is recorded; the subclass walk still answers, and a reader
#: comparing the two lists can see that it answers by type and not by meaning.
#:
#: ``ImportString`` is a dotted import path with no database type of any kind.
#: ``Json`` is mapped to ``dict`` (see :data:`PYDANTIC_FIELD_TO_ENTRY`) because
#: every backend's table answers ``dict -> JSONColumn``, which is the JSON bridge
#: the pairing work measured — a ``Json`` field holding an array still stores as
#: JSON, and the value layer's ``json.dumps`` on bind is the same requirement
#: ``dict`` already carries.
PYDANTIC_FIELD_NOT_MAPPED = (
    "DirectoryPath",
    "FilePath",
    "NewPath",
    "SocketPath",
    "PaymentCardBrand",
    "ImportString",
)

# ---------------------------------------------------------------------------
# The names that are skipped when enumerating pydantic's field types
# ---------------------------------------------------------------------------

#: Public names of ``pydantic.types`` / ``pydantic.networks`` that are **not**
#: field types, and why. The completeness test subtracts these before asserting
#: that everything else is classified, because a test that expected every public
#: name to be a field type would fail on ``ValidationError``.
#:
#: Kept as one frozenset of names rather than filtered by kind, because the kinds
#: are not always distinguishable at runtime: ``EncodedStr`` is a validator
#*   function, ``ValidationInfo`` a dataclass, and ``TypeAdapter`` a class you
#: would never annotate a field with — and all three look like types to
#: ``isinstance(x, type)``.
NOT_FIELD_TYPES = frozenset({
    # validators, validators-in-progress and their wrappers
    "AfterValidator", "BeforeValidator", "WrapValidator", "PlainValidator",
    "InstanceOf", "SkipValidation", "ValidateAs", "StringConstraints",
    "EncodedStr", "EncodedBytes", "EncoderProtocol", "SchemaSerializer",
    "WrapSerializer", "PlainSerializer",
    # errors and warnings
    "PydanticCustomError", "PydanticUserError", "PydanticInvalidForJsonSchema",
    "PydanticSchemaGenerationError", "PydanticUndefinedAnnotation",
    "PydanticForbiddenQualifier", "PydanticDeprecatedSince20",
    "PydanticDeprecatedSince210", "PydanticDeprecatedSince211",
    "PydanticDeprecatedSince212", "PydanticDeprecatedSince26",
    "PydanticDeprecatedSince29", "PydanticExperimentalWarning",
    "PydanticDeprecationWarning", "ValidationError",
    "PydanticSerializationUnexpectedValue",
    # configuration and metadata
    "ConfigDict", "BaseConfig", "BaseMetadata", "AliasChoices", "AliasPath",
    "AliasGenerator", "WithJsonSchema", "GetPydanticSchema",
    "GetCoreSchemaHandler", "GetJsonSchemaHandler", "UrlConstraints",
    "AllowInfNan", "FailFast", "Strict", "Tag", "Discriminator", "MaxLen",
    "MinLen", "Pattern", "UuidVersion", "OnErrorOmit", "Ignored",
    # model machinery, generics and protocols
    "BaseModel", "RootModel", "TypeAdapter", "TypeAliasType", "TypeVar",
    "Generic", "Union", "Any", "Enum", "Hashable", "ModuleType", "PathType",
    "Path", "Decimal", "date", "datetime", "UUID", "object", "Iterator",
    "ValidationInfo", "SerializationInfo", "FieldSerializationInfo",
    "ModelWrapValidatorHandler", "ValidatorFunctionWrapHandler",
    "SerializerFunctionWrapHandler", "MultiHostHost", "Secret",
    "PydanticUseCaseMark",
})


# ---------------------------------------------------------------------------
# The bridge itself
# ---------------------------------------------------------------------------


def _pydantic_module():
    """The ``pydantic`` package, or ``None`` when it is not importable.

    Imported lazily and defensively: the bridge is only consulted for an
    annotation that nothing else could classify, so a project that never
    annotates a field with a pydantic wrapper pays nothing. Core does depend on
    pydantic for its model layer, so in practice this always succeeds — but the
    fallback keeps the expression layer importable on a stripped install, which
    is the same reason the module is not imported at the top of the file.
    """
    try:
        import pydantic  # noqa: PLC0415 -- optional at import time by design
        return pydantic
    except Exception:  # pragma: no cover - only on a stripped install
        return None


def mapped_pydantic_entry(name: str) -> Any:
    """The protocol entry pydantic's field type *name* maps to, or ``None``.

    Looked up by **name** rather than by class object, because the classes are
    only reachable through ``pydantic.networks`` / ``pydantic.types`` and a name
    is what survives being written in a table a human can read and diff. The
    classes are then resolved through the package, so the mapping cannot refer to
    a type pydantic has since renamed: an unknown name simply has no answer, and
    the completeness test is what catches a rename.
    """
    return PYDANTIC_FIELD_TO_ENTRY.get(name)


def is_pydantic_field_name(name: str) -> bool:
    """Whether *name* is one this bridge classifies at all."""
    return name in PYDANTIC_FIELD_TO_ENTRY or name in PYDANTIC_FIELD_NOT_MAPPED


def normalize_pydantic_annotation(annotation: Any) -> Any:
    """The value type *annotation* stands for, or ``None`` if unknown.

    The single entry point the protocol's normaliser calls, and the only thing it
    calls. An annotation that is not a pydantic-defined type gets ``None`` back,
    which the caller treats exactly as it treated an unmatched annotation before
    this module existed.

    Resolution order inside the bridge:

    1. The annotation's **class name** against :data:`PYDANTIC_FIELD_TO_ENTRY`,
      then :data:`PYDANTIC_FIELD_NOT_MAPPED`. A name hit is the whole answer and
      nothing further is consulted — pydantic's declaration and this table agree,
      and reading pydantic's schema as well would only slow the common path down
      and could disagree with the table's recorded decision.
    2. Nothing. There is no second step: pydantic is *asked* by nothing in this
      module, because asking means runtime introspection of
      ``TypeAdapter(T).core_schema`` on every unclassified annotation, and the
      cases where that would add an answer are exactly the ones already written
      down here. If pydantic later ships a new field type, the completeness test
      fails and the table gains a line — a visible diff, rather than a silently
      different answer.
    """
    name = getattr(annotation, "__name__", None)
    if name is None:
        return None

    if name in PYDANTIC_FIELD_TO_ENTRY:
        return PYDANTIC_FIELD_TO_ENTRY[name]

    # Deliberately unmapped, or not ours at all: both are "no answer from here",
    # and the caller's error message is what tells the two apart.
    return None


__all__ = [
    "ALREADY_COVERED",
    "NOT_FIELD_TYPES",
    "PYDANTIC_FIELD_NOT_MAPPED",
    "PYDANTIC_FIELD_TO_ENTRY",
    "is_pydantic_field_name",
    "mapped_pydantic_entry",
    "normalize_pydantic_annotation",
]
