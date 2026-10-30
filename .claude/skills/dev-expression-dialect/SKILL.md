---
name: dev-expression-dialect
description: Architecture guide for the Expression-Dialect separation system in rhosocial-activerecord - expression modules, dialect protocols/mixins, SQL generation rules, when a backend may derive an expression class, and how to add new protocols
license: MIT
compatibility: opencode
metadata:
  category: architecture
  level: advanced
  audience: developers
---

# Expression-Dialect System

The architecture that separates SQL **query construction** (expressions) from SQL
**generation** (dialects), so the same query builds portably and each database
renders its own words.

```
Query (ActiveQuery)
  ↓
Expression (SQLColumn)      ← calls dialect.format_*()
  ↓
Dialect (SQLiteDialect)     ← generates SQL
  ↓
Backend (StorageBackend)
```

Information flows **one way**, from a typed object to SQL text:

```
caller builds an expression  →  factory composes expressions  →  dialect renders
   Column / Literal / ...        FunctionCall                   format_*
```

Two rules decide most of the rest:

1. **Information flows one way.** A formatter needs an expression to have
   anything to format, so **no formatting function may manufacture the
   expression it is about to render** — not by guessing, coercing, or parsing.
2. **A backend is entirely static.** An IDE and a type checker give a definite
   answer. Nothing is worked out at run time, and nothing is left for the caller
   to assert in a form a checker cannot read.

---

## 1. The only two semantic entry points

The expression layer exposes exactly two kinds of semantic entry point, and
nothing else.

**`to_sql()`** — the single method on every expression / predicate / statement.

> **IRON RULE — `to_sql()` accepts NO parameters. Absolutely never.** It is a
> terminal method: every value it needs was already collected when the
> expression was **instantiated**. The signature is fixed by `ToSQLProtocol` as
> `to_sql(self) -> SQLQueryAndParams`. No `to_sql(inline_literals=...)`, no
> keyword arguments, no rendering options.

**`dialect.format_*()`** — the single family of formatting functions.

> **IRON RULE — a `format_*()` accepts expression-class instances only, never
> additional formatting parameters.** It receives the expression it must render
> (and the dialect), and nothing else. No rendering flags, no per-call options.

**Consequence — every formatting choice is a construction-time choice.** If an
output must differ (a `Literal` in a DDL clause that takes no bind parameters has
to render inline), that is captured **when the expression is instantiated**: the
class collects it as a constructor parameter and carries it, so `to_sql()` and
`format_*()` are pure reads of already-collected state. A render-time choice that
seems necessary means the expression was constructed wrong.

### An expression collects; a formatter validates

An expression **collects its parameters and nothing more.** Its `__init__`
accepts them, stores them, and stops. It does **not** check them, does **not**
normalize them, and does **not** raise on a value a particular dialect might
reject.

**Validation belongs to the formatter**, because only the formatter knows the
dialect that has to render the expression:

```python
# WRONG — the expression decides, before any dialect is consulted
def __init__(self, dialect=None, *, unsigned: bool = False):
    if not isinstance(unsigned, bool):
        raise TypeError("unsigned must be a bool")
    self.unsigned = unsigned

# RIGHT — the expression collects; the dialect decides what it can honour
def __init__(self, dialect=None, *, unsigned: bool = False):
    self.unsigned = unsigned

def format_data_type_integer(self, data_type) -> Tuple[str, tuple]:
    self._check_spelling(data_type, IntegerType)   # dialect-level gate
    self._refuse_unsigned(data_type, "INTEGER")    # honour or refuse, by name
    ...
```

**Why.** An expression is dialect-independent and knows nothing about which
server will render it. A check placed in `__init__` can only answer a
dialect-blind question ("is this a bool?"), while the question that actually
matters — "can **this** backend honour this value?" — can only be answered by
the formatter that knows the backend. Putting the check where the knowledge
lives keeps one answer per question, and it is the answer a reader needs.

A type annotation already states the shape; a checker verifies it statically.
A second, run-time statement of the same fact is the kind of thing
`anti-patterns.md` lists as *disabling checking rather than satisfying it*, and
it is the reason so many expressions carry a raise that the annotation had
already made impossible.

