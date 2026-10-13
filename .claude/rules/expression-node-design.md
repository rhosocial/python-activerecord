# Expression node design: when a construct is a clause and when it is a parameter

## The question this answers

Two things that look alike in a grammar diagram get modelled differently: one
becomes a node with its own formatter, the other becomes a parameter. Guessing
wrong is expensive in both directions — too coarse and every dialect grows a
special case; too fine and the core carries fields nine backends cannot use.

The test is mechanical. Apply it to each production, recursively.

Worked reference throughout: SQLite's
[`column-def`](https://sqlite.org/syntax/column-def.html),
[`column-constraint`](https://sqlite.org/syntax/column-constraint.html),
[`table-constraint`](https://sqlite.org/syntax/table-constraint.html), and the
[`WITH` clause](https://sqlite.org/lang_with.html).

SQLite's syntax pages carry a `References:` field listing the sub-productions
each production actually depends on. That is the evidence for B1, and it is
worth reading before modelling anything.

## A. One expression, one formatter

| # | Rule |
|---|---|
| **A1** | Every expression has exactly one formatter. |
| **A2** | That formatter handles that expression **and its subclasses only**. No `Any`, no union, no "may also be a subclass of something else". |
| **A3** | The signature is exactly `(self, expr)`. `expr` is annotated with that expression's own class. No extra parameters — a helper needs a context is a sign the state belongs on an expression that does not exist yet. |
| **A4** | The return is `Tuple[str, tuple]`. A formatter returning bare `str` is doing half a job and forces every caller to re-wrap. |
| **A5** | Dialect formatters are public. A `_format_*` helper in a dialect mixin is a design mistake, not a visibility choice. |
| **A6** | Logic shared across expressions is **not** a formatter. Drop the `format_` prefix; it claims a 1:1 pairing it does not have. |
| **A7** | A formatter lives in the same protocol as its capability switches, and protocols are grouped by feature group — one protocol per constraint level, one per alter-action family, one for the index seam. |

A3 and A4 are what make A1 checkable. Measured:

| Function | A1 | A2 | A3 | A4 | Disposition |
|---|---|---|---|---|---|
| `_format_constraint_enforcement(constraint: Any) -> str` | ✗ | ✗ | ✗ | ✗ | **delete**; enforcement is a production-level trait, rendered by the branch's own formatter |
| `_format_constraint_validation(constraint: Any) -> str` | ✗ | ✗ | ✗ | ✗ | **delete**, same |
| `_format_ddl_check_predicate(predicate: Any) -> str` | ✗ | ✗ | ✗ | ✗ | **delete**; the predicate belongs to the check branch |
| `_format_with_clause(ctes_sql: List[str], has_recursive: bool) -> str` | ✗ | ✗ | ✗ | ✗ | **delete**; no `WithExpression` node exists, which is the actual defect |
| `_format_in_value_list(expr: InPredicate, expr_sql, expr_params, literal)` | ✗ | ~ | ✗ | ✓ | **inline into `format_in_predicate`, then delete** — `expr` was correctly typed; the other three parameters are what disqualify it |
| `_format_xml_passing_clause(expressions: List[BaseExpression], mechanism)` | ✗ | ✗ | ✗ | ✓ | **introduce `PassingClause`**, then rename to `format_passing_clause` |

The last row is the pattern for A3's failure mode: three XML expression classes
(`XMLQueryExpression`, `XMLExistsPredicate`, `XMLTableExpression`) hold the
identical pair `passing` + `passing_mechanism`, and no expression owns that
clause. The shared state has no home, so the formatter takes unpacked pieces.
`PASSING [ BY { VALUE | REF } ] { expr [ AS ident ] } [, ...]` is a named
production — by B1 it should already be a node.

The same shape appears as the split state of `format_column_fk_constraint`, which
takes the fat union and re-dispatches on `constraint_type` — the reason A1 was
violated in the first place.

A2 is why a formatter may not take `Any`. If the same helper has to serve a
column constraint and a table constraint, the shared data is on the wrong node.

A3, measured: `_format_constraint_enforcement(constraint: Any)` served both
`ColumnConstraint` and `TableConstraint`, and
`_format_with_clause(ctes_sql: List[str], has_recursive: bool)` took already
rendered SQL strings — so it corresponded to no expression, and no backend could
override it. Both were private.

## B. Node or parameter

| # | Rule | Evidence |
|---|---|---|
| **B1** | A named production, a complex subgraph, or anything the diagram marks `expr`, is a **node**. | `column-constraint References: conflict-clause, expr, foreign-key-clause, literal-value, signed-number` — 7 of its 9 branches carry a sub-production. Only `CONSTRAINT name` and `COLLATE collation-name` are bare. |
| **B2** | A **cycle** must be collapsed into one node, or it cannot be expressed at all. | `select-stmt` contains `common-table-expression`, which contains `select-stmt`. The recursion has to pass through the CTE node; flattened siblings have no way to point back at "my own item". |
| **B3** | Divergent **mandatory** paths are different variants, not a boolean. **Before calling them divergent, check whether one path is a superset of the others** — if it is, there is no divergence and they collapse to it. | See `DEFAULT` below. |
| **B4** | Parentheses are **syntax**. They are emitted by the formatter; they never enter the model. No `parenthesized: bool`. | |

B1 makes "is it a node?" answerable without taste. `PRIMARY KEY [conflict-clause]`
is a node because it carries `conflict-clause`, not because it is long.

## C. Count paths, not the nodes on a path

**Ask first whether what follows is a switch or a payload.** The two answer
different questions, and counting paths only applies to one of them.

| | Switch | Payload |
|---|---|---|
| Path shape | **several optional** paths | **one mandatory** slot |
| Each path is | a boolean state | a value |
| Parameters | **one per path** (C1) | **one**, whose type drives rendering |
| Example | `[ASC\|DESC]`, `[NOT] MATERIALIZED` | the parenthesised body of `DEFAULT` |

So `DEFAULT ( expr ) | literal-value | signed-number` is **one parameter**,
not three: the alternatives are payloads, not switches. `[ASC|DESC]` is
**two**, because those are optional switch paths.

A payload is unified as an expression. The caller wraps a literal:
`DEFAULT 'abc'` and `DEFAULT -1` become `Literal(...)` and render as
`DEFAULT ('abc')` and `DEFAULT (-1)`.

| # | Rule | Evidence |
|---|---|---|
| **C1** | **The number of parameters is the number of paths.** Never the number of keywords. | |
| **C2** | Several keywords on one path are **one** parameter. | `CREATE TABLE IF NOT EXISTS …` — three keywords, one path, one parameter: `if_not_exists: bool = False`. |
| **C3** | **Mutually exclusive** paths at one position get one parameter each, and the **formatter validates** the exclusion. | `TEMP` / `TEMPORARY` are two paths, so two parameters — even though they are synonyms. Mechanically counting is the rule; collapsing synonyms is not. |

Measured on SQLite 3.50.4, which is what collapses `DEFAULT`:

```
DEFAULT 'abc'     ->  OK        DEFAULT ('abc')   ->  OK
DEFAULT 1+2       ->  REJECT    DEFAULT (1+2)     ->  OK
DEFAULT -1        ->  OK        DEFAULT (-1)      ->  OK
```

`( expr )` is a **superset** of the other two paths, so there is no divergence
to model (B3).

C1 applied to what already exists, all of which stay as they are:

| Construct | Paths | Parameters |
|---|---|---|
| `AS [NOT] MATERIALIZED ( select-stmt )` | 2 | `materialized` / `not_materialized` |
| `[NOT] DEFERRABLE` | 2 | `deferrable` / `not_deferrable` |
| `INITIALLY { DEFERRED \| IMMEDIATE }` | 2 | `initially_deferred` / `initially_immediate` |
| `[ ENFORCED \| NOT ENFORCED ]` | 2 | `enforced` / `not_enforced` |
| `PRIMARY KEY [ASC\|DESC] [conflict-clause] [AUTOINCREMENT]` | 2 + 1 + 1 | `asc` / `desc`, `conflict`, `auto_increment` |

C3 is not optional. Measured on `_format_constraint_enforcement`, whose last
line was `return "ENFORCED" if enforced else "NOT ENFORCED"`:

```
constructor, both flags set  ->  ValueError            (constructor guard holds)
flag injected afterwards     ->  ' CHECK (0 < "age") ENFORCED'
                                                     ^ not_enforced silently dropped
```

The constructor guard does not cover deserialisation, a backend subclass, or
attribute injection. Every mutually exclusive pair needs the formatter to check
again as the last line of defence.

## D. Parameter shape

| # | Category | Form | Why |
|---|---|---|---|
| **D1** | Mandatory object | Required parameter, no default | Absence is a syntax error. `column-name` cannot be omitted. |
| **D2** | Optional object | **`Optional[X] = None`** | Absence is legal and there is **no natural default object**. |
| **D3** | Switch | Default value, **never `Optional`** | "Off" *is* the default behaviour, so there is something to default to. |
| **D4** | Optional list | **`= ()`**, never `Optional` | The empty collection already means "none". |

D2 exists because of D3's opposite. Measured on SQLite 3.50.4:

```
CREATE TABLE t1(x)          ->  OK,  pragma type = ''        <- no type at all
CREATE TABLE t2(x INTEGER)  ->  OK,  pragma type = 'INTEGER'
CREATE TABLE t4()           ->  syntax error                <- column-name cannot go
```

A missing type reports as the empty string, not as some sentinel type. A
defaulted `DataType` would therefore state something false. This is the one
place `Optional` is correct in an expression constructor, and it is not the same
thing as a switch.

## E. Layering and naming

| # | Rule |
|---|---|
| **E1** | A grammar production that is itself a clause is a **directly formattable node**. It carries whatever the grammar hangs on the production rather than on a branch. |
| **E2** | Each parallel path is that node's **branch**, with its own formatter. |
| **E3** | Prefix by the nature of the **owning parent node**: column → `Column*`, table → `Table*`, domain → `Domain*`. |
| **E4** | E3 extends to enum field types. An enum used at one level takes that prefix; one shared across levels takes none. |

E1 is why `ColumnConstraint` must not be an abstract base. `column-constraint`
is a clause, so it is formattable. The `Column*Constraint` nodes are its branch
parameters, not its subclasses.

The grammar decides where the shared data goes. Every backend that spells a
naming prefix puts it on the **production**, not on the branch:

```
PostgreSQL  column_constraint ::= [ CONSTRAINT constraint_name ] { …branches… }
                                    [ DEFERRABLE | NOT DEFERRABLE ] [ INITIALLY … ] [ ENFORCED | NOT ENFORCED ]
Oracle      inline_constraint  ::= [ CONSTRAINT constraint_name ] { …branches… } [ constraint_state ]
Snowflake   inlineUniquePK    ::= [ CONSTRAINT <name> ] { UNIQUE | PRIMARY KEY } [ <constraint_properties> ]
```

So `name` and the trailing traits live on `ColumnConstraint`, and each branch
carries only what is specific to it. Two levels is not a convenience — it is
where the grammar puts the data. It also removes the `Any` in A2: the shared
traits are rendered in exactly two places, `format_column_constraint` and
`format_table_constraint`, each with one concrete type.

### Layout

```
ColumnDefinition(name, data_type: Optional[…], constraints: List[ColumnConstraint], attributes: List[ColumnClause])

ColumnConstraint(dialect, *, branch,                 # <- the column-constraint clause
                 name = "", deferrable = False, not_deferrable = False,
                 initially_deferred = False, initially_immediate = False,
                 enforced = False, not_enforced = False)
    format_method -> "format_column_constraint"

ColumnConstraintBranch                                     # abstract, never instantiated
  ├─ ColumnPrimaryKeyConstraint      (asc, desc, conflict, auto_increment)
  ├─ ColumnUniqueConstraint          (conflict)
  ├─ ColumnNotNullConstraint         (conflict, no_inherit)
  ├─ ColumnNullableConstraint        ()
  ├─ ColumnCheckConstraint           (condition)          # mandatory
  ├─ ColumnDefaultConstraint         (value)              # mandatory; literal wrapped as Literal
  ├─ ColumnForeignKeyConstraint      (references)          # mandatory
  └─ ColumnGeneratedConstraint       (expression, stored, virtual)
```

Rendering walks the production, then dispatches to the branch:

```
format_column_definition
  └─ format_column_constraint(c)                       # once per column-constraint
       ├─ [CONSTRAINT name]                            # production level
       ├─ getattr(dialect, c.branch.format_method)(c.branch)
       └─ [DEFERRABLE…] [INITIALLY…] [ENFORCED…]        # production level, probe-gated
```

### A backend-only field stays in the backend

`PRIMARY KEY [ASC|DESC]` exists in exactly one of the ten backends. The core
`ColumnPrimaryKeyConstraint` carries `asc` / `desc` / `conflict` /
`auto_increment`; SQLite derives `SQLitePrimaryKeyConstraint` and adds what
only it has. "Accommodating the backend" means the core provides an extension
point that a backend can extend — not that the core grows a field nine backends
cannot use.

## Catalogue: what this replaced

| Anti-pattern | Why it was wrong |
|---|---|
| One `ColumnConstraint` class with a `ColumnConstraintType` tag and sixteen parameters | A fat tagged union. Required for `CHECK`, meaningless for `PRIMARY KEY`, and the docstring admitted it: "requesting them on one is accepted and simply never rendered". |
| `TableConstraint` shaped the same way | Same, plus `Any`-typed private formatters serving both families. |
| `is_auto_increment` on the core `ColumnConstraint` | A single-backend field on a shared node, silently dropped by backends that could not render it. |
| `format_column_constraint` dispatching on `constraint_type` | A1: one formatter, seven expressions. |
| `_format_constraint_enforcement(constraint: Any)` | A2 and A3. |
| `_format_with_clause(ctes_sql: List[str], …)` | Corresponded to no expression; took rendered strings, so no backend could override it. |
| `Optional[bool]` for switches | D3. |
| `Optional[List[X]] = None` then `list(x or [])` | D4. `None` and `[]` are the same thing here. |
