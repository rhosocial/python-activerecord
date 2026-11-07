# Constants: what a name in caps has to earn

A module-level name written in capitals is a claim: that the value is a fact
of the domain rather than a convenience of one call site, and that everyone
who reads it sees the same one. The claim is either true or it is decoration,
and decoration in caps reads as policy -- the next reader treats it as
settled and works around it instead of through it.

The justification is **being read in more than one place and having to stay
in step**. Nothing else earns the capital name: not the importance of the
value, not its length, not the wish to type a sentence once. A sentence a
function says once does not become a fact of the system because it was typed
in capitals; it becomes two things to keep in step, one of which nobody
reads.

## The decision

| Situation | What it takes |
|---|---|
| Read once | Inline it. Two exemptions only: a member of a closed value set, which takes an Enum, and a directory fact a test pins. |
| Read twice or more inside one function | A local variable, without the capital name. A name that outlives its function outlives the reader's ability to see its readers. |
| Read from more than one function, and the readings must agree | A module-level constant **and a test that pins it**. A value nobody asserts is text nobody guarantees. |
| Private `_CONST` | Stricter than public, never looser. The one legitimate private form is a table the same module reads in several places; a private name holding a single sentence is a way of not typing it twice. |

## Read once

`_AGGREGATE_PROFILE_NOTE` is the shape to recognise. Five repositories define
it -- SQL Server, MariaDB, Snowflake, MySQL and ClickHouse -- byte-identical,
each read at the two places its CLI prints it, and BigQuery writes the same
job as `_PROFILE_COST_NOTE` while Oracle splits it across `_VALUE_SAMPLE_NOTE`
and `_VALUE_SAMPLE_SOURCE`. Seven definitions of one sentence under three
names, with no test asserting any of them, because a note printed to stderr
is not a fact -- it is a sentence, and a sentence belongs where it is said.
The fix is inlining, or a function that returns the sentence when two call
sites genuinely want it. It is never an eighth copy.

The same shape is inside this repository, and the check at the end of this
rule names all of it. The clearest is in `impl/sqlite/dialect.py`, which
declares five diagnostic sentences -- `_SUGGESTION_JSON_TABLE`,
`_SUGGESTION_ARRAY_TYPES`, `_SUGGESTION_GRAPH_MATCH`, `_SUGGESTION_QUALIFY`
and `_SUGGESTION_ORDERED_SET_AGG` -- each read at the one place that raises
its diagnostic, and `impl/sqlite/mixins/ddl_view.py`, where
`_SUGGESTION_MATERIALIZED_VIEW` is read by both refusals that need it and
`_SUGGESTION_MATERIALIZED_VIEW_ALT`, defined on the next line holding the
same kind of sentence for the third refusal, is read once. Beside them,
`logging/defaults.py` declares seven logger names: `_LOGGER_QUERY` is read
three times and `_LOGGER_TRANSACTION` twice, while `_LOGGER_MODEL`,
`_LOGGER_BACKEND` and `_LOGGER_WORKER` are read once each and `_ROOT_LOGGER`
and `_LOGGER_CONNECTION` are read nowhere at all.

Run against this repository today, the check reports twenty-five names. They
are that shape: the six diagnostic sentences and three logger names above,
three single-reader CLI tables (`STATUS_TYPES`, `DIALECT_SPECIFIC_GROUPS`,
`PROTOCOL_FAMILY_GROUPS`), eleven tables and lists with one reader
(`MARKER_REGISTRY`, `PYDANTIC_FIELD_NOT_MAPPED`, `MULTI_WORD_TYPE_NAMES`,
`_FRAMEWORK_PACKAGES`, `SQLITE_RESERVED_WORDS`, `_SEEK_OPCODES`,
`_KNOWN_VTABLE_MODULES`, `SENSITIVE_FIELDS`, `_PARSE_CONCEPTS`,
`_PARSE_NUMERIC_PARAMS`, `ROOT`), one dotted-path format string that
`importlib` resolves at run time, and one `getattr` written as a constant.
Clearing them is a separate change; this rule and its check exist so the next
twenty-five do not arrive.

