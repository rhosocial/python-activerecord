# Coming from Other Frameworks

If you're familiar with other ORMs or frameworks, this guide will help you map your existing knowledge to `rhosocial-activerecord` concepts.

## If you're coming from **Django ORM**

| Django | rhosocial-activerecord | Notes |
|--------|------------------------|-------|
| `models.Model` | `ActiveRecord` | Base class for models |
| `objects.filter()` | `.query().where()` | Query building |
| `objects.get()` | `.find()` or `.one()` | Get single record |
| `ForeignKey` | `BelongsTo` | Many-to-one relationship |
| `ManyToManyField` | Use through model + `HasMany` | Many-to-many via intermediate table |
| `auto_now_add`, `auto_now` | `TimestampMixin` | Automatic timestamps |
| `SoftDelete` (django-softdelete) | `SoftDeleteMixin` | Logical deletion |
| `F()` expressions | `FieldProxy` (e.g., `User.c.age`) | Type-safe field references |
| `QuerySet` | `ActiveQuery` | Query builder class |
| `select_related` | `.with_()` | Eager loading |

**Key differences:**
- Django uses string references in queries; we use type-safe `FieldProxy`
- Django has automatic migrations; we use explicit SQL or migration tools
- Django has a global database connection; we use explicit backend configuration

> 💡 **AI Prompt:** "I know Django ORM. Explain the key differences and similarities with rhosocial-activerecord."

## If you're coming from **SQLAlchemy**

| SQLAlchemy | rhosocial-activerecord | Notes |
|------------|------------------------|-------|
| `declarative_base()` | `ActiveRecord` | Base class |
| `session.query(Model)` | `Model.query()` | Query entry point |
| `filter()`, `filter_by()` | `.where()` | Filtering |
| `relationship()` | `HasMany`, `BelongsTo` | Relationships |
| `Column(Integer)` | `int` with type hints | Native Python types |
| `session.add()` | `.save()` | Persist object |
| `session.commit()` | Auto-commit or explicit | Transaction handling |
| `select()` | `QueryExpression` | SQL expression building |
| `text()` raw SQL | Use with caution | We prefer expressions |

**Key differences:**
- SQLAlchemy uses a session-based approach; we use Active Record pattern
- SQLAlchemy has Core and ORM layers; we unified them
- SQLAlchemy requires explicit table definitions; we use Pydantic models
- Our Expression-Dialect separation is similar to SQLAlchemy's compiler but more explicit

> 💡 **AI Prompt:** "Compare SQLAlchemy 2.0 with rhosocial-activerecord architecture. What are the pros and cons of each?"

## If you're coming from **Rails ActiveRecord**

| Rails | rhosocial-activerecord | Notes |
|-------|------------------------|-------|
| `ActiveRecord::Base` | `ActiveRecord` | Base class |
| `where()` | `.where()` | Same method name! |
| `find()` | `.find()` | Get by primary key |
| `has_many` | `HasMany` | One-to-many |
| `belongs_to` | `BelongsTo` | Many-to-one |
| `has_one` | `HasOne` | One-to-one |
| `validates` | Pydantic `Field()` | Validation |
| `before_save` | Model events/hooks | Lifecycle callbacks |
| `scope` | Class methods returning queries | Reusable query definitions |

**Key differences:**
- Rails is Ruby; we are Python with full type safety
- Rails has magical methods; we prefer explicit type-safe approaches
- Rails migrations are Ruby DSL; we use SQL or migration tools
- Our `FieldProxy` provides IDE support that Ruby can't match

> 💡 **AI Prompt:** "I come from Rails. How do I translate my ActiveRecord knowledge to this Python ORM?"

## If you're coming from **Peewee**

| Peewee | rhosocial-activerecord | Notes |
|--------|------------------------|-------|
| `Model` | `ActiveRecord` | Base class |
| `CharField()`, `IntegerField()` | `str`, `int` with type hints | Native Python types |
| `fn` functions | `functions` module | SQL functions |
| `prefetch()` | `.with_()` | Eager loading |
| `database` proxy | Explicit backend | Database connection |

**Key differences:**
- Peewee uses field instances; we use Python type hints
- Peewee has a simpler API; we have more type safety
- Our Expression system is more powerful than Peewee's query builder

> 💡 **AI Prompt:** "Compare Peewee with rhosocial-activerecord. When should I choose one over the other?"

## If you're coming from **Prisma** (TypeScript/Node.js)

| Prisma | rhosocial-activerecord | Notes |
|--------|------------------------|-------|
| `schema.prisma` | Python type hints | Schema definition |
| `prisma.user.findMany()` | `User.query().all()` | Query methods |
| `include` | `.with_()` | Relation loading |
| Generated client | Direct class usage | No code generation needed |
| Type-safe queries | `FieldProxy` | Both provide type safety |

**Key differences:**
- Prisma requires schema file and code generation; we use pure Python
- Prisma has its own query language; we use Python expressions
- No build step required with rhosocial-activerecord

> 💡 **AI Prompt:** "I used Prisma in TypeScript. How does this Python ORM compare in terms of developer experience?"

## Common Migration Patterns

### Defining Models

**Django:**
```python
class User(models.Model):
    username = models.CharField(max_length=50)
    email = models.EmailField()
```

**rhosocial-activerecord:**
```python
class User(ActiveRecord):
    __table_name__ = "users"
    username: str = Field(max_length=50)
    email: str
```

### Querying

**SQLAlchemy:**
```python
session.query(User).filter(User.age > 18).all()
```

**rhosocial-activerecord:**
```python
User.query().where(User.c.age > 18).all()
```

### Relationships

**Rails:**
```ruby
class User < ApplicationRecord
  has_many :posts
end
```

**rhosocial-activerecord:**
```python
class User(ActiveRecord):
    posts: ClassVar[HasMany["Post"]] = HasMany(foreign_key="user_id")
```

## Quick Reference Card

| Concept | What to Use Here |
|---------|------------------|
| Model base class | `ActiveRecord` / `AsyncActiveRecord` |
| Field definition | Python type hints + `Field()` from Pydantic |
| Validation | Pydantic validation in `Field()` |
| Query building | `.query().where().order_by().all()` |
| Type-safe field access | `User.c.field_name` (FieldProxy) |
| Relationships | `BelongsTo`, `HasOne`, `HasMany` |
| Timestamps | `TimestampMixin` |
| Soft delete | `SoftDeleteMixin` |
| Database backend | Configure with `Backend` class |
| Raw SQL | Use only when necessary; prefer expressions |

## Getting Help

- Not sure how to translate a pattern? Look for 💡 AI Prompt markers in the documentation
- Ask your AI assistant: "How do I do [X] from [framework] in rhosocial-activerecord?"
- Check the [Glossary](glossary.md) for terminology explanations

## See Also

- [Technical Decision Guide](comparison.md) - Still evaluating which ORM to use?
- [Glossary](glossary.md) - Terminology explained
- [Key Features](key_features.md) - Core capabilities tour
- [AI-Assisted Development](ai_assistance.md) - Using AI to accelerate learning
