# Technical Decision Guide

Choosing an ORM is a significant architectural decision that affects your project's maintainability, performance, and team productivity. This guide helps you understand when `rhosocial-activerecord` is the right choice—and when you might want to consider alternatives.

## At a Glance

| Aspect | rhosocial-activerecord | Best For |
| :--- | :--- | :--- |
| **Pattern** | Active Record | Rapid development, intuitive data modeling |
| **Validation** | Pydantic V2 (Native) | Type-safe applications, FastAPI integration |
| **Architecture** | Standalone | Framework-agnostic projects, microservices |
| **Testing** | Zero-IO Testing | Fast test suites, CI/CD pipelines |
| **Performance** | Adjustable (Strict ↔ Raw) | Mixed workloads (OLTP + reporting) |
| **Learning Curve** | Low | Teams new to Python ORMs |

## When to Choose rhosocial-activerecord

### ✅ You want ActiveRecord pattern without framework lock-in

**The situation:** You love the ActiveRecord pattern (class = table, instance = row) but Django ORM forces you to use Django, and Rails is Ruby.

**Why us:** We provide a **standalone, modern ActiveRecord implementation** that works in:
- FastAPI applications
- Flask microservices  
- Standalone scripts and CLI tools
- Jupyter notebooks
- Data processing pipelines
- Any Python environment

> 💡 **AI Prompt:** "Explain the trade-offs between ActiveRecord and Data Mapper patterns for microservices architecture."

### ✅ You need type safety with minimal overhead

**The situation:** You want compile-time type checking and IDE autocomplete without complex configuration.

**Our approach:** 
- Native Pydantic V2 integration (not optional add-on)
- `FieldProxy` system: `User.c.age` provides IDE autocomplete and type checking
- No string-based queries that break silently

**Comparison:**
- Django ORM: Dynamic, limited IDE support
- SQLAlchemy: Can be typed but requires configuration
- **Us: Type-safe by default, zero config**

### ✅ You want to test without databases

**The situation:** Your CI/CD pipeline is slow because tests need Docker, database setup, and seed data.

**Our solution:** Native **Zero-IO Testing**
```python
# Test SQL generation without touching a database
sql, params = User.query().where(User.c.age > 18).to_sql()
assert "age > ?" in sql
assert params == (18,)
```

No Docker. No database. Tests run in milliseconds.

> 💡 **AI Prompt:** "Compare Zero-IO testing with traditional database-dependent testing. What are the trade-offs?"

### ✅ You have mixed performance requirements

**The situation:** Your application has both strict validation needs (user registration) and high-performance reporting needs (million-row aggregations).

**Our solution:** **Gradual ORM** approach
```python
# Strict mode: Full validation, lifecycle hooks
user = User(email="alice@example.com")
user.save()  # Validates, hooks, etc.

# Raw mode: Skip overhead for performance
results = User.query().where(User.c.active == True).aggregate()
# Returns dicts, skips model instantiation
```

Same ORM, different performance profiles.

### ✅ You want AI-assisted development

**The situation:** You want to leverage AI code agents (Claude Code, GitHub Copilot, Cursor) to accelerate development.

**Why us:** Built-in AI support
- Auto-discovered configurations for AI agents
- Skills and commands for code generation
- Type-safe API is easier for AI to understand and generate

## When to Consider Alternatives

### 🤔 Consider SQLAlchemy if...

**You need extreme flexibility**
- Complex multi-table inheritance hierarchies
- Database-agnostic DDL operations
- Custom SQL compilation for every query

**Why:** SQLAlchemy's Data Mapper pattern offers more flexibility for complex domain models.

> 💡 **AI Prompt:** "When should I choose SQLAlchemy's Data Mapper over ActiveRecord?"

### 🤔 Consider Django ORM if...

**You're already building a Django application**
- Using Django admin, forms, and templates
- Need Django's migration system
- Team is already familiar with Django

