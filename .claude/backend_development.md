# Backend Development — Entry Point

> **Scope**: This file is the **entry point** for backend development work. The full detailed
> implementation guide has moved into the **`dev-backend-development`** and
> **`dev-expression-dialect`** skills — load them when implementing a new database backend or
> adding dialect features.

## Start Here

- **New database backend / StorageBackend / type adaptation / transactions / error handling /
  async parity / testing / release checklist** → load **`dev-backend-development`**.
- **Expression-Dialect separation / SQL generation rules / protocol-mixin system / adding
  protocols** → load **`dev-expression-dialect`**.

## Key Facts (quick reminder)

- Backends must use **native database drivers only** (no SQLAlchemy/Django ORM).
- Backend package layout: `src/rhosocial/activerecord/backend/impl/{backend}/` with
  `backend.py`, `adapters.py`, `config.py`, `dialect.py`, `transaction.py`, plus required
  `expression/` and `functions/` **directories**. See the skill for layout evolution notes.
- `AsyncStorageBackend` must be **functionally equivalent** to the sync `StorageBackend`.
- Before public release: own test suite, `rhosocial-activerecord-testsuite` compliance, CI.

## Reference Implementations

Study `rhosocial-activerecord-mysql` (MySQL) and `rhosocial-activerecord-postgres`
(PostgreSQL) — especially `backend.py`, `adapters.py`, and `tests/`.