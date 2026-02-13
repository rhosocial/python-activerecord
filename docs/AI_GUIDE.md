# AI-Assisted Development Guide

This guide explains how AI code agents and editors can help you work with rhosocial-activerecord — whether you're building an application on top of it or contributing to the ORM itself.

## Overview

rhosocial-activerecord is designed to be AI-friendly by default: explicit type annotations, transparent SQL via `.to_sql()`, clean naming conventions, and structured documentation. On top of that, the repository ships with tool-specific configurations that are discovered automatically when you launch an agent in the project directory.

### What's in the Box

```
python-activerecord/
├── CLAUDE.md                    # Claude Code: project-level instructions
├── AGENTS.md                    # Codex / general agents: project context
├── .claude/
│   ├── skills/                  # Claude Code: 12 specialized skill files
│   │   ├── user-activerecord-pattern/SKILL.md
│   │   ├── user-backend-development/SKILL.md
│   │   ├── user-enterprise-features/SKILL.md
│   │   ├── user-getting-started/SKILL.md
│   │   ├── user-modeling-guide/SKILL.md
│   │   ├── user-performance-tuning/SKILL.md
│   │   ├── user-query-advanced/SKILL.md
│   │   ├── user-relationships/SKILL.md
│   │   ├── user-testing-guide/SKILL.md
│   │   ├── user-troubleshooting/SKILL.md
│   │   ├── dev-sync-async-parity/SKILL.md
│   │   ├── dev-expression-dialect/SKILL.md
│   │   ├── dev-protocol-design/SKILL.md
│   │   └── dev-testing-contributor/SKILL.md
│   └── commands/                # Claude Code: 13 slash commands
├── .opencode/
│   ├── commands/                # OpenCode: 13 slash commands
│   └── hints.yml               # OpenCode: keyword-triggered suggestions
├── docs/
│   ├── LLM_CONTEXT.md          # Structured reference for any LLM
│   └── ARCHITECTURE.md         # Architecture deep-dive
```

Each tool reads the files it understands:

| Tool | Auto-discovered files |
|---|---|
| Claude Code | `CLAUDE.md`, `.claude/skills/`, `.claude/commands/` |
| OpenCode | `.opencode/commands/`, `.opencode/hints.yml` |
| Codex | `AGENTS.md` |
| Cursor | `CLAUDE.md`, `AGENTS.md` (via context), `.cursor/rules/` if added |
| Windsurf | `CLAUDE.md`, `AGENTS.md` (via context), `.windsurfrules` if added |

> **Cursor and Windsurf**: Both editors can reference `CLAUDE.md` and `AGENTS.md` as project context. If you need editor-specific rules, you can add `.cursor/rules/` or `.windsurfrules` files — but we don't ship them by default since the existing context files cover the project conventions well.

## For Application Developers

If you're using rhosocial-activerecord to build an application, AI agents can accelerate your workflow in several concrete ways.

### Generating Models from Requirements

Describe your domain and let the agent generate model classes with proper fields, types, relationships, and behaviors.

**Example prompt:**
```
Create a blog system with User, Post, Comment, and Tag models.
Users have many posts. Posts have many comments and belong to a user.
Posts and tags have a many-to-many relationship.
Use timestamps and soft delete on Post and Comment.
```

The agent will produce model files with `ActiveRecord` base classes, `HasMany`/`BelongsTo`/`HasOne` relationships, `TimestampMixin`, `SoftDeleteMixin`, and `FieldProxy` declarations — all following project conventions.

### Building Complex Queries

The expression-based query API is powerful but has a learning curve for CTEs, window functions, and multi-table joins. Agents handle this well because every query component is a typed Python object.

**Example prompts:**
```
Write a query that finds the top 3 authors by post count, excluding soft-deleted posts.

Show me how to use a CTE to get all users who signed up in the last 30 days,
then join with their orders.

Create a window function query that ranks products by sales within each category.
```

### Inspecting SQL Before Execution

One of the most useful patterns is asking the agent to write a query _and_ show you the generated SQL:

```
Write a query to find users older than 18 with at least 5 posts,
then show me what SQL it generates for both SQLite and PostgreSQL.
```

The agent can call `.to_sql()` on the query object to reveal the exact SQL and parameter bindings, helping you verify correctness before running anything.

### Writing Tests

Describe the behavior you want to test and the agent will generate test functions covering both sync and async paths.

**Example prompt:**
```
Write tests for a User model: verify that save() persists to the database,
that query filters work correctly, and that soft delete sets deleted_at
instead of removing the row. Cover both sync and async.
```

## For Contributors

If you're contributing to rhosocial-activerecord itself, AI agents become even more valuable — the project has strict conventions that agents can enforce automatically.

### Implementing a New Backend

