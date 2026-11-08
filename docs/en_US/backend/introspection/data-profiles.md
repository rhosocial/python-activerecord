# Column Data Profiles

The introspection described in [Database Introspection](../introspection.md) reads
the schema catalogue: it reports what a database says its objects are. The three
methods on this page go one step further and ask what a column actually holds.

DDL is a promise: a type, a nullability, sometimes a default. The rows are the
reality, and the disagreements are the signal: a `NOT NULL` column containing
nulls, a `TEXT` column whose values are all numbers, a table with no declared key
whose one column is unique on every row.

## Three Questions, Kept Apart

| Method | The question |
|--------|--------------|
| `list_column_data_profiles(table_name, schema=None)` | What each column of this table holds: nulls, cardinality, extremes, and over how many rows |
| `sample_column_values(table_name, column_name, limit=100, schema=None)` | Which values occur in this column, and how heavily |
| `estimate_join_coverage(left_table, left_column, right_table, right_column, schema=None)` | How much of one column's value domain appears in another's |

Three calls rather than one, because their costs differ by orders of magnitude. A
value listing costs a pass over one column; join coverage costs a pass over two
columns in two tables; the profile is the cheapest as a rule, though how cheap
depends on where its figures came from, which `source` reports. Mixed into one
method, every caller would pay for the parts it did not ask for, and the cheapest
question, asked of every table, would pay most often.

## ColumnDataProfile

The declared shape, matching the class the library ships:

```python
from dataclasses import dataclass, field
from typing import Any, Dict, Optional
from rhosocial.activerecord.backend.introspection.types import ProfileSource


@dataclass
class ColumnDataProfile:
    schema: Optional[str] = None
    table_name: str = ""
    column_name: str = ""
    null_fraction: Optional[float] = None    # share of rows holding NULL, 0.0 .. 1.0
    distinct_count: Optional[int] = None     # distinct non-null values
    min_value: Optional[Any] = None          # the driver's own Python value
    max_value: Optional[Any] = None
    row_count: Optional[int] = None          # rows the figures were computed over
    source: Optional[ProfileSource] = None   # where the figures came from
    collected_at: Optional[str] = None       # as the collecting engine spells it
    extra: Dict[str, Any] = field(default_factory=dict)
```

The address slots carry the table and column a profile is about; `extra` carries
whatever the backend's own probe reports beyond the common slots, and its keys and
meaning belong to that backend.

### None Means Not Measured

Every slot may be `None`, and `None` means not measured, never zero: a backend that
does not keep a figure says so rather than reporting a zero it never counted.

Zero is a real answer on both numeric slots. A `null_fraction` of `0.0` says the
column holds no nulls; a `distinct_count` of `0` says it holds nothing else. A
`None` says neither, so code that reads it as `0.0` concludes a column has no
nulls when nobody ever looked.

### min_value and max_value Are the Driver's Values

They are `Any` because they are the values the driver returned, not strings: for a
text column the maximum is the lexicographic one, for a timestamp a datetime, for
an integer an int. Converting either to text would force every consumer to parse
back what it already had and would lose the ordering the value carries.

What "smallest" means therefore depends on the declared type, which the profile
does not repeat: read the extremes beside the column listing, where
`IntrospectionColumnInfo.data_type` (or `parsed_data_type`) says which comparison
produced them. Two profiles of different types are not comparing the same
quantity, even when both look numeric.

### row_count Is What Turns a Count into a Share

`distinct_count` says how many different non-null values exist; `row_count` says
over how many rows the count was taken. Together they give the ratio that
matters: a column whose distinct count equals its row count is unique on every
row, a candidate key the schema never declared.

What `row_count` counts depends on the source, which is why the two slots travel
together: the whole table for an aggregate, the sample size for a sample (the
ratio then estimates the whole), the collector's own row estimate for an estimate.

## ProfileSource

### A Number Without a Source Is Not a Fact

The same `null_fraction` can be a sampled estimate read from a statistics
catalogue or an exact count bought with a full scan, and both arrive as a float in
the same slot. A reader who cannot tell them apart is not reading `0.3`: is that
"roughly a third of the rows, as of a statistics refresh nobody dated", or
"exactly thirty percent of three million rows, counted just now"? Both are useful,
they are not the same fact, and one may be months old. So the source travels with
the number, and without it the probe would hand back numbers of unknown kind and
invite comparisons that are arithmetically valid and meaningless, such as
averaging an estimate with an aggregate. That is why this slot is the load-bearing
part of the family; it describes one profile's figures as a group, not as a
per-slot flag.

### The Four Sources

`ESTIMATE` means the figures were read from a statistics catalogue the engine
maintains: cheap, one query rather than a pass over the rows, and possibly stale
because nothing recomputes it when the data changes. `AGGREGATE` means they were
computed from the rows when asked: exact over the rows the query saw, paid for in
time proportional to the table, and describing the data at the call.

`SAMPLE` means they were computed over a subset. `row_count` is the sample size,
and the fractions describe the whole only insofar as the sample represents it. A
sample says what was sampled; it does not promise a sampling method, and a reader
who needs one should not infer it from the numbers.

`UNKNOWN` means the engine answered but did not say how. That is a fact worth
recording: no provenance, rather than permission to assume exactness. The slot
being `None` is different again: the row carried no source at all, silence rather
than a stated refusal.

### ESTIMATE and collected_at Travel Together