## A default is not a fact because two places wrote it down

`DEFAULT_VALUE_SAMPLE_LIMIT` is the same failure wearing a number. Five CLI
repositories define it as `100`, and this repository answers the same
question with `limit: int = 100` on four signatures -- the value-sample
statement, the sync statement factory, `sample_column_values` and its async
twin. Nine spellings of one default, with nothing keeping them in step:
change the introspector's default and five CLIs keep advertising the old one.
That is the textbook case for letting a signature answer, and for the help
text saying the default is the introspector's own rather than repeating it.

The same defect was once written out twice inside this repository under one
name: SQLite's pragma table was spelled in full in `backend/common.py` and
again as a `ClassVar` on `SQLitePragmaMixin` in `config.py`, with the two
backend classes aliased onto the first of them. No reference count could see
it, because every copy was read -- which is the limit of counting names. The
count asks whether a name is read; it cannot ask whether a value is one
thing. That question is the second check's, and it asks it wherever a value
claims a name: the default of a parameter answers the question that
parameter's name asks, and an assignment in capitals answers the question the
constant's name asks, so two places answering one name are two places that
must agree. A literal in neither position claims nothing, and repeating one
of those is as often an accident as a decision -- a `0.8` warn threshold and
the price of a banana in an example are not one fact written twice -- which
is why the second check reads the named sites and leaves the anonymous ones
alone.

## Read across functions

Here the constant is legitimate and the test is what makes it so.
`_TYPE_CAPABILITIES` earns its name: each backend's CLI reads it to resolve
the switch behind the type a caller asked for, and the tests walk it entry by
entry, so a type offered without a `supports_*` behind it fails the suite
rather than the server. `SNOWFLAKE_TABLE_TYPE_MAP` and `_RELKIND_LABELS` are
the other legitimate shape -- the engine's own catalogue vocabulary, read in
the places that answer a question about it. Snowflake reads its map from four
places and its table-types test walks every spelling and asserts the member
beside it. PostgreSQL's `_RELKIND_LABELS` is read once, in the CASE that
names a relation's kind, and that is the honest boundary of the exemption:
the five pairs it holds are what the parsing matrix asserts, so the facts are
pinned even though the name has one reader. There is no version of this rule
under which a table read in several places with its readings asserted should
be inlined.

## Private is stricter

A private name is not a public one with an underscore. It is a name the
module kept for itself, which means the only thing that can justify it is the
module's own need to read the same value in several places. `_TYPE_CAPABILITIES`
and `_NAME_RULE` pass that bar in this repository: the CLI resolves the switch
and the argument rule through them, and the tests walk both. A private name
holding one sentence, or one number, does not pass it -- the underscore was
supposed to limit the audience, not to lower the bar.

## What this adds to enum-first

`python-hazards.md` §11.3 already says a closed value set takes an Enum
rather than a string or a module-level tuple, frozenset or dict, and it
already grants the exemptions this rule inherits: compiled regexes and the
fragments composed into them, numeric defaults, and lazily built caches keyed
by classes. Its measured surface also settled the tables that are keyed by an
Enum member -- the alias tables beside `DateTimeField` and `IntervalUnit`,
and the arithmetic symbol table -- because a dict in an Enum body would be a
member rather than a lookup. It says nothing about a value that is read once
but is not a closed set, which is where the capitals were actually going. The
addition is the second reader: an Enum earns its members because the set is
closed, and a constant earns its name because a second place reads it and a
test pins the reading.

`ProfileSource` is the exhibit for the half that is already written down and
not followed. Core declares four members -- `ESTIMATE`, `AGGREGATE`, `SAMPLE`
and `UNKNOWN` -- and until this branch nothing constructed one: PostgreSQL
writes `source="estimate" if collected_at is not None else "unknown"`, MySQL
and MariaDB label their rows `"aggregate"` by hand, Oracle declares
`_VALUE_SAMPLE_SOURCE = "aggregate"`, and the sentence five CLIs print to
stderr carries `(source='aggregate')` in quotes. A closed set spelled as
strings and chosen by a branch is exactly what §11.3 forbids, and the cost is
not theoretical: a typo in one of those spellings is a value nothing
validates. `ProfileSource` is a `str` Enum, so tightening the slot costs the
existing consumers nothing and buys a checker that can name the members.