Adding a new database backend (e.g., Oracle, SQL Server) is one of the most common contribution tasks. The agent can scaffold the entire structure.

**Example prompt (Claude Code):**
```
@backend-development Create an Oracle backend. Follow the SQLite implementation
as reference. Include both sync and async backends, dialect, and tests.
```

The agent will:
1. Create a Dialect subclass with Oracle-specific SQL rendering (`:1` bind style, `ROWNUM` pagination, etc.)
2. Create sync and async Backend subclasses with connection management
3. Generate test files mirroring the existing test structure
4. Verify that the new code follows the dependency direction rules

### Adding a New Expression Type

If you need to support a new SQL construct (e.g., `LATERAL JOIN`, `GROUPING SETS`), the agent can help implement the expression node and its dialect renderers.

**Example prompt:**
```
@expression-dialect Add a LateralJoinExpression to the expression hierarchy.
Implement rendering in SQLite (error — not supported), MySQL, and PostgreSQL dialects.
Include ToSQLProtocol compliance and tests.
```

### Checking Sync-Async Parity

A core project rule: every sync method must have an async counterpart. The agent can audit your code for violations.

**Example prompt (Claude Code):**
```
@sync-async-parity Check if all public methods in active_query.py have
matching async implementations.
```

**Example prompt (OpenCode):**
```
/check-sync-async
```

### Running and Interpreting Tests

**Claude Code / OpenCode:**
```
@testing-guide Run the query tests and explain any failures.
```

**OpenCode:**
```
/test                    # Run full suite
/test-feature query      # Run query-specific tests
```

The agent will run `pytest`, parse the output, and explain what failed and why — often suggesting a fix in the same response.

## Tool-Specific Tips

### Claude Code

Claude Code reads `CLAUDE.md` at the project root for global instructions and discovers skill files in `.claude/skills/` automatically. You can reference skills explicitly:

```
@user-activerecord-pattern      # Model definition and relationship conventions
@user-backend-development       # Database backend usage guide
@user-enterprise-features       # Enterprise features (locking, soft delete, etc.)
@user-getting-started           # Quick start guide
@user-modeling-guide            # Model definition patterns
@user-performance-tuning        # Performance optimization
@user-query-advanced            # Advanced query techniques
@user-relationships             # Relationship management
@user-testing-guide             # Testing patterns for users
@user-troubleshooting           # Common issues and solutions
@dev-sync-async-parity          # Rules for sync/async API consistency (contributors)
@dev-expression-dialect          # Query expression system internals (contributors)
@dev-protocol-design            # Protocol-based design (contributors)
@dev-testing-contributor        # Testing architecture (contributors)
```

Skills teach Claude about project-specific patterns, so generated code follows conventions without you having to repeat them.

### OpenCode

OpenCode picks up slash commands from `.opencode/commands/` and keyword hints from `.opencode/hints.yml`:

**Development commands:**
```
/test                    # Run the test suite
/test:feature <category> # Run tests for a specific feature (basic, query, relation, etc.)
/lint                    # Check code style
/lint:fix                # Auto-fix code style issues
/type-check              # Run type checking with mypy
```

**Code generation commands:**
```
/gen:model               # Generate ActiveRecord model
/gen:query               # Generate preset query methods
/gen:relation            # Generate model relationships
/gen:migration           # Generate database migration SQL
/validate:model          # Validate model configuration
```

**Framework development:**
```
/new-feature             # Scaffold a new feature
/new-backend             # Create new database backend
/check-sync-async        # Verify sync-async parity
```

Hints trigger automatically when you mention certain keywords, surfacing relevant context without explicit commands.

### Codex

Codex reads `AGENTS.md` at the project root. This file contains the project overview, source layout, core patterns, and contribution rules — enough context for Codex to generate code that follows project conventions.

### Cursor and Windsurf

Open the project folder in either editor. The AI features will benefit from the project's type annotations and docstrings. For deeper context, you can:

1. Add `docs/LLM_CONTEXT.md` or `AGENTS.md` to the editor's context/rules configuration
2. Reference these files when asking the AI for help with project-specific patterns

## Best Practices

**Be specific about what you want.** "Create a User model" is fine. "Create a User model with email uniqueness validation, age as optional integer, timestamps, and soft delete" is better — it lets the agent produce a complete result in one shot.

**Ask for `.to_sql()` output.** When working with queries, always ask the agent to show the generated SQL. This catches issues early and helps you understand the expression tree.

**Reference the right context.** If the agent generates code that doesn't follow project conventions, point it to the relevant skill or context file. For example: "Check @sync-async-parity — this method needs an async counterpart."

**Use agents for auditing.** Beyond generating code, agents are good at reviewing existing code against project rules: checking type annotations, verifying sync-async parity, ensuring `ToSQLProtocol` compliance, and finding missing tests.