**The corollary — collect completely at instantiation.** Because nothing is
checked and normalized later, every value the rendering will need must be a
constructor parameter. A formatter that reaches back for a value the
constructor did not take has found a design error: either add the parameter, or
the choice was never the expression's to make.

### No probing: an attribute is either declared or it is an error

**An expression class *is* the protocol.** Its signature declares the fields it
carries, and a formatter is written against that declaration. So whether a field
exists is **statically settled**: either the core class declares it (every
subclass has it, because a subclass may not rewrite the core signature — see
"Protocol B" below), or no class in the family has it.

That is why a formatter **reads the attribute directly**:

```python
# WRONG — probes for something that is settled at class-definition time
if getattr(data_type, "unsigned", False):
    ...

# RIGHT — the field is declared; its presence is not in question
if data_type.unsigned:
    ...
```

**Why probing is forbidden.** The `getattr` default is a claim that the field
*might* be absent, and it is always false — either the field is there, or the
wrong class was passed. The two cases then look identical:

- a caller passes a class without the field, and the formatter renders as if the
  flag were `False`, silently dropping a declaration the caller made;
- the same formatter later "supports" a family it never renders, because it
  never distinguishes the two.

Using the wrong expression becomes an `AttributeError` **at the point of the
mistake**, which is the one place a reader can act on it. A default converts
that crash into a quiet wrong answer. `anti-patterns.md` lists `__getattr__`
forwarding on an expression class for the same reason — a checker stops there
and every attribute looks valid; `getattr` with a default is the same blindness,
written at the call site instead of on the class.

**What to do instead.** If the field really is optional for some member of the
family, that is a statement about the *protocol*, so fix the protocol: give each
class the field, or split the formatter so each one reads what its own annotation
declares. If the formatter is handed the wrong class, let it say so.

**Forbidden:** any `render*()` method, `to_sql_inline()`, or other "variant
rendering" entry point. One `to_sql()`, one `format_*()` per concern.

### An expression and its formatter are one-to-one

The pairing is **strictly one-to-one, in both directions**:

- Every concrete expression class **names exactly one** `format_*()` method, and
  declares that name **once, for itself** — via the read-only `format_method`
  property. An expression that has not overridden it is **not renderable**;
  reading the getter raises `NotImplementedError`, and a formatter the bound
  dialect does not provide raises `UnsupportedFeatureError`.
- **No formatter is shared by two expressions.** If two classes name the same
  `format_*()` method, the pairing is no longer one-to-one and one of them does
  not need to exist. A word-count difference between two expressions that render
  the same SQL is a `spelling`, a parameter, or a storage difference — not a
  reason for a second class pointing at one formatter.

The declaration is read-only by construction — a plain `@property` with no
setter — so it cannot be mutated at run time, and `to_sql()` resolves that one
declared name against the bound dialect and calls it with **this** expression.

**Why it is one-to-one.** The pairing is the seam that makes a backend
overridable and the system checkable: one name per expression means a renderer
is findable by reading the class, and a class is findable by its formatter.
Sharing a formatter across classes collapses that — two expressions become
indistinguishable to dispatch, and the schema differ starts inventing changes
between them. Measured: `PostgresByteaType` and core `BlobType` both render
`BYTEA`, and eleven Snowflake classes render what their core types already
render; one-to-one is what those defects break.

**No private helpers in the protocol or implementation.** All behaviour is
reachable through the public surface — `to_sql()`, `format_*()`, `supports_*()`.
If you feel the urge to add `_render_*` / `_format_*`, the public protocol is
missing a deliberate capability; the fix belongs in the protocol or in how the
expression is constructed, never in a hidden helper. A private helper becomes a
second, invisible protocol: a backend unaware of it renders differently and no
conformance test sees the divergence.

### Why the reverse direction is not a style preference

The type position of a cast cannot take a bind parameter, so whatever lands
there is SQL code. That is why `cast()` takes a `DataType` and refuses a string,
and why `CustomType` validates its name: the reverse direction is where
injection lives. The same shape appears wherever a loose value is turned into a
node — a helper that accepts `str` and decides whether it is a column name or a
string value infers SQL semantics at run time, invisibly at the call site.

**Forbidden:** a coercion helper that manufactures the expression; a factory
parameter typed `Any` or `Union[str, BaseExpression]`; parsing rendered SQL
back into a domain object.

