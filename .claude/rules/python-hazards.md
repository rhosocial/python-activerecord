# Python syntax for the organisation-level clauses

> The clauses themselves are language-neutral and live in the organisation's
> `.claude/rules/expression-dialect.md` §11 -- override order, the reflection
> ban, enum-first. This file records only the Python spelling of each and the
> measured surface in this repository.

| Clause | Python spelling |
|---|---|
| §11.1 override order | `class D(SQLiteJoinMixin, SQLDialectBase)`: the base list left to right *is* the MRO, so `super()` follows it |
| §11.2 reflection ban | `getattr` / `hasattr` may not probe an expression for a field; assert to `BaseExpression`, never to a method |
| §11.3 enum-first | `class U(str, Enum)`; inheriting `str` keeps the member usable wherever a string is expected |

---

## 1. Override order (clause §11.1)

Measured surface: **1** violation.

| Site | What |
|---|---|
| `impl/sqlite/expression/json.py` `SQLiteJsonExtractFunction` | spells `AliasableMixin, ComparisonMixin, TypeCastingMixin, SQLValue` by hand instead of deriving from the core JSON-extraction node, so the two sides drift when the core gains an operation |

Eighteen SQLite classes derive from a bare `BaseExpression` / `SQLValue` /
`SQLPredicate` and that is **correct**: `ATTACH`, `DETACH`, `REINDEX`, `VACUUM`,
`ANALYZE`, the virtual table statements and the FTS5 / R*Tree / Geopoly families
are concepts no other backend has and no core node describes. §11.1 exempts them
— the test is whether you can name the core node being specialised.

`impl/sqlite/dialect.py` already keeps the name mixins ahead of `NamespaceMixin`
and documents why; the same discipline is what the other mixins need.

---

## 2. Reflection ban (clause §11.2)

**`getattr(x, "f", None)` / `hasattr(x, "f")` on an expression is forbidden.**

| Instead of | Declare |
|---|---|
| `getattr(self, "alias", None)` | `alias: Optional[str] = None` on `BaseExpression` |
| `hasattr(other, "to_sql")` | `isinstance(other, BaseExpression)` |
| `getattr(self.dialect, name, None)` | `format_method` names it; absent ⇒ `UnsupportedFeatureError` |
| probing `_{name}` in `get_params()` | store each `__init__` parameter under its own name |

**`get_params()` is the exhibit.** `expression/bases.py:394-406` probes `_{name}`
then `name`, warns, and **skips the parameter**. A serialization path deciding
what to record by trial and error. `dummy2/test_expression_contract.py` already
enforces the convention that makes the probe unnecessary; once it holds,
`get_params()` is `getattr(self, name)` and the warning branch is unreachable.

Two exemptions, neither a discovery: `getattr` inside `__getattr__` itself, and
`getattr(module, name)` on the type registry where the name is already part of
the artifact's wire contract.

Measured surface: **205** `getattr`/`hasattr` sites under `backend/` —
`named_expression/procedure.py` (24), `type_adapter.py` (15),
`migration/cli.py` (13), `expression/mixins.py` (10), `expression/bases.py` (8).
The expression and dialect layers are the ones that must reach zero.

---

## 3. Enum-first (clause §11.3)

**A parameter with a closed value set takes an Enum, not a string and not a
module-level tuple / frozenset / dict.** `str` as the base keeps the member
usable wherever a string is expected.

Exempt: compiled regexes and fragments, numeric defaults, and lazily built
caches keyed by classes — the last is the same exemption §11.2 makes for the
registry.

Measured surface: **34** private constants under `expression/` and `dialect/`,
counting class-level ones and not only module-level. **9** are enumerable
domains; the other 25 are exempt.

| Site | Domain | Count |
|---|---|---|
| `expression/query_sources.py:105` `_VALID_OPS` | the four compound-SELECT word forms | 4 | — **done**: `SetOperationKind` / `SortDirection` / `NullsOrder` / `UuidConstantKind`
| `dialect/mixins/set_operation.py:15` `_OP_SYMBOLS` | the same four, mapped to their SQL keyword | 4 | — **done**: `SetOperationKind` / `SortDirection` / `NullsOrder` / `UuidConstantKind`
| `expression/mixins.py:839` `_OPERATOR_WORDS` | Python operator symbol -> operation word | 3 |
| `expression/query_parts.py:238` `_VALID_DIRECTIONS` | sort direction | 2 | — **done**: `SetOperationKind` / `SortDirection` / `NullsOrder` / `UuidConstantKind`
| `dialect/mixins/dql.py:160` `_VALID_ORDER_DIRECTIONS` | sort direction, **the same set declared a second time** | 2 | — **done**: `SetOperationKind` / `SortDirection` / `NullsOrder` / `UuidConstantKind`
| `expression/query_parts.py:239` `_VALID_NULLS` | where nulls sit in an ordering | 2 | — **done**: `SetOperationKind` / `SortDirection` / `NullsOrder` / `UuidConstantKind`
| `expression/uuid.py:115` `_KINDS` | which UUID constant | 2 | — **done**: `SetOperationKind` / `SortDirection` / `NullsOrder` / `UuidConstantKind`
| `expression/datetime.py:53` `_FIELD_ALIASES` | field aliases collapsing `"yyyy"`/`"yy"`/`"years"` | 24 |
| `expression/datetime.py:79` `_UNIT_ALIASES` | unit aliases, same shape | 22 |

The sort-direction set was declared in the expression layer *and* again in the
dialect layer with nothing keeping them in step. One Enum removes the duplication
and makes a fifth direction impossible to add to only one of them.