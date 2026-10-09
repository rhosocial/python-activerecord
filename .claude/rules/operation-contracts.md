# Operation contracts

The capability declaration baseline for the ten-backend operation survey
(`.claude/plan/2026-10-09/operation-groups-matrix.md`, sections A-F; measured
2026-10-09, per-backend records and probe outputs in the same directory and
its `backends/`). This file is the document the core factory docstrings and
the backend rendering overrides implement; when a new measurement disagrees
with it, this file changes first and the code follows.

## 1. String boundary contracts

Every one of these was measured on ten backends before it was written down.
Where the backends agree, the edge renders; where they do not, it is refused at
construction rather than rendered into whatever the dialect happens to do.

| Operation | Contract | What was measured, and why the other edges are not offered |
|---|---|---|
| `left` / `right` | `n >= 0` | 0 is `''` and `n > len` is the whole string on every backend. Below 0: PostgreSQL and ClickHouse drop the trailing/leading `\|n\|` characters, MySQL, MariaDB and Snowflake return `''`, SQL Server and Firebird raise, BigQuery raises, Oracle (via SUBSTR) yields NULL. |
| `repeat` | `n >= 0`; `n < 0` is `''` | The native answer on PostgreSQL, MySQL, MariaDB and ClickHouse alike. SQL Server's REPLICATE answers NULL; Oracle, Firebird and SQLite have no such function. Settled once, in the core, instead of once per backend. |
| `lpad` / `rpad` | `n >= 0`, pad non-empty, omitted pad means one space and is spelled out | The pad is passed explicitly because MySQL raises 1582 without it while MariaDB fills with spaces. Empty pad: untouched string on PostgreSQL/Firebird/Snowflake, `''` on MySQL 8.0, untouched on MySQL 26 (same server, two answers), NULL on MariaDB/Oracle, spaces on ClickHouse. |
| `substring` | `start >= 1`, `length >= 0` | Out-of-range positions: consumed by the length on PostgreSQL/SQL Server/Firebird/SQLite, empty string on MySQL/MariaDB/ClickHouse, read as 1 on Oracle. Negative length: an error on PostgreSQL/SQL Server/Firebird/BigQuery, `''` on MySQL/MariaDB, NULL on Oracle, something unrelated on ClickHouse. |
| `trim` | trim set is exactly **one** character | SQL:2016 feature E021-09. A longer set is a character set on PostgreSQL/SQL Server/ClickHouse/Snowflake, a whole string repeated on MySQL/MariaDB/Firebird (proved with `TRIM(BOTH 'xy' FROM 'xyxab')` = `'xab'`), and ORA-30001 on Oracle. |

## 2. Rendering-name contracts

The core name is the meaning; the rendered spelling is the backend's. A dialect
override renames or reorders, never reinterprets.

| Core call | Core meaning | Per-backend spelling (measured 2026-10-09) |
|---|---|---|
| `log(x)` | natural logarithm | native on MySQL, MariaDB, ClickHouse, SQL Server, BigQuery, Firebird, SQLite; `LN(x)` needed on PostgreSQL (where `log(x)` is base 10) and Oracle and Snowflake |
| `log(x, base)` | base second | native order on SQL Server, ClickHouse, BigQuery; `(base, x)` order on PostgreSQL, MySQL, MariaDB, Oracle, Firebird, Snowflake |
| `truncate(x[, n])` | truncation toward zero, distinct from `round` on negatives | `TRUNC` on PostgreSQL, Oracle, Firebird, BigQuery, SQLite, ClickHouse; `TRUNCATE` on MySQL, MariaDB, Snowflake; SQL Server has no scalar truncate and spells it `ROUND(x, n, 1)`. MariaDB's own `TRUNC` returns NULL for numerics (12.2+, absent before), so its gate keys on the rendered name |
| `position(substring, expr)` / `strpos(expr, substring)` | two spellings, one operation, needle-first for `position` and haystack-first for `strpos`, each matching the standard/native form | PostgreSQL takes only `POSITION(sub IN s)` (its comma form is a syntax error); SQL Server `CHARINDEX`; ClickHouse and BigQuery put the haystack first; MySQL/MariaDB `LOCATE`/`INSTR`; Oracle and Firebird `INSTR` |

## 3. Temporal contracts