## Across repositories: same name, same shape, same meaning

The rule applies to the whole `feature/introspection-enhancement` family, and
one name means one thing across it. Same name, same shape, same meaning:
`_NAME_RULE` is spelled that way in this repository, MariaDB, MySQL and
ClickHouse, and `_NAME_RULES` in SQL Server and Oracle; `INTROSPECT_TYPES` is
a `list` in nine repositories -- every one of the ten except BigQuery -- while
BigQuery spells the same idea `INTROSPECT_SUBCOMMANDS` as a `tuple`. Both are
copies of one decision that drifted, and both are invisible from inside any
single repository.

This extends §4 and §5 of `introspection.md` rather than adding a constraint
beside them. §4 gives each backend its own type list and states that core does
not arbitrate it, which is what makes the spellings independent in the first
place; §5 decides ownership by divergence and forbids folding a family into
`extra`, and its closing paragraph keeps the MySQL and MariaDB twins as twins
with the CHANGELOG annotating the other side. Same-name-same-shape is the
discipline that keeps per-backend ownership from becoming per-backend drift.
It is explicitly **not** a licence to extract a shared module: the copies stay
where the engines put them, and a unification is only ever chosen when the two
sides have stopped diverging. Copying is allowed. Deforming is not.

## The check

`tests/rhosocial/activerecord_test/feature/rules/test_constant_discipline.py`
implements the mechanical half. It parses every module under `src/`, collects
each module-level all-caps assignment, counts the loads of that name across
`src/` and `tests/`, and fails listing every name with exactly one load that
is not inside a test assertion. It applies the §11.3 exemptions above so it
does not re-litigate what that rule already settled, and it treats an
``import`` as plumbing rather than a read -- importing a name nobody reads is
the defect, not the exoneration.

An import is also why the check asks for exactly one load and not one or
none: a name nobody loads is the "never referenced" case, which the rule
settles as a deletion and which is a different finding from "one reader".

The same file holds the second check, which is the count's blind spot. It
parses `src/` alone, collects every literal that claims a name -- a parameter
default, or the value of a constant at module or class level -- and fails
listing every value one name answers in two or more places. A table counts as
one value, so a catalogue's entries are its contents rather than numbers
anybody wrote on their own; an Enum member is exempt, because a closed set
takes an Enum and two enums agreeing on a member are agreeing rather than
duplicating; and a literal claiming no name is not read, for the reason in
the section above. It reports both sites with the kind of each -- a parameter
default against a constant -- because the value alone, `100` written a
hundred times, is not something anyone can act on.

Run against this repository today the first check reports nothing and the
second reports twenty-one values, every one of them the shape above:
`limit` defaulting to `100` on four signatures, `batch_size` to `100` and
`page_size` to `1000` on the sync and async twins each, `wal_checkpoint`'s
`mode` to `PASSIVE` twice, `PARAMETERS = ("unsigned",)` on six classes and
`KIND_RESERVED = ("SQLite",)` on five, `OUTPUT_CHOICES` written three times
across the SQLite CLIs, and the example registries' `META` three times.
Clearing them is a separate change; the check stays red until it is done,
which is the point.

Three things the pair of them cannot see, each a limit of the rule as much as
of the code. They see this repository alone, so the cross-repository clause
above is unenforced here -- that check belongs in
`python-activerecord-testsuite`, which is the only layer that can hold all
ten. They see the AST alone, so a reader that is a `getattr`, a name in a
config file, a script or a document is invisible to them. And the second asks
whether two places answer the *same name*: `limit` written four times is
caught, `limit` here and `max_rows` there is the same defect and no AST says
so. The rule is worth exactly as much as the check behind it: a criterion
nobody runs is a preference, and this one was written after a survey of 665
constants across ten repositories found the capitals accumulating in the
branches nobody was reading.