An `ESTIMATE` carries `collected_at`, the moment the catalogue's figures describe:
a `null_fraction` from seven months ago and one from today are not the same fact.
It is text as the collecting engine spells it, and core does not normalise date
formats across engines. An `AGGREGATE` is as of the call, so the slot is not
required; a `SAMPLE` uses it to say when the sample was taken.

A profile whose source is `ESTIMATE` and whose `collected_at` is `None` still says
the figure is an estimate, but not of what moment; treat it as unusable for any
decision that depends on freshness.

Which source a backend reports for a given probe, and whether it answers the probe
at all, is that backend's own documentation to state; this page describes only
what the core contract means.

## ColumnValueFrequency

```python
@dataclass
class ColumnValueFrequency:
    value: Optional[Any] = None
    count: Optional[int] = None
    frequency: Optional[float] = None
    extra: Dict[str, Any] = field(default_factory=dict)
```

One value the column actually contains, with its weight. `count` is how many rows
held it, `frequency` its share of the rows. Both are optional because engines
report one or the other, and converting needs a row count the library does not
have: a caller holding the profile's `row_count` can divide, where a library that
divided would have had to guess the denominator.

A listing shorter than the requested `limit` is a correct answer, because `limit`
is an upper bound: an engine keeping a fixed-size most-frequent-values list
returns what it kept, and padding would invent values. `value` may legitimately be
`None`, since NULL is a member of the domain and often the most interesting one;
the "skip empty" rule that discards addressless rows elsewhere does not apply here.

## JoinCoverage

```python
@dataclass
class JoinCoverage:
    left_schema: Optional[str] = None
    left_table: str = ""
    left_column: str = ""
    right_schema: Optional[str] = None
    right_table: str = ""
    right_column: str = ""
    left_coverage: Optional[float] = None    # share of left's distinct values found on the right
    right_coverage: Optional[float] = None   # share of right's distinct values found on the left
    extra: Dict[str, Any] = field(default_factory=dict)
```

This answers the question a consumer asks when no foreign key exists and two
columns still look joinable: `orders.customer_ref` and `customers.code` are both
there, but only the data can say whether they meet. The answer is two fractions,
each the share of one column's distinct non-null values that also occurs on the
other side.

### Both Sides, Because It Is Not Symmetric

Every order's customer may exist while most customers have never ordered: a
`left_coverage` of `1.0` beside a much lower `right_coverage`, both true at once.
One similarity score would have to choose a side and lose the other, and the two
support different conclusions: a high left fraction says a join from the left
finds a match for every left value; a low right fraction says the relation is
selective and most right values are never referenced.

### None Is Not 0.0

`0.0` is a measurement: the domains do not meet. `None` is the absence of a
measurement for that side, and the method's return has the same rule one level
up: `None` in place of a `JoinCoverage` means no measurement was produced, which
a caller must tell apart from measured zero overlap. `(0.0, 0.0)` says the
columns share nothing; `None` says nothing was learned.

### NULLs Are Excluded on Both Sides

NULL is the absence of a value, not a member of the value domain. Counting it
would make every nullable column overlap every other nullable column and would let
an order with no customer match something. Excluded from both sides, coverage
describes how the values that exist relate.

### Evidence, Not Proof

Both fractions are estimates: an engine may sample, and collations are not
reconciled, so two columns whose strings compare differently can report lower
overlap than the data would support under one collation.

A high fraction means the two value sets agree, not that one references the
other. Two columns can share a domain for an unrelated reason: a postal code on
an address and a depot, a year on an order and an invoice. Coverage makes a join
worth trying, not correct; the declaration, or the data's own behaviour, has to do
that.

## Using Them

```python
from rhosocial.activerecord.backend.impl.sqlite.backend import SQLiteBackend
from rhosocial.activerecord.backend.introspection.types import ProfileSource

backend = SQLiteBackend(database=":memory:")
backend.connect()
introspector = backend.introspector

# One call profiles every column of the table.
profiles = introspector.list_column_data_profiles("orders")

for profile in profiles:
    print(f"{profile.column_name}: nulls={profile.null_fraction}, "
          f"distinct={profile.distinct_count}, rows={profile.row_count}, "
          f"source={profile.source}")
    if profile.source is ProfileSource.ESTIMATE:
        print(f"  collected {profile.collected_at}")
```

The result is a list with one entry per column of the table, and the names come
from the same listing `list_columns` returns, so a column the backend could read
gets a profile even when nothing was measured about it. Its shape is the dataclass
above:

```python
# Every slot of one profile, as plain data.
print(profiles[0])
```

The other two are separate calls, made when they are wanted. On the async
introspector the same three methods are awaited under the same names.

```python
coverage = introspector.estimate_join_coverage(
    "orders", "customer_ref",
    "customers", "code",
)
if coverage is None:
    print("not measured")
else:
    print(f"orders -> customers: {coverage.left_coverage}")
    print(f"customers -> orders: {coverage.right_coverage}")
```

## What They Cost

The value listing and the overlap measurement are expensive, and the second is
the most expensive thing in the introspection system: it reads two columns in two
tables to compare their distinct domains, so it is a double scan. That is why it
lives behind an explicit call and why nothing triggers it implicitly: profiling a
table does not measure any join coverage, listing tables does not, and the schema
differ does not ask for it on the way past.

The profile's own price is the price of what its `source` reports: a figure from a
catalogue the engine already maintains is cheap, one aggregated from the rows is
not. All three answers are cached like every introspection result, keyed by the
table, column, limit and schema they were asked with; a different `limit` is a
different key and pays again. Every answer describes the data at the time it was
taken, so a cached profile can be older than the rows it describes.