### Formatting is pure concatenation — never scan the SQL string

Formatting concatenates fragments (identifiers via `format_identifier`, literal
atoms via `format_literal`, placeholders, pre-rendered sub-fragments). It must
never inspect, parse, or rewrite the assembled SQL — no `startswith`/`endswith`
checks, no regex, no quote-state machine, no post-hoc placeholder substitution.

Generated SQL is the **output** of formatting, not its input; reading it guesses
at structure the formatter already held as typed data, and it is an injection
surface.

**The single exception — inline literals.** A value can be spliced into the SQL
text instead of bound, and the call site asks for that per value:
`Literal(dialect, value, inline=True)`. The dialect then produces escaped,
quoted atoms (`inline_sql_literal`) concatenated during formatting — no
re-scanning.

Whether to inline is **the caller's decision, not the framework's**: some
engines reject a statement carrying a bind parameter in a position with no room
for one, and the developer knows which engine the statement is for. The default
is bind parameters (`inline=False`), because inlining is an injection hazard by
nature — inline content is trusted-only, never reachable by end users. A
formatter must not inline on its own initiative, and must not refuse a statement
merely because it binds where an engine would prefer text.

---

## 2. Layering: where a feature belongs

Decide placement by how *broad* a feature's base is.

1. **Broad base → generic layer.** Exists with standard semantics across many
   databases. Lift it to core as a `XxxSupport` protocol + `XxxMixin`
   implementation + `supports_xxx()`. Backends compose the pair and inherit it
   untouched. The goal: the generic layer implements **as much as possible**,
   minimising backend work.
2. **No broad base → per-backend, backend-named.** Vendor-specific syntax (table
   partitioning, proprietary clauses) is implemented by each backend and
   **prefixed with the backend name** (`MySQLRangePartition`,
   `PostgresRangePartition`, …). Core provides at most an empty marker base;
   each backend claims its own classes.
3. **Generic implementation doesn't fit a backend → that backend overrides.** See
   "Override Discipline (Generic-First)" below.

Placement summary: **main package** when defined in the SQL standard or widely
supported; **dialect extension** when vendor-specific. `CREATE TRIGGER` /
`CREATE FUNCTION` → main; `COMMENT ON`, `BIGSERIAL` → PostgreSQL; `AUTO_INCREMENT`
→ MySQL; `RANGE`/`LIST`/`HASH` partitioning → backend-specific.

---

## 3. Generic vs backend: the two-way responsibility

The generic and concrete layers divide responsibility in **two** directions, and
both are mandatory.

**1. The generic layer must actively balance across backends.** When defining a
generic expression's parameters, `supports_*()` switches, and `format_*()`, the
core deliberately accounts for **how the backends differ** — modelled broadly
enough to cover the shared semantics, with a sensible generic default — so each
backend can inherit it untouched.

**2. A difference the generic layer cannot balance is handled by the backend
alone.** The backend derives **its own** expression class from the generic base,
its own `supports_*()` switches, and its own `format_*()`. This is the
`MySQLRangePartition` / `PostgresRangePartition` pattern.

> **IRON RULE — a backend must never reuse another backend's expression classes,
> switches, or formatters — not even when byte-for-byte identical.** MariaDB does
> not import MySQL's partition expressions; it declares its own `MariaDB*` classes
> from the same generic base. Backends are **independent**: each depends only on
> core, never on a sibling. Sharing welds their fates — a change for one silently
> changes the other, and the override seam lands in the wrong package. "Identical
> today" is not a reason to share; identity is not guaranteed tomorrow.

### Override Discipline (Generic-First)

Generic mixins implement the standard behaviour **once**. A concrete dialect
composes a Support/Mixin pair and inherits it; it overrides a method **only when
its real capability or behaviour differs from the generic implementation**. Never
re-declare a method just to return the value the mixin already provides.

Rationale: backends stay minimal, the overrides read as an exact diff against the
generic implementation, and dialects become comparable at a glance. Enforced by
`tests/.../dummy/test_dummy_protocol_member_completeness.py` plus per-feature
tests asserting `"method" not in ConcreteDialect.__dict__` for dialects that
match the generic behaviour.