**Why:** Django ORM integrates seamlessly with Django's ecosystem. Using a standalone ORM in Django adds complexity without benefit.

> ⚠️ **Exception:** If you're using Django for admin but FastAPI for APIs, consider using rhosocial-activerecord in the FastAPI service and Django ORM in the admin.

### 🤔 Consider SQLModel if...

**You specifically want SQLAlchemy + Pydantic integration**
- Need SQLAlchemy's ecosystem (alembic, etc.)
- Want Pydantic models that work with SQLAlchemy
- Comfortable with SQLAlchemy's learning curve

**Trade-off:** SQLModel inherits from both Pydantic and SQLAlchemy, which can cause metaclass conflicts. It also doesn't solve SQLAlchemy's session complexity.

### 🤔 Consider Prisma Client Python if...

**You want a schema-first approach**
- Prefer defining schema in a DSL
- Need code generation from schema
- Want type-safe queries generated from schema

**Trade-off:** Requires build step, less flexible for dynamic queries.

## Decision Matrix

| Your Situation | Recommendation |
| :--- | :--- |
| FastAPI + Pydantic + Type Safety | **✅ rhosocial-activerecord** |
| Flask microservice | **✅ rhosocial-activerecord** |
| Standalone scripts/CLI tools | **✅ rhosocial-activerecord** |
| Django monolith | 🤔 Django ORM (native) |
| Complex domain model, heavy inheritance | 🤔 SQLAlchemy |
| Need SQLAlchemy ecosystem | 🤔 SQLAlchemy or SQLModel |
| Schema-first, code generation | 🤔 Prisma |
| Learning Python ORMs for first time | **✅ rhosocial-activerecord** (lowest curve) |

## Migration Scenarios

### From Django ORM to rhosocial-activerecord

**Easiest when:**
- Extracting a Django app to a microservice
- Building a FastAPI API alongside Django admin
- Moving from monolith to services

**Challenges:**
- Losing Django's migration system (use Alembic or raw SQL)
- Replacing Django admin (build your own or use alternatives)

**See:** [Coming from Django](coming_from_frameworks.md#if-youre-coming-from-django-orm)

### From SQLAlchemy to rhosocial-activerecord

**Easiest when:**
- Simplifying a complex SQLAlchemy setup
- Wanting less boilerplate for CRUD operations
- Moving to async without SQLAlchemy's async complexity

**Challenges:**
- Losing SQLAlchemy's extreme flexibility
- Rewriting complex queries using Expression system

**See:** [Coming from SQLAlchemy](coming_from_frameworks.md#if-youre-coming-from-sqlalchemy)

### From Rails ActiveRecord

**Easiest when:**
- Ruby team moving to Python
- Wanting type safety that Ruby can't provide
- Keeping familiar ActiveRecord patterns

**Challenges:**
- Different conventions (snake_case vs camelCase)
- Python ecosystem differences

**See:** [Coming from Rails](coming_from_frameworks.md#if-youre-coming-from-rails-activerecord)

## Next Steps

### If you decide to use rhosocial-activerecord:

1. **[Getting Started](../getting_started/README.md)** — Installation and first model
2. **[Coming from Frameworks](coming_from_frameworks.md)** — Map your existing knowledge
3. **[Key Features](key_features.md)** — Tour of capabilities

### If you're still evaluating:

- **Prototype with both:** Build a small feature with rhosocial-activerecord and your current ORM
- **Check the ecosystem:** Ensure needed extensions exist
- **Team buy-in:** Let your team review this comparison

> 💡 **AI Prompt:** "I'm choosing between rhosocial-activerecord, SQLAlchemy, and Django ORM for [describe your project]. What factors should I consider?"

## See Also

- [Coming from Frameworks](coming_from_frameworks.md) — Detailed migration guides
- [Philosophy](philosophy.md) — Design principles and architectural decisions
- [Architecture](architecture.md) — Technical deep dive