- **temporal − temporal** is a duration whose **type is the backend's**, not a
  single interpolated one: integer days (PostgreSQL), decimal days (Firebird),
  seconds (ClickHouse), interval (Snowflake, BigQuery), timedelta-shaped
  (Oracle), silent numeric difference on MySQL and MariaDB. Only
  `timestamp − timestamp` is an interval nearly everywhere. `TemporalArithmeticMixin`
  no longer claims one result type.
- **date_diff** takes a unit enum (`YEAR MONTH WEEK DAY HOUR MINUTE SECOND`)
  and the counting rule is per unit: calendar units count boundaries crossed,
  exact-span units measure the span. Backends mix the two natively
  (PostgreSQL: YEAR/MONTH are year-month differences but DAY is an epoch
  difference), so the mix is declared per unit rather than promised away.

## 4. Value-layer echo (ResultTypeMixin)

| Conversion | Honest statement |
|---|---|
| `sign` | The value is -1/0/1, but the result is **numeric**, not integer: PostgreSQL answers an integer argument with `double precision` and a numeric argument with `numeric` |
| `round` | Halves are a function of (backend, version, column type): decimal half-away-from-zero on MySQL/MariaDB/PostgreSQL/Firebird/Oracle/SQL Server, half-to-even on ClickHouse; float half-to-even on MySQL 8.0/MariaDB/PostgreSQL/ClickHouse and half-away on Oracle/Firebird/SQL Server. SQL Server **raises 22003** on `ROUND(±0.5, 0)`; MySQL 5.6/5.7 reject `CAST(x AS DOUBLE)` |
| `cast` to integer | Truncation toward zero on SQLite, PostgreSQL, SQL Server, Firebird, ClickHouse; half-away from zero on Oracle, BigQuery |
| UUID / BLOB / JSON reads | Equality is portable for all three; ordering is not (UUID and BLOB are not orderable on most backends); JSON equality is not (PostgreSQL `json` has none, use `jsonb`) |

## 5. Boolean and pattern declaration

- **Boolean literals** come in three tiers: TRUE/FALSE keyword backends
  (PostgreSQL, SQLite, MySQL, MariaDB, ClickHouse, BigQuery, Snowflake),
  0/1 backends where the framework renders the 0/1 form (SQL Server `bit`),
  and backends with no boolean type at all (Oracle below 23ai). The framework
  renders the portable form rather than the native spelling.
- **LIKE sensitivity is the backend's**: case-insensitive on SQLite, MySQL,
  MariaDB and SQL Server (following collation), case-sensitive on PostgreSQL,
  ClickHouse, Oracle and BigQuery, collation-dependent on Firebird and
  Snowflake. `ilike` is the only spelling that *means* case-insensitive; no
  `COLLATE` clause on the predicate changes a CI default.
- **Length units** are three: characters (PostgreSQL, Oracle, Firebird),
  bytes (MySQL, MariaDB, ClickHouse) and UTF-16 code units (SQL Server, which
  maps both LENGTH and CHAR_LENGTH to LEN).

## 6. Version gates

A gate belongs to the dialect that has the limit and refuses below it --
never a silent substitution of a different question:

- **`IS [NOT] DISTINCT FROM`**: native on PostgreSQL, Firebird, Snowflake,
  BigQuery, SQL Server (2022+), SQLite (3.39+). Below the gate, or where the
  spelling is missing, the framework raises `UnsupportedFeatureError` naming
  the version. Oracle answers `NOT LNNVL(a = b)` / `LNNVL(a = b)` (its
  `IS NOT DISTINCT FROM` is ORA-00908), which is exact and therefore a
  rendering override rather than a downgrade.
- SQLite's function table carries the rest of its gates (math functions
  3.35+ with the build flag, `unhex` 3.45+, `json_array_insert` 3.53+,
  `concat` 3.44+, `jsonb` 3.45+); PostgreSQL's `regexp_like` gate corrects to
  15 (live-verified on 14 and 15).

## 7. Where each is enforced

- Construction-time refusal: the core factory that builds the node
  (`functions/string.py`, `functions/math.py`), so every caller meets the same
  error before SQL exists.
- Rendering overrides: the dialect's `format_*` hook (the only one for scalar
  function calls is `format_function_call`; pattern, comparison and null-test
  nodes have their own hooks).
- Capability statements: this file, plus the docstring of the method that
  makes the statement.