The identity / auto-increment probes fail closed: `IdentityColumnMixin` and
`AutoIncrementMixin` default every probe to `False` (a probe answering `True` by
default would emit SQL the server rejects), so each dialect declares only what it
really has and `DummyDialect` overrides them to `True`.

### Backend protocol changes require extreme restraint

The protocol is a **shared contract implicated across every backend**. Before
touching it: (1) research every backend's implementation and validate against
real servers; (2) make the change minimal, generic, composable with every
existing contract; (3) implement across the generic layer and every backend
together, keeping behaviour identical everywhere.

A hasty protocol change commits every backend to behaviour never surveyed;
backends drift as each "fixes" it differently. This is what repeatedly poisoned
the abandoned DDL-derivation work (`ddl_inline`, `inline_params`, string
sniffing, invented render helpers).

---

## 4. Deriving an expression class (every family)

This section governs when a backend may define an expression class of its own,
and what that class owes the core. It applies to `DataType`,
`SQLValueExpression`, `SQLPredicate`, DDL statements, sequence options alike.

### The line

> **Core first, respect the backend.** If core already expresses the concept
> completely, a backend does not define it again. Where core cannot serve a
> backend's need — a new parameter, a different storage, a word no core formatter
> can write — the backend derives from core and overrides the formatter.

One question decides whether a backend class belongs at all: **does it carry
something the core class does not?**

- Yes — a capability, a storage difference, a word only this server spells.
- No — it is a second name for something that already has one.

Decide on **capability or storage**, never on how two names sound. In PostgreSQL
`bytea` (variable-length, no format check) and `uuid` (fixed 128 bits,
validated, own operators) are separate types; size and "both look binary" say
nothing. Read the storage off the server, not the name.

### Derive, or own it outright

Once the answer is "yes, it carries something", there are two different places
that something can live, and they are not interchangeable.

**Derive from core** when the concept has a core counterpart and this backend
needs more of it — a new parameter, a different storage for the same idea, a word
this server writes. The backend subclasses the core class, adds only what core
lacks, and overrides the formatter. `MySQLIntType` is a core `IntegerType` plus
`zerofill`; `ClickHouseDateTimeType` is a core `TimestampType` rendered this
server's way. See the four shapes below.

**Own it outright, under the backend's own name** when the concept exists in
**neither the SQL standard nor any sibling backend** — it is this server's alone.
PostgreSQL has no peers for `citext`, `ltree`, `hstore`, `int4range`, `inet`,
`geometry` or `pg_lsn`, so those are defined in `impl/postgres` and nowhere else,
each carrying the `postgres_` prefix. There is no core base to derive from,
because there is no core concept to be a specialisation of; the core may supply
at most an empty marker base if one is needed for dispatch.

The test that separates the two: **ask whether a core class already names the
concept.** If it does, derive — even a large departure stays a derivation
(`FirebirdInt128Type` is an integer, so it derives from a core integer class
rather than standing alone). If nothing in core names it, own it. What never
justifies owning it is a difference in *spelling* or *size*; those belong to the
core class as a `spelling` or a parameter, not to a second class under a new
name.

### Protocol A — a core formatter does not reject a derived class

A core formatter's annotation takes the **core base class** —
`format_data_type_integer(self, data_type: IntegerType)` — and reads attributes.
A derived instance passes straight through; there is no exact-class check.

Two consequences, both load-bearing:

1. **A derived class that adds a field must bring its own formatter.** The core
   one cannot read what it does not know: a derived `zerofill` handed to the core
   formatter renders happily and the new parameter vanishes. Silent loss is the
   failure mode, not an error.
2. **The dispatch entry point keeps families apart.** `format_data_type()` routes
   on `data_type.name`, and `__init_subclass__` forces every derived class to
   carry a backend-prefixed `name`. A derived class therefore needs a
   `format_data_type_<its own name>`; a core formatter is never asked to render a
   foreign subclass by accident.

### Protocol B — a derived class does not rewrite the core signature

The parameter list is a contract shared with every formatter that accepts the
base class. Adding is fine; changing it is not, because a core formatter may
still be handed the instance.

| Move | Verdict | Example |
|---|---|---|
| Add a parameter, keep every core parameter | Correct | `MySQLIntType` adds `zerofill`; `MariaDBEnumType` adds `charset`, `collation` |
| Narrow the signature **and** narrow the identity together | Correct | `SQLServerTinyIntType` pins `unsigned=True`, still in `PARAMETERS`, so `==` still separates signed from unsigned; `MariaDBIntType` drops `spelling` because this backend writes one word for that width |
| Narrow the signature but leave the field in `PARAMETERS` | **Broken** | equality reads a field the constructor cannot supply |

The judgement is not "did the signature change" but **"do the signature and the
identity agree"**. Both may narrow; only one narrowing alone is a defect.

### The four shapes, on `DataType`

`spelling` is one parameter that appears only in the `DataType` family; it is the
answer to the fourth shape, not part of the two protocols above.

1. **A pure second name — do not derive.** No new capability, a prefixed `name`,
   and a formatter producing the same SQL as core's. `parse_type` then returns
   the core class, and since `__eq__` is class-exact the declaration and the
   catalog row read back from it are unequal — the schema differ invents a
   change. Measured: `PostgresByteaType`, `PostgresUUIDType`, `PostgresXMLType`,
   eleven Snowflake classes, four Firebird classes.
   The control case shows the judgement: `SQLServerUniqueIdentifierType` is
   **correct** because that backend does not implement core's
   `format_data_type_uuid`, so the substitute is its only entry point. The test
   is "can a core formatter write this word", never "does a same-named class
   exist".
2. **A new parameter — the healthy derivation.** Add what core lacks, override
   the formatter. Core-first working as intended.
3. **A real storage difference — derive, and say so.** `RAW(n)` bounded and in
   the row versus `BLOB` unbounded behind a locator; a SERIAL family that is a
   DDL declaration in its own right; an integer wider than anything core has.
   State the storage difference in the docstring — the reason must survive being
   read by the next person, because a docstring that justifies the class with the
   wrong argument invites its deletion. `OracleNVarChar2Type` is kept because no
   core formatter writes `NVARCHAR2(n)`, not because "the charset is a field".
4. **A synonym — one class plus a spelling.** Same storage, different word.
   `SPELLINGS` lists them, `spelling` selects, the formatter honours or refuses
   by name and never silently drops it. The list is the **union across
   dialects**, not one dialect's vocabulary. Two ways to get this wrong: splitting
   a synonym into several classes (shape 1), and accepting a `spelling` the
   formatter then ignores — a silent drop is more dangerous, being invisible
   where a second class is at least visible.

### One decision, across backends

Two backends must not give opposite answers to the same situation. Resolve it
with the line above: the question is whether the class carries capability core
lacks. `zerofill`, citext's case-insensitive operators, a wider integer — keep. A
second spelling of the same key with a backend prefix — delete.

### Two guards, written once

Both belong in the shared testsuite, not in nine backends:

1. **A formatter that receives a core parameter either honours it or refuses it
   by name.**
2. **A parameter absent from a derived `__init__` is absent from its identity.**

### Checklist, for adding a backend class

- [ ] Can core express this completely? If yes, do not derive; if only the word
      differs, use the family's synonym mechanism.
- [ ] If it needs something core lacks: **does a core class already name the
      concept?** If yes, derive from it and add only what is missing. If the
      concept is this server's alone, own it outright under the backend name.
- [ ] If derived, what does it carry that core lacks? Write it in the docstring.
- [ ] The expression **collects only** — no `raise` in its `__init__`. Whatever a
      dialect must accept or refuse (a spelling, an `unsigned`, a length) is
      checked in the `format_*()`, which is the only place that knows the backend.
- [ ] Core parameters: added only, never rewritten; if narrowed, identity narrows
      with them.
- [ ] It has its own formatter and handles inherited parameters honestly — honour
      or refuse, never drop.
- [ ] `name` carries the backend prefix, and parsing returns **this** subclass.
- [ ] The class names its **own** `format_*()` — one-to-one with the
      expression. If another expression already renders this, that difference
      belongs to that class (a `spelling`, a parameter, a storage fact).

---

## 5. Protocol / mixin architecture

- **Protocols** (`protocols.py`): the interface contract — what a dialect must
  implement. Never executed.
- **Mixins** (`mixins.py`): default SQL-standard implementations dialects can
  override.
- Every dialect inherits `SQLDialectBase` + relevant Mixins + relevant Protocols.

### Adding a new protocol

```python
# 1. main package protocols.py
@runtime_checkable
class NewFeatureSupport(Protocol):
    def supports_new_feature(self) -> bool: ...
    def format_new_feature_statement(self, expr): ...

# 2. main package mixins.py — generic implementation; the supports_* default
#    must represent the COMMON behaviour across databases
class NewFeatureMixin:
    def supports_new_feature(self): return False
    def format_new_feature_statement(self, expr): ...

# 3. concrete dialects: compose the pair; override ONLY what genuinely differs

# 4. dummy dialect: compose both and override supports_* to True only where the
#    generic default is not already True

# 5. tests: tests/.../dummy2/test_new_feature.py (expression),
#    tests/.../dummy/test_dummy_protocol_support.py (protocol support)
```

### Main-package protocol/mixin pairs

`WindowFunction`, `CTE`, `AdvancedGrouping`, `Returning`, `Upsert`, `LateralJoin`,
`Array`, `JSON`, `Explain`, `FilterClause`, `OrderedSetAggregation`, `Merge`,
`TemporalTable`, `QualifyClause`, `Locking`, `Graph`, `Join`, `SetOperation`,
`ILike`, `Table`, `View`, `Truncate`, `Schema`, `Index`, `Sequence`, `Trigger`,
`Function` — each as `XxxSupport` (protocol) + `XxxMixin` (implementation).

---

## 6. The Dummy dialect: generic reference and test vehicle

`backend/impl/dummy/dialect.py` (`DummyDialect`) is the SQL-standard reference
dialect and the vehicle for testing everything that does not need a live
connection.

- **Scope — compose (almost) everything:** every generic `XxxSupport`/`XxxMixin`
  pair, so each protocol's path is reachable without a database. Only genuinely
  server-bound capabilities are excluded (introspection composes but its
  `supports_*()` return `False`; backend-specific types are not modelled).
- **Behaviour — switches fully on:** every feature-detection method returns
  `True`, inherited or overridden. Dummy is a reference switchboard, not a
  simulation.
- **Enforcement:** `tests/.../dummy/test_dummy_protocol_member_completeness.py`
  discovers every Protocol in `protocols.py` and fails unless `DummyDialect`
  composes it and implements all members.

**Test organization.** `tests/.../feature/backend/dummy/` covers the protocol
surface (every `supports_*()` `True`, member completeness); `tests/.../feature/
backend/dummy2/` covers expression `to_sql()` generation through Dummy's
standard formatting. Extending both is part of the definition of done.

---

## 7. Backend boundary

**ActiveRecord is the user of the backend; the backend never knows ActiveRecord
exists.** The dialect/expression layer describes generic SQL and the concrete
capabilities of the target database — never a servant to the ActiveRecord layer
above it. ActiveRecord adapts to the backend; if it needs a feature requiring
backend cooperation, the feature is negotiated as a protocol on the backend's own
generic terms, never by bending the backend's design.

**Forbidden:** ActiveRecord-serving helpers on the dialect (`ddl_inline`,
`inline_params`, parameter-inlining machinery whose only purpose is an
ActiveRecord DDL feature); making the dialect infer intent from string
characteristics (regex, prefix/suffix checks, statement sniffing).

## 8. Verification

- Rendering is not validation. `(end - start) * 1` renders happily on a dialect
  that cannot execute it. Test against a real database.
- Semantic expectations come from the server, not intuition.
- A byte-identical SQL diff before and after is the evidence a refactor changed
  nothing. Capture it first, then compare.
- Run the whole check the change needs. Full suites are not run locally;
  targeted files, `--collect-only`, and lint are.
- A refusal is not a failure. `UnsupportedFeatureError: requires PostgreSQL 14+`
  is the code working: the dialect declined to render a type the server lacks. The
  test should ask the dialect what the server supports and skip.
- A check that was not run cannot have passed. Run the directory, not just the
  files you edited.

## Why this matters

Backend-agnostic expressions, injection-safe rendering centralised in the
dialect, a new backend reduced to a new dialect, and structure testable without
a database.


